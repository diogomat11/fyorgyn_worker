import time
import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def funccarteira(carteirinha):
    import re
    parts = re.split(r'[.-]', carteirinha)
    if len(parts) == 5:
        return parts[0], parts[1], parts[2], parts[3], parts[4]
    return parts[0] if len(parts) > 0 else "", "", "", "", ""

def execute(scraper, job_data):
    """
    Executa consulta de guias (Rotina 1) para Unimed Goiania.
    """
    job_id = job_data.get("job_id")
    carteirinha = job_data.get("carteirinha")
    carteirinha_db_id = job_data.get("carteirinha_id")
    
    scraper.log(f"Processando carteirinha: {carteirinha}", job_id=job_id, carteirinha_id=carteirinha_db_id)
    
    handles = scraper.driver.window_handles
    if len(handles) > 1:
        scraper.driver.switch_to.window(handles[0])

    # Helper to check element presence
    def is_element_present(by, value):
        try:
            scraper.driver.find_element(by, value)
            return True
        except NoSuchElementException:
            return False

    # Sort by Date (click header twice)
    scraper.log("Sorting table by date (Clicking header twice)...", job_id=job_id, carteirinha_id=carteirinha_db_id)
    try:
        header_xpath = '//*[@id="conteudo-submenu"]/table[2]/tbody/tr[1]/td[1]/a'
        if is_element_present(By.XPATH, header_xpath):
            scraper.driver.find_element(By.XPATH, header_xpath).click()
            scraper.log("Clicked header once. Waiting 4s...", job_id=job_id, carteirinha_id=carteirinha_db_id)
            time.sleep(4)
            
            scraper.driver.find_element(By.XPATH, header_xpath).click()
            scraper.log("Clicked header twice. Waiting 2s...", job_id=job_id, carteirinha_id=carteirinha_db_id)
            time.sleep(2)
        else:
            scraper.log("Sort header not found. Proceeding sem explicit sort.", level="WARNING", job_id=job_id, carteirinha_id=carteirinha_db_id)
    except Exception as sort_e:
        scraper.log(f"Error while sorting table: {sort_e}", level="ERROR", job_id=job_id, carteirinha_id=carteirinha_db_id)

    scraper.log("Starting scraping loop...", job_id=job_id, carteirinha_id=carteirinha_db_id)
    try:
        WebDriverWait(scraper.driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="cadastro_biometria"]/div/div[2]/span')))
        new_exame = scraper.driver.find_element(By.XPATH, '//*[@id="cadastro_biometria"]/div/div[2]/span')
        new_exame.click()
        scraper.log("Clicked 'new_exame'", job_id=job_id, carteirinha_id=carteirinha_db_id)
    except Exception as e:
        scraper.log(f"Failed to find/click 'new_exame': {str(e)}", level="ERROR", job_id=job_id, carteirinha_id=carteirinha_db_id)
        raise e

    time.sleep(3)
    
    if len(scraper.driver.window_handles) > 1:
        scraper.driver.switch_to.window(scraper.driver.window_handles[-1])
        scraper.driver.maximize_window()
        scraper.log("Switched to popup window", job_id=job_id, carteirinha_id=carteirinha_db_id)
    else:
        scraper.log("Popup window did not open!", level="ERROR", job_id=job_id, carteirinha_id=carteirinha_db_id)
        raise Exception("Popup window not found")
    
    x1, x2, x3, x4, x5 = funccarteira(carteirinha)
    cartCompleto = x1 + x2 + x3 + x4 + x5      
    cartaoParcial = x2 + x3 + x4 + x5
    
    scraper.log("Filling form...", job_id=job_id, carteirinha_id=carteirinha_db_id)
    element7 = scraper.driver.find_element(By.NAME, 'nr_via')
    element6 = scraper.driver.find_element(By.NAME, 'DS_CARTAO')
    element3 = scraper.driver.find_element(By.NAME, 'CD_DEPENDENCIA')
    
    scraper.driver.execute_script("arguments[0].setAttribute('type', 'text');", element7)
    element7.clear()
    element7.send_keys(cartCompleto)
    
    scraper.driver.execute_script("arguments[0].setAttribute('type', 'text');", element6)
    element6.clear()
    element6.send_keys(cartaoParcial)
    
    scraper.driver.execute_script("arguments[0].setAttribute('type', 'text');", element3)
    element3.clear()
    element3.send_keys(x3)
    
    if x1 != "0064":
         scraper.log(f"Carteirinha prefix {x1} != 0064. Checking Validade...", job_id=job_id, carteirinha_id=carteirinha_db_id)
         if len(scraper.driver.find_elements(By.XPATH, '//*[@id="Button_Consulta"]')) > 0:
              scraper.driver.find_element(By.XPATH, '//*[@id="Button_Consulta"]').click()
              time.sleep(2)
    
    scraper.log("Waiting for Results Table...", job_id=job_id, carteirinha_id=carteirinha_db_id)
    try:
        WebDriverWait(scraper.driver, 20).until(EC.presence_of_element_located((By.XPATH, '//*[@id="s_NR_GUIA"]')))
    except TimeoutException:
         scraper.log("Timeout waiting for results table. Maybe no guias or connection error.", level="WARNING", job_id=job_id, carteirinha_id=carteirinha_db_id)
         scraper.driver.close()
         scraper.driver.switch_to.window(scraper.driver.window_handles[0])
         return []

    collected_data = [] 

    while True:
        try:
            DataTable = scraper.driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/table[2]')
            linhas = DataTable.find_elements(By.TAG_NAME, "tr")
            rows_to_process = len(linhas)
            scraper.log(f"Found {rows_to_process} rows on page.", job_id=job_id, carteirinha_id=carteirinha_db_id)
            
            for idx in range(1, rows_to_process - 1):
                try:
                    # Robustez Adicionada (Prevenção de Stale Element em Tabelas Pagadas)
                    DataTable = scraper.driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/table[2]')
                    row_xpath = f'//*[@id="conteudo-submenu"]/table[2]/tbody/tr[{idx+1}]'
                    
                    if not is_element_present(By.XPATH, f'{row_xpath}/td[6]/span'):
                        continue
                        
                    status_span = scraper.driver.find_element(By.XPATH, f'{row_xpath}/td[6]/span')
                    scraper.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", status_span)
                    
                    if status_span.text == "Autorizado":
                        date_element = scraper.driver.find_element(By.XPATH, f'{row_xpath}/td[1]')
                        date_text = date_element.text.strip()
                        
                        try:
                            guia_date = datetime.datetime.strptime(date_text, "%d/%m/%Y").date()
                        except:
                            guia_date = datetime.datetime.now().date()
                        
                        cutoff_date = datetime.datetime.now().date() - datetime.timedelta(days=270)
                        if guia_date < cutoff_date:
                            scraper.log(f"Guia date {date_text} is older than limit. Stopping.", job_id=job_id, carteirinha_id=carteirinha_db_id)
                            scraper.driver.close()
                            scraper.driver.switch_to.window(scraper.driver.window_handles[0])
                            return collected_data

                        link_element = scraper.driver.find_element(By.XPATH, f'{row_xpath}/td[4]/a')
                        link_element.click()
                        time.sleep(2)
                        
                        try:
                            if is_element_present(By.XPATH, '//*[@id="Button_Voltar"]'):
                                new_num_guia = scraper.driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/form/table/tbody/tr[3]/td[2]').text
                                data_auth = scraper.driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/form/table/tbody/tr[4]/td[4]').text
                                senha = scraper.driver.find_element(By.XPATH, '//*[@id="conteudo-submenu"]/form/table/tbody/tr[5]/td[2]').text
                                data_valid = scraper.driver.find_element(By.XPATH, '//*[@id="CampoValidadeSenha"]').text
                                cod_terapia = scraper.driver.find_element(By.XPATH, '/html/body/div[1]/div[13]/div/table/tbody/tr[2]/td[3]/input').get_attribute("value")
                                qtde_solic = scraper.driver.find_element(By.XPATH, '/html/body/div[1]/div[13]/div/table/tbody/tr[2]/td[5]').text.strip()
                                qtde_aut = scraper.driver.find_element(By.XPATH, '/html/body/div[1]/div[13]/div/table/tbody/tr[2]/td[6]').text.strip()
                                
                                guia_data = {
                                    "numero_guia": new_num_guia,
                                    "data_autorizacao": data_auth,
                                    "senha": senha,
                                    "validade_senha": data_valid,
                                    "codigo_terapia": cod_terapia,
                                    "qtde_solicitada": qtde_solic,
                                    "qtde_autorizada": qtde_aut,
                                    "status_guia": "Autorizado"
                                }
                                collected_data.append(guia_data)
                                scraper.log(f"Scraped Guia {new_num_guia}", job_id=job_id, carteirinha_id=carteirinha_db_id)
                                
                                scraper.driver.find_element(By.XPATH, '//*[@id="Button_Voltar"]').click()
                                time.sleep(1)
                            else:
                                 scraper.log("Detail view not loaded correctly.", level="WARNING", job_id=job_id, carteirinha_id=carteirinha_db_id)
                                 scraper.driver.back()
                        except Exception as inner_e:
                            scraper.log(f"Error extracting details: {inner_e}", level="ERROR", job_id=job_id, carteirinha_id=carteirinha_db_id)
                            try:
                                scraper.driver.execute_script("window.history.go(-1)")
                            except: pass

                except Exception as row_e:
                    scraper.log(f"Error processing row {idx}: {row_e}", level="ERROR", job_id=job_id, carteirinha_id=carteirinha_db_id)
                    continue

            # Pagination (Robust)
            try:
                 next_links = scraper.driver.find_elements(By.LINK_TEXT, "Próxima")
                 if not next_links:
                     break # No more pages
                 scraper.log("Navigating to next page...", job_id=job_id, carteirinha_id=carteirinha_db_id)
                 scraper.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_links[0])
                 next_links[0].click()
                 time.sleep(2)
            except Exception:
                scraper.log("No more pages.", job_id=job_id, carteirinha_id=carteirinha_db_id)
                break

        except Exception as table_e:
            scraper.log(f"Error validating table loop: {table_e}", level="ERROR", job_id=job_id, carteirinha_id=carteirinha_db_id)
            break
    
    scraper.driver.close()
    scraper.driver.switch_to.window(scraper.driver.window_handles[0])
    
    return collected_data
