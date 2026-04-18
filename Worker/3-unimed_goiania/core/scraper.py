import os
import sys
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from sqlalchemy.orm import Session
from selenium.common.exceptions import TimeoutException

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
    def __init__(self, id_convenio=None, db: Session = None, headless=True):
        super().__init__(id_convenio, db, headless)
        self.db = db
        
        # Credentials loaded exclusively from DB (convenios table)
        self.username = None
        self.password = None
        
        if self.id_convenio:
             self._load_credentials()

    def _load_credentials(self):
        try:
            conv = self.db.query(Convenio).filter(Convenio.id_convenio == self.id_convenio).first()
            if conv and conv.usuario and conv.senha_criptografada:
                self.username = conv.usuario
                self.password = decrypt_password(conv.senha_criptografada)
                print(f">>> [Goiania] Credentials loaded from DB for convenio {self.id_convenio}")
            else:
                msg = f"[Goiania] ERRO: Credenciais ausentes no banco para convenio {self.id_convenio}"
                print(f">>> {msg}")
                self.log(msg, level="ERROR")
        except Exception as e:
            msg = f"[Goiania] ERRO ao carregar credenciais do banco: {e}"
            print(f">>> {msg}")
            self.log(msg, level="ERROR")

    def log(self, message, level="INFO", job_id=None, carteirinha_id=None):
        print(f"[{level}] {message}")
        if self.db:
            try:
                log_entry = Log(
                    job_id=job_id,
                    carteirinha_id=carteirinha_id,
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

    def login(self):
        from op.op0_login import execute
        execute(self, {"job_id": None})

    def process_job(self, rotina, job_data):
        job_id = job_data.get("job_id")
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

        results = []
        error_msg = None
        error_cat = None
        
        for attempt in range(self.max_retries):
            try:
                self.log(f"Attempt {attempt+1}/{self.max_retries} for routine '{rotina}'", job_id=job_id)
                
                if attempt > 0:
                    try:
                        if not self.driver or not self.driver.title:
                            self.start_driver()
                            self.login()
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

                if rotina in ("0", "op0", "login_test"):
                    from op.op0_login import execute as op0_execute
                    results = op0_execute(self, job_data)
                    
                elif rotina in ("1", "consulta_guias", "default"):
                    from op.op1_consulta import execute as op1_execute
                    try:
                        # Fast validation of session presence
                        self.driver.find_element("id", "conteudo-submenu")
                    except:
                        self.log("Sessão ausente. Invocando OP 0 automaticamente...", level="WARN", job_id=job_id)
                        if not self.driver: self.start_driver()
                        self.login()

                    results = op1_execute(self, job_data)
                    
                elif str(rotina).lower() == "captura":
                    from op.op2_captura import execute as op2_execute
                    results = op2_execute(self, job_data)
                    
                elif str(rotina).lower() in ("execução", "execucao", "3"):
                    from op.op3_execucao import execute as op3_execute
                    results = op3_execute(self, job_data)
                    
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
            
        return results

if __name__ == "__main__":
    pass
