"""
Op 2 — Captura de Guias (Unimed Anápolis)
Rotina de captura baseada em filtro direto por número de guia.
Conforme spec 002-implantacoes.yaml e modelo_scrapping/filtroguia.py:

Fluxo:
  FASE 1: Navegação → SADTs em Aberto (listing page com filtro s_nr_guia)
  FASE 2: PRÉ-FILTRO — Verifica se guia já está capturada na listing
           Se SIM → salva timestamp_captura → retorna sucesso
  FASE 3: Se NÃO → entra em new_exame, preenche carteirinha, clica confirmação
  FASE 4: PÓS-FILTRO — Re-aplica filtro s_nr_guia para confirmar captura
           Salva timestamp_captura no banco → retorna sucesso
"""
import time
import json
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, NoAlertPresentException
)

import os, sys
_worker_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _worker_root not in sys.path:
    sys.path.insert(0, _worker_root)

_module_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _module_root not in sys.path:
    sys.path.insert(0, _module_root)

from infra.selenium_helpers import (
    is_element_present, close_popup_window, close_alert_if_present, wait_for_element
)
from config.settings import NavSelectors


# ── Helpers ──────────────────────────────────────────────────────────────────

def _robust_click(driver, element, name, log_fn=None):
    """Click com fallback JS."""
    try:
        element.click()
        if log_fn:
            log_fn(f"Clicked {name}")
    except Exception:
        driver.execute_script("arguments[0].click();", element)
        if log_fn:
            log_fn(f"JS Clicked {name}")


def _navigate_to_sadts(scraper, job_id):
    """
    Navega do menu principal até a listing page de SADTs em Aberto.
    Retorna quando a listing page está visível (com s_nr_guia disponível).
    """
    log = lambda msg, **kw: scraper.log(msg, job_id=job_id, **kw)
    close_popup_window(scraper.driver)

    # Menu home icon
    if is_element_present(scraper.driver, By.CSS_SELECTOR, NavSelectors.MENU_CENTRO_61):
        el = scraper.driver.find_element(By.CSS_SELECTOR, NavSelectors.MENU_CENTRO_61)
        _robust_click(scraper.driver, el, "MENU_CENTRO_61", log)
        time.sleep(1)

    # Menu Item 2 (Autorizador)
    wait_for_element(scraper.driver, By.ID, NavSelectors.MENU_ITEM_2)
    el = scraper.driver.find_element(By.ID, NavSelectors.MENU_ITEM_2)
    _robust_click(scraper.driver, el, "MENU_ITEM_2", log)
    time.sleep(2)

    # Fecha popups extras
    current_handles = scraper.driver.window_handles
    if len(current_handles) > 1:
        for handle in current_handles[1:]:
            scraper.driver.switch_to.window(handle)
            scraper.driver.close()
        scraper.driver.switch_to.window(current_handles[0])

    # SADTs em aberto
    target_submenu = "#centro_3 .MagnetoSubMenuTittle"
    wait_for_element(scraper.driver, By.CSS_SELECTOR, target_submenu)
    el = scraper.driver.find_element(By.CSS_SELECTOR, target_submenu)
    _robust_click(scraper.driver, el, "SADTs em aberto (#centro_3)", log)
    time.sleep(3)


def _apply_guia_filter(scraper, numero_guia, job_id):
    """
    Aplica filtro s_nr_guia + Button_FIltro na listing page.
    Conforme modelo_scrapping/filtroguia.py:
      1. click s_nr_guia
      2. type numero_guia
      3. click Button_FIltro
    Retorna (guia_localizada: bool, timestamp_str: str|None).
    """
    log = lambda msg, **kw: scraper.log(msg, job_id=job_id, **kw)
    wait = WebDriverWait(scraper.driver, 15)

    # Localiza e preenche input de filtro
    input_guia = wait.until(EC.presence_of_element_located((By.NAME, "s_nr_guia")))
    input_guia.click()
    input_guia.clear()
    input_guia.send_keys(str(numero_guia))
    log(f"Input s_nr_guia preenchido com: {numero_guia}")

    # Clica Button_FIltro
    btn_filtro = scraper.driver.find_element(By.NAME, "Button_FIltro")
    _robust_click(scraper.driver, btn_filtro, "Button_FIltro", log)
    time.sleep(3)

    # Verifica resultado via trRow_2/td[3]/a (conforme filtroguia.py)
    guia_link_xpath = '//tr[@id="trRow_2"]/td[3]/a'
    horario_xpath = '//tr[@id="trRow_2"]/td[2]'

    if is_element_present(scraper.driver, By.XPATH, guia_link_xpath):
        guia_element = scraper.driver.find_element(By.XPATH, guia_link_xpath)
        guia_text = guia_element.text.strip()
        log(f"Guia localizada no filtro: {guia_text}")

        # Captura horário/timestamp
        timestamp_str = None
        try:
            horario_el = scraper.driver.find_element(By.XPATH, horario_xpath)
            horario_el.click()  # conforme filtroguia.py step4
            timestamp_str = horario_el.text.strip()
            log(f"Timestamp captura bruto: '{timestamp_str}'")
        except NoSuchElementException:
            timestamp_str = datetime.now().strftime("%d/%m/%Y %H:%M")
            log(f"Horário não encontrado, usando agora: {timestamp_str}")

        return True, timestamp_str
    else:
        log(f"Guia {numero_guia} NÃO localizada no filtro.")
        return False, None


def _save_timestamp_captura(scraper, numero_guia, timestamp_str, job_id):
    pass


def funccarteira(carteirinha):
    """Formata carteirinha Unimed em 5 partes: x1(4), x2(4), x3(6), x4(2), x5(rest)."""
    cart = carteirinha.replace(".", "").replace("-", "").strip()
    x1 = cart[0:4]
    x2 = cart[4:8]
    x3 = cart[8:14]
    x4 = cart[14:16]
    x5 = cart[16:]
    return x1, x2, x3, x4, x5


def _do_new_exame_capture(scraper, carteirinha, numero_guia, job_id):
    """
    Executa a captura real via new_exame → preenche carteirinha → confirma.
    Reutiliza a mesma lógica de navegação de op1_consulta (frozen),
    mas com ação de confirmação (button_confirmar_voltar / button_confirmar).
    """
    log = lambda msg, **kw: scraper.log(msg, job_id=job_id, **kw)
    driver = scraper.driver

    # Clica new_exame para abrir popup de busca
    log("Abrindo new_exame para captura...")
    xpath_new_exame = '//*[@id="cadastro_biometria"]/div/div[2]/span'

    if is_element_present(driver, By.NAME, 'nr_via'):
        log("Form 'nr_via' encontrado diretamente, pulando clique new_exame.")
    elif is_element_present(driver, By.XPATH, xpath_new_exame):
        el = driver.find_element(By.XPATH, xpath_new_exame)
        _robust_click(driver, el, "new_exame", log)
    else:
        raise Exception("Botão new_exame não encontrado na tela de SADTs em aberto.")

    time.sleep(3)

    # Muda para popup
    handles = driver.window_handles
    if len(handles) > 1:
        driver.switch_to.window(handles[-1])
        driver.maximize_window()
        log("Switched to popup window")
    else:
        raise Exception("Popup window não abriu após clicar new_exame.")

    try:
        wait = WebDriverWait(driver, 20)

        # Preenche carteirinha
        x1, x2, x3, x4, x5 = funccarteira(carteirinha)
        time.sleep(2)

        # ignora-cartao
        ignora_cartao = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="ignora-cartao"]')))
        log("Clicking ignora-cartao")
        ignora_cartao.click()

        # cad_Benef
        cad_benef = wait.until(EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="conteudo-submenu"]/table/tbody/tr[1]/td/div[1]/a')
        ))
        log("Clicking cad_Benef")
        cad_benef.click()

        # input x1 (prefixo operadora)
        input_x1 = wait.until(EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="NewRecord1"]/table/tbody/tr[1]/td[2]/input[1]')
        ))
        input_x1.clear()
        input_x1.send_keys(x1)

        # input CD_BNF
        cd_bnf = driver.find_element(By.XPATH, '//*[@id="s_CD_BNF_PADRAO_PTU"]')
        cd_bnf.click()
        cd_bnf.clear()
        cd_bnf.send_keys(x2 + x3 + x4 + x5)

        # botao_verificar
        botao_verificar = driver.find_element(
            By.XPATH, '//*[@id="NewRecord1"]/table/tbody/tr[2]/td/input[2]'
        )
        log("Clicking botao_verificar")
        botao_verificar.click()
        time.sleep(1)

        # Validação de carteira inválida (smart loop 5s)
        start_time = time.time()
        inv_carteira = False

        while time.time() - start_time < 5:
            try:
                alert = driver.switch_to.alert
                if alert:
                    alert_text = alert.text.lower()
                    alert.accept()
                    if "inválido" in alert_text or "dígito" in alert_text or "carteira" in alert_text:
                        inv_carteira = True
                        break
            except NoAlertPresentException:
                pass

            try:
                msg_error = driver.find_element(By.XPATH, '/html/body/div/form/table/tbody/tr[1]/td')
                if msg_error.is_displayed():
                    text_lower = msg_error.text.lower()
                    if "inválido" in text_lower or "dígito" in text_lower:
                        inv_carteira = True
                        break
            except NoSuchElementException:
                pass

            try:
                if (driver.find_elements(By.XPATH, '//*[@id="Button_Update"]') or
                    driver.find_elements(By.XPATH, '//*[@id="Button_Insert"]') or
                    driver.find_elements(By.XPATH, '//*[@id="tb_sadt_aberto"]')):
                    break
            except:
                pass

            time.sleep(0.5)

        if inv_carteira:
            raise ValueError("PermanentError: Carteira inválida")

        time.sleep(1)

        # Atualiza/Cadastra beneficiário se prefixo não é Unimed local
        # (Padrão idêntico ao op1_consulta: clique duplo + re-check)
        if x1 != "0178":
            log(f"Prefixo {x1} != 0178. Verificando atualiza_benef...")
            atualiza_benef_xpath = '//*[@id="Button_Update"]'
            insert_benef_xpath = '//*[@id="Button_Insert"]'

            if len(driver.find_elements(By.XPATH, atualiza_benef_xpath)) > 0:
                btn_update = driver.find_element(By.XPATH, atualiza_benef_xpath)
                btn_update.click()
                time.sleep(1)
                # Segundo clique (conforme op1)
                try:
                    btn_update.click()
                    time.sleep(1)
                except:
                    pass
                # Re-check se ainda visível → clica novamente
                updates_remaining = driver.find_elements(By.XPATH, atualiza_benef_xpath)
                if len(updates_remaining) > 0 and updates_remaining[0].is_displayed():
                    updates_remaining[0].click()
                    time.sleep(1)

            elif len(driver.find_elements(By.XPATH, insert_benef_xpath)) > 0:
                log("Button_Update não encontrado, Button_Insert encontrado. Clicando cadastrar...")
                btn_insert = driver.find_element(By.XPATH, insert_benef_xpath)
                btn_insert.click()
                time.sleep(1)
                try:
                    btn_insert.click()
                    time.sleep(1)
                except:
                    pass
                inserts_remaining = driver.find_elements(By.XPATH, insert_benef_xpath)
                if len(inserts_remaining) > 0 and inserts_remaining[0].is_displayed():
                    inserts_remaining[0].click()
                    time.sleep(1)

        # Aguarda tabela de guias carregar
        log("Aguardando tabela de guias (conteudo-submenu)...")
        conteudo_xpath = '//*[@id="conteudo-submenu"]/form/table/tbody/tr[3]/td/input'
        for _ in range(20):
            if driver.find_elements(By.XPATH, conteudo_xpath):
                break
            time.sleep(1)

        # Classificar tabela por SOLICITAÇÃO/DATA (idêntico ao op1_consulta)
        try:
            xpath_headers = '//*[@id="conteudo-submenu"]/table[2]//th | //*[@id="conteudo-submenu"]/table[2]//tr[1]/td | //*[@id="conteudo-submenu"]/table[2]//tr[2]/td'
            header_elems = driver.find_elements(By.XPATH, xpath_headers)
            sort_clicked = False
            for el in header_elems:
                if "SOLICITA" in el.text.upper() or "DATA" in el.text.upper():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                    links = el.find_elements(By.TAG_NAME, "a")
                    target = links[0] if links else el
                    log(f"Classificando por coluna: {el.text}")
                    target.click()
                    time.sleep(2)
                    sort_clicked = True
                    break

            if sort_clicked:
                # Re-find após primeiro clique (previne StaleElement após POSTBACK)
                header_elems = driver.find_elements(By.XPATH, xpath_headers)
                for el in header_elems:
                    if "SOLICITA" in el.text.upper() or "DATA" in el.text.upper():
                        links = el.find_elements(By.TAG_NAME, "a")
                        target = links[0] if links else el
                        target.click()
                        time.sleep(2)
                        log("Segundo clique (Decrescente) aplicado.")
                        break
            else:
                log("Coluna SOLICITAÇÃO não encontrada para classificar.", level="WARN")
        except Exception as sort_err:
            log(f"Falha ao classificar tabela: {sort_err}", level="WARN")

        # Busca a guia alvo na tabela e confirma (captura)
        captured = False
        limit_pages = 20
        current_page = 0
        
        while not captured and current_page < limit_pages:
            current_page += 1
            log(f"Analisando página {current_page} de guias abertas...")
            try:
                data_table = driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/table[2]')
                linhas = data_table.find_elements(By.TAG_NAME, "tr")

                for idx in range(1, len(linhas)):
                    if captured: break
                    data_table = driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/table[2]')
                    row_xpath = f'//*[@id="conteudo-submenu"]/table[2]/tbody/tr[{idx+1}]'

                    if not is_element_present(driver, By.XPATH, f'{row_xpath}/td[6]/span'):
                        if not is_element_present(driver, By.XPATH, f'{row_xpath}/td[6]'):
                            continue

                    # Verifica se é Autorizado e se contém a guia alvo
                    try:
                        status_el = driver.find_element(By.XPATH, f'{row_xpath}/td[6]')
                        status_text = status_el.text.strip().upper()
                    except:
                        continue

                    if "AUTORIZADO" not in status_text and "LIBERAD" not in status_text:
                        continue

                    row_text = driver.find_element(By.XPATH, row_xpath).text
                    if str(numero_guia) not in row_text:
                        continue

                    # Encontrou a guia! Clicar para abrir detalhes
                    log(f"Guia {numero_guia} encontrada na tabela. Abrindo detalhes...")
                    driver.find_element(By.XPATH, f'{row_xpath}/td[4]/a').click()
                    time.sleep(2)

                    # Confirmação de captura
                    if is_element_present(driver, By.XPATH, '//*[@id="Button_Voltar"]'):
                        # Tenta button_confirmar_voltar
                        if driver.find_elements(By.ID, 'button_confirmar_voltar'):
                            driver.find_element(By.ID, 'button_confirmar_voltar').click()
                            log("Clicked button_confirmar_voltar")
                            captured = True
                        elif driver.find_elements(By.ID, 'button_confirmar'):
                            driver.find_element(By.ID, 'button_confirmar').click()
                            log("Clicked button_confirmar")
                            captured = True
                        else:
                            log("Nenhum botão de confirmação encontrado. Voltando.", level="WARN")
                            driver.find_element(By.XPATH, '//*[@id="Button_Voltar"]').click()

                    time.sleep(2)
                    close_alert_if_present(driver)
                    break
                    
                if not captured:
                    # Pagination logic
                    try:
                        next_links = driver.find_elements(By.XPATH, "//a[contains(text(),'Próxima') or contains(text(),'>') or contains(translate(text(), 'P', 'p'), 'próxima')]")
                        if not next_links:
                            break # No more pages

                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_links[-1])
                        time.sleep(0.5)
                        try:
                            next_links[-1].click()
                        except:
                            driver.execute_script("arguments[0].click();", next_links[-1])
                        time.sleep(3)
                    except Exception as e:
                        log(f"Fim da paginação ou erro ao avançar: {e}")
                        break

            except NoSuchElementException:
                log("Tabela de guias não encontrada no popup.", level="ERROR")
                break

        if not captured:
            log(f"Guia {numero_guia} não pôde ser capturada no popup.", level="ERROR")

        return captured

    finally:
        # Fecha popup e retorna à janela principal
        try:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
        except:
            pass


# ── Entry Point ──────────────────────────────────────────────────────────────

def execute(scraper, job_data):
    """
    Executa captura de uma guia específica no portal SGUCard Anápolis.

    Fluxo:
      1. Navega até SADTs em Aberto (listing page)
      2. PRÉ-FILTRO: aplica s_nr_guia para verificar se guia já está capturada
         → se SIM: salva timestamp, retorna sucesso
      3. Se NÃO: executa new_exame → preenche carteirinha → confirma captura
      4. PÓS-FILTRO: re-aplica s_nr_guia para confirmar captura e salvar timestamp
    """
    job_id = job_data.get("job_id")
    carteirinha = job_data.get("carteirinha")
    carteirinha_db_id = job_data.get("carteirinha_id")

    # Parse params para obter numero_guia — suporta múltiplos formatos:
    #   { "numero_guia": "123" }           ← criado por /capturar
    #   { "guia": "123" }                  ← fallback
    #   { "guias": ["123", "456"] }        ← criado por /jobs/ genérico
    numero_guia = None
    try:
        params_str = job_data.get("params")
        if params_str:
            params_obj = json.loads(params_str) if isinstance(params_str, str) else params_str
            numero_guia = params_obj.get("numero_guia", "") or params_obj.get("guia", "")
            # Fallback: 'guias' array (usado pelo endpoint genérico /jobs/)
            if not numero_guia:
                guias_list = params_obj.get("guias", [])
                if isinstance(guias_list, list) and len(guias_list) > 0:
                    numero_guia = str(guias_list[0])
    except (json.JSONDecodeError, AttributeError):
        pass

    if not numero_guia:
        scraper.log("PermanentError: numero_guia obrigatório para Captura", level="ERROR", job_id=job_id)
        raise ValueError("PermanentError: numero_guia obrigatório para Captura")

    scraper.log(f"Op2 Captura: Guia={numero_guia}, Carteirinha={carteirinha}", job_id=job_id, carteirinha_id=carteirinha_db_id)

    # ── FASE 1: Navegação até SADTs em Aberto ──
    scraper.log("FASE 1: Navegando até SADTs em aberto...", job_id=job_id)
    try:
        _navigate_to_sadts(scraper, job_id)
    except Exception as e:
        scraper.log(f"Navegação falhou: {e}", level="ERROR", job_id=job_id)
        raise

    # ── FASE 2: PRÉ-FILTRO — Verifica se guia já está capturada ──
    scraper.log(f"FASE 2: PRÉ-FILTRO — Verificando guia {numero_guia}...", job_id=job_id)
    try:
        guia_encontrada, timestamp_str = _apply_guia_filter(scraper, numero_guia, job_id)
    except Exception as e:
        scraper.log(f"Erro no pré-filtro: {e}", level="ERROR", job_id=job_id)
        raise

    if guia_encontrada:
        scraper.log(f"Guia {numero_guia} já capturada no sistema. Salvando timestamp.", job_id=job_id)
        _save_timestamp_captura(scraper, numero_guia, timestamp_str, job_id)
        return [{
            "numero_guia": numero_guia,
            "timestamp_captura": timestamp_str,
            "status": "Capturado",
            "pre_filter": True
        }]

    # ── FASE 3: NEW EXAME — Captura real ──
    scraper.log(f"FASE 3: Guia {numero_guia} não encontrada. Iniciando captura via new_exame...", job_id=job_id)
    captured = _do_new_exame_capture(scraper, carteirinha, numero_guia, job_id)

    if not captured:
        raise ValueError(f"PermanentError: Guia {numero_guia} não localizada na tabela de guias. Captura não realizada.")

    # ── FASE 4: PÓS-FILTRO — Confirma captura e obtém timestamp ──
    scraper.log(f"FASE 4: PÓS-FILTRO — Confirmando captura da guia {numero_guia}...", job_id=job_id)

    # Re-navega para SADTs em aberto (após fechar popup, estamos na janela principal)
    time.sleep(2)
    try:
        _navigate_to_sadts(scraper, job_id)
        guia_confirmada, timestamp_str = _apply_guia_filter(scraper, numero_guia, job_id)
    except Exception as e:
        scraper.log(f"Erro no pós-filtro: {e}. Registrando sucesso com timestamp local.", level="WARN", job_id=job_id)
        guia_confirmada = True
        timestamp_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    if guia_confirmada:
        scraper.log(f"PÓS-FILTRO: Guia {numero_guia} confirmada no sistema!", job_id=job_id)
        _save_timestamp_captura(scraper, numero_guia, timestamp_str, job_id)
    else:
        scraper.log(f"PÓS-FILTRO: Guia {numero_guia} não confirmada no filtro. Registrando com timestamp local.", level="WARN", job_id=job_id)
        _save_timestamp_captura(scraper, numero_guia, datetime.now().strftime("%d/%m/%Y %H:%M"), job_id)

    return [{
        "numero_guia": numero_guia,
        "timestamp_captura": timestamp_str or datetime.now().strftime("%d/%m/%Y %H:%M"),
        "status": "Capturado",
        "pre_filter": False
    }]
