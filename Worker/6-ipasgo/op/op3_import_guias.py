from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta, timezone
import time
import os
import sys

# ── Isolate Environment (Fix Crosstalk) ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)]
if sys.path[0] != _mod_root:
    sys.path.insert(0, _mod_root)


from config.settings import get_runtime_settings
from config.constants import (
    DEFAULT_TIMEOUT,
    LONG_TIMEOUT,
    X_LOCALIZAR_MENU_FATURAMENTO,
    X_LOCALIZAR_NOTY_CONTAINER,
    X_LOCALIZAR_NOTY_FECHAR,
    X_LOCALIZAR_NOTY_MODAL,
    X_LOCALIZAR_DATA_INICIO,
    X_LOCALIZAR_DATA_FIM,
    X_LOCALIZAR_BTN_PESQUISAR,
    X_LOCALIZAR_TABELA_CONTAINER,
    X_LOCALIZAR_ROW_PACIENTE_FMT,
    X_LOCALIZAR_ROW_GUIA_FMT,
    X_LOCALIZAR_ROW_COD_BENEF_FMT,
    X_LOCALIZAR_ROW_SENHA_FMT,
    X_LOCALIZAR_ROW_SITUACAO_FMT,
    X_LOCALIZAR_ROW_DATA_SOL_FMT,
    X_LOCALIZAR_ROW_DATA_AUT_FMT,
    X_LOCALIZAR_ROW_COD_PROC_FMT,
    X_LOCALIZAR_ROW_BTN_DET_FMT,
    X_LOCALIZAR_DET_QT_SOL,
    X_LOCALIZAR_DET_QT_AUT,
    X_LOCALIZAR_DET_MODAL_FECHAR,
    X_LOCALIZAR_BTN_NEXT,
    X_LOCALIZAR_FIRST_GUIA,
    X_ALERT_AVISO_BANNER,
    X_LOADING_GLOBAL,
    X_ALERT_CLOSE,
    X_LOADING_OVERLAY,
    X_ALERT_CLOSE_STRONG,
)
# Supabase import removido para rodar 100% no Local DB.

def _find_any_xpath(wait, candidates):
    last_err = None
    for xp in candidates:
        try:
            return wait.until(EC.presence_of_element_located((By.XPATH, xp)))
        except Exception as e:
            last_err = e
    raise last_err or Exception("nenhum xpath encontrado")

def find_with_frames(driver, wait, candidates):
    try:
        return _find_any_xpath(wait, candidates)
    except Exception:
        pass
    # No FacPlan/Angular não usamos iframes para os dados principais.
    # Evitamos o for-loop de iframes para não multiplicar o timeout de forma absurda.
    for xp in candidates:
        elems = driver.find_elements(By.XPATH, xp)
        for el in elems:
            if el.is_displayed() and el.is_enabled():
                return el
    raise Exception("Elemento não encontrado")

def wait_xpath(driver, xpath, timeout=DEFAULT_TIMEOUT):
    try:
        # Respeita estritamente o timeout passado para não travar a rotina inteira
        wait = WebDriverWait(driver, timeout)
        return find_with_frames(driver, wait, [xpath])
    except Exception:
        return None

def _close_alert_if_present(driver):
    try:
        candidates = ['/html/body/div[5]/div/div/div[2]/button', 'button-1']
        for c in candidates:
            try:
                btn = driver.find_element(By.XPATH, c) if '/' in c else driver.find_element(By.ID, c)
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1)
                    break
            except: 
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

def normalizar_data(texto):
    try:
        return datetime.strptime(texto[:10], "%d/%m/%Y")
    except Exception:
        return None

def calcular_validade(data_autorizacao):
    if data_autorizacao:
        return data_autorizacao + timedelta(days=45)
    return None

def normalizar_codigo(c):
    try:
        s = str(c).strip()
        s = s[-12:] if len(s) >= 12 else s
        s = s.replace(".", "").replace("-", "")
        return s
    except Exception:
        return ""

def _page_is_loading(driver):
    try:
        def check_vis(xpath):
            elems = driver.find_elements(By.XPATH, xpath)
            for e in elems:
                try:
                    if e.is_displayed(): return True
                except: pass
            return False
        
        return check_vis(X_ALERT_AVISO_BANNER) or check_vis(X_LOADING_GLOBAL) or check_vis(X_LOADING_OVERLAY)
    except Exception:
        return False

def _wait_page_ready(driver, wait_seconds=3):
    end_time = time.time() + wait_seconds
    while time.time() < end_time:
        if not _page_is_loading(driver):
            break
        time.sleep(0.5)

def _first_guide_text(driver):
    try:
        el = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, X_LOCALIZAR_FIRST_GUIA)))
        return el.text
    except Exception:
        return ""

def _close_alert_if_present(driver):
    try:
        banner = driver.find_elements(By.XPATH, X_ALERT_AVISO_BANNER)
        if banner:
            btn = driver.find_elements(By.XPATH, X_ALERT_CLOSE)
            if not btn:
                btn = driver.find_elements(By.XPATH, X_ALERT_CLOSE_STRONG)
            if btn:
                try:
                    btn[0].click()
                except Exception:
                    driver.execute_script("arguments[0].click();", btn[0])
    except Exception:
        pass

def _wait_spinner_until_gone(driver, max_checks=3, step_seconds=3, logger=None):
    for attempt in range(1, max_checks + 1):
        try:
            elems = driver.find_elements(By.XPATH, X_LOADING_OVERLAY)
            is_visible = False
            for e in elems:
                try:
                    if e.is_displayed():
                        is_visible = True
                        break
                except:
                    pass
            
            if not is_visible:
                if logger: logger.debug("spinner não visível")
                return True
        except Exception:
            pass
            
        if logger: logger.debug(f"spinner visível (tentativa {attempt}/{max_checks})")
        time.sleep(step_seconds)
    
    return False

def _is_row_complete(row):
    req = [row.get("guia"), row.get("paciente"), row.get("status_guia"), row.get("codigo_terapia")]
    return all(bool(x and str(x).strip()) for x in req)

def should_process_page(pagina_idx, last_page):
    try:
        if last_page is None:
            return True
        return int(pagina_idx) > int(last_page)
    except Exception:
        return True

def _formatar_ddmmyyyy(s):
    try:
        return datetime.strptime(str(s).strip(), "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        try:
            # já em dd/mm/yyyy
            return datetime.strptime(str(s).strip(), "%d/%m/%Y").strftime("%d/%m/%Y")
        except Exception:
            return str(s).strip()

def _save_rows_local(rows, logger):
    try:
        from database import SessionLocal
        from models import BaseGuia, Carteirinha
        db_session = SessionLocal()
        try:
            for row_data in rows:
                guia_record = db_session.query(BaseGuia).filter(
                    BaseGuia.guia == str(row_data["guia"])
                ).first()
                if not guia_record:
                    guia_record = BaseGuia(guia=str(row_data["guia"]))
                    db_session.add(guia_record)
                
                guia_record.senha = row_data["senha"]
                guia_record.status_guia = row_data["status_guia"]
                guia_record.codigo_terapia = row_data["codigo_terapia"]
                try:
                    guia_record.qtde_solicitada = int(str(row_data["qtde_solicitada"]).strip()) if row_data["qtde_solicitada"] and str(row_data["qtde_solicitada"]).strip() else 0
                    guia_record.sessoes_autorizadas = int(str(row_data["sessoes_autorizadas"]).strip()) if row_data["sessoes_autorizadas"] and str(row_data["sessoes_autorizadas"]).strip() else 0
                except ValueError:
                    pass
                    
                if row_data.get("data_autorizacao"):
                    try:
                        dt_str = str(row_data["data_autorizacao"])[:10]
                        guia_record.data_autorizacao = datetime.strptime(dt_str, "%Y-%m-%d").date()
                    except ValueError:
                        pass
                if row_data.get("validade"):
                    try:
                        dt_str = str(row_data["validade"])[:10]
                        guia_record.validade = datetime.strptime(dt_str, "%Y-%m-%d").date()
                    except ValueError:
                        pass
                
                guia_record.id_convenio = 6 # IPASGO
                if row_data.get("codigo_beneficiario"):
                    guia_record.codigo_beneficiario = row_data["codigo_beneficiario"]
                    cart = db_session.query(Carteirinha).filter(Carteirinha.codigo_beneficiario == row_data["codigo_beneficiario"]).first()
                    if cart:
                        guia_record.carteirinha_id = cart.id

            db_session.commit()
            if logger:
                logger.info(f"Salvos {len(rows)} registros em base_guias locais (Worker DB)")
        finally:
            db_session.close()
    except Exception as db_err:
        if logger:
            logger.error(f"Erro ao salvar base_guias locais: {db_err}")

def run(scraper: 'BaseScraper', job_data: dict) -> list[dict]:
    driver = scraper.driver
    job_id = job_data.get("job_id") or job_data.get("id")
    if not job_id:
        import uuid
        job_id = f"local_{uuid.uuid4().hex[:6]}"
    
    # Parse params if it's a JSON string
    import json
    params = job_data.get("params", {})
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            params = {}
            
    start_date = job_data.get("start_date") or params.get("start_date")
    end_date = job_data.get("end_date") or params.get("end_date")
    carteira = job_data.get("carteira") or params.get("carteira")
    numero_guia = job_data.get("numero_guia") or params.get("numero_guia")
    
    settings = {}
    
    class _LoggerWrapper:
        def info(self, msg): scraper.log(msg, level="INFO", job_id=job_id)
        def error(self, msg): scraper.log(msg, level="ERROR", job_id=job_id)
        def warning(self, msg): scraper.log(msg, level="WARN", job_id=job_id)
        def debug(self, msg): scraper.log(msg, level="DEBUG", job_id=job_id)
    logger = _LoggerWrapper()

    runtime = get_runtime_settings()
    url = runtime.get("IMPORT_GUIAS_URL")
    if not url:
        logger.error("IMPORT_GUIAS_URL não definida")
        return []

    # Ensure Session logic and switch to Facplan tab if already opened by op0_login
    facplan_found = False
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "facplan" in driver.current_url.lower() or ("facplan" in url.lower() and url.lower() in driver.current_url.lower()):
            logger.info("Aba do Facplan localizada. Mantendo foco.")
            facplan_found = True
            break
            
    if not facplan_found:
        driver.get(url)
        time.sleep(2)
    else:
        if url.lower() not in driver.current_url.lower() and "importar-guias" not in driver.current_url.lower() and "localizar" not in driver.current_url.lower():
            logger.info("Navegando para aba alvo dentro do FacPlan.")
            driver.get(url)
            time.sleep(2)
        
    if "login" in driver.current_url.lower() or "ipasgo" in driver.current_url.lower() and "facplan" not in getattr(driver, "title", "").lower() and "login" in getattr(driver, "title", "").lower():
        logger.info("Sessão ausente ou expirada. Iniciando fluxo op0_login...")
        scraper.login()
        time.sleep(2)
        facplan_found = False
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            if "facplan" in driver.current_url.lower():
                facplan_found = True
                break
        if not facplan_found:
            driver.get(url)
        time.sleep(2)
        
    logger.info("Acesso à URL da rotina confirmado. Avançando para carregamento (Milestone 2)...")

    page_loaded = False
    for attempt_load in range(3):
        logger.info(f"Aguardando formulário de pesquisa (Tentativa {attempt_load+1}/3)...")
        
        logger.info("Procurando notificação (button-1)...")
        for _ in range(3):
            try:
                btn_close = wait_xpath(driver, '//*[@id="button-1"]', 1)
                if btn_close and btn_close.is_displayed():
                    logger.info("Notificação encontrada! Clicando para fechar...")
                    driver.execute_script("arguments[0].click();", btn_close)
                    time.sleep(1)
                    break
            except:
                pass
            time.sleep(1)
            
        _close_alert_if_present(driver)
        
        # 1. Localizar todos os possiveis campos antes de injetar valores (usando locators atualizados do op5)
        logger.info("Verificando carregamento dos inputs vitais...")
        campo_ini = wait_xpath(driver, '//input[contains(@data-bind, "idIni")]', 2)
        campo_fim = wait_xpath(driver, '//input[contains(@data-bind, "idFim")]', 1)
        campo_cart = wait_xpath(driver, '/html/body/main/div[2]/div[1]/div[2]/div[1]/div[1]/div[3]/input | //*[@id="localizarprocedimentos"]//input[contains(@data-bind, "arteira")]', 1)
        campo_guia = wait_xpath(driver, '/html/body/main/div[2]/div[1]/div[2]/div[1]/div[2]/input-text-search/div/div/div/input | //*[@id="localizarprocedimentos"]//input[contains(@data-bind, "umeroGuiaPrestador")]', 1)

        if campo_ini or campo_guia or campo_cart:
            page_loaded = True
            break
        else:
            logger.warning("Elementos vitais não completaram carga. Acionando refresh da aba (Milestone 2)...")
            try: driver.refresh()
            except: pass
            time.sleep(4)

    if not page_loaded:
        logger.error("Falha permanente ao carregar página de procedimentos após refreshes. Abortando para acionar Milestone 1.")
        raise Exception("Erro: Página de Localizar Procedimentos não carregou (Timeout Milestone 2).")

    wait_short = WebDriverWait(driver, 3)

    # 2. Aplicar Hierarquia de Regras Mutuamente Exclusivas do Usuario
    try:
        if numero_guia:
            logger.info(f"Filtro ativo por Numero de Guia ({numero_guia}). Apagando demais campos.")
            if campo_cart:
                try:
                    X_REMOVE_CARTEIRA = "/html/body/main/div[2]/div[1]/div[2]/div[1]/div[2]/beneficiario/div/div/div/div/div/div/div/a"
                    removes = driver.find_elements(By.XPATH, X_REMOVE_CARTEIRA)
                    if removes:
                        for r in removes:
                            if r.is_displayed():
                                r.click()
                                time.sleep(1)
                except: pass
                campo_cart.clear()
            if campo_ini: campo_ini.clear()
            if campo_fim: campo_fim.clear()
            
            if campo_guia:
                campo_guia.clear()
                time.sleep(0.2)
                campo_guia.send_keys(str(numero_guia))
                
        elif carteira:
            logger.info(f"Filtro ativo por Carteira ({carteira}). Apagando campo guia.")
            if campo_guia: campo_guia.clear()
            if campo_cart:
                try:
                    X_REMOVE_CARTEIRA = "/html/body/main/div[2]/div[1]/div[2]/div[1]/div[2]/beneficiario/div/div/div/div/div/div/div/a"
                    removes = driver.find_elements(By.XPATH, X_REMOVE_CARTEIRA)
                    if removes:
                        for r in removes:
                            if r.is_displayed():
                                r.click()
                                time.sleep(1)
                except: pass
                campo_cart.clear()
                time.sleep(0.2)
                campo_cart.send_keys(str(carteira))
                
            if start_date and end_date and campo_ini and campo_fim:
                logger.info(f"Intervalo de datas da carteira ({start_date} ate {end_date}).")
                campo_ini.clear()
                campo_fim.clear()
                time.sleep(0.1)
                campo_ini.send_keys(_formatar_ddmmyyyy(start_date))
                campo_fim.send_keys(_formatar_ddmmyyyy(end_date))
                
        elif start_date and end_date:
            logger.info(f"Filtro ativo apenas por Datas ({start_date} a {end_date}). Apagando guia e carteira.")
            if campo_guia: campo_guia.clear()
            if campo_cart:
                try:
                    X_REMOVE_CARTEIRA = "/html/body/main/div[2]/div[1]/div[2]/div[1]/div[2]/beneficiario/div/div/div/div/div/div/div/a"
                    removes = driver.find_elements(By.XPATH, X_REMOVE_CARTEIRA)
                    if removes:
                        for r in removes:
                            if r.is_displayed():
                                r.click()
                                time.sleep(1)
                except: pass
                campo_cart.clear()
            
            if campo_ini and campo_fim:
                campo_ini.clear()
                campo_fim.clear()
                time.sleep(0.1)
                campo_ini.send_keys(_formatar_ddmmyyyy(start_date))
                campo_fim.send_keys(_formatar_ddmmyyyy(end_date))
        else:
            logger.info("Nenhum filtro de busca fornecido. Clicando em localizar via listagem default...")
            
    except Exception as e:
        logger.error(f"Erro ao limpar campos e injetar parametros: {e}")

    # Pressionar Enter em um dos campos como fallback ou seguir para o click no botão
    if start_date and end_date and campo_fim:
        try:
            campo_fim.send_keys(Keys.ENTER)
        except Exception:
            pass
    time.sleep(1)

    try:
        # Locator atualizado com ID explícito
        xp_btn_pesquisa_op4 = '//*[@id="localizar-procedimentos-btn"]'
        btn_buscar = wait_xpath(driver, xp_btn_pesquisa_op4, 10)
        if not btn_buscar:
            btn_buscar = wait_xpath(driver, X_LOCALIZAR_BTN_PESQUISAR, 5)
            
        if not btn_buscar:
            logger.error("botão pesquisar não encontrado (timeout excedido). Página ou Facplan pode não ter carregado.")
            return []
            
        logger.info("Clicando no botão de busca...")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_buscar)
        time.sleep(0.5)
        try:
            btn_buscar.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn_buscar)
    except Exception as e:
        logger.error(f"Erro fatal ao tentar localizar ou clicar no botão buscar: {e}")
        return []
        
    time.sleep(5)
    _wait_spinner_until_gone(driver, max_checks=5, step_seconds=5, logger=logger)
    time.sleep(1)
    first_el = wait_xpath(driver, X_LOCALIZAR_FIRST_GUIA, 10)
    if first_el:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", first_el)
        except Exception:
            driver.execute_script("arguments[0].scrollIntoView(true);", first_el)
        time.sleep(0.5)
        logger.info("focada a primeira linha da tabela")

    continuar = True
    guia_primeira_pagina = None
    rows_total = []
    pagina_idx = 1
    
    # Retomada Local (Fallback do Dispatcher)
    last_page = 0
    import os
    import json
    state_file = f"base_guias/job_{job_id}_state.json"
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                state_data = json.load(f)
                last_page = state_data.get("ultima_pagina", 0)
                logger.info(f"Recuperação de Erro: Lida ultima_pagina={last_page} do arquivo local.")
        except Exception as e:
            logger.warning(f"Erro ao ler arquivo de estado da página: {e}")
            
    while continuar:
        # aguardas spinner/alert antes de iniciar leitura da página
        _wait_spinner_until_gone(driver, max_checks=3, step_seconds=5, logger=logger)
        time.sleep(1)
        _close_alert_if_present(driver)
        _wait_table_ready(driver, 10)
        tabela = wait_xpath(driver, X_LOCALIZAR_TABELA_CONTAINER)
        if not tabela:
            logger.error("tabela de resultados não encontrada (constants.py)")
            break
        logger.info(f"pagina atual {pagina_idx}, ultima logada {last_page}")
        logger.info("iniciando coleta de linhas da página atual")
        if last_page is not None and pagina_idx <= last_page:
            logger.info(f"Skip: página {pagina_idx} já processada (última={last_page}). Avançando...")
            prev_first = _first_guide_text(driver)
            
            advanced = False
            attempts = 0
            while attempts < 3:
                # 1. Obter o número da página atual na DOM antes do clique
                current_page_str = "0"
                try:
                    active_li = driver.find_elements(By.XPATH, '//li[contains(@class, "active")]/a/span')
                    if active_li:
                        current_page_str = active_li[0].text.strip()
                except Exception:
                    pass

                if not click_next_page(driver, logger):
                    logger.warning("Skip: click_next_page retornou False")
                
                time.sleep(1.5)
                _wait_spinner_until_gone(driver, max_checks=3, step_seconds=3)
                time.sleep(0.5)
                _close_alert_if_present(driver)
                
                new_first = _first_guide_text(driver)
                next_page_str = current_page_str
                try:
                    active_li = driver.find_elements(By.XPATH, '//li[contains(@class, "active")]/a/span')
                    if active_li:
                        next_page_str = active_li[0].text.strip()
                except Exception:
                    pass

                # 3. Considera avanço real se o Número da aba mudou no Angular OU o text do primeiro item mudou
                if (next_page_str != current_page_str) or (new_first and (not prev_first or new_first != prev_first)):
                    advanced = True
                    break
                
                logger.warning(f"Skip: página não mudou (Angular ativo={next_page_str}). Retentando {attempts+1}/3...")
                time.sleep(1.0)
                attempts += 1
            
            if not advanced:
                logger.error("Skip: Falha crítica - não foi possível avançar de página após 3 tentativas. Abortando.")
                break 
            
            pagina_idx += 1
            continue
        page_rows = []
        i = 1
        misses = 0
        # Encontre todos os 'div' filhos diretos do conteudo da tabela e itere sobre eles.
        row_xpath_base = '//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]/div'
        try:
            guias_rows = driver.find_elements(By.XPATH, row_xpath_base)
            max_rows = len(guias_rows)
            if logger:
                logger.info(f"MainLoop: Estrutura da tabela contem {max_rows} blocos DOM na página {pagina_idx}")
            
            # We iterate through all detected sibling divs perfectly, 
            # skipping any purely layout/spacing wrappers without incrementing any dangerous "misses" boundary.
            for i in range(1, max_rows + 1):
                try:
                    # Ignorando checks prematuros no container-pai para evitar falha silenciosa
                    # por StaleElementReference caso a tela se redesenhe ao fechar modais.
                    row_base = f"{row_xpath_base}[{i}]"
                
                    xp_paciente = X_LOCALIZAR_ROW_PACIENTE_FMT.format(i=i)
                    xp_guia = X_LOCALIZAR_ROW_GUIA_FMT.format(i=i)
                    xp_benef = X_LOCALIZAR_ROW_COD_BENEF_FMT.format(i=i)
                    xp_senha = X_LOCALIZAR_ROW_SENHA_FMT.format(i=i)
                    xp_situacao = X_LOCALIZAR_ROW_SITUACAO_FMT.format(i=i)
                    xp_data_sol = X_LOCALIZAR_ROW_DATA_SOL_FMT.format(i=i)
                    xp_data_aut = X_LOCALIZAR_ROW_DATA_AUT_FMT.format(i=i)
                    xp_cod_proc = X_LOCALIZAR_ROW_COD_PROC_FMT.format(i=i)
                    xp_btn_det = X_LOCALIZAR_ROW_BTN_DET_FMT.format(i=i)

                    # Como já validamos que há texto denso nesta `div`, os elementos DEVEM existir aqui. 
                    # Portanto, timeouts mínimos de 0.5s são suficientes.
                    guia_el = wait_xpath(driver, xp_guia, 0.5)
                    paciente_el = wait_xpath(driver, xp_paciente, 0.5)
                    benef_el = wait_xpath(driver, xp_benef, 0.5)
                    senha_el = wait_xpath(driver, xp_senha, 0.5)
                    situacao_el = wait_xpath(driver, xp_situacao, 0.5)
                
                    if not guia_el and not paciente_el:
                        continue
                    
                    elif not all([guia_el, paciente_el, senha_el, situacao_el]):
                        if logger:
                            logger.warning(f"linha {i}: parcialmente incompleta (layout quebrado?)")
                        continue
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", guia_el)
                    except Exception:
                        driver.execute_script("arguments[0].scrollIntoView(true);", guia_el)
                    time.sleep(0.3)

                    paciente = paciente_el.text
                    numero_guia = guia_el.text
                
                    codigo_beneficiario = benef_el.text if benef_el else ""
                
                    senha = senha_el.text
                    situacao = situacao_el.text

                    data_sol_el = wait_xpath(driver, xp_data_sol, 2)
                    data_aut_el = wait_xpath(driver, xp_data_aut, 2)
                    data_solicitacao = normalizar_data(data_sol_el.text) if data_sol_el else None
                    data_autorizacao = normalizar_data(data_aut_el.text) if data_aut_el else None
                    if situacao and (situacao.upper() in ["NEGADO", "CANCELADO"] or "ESTUDO" in situacao.upper()):
                        data_autorizacao = None
                    data_validade = calcular_validade(data_autorizacao)

                    cod_proc_el = wait_xpath(driver, xp_cod_proc, 2)
                    codigo_proc_bruto = cod_proc_el.text if cod_proc_el else ""
                    codigo_proc = normalizar_codigo(codigo_proc_bruto)

                    try:
                        if logger:
                            logger.info(f"Detalhes: tentando clicar no botão da linha {i}")
                        _close_alert_if_present(driver)
                        btn_det_clickable = None
                        try:
                            btn_det_clickable = WebDriverWait(driver, DEFAULT_TIMEOUT).until(
                                EC.element_to_be_clickable((By.XPATH, xp_btn_det))
                            )
                        except Exception:
                            btn_det_clickable = wait_xpath(driver, xp_btn_det, 2)
                        if not btn_det_clickable:
                            if logger:
                                logger.warning(f"Detalhes: botão da linha {i} não encontrado")
                            raise Exception("botão detalhe não encontrado")
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_det_clickable)
                        try:
                            btn_det_clickable.click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", btn_det_clickable)
                        _wait_spinner_until_gone(driver, max_checks=2, step_seconds=0.5, logger=logger)
                        time.sleep(1)
                        qt_sol = ""
                        qt_aut = ""
                        for _ in range(3):
                            qt_sol_el = wait_xpath(driver, X_LOCALIZAR_DET_QT_SOL, 3)
                            qt_aut_el = wait_xpath(driver, X_LOCALIZAR_DET_QT_AUT, 3)
                            qt_sol = qt_sol_el.text if qt_sol_el and qt_sol_el.text else qt_sol
                            qt_aut = qt_aut_el.text if qt_aut_el and qt_aut_el.text else qt_aut
                            if qt_sol:
                                break
                            time.sleep(1)
                    except Exception:
                        if logger:
                            logger.warning(f"Detalhes: falha ao abrir modal na linha {i}")
                        qt_sol = qt_aut = ""
                    finally:
                        if logger:
                            logger.info(f"Detalhes: coletado qt_sol='{qt_sol}', qt_aut='{qt_aut}' na linha {i}")
                        fechar_el = wait_xpath(driver, X_LOCALIZAR_DET_MODAL_FECHAR, 3)
                        if fechar_el:
                            try:
                                fechar_el.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", fechar_el)
                        time.sleep(0.5)

                    row = {
                        "paciente": paciente,
                        "guia": numero_guia,
                        "codigo_beneficiario": codigo_beneficiario,
                        "senha": senha,
                        "status_guia": situacao,
                        "data_solicitacao": (data_solicitacao.date().isoformat() if hasattr(data_solicitacao, 'date') and data_solicitacao else (data_solicitacao.isoformat() if data_solicitacao else None)),
                        "data_autorizacao": (data_autorizacao.date().isoformat() if hasattr(data_autorizacao, 'date') and data_autorizacao else (data_autorizacao.isoformat() if data_autorizacao else None)),
                        "codigo_terapia": codigo_proc,
                        "qtde_solicitada": int(str(qt_sol).strip()) if qt_sol and str(qt_sol).strip().isdigit() else 0,
                        "sessoes_autorizadas": int(str(qt_aut).strip()) if qt_aut and str(qt_aut).strip().isdigit() else 0,
                        "validade": data_validade.isoformat() if data_validade else None,
                        "saldo": 0,
                        "data_atualizacao": datetime.utcnow().isoformat(),
                    }
                    rows_total.append(row)
                    page_rows.append(row)
    
                    if i == 1:
                        guia_primeira_pagina = numero_guia
                except Exception as e_row:
                    if logger:
                        logger.error(f"Erro processando linha {i} na página {pagina_idx}: {str(e_row)}")
                    continue
        except Exception as e:
            if logger:
                logger.error(f"Erro catastrófico ao ler DOM da página {pagina_idx}: {str(e)}")
        # enviar por página e registrar log corretamente
        page_rows_complete = [r for r in page_rows if _is_row_complete(r)]
        if page_rows_complete:
            _save_rows_local(page_rows_complete, logger)
        
        # Salvando Estado de Navegação Localmente
        try:
            os.makedirs("base_guias", exist_ok=True)
            with open(state_file, "w") as f:
                json.dump({"ultima_pagina": pagina_idx}, f)
        except Exception as e:
            logger.warning(f"Erro ao salvar progresso de paginacao: {e}")
            
        page_rows = []
        prev_first = guia_primeira_pagina
        attempts = 0
        advanced = False
        
        while attempts < 3:
            # 1. Obter o número da página atual na DOM antes do clique
            current_page_str = "0"
            try:
                active_li = driver.find_elements(By.XPATH, '//li[contains(@class, "active")]/a/span')
                if active_li:
                    current_page_str = active_li[0].text.strip()
            except Exception:
                pass
                
            if not click_next_page(driver, logger):
                logger.warning(f"MainLoop: btn_next_page reportou fim das páginas ou falhou (Try {attempts+1})")
            
            time.sleep(1.5)
            _wait_spinner_until_gone(driver, max_checks=5, step_seconds=2)
            time.sleep(0.5)
            _close_alert_if_present(driver)
            
            # 2. Obter a nova aba ativa e text da 1a guia
            new_first = _first_guide_text(driver)
            next_page_str = current_page_str
            try:
                active_li = driver.find_elements(By.XPATH, '//li[contains(@class, "active")]/a/span')
                if active_li:
                    next_page_str = active_li[0].text.strip()
            except Exception:
                pass
            
            # 3. Considera avanço real se o Número da aba mudou no Angular OU o text do primeiro item mudou
            if (next_page_str != current_page_str) or (new_first and (not prev_first or new_first != prev_first)):
                advanced = True
                try:
                    pagina_idx = int(next_page_str) if next_page_str.isdigit() else pagina_idx + 1
                except:
                    pagina_idx += 1
                break
            
            logger.warning(f"MainLoop: página não mudou (Angular ativo={next_page_str}, guia1={new_first}). Tentativa {attempts+1}.")
            time.sleep(1.0)
            attempts += 1
        
        if not advanced:
            logger.info("MainLoop: Fim da paginação detectado. Encerrando avanço.")
            break

    logger.info(f"coletados {len(rows_total)} registros")
    logger.info("OP3 Importação de Guias — execução concluída")
    
    # Limpeza do Estado de Navegação em caso de Finalização Completa
    try:
        if os.path.exists(state_file):
            os.remove(state_file)
            logger.info("Arquivo de progresso descartado com sucesso.")
    except Exception:
        pass
        
    if not rows_total and misses > 0:
        raise ValueError("Guias localizadas na tela, mas nenhuma extraída corretamente. Falha na estruturação visual ou quebra da extração.")
            
    return rows_total
def _wait_table_ready(driver, timeout_seconds=5):
    end_time = time.time() + timeout_seconds
    while time.time() < end_time:
        tbl = wait_xpath(driver, X_LOCALIZAR_TABELA_CONTAINER, 1)
        first = wait_xpath(driver, X_LOCALIZAR_FIRST_GUIA, 1)
        if tbl and first:
            return True
        time.sleep(0.5)
    return False

def click_next_page(driver, logger=None):
    btn = wait_xpath(driver, X_LOCALIZAR_BTN_NEXT, 2)
    if not btn:
        if logger: logger.debug("click_next_page: botão próximo não encontrado")
        return False
        
    # Previne loop infinito em KnockoutJS (onde o botão fica com class disabled/inativo)
    try:
        class_str = btn.get_attribute("class") or ""
        disabled_attr = btn.get_attribute("disabled")
        if "disabled" in class_str.lower() or disabled_attr:
            if logger: logger.debug("click_next_page: botão 'próximo' visível porém desabilitado (Última Página)")
            return False
            
        span_interno = btn.find_elements(By.XPATH, ".//span[@class='disabled']")
        if span_interno:
            if logger: logger.debug("click_next_page: span interno acusa disabled (Última Página)")
            return False
    except Exception:
        pass
        
    try:
        if logger: logger.debug("click_next_page: scrollIntoView + click")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.5)
        btn.click()
    except Exception as e:
        if logger: logger.warning(f"click_next_page: click falhou ({str(e)}), tentando JS click")
        try:
            driver.execute_script("arguments[0].click();", btn)
        except Exception as e2:
            if logger: logger.error(f"click_next_page: JS click falhou ({str(e2)})")
            return False
    return True
