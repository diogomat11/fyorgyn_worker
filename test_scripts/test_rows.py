import sys
import logging
import json
sys.path.append('Worker')
from database import SessionLocal
from ipasgo_wrapper import IpasgoScraper
from selenium.webdriver.common.by import By
import time

logging.basicConfig(level=logging.DEBUG)

db = SessionLocal()
scraper = IpasgoScraper(db=db, headless=True)  
scraper.start_driver()
scraper.username = '15213080'
scraper.password = 'Brinca2025'

try:
    scraper.login()
    print("Navigating to localizador")
    scraper.driver.get('https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos')
    time.sleep(4)
    from op.op3_import_guias import _wait_page_ready, _wait_spinner_until_gone
    
    # Use explicit clear and send
    scraper.driver.find_element(By.XPATH, '(//input-periodo-data//input)[1]').clear()
    scraper.driver.find_element(By.XPATH, '(//input-periodo-data//input)[1]').send_keys('01/02/2026')
    scraper.driver.find_element(By.XPATH, '(//input-periodo-data//input)[2]').clear()
    scraper.driver.find_element(By.XPATH, '(//input-periodo-data//input)[2]').send_keys('15/02/2026')
    
    scraper.driver.find_element(By.XPATH, '//*[@id="localizar-procedimentos-btn"]').click()
    
    time.sleep(6) # hard wait for grid
    
    script = """
    var arr = [];
    var rows = document.querySelectorAll('#localizarprocedimentos > div:nth-child(2) > div > div.resultado-busca-corpo > div > div.corpo-tabela-resultado-conteudo > div');
    for(var i=0; i<rows.length; i++) {
        var r = rows[i];
        arr.push({
            index: i+1,
            className: r.className,
            innerHTML_length: r.innerHTML.length,
            children_count: r.children.length
        });
    }
    return arr;
    """
    
    print("Executando script JS DOM")
    js_output = scraper.driver.execute_script(script)
    with open("dump6.json", "w", encoding="utf-8") as f:
        json.dump(js_output, f, indent=2)
        print("Salvo dump6.json!")
except Exception as e:
    import traceback
    traceback.print_exc()

scraper.close_driver()
db.close()
