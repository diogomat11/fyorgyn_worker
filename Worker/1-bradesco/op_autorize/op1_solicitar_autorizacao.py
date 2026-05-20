"""
OP1 - Solicitar Autorização SADT (Bradesco / Polimed-Orizon)
Preenche o formulário completo de solicitação de autorização e captura o retorno.
"""
from __future__ import annotations
import time
from typing import TYPE_CHECKING
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import sys

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)]
if sys.path[0] != _mod_root:
    sys.path.insert(0, _mod_root)

from config.constants import (
    X_SELECT_EMS,
    REGISTRO_ANS_OPTIONS,
    X_RADIO_CARTEIRA,
    X_INPUT_CARTEIRA,
    X_ATENDIMENTO_RN_NAO,
    X_TIPO_CONTRATADO_SOLICITANTE_ID,
    X_TIPO_CONTRATADO_OPT_COD_OPERADORA,
    X_CODIGO_OPERADORA_ID,
    X_NOME_PROFISSIONAL_ID,
    X_CONSELHO_PROFISSIONAL_ID,
    X_NUMERO_CONSELHO_ID,
    X_UF_CONSELHO_ID,
    X_CBO_PROFISSIONAL_ID,
    X_RADIO_ELETIVA,
    X_IMG_PESQUISA_CID_ID,
    X_CID_DESCRICAO_ID,
    X_CID_BTN_PESQUISAR,
    X_CID_PRIMEIRO_RESULTADO,
    X_TIPO_ATENDIMENTO_PEQUENOS,
    X_TIPO_ATENDIMENTO_TERAPIAS,
    X_REGIME_ATENDIMENTO,
    X_INDICADOR_ACIDENTE,
    X_MATRICULA_EXECUTANTE_ID,
    X_CODIGO_PROCEDIMENTO_ID,
    X_QTD_PROCEDIMENTO_ID,
    X_UPLOAD_CONTAINER_ID,
    X_INPUT_FILE_ID,
    X_TIPO_ARQUIVO_OPT,
    X_BTN_ANEXAR_ID,
    X_INDICACAO_CLINICA_ID,
    X_BTN_ENVIAR_ID,
    X_GUIA_PRESTADOR,
    X_STATUS_PROCEDIMENTO_ID,
    DEFAULT_TIMEOUT,
    LONG_TIMEOUT,
    SHORT_TIMEOUT,
)
from config.settings import OP1_URL
from core.selenium_helpers import (
    aguardar_elemento,
    aguardar_elemento_presente,
    aguardar_clicavel,
    preencher_input,
    clicar_elemento,
    selecionar_option_contendo_texto,
    scroll_to_element,
    switch_to_next_window,
    switch_to_previous_window,
    capturar_texto,
    elemento_existe,
    fechar_janela_atual,
)

if TYPE_CHECKING:
    from base_scraper import BaseScraper


def _extrair_param(job_data: dict, chave: str, obrigatorio: bool = True):
    """Extrai parâmetro do job_data, lançando erro se obrigatório e ausente."""
    valor = job_data.get(chave)
    if obrigatorio and not valor:
        raise ValueError(f"Parâmetro obrigatório ausente: {chave}")
    return valor


def run(scraper: "BaseScraper", job_data: dict) -> list:
    """
    Executa a solicitação de autorização SADT no portal Bradesco (Polimed/Orizon).
    
    Parâmetros esperados no job_data (via params do Job):
        - RegistroAns: str
        - cod_prestador: str (sobrescreve o default do user_convenios)
        - carteira: str
        - nomeMedico: str
        - ConselhoMedico: str
        - NumeroRegistroMedico: str
        - UfConselhoMedico: str
        - Cbomedico: str
        - CodigoCid10: str
        - TipoAtendimento: str ("pequenos atendimentos" | "TERAPIAS")
        - codigoProcedimento: str
        - qtde_solicitad: int/str
        - caminho_arquivo_RM: str (caminho absoluto do arquivo)
    
    Retorno:
        [{"guiaprestador": str, "StatusGuia": str, ...}] ou exceção
    """
    job_id = job_data.get("job_id")
    driver = scraper.driver
    scraper.log("OP1 - Solicitar Autorização SADT iniciada", job_id=job_id)

    # ── Extrair parâmetros ──
    registro_ans = _extrair_param(job_data, "RegistroAns")
    cod_prestador = job_data.get("cod_prestador") or getattr(scraper, "cod_prestador", None)
    if not cod_prestador:
        raise ValueError("PermanentError: cod_prestador não informado nos params e não encontrado nas credenciais")

    carteira = _extrair_param(job_data, "carteira")
    nome_medico = _extrair_param(job_data, "nomeMedico")
    conselho_medico = _extrair_param(job_data, "ConselhoMedico")
    numero_registro_medico = _extrair_param(job_data, "NumeroRegistroMedico")
    uf_conselho = _extrair_param(job_data, "UfConselhoMedico")
    cbo_medico = _extrair_param(job_data, "Cbomedico")
    codigo_cid10 = _extrair_param(job_data, "CodigoCid10")
    tipo_atendimento = _extrair_param(job_data, "TipoAtendimento")
    codigo_procedimento = _extrair_param(job_data, "codigoProcedimento")
    qtde_solicitada = _extrair_param(job_data, "qtde_solicitad")
    caminho_arquivo_rm = _extrair_param(job_data, "caminho_arquivo_RM")

    # ── Validar RegistroAns ──
    if registro_ans not in REGISTRO_ANS_OPTIONS:
        scraper.log(f"RegistroAns '{registro_ans}' não está na lista permitida: {REGISTRO_ANS_OPTIONS}", level="WARN", job_id=job_id)

    # ── 1. Navegar para a página da OP1 ──
    driver.get(OP1_URL)
    scraper.log(f"Navegando para {OP1_URL}", job_id=job_id)
    time.sleep(3)

    # ── 1.1 Mapeamento de iFrames (Baseado no Selenium IDE) ──
    try:
        driver.switch_to.default_content()
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(0)
            scraper.log("Entrou no primeiro iframe (index=0)", job_id=job_id)
            iframes_aninhados = driver.find_elements(By.TAG_NAME, "iframe")
            if len(iframes_aninhados) > 0:
                driver.switch_to.frame(0)
                scraper.log("Entrou no segundo iframe aninhado (index=0)", job_id=job_id)
    except Exception as e:
        scraper.log(f"Aviso ao tentar mapear iframes: {e}", level="WARN", job_id=job_id)

    # ── 2. Selecionar operadora ──
    scraper.log("Selecionando operadora...", job_id=job_id)
    
    try:
        select_el = aguardar_elemento_presente(driver, By.XPATH, X_SELECT_EMS, DEFAULT_TIMEOUT)
        scroll_to_element(driver, select_el)
        time.sleep(1)
        
        from selenium.webdriver.support.ui import Select
        sel = Select(select_el)
        
        found = False
        for opt in sel.options:
            if registro_ans in opt.text or registro_ans in (opt.get_attribute("value") or "") or registro_ans in (opt.get_attribute("registroans") or ""):
                sel.select_by_visible_text(opt.text)
                found = True
                break
                
        if not found:
            # Fallback direto baseado no padrão de texto da Polimed/Bradesco
            sel.select_by_visible_text(f"BRADESCO SAÚDE - {registro_ans}")
            found = True
            
        scraper.log(f"Operadora selecionada com sucesso via Select: {registro_ans}", job_id=job_id)
        time.sleep(1)
        
    except Exception as e_step2:
        scraper.log(f"Erro FATAL na etapa 2 (Selecionando operadora): {e_step2}", level="ERROR", job_id=job_id)
        raise

    # ── 3. Selecionar rádio carteira e preencher número ──
    clicar_elemento(driver, By.ID, X_RADIO_CARTEIRA, DEFAULT_TIMEOUT)
    preencher_input(driver, By.XPATH, X_INPUT_CARTEIRA, carteira, clear=True)
    scraper.log(f"Carteira preenchida: {carteira}", job_id=job_id)

    # ── 4. Atendimento RN = Não ──
    clicar_elemento(driver, By.XPATH, X_ATENDIMENTO_RN_NAO, DEFAULT_TIMEOUT)

    # ── 5. Contratado Solicitante ──
    clicar_elemento(driver, By.ID, X_TIPO_CONTRATADO_SOLICITANTE_ID, DEFAULT_TIMEOUT)
    clicar_elemento(driver, By.XPATH, X_TIPO_CONTRATADO_OPT_COD_OPERADORA, DEFAULT_TIMEOUT)

    # Código operadora (cod_prestador)
    preencher_input(driver, By.ID, X_CODIGO_OPERADORA_ID, cod_prestador, clear=True)
    scraper.log(f"Código prestador: {cod_prestador}", job_id=job_id)

    # ── 6. Profissional Solicitante ──
    preencher_input(driver, By.ID, X_NOME_PROFISSIONAL_ID, nome_medico)

    # Conselho — clicar fisicamente no item (option) com o value exato
    conselho_xpath = f"//select[@id='{X_CONSELHO_PROFISSIONAL_ID}']//option[@value='{conselho_medico}']"
    try:
        clicar_elemento(driver, By.XPATH, conselho_xpath, DEFAULT_TIMEOUT, js_fallback=True)
    except Exception as e:
        scraper.log(f"Falha ao clicar no item Conselho: {e}", level="WARN", job_id=job_id)

    # Número do conselho
    preencher_input(driver, By.ID, X_NUMERO_CONSELHO_ID, numero_registro_medico)

    # UF do conselho — clicar fisicamente no item (option) com o value exato
    uf_xpath = f"//select[@id='{X_UF_CONSELHO_ID}']//option[@value='{uf_conselho}']"
    try:
        clicar_elemento(driver, By.XPATH, uf_xpath, DEFAULT_TIMEOUT, js_fallback=True)
    except Exception as e:
        scraper.log(f"Falha ao clicar no item UF Conselho: {e}", level="WARN", job_id=job_id)

    # CBO
    clicar_elemento(driver, By.ID, X_CBO_PROFISSIONAL_ID, DEFAULT_TIMEOUT)
    preencher_input(driver, By.ID, X_CBO_PROFISSIONAL_ID, cbo_medico, clear=False)
    scraper.log("Dados do profissional solicitante preenchidos", job_id=job_id)

    # ── 7. Caráter eletivo ──
    clicar_elemento(driver, By.XPATH, X_RADIO_ELETIVA, DEFAULT_TIMEOUT)

    # ── 8. CID10 (popup) ──
    scraper.log(f"Pesquisando CID10: {codigo_cid10}", job_id=job_id)
    clicar_elemento(driver, By.ID, X_IMG_PESQUISA_CID_ID, DEFAULT_TIMEOUT)
    time.sleep(1)

    # Trocar para janela do CID
    switch_to_next_window(driver, timeout=10)

    # Pesquisar CID
    preencher_input(driver, By.ID, X_CID_DESCRICAO_ID, codigo_cid10)
    clicar_elemento(driver, By.XPATH, X_CID_BTN_PESQUISAR, DEFAULT_TIMEOUT)
    time.sleep(2)

    # Selecionar primeiro resultado
    if elemento_existe(driver, By.XPATH, X_CID_PRIMEIRO_RESULTADO, timeout=5):
        clicar_elemento(driver, By.XPATH, X_CID_PRIMEIRO_RESULTADO, SHORT_TIMEOUT)
        scraper.log(f"CID10 selecionado: {codigo_cid10}", job_id=job_id)
    else:
        # Fechar popup e lançar erro
        try:
            fechar_janela_atual(driver)
        except Exception:
            switch_to_previous_window(driver)
        raise ValueError(f"CID inválido ou não localizado: {codigo_cid10}")

    # Retornar para janela principal (a seleção do CID fecha o popup automaticamente)
    time.sleep(1)
    try:
        switch_to_previous_window(driver)
    except Exception:
        pass

    # ── 8.1 Re-entrar nos iframes após popup CID ──
    scraper.log("Re-entrando nos iframes após popup CID...", job_id=job_id)
    try:
        driver.switch_to.default_content()
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(0)
            iframes_aninhados = driver.find_elements(By.TAG_NAME, "iframe")
            if len(iframes_aninhados) > 0:
                driver.switch_to.frame(0)
        scraper.log("Iframes re-mapeados com sucesso", job_id=job_id)
    except Exception as e:
        scraper.log(f"Aviso re-mapeamento iframes: {e}", level="WARN", job_id=job_id)

    time.sleep(1)

    # ── 9. Tipo de Atendimento ──
    scraper.log("Passo 9: Tipo de Atendimento", job_id=job_id)
    try:
        # Verificar se o elemento existe no contexto atual
        el_tipo = aguardar_elemento_presente(driver, By.ID, "tipoAtendimento", SHORT_TIMEOUT)
        scraper.log(f"tipoAtendimento encontrado: tag={el_tipo.tag_name}, displayed={el_tipo.is_displayed()}", job_id=job_id)
        scroll_to_element(driver, el_tipo)
        time.sleep(0.5)
        
        tipo_lower = tipo_atendimento.lower().strip()
        search_term = "pequenos atendimentos" if "pequeno" in tipo_lower else ("terapias" if "terapia" in tipo_lower else tipo_lower)
        
        # Clicar na div-pai para ativar a área do select
        try:
            div_pai = driver.find_element(By.XPATH, "//*[@id='tipoAtendimento']/ancestor::div[1]")
            div_pai.click()
            scraper.log("Clicou na div-pai do tipoAtendimento", job_id=job_id)
            time.sleep(0.3)
        except Exception:
            scraper.log("Div-pai não encontrada, prosseguindo direto", level="WARN", job_id=job_id)
        
        # Listar opções disponíveis para debug
        opts_debug = driver.execute_script("""
            var sel = document.getElementById('tipoAtendimento');
            if(!sel) return 'ELEMENTO NAO ENCONTRADO NO DOM';
            var opts = [];
            for(var i=0; i<sel.options.length; i++) {
                opts.push(i + ': text=' + sel.options[i].text + ' | label=' + (sel.options[i].getAttribute('label')||'') + ' | value=' + sel.options[i].value);
            }
            return opts.join(' ;; ');
        """)
        scraper.log(f"Opções disponíveis em tipoAtendimento: {opts_debug}", job_id=job_id)
        
        # Selecionar via JS
        result = driver.execute_script(f"""
            var sel = document.getElementById('tipoAtendimento');
            if(!sel) return 'SELECT_NAO_ENCONTRADO';
            for(var i=0; i<sel.options.length; i++) {{
                var txt = (sel.options[i].text || '').toLowerCase();
                var lbl = (sel.options[i].getAttribute('label') || '').toLowerCase();
                if(txt.indexOf('{search_term}') > -1 || lbl.indexOf('{search_term}') > -1) {{
                    sel.selectedIndex = i;
                    sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                    return 'OK:' + i + ':' + sel.options[i].text;
                }}
            }}
            return 'NAO_ENCONTRADO';
        """)
        scraper.log(f"Resultado seleção tipoAtendimento: {result}", job_id=job_id)
        time.sleep(0.5)
    except Exception as e:
        scraper.log(f"ERRO Tipo de Atendimento: {type(e).__name__}: {e}", level="ERROR", job_id=job_id)

    # ── 10. Regime de Atendimento ──
    scraper.log("Passo 10: Regime de Atendimento", job_id=job_id)
    try:
        el_regime = aguardar_elemento_presente(driver, By.ID, "regimeAtendimento", SHORT_TIMEOUT)
        scraper.log(f"regimeAtendimento encontrado: tag={el_regime.tag_name}", job_id=job_id)
        scroll_to_element(driver, el_regime)
        time.sleep(0.5)
        
        result = driver.execute_script("""
            var sel = document.getElementById('regimeAtendimento');
            if(!sel) return 'SELECT_NAO_ENCONTRADO';
            for(var i=0; i<sel.options.length; i++) {
                var txt = (sel.options[i].text || '').toLowerCase();
                var lbl = (sel.options[i].getAttribute('label') || '').toLowerCase();
                if(txt.indexOf('ambulatorial') > -1 || lbl.indexOf('ambulatorial') > -1) {
                    sel.selectedIndex = i;
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                    return 'OK:' + i + ':' + sel.options[i].text;
                }
            }
            return 'NAO_ENCONTRADO';
        """)
        scraper.log(f"Resultado seleção regimeAtendimento: {result}", job_id=job_id)
        time.sleep(0.5)
    except Exception as e:
        scraper.log(f"ERRO Regime Atendimento: {type(e).__name__}: {e}", level="ERROR", job_id=job_id)

    # ── 11. Indicador de Acidente ──
    scraper.log("Passo 11: Indicador de Acidente", job_id=job_id)
    try:
        el_acidente = aguardar_elemento_presente(driver, By.ID, "indicadorAcidente", SHORT_TIMEOUT)
        scraper.log(f"indicadorAcidente encontrado: tag={el_acidente.tag_name}", job_id=job_id)
        scroll_to_element(driver, el_acidente)
        time.sleep(0.5)
        
        result = driver.execute_script("""
            var sel = document.getElementById('indicadorAcidente');
            if(!sel) return 'SELECT_NAO_ENCONTRADO';
            for(var i=0; i<sel.options.length; i++) {
                var txt = (sel.options[i].text || '').toLowerCase();
                var lbl = (sel.options[i].getAttribute('label') || '').toLowerCase();
                if(txt.indexOf('acidente') > -1 && (txt.indexOf('não') > -1 || txt.indexOf('nao') > -1)) {
                    sel.selectedIndex = i;
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                    return 'OK:' + i + ':' + sel.options[i].text;
                }
            }
            return 'NAO_ENCONTRADO';
        """)
        scraper.log(f"Resultado seleção indicadorAcidente: {result}", job_id=job_id)
        time.sleep(0.5)
    except Exception as e:
        scraper.log(f"ERRO Indicador Acidente: {type(e).__name__}: {e}", level="ERROR", job_id=job_id)

    # ── 12. Prestador Executante ──
    scraper.log("Passo 12: Prestador Executante", job_id=job_id)
    el_matricula = aguardar_elemento_presente(driver, By.ID, X_MATRICULA_EXECUTANTE_ID, DEFAULT_TIMEOUT)
    scroll_to_element(driver, el_matricula)
    time.sleep(0.5)
    preencher_input(driver, By.ID, X_MATRICULA_EXECUTANTE_ID, cod_prestador)

    # ── 13. Procedimento ──
    scraper.log("Passo 13: Procedimento", job_id=job_id)
    el_proc = aguardar_elemento_presente(driver, By.ID, X_CODIGO_PROCEDIMENTO_ID, DEFAULT_TIMEOUT)
    scroll_to_element(driver, el_proc)
    time.sleep(0.5)
    preencher_input(driver, By.ID, X_CODIGO_PROCEDIMENTO_ID, codigo_procedimento, clear=True)
    preencher_input(driver, By.ID, X_QTD_PROCEDIMENTO_ID, str(qtde_solicitada), clear=True)
    scraper.log(f"Procedimento: {codigo_procedimento} x{qtde_solicitada}", job_id=job_id)

    # ── 13.1 Clicar em Adicionar Procedimento ──
    scraper.log("Passo 13.1: Adicionar Procedimento", job_id=job_id)
    el_adicionar = aguardar_elemento_presente(driver, By.ID, "AdicionarProcedimento", DEFAULT_TIMEOUT)
    scroll_to_element(driver, el_adicionar)
    time.sleep(0.5)
    clicar_elemento(driver, By.ID, "AdicionarProcedimento", DEFAULT_TIMEOUT, js_fallback=True)
    scraper.log("Botão AdicionarProcedimento clicado", job_id=job_id)
    time.sleep(1)

    # ── 14. Upload arquivo RM ──
    scraper.log(f"Passo 14: Upload arquivo RM: {caminho_arquivo_rm}", job_id=job_id)
    el_upload = aguardar_elemento_presente(driver, By.ID, X_UPLOAD_CONTAINER_ID, DEFAULT_TIMEOUT)
    scroll_to_element(driver, el_upload)
    time.sleep(0.5)
    clicar_elemento(driver, By.ID, X_UPLOAD_CONTAINER_ID, DEFAULT_TIMEOUT, js_fallback=True)
    time.sleep(2)  # Aguardar frame de upload

    # Input file (não clicar, apenas send_keys com o caminho)
    file_input = aguardar_elemento_presente(driver, By.ID, X_INPUT_FILE_ID, DEFAULT_TIMEOUT)
    file_input.send_keys(caminho_arquivo_rm)

    # Tipo de documento
    clicar_elemento(driver, By.XPATH, X_TIPO_ARQUIVO_OPT, DEFAULT_TIMEOUT)

    # Anexar
    el_anexar = aguardar_elemento_presente(driver, By.ID, X_BTN_ANEXAR_ID, DEFAULT_TIMEOUT)
    scroll_to_element(driver, el_anexar)
    time.sleep(0.5)
    clicar_elemento(driver, By.ID, X_BTN_ANEXAR_ID, DEFAULT_TIMEOUT, js_fallback=True)
    time.sleep(3)  # Aguardar upload
    scraper.log("Arquivo RM anexado", job_id=job_id)

    # ── 15. Indicação Clínica ──
    scraper.log("Passo 15: Indicação Clínica", job_id=job_id)
    indicacao_el = aguardar_elemento_presente(driver, By.ID, X_INDICACAO_CLINICA_ID, DEFAULT_TIMEOUT)
    scroll_to_element(driver, indicacao_el)
    time.sleep(0.5)
    preencher_input(driver, By.ID, X_INDICACAO_CLINICA_ID, codigo_cid10, clear=True)
    scraper.log(f"Indicação Clínica preenchida com CID: {codigo_cid10}", job_id=job_id)
    time.sleep(1)

    # ── 16. Enviar solicitação ──
    scraper.log("Passo 16: Enviando solicitação...", job_id=job_id)
    el_enviar = aguardar_elemento_presente(driver, By.ID, X_BTN_ENVIAR_ID, DEFAULT_TIMEOUT)
    scroll_to_element(driver, el_enviar)
    time.sleep(0.5)
    clicar_elemento(driver, By.ID, X_BTN_ENVIAR_ID, LONG_TIMEOUT, js_fallback=True)

    # ── 15. Capturar resultado (janela de resposta) ──
    time.sleep(3)
    try:
        switch_to_next_window(driver, timeout=15)
    except Exception as e:
        scraper.log(f"Janela de resultado não abriu: {e}", level="ERROR", job_id=job_id)
        raise ValueError("Falha ao capturar resultado — janela de retorno não apareceu")

    # Capturar guia prestador
    guia_prestador = ""
    try:
        guia_prestador = capturar_texto(driver, By.XPATH, X_GUIA_PRESTADOR, DEFAULT_TIMEOUT)
    except Exception as e:
        scraper.log(f"Não foi possível capturar guia_prestador: {e}", level="WARN", job_id=job_id)

    # Capturar status
    status_guia = ""
    try:
        status_guia = capturar_texto(driver, By.ID, X_STATUS_PROCEDIMENTO_ID, DEFAULT_TIMEOUT)
    except Exception as e:
        scraper.log(f"Não foi possível capturar StatusGuia: {e}", level="WARN", job_id=job_id)

    scraper.log(f"Resultado — Guia Prestador: {guia_prestador}, Status: {status_guia}", job_id=job_id)

    # ── 16. Montar JSON de retorno padronizado ──
    resultado = {
        "guia_prestador": guia_prestador,
        "status_guia": status_guia,
        "numero_guia": guia_prestador,  # Mapeamento para base_guias
        "codigo_terapia": codigo_procedimento,
        "qtde_solicitada": int(qtde_solicitada),
        "cod_prestador": cod_prestador,
    }

    # ── 17. Fechar janela resultado e retornar ──
    try:
        fechar_janela_atual(driver)
    except Exception:
        switch_to_previous_window(driver)

    scraper.log("OP1 - Solicitar Autorização SADT concluída com sucesso", job_id=job_id)
    return [resultado]
