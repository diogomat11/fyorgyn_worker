"""
Helpers Selenium reutilizáveis para o módulo Unimed Anapolis.
Waits, popup handling, window management.
"""
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, 
    NoAlertPresentException, UnexpectedAlertPresentException
)


def wait_for_element(driver, by, value, timeout=10):
    """Espera um elemento aparecer e retorna-o."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


def wait_for_clickable(driver, by, value, timeout=10):
    """Espera um elemento ficar clicável e retorna-o."""
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, value))
    )


def close_alert_if_present(driver):
    """Fecha alert JS se estiver presente."""
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        alert.accept()
        print(f">>> Alert fechado: {alert_text}")
        return True
    except NoAlertPresentException:
        return False


def close_popup_window(driver):
    """
    Detecta e fecha janelas popup extras (SGUCard abre popups frequentemente).
    Retorna para a janela principal.
    """
    handles = driver.window_handles
    if len(handles) <= 1:
        return False
    
    main_handle = handles[0]
    closed_count = 0
    
    for handle in handles[1:]:
        try:
            driver.switch_to.window(handle)
            driver.close()
            closed_count += 1
        except Exception:
            pass
    
    driver.switch_to.window(main_handle)
    if closed_count > 0:
        print(f">>> Fechou {closed_count} popup(s)")
    return closed_count > 0


def switch_to_new_window(driver, original_handles, timeout=5):
    """
    Espera uma nova janela abrir e muda para ela.
    Retorna o handle da nova janela ou None.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        current_handles = driver.window_handles
        new_handles = set(current_handles) - set(original_handles)
        if new_handles:
            new_handle = new_handles.pop()
            driver.switch_to.window(new_handle)
            return new_handle
        time.sleep(0.3)
    return None


def is_element_present(driver, by, value):
    """Checa se um elemento existe sem esperar."""
    try:
        driver.find_element(by, value)
        return True
    except NoSuchElementException:
        return False
