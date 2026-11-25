"""
Funções Selenium reutilizáveis para o módulo AMIL (9-amil).
Copia/adapta o padrão do 1-bradesco/core/selenium_helpers.py: encapsula
operações comuns para manter as OPs limpas e DRY.
"""
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def aguardar_elemento(driver, by, value, timeout=20):
    """Aguarda e retorna um elemento visível na página."""
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.visibility_of_element_located((by, value)))


def aguardar_elemento_presente(driver, by, value, timeout=20):
    """Aguarda e retorna um elemento presente no DOM (pode não estar visível)."""
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.presence_of_element_located((by, value)))


def aguardar_clicavel(driver, by, value, timeout=20):
    """Aguarda até o elemento ser clicável e retorna."""
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.element_to_be_clickable((by, value)))


def preencher_input(driver, by, value, texto, clear=True, timeout=20):
    """Localiza um input, limpa (clear antes do sendkeys) e digita o texto.

    O clear é indispensável no SPA da AMIL: inputs Angular mantêm valor
    residual entre tentativas e o send_keys concatenaria a senha.
    """
    el = aguardar_elemento(driver, by, value, timeout)
    if clear:
        el.clear()
    el.send_keys(str(texto))
    return el


def clicar_elemento(driver, by, value, timeout=20, js_fallback=True):
    """Clica em um elemento. Usa JS como fallback se o click normal falhar."""
    el = aguardar_clicavel(driver, by, value, timeout)
    try:
        el.click()
    except Exception:
        if js_fallback:
            driver.execute_script("arguments[0].click();", el)
        else:
            raise
    return el


def elemento_existe(driver, by, value, timeout=3):
    """Verifica se um elemento existe na página (sem lançar exceção)."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return True
    except Exception:
        return False
