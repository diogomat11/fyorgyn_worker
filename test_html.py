import sys
import logging
sys.path.append('Worker')
from database import SessionLocal
from ipasgo_wrapper import IpasgoScraper
from selenium.webdriver.common.by import By
import time

logging.basicConfig(level=logging.DEBUG)

db = SessionLocal()
scraper = IpasgoScraper(db=db, headless=False)  
scraper.start_driver()
scraper.username = '15213080'
scraper.password = 'Brinca2025'

try:
    scraper.login()
    print("Navigating to localizador")
    scraper.driver.get('https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos')
    time.sleep(4)
    from op.op3_import_guias import _wait_page_ready, _wait_spinner_until_gone
    
    scraper.driver.find_element(By.XPATH, '(//input-periodo-data//input)[1]').send_keys('01/02/2026')
    scraper.driver.find_element(By.XPATH, '(//input-periodo-data//input)[2]').send_keys('15/02/2026')
    scraper.driver.find_element(By.XPATH, '//*[@id="localizar-procedimentos-btn"]').click()
    
    time.sleep(10)
    
    table = scraper.driver.find_element(By.XPATH, '//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]')
    with open("table_struct.html", "w", encoding="utf-8") as f:
        f.write(table.get_attribute("innerHTML"))
    
    print("HTML salvo em table_struct.html")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    scraper.close_driver()
    db.close()
