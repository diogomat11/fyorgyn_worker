"""
UnimedAnopolisScraper — Scraper principal para Unimed Anapolis (id_convenio=2)
Herda de BaseScraper e implementa login, processamento de jobs e roteamento de rotinas.
"""
import os
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from sqlalchemy.orm import Session

# Ensure Worker root is in path
_worker_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _worker_root not in sys.path:
    sys.path.insert(0, _worker_root)

from base_scraper import BaseScraper
from database import SessionLocal
from models import Log, Convenio, JobExecution
from security_utils import decrypt_password

# Module-local imports
_module_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _module_root not in sys.path:
    sys.path.insert(0, _module_root)

from config.settings import (
    LOGIN_URL, LoginSelectors, 
    LOGIN_TIMEOUT, POST_LOGIN_WAIT
)
from infra.selenium_helpers import (
    wait_for_element, close_alert_if_present, 
    close_popup_window
)


class UnimedAnopolisScraper(BaseScraper):
    """
    Scraper para o portal SGUCard da Unimed Anapolis.
    URL: https://sgucard.unimedanapolis.com.br
    """

    def __init__(self, id_convenio=None, db: Session = None, headless=True):
        super().__init__(id_convenio, db, headless)
        self.db = db

        # Default fallback (will be overridden by DB)
        self.username = None
        self.password = None

        # Load from DB
        if self.id_convenio:
            self._load_credentials()

    def _load_credentials(self):
        """Carrega usuário/senha da tabela convenios (criptografada)."""
        try:
            conv = self.db.query(Convenio).filter(
                Convenio.id_convenio == self.id_convenio
            ).first()
            if conv and conv.usuario and conv.senha_criptografada:
                self.username = conv.usuario
                self.password = decrypt_password(conv.senha_criptografada)
                print(f">>> [Anapolis] Credentials loaded from DB for convenio {self.id_convenio}")
            else:
                print(f">>> [Anapolis] WARNING: No credentials in DB for convenio {self.id_convenio}")
        except Exception as e:
            print(f">>> [Anapolis] Failed to load credentials from DB: {e}")

    # ── Logging ──────────────────────────────────────────────

    def log(self, message, level="INFO", job_id=None, carteirinha_id=None):
        """Registra log no console e no banco de dados."""
        print(f"[{level}] [Anapolis] {message}")
        if self.db:
            try:
                self.db.add(Log(
                    job_id=job_id,
                    carteirinha_id=carteirinha_id,
                    level=level,
                    message=message
                ))
                self.db.commit()
            except Exception as e:
                print(f"Failed to write log to DB: {e}")

    # ── Driver Management ────────────────────────────────────

    def start_driver(self):
        # Prevent ghost memory leaks by closing previous window if it exists
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
            self.driver = None

    # ── Login ────────────────────────────────────────────────

    def login(self):
        """Executa login no SGUCard Unimed Anapolis."""
        if not self.driver:
            self.start_driver()

        if not self.username or not self.password:
            raise ValueError("Credentials not loaded. Check convenio DB entry.")

        try:
            self.driver.get(LOGIN_URL)

            # Wait for password field (indicates page loaded)
            wait_for_element(
                self.driver, By.ID, 
                LoginSelectors.INPUT_PASSWORD, 
                LOGIN_TIMEOUT
            )

            # Fill credentials
            login_elem = self.driver.find_element(By.ID, LoginSelectors.INPUT_LOGIN)
            password_elem = self.driver.find_element(By.ID, LoginSelectors.INPUT_PASSWORD)
            login_btn = self.driver.find_element(By.ID, LoginSelectors.BUTTON_LOGIN)

            login_elem.clear()
            login_elem.send_keys(self.username)
            time.sleep(0.5)
            
            password_elem.clear()
            password_elem.send_keys(self.password)
            
            login_btn.click()
            time.sleep(POST_LOGIN_WAIT)

            # Handle potential alerts/popups after login
            close_alert_if_present(self.driver)
            close_popup_window(self.driver)

            self.log("Login performed")
            return True

        except Exception as e:
            self.log(f"Login failed: {e}", level="ERROR")
            raise

    # ── Job Processing (Roteamento por Rotina) ───────────────

    def process_job(self, rotina, job_data):
        """
        Roteia a execução para a operação correta.
        Rotinas:
            - op0 / login_test: Login e validação de sessão
            - (futuras rotinas serão adicionadas aqui)
        """
        job_id = job_data.get("job_id")
        start_time = datetime.now()

        # Init execution record
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
                self.log(
                    f"Attempt {attempt+1}/{self.max_retries} for routine '{rotina}'",
                    job_id=job_id
                )

                # Re-login on retry
                if attempt > 0:
                    try:
                        if not self.driver or not self.driver.title:
                            self.start_driver()
                            self.login()
                    except:
                        self.start_driver()
                        self.login()

                # ── Ensure Login State Before Any Routine ──
                try:
                    self.driver.find_element(By.ID, "mainMenuItem2")
                except:
                    if not self.driver: self.start_driver()
                    self.login()

                # ── Route by rotina ──
                if not rotina:
                    rotina = "1"
                    
                if rotina in ("0", "op0", "login_test"):
                    from op.op0_login import execute as op0_execute
                    results = op0_execute(self, job_data)
                
                elif rotina in ("1", "consulta_guias"):
                    from op.op1_consulta import execute as op1_execute
                    results = op1_execute(self, job_data)
                    
                elif rotina in ("2", "captura"):
                    from op.op2_captura import execute as op2_execute
                    results = op2_execute(self, job_data)

                else:
                    raise NotImplementedError(
                        f"Rotina '{rotina}' not implemented for Unimed Anapolis"
                    )

                execution.status = "success"
                break  # Success!

            except TimeoutException as te:
                error_msg = str(te)
                error_cat = "timeout"
                self.log(f"Timeout attempt {attempt+1}: {te}", level="WARN", job_id=job_id)
                if attempt < self.max_retries - 1:
                    time.sleep(5)

            except NotImplementedError as nie:
                error_msg = str(nie)
                error_cat = "not_implemented"
                self.log(f"Not implemented: {nie}", level="ERROR", job_id=job_id)
                break  # Don't retry

            except Exception as e:
                error_msg = str(e)
                error_cat = "general_error"
                
                # Check for fatal errors that shouldn't be retried
                if "PermanentError:" in str(e):
                    error_msg = str(e).replace("PermanentError:", "").strip()
                    error_cat = "validation_error"
                    self.log(f"Erro Fatal (sem retentativas): {error_msg}", level="ERROR", job_id=job_id)
                    break
                
                self.log(f"Error attempt {attempt+1}: {e}", level="ERROR", job_id=job_id)
                if attempt < self.max_retries - 1:
                    time.sleep(2)

        # Finalize execution
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
