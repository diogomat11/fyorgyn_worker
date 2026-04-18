import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def execute(scraper, job_data):
    """
    Executa a autenticação no portal SGURCard Unimed Goiânia.
    """
    job_id = job_data.get("job_id")
    scraper.log("Iniciando OP0 - Login", job_id=job_id)

    if not scraper.driver:
        scraper.start_driver()

    if not scraper.username or not scraper.password:
        raise ValueError("Credentials not loaded. Check convenio DB entry.")

    try:
        scraper.driver.get("https://sgucard.unimedgoiania.coop.br/cmagnet/Login.do")
        
        WebDriverWait(scraper.driver, 20).until(EC.presence_of_element_located((By.ID, "passwordTemp")))
        
        login_elem = scraper.driver.find_element(By.ID, "login")
        passwordTemp = scraper.driver.find_element(By.ID, "passwordTemp")
        Button_DoLogin = scraper.driver.find_element(By.ID, "Button_DoLogin")
        
        login_elem.clear()
        login_elem.send_keys(scraper.username)
        time.sleep(1)
        
        passwordTemp.clear()
        passwordTemp.send_keys(scraper.password)
        
        Button_DoLogin.click()
        time.sleep(4)
        
        scraper.log("Login performed", job_id=job_id)
        return [{"status": "success", "message": "Login performed"}]

    except Exception as e:
        scraper.log(f"Login failed: {e}", level="ERROR", job_id=job_id)
        raise e
