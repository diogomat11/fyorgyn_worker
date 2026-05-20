"""
OP0 - Login no portal Polimed/Orizon (Bradesco)
Autentica o usuário no portal de autorização.
"""
from __future__ import annotations
import time
from typing import TYPE_CHECKING
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import sys

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)]
if sys.path[0] != _mod_root:
    sys.path.insert(0, _mod_root)

from config.constants import (
    LOGIN_FIELD_USERNAME,
    LOGIN_FIELD_PASSWORD_ID,
    LOGIN_BUTTON_XPATH,
    DEFAULT_TIMEOUT,
)
from config.settings import PORTAL_URL
from core.selenium_helpers import (
    aguardar_elemento,
    preencher_input,
    clicar_elemento,
    elemento_existe,
)

if TYPE_CHECKING:
    from base_scraper import BaseScraper


def run(scraper: "BaseScraper", job_data: dict) -> list:
    """
    Executa o login no portal Polimed/Orizon (Bradesco).
    Credenciais carregadas previamente pelo BradescoScraper._load_credentials().
    """
    job_id = job_data.get("job_id")
    usuario = getattr(scraper, "username", None)
    senha = getattr(scraper, "password", None)

    if not usuario or not senha:
        scraper.log("Credenciais Bradesco não encontradas / não configuradas", level="ERROR", job_id=job_id)
        raise ValueError("PermanentError: Credenciais Bradesco ausentes")

    driver = scraper.driver

    # Limpar abas residuais
    scraper.log("Limpando abas residuais...", job_id=job_id)
    try:
        main_h = driver.window_handles[0]
        for h in driver.window_handles[1:]:
            driver.switch_to.window(h)
            driver.close()
        driver.switch_to.window(main_h)
    except Exception as e:
        scraper.log(f"Aviso ao limpar abas: {e}", level="WARN", job_id=job_id)

    # 1. Navegar para o portal
    driver.get(PORTAL_URL)
    scraper.log(f"Acessando portal Bradesco: {PORTAL_URL}", job_id=job_id)

    wait = WebDriverWait(driver, DEFAULT_TIMEOUT)

    # 2. Verificar se já está logado ou se os campos de login estão presentes
    try:
        if not elemento_existe(driver, By.NAME, LOGIN_FIELD_USERNAME, timeout=5):
            scraper.log("Campos de login não encontrados. Verificando se já estamos logados...", job_id=job_id)
            if elemento_existe(driver, By.XPATH, "//*[contains(text(), 'Sair') or contains(text(), 'Desconectar')]", timeout=3):
                scraper.log("Sessão já estava ativa (botão Sair encontrado). Pulando login.", job_id=job_id)
                return []
            else:
                scraper.log("Não estamos logados e a tela de login não apareceu corretamente.", level="WARN", job_id=job_id)
        else:
            # Preencher formulário de login
            user_el = aguardar_elemento(driver, By.NAME, LOGIN_FIELD_USERNAME, DEFAULT_TIMEOUT)
            user_el.clear()
            user_el.send_keys(usuario)

            pass_el = aguardar_elemento(driver, By.ID, LOGIN_FIELD_PASSWORD_ID, DEFAULT_TIMEOUT)
            pass_el.clear()
            pass_el.send_keys(senha)

            clicar_elemento(driver, By.XPATH, LOGIN_BUTTON_XPATH, DEFAULT_TIMEOUT)
            scraper.log("Login submetido com sucesso no portal Bradesco", job_id=job_id)

    except Exception as e:
        scraper.log(f"Falha ao preencher formulário de login: {e}", level="ERROR", job_id=job_id)
        raise

    # 3. Aguardar carregamento pós-login
    time.sleep(3)
    
    # 3.1 Tratamento específico para "Sessão já logada" no Orizon/Polimed
    try:
        # Se aparecer um link para derrubar a sessão anterior (muito comum em portais de saúde)
        derrubar_xpath = "//*[contains(text(), 'derrubar') or contains(text(), 'desconectar') or contains(text(), 'encerrar a outra') or contains(text(), 'Forçar')]"
        if elemento_existe(driver, By.XPATH, derrubar_xpath, timeout=2):
            scraper.log("Detectada mensagem de sessão já logada. Tentando forçar desconexão da anterior...", job_id=job_id)
            clicar_elemento(driver, By.XPATH, derrubar_xpath, timeout=2)
            time.sleep(3)
    except Exception as e:
        pass

    # 4. Validar que não ficou na tela de erro
    try:
        error_indicators = [
            "//div[contains(@class,'alert-danger')]",
            "//*[contains(@class,'error')]",
            "//*[contains(text(),'Usuário ou senha inválidos')]",
        ]
        for xpath in error_indicators:
            if elemento_existe(driver, By.XPATH, xpath, timeout=2):
                error_text = driver.find_element(By.XPATH, xpath).text
                raise ValueError(f"PermanentError: Login falhou — {error_text}")
    except ValueError:
        raise
    except Exception:
        pass  # Sem erro detectado — login OK

    scraper.log("Sessão Bradesco autenticada com sucesso", job_id=job_id)

    # 5. Fechar notificações e popups (Chrome nativo e HTML do site)
    scraper.log("Verificando e fechando possíveis notificações/popups...", job_id=job_id)
    
    # 5.1 Tentar fechar balões nativos do Chrome (como o de senha vazada) enviando ESCAPE
    try:
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys
        # Pressiona ESCAPE duas vezes para garantir que modais de browser percam o foco ou fechem
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(0.5)
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
    except Exception as e:
        scraper.log(f"Aviso ao enviar ESCAPE: {e}", level="WARN", job_id=job_id)

    # 5.2 Loop para fechar modais/banners HTML do site
    try:
        popup_close_selectors = [
            "//button[contains(@class, 'close')]",
            "//span[contains(@class, 'close')]",
            "//a[contains(text(), 'Fechar') or contains(text(), 'fechar')]",
            "//button[contains(text(), 'Fechar') or contains(text(), 'fechar')]",
            "//div[contains(@class, 'modal')]//button[contains(@class, 'btn-close')]",
            "//button[contains(text(), 'OK') or contains(text(), 'Ok')]",
            "//a[contains(text(), 'OK') or contains(text(), 'Ok')]",
        ]
        
        # Tenta fechar até 3 popups sucessivos
        for _ in range(3):
            fechou_algum = False
            for xpath in popup_close_selectors:
                if elemento_existe(driver, By.XPATH, xpath, timeout=1):
                    clicar_elemento(driver, By.XPATH, xpath, timeout=2)
                    scraper.log(f"Popup fechado via seletor: {xpath}", job_id=job_id)
                    time.sleep(1)
                    fechou_algum = True
            
            if not fechou_algum:
                break # Nenhum popup encontrado nesta iteração, sai do loop
                
    except Exception as e:
        scraper.log(f"Aviso ao tentar fechar popups HTML: {e}", level="WARN", job_id=job_id)

    return []
