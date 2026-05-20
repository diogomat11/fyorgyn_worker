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
    scraper.log("Iniciando OP1 Fature (Consulta Guias)")
    driver = scraper.driver

    # Extrair parâmetros
    guia = job_data.get("guia")
    dataInicio = job_data.get("dataInicio")
    dataFim = job_data.get("dataFim")
    prestador_id = job_data.get("prestador_id") or scraper.cod_prestador
    reg_ans = str(job_data.get("reg_ans", "")).lstrip("0")

    if not all([guia, dataInicio, dataFim, prestador_id, reg_ans]):
        scraper.log(f"Faltam parâmetros. Valores recebidos: guia={guia}, dataInicio={dataInicio}, dataFim={dataFim}, prestador_id={prestador_id}, reg_ans={reg_ans}", level="ERROR")
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
        scraper.log(f"Acessando URL base do Fature: {url_base}")
        driver.get(url_base)
        
        # Aguarda a página carregar
        aguardar_elemento(driver, By.ID, "buscarGuias", timeout=20)
        time.sleep(2)

        # Prepara chamada 1: Verificar se tem status 199
        url_chamada_1 = (
            f"https://rest-guia-fature-apicast-production.api.ocppr.orizon.com.br/api/Status_Guia/Get"
            f"?Operadora_Id=&Lote_Id=&Tipo_Guia_Id=&dt_Inicial={dataInicio}&dt_Final={dataFim}"
            f"&Prestador_Id={prestador_id}&StatusGuia=199&Tipo_Entrada_Id=&Critica_Id="
            f"&descricaoLote=&descricaoBeneficiario=&carteirinhaOuGuiaPrestador={guia}"
            f"&numeroGuiaPrestador=&reg_ans="
        )
        
        scraper.log("Consultando guias (Chamada 1: pendentes / StatusGuia=199)...")
        res1_text = _fetch_via_js(driver, url_chamada_1)
        res1_json = []
        if res1_text:
            try:
                res1_json = json.loads(res1_text)
            except json.JSONDecodeError:
                scraper.log("Falha ao fazer parse do JSON na chamada 1", level="WARN")

        # Se encontrou na chamada 1
        if isinstance(res1_json, list) and len(res1_json) > 0:
            status_guia = res1_json[0].get("StatusGuia")
            descricao = res1_json[0].get("Descricao", "Desconhecido")
            scraper.log(f"Guia encontrada na Chamada 1. StatusGuia: {status_guia} ({descricao})")
            return [{"guia": guia, "status_guia": status_guia, "descricao": descricao}]

        # Se retornou vazio, tenta a chamada 2: Verificar se tem status 5
        scraper.log("Chamada 1 vazia. Tentando Chamada 2 (Faturadas / Lote)...")
        url_chamada_2 = (
            f"https://rest-guia-fature-apicast-production.api.ocppr.orizon.com.br/api/Status_Guia/GetGuiasLote"
            f"?Prestador_Id={prestador_id}&Operadora_Id=48&Status_Guia_Id=5"
            f"&carteirinhaOuNomeBeneficiario={guia}&reg_ans={reg_ans}&numeroGuiaPrestador={guia}"
        )
        
        res2_text = _fetch_via_js(driver, url_chamada_2)
        res2_json = []
        if res2_text:
            try:
                res2_json = json.loads(res2_text)
            except json.JSONDecodeError:
                scraper.log("Falha ao fazer parse do JSON na chamada 2", level="WARN")

        if isinstance(res2_json, list) and len(res2_json) > 0:
            status_guia = res2_json[0].get("StatusGuia")
            descricao = res2_json[0].get("Descricao", "Desconhecido")
            scraper.log(f"Guia encontrada na Chamada 2. StatusGuia: {status_guia} ({descricao})")
            return [{"guia": guia, "status_guia": status_guia, "descricao": descricao}]

        # Se não achou em nenhum lugar
        scraper.log("Nenhum dado encontrado para a guia nas duas consultas.")
        return [{"guia": guia, "status_guia": "Guia não localizada", "descricao": "Não Encontrado"}]

    except Exception as e:
        scraper.log(f"Erro na consulta de guias do faturamento: {str(e)}", level="ERROR")
        raise

def _fetch_via_js(driver, url: str) -> str:
    """
    Executa uma chamada fetch via JS na mesma sessão do navegador para aproveitar
    cookies e headers de autorização automaticamente incluídos pelo browser.
    """
    script = """
    var callback = arguments[arguments.length - 1];
    fetch(arguments[0], {
        method: 'GET',
        headers: {
            'Accept': 'application/json, text/plain, */*'
        }
    })
    .then(response => response.text())
    .then(text => callback(text))
    .catch(err => callback(null));
    """
    return driver.execute_async_script(script, url)
