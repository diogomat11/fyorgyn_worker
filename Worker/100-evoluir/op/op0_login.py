import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def run(scraper, job_data):
    driver = scraper.driver
    job_id = job_data.get("job_id")
    
    if not scraper.username or not scraper.password:
        raise ValueError("Credenciais da Evoluir não carregadas!")
        
    scraper.log("Iniciando login no portal Evoluir...", job_id=job_id)
    
    # 1. Acessar tela de login
    login_url = "https://sistemaevoluir.com.br/login"
    driver.get(login_url)
    time.sleep(1.5) # Aguarda redirecionamento se houver
    
    # Se redirecionar para o painel, verifica se temos um token válido
    already_logged_in = "login" not in driver.current_url.lower()
    if already_logged_in:
        try:
            # Espera até 3 segundos para ver se o token está presente no global scope
            WebDriverWait(driver, 3).until(
                lambda d: d.execute_script("return (window.dashboardAuthHeader && window.dashboardAuthHeader.length > 0) || false;")
            )
            scraper.log("Sessão já está ativa no Chrome e token window.dashboardAuthHeader validado.", job_id=job_id)
        except Exception:
            scraper.log("Redirecionado para o painel mas window.dashboardAuthHeader está vazio ou indisponível. Forçando logout para novo login...", job_id=job_id)
            already_logged_in = False
            driver.delete_all_cookies()
            driver.get(login_url)
            time.sleep(1)

    if not already_logged_in:
        # 2. Preencher credenciais
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        email_input.clear()
        email_input.send_keys(scraper.username)
        
        pass_input = driver.find_element(By.ID, "password")
        pass_input.clear()
        pass_input.send_keys(scraper.password)
        
        # 3. Clicar em Entrar (usando seletor CSS robusto para o botão de submit)
        btn_entrar = driver.find_element(By.CSS_SELECTOR, "button.btn-primary")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_entrar)
        time.sleep(0.5)
        btn_entrar.click()
        
        # 4. Aguardar carregamento da página interna
        WebDriverWait(driver, 15).until(
            lambda d: "login" not in d.current_url.lower()
        )
    
    current_url = driver.current_url
    scraper.log(f"Login validado com sucesso! Redirecionado para: {current_url}", job_id=job_id)
    
    # 5. Capturar cookies e passar para a session do Requests com os cabeçalhos padrão
    selenium_cookies = driver.get_cookies()
    scraper.session.cookies.clear()
    xsrf_token_val = None
    for cookie in selenium_cookies:
        scraper.session.cookies.set(cookie['name'], cookie['value'])
        if cookie['name'] == 'XSRF-TOKEN':
            import urllib.parse
            xsrf_token_val = urllib.parse.unquote(cookie['value'])
            
    # Atualizar headers da requests.Session para emular o navegador
    scraper.session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://sistemaevoluir.com.br/painel",
        "Accept": "application/json, text/plain, */*"
    })
    
    if xsrf_token_val:
        scraper.session.headers.update({"X-XSRF-TOKEN": xsrf_token_val})
        
    # 6. Capturar o token CSRF (_token) do HTML para chamadas de PUT/POST da API
    html = driver.page_source
    token_match = re.search(r'name="_token"\s+value="([^"]+)"', html)
    if not token_match:
        token_match = re.search(r'csrf-token"\s+content="([^"]+)"', html)
        
    if token_match:
        scraper.csrf_token = token_match.group(1)
        scraper.log(f"Token CSRF capturado: {scraper.csrf_token[:10]}...", job_id=job_id)
    else:
        scraper.log("AVISO: Token CSRF não encontrado na página! Requisições de gravação podem falhar.", level="WARN", job_id=job_id)
        
    # 7. Aguardar e capturar window.dashboardAuthHeader para chamadas da API
    try:
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return (window.dashboardAuthHeader && window.dashboardAuthHeader.length > 0) || false;")
        )
        auth_token = driver.execute_script("return window.dashboardAuthHeader;")
        scraper.auth_token = auth_token
        scraper.session.headers.update({"Authorization": auth_token})
        scraper.log(f"Token de Autorização (dashboardAuthHeader) capturado: {auth_token[:15]}...", job_id=job_id)
    except Exception as e:
        scraper.log(f"Erro/Timeout ao capturar dashboardAuthHeader: {e}", level="ERROR", job_id=job_id)
        
    return {"status": "success", "message": "Logado na Evoluir e sessão exportada."}
