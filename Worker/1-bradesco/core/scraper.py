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

from base_scraper import BaseScraper
from models import Convenio, JobExecution, UserConvenio
from security_utils import decrypt_password
from database import SessionLocal


class BradescoScraper(BaseScraper):
    """
    Scraper para o convênio Bradesco (id_convenio=1).
    Portal de autorização: Polimed/Orizon.
    """

    def __init__(self, id_convenio=1, db=None, headless=True, user_id=None):
        super().__init__(id_convenio, db, headless)
        self.db = db if db else SessionLocal()
        self.user_id = user_id
        self.username = None
        self.password = None
        self.cod_prestador = None
        self._load_credentials()
        self.module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 1-bradesco root

    def _load_credentials(self):
        """
        Busca credenciais na user_convenios (por user_id + id_convenio).
        """
        try:
            if self.user_id:
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
                    self.log(
                        f"Registro user_convenios incompleto para user_id={self.user_id} e convenio={self.id_convenio}. "
                        f"Login={getattr(user_conv, 'login', 'N/A') if user_conv else 'NOT FOUND'}",
                        level="ERROR"
                    )
            else:
                self.log("user_id nao fornecido ao scraper — nao foi possivel carregar credenciais", level="ERROR")
            self.log(
                f"Credenciais nao encontradas em user_convenios para user_id={self.user_id} e convenio={self.id_convenio}",
                level="ERROR"
            )
        except Exception as e:
            self.log(f"Bradesco Credential Load Error: {e}", level="ERROR")

    def reload_credentials(self, user_id):
        """
        Recarrega credenciais para um user_id diferente.
        Chamado pelo server.py antes de processar cada job para garantir
        isolamento multi-tenant.
        """
        self.user_id = user_id
        self.username = None
        self.password = None
        self.cod_prestador = None
        self._load_credentials()

    def start_driver(self):
        pass  # Managed by SeleniumManager

    def close_driver(self):
        pass  # Managed by SeleniumManager

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

        # Prioritize credentials injected from dispatcher via params
        injected_login = job_data.get("login") or job_data.get("users_convenio_login")
        if injected_login:
            self.username = injected_login
            if job_data.get("senha_criptografada"):
                from security_utils import decrypt_password
                self.password = decrypt_password(job_data.get("senha_criptografada"))
            self.log(f"Credenciais Bradesco aplicadas a partir dos parâmetros do Job (login={self.username})", job_id=job_id)

        # cod_prestador do JSON SEMPRE prevalece sobre o padrão do banco
        if job_data.get("cod_prestador"):
            self.cod_prestador = job_data.get("cod_prestador")
            self.log(f"cod_prestador sobrescrito pelo JSON do Job: {self.cod_prestador}", job_id=job_id)

        results = []
        error_msg = None
        error_cat = "scraper_error"

        contexto = job_data.get("contexto", "autorize")
        
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
                need_login = attempt > 0
                if not need_login:
                    try:
                        url = self.driver.current_url if self.driver else "data:,"
                        if url.startswith("data:") or "login" in url.lower():
                            need_login = True
                    except Exception:
                        need_login = True

                if need_login:
                    if not self.driver or getattr(self.driver, 'session_id', None) is None:
                        try:
                            from server import sel_manager
                            self.driver = sel_manager.get_driver(self.id_convenio, headless=self.headless)
                        except Exception as pool_err:
                            self.log(f"Using isolated driver mode: {pool_err}", level="WARN", job_id=job_id)

                    self.login(job_data)

                # Execute mapped OP
                results = self.execute_op(op_name, job_data)

                execution.status = "success"
                break
            except Exception as e:
                error_msg = str(e)
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

        return results
