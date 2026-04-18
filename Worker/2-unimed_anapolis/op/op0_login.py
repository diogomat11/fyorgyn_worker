"""
Op 0 — Login Test
Rotina de teste: faz login no SGUCard e valida que a sessão está ativa.
Retorna lista com status do login.
"""
import time
from selenium.webdriver.common.by import By

import os, sys
_worker_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _worker_root not in sys.path:
    sys.path.insert(0, _worker_root)

_module_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _module_root not in sys.path:
    sys.path.insert(0, _module_root)

from infra.selenium_helpers import (
    is_element_present, close_popup_window, close_alert_if_present
)
from config.settings import NavSelectors


def execute(scraper, job_data):
    """
    Executa login e valida sessão.
    
    Args:
        scraper: UnimedAnopolisScraper instance (com driver injetado)
        job_data: dict com job_id, carteirinha, etc.
    
    Returns:
        list com resultado do teste de login
    """
    job_id = job_data.get("job_id")
    
    # 1. Fazer login
    scraper.log("Op0: Starting login test...", job_id=job_id)
    scraper.login()
    
    # 2. Validar sessão — procurar elementos do menu principal
    time.sleep(2)
    
    # Fechar popups que possam ter aparecido
    close_alert_if_present(scraper.driver)
    close_popup_window(scraper.driver)
    
    # 3. Verificar se estamos na página principal (pós-login)
    session_valid = False
    validation_detail = ""
    
    try:
        # Tenta encontrar o menu principal (centro_61 img) — indica login OK
        if is_element_present(scraper.driver, By.CSS_SELECTOR, NavSelectors.MENU_CENTRO_61):
            session_valid = True
            validation_detail = "Menu principal encontrado"
        elif is_element_present(scraper.driver, By.ID, NavSelectors.MENU_ITEM_2):
            session_valid = True
            validation_detail = "MenuItem2 encontrado"
        else:
            # Fallback: checar se não estamos mais na página de login
            current_url = scraper.driver.current_url
            if "Login.do" not in current_url:
                session_valid = True
                validation_detail = f"Redirecionado para: {current_url}"
            else:
                validation_detail = "Ainda na página de login"
    except Exception as e:
        validation_detail = f"Erro na validação: {e}"

    # 4. Log resultado
    if session_valid:
        scraper.log(f"Op0: Login OK — {validation_detail}", job_id=job_id)
    else:
        scraper.log(f"Op0: Login FALHOU — {validation_detail}", level="ERROR", job_id=job_id)
        raise Exception(f"Login validation failed: {validation_detail}")

    return [{
        "op": "op0_login",
        "status": "success" if session_valid else "error",
        "detail": validation_detail,
        "url": scraper.driver.current_url
    }]
