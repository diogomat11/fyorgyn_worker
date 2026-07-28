import time
import os
import sys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.constants import LOGIN_URL, LOGIN_FIELD_EMAIL, LOGIN_FIELD_PASSWORD, LOGIN_BUTTON_XPATH

def run(scraper, job_data):
    driver = scraper.driver
    job_id = job_data.get("job_id")
    
    if not scraper.username or not scraper.password:
        raise ValueError("Credenciais da ABA_clmf não carregadas!")
        
    scraper.log("Iniciando login no portal ABA_clmf...", job_id=job_id)
    
    driver.get(LOGIN_URL)
    time.sleep(1.5)
    
    # Preencher credenciais
    email_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, LOGIN_FIELD_EMAIL))
    )
    email_input.clear()
    email_input.send_keys(scraper.username)
    
    pass_input = driver.find_element(By.NAME, LOGIN_FIELD_PASSWORD)
    pass_input.clear()
    pass_input.send_keys(scraper.password)
    
    # Botão Entrar
    btn_entrar = driver.find_element(By.XPATH, LOGIN_BUTTON_XPATH)
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_entrar)
    time.sleep(0.5)
    btn_entrar.click()
    
    # Aguardar carregamento
    time.sleep(2)
    current_url = driver.current_url
    scraper.log(f"Login efetuado! Redirecionado para: {current_url}", job_id=job_id)
    
    # Copiar cookies do Selenium para a session Requests
    selenium_cookies = driver.get_cookies()
    scraper.session.cookies.clear()
    for cookie in selenium_cookies:
        scraper.session.cookies.set(cookie['name'], cookie['value'])
        
    return {"status": "success", "message": "Logado no portal ABA_clmf e sessão capturada."}

execute = run
