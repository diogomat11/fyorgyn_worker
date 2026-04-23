import re

with open('Local_worker/Worker/6-ipasgo/op/op11_import_guias_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the specific block of code for Bootstrap logic
old_block = """    # 1. Navegação de Bootstrap (Garante que os cookies do módulo GuiasTISS sejam inicializados)
    url_bootstrap = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos"
    scraper.log(f"OP11 - Acessando URL Bootstrap para setup de contexto: {url_bootstrap}", job_id=job_id)
    driver.get(url_bootstrap)
    time.sleep(3) # Wait for redirects / cookies
    
    # 2. Inicialização do Client"""

new_block = """    # 1. Navegação de Bootstrap (Garante que os cookies do módulo GuiasTISS sejam inicializados)
    url_bootstrap = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos"
    scraper.log(f"OP11 - Acessando URL Bootstrap para setup de contexto: {url_bootstrap}", job_id=job_id)
    driver.get(url_bootstrap)
    time.sleep(3) # Wait for redirects / cookies
    
    # 1.1 Avaliar se é exibido notificação e fechar via selenium assim como no OP3
    scraper.log("Procurando notificação (button-1)...", job_id=job_id)
    for _ in range(3):
        try:
            btn_close = wait_xpath(driver, '//*[@id="button-1"]', 1)
            if btn_close and btn_close.is_displayed():
                scraper.log("Notificação encontrada! Clicando para fechar...", job_id=job_id)
                driver.execute_script("arguments[0].click();", btn_close)
                time.sleep(1)
                break
        except:
            pass
        time.sleep(1)
        
    _close_alert_if_present(driver)
    
    # 2. Inicialização do Client"""

# Ensure character matches (due to some charset issues where ção might be represented differently)
# We will just regex it.
import sys

# Replace import section
imports_str = """import os
import sys
import logging
import time
from sqlalchemy.dialects.postgresql import insert
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime"""

content = re.sub(r'import os\nimport sys\nimport logging\nimport time\nfrom sqlalchemy\.dialects\.postgresql import insert', imports_str, content)

funcs_str = """def wait_xpath(driver, xpath, timeout=5):
    try:
        wait = WebDriverWait(driver, timeout)
        return wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
    except Exception:
        return None

def _close_alert_if_present(driver):
    try:
        candidates = ['/html/body/div[5]/div/div/div[2]/button', 'button-1']
        for c in candidates:
            try:
                btn = driver.find_element(By.XPATH, c) if '/' in c else driver.find_element(By.ID, c)
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1)
                    break
            except: 
                if c == 'button-1':
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    for i in range(len(iframes)):
                        try:
                            driver.switch_to.frame(i)
                            btn = driver.find_element(By.ID, "button-1")
                            if btn.is_displayed():
                                driver.execute_script("arguments[0].click();", btn)
                                time.sleep(1)
                                break
                        except: pass
                        finally: driver.switch_to.default_content()
    except: pass

def _save_rows_local(rows, logger):
    try:
        from database import SessionLocal
        from models import BaseGuia, Carteirinha
        db_session = SessionLocal()
        try:
            for row_data in rows:
                if not row_data.get("numero_guia"):
                    continue
                guia_record = db_session.query(BaseGuia).filter(
                    BaseGuia.guia == str(row_data["numero_guia"])
                ).first()
                if not guia_record:
                    guia_record = BaseGuia(guia=str(row_data["numero_guia"]))
                    db_session.add(guia_record)
                
                guia_record.status_guia = row_data.get("situacao")
                if row_data.get("codigo_amb"):
                    guia_record.codigo_terapia = str(row_data["codigo_amb"])
                
                guia_record.id_convenio = 6 # IPASGO
                if row_data.get("codigo_beneficiario"):
                    guia_record.codigo_beneficiario = row_data["codigo_beneficiario"]
                    cart = db_session.query(Carteirinha).filter(Carteirinha.codigo_beneficiario == row_data["codigo_beneficiario"]).first()
                    if cart:
                        guia_record.carteirinha_id = cart.id

            db_session.commit()
            if logger:
                logger.info(f"Salvos {len(rows)} registros em base_guias locais (Worker DB)")
        finally:
            db_session.close()
    except Exception as db_err:
        if logger:
            logger.error(f"Erro ao salvar base_guias locais: {db_err}")

def run(scraper, job_data):"""

content = content.replace("def run(scraper, job_data):", funcs_str)


# The navigate replace
pattern_nav = r"(# 1\. Navega.+?)(# 2\. Inicializa.+?)"
def nav_replacer(m):
    return m.group(1) + """
    # 1.1 Avaliar se é exibido notificação e fechar via selenium assim como no OP3
    scraper.log("Procurando notificação (button-1)...", job_id=job_id)
    for _ in range(3):
        try:
            btn_close = wait_xpath(driver, '//*[@id="button-1"]', 1)
            if btn_close and btn_close.is_displayed():
                scraper.log("Notificação encontrada! Clicando para fechar...", job_id=job_id)
                driver.execute_script("arguments[0].click();", btn_close)
                time.sleep(1)
                break
        except:
            pass
        time.sleep(1)
        
    _close_alert_if_present(driver)
    
    """ + m.group(2)

content = re.sub(r'(# 1\. Navega[\s\S]*?)(# 2\. Inicializa[\s\S]*?client = WebPlanClient\(driver\))', nav_replacer, content)


db_pattern = r"# 4\. TODO: Implementa[\s\S]*?# scraper\.db\.commit\(\)"
db_replacer = """# 4. Implementação de banco de dados (Upsert bulk)
    _save_rows_local(todas_guias_extraidas, scraper.logger if hasattr(scraper, 'logger') else logging.getLogger())"""
content = re.sub(db_pattern, db_replacer, content)


with open('Local_worker/Worker/6-ipasgo/op/op11_import_guias_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
