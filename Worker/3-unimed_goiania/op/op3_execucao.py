"""
Op 3 — Execução de Guias SP/SADT (Unimed Goiania)
Rotina idêntica estruturalmente à Unimed Anápolis, mas com regras específicas de Goiania:
  - Validação rigorosa de Timeout pelo Banco (retro-disparar captura se <= 2m para timeout de 59m)
  - JS para remover 'disabled' e 'readonly' do input data_hora.
  - Oissão do clique em 'Gravar' após preencher data.
  - Botão de vínculo específico (//*[@id="1"]/td[15]/span/a/span) e check de erro na tela de vínculo.
"""
import time
import json
import os, sys
import requests
from datetime import datetime, timedelta

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, NoAlertPresentException
)

_worker_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _worker_root not in sys.path:
    sys.path.insert(0, _worker_root)

_module_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _module_root not in sys.path:
    sys.path.insert(0, _module_root)

from infra.selenium_helpers import (
    is_element_present, close_popup_window, close_alert_if_present,
    wait_for_element, switch_to_new_window
)
from config.settings import NavSelectors

# Reutiliza helpers DRY de op2_captura de Goiania
from op.op2_captura import _navigate_to_sadts, _apply_guia_filter, _robust_click


# ── Mapeamento de Conselho ──────────────────────────────────────────────────
_CONSELHO_PREFIX_MAP = {
    "CRP":     "CRP",
    "CREFONO": "CREFONO",
    "CREFITO": "CREFITO",
    "CRM":     "CRM",
    "CFO":     "CFO",
    "CRN":     "CRN",
    "COREN":   "COREN",
    "CRP-GO":  "CRP",
    "CREFONO-GO": "CREFONO",
}


def _select_conselho(driver, conselho_code, log):
    prefix = _CONSELHO_PREFIX_MAP.get(conselho_code.upper().strip(), conselho_code.upper().strip())
    try:
        select_el = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "s_tp_conselho"))
        )
        sel = Select(select_el)
        for option in sel.options:
            if option.get_attribute("value").upper().startswith(prefix) or \
               option.text.upper().startswith(prefix):
                sel.select_by_value(option.get_attribute("value"))
                log(f"Conselho selecionado: {option.text}")
                return True
        log(f"Conselho '{prefix}' não encontrado. Tentando match parcial...", level="WARN")
        for option in sel.options:
            if prefix in option.text.upper():
                sel.select_by_value(option.get_attribute("value"))
                log(f"Conselho (parcial) selecionado: {option.text}")
                return True
    except Exception as e:
        log(f"Erro ao selecionar conselho: {e}", level="WARN")
    return False


def _select_option_by_partial_text(driver, element_id, partial_text, log, by=By.ID):
    try:
        select_el = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((by, element_id))
        )
        sel = Select(select_el)
        for option in sel.options:
            if partial_text in option.text or partial_text in option.get_attribute("value"):
                sel.select_by_value(option.get_attribute("value"))
                log(f"Item selecionado: {option.text}")
                return True
        log(f"Item '{partial_text}' não encontrado no select '{element_id}'.", level="WARN")
    except Exception as e:
        log(f"Erro ao selecionar item '{partial_text}': {e}", level="WARN")
    return False


def _wait_page_stable(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        time.sleep(2)


# ── Entry Point ───────────────────────────────────────────────────────────────

def execute(scraper, job_data):
    """
    Executa a Rotina 3 (Execução/Faturamento SP/SADT) para Unimed Goiania.
    """
    job_id = job_data.get("job_id")
    log = lambda msg, **kw: scraper.log(msg, job_id=job_id, **kw)
    driver = scraper.driver

    # ── Parse params ─────────────────────────────────────────────────────────
    numero_guia       = None
    agendamento_id    = None
    nome_profissional = ""
    conselho          = ""
    data_hora         = ""
    cod_proc_fat      = ""

    try:
        params_str = job_data.get("params")
        if params_str:
            p = json.loads(params_str) if isinstance(params_str, str) else params_str
            numero_guia       = p.get("numero_guia", "") or p.get("guia", "")
            if not numero_guia:
                guias_list = p.get("guias", [])
                if isinstance(guias_list, list) and guias_list:
                    numero_guia = str(guias_list[0])
            agendamento_id    = p.get("agendamento_id")
            nome_profissional = (p.get("nome_profissional") or "").strip()
            conselho          = (p.get("conselho") or "").strip()
            data_hora         = (p.get("data_hora") or "").strip()
            cod_proc_fat      = (p.get("cod_procedimento_fat") or "").strip()
    except (json.JSONDecodeError, AttributeError) as e:
        log(f"Partial parse erro (params): {e}", level="WARN")

    if not numero_guia:
        log("PermanentError: Guia não informada para Execução.", level="ERROR")
        raise ValueError("PermanentError: Guia não informada para Execução.")

    log(
        f"Op3 Execução Goiania: Guia={numero_guia} | Profissional='{nome_profissional}' "
        f"| Conselho='{conselho}' | DataHora='{data_hora}' | CodFat='{cod_proc_fat}'"
    )

    # ── FASE 0: VERIFICAÇÃO DE TIMEOUT NO BANCO (Regra Goiania) ───────────────
    db = getattr(scraper, "db", None)
    if not db:
        log("Conexão ao DB indisponível no Worker. Verificação de timeout ignorada.", level="WARN")
    else:
        from models import BaseGuia, Job
        guia_record = db.query(BaseGuia).filter(BaseGuia.guia == numero_guia).first()
        if not guia_record or not getattr(guia_record, "timestamp_captura", None):
            log("Guia não possui timestamp de captura válido na base.", level="ERROR")
            raise ValueError("Guia expirada ou não capturada previamente.")
            
        ts_captura = getattr(guia_record, "timestamp_captura")
        agora = datetime.utcnow() # Assume UTC, if db uses local time adjust as needed
        if ts_captura.tzinfo is None:
            # Assuming DB time is local for this legacy system based on existing op3 script
            agora = datetime.now()

        limite = ts_captura + timedelta(minutes=59)
        if limite < (agora + timedelta(minutes=2)):
            log(f"Timeout baterá na porta! Timestamp: {ts_captura}. Faltam menos de 2m para Expirar. Cancelando execução nativa e re-disparando Captura...", level="WARN")
            backend_url = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8000")
            
            guia_record.timestamp_captura = None
            db.commit()
            
            if agendamento_id:
                try:
                    resp = requests.post(f"{backend_url}/agendamentos/capturar", json={"agendamento_id": agendamento_id})
                    if resp.status_code == 200:
                        data = resp.json()
                        new_job_id = data.get("job_id")
                        current_job = db.query(Job).filter(Job.id == job_id).first()
                        if current_job:
                            current_job.depending_id = new_job_id
                            current_job.status = "pending"
                            current_job.attempts = 0
                            current_job.locked_by = None
                            db.commit()
                            log(f"Execução suspensa com sucesso. Dependência amarrada ao novo Job Captura {new_job_id}")
                            raise NotImplementedError("Execução Adiada. Timeout iminente.") 
                except Exception as e:
                    if isinstance(e, NotImplementedError): raise e
                    log(f"Erro ao retro-disparar a Captura via API Backend: {e}", level="ERROR")
                    raise Exception("Falha na re-orquestração do Job por Timeout")
            else:
                 raise Exception("Agendamento ID ausente no Job para re-roteamento automático.")


    # ── FASE 1: Navegação até SADTs em Aberto ─────────────────────────────────
    log("FASE 1: Navegando até SADTs em aberto...")
    try:
        _navigate_to_sadts(scraper, job_id)
    except Exception as e:
        log(f"FASE 1 falhou: {e}", level="ERROR")
        raise


    # ── FASE 2: Filtrar pela guia ──────────────────────────────────────────────
    log(f"FASE 2: Filtrando guia {numero_guia}...")
    try:
        guia_encontrada, _ = _apply_guia_filter(scraper, numero_guia, job_id)
    except Exception as e:
        log(f"FASE 2 erro no filtro: {e}", level="ERROR")
        raise

    if not guia_encontrada:
        log(f"FASE 2: Guia {numero_guia} não localizada na lista de SADTs abertos.", level="ERROR")
        raise Exception(f"PermanentError: Guia {numero_guia} não capturada ou não disponível no portal.")


    # ── FASE 3: Abre guia → Tipo/Regime/DataHora ─────────────────────
    log(f"FASE 3: Abrindo detalhes da guia {numero_guia}...")

    # Clica no link da guia (Atenção: em Goiania a row principal pode ser tr[2] do loop. O apply_filter usou tr[2])
    guia_link = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="conteudo-submenu"]/table[2]/tbody/tr[2]/td[3]/a'))
    )
    _robust_click(driver, guia_link, "guia_link (tr[2]/td[3]/a)", log)
    _wait_page_stable(driver)
    time.sleep(2)

    try:
        tp_atend = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "DM_TP_ATEND_SADT"))
        )
        sel_tp = Select(tp_atend)
        sel_tp.select_by_visible_text("03 - Outras Terapias")
        log("Tipo Atendimento → '03 - Outras Terapias'")
    except Exception as e:
        log(f"FASE 3: Erro ao selecionar Tipo Atendimento: {e}", level="WARN")

    try:
        regime = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "DM_REGIME_ATEND"))
        )
        sel_reg = Select(regime)
        sel_reg.select_by_visible_text("01 - Ambulatorial")
        log("Regime Atendimento → '01 - Ambulatorial'")
    except Exception as e:
        log(f"FASE 3: Erro ao selecionar Regime: {e}", level="WARN")

    # Regra Goiania: Remover disabled e readonly de dt_serie_1 antes de preencher
    if data_hora:
        try:
            dt_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "dt_serie_1"))
            )
            driver.execute_script("arguments[0].removeAttribute('readonly'); arguments[0].removeAttribute('disabled');", dt_input)
            log("Atributos 'disabled' e 'readonly' removidos via JS.")
            time.sleep(1)
            
            dt_input.click()
            dt_input.clear()
            dt_input.send_keys(data_hora)
            log(f"dt_serie_1 preenchido: {data_hora}")
        except Exception as e:
            log(f"FASE 3: Erro ao preencher dt_serie_1: {e}", level="WARN")
    else:
        log("data_hora não fornecida — dt_serie_1 não será preenchido.", level="WARN")

    # Regra Goiania: Removida a etapa de clique no botão Gravar após informar data
    log("FASE 3 concluída (Botão Gravar omitido conforme especificado para Goiania).")
    time.sleep(2)


    # ── FASE 4: Vínculo profissional ──────────────
    log("FASE 4: Clicando ícone de vínculo do profissional (XPath Unimed Goiania)...")
    try:
        # Ícone de vínculo específico para Unimed Goiania
        vinculo_icon = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="1"]/td[15]/span/a/span'))
        )
        _robust_click(driver, vinculo_icon, "vinculo_icon (//*[@id='1']/td[15]/span/a/span)", log)
        
        # Treatment of error after click:
        time.sleep(3)
        try:
            msg_erro_box = driver.find_elements(By.XPATH, '//*[@id="msgs_conf_consulta"]/div[2]')
            if len(msg_erro_box) > 0 and msg_erro_box[0].is_displayed():
                texto_erro = msg_erro_box[0].text.strip()
                log(f"Erro ao vincular profissional: {texto_erro}", level="ERROR")
                raise Exception(f"Erro de negócio no vínculo: {texto_erro}")
        except Exception as er_val:
            if "Erro de negócio" in str(er_val):
                raise
                
    except Exception as e:
        log(f"FASE 4: Ícone de vínculo não encontrado ou erro reportado: {e}", level="ERROR")
        raise

    time.sleep(2)

    # Clica em Nova Participação (Segue idêntico à Anápolis a partir daqui)
    try:
        nova_part = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".MagnetoRoundedButtonLink:nth-child(1) .MagnetoBigRoundedButtonRight")
            )
        )
        _robust_click(driver, nova_part, "Nova Participação", log)
    except Exception as e:
        log(f"FASE 4: Botão Nova Participação não encontrado: {e}", level="ERROR")
        raise

    _wait_page_stable(driver)
    time.sleep(2)
    log("FASE 4 concluída.")


    # ── FASE 5: Lupa prestador → nova janela → preenche → filtrar → resultado ─
    log("FASE 5: Clicando lupa de localizar profissional...")
    handles_before_lupa = driver.window_handles

    try:
        lupa = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#link_busca_prest > img"))
        )
        _robust_click(driver, lupa, "lupa_prestador (#link_busca_prest > img)", log)
    except Exception as e:
        log(f"FASE 5: Lupa de prestador não encontrada: {e}", level="ERROR")
        raise

    nova_janela = switch_to_new_window(driver, handles_before_lupa, timeout=8)
    if not nova_janela:
        raise Exception("FASE 5: Janela de busca de prestador não abriu.")

    log(f"FASE 5: Janela prestador aberta ({driver.title})")

    try:
        campo_nome = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.NAME, "s_nm_prestador"))
        )
        campo_nome.click()
        campo_nome.clear()
        campo_nome.send_keys(nome_profissional)
        log(f"Nome prestador preenchido: '{nome_profissional}'")
    except Exception as e:
        log(f"FASE 5: Erro ao preencher nome prestador: {e}", level="WARN")

    if conselho:
        _select_conselho(driver, conselho, log)
    else:
        log("Conselho não fornecido — select s_tp_conselho não será alterado.", level="WARN")

    try:
        _select_option_by_partial_text(driver, "s_tp_busca_Options", "Prestador Externo", log, by=By.ID)
    except Exception as e:
        log(f"FASE 5: Erro ao selecionar Prestador Externo: {e}", level="WARN")

    try:
        btn_filtrar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.NAME, "Button_DoSearch"))
        )
        _robust_click(driver, btn_filtrar, "Button_DoSearch (Filtrar)", log)
    except Exception as e:
        log(f"FASE 5: Erro ao clicar Filtrar: {e}", level="ERROR")
        raise

    time.sleep(3)

    try:
        primeiro_resultado = None
        try:
            xpath_attr = f"//a[@data-nm-prest='{nome_profissional.upper()}']"
            primeiro_resultado = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath_attr))
            )
            log(f"FASE 5: Localizado pelo atributo data-nm-prest='{nome_profissional.upper()}'.")
        except:
            log("FASE 5: Atributo não encontrado, tentando XPath preciso tr[3].")
            selectors = [
                "/html/body/div/table/tbody/tr[3]/td[2]/a",
                "//tr[starts-with(@id, 'trRow_')]//td[2]//a"
            ]
            for sel in selectors:
                try:
                    primeiro_resultado = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                    if primeiro_resultado: 
                        log(f"FASE 5: Localizado pelo seletor: {sel}")
                        break
                except:
                    continue

        if not primeiro_resultado:
            raise Exception("Profissional não localizado nos resultados da busca.")

        _robust_click(driver, primeiro_resultado, "1º resultado prestador", log)
        log("FASE 5: Profissional selecionado com sucesso.")

    except Exception as e:
        log(f"FASE 5: Profissional '{nome_profissional}' não encontrado.", level="ERROR")
        try:
            if len(driver.window_handles) > 1:
                if driver.current_window_handle != handles_before_lupa[0]:
                    driver.close()
                driver.switch_to.window(handles_before_lupa[0])
        except:
            pass

        msg_erro = "PermanentError: Profissional não cadastrado."
        if db and job_id and job_id != 9999:
            try:
                from models import Job
                job_obj = db.query(Job).filter(Job.id == job_id).first()
                if job_obj:
                    job_obj.attempts = 3
                    job_obj.status = "error"
                    db.commit()
                    log(f"Job {job_id} encerrado (3 tentativas) - Profissional não cadastrado.")
            except:
                pass
        raise Exception(msg_erro)

    time.sleep(2)
    current_handles = driver.window_handles
    if nova_janela not in current_handles:
        log("FASE 5: Janela prestador fechou automaticamente.")
        driver.switch_to.window(handles_before_lupa[0])
    else:
        log("FASE 5: Fechando janela prestador manualmente...")
        driver.close()
        driver.switch_to.window(handles_before_lupa[0])

    _wait_page_stable(driver)
    time.sleep(2)
    log("FASE 5 concluída.")


    # ── FASE 6: Cadastrar → Grau → Item → Gravar ──────────────────────────────
    log("FASE 6: Clicando em Cadastrar...")
    try:
        btn_cadastrar = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.NAME, "Button_Insert"))
        )
        _robust_click(driver, btn_cadastrar, "Button_Insert (Cadastrar)", log)
    except Exception as e:
        log(f"FASE 6: Botão Cadastrar não encontrado: {e}", level="ERROR")
        raise

    _wait_page_stable(driver)
    time.sleep(2)

    try:
        _select_option_by_partial_text(driver, "DM_GRAU_PARTIC_1", "12", log, by=By.ID)
        log("Grau de Participação → '12 - Clínico'")
    except Exception as e:
        log(f"FASE 6: Erro ao selecionar Grau de Participação: {e}", level="WARN")

    if cod_proc_fat:
        selected = _select_option_by_partial_text(driver, "NR_SEQ_ITEM_1", cod_proc_fat, log, by=By.ID)
        if not selected:
            log(
                f"FASE 6: Código '{cod_proc_fat}' não encontrado em NR_SEQ_ITEM_1. "
                "Verificar cod_procedimento_fat do agendamento.",
                level="WARN"
            )
    else:
        log("cod_procedimento_fat não fornecido — NR_SEQ_ITEM_1 não será selecionado.", level="WARN")

    try:
        btn_submit = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "Button_Submit"))
        )
        _robust_click(driver, btn_submit, "Button_Submit (Gravar)", log)
    except Exception as e:
        log(f"FASE 6: Erro ao clicar Gravar: {e}", level="ERROR")
        raise

    _wait_page_stable(driver)
    close_alert_if_present(driver)
    time.sleep(2)
    log("FASE 6 concluída.")


    # ── FASE 7: Dados da Guia SP/SADT → Finalizar Parcial ────────────────────
    log("FASE 7: Clicando em 'Dados da Guia SP/SADT'...")
    try:
        btn_spsadt = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".MagnetoRoundedButtonLink:nth-child(2) .MagnetoBigRoundedButtonRight")
            )
        )
        _robust_click(driver, btn_spsadt, "Dados da Guia SP/SADT", log)
    except Exception as e:
        log(f"FASE 7: Botão Dados da Guia SP/SADT não encontrado: {e}", level="ERROR")
        raise

    _wait_page_stable(driver)
    time.sleep(2)

    log("FASE 7: Clicando em Finalizar Parcial...")
    handles_before_parcial = driver.window_handles
    try:
        btn_parcial = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "Button_Parcial"))
        )
        _robust_click(driver, btn_parcial, "Button_Parcial (Finalizar Parcial)", log)
        
        log("FASE 7: Aguardando abertura do popup de confirmação final...")
        popup_confirmacao = switch_to_new_window(driver, handles_before_parcial, timeout=8)
        
        if popup_confirmacao:
            log(f"FASE 7: Popup Confirmar detectado ({driver.title})")
            btn_confirmar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "btn_confirmar"))
            )
            _robust_click(driver, btn_confirmar, "btn_confirmar (Confirmar Finalização)", log)
            log("Confirmação final realizada com sucesso na nova janela.")
            
            time.sleep(2)
            if len(driver.window_handles) > 1 and driver.current_window_handle != handles_before_parcial[0]:
                driver.close()
            driver.switch_to.window(handles_before_parcial[0])
            
        else:
             log("FASE 7: Nenhuma nova aba aberta. Tentando confirmar no DOM original.")
             btn_confirmar = WebDriverWait(driver, 5).until(
                 EC.element_to_be_clickable((By.ID, "btn_confirmar"))
             )
             _robust_click(driver, btn_confirmar, "btn_confirmar (Confirmar Finalização - DOM Original)", log)
             log("Confirmação final realizada com sucesso no DOM original.")
             
    except Exception as e:
        log(f"FASE 7: Erro na finalização da guia: {e}", level="ERROR")
        try:
             driver.switch_to.window(handles_before_parcial[0])
        except:
             pass
        raise

    _wait_page_stable(driver)
    close_alert_if_present(driver)
    time.sleep(2)
    log("FASE 7 concluída.")


    # ── Atualizar execucao_status no banco ────────────────────────────────────
    if agendamento_id:
        if db:
            try:
                from models import Agendamento
                agenda = db.query(Agendamento).filter(
                    Agendamento.id_agendamento == int(agendamento_id)
                ).first()
                if agenda:
                    agenda.execucao_status = "sucesso"
                    db.commit()
                    log(f"Agendamento {agendamento_id} execucao_status → 'sucesso'")
                else:
                    log(f"Agendamento {agendamento_id} não encontrado no banco.", level="WARN")
            except Exception as db_err:
                log(f"Erro ao atualizar execucao_status: {db_err}", level="ERROR")

    log(f"Op3 Execução concluída com sucesso! Guia={numero_guia}")
    return [{
        "numero_guia":    numero_guia,
        "agendamento_id": agendamento_id,
        "executado":      True,
        "data_hora":      data_hora,
        "profissional":   nome_profissional
    }]
