from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta, timezone
import time
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
from infra.supabase_store import save_rows, log_import_page, get_last_log, clear_log

def wait_xpath(driver, xpath, timeout=DEFAULT_TIMEOUT):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
    except Exception:
        return None

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

def _wait_page_ready(driver, wait_seconds=3):
    end_time = time.time() + wait_seconds
    while time.time() < end_time:
        aviso = driver.find_elements(By.XPATH, X_ALERT_AVISO_BANNER)
        load = driver.find_elements(By.XPATH, X_LOADING_GLOBAL)
        overlay = driver.find_elements(By.XPATH, X_LOADING_OVERLAY)
        if not aviso and not load and not overlay:
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
        overlay = driver.find_elements(By.XPATH, X_LOADING_OVERLAY)
        if not overlay:
            if logger:
                logger.debug("spinner não visível")
            return True
        if logger:
            logger.debug(f"spinner visível (tentativa {attempt}/{max_checks})")
        time.sleep(step_seconds)
    return not driver.find_elements(By.XPATH, X_LOADING_OVERLAY)

def _is_row_complete(row):
    req = [row.get("numero_guia"), row.get("paciente"), row.get("status"), row.get("codigo_procedimento"), row.get("qtde_solicitado")]
    return all(req)

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

def run(driver, settings, logger, start_date=None, end_date=None):
    runtime = get_runtime_settings()
    url = runtime.get("IMPORT_GUIAS_URL")
    if not url:
        logger.error("IMPORT_GUIAS_URL não definida")
        return
    driver.get(url)
    time.sleep(2)
    logger.info("Aviso: erros DEPRECATED_ENDPOINT do Chrome serão ignorados; não impactam o fluxo de coleta")

    # Fechar notificação/overlay se existir
    try:
        overlay = wait_xpath(driver, X_LOCALIZAR_NOTY_MODAL, 2)
        container = wait_xpath(driver, X_LOCALIZAR_NOTY_CONTAINER, 2)
        if overlay or container:
            fechar = wait_xpath(driver, X_LOCALIZAR_NOTY_FECHAR, 2)
            if fechar:
                fechar.click()
                time.sleep(1)
            else:
                try:
                    driver.execute_script("document.querySelector('.noty_modal')?.remove();")
                except Exception:
                    pass
    except Exception:
        pass

    if start_date and end_date:
        campo_ini = wait_xpath(driver, X_LOCALIZAR_DATA_INICIO)
        campo_fim = wait_xpath(driver, X_LOCALIZAR_DATA_FIM)
        if not (campo_ini and campo_fim):
            logger.error("campos de data não encontrados (constants.py)")
            return
        campo_ini.clear()
        campo_fim.clear()
        campo_ini.send_keys(_formatar_ddmmyyyy(start_date))
        campo_fim.send_keys(_formatar_ddmmyyyy(end_date))
        campo_fim.send_keys(Keys.ENTER)
        time.sleep(1)

    try:
        btn_buscar = WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, X_LOCALIZAR_BTN_PESQUISAR))
        )
    except Exception:
        btn_buscar = wait_xpath(driver, X_LOCALIZAR_BTN_PESQUISAR)
    if not btn_buscar:
        logger.error("botão pesquisar não encontrado (constants.py)")
        return
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_buscar)
        btn_buscar.click()
    except Exception:
        driver.execute_script("arguments[0].click();", btn_buscar)
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
    # retomada opcional por log
    di = datetime.strptime(_formatar_ddmmyyyy(start_date), "%d/%m/%Y").date().isoformat() if start_date else None
    df = datetime.strptime(_formatar_ddmmyyyy(end_date), "%d/%m/%Y").date().isoformat() if end_date else None
    reset = (settings or {}).get("IMPORT_LOG_RESET") in (True, "true", "1")
    if reset:
        clear_log("op3_import_guias", di, df, logger)
    last = get_last_log("op3_import_guias", di, df, logger)
    if last and (last.get("pagina") or 0) >= 1:
        from datetime import timezone
        try:
            ca = last.get("created_at")
            # formato ISO: 2025-12-08T01:50:02.774Z
            dt = datetime.fromisoformat(ca.replace("Z", "+00:00")) if ca else None
        except Exception:
            dt = None
        fresh = False
        if dt:
            now = datetime.now(timezone.utc)
            delta = (now - dt).total_seconds()
            fresh = delta < 3600
        if fresh:
            logger.info(f"retomando a partir da página {last['pagina']+1}")
        else:
            clear_log("op3_import_guias", di, df, logger)
            last = None
    if last and (last.get("pagina") or 0) >= 1:
        target = last["pagina"] + 1
        logger.info(f"Retomada: avançando da pág 1 até {target}...")
        current = 1
        while current < target:
            prev_first = _first_guide_text(driver)
            if not click_next_page(driver, logger):
                logger.error(f"Retomada: falha ao clicar próxima página na pág {current}")
                break
            
            _wait_spinner_until_gone(driver, max_checks=3, step_seconds=3, logger=logger)
            time.sleep(1)
            _close_alert_if_present(driver)
            
            # Verificar se mudou de página
            attempts = 0
            changed = False
            while attempts < 3:
                new_first = _first_guide_text(driver)
                if new_first and (not prev_first or new_first != prev_first):
                    changed = True
                    break
                time.sleep(1)
                attempts += 1
            
            if not changed:
                logger.warning(f"Retomada: página parece não ter mudado em {current} -> {current+1}")
            
            _wait_table_ready(driver, 3)
            current += 1
        pagina_idx = current
        logger.info(f"Retomada concluída. Página atual estimada: {pagina_idx}")

    last_page = (last.get("pagina") if last else None)
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
                if not click_next_page(driver, logger):
                    logger.warning("Skip: click_next_page retornou False")
                
                _wait_spinner_until_gone(driver, max_checks=3, step_seconds=3)
                time.sleep(1.5)
                _close_alert_if_present(driver)
                
                new_first = _first_guide_text(driver)
                if new_first and (not prev_first or new_first != prev_first):
                    advanced = True
                    break
                
                logger.warning(f"Skip: página não mudou (tentativa {attempts+1}/3). Retentando...")
                attempts += 1
            
            if not advanced:
                logger.error("Skip: Falha crítica - não foi possível avançar de página após 3 tentativas. Abortando.")
                break 
            
            pagina_idx += 1
            continue
        page_rows = []
        i = 1
        misses = 0
        max_rows = 20
        misses_max = 2
        try:
            while i <= max_rows and misses < misses_max:
                xp_paciente = X_LOCALIZAR_ROW_PACIENTE_FMT.format(i=i)
                xp_guia = X_LOCALIZAR_ROW_GUIA_FMT.format(i=i)
                xp_benef = X_LOCALIZAR_ROW_COD_BENEF_FMT.format(i=i)
                xp_senha = X_LOCALIZAR_ROW_SENHA_FMT.format(i=i)
                xp_situacao = X_LOCALIZAR_ROW_SITUACAO_FMT.format(i=i)
                xp_data_sol = X_LOCALIZAR_ROW_DATA_SOL_FMT.format(i=i)
                xp_data_aut = X_LOCALIZAR_ROW_DATA_AUT_FMT.format(i=i)
                xp_cod_proc = X_LOCALIZAR_ROW_COD_PROC_FMT.format(i=i)
                xp_btn_det = X_LOCALIZAR_ROW_BTN_DET_FMT.format(i=i)

                guia_el = wait_xpath(driver, xp_guia, 2)
                paciente_el = wait_xpath(driver, xp_paciente, 2)
                benef_el = wait_xpath(driver, xp_benef, 2)
                senha_el = wait_xpath(driver, xp_senha, 2)
                situacao_el = wait_xpath(driver, xp_situacao, 2)
                if not all([guia_el, paciente_el, senha_el, situacao_el]):
                    misses += 1
                    if logger:
                        logger.info(f"linha {i}: elementos incompletos, misses={misses}")
                    i += 1
                    continue
                misses = 0
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", guia_el)
                except Exception:
                    driver.execute_script("arguments[0].scrollIntoView(true);", guia_el)
                time.sleep(0.3)

                paciente = paciente_el.text
                numero_guia = guia_el.text
                cod_benef = benef_el.text if benef_el else ""
                senha = senha_el.text
                situacao = situacao_el.text

                data_sol_el = wait_xpath(driver, xp_data_sol, 2)
                data_aut_el = wait_xpath(driver, xp_data_aut, 2)
                data_solicitacao = normalizar_data(data_sol_el.text) if data_sol_el else None
                data_autorizacao = normalizar_data(data_aut_el.text) if data_aut_el else None
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
                    "numero_guia": numero_guia,
                    "senha": senha,
                    "status": situacao,
                    "data_solicitacao": (data_solicitacao.date().isoformat() if hasattr(data_solicitacao, 'date') and data_solicitacao else (data_solicitacao.isoformat() if data_solicitacao else None)),
                    "data_autorizacao": (data_autorizacao.date().isoformat() if hasattr(data_autorizacao, 'date') and data_autorizacao else (data_autorizacao.isoformat() if data_autorizacao else None)),
                    "codigo_procedimento": codigo_proc,
                    "qtde_solicitado": qt_sol,
                    "qtde_autorizado": qt_aut,
                    "data_validade": data_validade.isoformat() if data_validade else None,
                    "saldo": None,
                    "cod_beneficiario": cod_benef,
                    "data_atualizacao": datetime.now(timezone.utc).isoformat(),
                }
                rows_total.append(row)
                page_rows.append(row)

                if i == 1:
                    guia_primeira_pagina = numero_guia
                i += 1
        except Exception as e:
            logger.error(f"erro inesperado na coleta da página {pagina_idx}: {str(e)}")
        # enviar por página e registrar log corretamente
        page_rows_complete = [r for r in page_rows if _is_row_complete(r)]
        if page_rows_complete:
            save_rows(page_rows_complete, logger)
        log_import_page({
            "op": "op3_import_guias",
            "data_inicio": datetime.strptime(_formatar_ddmmyyyy(start_date), "%d/%m/%Y").date().isoformat() if start_date else None,
            "data_fim": datetime.strptime(_formatar_ddmmyyyy(end_date), "%d/%m/%Y").date().isoformat() if end_date else None,
            "pagina": pagina_idx,
            "total_registros": len(page_rows_complete),
            "primeira_guia": guia_primeira_pagina,
        }, logger)
        page_rows = []
        prev_first = guia_primeira_pagina
        attempts = 0
        advanced = False
        while attempts < 3:
            if not click_next_page(driver, logger):
                logger.warning(f"MainLoop: click_next_page falhou na tentativa {attempts+1}")
            
            _wait_spinner_until_gone(driver, max_checks=3, step_seconds=3)
            time.sleep(0.5)
            _close_alert_if_present(driver)
            
            new_first = _first_guide_text(driver)
            if new_first and (not prev_first or new_first != prev_first):
                advanced = True
                break
            
            logger.warning(f"MainLoop: página não mudou (tentativa {attempts+1}). Retentando...")
            attempts += 1
        
        if not advanced:
            logger.error("MainLoop: Falha ao avançar para próxima página. Encerrando.")
            break
        pagina_idx += 1

    logger.info(f"coletados {len(rows_total)} registros")
    logger.info("OP3 Importação de Guias — execução concluída")
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
