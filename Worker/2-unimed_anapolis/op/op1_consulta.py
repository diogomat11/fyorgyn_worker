"""
Op 1 — Consulta Guias
Rotina de consulta de guias (consultaGuias), espelhada da lógica da Unimed Goiânia (new_exame).
"""
import time
import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import os, sys
# Ensure imports work if run as module
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

def funccarteira(carteirinha):
    """
    Formata carteirinha Unimed:
    Ex: 0064.8000.387928.00-0 -> x1='0064', x2='8000', x3='387928', x4='00', x5='0'
    """
    cart = carteirinha.replace(".", "").replace("-", "").strip()
    # 0064 8000 387928 00 0
    # 4    4    6      2  1  = 17 chars
    if len(cart) < 17:
        # Fallback or error? Goiania script didn't allow < 17 properly potentially
        pass
    
    x1 = cart[0:4]
    x2 = cart[4:8]
    x3 = cart[8:14]
    x4 = cart[14:16]
    x5 = cart[16:]
    return x1, x2, x3, x4, x5

def execute(scraper, job_data):
    """
    Executa consulta de guias para uma carteirinha.
    Lógica copiada e adaptada de Unimed Goiânia (ImportBaseGuias.py).
    """
    job_id = job_data.get("job_id")
    carteirinha = job_data.get("carteirinha")
    carteirinha_db_id = job_data.get("carteirinha_id") # if available
    
    scraper.log(f"Op1: Processing carteirinha {carteirinha}", job_id=job_id, carteirinha_id=carteirinha_db_id)
    
    if not carteirinha:
        scraper.log("Carteirinha not provided in job_data", level="ERROR", job_id=job_id)
        raise ValueError("Carteirinha required for op1")

    # Ensure main window
    close_popup_window(scraper.driver)

    # 1. Navigation (Anapolis Specific)
    scraper.log("Navigating to Consulta (Anapolis sequence)...", job_id=job_id)
    
    def robust_click(element, name):
        try:
            element.click()
            scraper.log(f"Clicked {name}", job_id=job_id)
        except Exception as e:
            scraper.log(f"Standard click failed for {name}, trying JS...", job_id=job_id)
            scraper.driver.execute_script("arguments[0].click();", element)
            scraper.log(f"JS Clicked {name}", job_id=job_id)

    try:
        # 1.1 Click Main Menu Icon (if present)
        if is_element_present(scraper.driver, By.CSS_SELECTOR, NavSelectors.MENU_CENTRO_61):
            el = scraper.driver.find_element(By.CSS_SELECTOR, NavSelectors.MENU_CENTRO_61)
            robust_click(el, "MENU_CENTRO_61")
            time.sleep(1)

        # 1.2 Click Main Menu Item 2 (Autorizador?)
        wait_for_element(scraper.driver, By.ID, NavSelectors.MENU_ITEM_2)
        el = scraper.driver.find_element(By.ID, NavSelectors.MENU_ITEM_2)
        robust_click(el, "MENU_ITEM_2")
        time.sleep(2)

        # 1.3 Handle Popup
        current_handles = scraper.driver.window_handles
        if len(current_handles) > 1:
            scraper.log(f"Popup detected ({len(current_handles)} windows), checking...", job_id=job_id)
            # Switch to new window to see what it is, or just close it?
            # IDE script closed it.
            for handle in current_handles[1:]:
                scraper.driver.switch_to.window(handle)
                scraper.log(f"Closing popup: {scraper.driver.title}", job_id=job_id)
                scraper.driver.close()
            scraper.driver.switch_to.window(current_handles[0])
        
        # 1.4 Click Submenu (SADTs em aberto)
        # centro_21 was "Finalizados". centro_3 is "Em Aberto".
        # We try centro_3 first as it's more likely to have "New" button.
        target_submenu = "#centro_3 .MagnetoSubMenuTittle"
        
        wait_for_element(scraper.driver, By.CSS_SELECTOR, target_submenu)
        el = scraper.driver.find_element(By.CSS_SELECTOR, target_submenu)
        robust_click(el, "SADTs em aberto (#centro_3)")
        time.sleep(3)

    except Exception as e:
        scraper.log(f"Navigation failed: {e}", level="ERROR", job_id=job_id)
        raise

    # 2. Now we should be at the "Comum" part (Biometria / New Exame)
    scraper.log("Looking for 'new_exame'...", job_id=job_id)
    try:
        xpath_new_exame = '//*[@id="cadastro_biometria"]/div/div[2]/span' # Generic
        
        # Check frameworks/iframes?
        if len(scraper.driver.find_elements(By.TAG_NAME, 'iframe')) > 0:
            scraper.log("IFRAMES detected! We might need to switch frame.", job_id=job_id)
            
        if is_element_present(scraper.driver, By.NAME, 'nr_via'):
             scraper.log("Form 'nr_via' found directly! Skipping new_exame click.", job_id=job_id)
        elif is_element_present(scraper.driver, By.XPATH, xpath_new_exame):
            el = scraper.driver.find_element(By.XPATH, xpath_new_exame)
            robust_click(el, "new_exame")
        else:
            scraper.log("'new_exame' OR form not found. Dumping page source...", level="ERROR", job_id=job_id)
            with open("anapolis_source_emaberto.html", "w", encoding="utf-8") as f:
                f.write(scraper.driver.page_source)

    except Exception as e:
        scraper.log(f"Error handling 'new_exame': {e}", level="WARN", job_id=job_id)


    time.sleep(3)

    # 3. Handle Popup
    handles = scraper.driver.window_handles
    if len(handles) > 1:
        scraper.driver.switch_to.window(handles[-1])
        scraper.driver.maximize_window()
        scraper.log("Switched to popup window", job_id=job_id)
        # time.sleep(2) # Loaded from wait below
    else:
        scraper.log("Popup window did not open!", level="ERROR", job_id=job_id)
        raise Exception("Popup window not found")

    collected_data = []

    try:
        # 4. Fill Form (Anapolis specific fallback via ignora-cartao)
        x1, x2, x3, x4, x5 = funccarteira(carteirinha)
        cartCompleto = x1 + x2 + x3 + x4 + x5      
        cartaoParcial = x2 + x3 + x4 + x5
        
        time.sleep(2)
        wait = WebDriverWait(scraper.driver, 20)
        
        # ignora_cartao
        ignora_cartao = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="ignora-cartao"]')))
        scraper.log("Clicking ignora-cartao", job_id=job_id)
        ignora_cartao.click()
        
        # cad_Benef
        cad_benef = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="conteudo-submenu"]/table/tbody/tr[1]/td/div[1]/a')))
        scraper.log("Clicking cad_Benef", job_id=job_id)
        cad_benef.click()
        
        # input x1
        input_x1 = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="NewRecord1"]/table/tbody/tr[1]/td[2]/input[1]')))
        input_x1.clear()
        input_x1.send_keys(x1)
        
        # input CD_BNF
        cd_bnf = scraper.driver.find_element(By.XPATH, '//*[@id="s_CD_BNF_PADRAO_PTU"]')
        cd_bnf.click()
        cd_bnf.clear()
        cd_bnf.send_keys(x2 + x3 + x4 + x5)
        
        # botao_verificar
        botao_verificar = scraper.driver.find_element(By.XPATH, '//*[@id="NewRecord1"]/table/tbody/tr[2]/td/input[2]')
        scraper.log("Clicking botao_verificar", job_id=job_id)
        botao_verificar.click()
        time.sleep(1)
        
        # Validacao de Carteira Invalida via Smart Loop (Aguardar SGUCard processar até 5s)
        from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
        start_time = time.time()
        inv_carteira = False
        
        while time.time() - start_time < 5:
            # 1. Verifica Javascript Alert
            try:
                alert = scraper.driver.switch_to.alert
                if alert:
                    alert_text = alert.text.lower()
                    alert.accept()
                    if "inválido" in alert_text or "dígito" in alert_text or "carteira" in alert_text:
                        inv_carteira = True
                        break
            except NoAlertPresentException:
                pass
            
            # 2. Verifica DOM Table
            try:
                msg_error = scraper.driver.find_element(By.XPATH, '/html/body/div/form/table/tbody/tr[1]/td')
                if msg_error.is_displayed():
                    text_lower = msg_error.text.lower()
                    if "inválido" in text_lower or "dígito" in text_lower:
                        inv_carteira = True
                        break
            except NoSuchElementException:
                pass
                
            # 3. Se aparecerem os botões de próximo passo, significa que a carteira é VÁLIDA. Pode sair do wait.
            try:
                if scraper.driver.find_elements(By.XPATH, '//*[@id="Button_Update"]') or \
                   scraper.driver.find_elements(By.XPATH, '//*[@id="Button_Insert"]') or \
                   scraper.driver.find_elements(By.XPATH, '//*[@id="tb_sadt_aberto"]'):
                    break
            except:
                pass
                
            time.sleep(0.5)

        if inv_carteira:
            raise ValueError("PermanentError: Carteira inválida")
        
        # 5. Check 'Validade', 'Atualiza Beneficiario', or 'Cadastrar' button if not Unimed local
        if x1 != "0178":
            scraper.log(f"Prefix {x1} != 0178. Checking atualiza_benef or cadastrar...", job_id=job_id)
            atualiza_benef_xpath = '//*[@id="Button_Update"]'
            insert_benef_xpath = '//*[@id="Button_Insert"]'
            
            if len(scraper.driver.find_elements(By.XPATH, atualiza_benef_xpath)) > 0:
                btn_update = scraper.driver.find_element(By.XPATH, atualiza_benef_xpath)
                btn_update.click()
                time.sleep(1)
                # User requested double click logic
                try:
                    btn_update.click()
                    time.sleep(1)
                except:
                    pass
                
                # re-check if still visible
                updates_remaining = scraper.driver.find_elements(By.XPATH, atualiza_benef_xpath)
                if len(updates_remaining) > 0 and updates_remaining[0].is_displayed():
                    updates_remaining[0].click()
                    time.sleep(1)
                    
            elif len(scraper.driver.find_elements(By.XPATH, insert_benef_xpath)) > 0:
                scraper.log("Button_Update not found, mas Button_Insert encontrado. Clicando cadastrar...", job_id=job_id)
                btn_insert = scraper.driver.find_element(By.XPATH, insert_benef_xpath)
                btn_insert.click()
                time.sleep(1)
                try:
                    btn_insert.click()
                    time.sleep(1)
                except:
                    pass
                
                # re-check if still visible
                inserts_remaining = scraper.driver.find_elements(By.XPATH, insert_benef_xpath)
                if len(inserts_remaining) > 0 and inserts_remaining[0].is_displayed():
                    inserts_remaining[0].click()
                    time.sleep(1)

        # 6. Wait for conteudo_submenu appears (wait loop) o elemento botão filtrar
        scraper.log("Waiting for conteudo_submenu form...", job_id=job_id)
        conteudo_submenu_xpath = '//*[@id="conteudo-submenu"]/form/table/tbody/tr[3]/td/input'
        
        max_retries = 20
        for i in range(max_retries):
            if len(scraper.driver.find_elements(By.XPATH, conteudo_submenu_xpath)) > 0:
                break
            time.sleep(1)
        else:
            scraper.log("conteudo_submenu did not appear after waiting.", level="WARN", job_id=job_id)
            raise Exception("Formulário de guias (conteudo-submenu) não apareceu na tela.")

        # 7. Scrape Table Loop
        try:
            DataTable = scraper.driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/table[2]')
            linhas = DataTable.find_elements(By.TAG_NAME, "tr")
            scraper.log(f"Início Tabela: Encontradas {len(linhas)} linhas na tabela[2]", job_id=job_id)
            
            if len(linhas) <= 1:
                html = DataTable.get_attribute("outerHTML")
                scraper.log(f"HTML da Tabela Vazia: {html[:500]}...", job_id=job_id)
                scraper.log("Paciente sem guias para processar", job_id=job_id)
                return []
        except NoSuchElementException:
            scraper.log("Tabela 2 não encontrada. Paciente sem guias.", job_id=job_id)
            return []

        # Click Sort
        try:
            xpath_headers = '//*[@id="conteudo-submenu"]/table[2]//th | //*[@id="conteudo-submenu"]/table[2]//tr[1]/td | //*[@id="conteudo-submenu"]/table[2]//tr[2]/td'
            header_elems = scraper.driver.find_elements(By.XPATH, xpath_headers)
            clicked = False
            for el in header_elems:
                if "SOLICITA" in el.text.upper() or "DATA" in el.text.upper():
                    scraper.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                    links = el.find_elements(By.TAG_NAME, "a")
                    target = links[0] if links else el
                    
                    scraper.log(f"Clicando para classificar na coluna: {el.text}", job_id=job_id)
                    target.click()
                    time.sleep(2)
                    clicked = True
                    break
                    
            if clicked:
                # Re-find after first click (prevent Stale Element if POSTBACK occurred)
                header_elems = scraper.driver.find_elements(By.XPATH, xpath_headers)
                for el in header_elems:
                    if "SOLICITA" in el.text.upper() or "DATA" in el.text.upper():
                        links = el.find_elements(By.TAG_NAME, "a")
                        target = links[0] if links else el
                        target.click()
                        time.sleep(2)
                        scraper.log("Segundo clique (Decrescente) aplicado.", job_id=job_id)
                        break
            else:
                scraper.log("Aviso: Coluna SOLICITAÇÃO não encontrada para classificar.", level="WARN", job_id=job_id)
                
        except Exception as e:
            scraper.log(f"Warning: Falha ao classificar tabela: {e}", level="WARN", job_id=job_id)

        while True:
            try:
                # Re-fetch the table strictly to get the dynamic count
                DataTable = scraper.driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/table[2]')
                linhas = DataTable.find_elements(By.TAG_NAME, "tr")
                rows_to_process = len(linhas)
                scraper.log(f"Found {rows_to_process} rows in table", job_id=job_id)

                for idx in range(1, rows_to_process): 
                    try:
                        # Re-fetch table because DOM changes when we click "Voltar" or "Back"
                        DataTable = scraper.driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/table[2]')
                        row_xpath = f'//*[@id="conteudo-submenu"]/table[2]/tbody/tr[{idx+1}]'
                        
                        if not is_element_present(scraper.driver, By.XPATH, f'{row_xpath}/td[6]'):
                            continue

                        status_td = scraper.driver.find_element(By.XPATH, f'{row_xpath}/td[6]')
                        scraper.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", status_td)
                        
                        status_text = status_td.text.strip().upper()
                        scraper.log(f"Row {idx} Status: {status_text}", job_id=job_id)
                        
                        mapped_status = None
                        if "AUTORIZADO" in status_text or "LIBERAD" in status_text:
                            mapped_status = "Autorizado"
                        elif "ESTUDO" in status_text or "ANÁLISE" in status_text or "ANALISE" in status_text or "PENDENTE" in status_text:
                            mapped_status = "Em Estudo"
                        elif "NEGADO" in status_text:
                            mapped_status = "Negado"
                        elif "CANCEL" in status_text:
                            mapped_status = "Cancelado"
                            
                        if not mapped_status:
                            scraper.log(f"Row {idx}: Status não mapeado/ignorado '{status_text}'", job_id=job_id)
                            continue

                        date_element = scraper.driver.find_element(By.XPATH, f'{row_xpath}/td[1]')
                        date_text = date_element.text.strip()
                        
                        try:
                            guia_date = datetime.datetime.strptime(date_text, "%d/%m/%Y").date()
                        except:
                            guia_date = datetime.datetime.now().date()
                        
                        # Filter old (180 days per user request)
                        cutoff = datetime.datetime.now().date() - datetime.timedelta(days=180)
                        if guia_date < cutoff:
                            scraper.log(f"Date {date_text} too old. Stopping.", job_id=job_id)
                            # Close popup and return to base window
                            try:
                                scraper.driver.close()
                                scraper.driver.switch_to.window(scraper.driver.window_handles[0])
                            except:
                                pass
                            return collected_data

                        # Click details
                        try:
                            link_el = scraper.driver.find_element(By.XPATH, f'{row_xpath}/td[4]/a')
                            scraper.driver.execute_script("arguments[0].click();", link_el)
                            time.sleep(2)
                        except NoSuchElementException:
                            scraper.log(f"Row {idx} no details link, skipping.", job_id=job_id)
                            continue

                        # Extract Details
                        try:
                            err_el = scraper.driver.find_element(By.ID, "label_error_redeAtendPrestEspec")
                            if err_el.is_displayed() or "block" in (err_el.get_attribute("style") or ""):
                                scraper.log(f"Row {idx} access denied by system, skipping.", job_id=job_id)
                                try:
                                    scraper.driver.back()
                                    time.sleep(1)
                                except: pass
                                continue
                        except NoSuchElementException:
                            pass
                            
                        if is_element_present(scraper.driver, By.XPATH, '//*[@id="Button_Voltar"]'):
                            new_num_guia = ""
                            data_auth = ""
                            senha = ""
                            data_valid = ""
                            cod_terapia = ""
                            qtde_solic = "0"
                            qtde_aut = "0"

                            try:
                                new_num_guia = scraper.driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/form/table/tbody/tr[3]/td[2]').text
                            except: pass
                            
                            try:
                                data_auth = scraper.driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/form/table/tbody/tr[4]/td[4]').text
                            except: pass
                            
                            try:
                                senha = scraper.driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/form/table/tbody/tr[5]/td[2]').text
                            except: pass
                            
                            try:
                                data_valid_el = scraper.driver.find_element(By.XPATH, '//*[@id="CampoValidadeSenha"]')
                                if data_valid_el.is_displayed():
                                    data_valid = data_valid_el.text
                            except: pass

                            try:
                                cod_el = scraper.driver.find_elements(By.XPATH, '/html/body/div[1]/div[13]/div/table/tbody/tr[2]/td[3]/input')
                                if cod_el: cod_terapia = cod_el[0].get_attribute("value")
                                
                                qs_el = scraper.driver.find_elements(By.XPATH, '/html/body/div[1]/div[13]/div/table/tbody/tr[2]/td[5]')
                                if qs_el: qtde_solic = qs_el[0].text.strip()
                                
                                qa_el = scraper.driver.find_elements(By.XPATH, '/html/body/div[1]/div[13]/div/table/tbody/tr[2]/td[6]')
                                if qa_el: qtde_aut = qa_el[0].text.strip()
                            except Exception as therapy_err:
                                scraper.log(f"Warning: Could not extract therapy details: {therapy_err}", level="WARN", job_id=job_id)
                            
                            guia_data = {
                                "carteirinha": carteirinha,
                                "numero_guia": new_num_guia,
                                "data_autorizacao": data_auth,
                                "senha": senha,
                                "validade_senha": data_valid,
                                "codigo_terapia": cod_terapia,
                                "qtde_solicitada": qtde_solic,
                                "qtde_autorizada": qtde_aut,
                                "status_guia": mapped_status # Used by dispatcher
                            }
                            collected_data.append(guia_data)
                            scraper.log(f"Scraped Guia {new_num_guia} ({mapped_status})", job_id=job_id)
                            
                            try:
                                scraper.driver.find_element(By.XPATH, '//*[@id="Button_Voltar"]').click()
                                time.sleep(1)
                            except:
                                scraper.driver.back()
                                time.sleep(1)
                        else:
                            scraper.driver.back()
                            time.sleep(1)

                    except Exception as row_e:
                        scraper.log(f"Row error: {row_e}", level="ERROR", job_id=job_id)
                        continue

                # Pagination
                try:
                    next_links = scraper.driver.find_elements(By.LINK_TEXT, "Próxima")
                    if len(next_links) == 0:
                        break # No more pages
                    scraper.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_links[0])
                    next_links[0].click()
                    time.sleep(2)
                except Exception:
                    break

            except Exception as table_e:
                scraper.log(f"Table Loop Error ou Tabela não encontrada: {table_e}", level="ERROR", job_id=job_id)
                raise Exception(f"Falha ao ler tabela de guias: {table_e}")

    finally:
        # Ensure cleanup of popup
        try:
            if len(scraper.driver.window_handles) > 1:
                scraper.driver.close()
                scraper.driver.switch_to.window(scraper.driver.window_handles[0])
        except: pass

    return collected_data
