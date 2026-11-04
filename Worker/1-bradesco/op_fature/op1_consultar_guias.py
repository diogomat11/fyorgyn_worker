"""
OP1 - Consulta Guias no portal Faturamento
Cascata reg_ans × status_guia (PO 2026-10-21): para cada REG ANS (o do job e o
alternativo 421715), tenta GetGuiasLote com cada Status_Guia_Id (prioriza 5).
Fetch robusto: timeout por request (AbortController), retry transiente, medição
de duração e distinção entre "vazio de verdade" e erro (sessão expirada →
SessionExpiredError → re-login pela escada do core/scraper.py).

Evidência da auditoria (jobs 20614-20628): "Authentication failed" era tratado
como lista vazia → falsas "Guia não localizada". Agora 401 é erro de sessão.
"""
from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional, Tuple

from selenium.webdriver.common.by import By

import os
import sys

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)]
if sys.path[0] != _mod_root:
    sys.path.insert(0, _mod_root)

from config.constants import (
    FATURE_API_BASE,
    FATURE_OPERADORA_ID,
    FATURE_STATUS_GUIA_ORDEM,
    FATURE_REG_ANS_FALLBACK,
    FATURE_FETCH_TIMEOUT_S,
    FATURE_SCRIPT_TIMEOUT_S,
    FATURE_FETCH_RETRIES,
    FATURE_THROTTLE_S,
)
from config.settings import OP1_URL  # noqa: F401 (mantido por compatibilidade de imports)
from core.selenium_helpers import aguardar_elemento
from core.exceptions import SessionExpiredError

if TYPE_CHECKING:
    from base_scraper import BaseScraper


# ── Funções puras (testáveis sem Selenium/banco — backend/tests/test_fature_cascata.py) ──

def montar_tentativas(reg_ans_job: str, ordem_status=None, fallback=None) -> List[Tuple[str, int]]:
    """Combinações (reg_ans, status_guia_id) na ordem de tentativa.

    O reg_ans do job vem primeiro; o alternativo (421715) só se for diferente
    (dedup). Status na ordem definida — prioridade para 5 (PO).
    """
    ordem_status = ordem_status if ordem_status is not None else FATURE_STATUS_GUIA_ORDEM
    fallback = fallback if fallback is not None else FATURE_REG_ANS_FALLBACK
    reg_ans_list = [reg_ans_job] + [r for r in fallback if r != reg_ans_job]
    return [(reg, status) for reg in reg_ans_list for status in ordem_status]


def montar_url_get_guias_lote(prestador_id: str, reg_ans: str, status_guia_id: int, guia: str) -> str:
    """URL do GetGuiasLote com os params na ordem observada no portal (PO)."""
    return (
        f"{FATURE_API_BASE}/Status_Guia/GetGuiasLote"
        f"?Prestador_Id={prestador_id}&Operadora_Id={FATURE_OPERADORA_ID}"
        f"&Status_Guia_Id={status_guia_id}"
        f"&carteirinhaOuNomeBeneficiario={guia}&reg_ans={reg_ans}&numeroGuiaPrestador={guia}"
    )


def classificar_fetch(http_status: int, parsed) -> str:
    """Classifica uma resposta do GetGuiasLote.

    ok_com_itens | ok_vazio | transiente (rede/429/5xx) | auth (401/403 HTTP —
    sessão expirada) | invalido (200 com corpo não-lista).
    """
    if http_status == 200:
        if isinstance(parsed, list):
            return "ok_com_itens" if len(parsed) > 0 else "ok_vazio"
        return "invalido"
    if http_status in (401, 403):
        return "auth"
    return "transiente"


# ── Execução ──

def run(scraper: "BaseScraper", job_data: dict) -> list:
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

    # Timeout do Selenium para o execute_async_script (determinístico — antes
    # dependia do default do chromedriver). SEMPRE > FATURE_FETCH_TIMEOUT_S:
    # o AbortController interno estoura primeiro e devolve status 0 classificável.
    try:
        driver.set_script_timeout(FATURE_SCRIPT_TIMEOUT_S)
    except Exception as e:
        scraper.log(f"Aviso ao setar script timeout: {e}", level="WARN", job_id=job_id)

    inicio_op = time.perf_counter()
    tentativas_feitas = 0
    falhas_transporte = 0

    try:
        # Acessar a página para obter cookies e tokens necessários no contexto da sessão
        url_base = "https://portal.orizon.com.br/fature/prestador.html#/guias"
        scraper.log(f"Acessando URL base do Fature: {url_base}", job_id=job_id)
        driver.get(url_base)

        try:
            aguardar_elemento(driver, By.ID, "buscarGuias", timeout=15)
        except Exception:
            scraper.log("Elemento 'buscarGuias' não encontrado (timeout — possível sessão expirada). Prosseguindo com fetch JS para confirmar.", level="WARN", job_id=job_id)
        time.sleep(2)

        _fechar_popups(driver, scraper, job_id)

        # Pré-passo (comportamento anterior mantido): pendentes via Status_Guia/Get
        url_199 = (
            f"{FATURE_API_BASE}/Status_Guia/Get"
            f"?Operadora_Id=&Lote_Id=&Tipo_Guia_Id=&dt_Inicial={dataInicio}&dt_Final={dataFim}"
            f"&Prestador_Id={prestador_id}&StatusGuia=199&Tipo_Entrada_Id=&Critica_Id="
            f"&descricaoLote=&descricaoBeneficiario=&carteirinhaOuGuiaPrestador={guia}"
            f"&numeroGuiaPrestador=&reg_ans="
        )
        scraper.log("Consultando guias (pré-passo: pendentes / StatusGuia=199)...", job_id=job_id)
        parsed, dur_ms, http = _fetch_json(scraper, driver, job_id, url_199)
        tentativas_feitas += 1
        tipo = classificar_fetch(http, parsed)
        if tipo == "ok_com_itens":
            item = parsed[0]
            scraper.log(f"Guia encontrada no pré-passo. StatusGuia: {item.get('StatusGuia')} ({item.get('Descricao', 'Desconhecido')}) [HTTP {http}, {dur_ms}ms]", job_id=job_id)
            return [_resultado(guia, item, reg_ans=reg_ans, status_id=item.get("StatusGuia"),
                               tentativas=tentativas_feitas, duracao_ms=dur_ms)]
        if tipo == "auth":
            raise SessionExpiredError()
        if tipo == "transiente":
            falhas_transporte += 1

        # Cascata GetGuiasLote: reg_ans do job → alternativo; status prioriza 5
        tentativas = montar_tentativas(reg_ans)
        for reg_ans_tentativa, status_id in tentativas:
            url = montar_url_get_guias_lote(prestador_id, reg_ans_tentativa, status_id, guia)
            scraper.log(f"[FATURE] consultando reg_ans={reg_ans_tentativa} status_guia={status_id}...", job_id=job_id)
            parsed, dur_ms, http = _fetch_json(scraper, driver, job_id, url)
            tentativas_feitas += 1
            tipo = classificar_fetch(http, parsed)
            scraper.log(f"[FATURE] reg_ans={reg_ans_tentativa} status_guia={status_id} → HTTP {http} → {dur_ms}ms → "
                        f"{len(parsed) if isinstance(parsed, list) else '?'} item(ns)", job_id=job_id)

            if tipo == "ok_com_itens":
                item = parsed[0]
                scraper.log(f"Guia encontrada. StatusGuia: {item.get('StatusGuia')} ({item.get('Descricao', 'Desconhecido')})", job_id=job_id)
                return [_resultado(guia, item, reg_ans=reg_ans_tentativa, status_id=item.get("StatusGuia"),
                                   tentativas=tentativas_feitas, duracao_ms=dur_ms)]
            if tipo == "auth":
                # "Authentication failed" (auditoria jobs 20614-20628): sessão do
                # Faturi expirada — nunca é "não localizada". Escada do scraper assume.
                raise SessionExpiredError()
            if tipo == "transiente":
                falhas_transporte += 1

            time.sleep(FATURE_THROTTLE_S)

        # Fim da cascata
        dur_total = int((time.perf_counter() - inicio_op) * 1000)
        if falhas_transporte > 0 and falhas_transporte >= tentativas_feitas:
            raise ValueError(
                f"Fature: falha de rede/HTTP em todas as tentativas ({falhas_transporte}) — consulta inconclusiva"
            )
        if falhas_transporte > 0:
            scraper.log(
                f"Cascata concluída com {falhas_transporte} falha(s) de transporte em "
                f"{tentativas_feitas} tentativas — respostas 200 restantes foram vazias.",
                level="WARN", job_id=job_id,
            )
        scraper.log(f"Nenhum dado encontrado para a guia em {tentativas_feitas} consultas ({dur_total}ms no total).", job_id=job_id)
        return [{
            "guia": guia,
            "status_guia": "Guia não localizada",
            "descricao": "Não Encontrado",
            "tentativas": tentativas_feitas,
            "duracao_ms": dur_total,
        }]

    except SessionExpiredError:
        raise
    except Exception as e:
        scraper.log(f"Erro na consulta de guias do faturamento: {str(e)}", level="ERROR", job_id=job_id)
        raise


def _resultado(guia: str, item: dict, reg_ans: str, status_id, tentativas: int, duracao_ms: int) -> dict:
    """Envelope de saída — chaves antigas preservadas (guia/status_guia/descricao)
    + campos informativos novos (reg_ans/status_guia_id/tentativas/duracao_ms)."""
    return {
        "guia": guia,
        "status_guia": item.get("StatusGuia"),
        "descricao": item.get("Descricao", "Desconhecido"),
        "reg_ans": reg_ans,
        "status_guia_id": status_id,
        "tentativas": tentativas,
        "duracao_ms": duracao_ms,
    }


def _fetch_json(scraper, driver, job_id, url: str) -> Tuple[Optional[list], int, int]:
    """GET via fetch JS na sessão do navegador, com timeout por request e retry
    transiente. Retorna (parsed|None, duracao_ms, http_status — 0 = rede/timeout)."""
    for tentativa in range(FATURE_FETCH_RETRIES + 1):
        if tentativa > 0:
            time.sleep(2)  # backoff do retry transiente
        t0 = time.perf_counter()
        http_status, body = _fetch_via_js(driver, url, FATURE_FETCH_TIMEOUT_S)
        dur_ms = int((time.perf_counter() - t0) * 1000)

        if http_status == 200:
            try:
                return json.loads(body), dur_ms, http_status
            except (json.JSONDecodeError, TypeError):
                # Ex.: corpo "Authentication failed" com 200 raro / HTML de erro
                scraper.log(f"Resposta HTTP 200 com corpo não-JSON (primeiros 80 chars): {str(body)[:80]!r}", level="WARN", job_id=job_id)
                return None, dur_ms, -1
        if http_status in (401, 403):
            scraper.log(f"Sessão expirada no Faturi (HTTP {http_status}: {str(body)[:80]!r})", level="ERROR", job_id=job_id)
            return None, dur_ms, http_status
        # transiente (0 = rede/timeout, 429, 5xx) — retry se ainda há tentativas
        scraper.log(f"Falha transiente HTTP {http_status} ({dur_ms}ms){' — retentando' if tentativa < FATURE_FETCH_RETRIES else ''}", level="WARN", job_id=job_id)
    return None, dur_ms, http_status


def _fechar_popups(driver, scraper, job_id):
    """Fecha popovers e modais que aparecem na tela do faturamento"""
    scraper.log("Verificando se existem popovers ou modais para fechar...", job_id=job_id)
    try:
        popovers = driver.find_elements(By.XPATH, "//*[@class='btn btn-sm btn-default']")
        for p in popovers:
            if p.is_displayed():
                scraper.log("Fechando popover...", job_id=job_id)
                driver.execute_script("arguments[0].click();", p)
                time.sleep(1)

        modais = driver.find_elements(By.XPATH, "//*[@id='modal_enviar_imagens']/div/div/button")
        for m in modais:
            if m.is_displayed():
                scraper.log("Fechando modal_enviar_imagens...", job_id=job_id)
                driver.execute_script("arguments[0].click();", m)
                time.sleep(1)
    except Exception as e:
        scraper.log(f"Erro ao tentar fechar popups (pode ser ignorado se não existirem): {e}", level="WARN", job_id=job_id)


def _fetch_via_js(driver, url: str, timeout_s: int):
    """
    Chamada fetch via JS na mesma sessão do navegador (cookies + Bearer do
    storage). AbortController cancela após timeout_s e o callback devolve
    {status, body} — status 0 indica erro de rede/timeout. O callback SEMPRE
    responde antes do set_script_timeout do Selenium.
    """
    script = """
    var callback = arguments[arguments.length - 1];
    var url = arguments[0];
    var timeoutMs = arguments[1];

    var headers = {
        'Accept': 'application/json, text/plain, */*'
    };

    var token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') ||
                localStorage.getItem('token') || sessionStorage.getItem('token') ||
                localStorage.getItem('jwt') || sessionStorage.getItem('jwt') || '';

    if (token) {
        token = token.replace(/^["']|["']$/g, '');
        headers['Authorization'] = 'Bearer ' + token;
    }

    var authHeader = localStorage.getItem('Authorization') || sessionStorage.getItem('Authorization');
    if (authHeader) {
        headers['Authorization'] = authHeader.replace(/^["']|["']$/g, '');
    }

    var controller = new AbortController();
    var timer = setTimeout(function() { controller.abort(); }, timeoutMs);

    fetch(url, {
        method: 'GET',
        credentials: 'include',
        headers: headers,
        signal: controller.signal
    })
    .then(function(response) {
        return response.text().then(function(text) {
            clearTimeout(timer);
            callback({status: response.status, body: text});
        });
    })
    .catch(function(err) {
        clearTimeout(timer);
        callback({status: 0, body: null});
    });
    """
    result = driver.execute_async_script(script, url, int(timeout_s * 1000))
    if not isinstance(result, dict):
        return 0, None
    return result.get("status", 0), result.get("body")
