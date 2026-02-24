from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from base_scraper import BaseScraper
from models import Convenio, JobExecution
from security_utils import decrypt_password
from database import SessionLocal
from datetime import datetime
import time

class IpasgoScraper(BaseScraper):
    def __init__(self, id_convenio=6, db=None, headless=True):
        super().__init__(id_convenio, db, headless)
        self.db = db
        self.username = None
        self.password = None
        self._load_credentials()

    def _load_credentials(self):
        try:
            conv = self.db.query(Convenio).filter(Convenio.id_convenio == self.id_convenio).first()
            if conv and conv.usuario and conv.senha_criptografada:
                self.username = conv.usuario
                self.password = decrypt_password(conv.senha_criptografada)
        except Exception as e:
            print(f">>> IPASGO Credential Load Error: {e}")

    def start_driver(self):
        try:
            self.close_driver()
        except: pass
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window()

    def close_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def login(self):
        # Implementation depends on the IPASGO site
        pass

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
        except: self.db.rollback()

        results = []
        error_msg = None
        error_cat = None

        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    self.close_driver()
                    self.start_driver()
                    self.login()
                
                if rotina == "op3_import_guias":
                    import importlib
                    op3_import_guias = importlib.import_module("6-ipasgo.op.op3_import_guias")
                    # Dummy run call - needs actual valid params
                    results = op3_import_guias.run(self.driver, {}, None, start_date=job_data.get("start_date"), end_date=job_data.get("end_date"))
                else:
                    raise NotImplementedError(f"Rotina {rotina} not implemented for IPASGO")
                
                execution.status = "success"
                break
            except Exception as e:
                error_msg = str(e)
                error_cat = "scraper_error"
                if attempt < self.max_retries - 1:
                    time.sleep(5)
        
        execution.end_time = datetime.now()
        execution.duration_seconds = int((execution.end_time - start_time).total_seconds())
        execution.items_found = len(results) if results else 0
        if execution.status != "success":
            execution.status = "error"
            execution.error_message = error_msg[:1000] if error_msg else "Unknown"
            execution.error_category = error_cat
        
        try:
            self.db.commit()
        except: self.db.rollback()
        
        return results
