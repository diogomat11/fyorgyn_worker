"""
Funções Selenium reutilizáveis para o módulo Bradesco.
Encapsula operações comuns para manter as OPs limpas e DRY.
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
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
    """Localiza um input, limpa (opcional) e digita o texto."""
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


def selecionar_option_por_texto(driver, select_id, texto, timeout=20):
    """
    Seleciona uma opção de um <select> pelo texto visível.
    Não utiliza índice fixo — varre as opções e localiza pelo valor.
    """
    el = aguardar_elemento(driver, By.ID, select_id, timeout)
    select = Select(el)
    select.select_by_visible_text(texto)
    return el


def selecionar_option_por_valor(driver, select_id, valor, timeout=20):
    """Seleciona uma opção de um <select> pelo atributo value."""
    el = aguardar_elemento(driver, By.ID, select_id, timeout)
    select = Select(el)
    select.select_by_value(str(valor))
    return el


def selecionar_option_contendo_texto(driver, select_id, texto_parcial, timeout=20):
    """
    Seleciona a primeira opção cujo texto contenha o texto_parcial (case-insensitive).
    Útil para combos onde o texto exato pode variar.
    """
    el = aguardar_elemento(driver, By.ID, select_id, timeout)
    select = Select(el)
    texto_lower = texto_parcial.lower()
    for option in select.options:
        if texto_lower in option.text.lower():
            select.select_by_visible_text(option.text)
            return el
    raise ValueError(f"Nenhuma opção contendo '{texto_parcial}' encontrada no select '{select_id}'")


def scroll_to_element(driver, element):
    """Faz scroll até o elemento ficar centralizado na viewport."""
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior:'instant', block:'center'});",
            element
        )
    except Exception:
        pass


def switch_to_next_window(driver, timeout=10):
    """
    Troca para a próxima janela/aba disponível.
    Aguarda até que haja mais de uma handle.
    """
    current = driver.current_window_handle
    WebDriverWait(driver, timeout).until(lambda d: len(d.window_handles) > 1)
    for handle in driver.window_handles:
        if handle != current:
            driver.switch_to.window(handle)
            return handle
    raise Exception("Nenhuma nova janela encontrada")


def switch_to_previous_window(driver):
    """Retorna para a primeira janela (handle principal)."""
    handles = driver.window_handles
    if handles:
        driver.switch_to.window(handles[0])


def capturar_texto(driver, by, value, timeout=20):
    """Captura o texto de um elemento."""
    el = aguardar_elemento_presente(driver, by, value, timeout)
    return el.text.strip()


def elemento_existe(driver, by, value, timeout=3):
    """Verifica se um elemento existe na página (sem lançar exceção)."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return True
    except Exception:
        return False


def fechar_janela_atual(driver):
    """Fecha a janela/aba atual e volta para a anterior."""
    driver.close()
    handles = driver.window_handles
    if handles:
        driver.switch_to.window(handles[-1])
