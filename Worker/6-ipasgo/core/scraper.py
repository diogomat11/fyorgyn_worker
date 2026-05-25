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

class IpasgoScraper(BaseScraper):
    def __init__(self, id_convenio=6, db=None, headless=True, user_id=None):
        super().__init__(id_convenio, db, headless, user_id)
        # Use provided DB or create a fresh local session
        self.db = db if db else SessionLocal()
        self.user_id = user_id  # Owner do job atual
        self.username = None
        self.password = None
        self.cod_prestador = None
        self._load_credentials()
        self.module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 6-ipasgo root

    def _load_credentials(self):
        """
        Busca credenciais na user_convenios (por user_id).
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
                    self.log(f"Registro user_convenios encontrado mas incompleto para user_id={self.user_id} e convenio={self.id_convenio}. Login={getattr(user_conv, 'login', 'N/A') if user_conv else 'NOT FOUND'}", level="ERROR")
            else:
                self.log(f"user_id nao fornecido ao scraper — nao foi possivel carregar credenciais", level="ERROR")
            self.log(f"Credenciais nao encontradas em user_convenios para user_id={self.user_id} e convenio={self.id_convenio}", level="ERROR")
        except Exception as e:
            self.log(f"IPASGO Credential Load Error: {e}", level="ERROR")

    def reload_credentials(self, user_id):
        """
        Recarrega credenciais para um user_id diferente.
        Chamado pelo server.py antes de processar cada job para garantir que
        a sessão reutilizada do Chrome use as credenciais corretas do tenant.
        """
        self.user_id = user_id
        self.username = None
        self.password = None
        self.cod_prestador = None
        self._load_credentials()

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
        return self.execute_op("op0_login", {"job_id": "internal_login"})

    def execute_op(self, op_name, job_data):
        """Generic OP loader and executor."""
        op_file = f"{op_name}.py"
        op_path = os.path.join(self.module_path, "op", op_file)
        
        if not os.path.exists(op_path):
            raise FileNotFoundError(f"Operação {op_name} não encontrada em {op_path}")

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
            "13_poll": "op13_poll_lote",
        }
        
        op_name = op_map.get(str(rotina))
        if not op_name:
            # Fallback for named routines
            if rotina.startswith("op"):
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
                        if url.startswith("data:") or "login" in url.lower() or "ipasgo" not in url.lower():
                            need_login = True
                    except:
                        need_login = True

                if need_login:
                    if not self.driver or getattr(self.driver, 'session_id', None) is None:
                        try:
                            from server import sel_manager
                            self.driver = sel_manager.get_driver(self.id_convenio, headless=self.headless)
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
                self.log(f"Attempt {attempt+1} failed: {error_msg}", level="ERROR", job_id=job_id)
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
        except: self.db.rollback()
        
        return results

