"""
OP1 - Consulta Guias no portal Faturamento
Verifica o status de uma guia específica (se está pendente ou faturada).
"""
from __future__ import annotations
import time
import json
from typing import TYPE_CHECKING
from selenium.webdriver.common.by import By

import os
import sys

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)]
if sys.path[0] != _mod_root:
    sys.path.insert(0, _mod_root)

from core.selenium_helpers import aguardar_elemento

if TYPE_CHECKING:
    from base_scraper import BaseScraper

def run(scraper: BaseScraper, job_data: dict) -> list:
    """
    Executa a consulta de guias no Faturamento Orizon.
    Parâmetros esperados no job_data:
        guia: str
        dataInicio: str (YYYY-MM-DD)
        dataFim: str (YYYY-MM-DD)
        prestador_id: str (ou do scraper)
        reg_ans: str
    """
    job_id = job_data.get("job_id")
    scraper.log("Iniciando OP1 Fature (Consulta Guias)", job_id=job_id)
    driver = scraper.driver

    # Extrair parâmetros
    guia = job_data.get("guia")
    dataInicio = job_data.get("dataInicio")
    dataFim = job_data.get("dataFim")
    prestador_id = job_data.get("prestador_id") or scraper.cod_prestador
    reg_ans = str(job_data.get("reg_ans") or job_data.get("regAns") or "").lstrip("0")

    if not all([guia, dataInicio, dataFim, prestador_id, reg_ans]):
        scraper.log(f"Faltam parâmetros. Valores recebidos: guia={guia}, dataInicio={dataInicio}, dataFim={dataFim}, prestador_id={prestador_id}, reg_ans={reg_ans}", level="ERROR", job_id=job_id)
        raise ValueError("Parâmetros obrigatórios ausentes para consulta de guias de faturamento.")

    # Converte data (DD/MM/YYYY) para (YYYY-MM-DD) se necessário
    if "/" in dataInicio:
        d, m, y = dataInicio.split("/")
        dataInicio = f"{y}-{m}-{d}"
    if "/" in dataFim:
        d, m, y = dataFim.split("/")
        dataFim = f"{y}-{m}-{d}"

    try:
        # Acessar a página para obter cookies e tokens necessários no contexto da sessão
        url_base = "https://portal.orizon.com.br/fature/prestador.html#/guias"
        scraper.log(f"Acessando URL base do Fature: {url_base}", job_id=job_id)
        driver.get(url_base)
        
        # Aguarda a página carregar
        aguardar_elemento(driver, By.ID, "buscarGuias", timeout=20)
        time.sleep(2)
        
        # ── Fechar popups e modais que possam atrapalhar ──
        _fechar_popups(driver, scraper, job_id)

        # Prepara chamada 1: Verificar se tem status 199
        url_chamada_1 = (
            f"https://rest-guia-fature-apicast-production.api.ocppr.orizon.com.br/api/Status_Guia/Get"
            f"?Operadora_Id=&Lote_Id=&Tipo_Guia_Id=&dt_Inicial={dataInicio}&dt_Final={dataFim}"
            f"&Prestador_Id={prestador_id}&StatusGuia=199&Tipo_Entrada_Id=&Critica_Id="
            f"&descricaoLote=&descricaoBeneficiario=&carteirinhaOuGuiaPrestador={guia}"
            f"&numeroGuiaPrestador=&reg_ans="
        )
        
        scraper.log(f"Consultando guias (Chamada 1: pendentes / StatusGuia=199)... URL: {url_chamada_1}", job_id=job_id)
        res1_text = _fetch_via_js(driver, url_chamada_1)
        scraper.log(f"Raw Resposta Chamada 1: {res1_text}", job_id=job_id)
        res1_json = []
        if res1_text:
            try:
                res1_json = json.loads(res1_text)
            except json.JSONDecodeError:
                scraper.log("Falha ao fazer parse do JSON na chamada 1", level="WARN", job_id=job_id)

        # Se encontrou na chamada 1
        if isinstance(res1_json, list) and len(res1_json) > 0:
            status_guia = res1_json[0].get("StatusGuia")
            descricao = res1_json[0].get("Descricao", "Desconhecido")
            scraper.log(f"Guia encontrada na Chamada 1. StatusGuia: {status_guia} ({descricao})", job_id=job_id)
            return [{"guia": guia, "status_guia": status_guia, "descricao": descricao}]

        # Se retornou vazio, tenta a chamada 2: Verificar se tem status 5
        url_chamada_2 = (
            f"https://rest-guia-fature-apicast-production.api.ocppr.orizon.com.br/api/Status_Guia/GetGuiasLote"
            f"?Prestador_Id={prestador_id}&Operadora_Id=48&Status_Guia_Id=5"
            f"&carteirinhaOuNomeBeneficiario={guia}&reg_ans={reg_ans}&numeroGuiaPrestador={guia}"
        )
        
        scraper.log(f"Chamada 1 vazia. Tentando Chamada 2 (Faturadas / Lote)... URL: {url_chamada_2}", job_id=job_id)
        
        res2_text = _fetch_via_js(driver, url_chamada_2)
        scraper.log(f"Raw Resposta Chamada 2: {res2_text}", job_id=job_id)
        res2_json = []
        if res2_text:
            try:
                res2_json = json.loads(res2_text)
            except json.JSONDecodeError:
                scraper.log("Falha ao fazer parse do JSON na chamada 2", level="WARN", job_id=job_id)

        if isinstance(res2_json, list) and len(res2_json) > 0:
            status_guia = res2_json[0].get("StatusGuia")
            descricao = res2_json[0].get("Descricao", "Desconhecido")
            scraper.log(f"Guia encontrada na Chamada 2. StatusGuia: {status_guia} ({descricao})", job_id=job_id)
            return [{"guia": guia, "status_guia": status_guia, "descricao": descricao}]

        # Se não achou em nenhum lugar
        scraper.log("Nenhum dado encontrado para a guia nas duas consultas.", job_id=job_id)
        return [{"guia": guia, "status_guia": "Guia não localizada", "descricao": "Não Encontrado"}]

    except Exception as e:
        scraper.log(f"Erro na consulta de guias do faturamento: {str(e)}", level="ERROR", job_id=job_id)
        raise

def _fechar_popups(driver, scraper, job_id):
    """Fecha popovers e modais que aparecem na tela do faturamento"""
    scraper.log("Verificando se existem popovers ou modais para fechar...", job_id=job_id)
    try:
        # Fechar popover (class="btn btn-sm btn-default")
        popovers = driver.find_elements(By.XPATH, "//*[@class='btn btn-sm btn-default']")
        for p in popovers:
            if p.is_displayed():
                scraper.log("Fechando popover...", job_id=job_id)
                driver.execute_script("arguments[0].click();", p)
                time.sleep(1)
                
        # Fechar modal enviar imagens
        modais = driver.find_elements(By.XPATH, "//*[@id='modal_enviar_imagens']/div/div/button")
        for m in modais:
            if m.is_displayed():
                scraper.log("Fechando modal_enviar_imagens...", job_id=job_id)
                driver.execute_script("arguments[0].click();", m)
                time.sleep(1)
    except Exception as e:
        scraper.log(f"Erro ao tentar fechar popups (pode ser ignorado se não existirem): {e}", level="WARN", job_id=job_id)


def _fetch_via_js(driver, url: str) -> str:
    """
    Executa uma chamada fetch via JS na mesma sessão do navegador para aproveitar
    cookies e headers de autorização automaticamente incluídos pelo browser.
    """
    script = """
    var callback = arguments[arguments.length - 1];
    var url = arguments[0];
    
    var headers = {
        'Accept': 'application/json, text/plain, */*'
    };
    
    // Tentar extrair tokens do storage (comum em SPAs Angular/React)
    var token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || 
                localStorage.getItem('token') || sessionStorage.getItem('token') || 
                localStorage.getItem('jwt') || sessionStorage.getItem('jwt') || '';
                
    if (token) {
        // Remover aspas extras se o token foi salvo via JSON.stringify
        token = token.replace(/^["']|["']$/g, '');
        headers['Authorization'] = 'Bearer ' + token;
    }
    
    var authHeader = localStorage.getItem('Authorization') || sessionStorage.getItem('Authorization');
    if (authHeader) {
        headers['Authorization'] = authHeader.replace(/^["']|["']$/g, '');
    }

    fetch(url, {
        method: 'GET',
        credentials: 'include', // IMPORTANTE: Envia cookies em requisições cross-origin (CORS)
        headers: headers
    })
    .then(response => response.text())
    .then(text => callback(text))
    .catch(err => callback(null));
    """
    return driver.execute_async_script(script, url)
