import os
import sys
import importlib.util
from datetime import datetime
import json
import time
import requests

# ── Isolate Environment (Ensure base imports from Worker/ root) ──
_worker_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _worker_root not in sys.path:
    sys.path.insert(0, _worker_root)

from base_scraper import BaseScraper
from models import Convenio, JobExecution, UserConvenio
from security_utils import decrypt_password
from database import SessionLocal

class AbaClmfScraper(BaseScraper):
    def __init__(self, id_convenio=101, db=None, headless=True, user_id=None):
        super().__init__(id_convenio, db, headless, user_id)
        self.db = db if db else SessionLocal()
        self.user_id = user_id
        self.username = None
        self.password = None
        self.cod_prestador = None
        self._load_credentials()
        self.module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Hibrido HTTP Requests
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*"
        })

    def _load_credentials(self):
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
                    self.log(f"Credenciais ABA_clmf carregadas (user_id={self.user_id})")
                    return
            self.log(f"Credenciais ABA_clmf nao encontradas para user_id={self.user_id}", level="ERROR")
        except Exception as e:
            self.log(f"ABA_clmf Credential Load Error: {e}", level="ERROR")

    def reload_credentials(self, user_id):
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
                    message=f"[ABA_clmf] {message}"
                )
                self.db.add(log_entry)
                self.db.commit()
            except Exception:
                try: self.db.rollback()
                except: pass

    def login(self):
        """Executes OP0 login routine via Selenium to capture session cookies."""
        return self.execute_op("op0_login", {"job_id": "internal_login"})

    def execute_op(self, op_name, job_data):
        op_file = f"{op_name}.py"
        op_path = os.path.join(self.module_path, "op", op_file)
        
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

        # Merge params
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

        # Map routines (op0, op1, op2, etc.)
        op_name = rotina if rotina.startswith("op") else f"op{rotina}"

        # Sync cookies from Selenium if driver active
        if self.driver and getattr(self.driver, 'session_id', None) is not None:
            try:
                selenium_cookies = self.driver.get_cookies()
                if selenium_cookies:
                    self.session.cookies.clear()
                    for cookie in selenium_cookies:
                        self.session.cookies.set(cookie['name'], cookie['value'])
                    self.log("Sessão HTTP sincronizada com o Chrome.", job_id=job_id)
            except Exception as e:
                self.log(f"Aviso ao sincronizar cookies: {e}", level="WARN", job_id=job_id)

        for attempt in range(self.max_retries):
            try:
                need_login = attempt > 0 or len(self.session.cookies) == 0
                
                if need_login:
                    driver_alive = False
                    if self.driver and getattr(self.driver, 'session_id', None) is not None:
                        try:
                            self.driver.title
                            driver_alive = True
                        except Exception:
                            pass
                            
                    if not driver_alive:
                        try:
                            from server import sel_manager
                            self.driver = sel_manager.get_driver(self.id_convenio, headless=self.headless, user_id=self.user_id)
                        except Exception as pool_err:
                            self.log(f"Failed to acquire Selenium driver: {pool_err}", level="WARN", job_id=job_id)
                    
                    self.log("Sessao HTTP ausente. Iniciando login via Selenium...")
                    self.login()
                
                # Execute mapped OP
                results = self.execute_op(op_name, job_data)
                execution.status = "success"
                break
            except Exception as e:
                error_msg = str(e)
                self.log(f"Attempt {attempt+1} failed: {error_msg}", level="ERROR", job_id=job_id)
                if attempt < self.max_retries - 1:
                    time.sleep(3)
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
        
        if execution.status == "error":
            raise Exception(f"Job failed internally: {error_msg}")
            
        return results
