import os
import sys
import re
import importlib.util
from datetime import datetime
import json
import time

# ── Isolate Environment (Ensure base imports from Worker/ root) ──
_worker_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _worker_root not in sys.path:
    sys.path.insert(0, _worker_root)

from base_scraper import BaseScraper
from models import Convenio, JobExecution, UserConvenio
from security_utils import decrypt_password
from database import SessionLocal

class IpasgoScraper(BaseScraper):
    def __init__(self, id_convenio=6, db=None, headless=True, user_id=None):
        super().__init__(id_convenio, db, headless, user_id)
        # Use provided DB or create a fresh local session
        self.db = db if db else SessionLocal()
        self.user_id = user_id  # Owner do job atual
        self.username = None
        self.password = None
        self.cod_prestador = None
        self.module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 6-ipasgo root

    def _extract_credentials_from_dict(self, data_dict):
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
        if login_val:
            self.username = str(login_val).strip()

        # Atenção: em params da OP19 "senha" é a senha de 11 dígitos da GUIA,
        # não a senha do portal! Priorizar senha_criptografada / password.
        pwd_raw = merged.get("password")
        if not pwd_raw and merged.get("senha_criptografada"):
            try:
                pwd_raw = decrypt_password(merged.get("senha_criptografada"))
            except Exception:
                pass
        if pwd_raw:
            self.password = str(pwd_raw).strip()

        prest_val = (
            merged.get("cod_prestador") or
            merged.get("codigoPrestador") or
            merged.get("prestador")
        )
        if prest_val:
            self.cod_prestador = str(prest_val).strip()

        return bool(self.username and self.password)

    def _load_credentials(self, job_data=None):
        """
        Busca credenciais via job_data ou na user_convenios (por user_id).
        """
        try:
            if job_data and self._extract_credentials_from_dict(job_data):
                self.log(f"Credenciais carregadas via job_data (user_id={self.user_id}, prestador={self.cod_prestador})")
                return

            if self.user_id and self.db:
                user_conv = self.db.query(UserConvenio).filter(
                    UserConvenio.user_id == self.user_id,
                    UserConvenio.id_convenio == self.id_convenio
                ).first()
                if user_conv and user_conv.login and user_conv.senha_criptografada:
                    self.username = user_conv.login
                    self.password = decrypt_password(user_conv.senha_criptografada)
                    self.cod_prestador = user_conv.cod_prestador
                    self.log(f"Credenciais carregadas de user_convenios (user_id={self.user_id}, prestador={self.cod_prestador})")
                    return
                else:
                    self.log(f"Registro user_convenios encontrado mas incompleto para user_id={self.user_id} e convenio={self.id_convenio}. Login={getattr(user_conv, 'login', 'N/A') if user_conv else 'NOT FOUND'}", level="WARN")
            else:
                self.log(f"user_id nao fornecido ao scraper — nao foi possivel carregar credenciais", level="WARN")
            self.log(f"Credenciais nao encontradas em user_convenios para user_id={self.user_id} e convenio={self.id_convenio}", level="WARN")
        except Exception as e:
            self.log(f"IPASGO Credential Load Error: {e}", level="ERROR")

    def reload_credentials(self, user_id, job_data=None):
        """
        Recarrega credenciais para um user_id diferente.
        """
        self.user_id = user_id
        self.username = None
        self.password = None
        self.cod_prestador = None
        self._load_credentials(job_data)

    def start_driver(self):
        pass # Managed by SeleniumManager
        
    def close_driver(self):
        pass # Managed by SeleniumManager

    def log(self, message, level="INFO", job_id=None, carteirinha_id=None):
        job_prefix = f"[Job {job_id}] " if job_id else ""
        print(f"[{level}] {job_prefix}{message}")
        if self.db:
            try:
                from models import Log as LogModel
                log_entry = LogModel(
                    job_id=job_id,
                    carteirinha_id=carteirinha_id,
                    user_id=self.user_id,
                    level=level,
                    message=f"[IPASGO] {message}"
                )
                self.db.add(log_entry)
                self.db.commit()
            except Exception:
                try: self.db.rollback()
                except: pass

    def login(self):
        """Executes OP0 login routine."""
        # Logs do login carregam o job_id real quando o login roda dentro de um
        # job (retry do process_job) — antes iam para 'internal_login' e sumiam
        # da view de logs do job (incidente 23603: "sumiu após Attempt 1 failed").
        return self.execute_op("op0_login", {"job_id": getattr(self, "_current_job_id", None) or "internal_login"})

    def execute_op(self, op_name, job_data):
        """Generic OP loader and executor."""
        # Módulos core/ ficam cacheados em sys.modules; OPs são recarregadas do
        # disco a cada job. Sem isto, mudanças em core/ exigem restart do worker
        # (incidente job #19062: AttributeError em método novo do WebPlanClient).
        try:
            if self.module_path not in sys.path:
                sys.path.insert(0, self.module_path)
            # Cross-talk sequencial: um job de OUTRO convênio (ex. 1-bradesco)
            # no MESMO processo deixa sys.modules['core'] apontando para o
            # pacote DELE — o import abaixo bateria no pacote errado
            # ("No module named 'core.module_reloader'"). Purga antes.
            for _k in [k for k in list(sys.modules)
                       if k in ("core", "config") or k.startswith("core.") or k.startswith("config.")]:
                del sys.modules[_k]
            from core.module_reloader import reload_stale_modules
            reload_stale_modules(self.module_path, log=lambda m: self.log(m, level="WARN"))
        except Exception as reload_err:
            self.log(f"Hot-reload de módulos core falhou (segue com cache atual): {reload_err}", level="WARN")

        op_file = f"{op_name}.py"
        op_path = os.path.join(self.module_path, "op", op_file)
        
        if not os.path.exists(op_path):
            raise FileNotFoundError(f"Operação {op_name} não encontrada em {op_path}")

        # Cross-talk entre integradores: job anterior de OUTRO convênio no mesmo
        # processo deixa 'config' (e módulos dele) cacheado em sys.modules — o
        # import da OP resolveria o pacote errado (ex.: config do 102-caesan
        # servindo o 6-ipasgo → ImportError em X_LOGIN_USERNAME). Purga módulos
        # de QUALQUER Worker/<id>-* antes de carregar a OP (a OP é recarregada
        # do disco; módulos da raiz do Worker ficam de fora).
        #
        # Incidente 2026-11-11 (jobs CAESAN 23711/23667): pacotes NAMESPACE
        # (sem __init__.py) têm __file__=None e sobreviviam a esta purga — o
        # 'config' namespace envenenado persistia entre jobs e `from config
        # import settings` no op0 do 102-caesan levava o Chrome ao PORTAL
        # ERRADO. A purga agora também examina cada entrada de __path__ de
        # pacotes sem __file__ (config/ de 102-caesan e 6-ipasgo hoje têm
        # __init__.py, mas processos vivos podem ainda carregar o namespace).
        for _key in list(sys.modules):
            _mod = sys.modules.get(_key)
            if _mod is None:
                continue
            _caminhos = []
            if getattr(_mod, "__file__", None):
                _caminhos.append(os.path.abspath(_mod.__file__))
            for _pth in getattr(_mod, "__path__", None) or []:
                try:
                    _caminhos.append(os.path.abspath(_pth))
                except Exception:
                    continue
            if not _caminhos:
                continue
            for _abs in _caminhos:
                _parts = _abs.lower().split(os.sep)
                try:
                    _i = next(i for i, p in enumerate(_parts)
                              if p == "worker" and i + 1 < len(_parts) and _parts[i + 1][0].isdigit())
                except StopIteration:
                    continue
                del sys.modules[_key]
                break

        spec = importlib.util.spec_from_file_location(op_name, op_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Try 'run' or 'execute'
        func = getattr(module, "run", None) or getattr(module, "execute", None)
        if not func:
            raise AttributeError(f"Módulo {op_name} não possui função 'run' ou 'execute'")
            
        return func(self, job_data)

    def process_job(self, rotina, job_data):
        job_id = job_data.get("job_id") or job_data.get("id")
        self._current_job_id = job_id
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

        # Garantir extração de credenciais a partir do job_data/params mesclado (schema isolation)
        self._extract_credentials_from_dict(job_data)
        if not self.username or not self.password:
            self._load_credentials(job_data)

        results = []
        error_msg = None
        error_cat = "scraper_error"

        # Map routine strings to op names
        op_map = {
            "0": "op0_login",
            "1": "op1_autorizar_facplan",
            "2": "op2_open_facplan",
            "3": "op3_import_guias",
            "4": "op4_confirma_guia",
            "5": "op5_impress_guia",
            "6": "op6_check_baixados",
            "7": "op7_fat_facplan",
            "8": "op8_check_facplan",
            "9": "op9_anexos_facplan",
            "10": "op10_recurso_glosa",
            "11": "op11_import_guias_api",
            "12": "op12_impressao_api",
            "13": "op13_criar_lote",
            "14": "op14_cancelar_lote",
            "15": "op15_enviar_justificativa",
            "16": "op16_enviar_recurso_glosa",
            "17": "op17_importar_conferencia",
            "18": "op18_conferir_faturamento",
            "19": "op19_anexar_arquivo_guia",
            "20": "op20_validar_codigo_beneficiario",
            "op20_validar_codigo_beneficiario": "op20_validar_codigo_beneficiario",
            "21": "op21_anexar_recurso_glosa",
            "op21_anexar_recurso_glosa": "op21_anexar_recurso_glosa",
            "13_poll": "op13_poll_lote",
            "Execução": "op4_confirma_guia",
            "execucao": "op4_confirma_guia",
            "execução": "op4_confirma_guia",
            "Captura": "op3_import_guias",
            "captura": "op3_import_guias",
            "Impressão": "op5_impress_guia",
            "impressao": "op5_impress_guia",
            "impressão": "op5_impress_guia",
        }
        
        op_name = op_map.get(str(rotina))
        if not op_name:
            # Fallback for named routines
            if rotina.startswith("op"):
                op_name = rotina
            else:
                op_name = f"op{rotina}"

        # Pre-flight anexos (OP19 e OP21): se o lote já teve >= 3 falhas/abortos sem reprocessamento recente,
        # aborta imediatamente sem abrir/ocupar o Selenium.
        is_op19 = str(rotina) in ("19", "op19_anexar_arquivo_guia")
        is_op21 = str(rotina) in ("21", "op21_anexar_recurso_glosa")
        is_op_anexo = is_op19 or is_op21
        rotinas_anexo = ["19", "op19_anexar_arquivo_guia"] if is_op19 else (["21", "op21_anexar_recurso_glosa"] if is_op21 else [])
        protocolo_op19 = str(job_data.get("protocolo") or job_data.get("capa") or "").strip() if is_op_anexo else ""
        if is_op_anexo and self.db and protocolo_op19:
            try:
                from models import Job as JobModel
                from datetime import timezone
                all_op_anexo = self.db.query(JobModel).filter(
                    JobModel.rotina.in_(rotinas_anexo),
                    JobModel.id_convenio == 6,
                ).all()
                lote_jobs = []
                for j_row in all_op_anexo:
                    p_raw = j_row.params
                    p_d = json.loads(p_raw) if isinstance(p_raw, str) else (p_raw or {})
                    if str(p_d.get("protocolo") or p_d.get("capa") or "").strip() == protocolo_op19:
                        lote_jobs.append(j_row)
                # Conta falhas ou verifica se algum já esgotou 3 tentativas.
                # Jobs abortados em cascata ("não foi tentado") NÃO são evidência
                # de portal bloqueado: são efeito, não causa. Sem esse filtro,
                # reprocessar 1 anexo re-abortava na hora sem nem tocar no portal.
                # Falha soft (401/500) isolada também não aborta — o retry do
                # dispatcher recupera; só bloqueio hard ou exaustão (attempts>=3).
                def _falha_real(j_row):
                    if j_row.status != "error":
                        return False
                    m = (j_row.error_message or "").lower()
                    return not (
                        m.startswith("abortado em cascata")
                        or m.startswith("abortado -")
                        or "não foi tentado" in m
                    )
                def _hard(m):
                    low = (m or "").lower()
                    return bool(re.search(r"\b(403|429)\b", low)) or any(
                        k in low for k in ("bloqueio", "bloqueado", "rate limit", "too many requests", "limite de requisições")
                    )
                erros_lote = [j for j in lote_jobs if _falha_real(j)]
                ja_abortado = any((j.attempts or 0) >= 3 for j in erros_lote) or any(
                    _hard(j.error_message) for j in erros_lote
                )
                if ja_abortado:
                    now_utc = datetime.now(timezone.utc)
                    for j_row in lote_jobs:
                        if j_row.status != "success":
                            j_row.status = "error"
                            j_row.attempts = max(3, j_row.attempts or 0)
                            j_row.locked_by = None
                            if not j_row.error_message or "abortad" not in j_row.error_message.lower():
                                j_row.error_message = "Abortado após 3 tentativas (falha do portal em outro job do lote). Reenvio automático após pausa."
                            j_row.updated_at = now_utc
                    self.db.commit()
                    raise RuntimeError("Abortado após 3 tentativas (falha do portal em outro job do lote). Reenvio automático após pausa.")
            except RuntimeError as pre_abort:
                error_msg = str(pre_abort)
                execution.status = "error"
            except Exception as pre_e:
                try:
                    self.db.rollback()
                except Exception:
                    pass

        for attempt in range(0 if execution.status == "error" else self.max_retries):
            try:
                # Check session
                need_login = attempt > 0
                if not need_login:
                    try:
                        url = self.driver.current_url if self.driver else "data:,"
                        if url.startswith("data:") or "login" in url.lower() or "ipasgo" not in url.lower():
                            need_login = True
                    except:
                        need_login = True

                if need_login:
                    if not self.driver or getattr(self.driver, 'session_id', None) is None:
                        try:
                            from server import sel_manager
                            self.driver = sel_manager.get_driver(self.id_convenio, headless=self.headless, user_id=self.user_id)
                        except Exception as pool_err:
                            self.log(f"Using isolated driver mode: {pool_err}", level="WARN", job_id=job_id)
                            # Logic for starting isolated driver if needed could go here
                    
                    self.login()
                
                # Execute mapped OP
                results = self.execute_op(op_name, job_data)
                
                execution.status = "success"
                break
            except Exception as e:
                error_msg = str(e)
                # Para OP19/OP21 (anexos) ou bloqueio do IPASGO, fail-fast:
                # (\b evita falso positivo com dígitos de guia/senha na mensagem)
                if is_op_anexo or (
                    re.search(r"\b(403|429)\b", error_msg.lower())
                    or any(b in error_msg.lower() for b in ["bloqueio", "bloqueado"])
                ):
                    self.log(f"Fail-fast para OP anexos/bloqueio IPASGO: {error_msg}", level="WARN", job_id=job_id)
                    execution.status = "error"
                    break
                self.log(f"Attempt {attempt+1} failed: {error_msg}", level="ERROR", job_id=job_id)
                if attempt < self.max_retries - 1:
                    time.sleep(5)
                else:
                    self.log(f"Fail-fast para OP anexos/bloqueio IPASGO: {error_msg}", level="WARN", job_id=job_id)
                    execution.status = "error"

        execution.end_time = datetime.now()
        execution.duration_seconds = int((execution.end_time - start_time).total_seconds())
        execution.items_found = len(results) if isinstance(results, list) else 1
        
        if execution.status != "success":
            execution.error_message = error_msg[:1000] if error_msg else "Unknown Error"
            execution.error_category = error_cat
        
        try:
            self.db.commit()
        except: self.db.rollback()
        
        if execution.status == "error":
            if is_op_anexo and self.db:
                try:
                    from models import Job as JobModel
                    from datetime import timezone
                    now_utc = datetime.now(timezone.utc)
                    curr_j = self.db.query(JobModel).filter(JobModel.id == job_id).first()
                    all_op_anexo = self.db.query(JobModel).filter(
                        JobModel.rotina.in_(rotinas_anexo),
                        JobModel.id_convenio == 6,
                    ).all()
                    lote_jobs = []
                    for j_row in all_op_anexo:
                        p_raw = j_row.params
                        p_d = json.loads(p_raw) if isinstance(p_raw, str) else (p_raw or {})
                        if not protocolo_op19 or str(p_d.get("protocolo") or p_d.get("capa") or "").strip() == protocolo_op19:
                            lote_jobs.append(j_row)
                    # Cascata imediata só para hard (403/429/rate-limit). Soft
                    # (401/500/timeout/sessão) espera exaurir as 3 tentativas —
                    # falha transiente isolada não trava a fila (retry recupera).
                    _low = (error_msg or "").lower()
                    is_hard = bool(re.search(r"\b(403|429)\b", _low)) or any(
                        b in _low for b in [
                            "bloqueio", "bloqueado", "rate limit",
                            "too many requests", "limite de requisições",
                        ]
                    )
                    curr_attempts = (curr_j.attempts or 1) if curr_j else 1
                    if is_hard or curr_attempts >= 3:
                        for j_row in lote_jobs:
                            if j_row.status != "success":
                                j_row.status = "error"
                                j_row.attempts = max(3, j_row.attempts or 0)
                                j_row.locked_by = None
                                if j_row.id == job_id:
                                    j_row.error_message = f"Abortado após {j_row.attempts} tentativa(s): {(error_msg or '')[:450]}"
                                elif not j_row.error_message or "abortad" not in j_row.error_message.lower():
                                    j_row.error_message = f"Abortado em cascata — falha do portal no job #{job_id}. Este anexo não foi tentado. Reenvio automático após pausa."
                                j_row.updated_at = now_utc
                        self.db.commit()
                except Exception:
                    try:
                        self.db.rollback()
                    except Exception:
                        pass
            raise Exception(f"Job failed internally: {error_msg}")
            
        return results

