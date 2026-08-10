import os
import sys
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from sqlalchemy.orm import Session
from selenium.common.exceptions import TimeoutException
try:
    import requests as _requests_lib
except ImportError:
    _requests_lib = None

_worker_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _worker_root not in sys.path:
    sys.path.insert(0, _worker_root)

_module_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _module_root not in sys.path:
    sys.path.insert(0, _module_root)

from models import Log, Convenio, JobExecution
from security_utils import decrypt_password
from base_scraper import BaseScraper

class UnimedScraper(BaseScraper):
    def __init__(self, id_convenio=None, db: Session = None, headless=True, user_id=None):
        super().__init__(id_convenio, db, headless, user_id)
        self.db = db
        self.user_id = user_id
        
        # Credentials loaded exclusively from DB (convenios table)
        self.username = None
        self.password = None
        
        if self.id_convenio:
             self._load_credentials()

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

    def touch_activity(self):
        """Notifica o SeleniumManager de que o driver está ativo no momento."""
        try:
            from server import sel_manager
            sel_manager.touch(self.id_convenio, self.user_id)
        except Exception:
            pass

    def login_http(self):
        """
        Realiza login no SGURCard via requests.Session (sem Selenium).
        Usado pelas OPs que operam 100% via HTTP (ex: OP4).
        Retorna a soup da página pós-login para extração de submenu/dynaHash.
        """
        import re
        import html as html_mod
        from bs4 import BeautifulSoup

        if _requests_lib is None:
            raise ImportError("[UnimedGoiania] 'requests' não instalado no ambiente.")

        if not hasattr(self, 'session') or self.session is None:
            self.session = _requests_lib.Session()

        HEADERS = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }
        self.session.headers.update(HEADERS)

        BASE = "https://sgucard.unimedgoiania.coop.br/cmagnet"
        r = self.session.get(f"{BASE}/Login.do", timeout=30)
        r.encoding = "iso-8859-1"
        soup = BeautifulSoup(r.text, "html.parser")

        form = soup.find("form", action=re.compile(r"Login\.do"))
        if not form:
            raise Exception("[UnimedGoiania HTTP] Form de login não encontrado.")

        m = re.search(r'[?&]dynaHash=([a-f0-9]{32})', form.get("action", ""))
        if not m:
            raise Exception("[UnimedGoiania HTTP] dynaHash não encontrado no form de login.")
        dyna = m.group(1)

        payload = {
            "ccsForm": "Login",
            "LOGIN": self.username,
            "SENHA": self.password,
            "dynaHash": dyna,
        }
        r2 = self.session.post(
            f"{BASE}/Login.do?ccsForm=Login&dynaHash={dyna}",
            data=payload, timeout=30
        )
        r2.encoding = "iso-8859-1"

        if "Sair" not in r2.text and "logout" not in r2.text.lower():
            raise Exception(
                "[UnimedGoiania HTTP] Login falhou — credenciais inválidas ou captcha ativo."
            )
        return BeautifulSoup(r2.text, "html.parser")

    def _load_credentials(self, job_data=None):
        try:
            if job_data and self._extract_credentials_from_dict(job_data):
                print(f">>> [Goiania] Credentials loaded from job_data for user {self.user_id}")
                return

            if self.user_id and self.db:
                from models import UserConvenio
                uconv = self.db.query(UserConvenio).filter(
                    UserConvenio.user_id == self.user_id,
                    UserConvenio.id_convenio == self.id_convenio
                ).first()
                if uconv:
                    self.username = uconv.login
                    if uconv.senha_criptografada:
                        self.password = decrypt_password(uconv.senha_criptografada)
                    print(f">>> [Goiania] Credentials loaded from UserConvenio for user {self.user_id}")
                    return
            print(f">>> [Goiania] Credentials will be loaded from Job params.")
        except Exception as e:
            msg = f"[Goiania] ERRO ao carregar credenciais do banco: {e}"
            print(f">>> {msg}")

    def reload_credentials(self, user_id, job_data=None):
        self.user_id = user_id
        self.username = None
        self.password = None
        self.cod_prestador = None
        self._load_credentials(job_data)

    def log(self, message, level="INFO", job_id=None, carteirinha_id=None):
        print(f"[{level}] {message}")
        if self.db:
            try:
                log_entry = Log(
                    job_id=job_id,
                    carteirinha_id=carteirinha_id,
                    user_id=self.user_id,
                    level=level,
                    message=message
                )
                self.db.add(log_entry)
                self.db.commit()
            except Exception:
                pass

    def start_driver(self):
        try:
            self.close_driver()
        except: pass
        
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-gpu")
        if self.headless:
            chrome_options.add_argument("--headless")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window()

    def close_driver(self):
        if self.driver:
            self.driver.quit()

    def _isolate_env(self):
        import sys, os
        _mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path = [p for p in sys.path if not ("Worker" in p and p != _mod_root and any(c.isdigit() for c in os.path.basename(p)))]
        if not sys.path or sys.path[0] != _mod_root:
            sys.path.insert(0, _mod_root)
        for k in list(sys.modules.keys()):
            if k.startswith("op.") or k == "op":
                del sys.modules[k]

    def login(self):
        self._isolate_env()
        from op.op0_login import execute
        execute(self, {"job_id": None})

    def process_job(self, rotina, job_data):
        self._isolate_env()
        job_id = job_data.get("job_id") or job_data.get("id")
        start_time = datetime.now()
        
        execution = JobExecution(
            job_id=job_id,
            id_convenio=self.id_convenio,
            rotina=rotina,
            status="processing",
            start_time=start_time
        )
        self.db.add(execution)
        try:
            self.db.commit()
        except: 
            self.db.rollback()

        # Merge params (supports both JSONB dict and legacy text string)
        import json
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

        # Inject injected credentials
        injected_login = job_data.get("login")
        if injected_login:
            self.username = injected_login
            if job_data.get("senha_criptografada"):
                from security_utils import decrypt_password
                try:
                    self.password = decrypt_password(job_data.get("senha_criptografada"))
                except Exception:
                    self.password = job_data.get("senha_criptografada")
            self.log(f"Credenciais Goiania aplicadas a partir dos parametros do Job (login={self.username})", job_id=job_id)

        if not self.username or not self.password:
            self._load_credentials()

        results = []
        error_msg = None
        error_cat = None
        
        for attempt in range(self.max_retries):
            try:
                self.log(f"Attempt {attempt+1}/{self.max_retries} for routine '{rotina}'", job_id=job_id)
                
                # On first attempt: ensure session active. On retries: always force login.
                if attempt == 0:
                    session_active = False
                    try:
                        if len(self.driver.window_handles) > 0 and 'sgucard' in self.driver.current_url.lower() and 'login' not in self.driver.current_url.lower():
                            session_active = True
                            self.log("Session already active. Skipping login.", job_id=job_id)
                    except:
                        pass
                    if not session_active:
                        self.login()
                else:
                    if not self.driver:
                        self.start_driver()
                    try:
                        self.driver.title
                    except:
                        self.start_driver()
                    self.login()

                if not rotina: rotina = "1"

                # ── Isolate Environment (Fix Crosstalk) ──
                import sys, os
                _mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)]
                if sys.path[0] != _mod_root:
                    sys.path.insert(0, _mod_root)
                
                for k in list(sys.modules.keys()):
                    if k.startswith("op.") or k == "op":
                        del sys.modules[k]

                if str(rotina).lower() in ("0", "op0", "login_test", "op0_login"):
                    from op.op0_login import execute as op0_execute
                    results = op0_execute(self, job_data)
                    
                elif str(rotina).lower() in ("1", "consulta_guias", "default", "op1_consulta", "op1_consultar_guias"):
                    from op.op1_consulta import execute as op1_execute
                    results = op1_execute(self, job_data)

                    
                elif str(rotina).lower() in ("captura", "op2_captura", "2", "op2_autorizar", "autorizar"):
                    from op.op2_captura import execute as op2_execute
                    results = op2_execute(self, job_data)
                    
                elif str(rotina).lower() in ("execução", "execucao", "3", "op3_execucao"):
                    from op.op3_execucao import execute as op3_execute
                    results = op3_execute(self, job_data)

                elif str(rotina).lower() in ("4", "op4_finalizados", "finalizados", "exames_finalizados"):
                    # OP4 opera 100% via HTTP (requests.Session), sem Selenium.
                    from op.op4_finalizados import execute as op4_execute
                    results = op4_execute(self, job_data)

                else:
                    raise NotImplementedError(f"Rotina '{rotina}' not implementada para Unimed Goiania")
                
                execution.status = "success"
                break 
                
            except TimeoutException as te:
                error_msg = str(te)
                error_cat = "timeout"
                self.log(f"Timeout on attempt {attempt+1}: {te}", level="WARN", job_id=job_id)
                if attempt < self.max_retries - 1:
                    time.sleep(5)
            except Exception as e:
                error_msg = str(e)
                error_cat = "general_error"
                self.log(f"Critical error on attempt {attempt+1}: {e}", level="ERROR", job_id=job_id)
                if "NotImplementedError" in str(e): break
                if attempt < self.max_retries - 1:
                    time.sleep(2)
        
        execution.end_time = datetime.now()
        execution.duration_seconds = int((execution.end_time - start_time).total_seconds())
        execution.items_found = len(results) if results else 0
        if execution.status != "success":
            execution.status = "error"
            execution.error_message = error_msg[:1000] if error_msg else "Unknown failure"
            execution.error_category = error_cat
            
        try:
            self.db.commit()
        except:
            self.db.rollback()
            
        if execution.status == "error":
            raise Exception(f"Job failed internally: {error_msg}")
            
        return results

if __name__ == "__main__":
    pass
