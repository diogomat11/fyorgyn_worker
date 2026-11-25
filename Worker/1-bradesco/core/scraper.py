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

# Raiz do módulo 1-bradesco (para core.exceptions / core.mfa_helper dos op_*)
_module_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _module_root not in sys.path:
    sys.path.insert(0, _module_root)

# Cross-talk SEQUENCIAL entre convênios no MESMO processo server (job_lock
# serializa jobs, mas o scraper do convênio anterior — ex. 6-ipasgo — deixa
# sys.modules['core'] apontando para o pacote DELE; o import top-level abaixo
# resolveria o pacote errado → "No module named 'core.exceptions'"). Este
# import roda ANTES do purge do execute_op, então purga aqui (incidentes
# 26219-26224 / 26219 canário 14/11).
for _k in [k for k in list(sys.modules)
           if k in ("core", "config") or k.startswith("core.") or k.startswith("config.")]:
    del sys.modules[_k]

from base_scraper import BaseScraper
from op_load_lock import op_load_lock
from models import Convenio, JobExecution, UserConvenio
from security_utils import decrypt_password
from database import SessionLocal
from core.exceptions import LoginFailedError, MfaError, SessionExpiredError


class BradescoScraper(BaseScraper):
    """
    Scraper para o convênio Bradesco (id_convenio=1).
    Portal de autorização: Polimed/Orizon.
    """

    def __init__(self, id_convenio=1, db=None, headless=True, user_id=None):
        super().__init__(id_convenio, db, headless, user_id)
        self.db = db if db else SessionLocal()
        self.user_id = user_id
        self.username = None
        self.password = None
        self.cod_prestador = None
        self.module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 1-bradesco root

    def _extract_credentials_from_dict(self, data_dict, contexto="autorize"):
        """Resolve credenciais dos PARAMS do job (arquitetura params-first).

        SEGREGAÇÃO POR CONTEXTO (incidente: senha do Autorize digitada no
        Faturi → conta bloqueada): os portais Autorize (Polimed) e Fature
        (Orizon/Faturi) têm credenciais DISTINTAS —
          autorize → login / senha_criptografada
          fature   → login_fat / senha_fat_criptografada
        SEM fallback silencioso entre os pares (era o bug raiz).
        Senhas CRIPTOGRAFADAS têm prioridade sobre plaintext (params de OP19
        carregam 'senha' = senha da GUIA, não do portal).
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

        if contexto == "fature":
            login_val = merged.get("login_fat")
            pwd_raw = None
            if merged.get("senha_fat_criptografada"):
                try:
                    pwd_raw = decrypt_password(merged.get("senha_fat_criptografada"))
                except Exception:
                    pwd_raw = None
            if not pwd_raw and merged.get("senha_fat"):
                pwd_raw = merged.get("senha_fat")
        else:
            login_val = merged.get("login") or merged.get("username") or merged.get("usuario")
            pwd_raw = None
            if merged.get("senha_criptografada"):
                try:
                    pwd_raw = decrypt_password(merged.get("senha_criptografada"))
                except Exception:
                    pwd_raw = None
            if not pwd_raw:
                # Fallback plaintext só na ausência de versão criptografada
                pwd_raw = merged.get("password") or merged.get("senha")

        login_val = str(login_val).strip() if login_val else None
        pwd_val = str(pwd_raw).strip() if pwd_raw else None
        # VALIDAÇÃO LOCAL POR CONTEXTO: só atribui quando o par DO CONTEXTO
        # existe. Antes, username/password podiam ser HERANÇA de um load
        # anterior (server.reload_credentials com contexto autorize) → o login
        # do Faturi recebia a senha do Autorize → "inválidos" (incidente canário
        # 14/11: manual OK, automatizado rejeitado).
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

    def _load_credentials(self, job_data=None, contexto="autorize"):
        """
        Credenciais via PARAMS do job (params-first); user_convenios apenas
        como último recurso — com as colunas DO CONTEXTO (fature lê
        login_fat/senha_fat_criptografada, autorize lê login/senha_criptografada).
        """
        try:
            if job_data and self._extract_credentials_from_dict(job_data, contexto):
                self.log(f"Credenciais ({contexto}) carregadas via job_data (user_id={self.user_id}, prestador={self.cod_prestador}, login={self.username})")
                return True

            if self.user_id and self.db:
                user_conv = self.db.query(UserConvenio).filter(
                    UserConvenio.user_id == self.user_id,
                    UserConvenio.id_convenio == self.id_convenio
                ).first()
                if user_conv:
                    if contexto == "fature":
                        # SEM fallback para credenciais do Autorize (bloqueou a conta)
                        if user_conv.login_fat and user_conv.senha_fat_criptografada:
                            self.username = user_conv.login_fat
                            self.password = decrypt_password(user_conv.senha_fat_criptografada)
                            self.cod_prestador = user_conv.cod_prestador
                            self.log(f"Credenciais fature carregadas de user_convenios (user_id={self.user_id}, login_fat={self.username})")
                            return True
                        self.log(
                            f"CREDENCIAIS FATURE AUSENTES (login_fat/senha_fat_criptografada vazios em user_convenios "
                            f"user_id={self.user_id}). Configure no frontend (campo Senha (Fat)).",
                            level="ERROR",
                        )
                        return False
                    if user_conv.login and user_conv.senha_criptografada:
                        self.username = user_conv.login
                        self.password = decrypt_password(user_conv.senha_criptografada)
                        self.cod_prestador = user_conv.cod_prestador
                        self.log(f"Credenciais autorize carregadas de user_convenios (user_id={self.user_id}, prestador={self.cod_prestador})")
                        return True
                self.log(
                    f"Registro user_convenios incompleto para user_id={self.user_id} e convenio={self.id_convenio}. "
                    f"Login={getattr(user_conv, 'login', 'N/A') if user_conv else 'NOT FOUND'}",
                    level="INFO"
                )
            else:
                self.log("user_id nao fornecido ao scraper — nao foi possivel carregar credenciais", level="INFO")
            self.log(
                f"Credenciais nao encontradas em user_convenios para user_id={self.user_id} e convenio={self.id_convenio}",
                level="INFO"
            )
        except Exception as e:
            self.log(f"Bradesco Credential Load Error: {e}", level="ERROR")
        return False

    def reload_credentials(self, user_id, job_data=None, contexto="autorize"):
        self.user_id = user_id
        self.username = None
        self.password = None
        self.cod_prestador = None
        self._load_credentials(job_data, contexto)

    def start_driver(self):
        pass  # Managed by SeleniumManager

    def close_driver(self):
        pass  # Managed by SeleniumManager

    def _reciclar_driver(self, job_id=None):
        """Escada de recuperação de sessão (plano MFA/cascata, FASE C): a sessão
        persistiu expirada mesmo após re-login no mesmo driver → recicla o Chrome
        com quit() SEM logoff (nunca clicamos em 'sair'). O próximo attempt pega
        um driver novo pelo pool (get_driver detecta o driver morto na chave)."""
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
        print(f"[{level}] [BRADESCO] {job_prefix}{message}")
        # Persist to database logs table for frontend visibility
        try:
            if self.db:
                from models import Log as LogModel
                log_entry = LogModel(
                    job_id=job_id,
                    carteirinha_id=carteirinha_id,
                    user_id=self.user_id,
                    level=level,
                    message=f"[BRADESCO] {message}"
                )
                self.db.add(log_entry)
                self.db.commit()
        except Exception as e:
            # Never let a logging failure break the scraper flow
            print(f"[WARN] [BRADESCO] Failed to persist log to DB: {e}")
            try:
                self.db.rollback()
            except Exception:
                pass

    def login(self, job_data=None):
        """Executes OP0 login routine."""
        if job_data is None:
            job_data = {}
        return self.execute_op("op0_login", job_data)

    def execute_op(self, op_name, job_data):
        """Generic OP loader and executor."""
        contexto = job_data.get("contexto", "autorize")
        if contexto not in ["autorize", "fature"]:
            contexto = "autorize"
            
        op_file = f"{op_name}.py"
        op_path = os.path.join(self.module_path, f"op_{contexto}", op_file)

        if not os.path.exists(op_path):
            raise FileNotFoundError(f"Operação {op_name} não encontrada em {op_path}")

        # Cross-talk entre integradores: job anterior de OUTRO convênio no mesmo
        # processo deixa 'config' (e módulos dele) cacheado em sys.modules — o
        # import da OP resolveria o pacote errado (ex.: config do 102-caesan
        # servindo o 6-ipasgo → ImportError em X_LOGIN_USERNAME). Purga módulos
        # de QUALQUER Worker/<id>-* antes de carregar a OP (a OP é recarregada
        # do disco; módulos da raiz do Worker ficam de fora).
        # Lock global (incidente 26219-26224): purge + exec_module são região
        # crítica — sem o lock, dois convênios carregando OPs concorrentemente
        # fazem 'core'/'config' resolverem para o pacote errado (sys.path[0]
        # do outro) → ModuleNotFoundError: core.exceptions.
        with op_load_lock:
            for _key in list(sys.modules):
                _mod = sys.modules.get(_key)
                _f = getattr(_mod, "__file__", None)
                if not _f:
                    continue
                _parts = os.path.abspath(_f).lower().split(os.sep)
                try:
                    _i = next(i for i, p in enumerate(_parts)
                              if p == "worker" and i + 1 < len(_parts) and _parts[i + 1][0].isdigit())
                except StopIteration:
                    continue
                del sys.modules[_key]

            spec = importlib.util.spec_from_file_location(op_name, op_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        func = getattr(module, "run", None) or getattr(module, "execute", None)
        if not func:
            raise AttributeError(f"Módulo {op_name} não possui função 'run' ou 'execute'")

        return func(self, job_data)

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

        # Merge params (supports both JSONB dict and legacy text string)
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

        # Contexto PRIMEIRO (define qual par de credenciais usar e qual OP map)
        contexto = job_data.get("contexto", "autorize")

        # Credenciais SEGREGADAS por contexto, a partir dos PARAMS do job
        # (params-first; user_convenios só como último recurso). Antes disto o
        # login do Faturi recebia a senha do AUTORIZE → "Usuário e/ou senha
        # inválidos" → retries → conta bloqueada (incidente 26219+).
        if not self._load_credentials(job_data, contexto):
            fat_msg = (
                "FATURA_SEM_CREDENCIAIS: login_fat/senha_fat_criptografada ausentes nos params do job "
                "e em user_convenios — configure no frontend (campo Senha (Fat)). Sem tentativa de login."
                if contexto == "fature"
                else "AUTORIZE_SEM_CREDENCIAIS: login/senha_criptografada ausentes — configure no frontend."
            )
            self.log(fat_msg, level="ERROR", job_id=job_id)
            raise ValueError(fat_msg)
        self.log(f"Credenciais {contexto} ativas (login={self.username})", job_id=job_id)

        # cod_prestador do JSON SEMPRE prevalece sobre o padrão do banco
        if job_data.get("cod_prestador"):
            self.cod_prestador = job_data.get("cod_prestador")
            self.log(f"cod_prestador sobrescrito pelo JSON do Job: {self.cod_prestador}", job_id=job_id)

        results = []
        error_msg = None
        error_cat = "scraper_error"
        sessoes_expiradas = 0  # quedas consecutivas de sessão (escada: 2ª → reciclar driver)
        
        # Map routine strings to op names based on context
        if contexto == "fature":
            op_map = {
                "0": "op0_login",
                "1": "op1_consultar_guias",
            }
        else:
            op_map = {
                "0": "op0_login",
                "1": "op1_solicitar_autorizacao",
            }

        op_name = op_map.get(str(rotina))
        if not op_name:
            if str(rotina).startswith("op"):
                op_name = rotina
            else:
                op_name = f"op{rotina}"

        for attempt in range(self.max_retries):
            try:
                # Check session
                # Incidente 26223: URL do pool sem "login" (casca do SPA em
                # portal.orizon.com.br ou about:blank pós-limpeza de cookies)
                # era tratada como sessão válida → op1 rodava sem op0_login e o
                # fetch morria em CORS (HTTP 0 em ~5ms). Só dispensa login se a
                # URL estiver NA ÁREA AUTENTICADA do portal (allowlist positiva).
                need_login = attempt > 0
                if not need_login:
                    try:
                        url = self.driver.current_url if self.driver else "data:,"
                        url_l = url.lower()
                        # Allowlist positiva E CONTEXTO-AWARE: o login do Autorize
                        # (Polimed) é diferente do Fature (Orizon/Keycloak). Um
                        # driver deixado no Autorize NÃO tem sessão válida para
                        # um job do Fature (e vice-versa) — cada contexto só
                        # dispensa login na SUA área autenticada.
                        if contexto == "fature":
                            autenticado = url_l.startswith("https://portal.orizon.com.br/fature/")
                        else:
                            autenticado = url_l.startswith("https://www.polimed.com.br/autorize/")
                        if "login" in url_l or "/acesso-restrito" in url_l:
                            autenticado = False
                        if not autenticado:
                            need_login = True
                        elif self.driver:
                            # Strict check: did the driver previously log in with a different user?
                            driver_login = getattr(self.driver, "last_login", None)
                            if self.username and driver_login and driver_login != self.username:
                                self.log(
                                    f"Driver session belongs to login={driver_login}, but job needs login={self.username}. "
                                    f"Clearing cookies and forcing re-login.", 
                                    job_id=job_id
                                )
                                try:
                                    self.driver.delete_all_cookies()
                                    self.driver.get("about:blank") # Reset to clean page
                                except Exception as cookie_err:
                                    self.log(f"Failed to clear cookies: {cookie_err}", level="WARN", job_id=job_id)
                                need_login = True
                    except Exception:
                        need_login = True

                if need_login:
                    if not self.driver or getattr(self.driver, 'session_id', None) is None:
                        try:
                            from server import sel_manager
                            self.driver = sel_manager.get_driver(self.id_convenio, headless=self.headless, user_id=self.user_id)
                        except Exception as pool_err:
                            self.log(f"Using isolated driver mode: {pool_err}", level="WARN", job_id=job_id)

                    # Incidente 20652: quando a rotina JÁ É o login (op0_login),
                    # self.login() e execute_op() executavam o MESMO op duas vezes
                    # — a 2ª navega de volta ao portal já autenticado e falha.
                    # op0_login é auto-suficiente (detecta sessão ativa/MFA); as
                    # demais rotinas seguem o fluxo login → operação.
                    if op_name != "op0_login":
                        self.login(job_data)

                # Update the active login session on the driver object
                if self.driver:
                    self.driver.last_login = self.username

                # Execute mapped OP
                results = self.execute_op(op_name, job_data)

                execution.status = "success"
                break
            except MfaError as e:
                # Código MFA expira — retry automático é inútil (plano_mfa_bradesco D4)
                error_msg = str(e)
                self.log(f"Attempt {attempt + 1} failed (MFA — sem retry): {error_msg}", level="ERROR", job_id=job_id)
                execution.status = "error"
                break
            except LoginFailedError as e:
                # Portal REJEITOU as credenciais (mensagem da página incluída) —
                # retry com a mesma senha multiplica tentativas erradas e pode
                # BLOQUEAR a conta (incidente: usuário bloqueado). Fatal: o
                # usuário corrige a senha no frontend e os próximos jobs pegam
                # a nova de user_convenios.
                error_msg = str(e)
                self.log(f"Attempt {attempt + 1} failed (LOGIN REJEITADO — sem retry): {error_msg}", level="ERROR", job_id=job_id)
                execution.status = "error"
                break
            except SessionExpiredError as e:
                # Escada de recuperação (FASE C): 1ª queda → re-login no mesmo driver
                # (attempt seguinte já força need_login); 2ª consecutiva → reciclar o
                # Chrome (quit sem logoff) e re-login em estado limpo (com MFA se devido).
                error_msg = str(e)
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
            except Exception as e:
                error_msg = str(e)
                # FATAL POR PREFIXO (imune à purga de sys.modules: factory.py
                # re-executa este módulo por job e execute_op purga core.exceptions
                # — a OP levanta uma classe LoginFailedError DIFERENTE da testada
                # pelo except acima, isinstance falha e o erro caía aqui como
                # genérico → 3 tentativas → conta bloqueada). Prefixo é estável.
                if (error_msg.startswith("LOGIN_REJEITADO:")
                        or error_msg.startswith("FATURA_SEM_CREDENCIAIS")
                        or error_msg.startswith("AUTORIZE_SEM_CREDENCIAIS")
                        or "PermanentError:" in error_msg):
                    self.log(f"Attempt {attempt + 1} failed (LOGIN REJEITADO — sem retry): {error_msg}", level="ERROR", job_id=job_id)
                    execution.status = "error"
                    break
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
            execution.error_category = error_cat

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()

        # Propaga a falha para o server/dispatcher: antes, uma OP com erro que
        # retornava lista vazia era envelopada como {"status": "success", "data": []}
        # pelo server (incidente job 20646 — MFA_TIMEOUT terminou em job success
        # vazio). Com o raise, o server devolve status=error e o dispatcher marca
        # o job (aplicando inclusive a regra fatal de MFA_*).
        if execution.status != "success":
            raise ValueError(error_msg or "Unknown Error")

        return results
