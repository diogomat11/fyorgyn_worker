"""
Op 4 — Execução/Confirmação de Guias SP/SADT (IPASGO)

Rotina desenhada usando automação baseada primariamente em elementos KnockoutJS (data-bind).

Parâmetros esperados em job_data['params']:
  - carteira           : str
  - numero_guia        : str
  - sessoes_realizadas : int (quantas sessoes ja passaram)
"""
import time
import json
import traceback
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

from config.constants import DEFAULT_TIMEOUT

# XPaths essenciais da busca (mesma página do op3)
X_LOCALIZAR_BTN_PESQUISAR = '//*[@id="localizar-procedimentos-btn"]'
X_LOCALIZAR_INPUT_GUIA = '//*[@id="localizarprocedimentos"]/div[1]/div[1]/div[2]/div/form/div[1]/div[1]/div[2]/div/input'
X_LOCALIZAR_INPUT_CARTEIRA = '//*[@id="localizarprocedimentos"]/div[1]/div[1]/div[2]/div/form/div[1]/div[1]/div[4]/div[2]/input'

# --- WAIT HELPERS COMPATÍVEIS COM OP3 ---
def _find_any_xpath(wait, candidates):
    last_err = None
    for xp in candidates:
        try:
            return wait.until(EC.presence_of_element_located((By.XPATH, xp)))
        except Exception as e:
            last_err = e
    raise last_err or Exception("nenhum xpath encontrado")

class _LoggerWrapper:
    def __init__(self, scraper, job_id):
        self.scraper = scraper
        self.job_id = job_id
    def info(self, msg): self.scraper.log(msg, level="INFO", job_id=self.job_id)
    def error(self, msg): self.scraper.log(msg, level="ERROR", job_id=self.job_id)
    def warning(self, msg): self.scraper.log(msg, level="WARN", job_id=self.job_id)
    def debug(self, msg): self.scraper.log(msg, level="DEBUG", job_id=self.job_id)

def wait_xpath(driver, xpath, timeout=DEFAULT_TIMEOUT):
    try:
        wait = WebDriverWait(driver, timeout)
        return _find_any_xpath(wait, [xpath])
    except Exception:
        return None

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


def execute(scraper, job_data):
    job_id = job_data.get("job_id")
    logger = _LoggerWrapper(scraper, job_id)
    driver = scraper.driver

    params_str = job_data.get("params", "")
    p = {}
    if params_str:
        try:
            p = json.loads(params_str) if isinstance(params_str, str) else params_str
        except:
            pass

    numero_guia = p.get("numero_guia", "") or p.get("guia", "")
    carteira = p.get("carteira", "")
    sessoes_realizadas = int(p.get("sessoes_realizadas") or 0)

    if not numero_guia:
        msg = "PermanentError: Guia não informada para execução."
        logger.error(msg)
        raise ValueError(msg)

    logger.info(f"OP4 Iniciado. Guia: {numero_guia} | Sessoes Realizadas: {sessoes_realizadas}")

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
            title = driver.title.lower() if getattr(driver, "title", None) else ""
            if "facplan" in title or "bem-vindo" in title:
                facplan_handle = h
                logger.info(f"Item 4 - Aba alvo encontrada com sucesso: {driver.title}")
                break
        if facplan_handle: break
        time.sleep(1)
    
    if not facplan_handle:
        logger.warning("Item 4 - Aba WebPlan não confirmada pelo título, prosseguindo com aba autêntica se existir.")

    # Fechamento de abas espúrias antigas (mantém apenas principal logada [0] e Facplan secundária)
    if len(driver.window_handles) > 2:
        logger.info("Múltiplas abas detectadas. Limpando histórico residual...")
        main_h = driver.window_handles[0]
        for h in driver.window_handles[1:]:
             driver.switch_to.window(h)
             if facplan_handle and h != facplan_handle:
                  driver.close()
        # Retorna foco para Facplan se localizado, senao a ultima aberta
        if facplan_handle: driver.switch_to.window(facplan_handle)
        else: driver.switch_to.window(driver.window_handles[-1])

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

    _wait_spinner_until_gone(driver, max_checks=4, step_seconds=5, logger=logger)
    time.sleep(2)
    logger.info("Spinner de carregamento finalizado. Rolando a página para renderizar...")
    
    # Adicionada rolagem global (idêntica ao OP5) para forçar a renderização da tabela Angular
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)

    # 3. VERIFICAÇÃO DE DADOS NÃO ENCONTRADOS
    try:
        not_found_xpath = '//div[@data-bind="visible: !possuiProcedimentos() && pesquisaEfetuada()"]'
        not_found_panel = wait_xpath(driver, not_found_xpath, 3)
        if not_found_panel and not_found_panel.is_displayed():
            logger.error("guia_nao_localizada")
            raise Exception("PermanentError: Guia não localizada no sistema IPASGO (Nenhum registro retornado).")
    except Exception as e:
        if "PermanentError" in str(e): raise

    # 4. ABRIR MODAL DE CONFIRMAÇÃO
    try:
        # A lógica exata do VBA recuperada:
        icone_execucao_xpath = '//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]/div[1]/div/div/div/div[2]/div[2]/div/div[1]/div/div[1]/div[2]/div/i[2]'
        
        icone_execucao_element = None
        logger.info("Aguardando botão de confirmação de procedimentos ou renderização da Guia (Máximo 10s)...")
        for i in range(10):
            try:
                elems = driver.find_elements(By.XPATH, icone_execucao_xpath)
                if elems and elems[0].is_displayed():
                    icone_execucao_element = elems[0]
                    break
            except:
                pass
            time.sleep(1)
        
        if not icone_execucao_element:
            logger.info("guia_consulta_execucao_dispensada - Guia localizada porém botão de execução invisível/inexistente.")
            return [{"status": "execucao_dispensada", "motivo": "Guia localizada, mas ícone de detalhe/execução invisível."}]

        # Verificação exata conforme VBA (grayscale)
        statusguia = icone_execucao_element.get_attribute("style") or ""
        logger.info(f"Atributo style do ícone capturado: {statusguia}")
        if "grayscale(1)" in statusguia:
            logger.info("guia_totalmente_executada - Filtro visual detectado no ícone. (grayscale)")
            return [{"status": "totalmente_executada", "execucoes_efetuadas": 0}]
            
        logger.info("Ícone de confirmação apto para clique. Centralizando (H/V)...")
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", icone_execucao_element)
        time.sleep(1)
        
        logger.info("Clicando para abrir painel de execução...")
        try:
            icone_execucao_element.click()
        except:
            logger.info("Falha no clique padrão. Disparando clique via Javascript...")
            driver.execute_script("arguments[0].click();", icone_execucao_element)
            
        time.sleep(3)
        _wait_spinner_until_gone(driver, max_checks=3, step_seconds=3, logger=logger)
        
    except Exception as e:
        logger.error(f"Falha ao validar ícone de execução: {e}")
        raise

    # 5. LOOP DE EXECUÇÃO DENTRO DO MODAL
    execucoes_efetuadas = 0
    
    try:
        # A API solicita focar nos '.col-xs-...' das sessoes da tabela do modal (.card-body).
        card_linhas_xpath = '//*[@id="indentificar-confirmar-procedimentos-modal"]//div[contains(@class, "card-body")]/div[contains(@class, "col-xs-")]'
        linhas_sessoes = driver.find_elements(By.XPATH, card_linhas_xpath)
        
        if not linhas_sessoes:
            card_orig = wait_xpath(driver, '//*[@id="indentificar-confirmar-procedimentos-modal"]//div[contains(@class, "card-body")]', 5)
            if card_orig:
                linhas_sessoes = card_orig.find_elements(By.XPATH, './div')
            else:
                linhas_sessoes = []

        max_disponivel = len(linhas_sessoes)
        logger.info(f"Identificadas {max_disponivel} sessões passíveis na guia.")
        
        sessoes_processar = min(sessoes_realizadas, max_disponivel)
        
        if sessoes_processar <= 0:
            logger.info("Nenhuma sessão solicitada para confirmar.")
        else:
            for i in range(1, sessoes_processar + 1):
                try:
                    linha_box_xpath = f'//*[@id="indentificar-confirmar-procedimentos-modal"]//div[contains(@class, "card-body")]/div[contains(@class, "col-xs-")][{i}]'
                    linha_el = wait_xpath(driver, linha_box_xpath, 2)
                    
                    if not linha_el:
                        # Fallback index caso o col-xs n bata a arvore
                        linha_box_xpath = f'//*[@id="indentificar-confirmar-procedimentos-modal"]//div[contains(@class, "card-body")]/div[{i}]'
                        linha_el = wait_xpath(driver, linha_box_xpath, 2)
                        if not linha_el:
                            continue
                        
                    texto = linha_el.text
                    if "Não confirmado" not in texto:
                        logger.info(f"Sessão index {i} ignorada (aparentemente item_ja_executado pelas validações visuais).")
                        continue
                        
                    btn_confirma_xpath = f'{linha_box_xpath}//button[@data-bind="visible: HabilitadoConfirmacao"]'
                    btn_confirmar = wait_xpath(driver, btn_confirma_xpath, 3)
                    
                    if btn_confirmar and btn_confirmar.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_confirmar)
                        time.sleep(0.5)
                        btn_confirmar.click()
                        time.sleep(1)
                        
                        input_carteira_modal = wait_xpath(driver, '//*[@id="numeroDaCarteiraConfirmacao"]', 5)
                        if input_carteira_modal:
                            if input_carteira_modal.get_attribute("disabled"):
                                driver.execute_script("arguments[0].removeAttribute('disabled');", input_carteira_modal)
                            input_carteira_modal.send_keys(Keys.CONTROL, "a")
                            input_carteira_modal.send_keys(Keys.DELETE)
                            input_carteira_modal.send_keys(carteira)
                            time.sleep(0.5)
                            input_carteira_modal.send_keys(Keys.TAB)
                            time.sleep(2)
                            
                        # Notificacao do sistema Noty (Angular Toaster) confirmando ou criticando a validez
                        noty_text = wait_xpath(driver, '//span[@class="noty_text"]', 5)
                        if noty_text:
                            msg_noty = noty_text.text
                            if "sucesso" in msg_noty.lower():
                                logger.info(f"procedimento_confirmado: index {i} -> OK")
                                execucoes_efetuadas += 1
                                
                                fechar_noty = wait_xpath(driver, '//i[@class="fa fa-times fa-fw close"]', 2)
                                if fechar_noty:
                                    fechar_noty.click()
                                    time.sleep(1)
                            else:
                                logger.error(f"carteira_invalida ou erro reportado: {msg_noty}")
                                raise Exception(f"PermanentError: Validação IPASGO: {msg_noty}")
                        else:
                            logger.warning(f"Não pôde detectar popup de Noty de Sucesso ou falha na sessao {i}")

                    else:
                        logger.warning(f"Botão de autorizar da sessão index {i} inativo/oculto.")

                except Exception as ex_loop:
                    if "PermanentError:" in str(ex_loop):
                        raise
                    logger.warning(f"Falha local na sessão de index {i}: {ex_loop}")
                    
    except Exception as e:
        logger.error(f"Rompimento fatal no loop de execução: {e}")
        raise
    finally:
        # 6. FECHAMENTO DO MODAL DO IPASGO
        try:
            fechar_btn_xpath = '//*[@id="indentificar-confirmar-procedimentos-modal"]//button[contains(text(), "Fechar") or @data-dismiss="modal"]'
            fechar_btn = wait_xpath(driver, fechar_btn_xpath, 3)
            if fechar_btn:
                driver.execute_script("arguments[0].click();", fechar_btn)
                time.sleep(1)
            else:
                fallback_fechar = '//*[@id="indentificar-confirmar-procedimentos-modal"]/div/div/div[3]/div/button[1]'
                fbc = wait_xpath(driver, fallback_fechar, 1)
                if fbc:
                     driver.execute_script("arguments[0].click();", fbc)
                     time.sleep(1)
        except:
             pass

    logger.info(f"OP4 Finalizado. {execucoes_efetuadas} sessões executadas.")
    return [{"numero_guia": numero_guia, "sessoes_realizadas_aplicadas": execucoes_efetuadas, "sucesso": True}]
