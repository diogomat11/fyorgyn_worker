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
        
        # Validar se o login foi bem-sucedido
        current_url = scraper.driver.current_url
        if "Login.do" in current_url:
            error_msg = "Credenciais inválidas ou rejeitadas pelo portal."
            for selector in [".alert", "#erro", ".message", "table[style*='color: red']", "table[style*='color:red']"]:
                try:
                    elems = scraper.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elems and elems[0].text.strip():
                        error_msg = elems[0].text.strip()
                        break
                except:
                    pass
            raise Exception(f"Validação de Login Falhou: {error_msg}")

        scraper.log("Login performed successfully", job_id=job_id)
        return [{"status": "success", "message": "Login performed"}]

    except Exception as e:
        scraper.log(f"Login failed: {e}", level="ERROR", job_id=job_id)
        raise e

