"""
Op 5 — Impressão de Guias (IPASGO)

Adaptado de op4 (navegação) e impressaoLote-Ipasgo.py (impressão).
Parâmetros esperados em job_data['params']:
  - numero_guia : str
  - numero_copias : int (padrão 1)
"""
import time
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

import os
import sys

# ── Isolate Environment (Fix Crosstalk) ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from config.settings import get_runtime_settings
from config.constants import DEFAULT_TIMEOUT

# XPaths adaptados do op4
X_LOCALIZAR_BTN_PESQUISAR = '//*[@id="localizar-procedimentos-btn"]'
X_LOCALIZAR_INPUT_GUIA = '//*[@id="localizarprocedimentos"]/div[1]/div[1]/div[2]/div/form/div[1]/div[1]/div[2]/div/input'
X_LOCALIZAR_INPUT_CARTEIRA = '//*[@id="localizarprocedimentos"]/div[1]/div[1]/div[2]/div/form/div[1]/div[1]/div[4]/div[2]/input'

class _LoggerWrapper:
    def __init__(self, scraper, job_id):
        self.scraper = scraper
        self.job_id = job_id
    def info(self, msg): self.scraper.log(msg, level="INFO", job_id=self.job_id)
    def error(self, msg): self.scraper.log(msg, level="ERROR", job_id=self.job_id)
    def warning(self, msg): self.scraper.log(msg, level="WARN", job_id=self.job_id)
    def debug(self, msg): self.scraper.log(msg, level="DEBUG", job_id=self.job_id)

def _wait_spinner_until_gone(driver, max_checks=3, step_seconds=5, logger=None):
    if logger: logger.debug("Aguardando carregamento Angular (Spinner)...")
    for _ in range(max_checks):
        try:
            overlay = driver.find_elements(By.XPATH, "/html/body/div[1]/div/div/div")
            block_ui = driver.find_elements(By.CSS_SELECTOR, ".blockUI.blockOverlay")
            if not overlay and not block_ui:
                break
            if overlay and not overlay[0].is_displayed():
                break
            if block_ui and not block_ui[0].is_displayed():
                break
            time.sleep(step_seconds)
        except Exception:
            break

def _close_alert_if_present(driver):
    try:
        # Tenta fechar modal inicial via ID ou XPath fixo do op4
        candidates = ['/html/body/div[5]/div/div/div[2]/button', 'button-1']
        for c in candidates:
            try:
                btn = driver.find_element(By.XPATH, c) if '/' in c else driver.find_element(By.ID, c)
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1)
                    break
            except: 
                # Se não visível no topo, tenta em iframes (apenas para o alerta)
                if c == 'button-1':
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    for i in range(len(iframes)):
                        try:
                            driver.switch_to.frame(i)
                            btn = driver.find_element(By.ID, "button-1")
                            if btn.is_displayed():
                                driver.execute_script("arguments[0].click();", btn)
                                time.sleep(1)
                                break
                        except: pass
                        finally: driver.switch_to.default_content()
    except: pass

def wait_xpath(driver, xpath, timeout=DEFAULT_TIMEOUT):
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
    except:
        return None

def execute(scraper, job_data):
    job_id = job_data.get("job_id")
    logger = _LoggerWrapper(scraper, job_id)
    driver = scraper.driver

    params_str = job_data.get("params", "")
    p = {}
    if params_str:
        try:
            p = json.loads(params_str) if isinstance(params_str, str) else params_str
        except: pass

    numero_guia = p.get("numero_guia", "") or p.get("guia", "")
    numero_copias = int(p.get("numero_copias") or p.get("copias") or 1)

    if not numero_guia:
        msg = "PermanentError: Guia não informada para impressão."
        logger.error(msg)
        raise ValueError(msg)

    logger.info(f"OP5 Iniciado. Guia: {numero_guia} | Cópias: {numero_copias}")

    # --- ITEM 3: CLICA LINK OPENFACPLAN ---
    logger.info("Localizando e clicando no link FacPlan...")
    menu_xpath = '//*[@id="linkfacplan"]'
    link = wait_xpath(driver, menu_xpath, 10)
    if link:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", link)
        time.sleep(1)
        # Tenta clique padrão primeiro, fallback JS se necessário para o link inicial
        try: link.click()
        except: driver.execute_script("arguments[0].click();", link)
        time.sleep(2)
    else:
        logger.warning("Link FacPlan não localizado. Verificando abas existentes.")

    # --- ITEM 4: FOCA NA NOVA ABA AGUARDA CARREGAR 'BEM VINDO' ---
    logger.info("Item 4 - Aguardando carregamento da aba 'Bem-vindo ao WebPlan'...")
    facplan_handle = None
    for step in range(12): # Aguarda até 12s
        logger.info(f"Item 4 - Verificando abas... (Tentativa {step+1}/12)")
        for h in driver.window_handles:
            driver.switch_to.window(h)
            title = driver.title.lower()
            if "bem-vindo" in title or "webplan" in title:
                facplan_handle = h
                logger.info(f"Item 4 - Aba 'Bem-vindo' focada com sucesso: {driver.title}")
                break
        if facplan_handle: break
        time.sleep(1)
    
    if not facplan_handle:
        logger.warning("Item 4 - Aba 'Bem-vindo' não localizada. Continuando na aba atual.")

    # --- ITEM 5: ABRE LINK LOCALIZAR PROCEDIMENTOS ---
    url_procedimentos = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos"
    logger.info(f"Item 5 - Navegando para link direto: {url_procedimentos}")
    driver.get(url_procedimentos)

    # --- ITEM 6: ITERAÇÃO APÓS CARREGAMENTO DA PÁGINA (MILESTONE 2: REFRESH FALLBACK) ---
    X_ANCHOR_PAGE = "/html/body/header/div[5]/h4/strong"
    X_LOCALIZAR_INPUT_GUIA = "/html/body/main/div[2]/div[1]/div[2]/div[1]/div[2]/input-text-search/div/div/div/input"
    
    page_loaded = False
    for attempt_load in range(3):
        logger.info(f"Item 6 - Verificação de carregamento da página (Tentativa {attempt_load+1}/3)...")
        wait_xpath(driver, X_ANCHOR_PAGE, 3) # Espera leve pela âncora
        
        logger.info("Item 6.1 - Procurando notificação (button-1)...")
        for _ in range(3):
            try:
                btn_close = wait_xpath(driver, '//*[@id="button-1"]', 1)
                if btn_close and btn_close.is_displayed():
                    logger.info("Item 6.1 - Notificação encontrada! Clicando para fechar...")
                    driver.execute_script("arguments[0].click();", btn_close)
                    time.sleep(1)
                    break
            except:
                pass
            time.sleep(1)
        
        _close_alert_if_present(driver)
        
        logger.info("Item 6.1 - Verificando o Input da Guia...")
        input_guia = wait_xpath(driver, X_LOCALIZAR_INPUT_GUIA, 3)
        if input_guia:
            page_loaded = True
            break
        else:
            logger.warning("Item 6 - Input de Guia ausente. Acionando refresh da aba (Milestone 2)...")
            try: driver.refresh()
            except: pass
            time.sleep(4)
            
    if not page_loaded:
        logger.error("Item 6 - Falha permanente ao carregar página de procedimentos após refreshes. Abortando para acionar Milestone 1.")
        raise Exception("Erro: Página de Localizar Procedimentos não carregou (Timeout Milestone 2).")
        
    logger.info("Item 6 - Página carregada e estabilizada.")

    # 6.2 - Se elemento remove estiver presente clicar (apagará carteira)
    logger.info("Item 6.2 - Verificando presença do botão 'remove' (limpeza de carteira) via VBA XPath...")
    try:
        X_REMOVE_CARTEIRA = "/html/body/main/div[2]/div[1]/div[2]/div[1]/div[2]/beneficiario/div/div/div/div/div/div/div/a"
        removes = driver.find_elements(By.XPATH, X_REMOVE_CARTEIRA)
        if removes:
            logger.info("Item 6.2 - Elemento 'remove' da carteira encontrado. Clicando...")
            for r in removes:
                if r.is_displayed():
                    r.click()
                    time.sleep(1) # Wait 1000ms conforme VBA
            logger.info("Item 6.2 - Carteira limpa com sucesso.")
        else:
            logger.info("Item 6.2 - Nenhum botão 'remove' de carteira visível.")
    except Exception as e:
        logger.warning(f"Item 6.2 - Falha ao interagir com 'remove' da carteira: {e}")

    # 6.3 - Apagar dados .clear() e enviar numero_guia
    logger.info(f"Item 6.3 - Input localizado. Executando .clear() e injetando: {numero_guia}...")
    try:
        input_guia.clear()
        time.sleep(0.3)
        input_guia.send_keys(numero_guia)
        time.sleep(0.2)
        logger.info("Item 6.3 - Guia injetada.")
    except Exception as e:
        logger.error(f"Erro no passo 6.3 ao interagir com o input injetado: {e}")
        raise

    # 6.4 - Localizar data ini e data fim pelo data-bind e apagar .clear()
    logger.info("Item 6.4 - Localizando e limpando filtros de data (data-bind)...")
    try:
        dini = wait_xpath(driver, '//input[contains(@data-bind, "idIni")]', 5)
        if dini: 
            logger.info("Item 6.4 - idIni encontrado. Limpando...")
            dini.clear()
            time.sleep(0.2)
        
        dfim = wait_xpath(driver, '//input[contains(@data-bind, "idFim")]', 5)
        if dfim:
            logger.info("Item 6.4 - idFim encontrado. Limpando...")
            dfim.clear()
            time.sleep(0.2)
        logger.info("Item 6.4 - Limpeza de datas concluída.")
    except Exception as e:
        logger.warning(f"Item 6.4 - Exception ao limpar datas: {e}")

    # 6.5 - Botão Pesquisar (X_LOCALIZAR_BTN_PESQUISAR) clicar
    logger.info("Item 6.5 - Localizando botão de Pesquisar...")
    btn_pesquisar = wait_xpath(driver, X_LOCALIZAR_BTN_PESQUISAR, 5)
    if btn_pesquisar:
        logger.info("Item 6.5 - Botão de Pesquisar encontrado. Centralizando e clicando...")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_pesquisar)
        time.sleep(0.5)
        btn_pesquisar.click()
    else:
        logger.error("Item 6.5 - Falha: Botão de pesquisar não localizado.")
        raise Exception("Erro: Botão de pesquisar não localizado.")

    # 6.6 - Aguardar spinner de carregamento
    logger.info("Item 6.6 - Aguardando spinner de processamento (Angular)...")
    _wait_spinner_until_gone(driver, max_checks=5, step_seconds=5, logger=logger)
    time.sleep(2)
    logger.info("Item 6.6 - Spinner de carregamento finalizado. Rolando a página para renderizar...")
    
    # Restaura rolagem global que forçava renderização da tabela
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)

    # 6.7 - Localiza ícone de impressão e segue o fluxo
    logger.info("Item 6.7 - Localizando ícone de impressão pelo data-bind...")
    try:
        print_icon_xpath = '//*[@data-bind="css: CssImpressao(), click: $root.escolherRelatorio"]'
        print_btn = wait_xpath(driver, print_icon_xpath, 10)
        
        if not print_btn:
            logger.error("Item 6.7 - Ícone de impressão não localizado.")
            raise Exception("PermanentError: Guia não localizada ou ícone de impressão ausente após pesquisa.")

        logger.info("Item 6.7 - Ícone de impressão localizado. Centralizando (H/V) e aguardando 500ms...")
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", print_btn)
        time.sleep(0.5)
        
        try:
            logger.info("Item 6.7 - Tentando clique padrão Selenium...")
            print_btn.click()
        except:
            logger.info("Item 6.7 - Falha no clique padrão. Disparando clique via Javascript...")
            driver.execute_script("arguments[0].click();", print_btn)
            
        time.sleep(3)

        # Alternar para a aba de impressão
        logger.info("Alternando para aba de visualização de impressão (índice -1)...")
        driver.switch_to.window(driver.window_handles[-1])

        # Ajustar zoom para 90%
        logger.info("Ajustando zoom para 90%...")
        driver.execute_script("document.body.style.zoom='90%'")
        time.sleep(1)  # Aguarde um pouco para o ajuste de zoom

        # Configurar número de cópias para impressão
        for _ in range(numero_copias):
            try:
                driver.execute_script("window.print();")
            except Exception as e:
                logger.error(f"Erro ao acionar impressão da guia: {e}")
                raise
            time.sleep(2)
        
        # Fecha aba
        driver.close()
        
        # Retorna aba anterior
        logger.info("Aba de impressão fechada. Retornando ao handle principal (índice 0/1)...")
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[1])
        else:
            driver.switch_to.window(driver.window_handles[0])

    except Exception as e:
        logger.error(f"Falha na etapa de impressão interativa: {e}")
        raise

    logger.info("OP5 Finalizado.")
    return [{"numero_guia": numero_guia, "copias_impressas": numero_copias, "sucesso": True}]
