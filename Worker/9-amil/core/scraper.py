import os
import sys
import importlib.util
from datetime import datetime
import json
import time

# ── Isolate Environment (Ensure base imports from Worker/ root) ──
_worker_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _worker_root not in sys.path:
    sys.path.insert(0, _worker_root)

# Raiz do módulo 9-amil (para core.exceptions / config.constants das OPs)
_module_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _module_root not in sys.path:
    sys.path.insert(0, _module_root)

# Cross-talk SEQUENCIAL entre convênios no MESMO processo server (job_lock
# serializa jobs, mas o scraper do convênio anterior — ex. 6-ipasgo — deixa
# sys.modules['core'] apontando para o pacote DELE; o import top-level abaixo
# resolveria o pacote errado → "No module named 'core.exceptions'"). Este
# import roda ANTES do purge do execute_op, então purga aqui (mesma defesa
# do 1-bradesco, incidentes 26219-26224).
for _k in [k for k in list(sys.modules)
           if k in ("core", "config") or k.startswith("core.") or k.startswith("config.")]:
    del sys.modules[_k]

from base_scraper import BaseScraper
from op_load_lock import op_load_lock
from models import JobExecution, UserConvenio
from security_utils import decrypt_password
from database import SessionLocal
from core.exceptions import LoginFailedError, SessionExpiredError


class AmilScraper(BaseScraper):
    """
    Scraper da AMIL (id_convenio=9, integrador 9 — credenciado.amil.com.br).

    Arquitetura (plano_amil_op0_op1, decisões D4/D5/D8):
      - Sessão = driver vivo no pool ((id_convenio, user_id)); tokens vivem no
        storage do navegador e NUNCA são persistidos completos no banco.
      - UC driver (Akamai _abck/bm_sz) garantido pelo SeleniumManager (conv. 9).
      - Rotinas canônicas: op0_login / op1_consulta (aliases '0'/'1' aceitos).
    """

    def __init__(self, id_convenio=9, db=None, headless=True, user_id=None):
        super().__init__(id_convenio, db, headless, user_id)
        self.db = db if db else SessionLocal()
        self.user_id = user_id
        self.username = None
        self.password = None
        self.cod_prestador = None
        self.module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 9-amil root

    # ── Credenciais (params-first; user_convenios como fallback) ──

    def _extract_credentials_from_dict(self, data_dict):
        """Resolve credenciais dos PARAMS do job (arquitetura params-first).

        Senha CRIPTOGRAFADA tem prioridade sobre plaintext: em params de
        consulta 'senha' pode ser a senha da GUIA (senhaAutorizacao), não a
        senha do portal (mesma defesa do BaseScraper/Bradesco).
        """
        if not data_dict or not isinstance(data_dict, dict):
            return False

        params = data_dict.get("params")
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except Exception:
                params = None

        merged = {}
        merged.update(data_dict)
        if isinstance(params, dict):
            merged.update(params)

        login_val = merged.get("login") or merged.get("username") or merged.get("usuario")
        pwd_raw = None
        if merged.get("senha_criptografada"):
            try:
                pwd_raw = decrypt_password(merged.get("senha_criptografada"))
            except Exception:
                pwd_raw = None
        if not pwd_raw and merged.get("password"):
            pwd_raw = merged.get("password")

        login_val = str(login_val).strip() if login_val else None
        pwd_val = str(pwd_raw).strip() if pwd_raw else None
        # Só atribui quando o PAR completo existe — evita herança de um load
        # anterior com senha de outro portal (lição do incidente Bradesco).
        if not (login_val and pwd_val):
            return False
        self.username = login_val
        self.password = pwd_val

        prest_val = (
            merged.get("cod_prestador") or
            merged.get("codigoPrestador") or
            merged.get("prestador")
        )
        if prest_val:
            self.cod_prestador = str(prest_val).strip()

        return True

    def _load_credentials(self, job_data=None):
        """Credenciais via PARAMS do job; user_convenios apenas como último
        recurso (decrypt de security_utils)."""
        try:
            if job_data and self._extract_credentials_from_dict(job_data):
                self.log(
                    f"Credenciais carregadas via job_data (user_id={self.user_id}, "
                    f"prestador={self.cod_prestador}, login={self.username})"
                )
                return True

            if self.user_id and self.db:
                user_conv = self.db.query(UserConvenio).filter(
                    UserConvenio.user_id == self.user_id,
                    UserConvenio.id_convenio == self.id_convenio
                ).first()
                if user_conv and user_conv.login and user_conv.senha_criptografada:
                    self.username = user_conv.login
                    self.password = decrypt_password(user_conv.senha_criptografada)
                    self.cod_prestador = user_conv.cod_prestador
                    self.log(
                        f"Credenciais carregadas de user_convenios "
                        f"(user_id={self.user_id}, prestador={self.cod_prestador})"
                    )
                    return True
                self.log(
                    f"Registro user_convenios incompleto para user_id={self.user_id} e "
                    f"convenio={self.id_convenio}. "
                    f"Login={getattr(user_conv, 'login', 'N/A') if user_conv else 'NOT FOUND'}",
                    level="WARN"
                )
            else:
                self.log("user_id nao fornecido ao scraper — nao foi possivel carregar credenciais", level="WARN")
        except Exception as e:
            self.log(f"AMIL Credential Load Error: {e}", level="ERROR")
        return False

    def reload_credentials(self, user_id, job_data=None):
        """Recarrega credenciais para um user_id diferente."""
        self.user_id = user_id
        self.username = None
        self.password = None
        self.cod_prestador = None
        self._load_credentials(job_data)

    # ── Driver (gerenciado pelo SeleniumManager — UC para convênio 9) ──

    def start_driver(self):
        pass  # Managed by SeleniumManager

    def close_driver(self):
        pass  # Managed by SeleniumManager

    def _reciclar_driver(self, job_id=None):
        """Escada de recuperação de sessão: a sessão persistiu expirada mesmo
        após re-login no mesmo driver → recicla o Chrome com quit() SEM logoff.
        O próximo attempt pega um driver novo pelo pool (padrão bradesco)."""
        drv = getattr(self, "driver", None)
        if drv is not None:
            try:
                drv.quit()
            except Exception:
                pass
        self.driver = None
        self.log(
            "Driver reciclado (sessão expirada persistiu após re-login) — "
            "novo Chrome será criado na próxima tentativa",
            job_id=job_id,
        )

    def log(self, message, level="INFO", job_id=None, carteirinha_id=None):
        job_prefix = f"[Job {job_id}] " if job_id else ""
        print(f"[{level}] [AMIL] {job_prefix}{message}")
        # Persist to database logs table for frontend visibility
        try:
            if self.db:
                from models import Log as LogModel
                log_entry = LogModel(
                    job_id=job_id,
                    carteirinha_id=carteirinha_id,
                    user_id=self.user_id,
                    level=level,
                    message=f"[AMIL] {message}"
                )
                self.db.add(log_entry)
                self.db.commit()
        except Exception as e:
            # Never let a logging failure break the scraper flow
            print(f"[WARN] [AMIL] Failed to persist log to DB: {e}")
            try:
                self.db.rollback()
            except Exception:
                pass

    # ── Execução de OPs ──

    def login(self, job_data=None):
        """Executes OP0 login routine."""
        if job_data is None:
            job_data = {}
        return self.execute_op("op0_login", job_data)

    def execute_op(self, op_name, job_data):
        """Carregador e executor genérico de OP (padrão importlib do projeto).

        Purga módulos de Worker/<id>-* de sys.modules sob o op_load_lock global
        (mesma região crítica do 1-bradesco — sem o lock, dois convênios
        carregando OPs concorrentemente fazem 'core'/'config' resolverem para
        o pacote errado). A purga também examina __path__ de pacotes NAMESPACE
        (sem __init__.py, __file__=None — defesa do 102-caesan). Módulos da
        raiz do Worker (base_scraper/models/...) ficam de fora.
        """
        op_path = os.path.join(self.module_path, "op", f"{op_name}.py")
        if not os.path.exists(op_path):
            raise FileNotFoundError(f"Operação {op_name} não encontrada em {op_path}")

        with op_load_lock:
            for key in list(sys.modules):
                mod = sys.modules.get(key)
                if mod is None:
                    continue
                caminhos = []
                if getattr(mod, "__file__", None):
                    caminhos.append(os.path.abspath(mod.__file__))
                for pth in getattr(mod, "__path__", None) or []:
                    try:
                        caminhos.append(os.path.abspath(pth))
                    except Exception:
                        continue
                if not caminhos:
                    continue
                for mod_abs in caminhos:
                    # dentro de Worker\<dígitos>-...? (não purge módulos da raiz)
                    partes = mod_abs.lower().split(os.sep)
                    try:
                        idx = next(i for i, p in enumerate(partes)
                                   if p == "worker" and i + 1 < len(partes) and partes[i + 1][0].isdigit())
                    except StopIteration:
                        continue
                    del sys.modules[key]
                    break

            spec = importlib.util.spec_from_file_location(op_name, op_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        func = getattr(module, "run", None) or getattr(module, "execute", None)
        if not func:
            raise AttributeError(f"Módulo {op_name} não possui função 'run' ou 'execute'")

        return func(self, job_data)

    # ── Sessão ──

    def _sessao_invalida(self, job_id=None):
        """Detecta sessão inválida do SPA AMIL no driver atual:
        URL caiu em /login OU o elemento login-usuario está visível.
        Retorna True também quando não há driver (primeira execução).

        Usa Selenium DIRETO (sem core.selenium_helpers): este método roda ANTES
        da purga do execute_op e o pacote 'core' pode estar cacheado em
        sys.modules apontando para o de OUTRO integrador (cross-talk).
        """
        if not self.driver or getattr(self.driver, "session_id", None) is None:
            return True
        try:
            url = (self.driver.current_url or "").lower()
            if "/login" in url:
                return True
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.ID, "login-usuario"))
            )
            self.log("Elemento de login visível fora de /login — sessão inválida", level="WARN", job_id=job_id)
            return True
        except Exception:
            return False

    # ── Classificação de erros (imune à purga de sys.modules) ──

    def _classificar_erro(self, exc) -> str:
        """Roteia uma exceção do loop de tentativas em 3 categorias:
        'login_rejeitado' (fatal, sem retry), 'sessao' (escada de recuperação)
        ou 'generico' (retry simples).

        A purga de sys.modules do execute_op recarrega a OP do disco a cada
        job, então a LoginFailedError/SessionExpiredError que ela levanta é
        uma classe DIFERENTE das importadas neste módulo — isinstance falha.
        Por isso o fallback por PREFIXO da mensagem (estável), no padrão do
        1-bradesco (documentado em core/exceptions.py).
        """
        if isinstance(exc, LoginFailedError):
            return "login_rejeitado"
        if isinstance(exc, SessionExpiredError):
            return "sessao"
        msg = str(exc)
        if msg.startswith("LOGIN_REJEITADO:") or msg.startswith("AMIL_SEM_CREDENCIAIS"):
            return "login_rejeitado"
        if msg.startswith("SESSAO_EXPIRADA:"):
            return "sessao"
        return "generico"

    # ── Processamento do job ──

    def process_job(self, rotina, job_data):
        job_id = job_data.get("job_id") or job_data.get("id")
        start_time = datetime.now()

        execution = JobExecution(
            job_id=job_id,
            id_convenio=self.id_convenio,
            rotina=str(rotina),
            status="processing",
            start_time=start_time
        )
        self.db.add(execution)
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            self.log(f"Failed to record execution start: {e}", level="ERROR", job_id=job_id)

        # Merge params (JSONB dict ou string legada)
        params_raw = job_data.get("params")
        if params_raw:
            if isinstance(params_raw, dict):
                job_data.update(params_raw)
            elif isinstance(params_raw, str):
                try:
                    parsed = json.loads(params_raw)
                    if isinstance(parsed, dict):
                        job_data.update(parsed)
                except Exception as e:
                    self.log(f"Failed to parse job params: {e}", level="WARN", job_id=job_id)

        # Credenciais params-first; sem elas NEM TENTA o login (evita retries
        # com senha errada bloquearem a conta no portal).
        if not self._load_credentials(job_data):
            error_msg = (
                "AMIL_SEM_CREDENCIAIS: login/senha_criptografada ausentes nos params "
                "do job e em user_convenios — configure no frontend. Sem tentativa de login."
            )
            self.log(error_msg, level="ERROR", job_id=job_id)
            execution.status = "error"
            execution.error_message = error_msg[:1000]
            execution.error_category = "credential_error"
            execution.end_time = datetime.now()
            execution.duration_seconds = int((execution.end_time - start_time).total_seconds())
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
            raise ValueError(error_msg)
        self.log(f"Credenciais ativas (login={self.username})", job_id=job_id)

        # cod_prestador do JSON SEMPRE prevalece sobre o padrão do banco
        # (header x-user da API e codigoCredenciado da busca)
        if job_data.get("cod_prestador"):
            self.cod_prestador = str(job_data.get("cod_prestador")).strip()
            self.log(f"cod_prestador sobrescrito pelo JSON do Job: {self.cod_prestador}", job_id=job_id)

        results = []
        error_msg = None
        sessoes_expiradas = 0  # quedas consecutivas de sessão (escada: 2ª → reciclar driver)

        # Rotinas canônicas (D5): op0_login / op1_consulta + aliases numéricos
        op_map = {
            "0": "op0_login",
            "op0_login": "op0_login",
            "1": "op1_consulta_guias",
            "op1_consulta": "op1_consulta_guias",
            "op1_consulta_guias": "op1_consulta_guias",
        }

        op_name = op_map.get(str(rotina))
        if not op_name:
            if str(rotina).startswith("op"):
                op_name = str(rotina)
            else:
                op_name = f"op{rotina}"

        for attempt in range(self.max_retries):
            try:
                # Escada de sessão: dispensa login somente com sessão válida
                # no driver (URL fora de /login e sem formulário de login) E
                # do MESMO usuário do job (padrão bradesco).
                need_login = attempt > 0
                if not need_login:
                    if self._sessao_invalida(job_id=job_id):
                        need_login = True
                    elif self.driver:
                        driver_login = getattr(self.driver, "last_login", None)
                        if self.username and driver_login and driver_login != self.username:
                            self.log(
                                f"Driver session belongs to login={driver_login}, but job needs "
                                f"login={self.username}. Clearing cookies and forcing re-login.",
                                job_id=job_id
                            )
                            try:
                                self.driver.delete_all_cookies()
                                self.driver.get("about:blank")
                            except Exception as cookie_err:
                                self.log(f"Failed to clear cookies: {cookie_err}", level="WARN", job_id=job_id)
                            need_login = True

                if need_login:
                    if not self.driver or getattr(self.driver, 'session_id', None) is None:
                        try:
                            from server import sel_manager
                            self.driver = sel_manager.get_driver(self.id_convenio, headless=self.headless, user_id=self.user_id)
                        except Exception as pool_err:
                            self.log(f"Using isolated driver mode: {pool_err}", level="WARN", job_id=job_id)

                    # Rotina de login é auto-suficiente (detecta sessão ativa);
                    # as demais seguem o fluxo login → operação (evita dupla
                    # execução da OP0 — lição do incidente Bradesco 20652).
                    if op_name != "op0_login":
                        self.login(job_data)

                # Marca o usuário dono da sessão no driver (usado pela checagem acima)
                if self.driver:
                    self.driver.last_login = self.username

                # Execute mapped OP
                results = self.execute_op(op_name, job_data)

                execution.status = "success"
                break
            except Exception as e:
                error_msg = str(e)
                categoria = self._classificar_erro(e)

                if categoria == "login_rejeitado":
                    # Portal REJEITOU as credenciais (ou estão ausentes) — SEM
                    # retry: repetir a mesma senha multiplica tentativas erradas
                    # e pode BLOQUEAR a conta. O usuário corrige no frontend.
                    self.log(
                        f"Attempt {attempt + 1} failed (LOGIN REJEITADO — sem retry): {error_msg}",
                        level="ERROR", job_id=job_id,
                    )
                    execution.status = "error"
                    break

                if categoria == "sessao":
                    # Escada de recuperação: 1ª queda → re-login no mesmo driver
                    # (attempt seguinte já força need_login); 2ª consecutiva →
                    # reciclar o Chrome (quit sem logoff) e re-login limpo.
                    sessoes_expiradas += 1
                    self.log(
                        f"Attempt {attempt + 1} failed: {error_msg} "
                        f"(queda de sessão {sessoes_expiradas}/2)",
                        level="ERROR", job_id=job_id,
                    )
                    if sessoes_expiradas >= 2:
                        self._reciclar_driver(job_id=job_id)
                    if attempt < self.max_retries - 1:
                        time.sleep(5)
                    else:
                        execution.status = "error"
                    continue

                # Genérico: retry simples (reseta a escada de sessão)
                sessoes_expiradas = 0
                self.log(f"Attempt {attempt + 1} failed: {error_msg}", level="ERROR", job_id=job_id)
                if attempt < self.max_retries - 1:
                    time.sleep(5)
                else:
                    execution.status = "error"

        execution.end_time = datetime.now()
        execution.duration_seconds = int((execution.end_time - start_time).total_seconds())
        execution.items_found = len(results) if isinstance(results, list) else 1

        if execution.status != "success":
            execution.error_message = error_msg[:1000] if error_msg else "Unknown Error"
            execution.error_category = "scraper_error"

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()

        # Propaga a falha para o server/dispatcher: uma OP com erro NUNCA deve
        # terminar em job success vazio (lição do incidente Bradesco 20646).
        if execution.status != "success":
            raise ValueError(error_msg or "Unknown Error")

        return results
