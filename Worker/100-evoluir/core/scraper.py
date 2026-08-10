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

class EvoluirScraper(BaseScraper):
    def __init__(self, id_convenio=100, db=None, headless=True, user_id=None):
        super().__init__(id_convenio, db, headless, user_id)
        self.db = db if db else SessionLocal()
        self.user_id = user_id
        self.username = None
        self.password = None
        self.cod_prestador = None
        self._load_credentials()
        self.module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Híbrido HTTP Requests
        self.session = requests.Session()
        self.csrf_token = None
        self.auth_token = None

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

        pwd_raw = merged.get("password") or merged.get("senha")
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
        try:
            if job_data and self._extract_credentials_from_dict(job_data):
                self.log(f"Credenciais Evoluir carregadas via job_data (user_id={self.user_id})")
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
                    self.log(f"Credenciais Evoluir carregadas de user_convenios (user_id={self.user_id})")
                    return
            self.log(f"Credenciais Evoluir nao encontradas para user_id={self.user_id}", level="WARN")
        except Exception as e:
            self.log(f"Evoluir Credential Load Error: {e}", level="ERROR")

    def reload_credentials(self, user_id, job_data=None):
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
                    message=f"[Evoluir] {message}"
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

        # Garantir extração de credenciais a partir do job_data/params mesclado (schema isolation)
        self._extract_credentials_from_dict(job_data)
        if not self.username or not self.password:
            self._load_credentials(job_data)

        results = []
        error_msg = None
        error_cat = "scraper_error"

        # Map routines (op0, op1, op2, etc.)
        op_name = rotina if rotina.startswith("op") else f"op{rotina}"

        # Try to restore session from existing driver cookies/token
        if self.driver and getattr(self.driver, 'session_id', None) is not None:
            try:
                selenium_cookies = self.driver.get_cookies()
                has_session = any(c['name'] == 'evoluir_session' for c in selenium_cookies)
                if has_session:
                    self.session.cookies.clear()
                    xsrf_val = None
                    for cookie in selenium_cookies:
                        self.session.cookies.set(cookie['name'], cookie['value'])
                        if cookie['name'] == 'XSRF-TOKEN':
                            import urllib.parse
                            xsrf_val = urllib.parse.unquote(cookie['value'])
                    
                    # Atualizar headers para emular perfeitamente o navegador
                    self.session.headers.update({
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Referer": "https://sistemaevoluir.com.br/painel",
                        "Accept": "application/json, text/plain, */*"
                    })
                    if xsrf_val:
                        self.session.headers.update({"X-XSRF-TOKEN": xsrf_val})
                    
                    auth_token = self.driver.execute_script("return window.dashboardAuthHeader || '';")
                    if auth_token:
                        self.auth_token = auth_token
                        self.session.headers.update({"Authorization": auth_token})
                        
                    csrf = self.driver.execute_script("return document.querySelector('input[name=\"_token\"]')?.value || '';")
                    if csrf:
                        self.csrf_token = csrf
                        
                    self.log("Sessão HTTP restaurada com sucesso a partir do Chrome ocioso.", job_id=job_id)
            except Exception as e:
                self.log(f"Aviso ao tentar restaurar sessão do driver: {e}", level="WARN", job_id=job_id)

        for attempt in range(self.max_retries):
            try:
                # Se não houver cookies/token na sessão, força OP0_Login para carregar o contexto
                need_login = attempt > 0 or not self.csrf_token or len(self.session.cookies) == 0
                
                # Double check se o driver Selenium está de fato instanciado e vivo para rodar a OP0
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
                    
                    self.log("Sessão HTTP expirada ou ausente. Iniciando login via Selenium...")
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
        
        if execution.status == "error":
            raise Exception(f"Job failed internally: {error_msg}")
            
        return results
