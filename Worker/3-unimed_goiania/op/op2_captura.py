"""
Op 2 — Captura de Guias (Unimed Goiania)
Rotina de captura baseada em filtro direto por número de guia e com gestão de timeout.

Fluxo:
  FASE 1: Navegação → SADTs em Aberto (listing page com filtro s_nr_guia)
  FASE 2: PRÉ-FILTRO — Verifica se guia já está capturada na listing
           Se SIM: 
             Verifica timeout do timestamp (limite de 59 min).
             Se expirada → exclui da lista e segue para captura.
             Se válida → salva timestamp_captura → retorna sucesso.
  FASE 3: Se NÃO (ou se excluída por timeout) → entra em new_exame, preenche carteirinha, clica confirmação
  FASE 4: PÓS-FILTRO — Re-aplica filtro s_nr_guia para confirmar captura
           Salva timestamp_captura no banco → retorna sucesso
"""
import time
import json
from datetime import datetime, timedelta
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
    Goiania possui a regra de verificar se está expirada (59 minutos limite).
    Se expirada, deleta a guia no portal e retorna (False, None) para recapturar.
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

    # Verifica resultado via trRow_2
    row_xpath = '//*[@id="conteudo-submenu"]/table[2]/tbody/tr[2]' # First real row (ou trRow_2)
    guia_link_xpath = f'{row_xpath}/td[3]/a'
    
    if is_element_present(scraper.driver, By.XPATH, guia_link_xpath):
        guia_element = scraper.driver.find_element(By.XPATH, guia_link_xpath)
        guia_text = guia_element.text.strip()
        log(f"Guia localizada no filtro: {guia_text}")

        # Captura horário/timestamp (Goiania logic)
        try:
            data_str = scraper.driver.find_element(By.XPATH, f"{row_xpath}/td[1]").text.strip()
            hora_str = ""
            if is_element_present(scraper.driver, By.XPATH, f"{row_xpath}/td[2]"):
                hora_str = scraper.driver.find_element(By.XPATH, f"{row_xpath}/td[2]").text.strip()
                
            timestamp_str = f"{data_str} {hora_str}".strip()
            log(f"Timestamp captura bruto: '{timestamp_str}'")
            
            # Validação do timeout
            try:
                if len(hora_str) > 0:
                    if len(hora_str.split(':')) == 3:
                        guia_dt = datetime.strptime(f"{data_str} {hora_str}", "%d/%m/%Y %H:%M:%S")
                    else:
                        guia_dt = datetime.strptime(f"{data_str} {hora_str}", "%d/%m/%Y %H:%M")
                else:
                    guia_dt = datetime.strptime(data_str, "%d/%m/%Y")
            except Exception as e:
                log(f"Não foi possível converter o timestamp '{timestamp_str}': {e}", level="WARN")
                guia_dt = datetime.now()

            agora = datetime.now()
            limite = guia_dt + timedelta(minutes=59)
            
            # Verifica se está expirada
            if limite < (agora + timedelta(minutes=2)):
                log(f"Guia Expirada localmente! (Limite: {limite} | Atual: {agora}). Excluindo do Grid Web...", level="WARN")
                try:
                    excluir_btn = scraper.driver.find_element(By.XPATH, f"{row_xpath}//img[contains(@src, 'excluir')]/..")
                    _robust_click(scraper.driver, excluir_btn, "Botão Excluir (Timeout)", log)
                    time.sleep(1)
                    # Accept alert
                    WebDriverWait(scraper.driver, 3).until(EC.alert_is_present())
                    alert = scraper.driver.switch_to.alert
                    alert.accept()
                    log("Guia excluída do grid com sucesso. Retornando False para recaptura.", job_id=job_id)
                except Exception as excl_e:
                    log(f"Falha ao tentar clicar em Excluir: {excl_e}", level="ERROR")
                
                # Se excluiu, a guia não está mais presente e precisa ser recapturada.
                return False, None

        except NoSuchElementException:
            timestamp_str = datetime.now().strftime("%d/%m/%Y %H:%M")
            log(f"Horário não encontrado, usando agora: {timestamp_str}")

        return True, timestamp_str
    else:
        log(f"Guia {numero_guia} NÃO localizada no filtro.")
        return False, None


def _save_timestamp_captura(scraper, numero_guia, timestamp_str, job_id):
    """Persiste timestamp_captura na tabela base_guias."""
    try:
        from database import SessionLocal
        from models import BaseGuia
        db_session = SessionLocal()
        try:
            guia_record = db_session.query(BaseGuia).filter(
                BaseGuia.guia == str(numero_guia)
            ).first()

            if guia_record:
                ts = None
                if timestamp_str:
                    for fmt in ["%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M"]:
                        try:
                            ts = datetime.strptime(timestamp_str, fmt)
                            break
                        except ValueError:
                            continue
                if not ts:
                    ts = datetime.now()

                guia_record.timestamp_captura = ts
                db_session.commit()
                scraper.log(f"timestamp_captura salvo para guia {numero_guia}: {ts}", job_id=job_id)
            else:
                scraper.log(f"Registro base_guias não encontrado para guia {numero_guia}.", level="WARN", job_id=job_id)
        finally:
            db_session.close()
    except Exception as db_err:
        scraper.log(f"Erro ao salvar timestamp_captura: {db_err}", level="ERROR", job_id=job_id)


def funccarteira(carteirinha):
    import re
    parts = re.split(r'[.-]', carteirinha)
    if len(parts) == 5:
        return parts[0], parts[1], parts[2], parts[3], parts[4]
    return parts[0] if len(parts) > 0 else "", "", "", "", ""


def _do_new_exame_capture(scraper, carteirinha, numero_guia, job_id):
    """
    Executa a captura real via new_exame → preenche carteirinha → confirma.
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

        x1, x2, x3, x4, x5 = funccarteira(carteirinha)
        cartCompleto = x1 + x2 + x3 + x4 + x5
        cartaoParcial = x2 + x3 + x4 + x5
        
        log("Filling form (Goiania format)...")
        element7 = wait.until(EC.presence_of_element_located((By.NAME, 'nr_via')))
        element6 = driver.find_element(By.NAME, 'DS_CARTAO')
        element3 = driver.find_element(By.NAME, 'CD_DEPENDENCIA')
        
        driver.execute_script("arguments[0].setAttribute('type', 'text');", element7)
        element7.clear()
        element7.send_keys(cartCompleto)
        
        driver.execute_script("arguments[0].setAttribute('type', 'text');", element6)
        element6.clear()
        element6.send_keys(cartaoParcial)
        
        driver.execute_script("arguments[0].setAttribute('type', 'text');", element3)
        element3.clear()
        element3.send_keys(x3)
        
        if x1 != "0064":
            log(f"Carteirinha prefix {x1} != 0064. Checking Validade...")
            if len(driver.find_elements(By.XPATH, '//*[@id="Button_Consulta"]')) > 0:
                driver.find_element(By.XPATH, '//*[@id="Button_Consulta"]').click()
                time.sleep(2)

        # Aguarda tabela de guias carregar
        log("Aguardando tabela de guias (conteudo-submenu)...")
        conteudo_xpath = '//*[@id="conteudo-submenu"]/form/table/tbody/tr[3]/td/input'
        for _ in range(20):
            if driver.find_elements(By.XPATH, conteudo_xpath):
                break
            time.sleep(1)

        # Classificar tabela por SOLICITAÇÃO/DATA
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
        try:
            data_table = driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/table[2]')
            linhas = data_table.find_elements(By.TAG_NAME, "tr")

            for idx in range(1, len(linhas)):
                data_table = driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/table[2]')
                row_xpath = f'//*[@id="conteudo-submenu"]/table[2]/tbody/tr[{idx+1}]'

                if not is_element_present(driver, By.XPATH, f'{row_xpath}/td[6]/span'):
                    if not is_element_present(driver, By.XPATH, f'{row_xpath}/td[6]'):
                        continue

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

                time.sleep(3)
                close_alert_if_present(driver)
                
                # Check for Facial Biometrics
                if captured:
                    biometria_xpath = '//*[@id="root"]/section/div/div/div/div[2]/div/div[3]/button[1]/span[1]'
                    if is_element_present(driver, By.XPATH, biometria_xpath):
                        log("Tela de Biometria Facial detectada. Aguardando realização (até 3 min)...")
                        start_wait = time.time()
                        biometria_concluida = False
                        
                        while time.time() - start_wait < 180:
                            if not is_element_present(driver, By.XPATH, biometria_xpath):
                                log("Tela de biometria desapareceu.")
                                biometria_concluida = True
                                break
                            time.sleep(3)
                            
                        if not biometria_concluida:
                            log("Timeout de 3 min para Biometria Facial. Fechando janela.", level="WARN")
                            try:
                                driver.close()
                                driver.switch_to.window(driver.window_handles[0])
                            except:
                                pass

                break

        except NoSuchElementException:
            log("Tabela de guias não encontrada no popup.", level="ERROR")

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
    Executa captura de uma guia específica no portal SGUCard Goiania.
    """
    job_id = job_data.get("job_id")
    carteirinha = job_data.get("carteirinha")
    carteirinha_db_id = job_data.get("carteirinha_id")

    numero_guia = None
    try:
        params_str = job_data.get("params")
        if params_str:
            params_obj = json.loads(params_str) if isinstance(params_str, str) else params_str
            numero_guia = params_obj.get("numero_guia", "") or params_obj.get("guia", "")
            if not numero_guia:
                guias_list = params_obj.get("guias", [])
                if isinstance(guias_list, list) and len(guias_list) > 0:
                    numero_guia = str(guias_list[0])
    except (json.JSONDecodeError, AttributeError):
        pass

    if not numero_guia:
        scraper.log("PermanentError: numero_guia obrigatório para Captura", level="ERROR", job_id=job_id)
        raise ValueError("PermanentError: numero_guia obrigatório para Captura")

    scraper.log(f"Op2 Captura Guias Goiania: Guia={numero_guia}, Carteirinha={carteirinha}", job_id=job_id, carteirinha_id=carteirinha_db_id)

    scraper.log("FASE 1: Navegando até SADTs em aberto...", job_id=job_id)
    try:
        _navigate_to_sadts(scraper, job_id)
    except Exception as e:
        scraper.log(f"Navegação falhou: {e}", level="ERROR", job_id=job_id)
        raise

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

    scraper.log(f"FASE 3: Guia {numero_guia} ausente/expirada. Iniciando captura via new_exame...", job_id=job_id)
    captured = _do_new_exame_capture(scraper, carteirinha, numero_guia, job_id)

    if not captured:
        raise ValueError(f"PermanentError: Guia {numero_guia} não localizada na tabela de guias. Captura não realizada.")

    scraper.log(f"FASE 4: PÓS-FILTRO — Confirmando captura da guia {numero_guia}...", job_id=job_id)

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
        scraper.log("guia não capturada ou biometria não realizada", level="ERROR", job_id=job_id)
        raise ValueError("PermanentError: guia não capturada ou biometria não realizada")

    return [{
        "numero_guia": numero_guia,
        "timestamp_captura": timestamp_str or datetime.now().strftime("%d/%m/%Y %H:%M"),
        "status": "Capturado",
        "pre_filter": False
    }]
