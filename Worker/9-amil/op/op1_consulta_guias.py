"""
OP1 — Consulta de Guias (pedidos de autorização) AMIL.

Padrão do 1-bradesco/op_fature/op1_consultar_guias.py: fetch via JS no contexto
autenticado do SPA (cookies + tokens do storage — decisão D4), SEM Selenium
para a extração em si.

CONTRATO CONFIRMADO no portal real (DevTools, 2026-11-20):
  - Tokens: localStorage['acesso-info'] → tokenInfo.accessToken (Bearer,
    ROTACIONA a cada ~30 min — reler ANTES DE CADA requisição), sessionToken
    (x-session) e credenciadoInfo.codigo (x-user). Ver core/session_extractor.py.
  - 404 com messageKey 'integracao.pedido.autorizacao.nao.encontrado' =
    resultado VAZIO (não é erro — sem retry).
  - 403 com HTML 'Acesso Negado' = bloqueio Akamai na edge (UA headless
    'HeadlessChrome' causa isso — preferir SGUCARD_HEADLESS=false); o re-login
    renova o sensor e vale como recuperação.

Fluxo (docs/plano_amil_op0_op1.md, decisões D6/D7/D9):
  - Filtros (D6): senha (senhaAutorizacao, SEM datas) > carteirinha
    (numeroAssociado, mantém datas) > intervalo de datas obrigatório.
    Sempre: codigoCredenciado + limit=PAGE_LIMIT + sort=-numeroPedido.
    ATENÇÃO: o nome do query param 'senhaAutorizacao' é HIPÓTESE a validar
    na 1ª execução real (plano B no doc de fluxo).
  - Paginação (D7): start=1, 11, 21... até ceil(totalCount/limit), cap
    MAX_PAGINAS — independe dos links.next (base distinta).
  - Detalhe (D9): GET /{numeroPedido}?numeroAssociado={n} enriquece cada
    record (procedimentos, pacote, pedidoConfirmado, numeroGuia seq001).

Funções PURAS testáveis no topo (sem Selenium — backend/tests/test_amil_op1.py):
montar_params_busca, calcular_starts, montar_url_lista, montar_url_detalhe,
mapear_pedido_para_records (extrair_tokens_pagina usa driver; as cascatas puras
estão em core/session_extractor.py).
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
import urllib.parse
from typing import TYPE_CHECKING, List, Optional, Tuple

from selenium.webdriver.support.ui import WebDriverWait

# ── Isolate Environment (mesma defesa do 1-bradesco/102-caesan) ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)]
if sys.path[0] != _mod_root:
    sys.path.insert(0, _mod_root)

from config.constants import (
    PEDIDOS_URL,
    API_PEDIDOS,
    ACCEPT_HEADER,
    PAGE_LIMIT,
    MAX_PAGINAS,
    MAX_GUIAS_DETALHE,
    FETCH_TIMEOUT_S,
    SCRIPT_TIMEOUT_S,
    FETCH_RETRIES,
    THROTTLE_S,
    BACKOFF_S,
    LOTE_CONCORRENCIA,
    LOTE_TAMANHO_DETALHE,
    LOTE_BATCH_TIMEOUT_S,
)
from core.exceptions import SessionExpiredError
from core.session_extractor import extrair_tokens_pagina  # cascata D4 (a→b→c)

if TYPE_CHECKING:
    from base_scraper import BaseScraper


# ═══════════════ Funções puras (testáveis sem Selenium) ═══════════════

def _normalizar_data(valor) -> Optional[str]:
    """Normaliza datas para YYYY-MM-DD (aceita 'DD/MM/YYYY', padrão bradesco).
    Já-ISO passa direto; vazio/inválido devolve None."""
    if not valor:
        return None
    v = str(valor).strip()
    if "/" in v:
        partes = v.split("/")
        if len(partes) == 3:
            d, m, y = partes
            return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
        return None
    return v[:10] if len(v) >= 10 else None


def montar_params_busca(params: dict, cod_prestador: str) -> dict:
    """Query params da listagem — precedência D6 (revisada pelo portal real).

    Contrato CONFIRMADO no portal (DevTools 2026-11-20): o filtro unificado é
    `identificacao` ("Número da carteirinha, senha ou número do pedido") e,
    com identificador, a API DESCARTA as datas (o próprio SPA não as envia).
    O nome `senhaAutorizacao` (hipótese original) retorna 400
    'pedido.nao.encontrato' — NÃO usar.

    - senha informada → identificacao=<senha> SEM datas (regra do usuário);
    - senão guia (numeroPedido) → identificacao=<guia> SEM datas;
    - senão carteirinha → identificacao=<carteirinha> SEM datas;
    - senão datas obrigatórias (dataAutorizacaoDe/Ate).
    Sempre: codigoCredenciado, limit=PAGE_LIMIT, sort=-numeroPedido.
    Datas aceitas em 'YYYY-MM-DD' ou 'DD/MM/YYYY' (normalizadas).
    """
    params = params or {}
    senha = str(params.get("senha") or params.get("senhaAutorizacao") or "").strip()
    guia = str(params.get("guia") or params.get("numeroPedido") or "").strip()
    carteirinha = str(params.get("carteirinha") or params.get("numeroAssociado") or "").strip()
    data_ini = _normalizar_data(params.get("data_ini") or params.get("dataInicio"))
    data_fim = _normalizar_data(params.get("data_fim") or params.get("dataFim"))

    if not cod_prestador:
        raise ValueError("AMIL_OP1_SEM_PRESTADOR: cod_prestador ausente (params do job e user_convenios).")

    query = {
        "codigoCredenciado": str(cod_prestador),
        "limit": PAGE_LIMIT,
        "sort": "-numeroPedido",
    }

    identificador = senha or guia or carteirinha
    if identificador:
        # D6 revisada: identificador dispensa datas (contrato real da API)
        query["identificacao"] = identificador
        return query

    if not (data_ini and data_fim):
        raise ValueError(
            "AMIL_OP1_SEM_FILTRO: informe ao menos um filtro (senha, carteirinha, "
            "guia ou período data_ini/data_fim)."
        )
    query["dataAutorizacaoDe"] = data_ini
    query["dataAutorizacaoAte"] = data_fim
    return query


def calcular_starts(total_count: int, limit: int) -> List[int]:
    """Starts de paginação determinística (D7): [1, 11, 21, ...].

    Primeira página = start 1; próximas incrementam `limit`; nº de páginas =
    ceil(total_count/limit) com safety cap MAX_PAGINAS. total 0/negativo → [].
    """
    if not total_count or total_count <= 0 or not limit or limit <= 0:
        return []
    paginas = min(math.ceil(int(total_count) / int(limit)), MAX_PAGINAS)
    return [1 + i * limit for i in range(paginas)]


def montar_url_lista(query: dict) -> str:
    """URL da listagem: API_PEDIDOS + querystring (urlencode)."""
    return f"{API_PEDIDOS}?{urllib.parse.urlencode(query)}"


def montar_url_detalhe(guia: str, numero_associado: str) -> str:
    """URL do detalhe (D9): GET /{numeroPedido}?numeroAssociado={numeroAssociado}."""
    guia_q = urllib.parse.quote(str(guia), safe="")
    assoc_q = urllib.parse.quote(str(numero_associado or ""), safe="")
    return f"{API_PEDIDOS}/{guia_q}?numeroAssociado={assoc_q}"


def _data10(valor) -> Optional[str]:
    """Data ISO-like truncada para os 10 primeiros chars (YYYY-MM-DD)."""
    if not valor:
        return None
    return str(valor)[:10]


def mapear_pedido_para_records(pedido: dict, detalhe: Optional[dict] = None) -> List[dict]:
    """Mapeia um pedido da listagem (+ detalhe opcional) para records do hub.

    Contrato com guias_sync_service (chaves EXATAS — plano §3):
    1 record por item de detalhe.sequenciaPrincipal.procedimentosMedicos;
    sem detalhe/procedimentos → 1 record mínimo com os dados da listagem.
    numeroGuia/pedidoConfirmado/validadeSenhaAutorizacao/pacotesAutorizados
    vêm do DETALHE; o restante da listagem.
    """
    pedido = pedido or {}
    detalhe = detalhe or {}

    # pacotesAutorizados vive DENTRO de sequenciaPrincipal (contrato real —
    # captura do usuário e DevTools 2026-11-20); fallback na raiz por robustez.
    sequencia = detalhe.get("sequenciaPrincipal") or {}
    pacotes = sequencia.get("pacotesAutorizados") or detalhe.get("pacotesAutorizados") or []
    codigo_faturamento = None
    if pacotes and isinstance(pacotes[0], dict):
        codigo_faturamento = pacotes[0].get("codigo")

    base = {
        "guia": pedido.get("numeroPedido"),
        "guia_prestador": detalhe.get("numeroGuia"),
        # carteirinha SEMPRE como TEXTO — o numeroAssociado da AMIL tem zeros à
        # esquerda ("080988488"); qualquer coerção numérica os apagaria e
        # quebraria o vínculo com a carteirinha cadastrada (regra PO 2026-11-21).
        "carteirinha": str(pedido.get("numeroAssociado") or "") or None,
        "codigo_beneficiario": str(pedido.get("numeroAssociado") or "") or None,
        "paciente": pedido.get("nomeAssociado"),
        "status_guia": pedido.get("situacao"),
        "senha": pedido.get("senhaAutorizacao"),
        "data_solicitacao": _data10(pedido.get("dataSolicitacao")),
        "data_autorizacao": _data10(pedido.get("dataAutorizacao")),
        "validade": _data10(detalhe.get("validadeSenhaAutorizacao") or pedido.get("dataValidade")),
        "codigo_terapia": None,
        "nome_terapia": None,
        "qtde_solicitada": None,
        "sessoes_autorizadas": None,
        "status_token": detalhe.get("pedidoConfirmado"),
        "codigo_faturamento": codigo_faturamento,
    }

    procedimentos = sequencia.get("procedimentosMedicos") or []
    if not procedimentos:
        # Sem detalhe (ou detalhe sem procedimentos): record mínimo da listagem
        return [base]

    records = []
    for proc in procedimentos:
        if not isinstance(proc, dict):
            continue
        record = dict(base)
        record["codigo_terapia"] = proc.get("codigo")
        record["nome_terapia"] = proc.get("nome")
        record["qtde_solicitada"] = proc.get("quantidadeSolicitada")
        record["sessoes_autorizadas"] = proc.get("quantidadeAutorizada")
        records.append(record)
    return records or [base]


def _extrair_total_e_pedidos(payload) -> Tuple[int, List[dict]]:
    """Shape defensivo da resposta da listagem: total em totalCount/total/
    totalcount/count; lista em pedidos/pedidosAutorizacao/content/items/lista
    (ou a própria resposta quando é lista). Retorna (0, []) se irreconhecível."""
    if isinstance(payload, list):
        return len(payload), [p for p in payload if isinstance(p, dict)]
    if not isinstance(payload, dict):
        return 0, []

    total = 0
    for chave in ("totalCount", "totalcount", "total", "count"):
        valor = payload.get(chave)
        if isinstance(valor, int):
            total = valor
            break
        if isinstance(valor, str) and valor.isdigit():
            total = int(valor)
            break

    pedidos: List[dict] = []
    for chave in ("pedidos", "pedidosAutorizacao", "content", "items", "lista"):
        valor = payload.get(chave)
        if isinstance(valor, list):
            pedidos = [p for p in valor if isinstance(p, dict)]
            break
    if not pedidos:
        embedded = payload.get("_embedded")
        if isinstance(embedded, dict):
            for valor in embedded.values():
                if isinstance(valor, list):
                    pedidos = [p for p in valor if isinstance(p, dict)]
                    break
    return total, pedidos


def dividir_em_lotes(itens: list, tamanho: int) -> List[list]:
    """Divide uma lista em lotes de `tamanho` (último pode ser menor).

    Perf (incidente jobs 28845/28846): detalhes sequenciais custavam
    N × (round-trip Selenium + fetch + throttle) ≈ 11 min para 199 guias.
    Em lote, N fetches concorrentes rodam DENTRO do navegador em uma única
    chamada execute_async_script — ~9 lotes de 24 cobrem 199 guias em ~1 min.
    """
    itens = list(itens or [])
    if tamanho <= 0:
        return [itens] if itens else []
    return [itens[i:i + tamanho] for i in range(0, len(itens), tamanho)]


# ═══════════════ Execução (com driver) ═══════════════

def _montar_headers(tokens: dict) -> dict:
    """Headers vendor da API AMIL a partir dos tokens do acesso-info (D4):
    accept + content-type + authorization (Bearer) + x-session + x-user."""
    headers = {
        "accept": ACCEPT_HEADER,
        "content-type": "application/json",
    }
    if tokens.get("authorization"):
        headers["authorization"] = tokens["authorization"]
    if tokens.get("x_session"):
        headers["x-session"] = tokens["x_session"]
    if tokens.get("x_user"):
        headers["x-user"] = tokens["x_user"]
    return headers


def _fetch_via_js(driver, url: str, tokens: dict, timeout_s: int):
    """GET via fetch JS na sessão do navegador (padrão bradesco).

    credentials:'include' leva os cookies (JSESSIONID/Akamai). AbortController
    cancela após timeout_s → status 0; o callback SEMPRE responde antes do
    set_script_timeout do Selenium.
    """
    headers = _montar_headers(tokens)

    script = """
    var callback = arguments[arguments.length - 1];
    var url = arguments[0];
    var timeoutMs = arguments[1];
    var headers = arguments[2];

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
        callback({status: 0, body: (err && err.message) ? err.message : 'network error'});
    });
    """
    result = driver.execute_async_script(script, url, int(timeout_s * 1000), headers)
    if not isinstance(result, dict):
        return 0, None
    return result.get("status", 0), result.get("body")


# Pool de fetches concorrentes DENTRO do navegador — um único round-trip
# Selenium devolve N respostas (perf: incidente jobs 28845/28846).
_LOTE_JS = """
var callback = arguments[arguments.length - 1];
var urls = arguments[0];
var headers = arguments[1];
var timeoutMs = arguments[2];
var maxConc = arguments[3];

function fetchOne(url) {
    return new Promise(function(resolve) {
        var ctrl = new AbortController();
        var t = setTimeout(function() { ctrl.abort(); }, timeoutMs);
        fetch(url, {method: 'GET', credentials: 'include', headers: headers, signal: ctrl.signal})
            .then(function(r) {
                return r.text().then(function(txt) {
                    clearTimeout(t);
                    resolve({url: url, status: r.status, body: txt});
                });
            })
            .catch(function(e) {
                clearTimeout(t);
                resolve({url: url, status: 0, body: (e && e.message) ? e.message : 'network error'});
            });
    });
}

var resultados = [];
var fila = urls.slice();
var ativos = 0;
function proxima() {
    if (!fila.length && !ativos) { callback(resultados); return; }
    while (ativos < maxConc && fila.length) {
        ativos++;
        fetchOne(fila.shift()).then(function(r) {
            ativos--;
            resultados.push(r);
            proxima();
        });
    }
}
proxima();
"""


def _fetch_em_lote(driver, urls: List[str], tokens: dict, timeout_s: int,
                   max_conc: int = LOTE_CONCORRENCIA) -> dict:
    """Dispara N fetches concorrentes no contexto autenticado do SPA e devolve
    {url: (status, body)} — um único round-trip Selenium para o lote inteiro.

    Cada fetch tem AbortController próprio (timeout_s); a chamada batch inteira
    responde dentro do set_script_timeout (LOTE_BATCH_TIMEOUT_S > timeout_s).
    """
    if not urls:
        return {}
    tokens = tokens or {}
    headers = _montar_headers(tokens)
    try:
        driver.set_script_timeout(max(SCRIPT_TIMEOUT_S, int(timeout_s) + 10))
    except Exception:
        pass
    resultados = driver.execute_async_script(
        _LOTE_JS, list(urls), headers, int(timeout_s * 1000), int(max_conc)
    )
    mapa = {}
    for item in resultados or []:
        if isinstance(item, dict) and item.get("url") in urls:
            mapa[item["url"]] = (item.get("status", 0), item.get("body"))
    for url in urls:
        mapa.setdefault(url, (0, "sem resposta do lote"))
    return mapa


# Chave de resposta 404-vazio da API AMIL (contrato confirmado no portal real:
# filtro sem pedidos → 404 JSON, NÃO é erro)
KEY_MSG_404_VAZIO = "integracao.pedido.autorizacao.nao.encontrado"


def _eh_404_vazio(http_status: int, body) -> bool:
    """404 com messageKey de 'nenhum pedido encontrado' = resultado VAZIO
    (contrato real da API — não é falha, não deve ter retry)."""
    if http_status != 404:
        return False
    try:
        parsed = json.loads(body) if isinstance(body, (str, bytes)) else body
        return isinstance(parsed, dict) and parsed.get("messageKey") == KEY_MSG_404_VAZIO
    except Exception:
        return False


def _fetch_json(scraper, driver, job_id, url: str, tokens_fn) -> Optional[dict]:
    """Fetch com classificação de status e retry transiente (1x, backoff 2s).

    tokens_fn: callable que devolve os headers ATUAIS do storage — o accessToken
    da AMIL rotaciona a cada ~30 min, então os tokens são re-extraídos ANTES DE
    CADA tentativa (não se cacheia Bearer/JWT entre requisições).

    Contratos:
      200      → JSON parseado (corpo não-JSON → erro logado);
      404 vazio → None (resultado sem pedidos — chamador trata como lista vazia);
      401/403  → SessionExpiredError (escada de re-login do core); 403 com HTML
                 'Acesso Negado' recebe diagnóstico Akamai (UA headless);
      5xx/0    → retry (FETCH_RETRIES) e, esgotado, erro.
    """
    body = None
    http_status = 0
    for tentativa in range(FETCH_RETRIES + 1):
        if tentativa > 0:
            time.sleep(BACKOFF_S)
            scraper.log(f"Retry {tentativa}/{FETCH_RETRIES} após HTTP {http_status}: {url[:120]}", level="WARN", job_id=job_id)
        tokens = tokens_fn() or {}
        http_status, body = _fetch_via_js(driver, url, tokens, FETCH_TIMEOUT_S)

        if http_status == 200:
            try:
                parsed = json.loads(body)
            except (json.JSONDecodeError, TypeError):
                scraper.log(
                    f"HTTP 200 com corpo não-JSON (primeiros 80 chars): {str(body)[:80]!r}",
                    level="WARN", job_id=job_id,
                )
                raise ValueError("AMIL_API_RESPOSTA_INVALIDA: corpo não-JSON na API de pedidos")
            time.sleep(THROTTLE_S)
            return parsed
        if _eh_404_vazio(http_status, body):
            time.sleep(THROTTLE_S)
            return None
        if http_status in (401, 403):
            corpo = str(body or "")
            akamai = "Acesso Negado" in corpo or "<!doctype html" in corpo.lower()
            if akamai:
                scraper.log(
                    f"HTTP {http_status} — página 'Acesso Negado' do Akamai na API "
                    f"(bot-score reprovado; o UA headless ('HeadlessChrome') causa isso "
                    f"na edge — preferir SGUCARD_HEADLESS=false). Corpo: {corpo[:80]!r}",
                    level="ERROR", job_id=job_id,
                )
                raise SessionExpiredError(
                    f"SESSAO_EXPIRADA: HTTP {http_status} Akamai 'Acesso Negado' na API "
                    f"de pedidos-autorizacao — tentando re-login para renovar sensor"
                )
            scraper.log(
                f"Sessão expirada na API AMIL (HTTP {http_status}: {corpo[:80]!r})",
                level="ERROR", job_id=job_id,
            )
            raise SessionExpiredError(f"SESSAO_EXPIRADA: HTTP {http_status} na API de pedidos-autorizacao")
        # transiente (0 = rede/timeout, 429, 5xx) — segue para retry
        scraper.log(f"Falha transiente HTTP {http_status} em {url[:120]}", level="WARN", job_id=job_id)
    raise ValueError(f"AMIL_API_TRANSIENTE: HTTP {http_status} persistiu após {FETCH_RETRIES + 1} tentativas")


def _parse_item_lote(http_status: int, body, url: str):
    """Classifica UMA resposta do lote. Retorna:
    - dict   → JSON 200 parseado;
    - None   → 404 vazio (contrato real — sem dados para a url);
    - ('transiente', motivo) → item para retry em lote;
    - levanta SessionExpiredError em 401/403 (escada de re-login do core)."""
    corpo = str(body or "")
    if http_status in (401, 403):
        akamai = "Acesso Negado" in corpo or "<!doctype html" in corpo.lower()
        raise SessionExpiredError(
            f"SESSAO_EXPIRADA: HTTP {http_status} "
            + ("Akamai 'Acesso Negado' — preferir SGUCARD_HEADLESS=false" if akamai else "na API de pedidos-autorizacao")
            + f" (url={url[:100]})"
        )
    if _eh_404_vazio(http_status, body):
        return None
    if http_status == 200:
        try:
            return json.loads(corpo)
        except (json.JSONDecodeError, TypeError):
            return ("transiente", f"200 não-JSON: {corpo[:60]!r}")
    return ("transiente", f"HTTP {http_status}")


def _fetch_lote_json(scraper, driver, job_id, urls: List[str], tokens_fn, timeout_s: int = LOTE_BATCH_TIMEOUT_S) -> dict:
    """Lote de urls com classificação por item e UM retry batch para transientes.

    Tokens re-extraídos ANTES DE CADA tentativa (rotação de ~30 min do accessToken).
    401/403 em qualquer item aborta o lote (SessionExpiredError → escada do core).
    Retorna {url: json_dict|None} — None = vazio.
    """
    pendentes = list(urls)
    resultado: dict = {}
    for tentativa in range(FETCH_RETRIES + 1):
        if not pendentes:
            break
        if tentativa > 0:
            time.sleep(BACKOFF_S)
            scraper.log(
                f"Retry batch {tentativa}/{FETCH_RETRIES} para {len(pendentes)} url(s) transiente(s)",
                level="WARN", job_id=job_id,
            )
        tokens = tokens_fn() or {}
        mapa = _fetch_em_lote(driver, pendentes, tokens, timeout_s)
        transientes = []
        for url in pendentes:
            status, body = mapa.get(url, (0, "sem resposta"))
            parsed = _parse_item_lote(status, body, url)
            if isinstance(parsed, tuple) and parsed[0] == "transiente":
                transientes.append(url)
                if tentativa == FETCH_RETRIES:  # esgotou — loga e segue sem a url
                    scraper.log(f"Item transiente sem retry disponível ({parsed[1]}): {url[:120]}", level="WARN", job_id=job_id)
            else:
                resultado[url] = parsed
        pendentes = transientes
    return resultado


def run(scraper: "BaseScraper", job_data: dict) -> list:
    """
    Executa a consulta de guias (pedidos de autorização) AMIL.

    Parâmetros esperados no job_data (D6 — pelo menos um filtro):
        senha: str (senha de autorização) OU
        carteirinha: str OU
        data_ini / data_fim: str ('YYYY-MM-DD' ou 'DD/MM/YYYY')
    """
    job_id = job_data.get("job_id")
    scraper.log("Iniciando OP1 AMIL (Consulta Guias / pedidos-autorizacao)", job_id=job_id)
    driver = scraper.driver

    cod_prestador = str(scraper.cod_prestador or job_data.get("cod_prestador") or "").strip()

    # Query params (valida filtros e cod_prestador — funções puras acima)
    query = montar_params_busca(job_data, cod_prestador)
    scraper.log(f"Filtros da busca: { {k: (v if k != 'senhaAutorizacao' else '***') for k, v in query.items()} }", job_id=job_id)

    # 1. Abrir o SPA na área de pedidos — valida a sessão no contexto certo
    driver.get(PEDIDOS_URL)
    url_apos_load = (driver.current_url or "").lower()
    if "/login" in url_apos_load:
        raise SessionExpiredError(
            f"SESSAO_EXPIRADA: {PEDIDOS_URL} redirecionou para {url_apos_load} — refazendo login"
        )

    # 2. Esperar carregamento (readyState + sleep curto p/ boot do SPA)
    try:
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass
    time.sleep(2)

    # Timeout do Selenium p/ execute_async_script — SEMPRE > FETCH_TIMEOUT_S
    try:
        driver.set_script_timeout(SCRIPT_TIMEOUT_S)
    except Exception as e:
        scraper.log(f"Aviso ao setar script timeout: {e}", level="WARN", job_id=job_id)

    # Tokens do storage em runtime (D4). O accessToken rotaciona a cada ~30 min
    # e o SPA reescreve acesso-info no refresh: tokens_fn re-extrai ANTES DE
    # CADA requisição (cache de Bearer/JWT entre calls causaria 401 tardio).
    tokens_fn = lambda: extrair_tokens_pagina(driver)  # noqa: E731
    tokens_iniciais = tokens_fn()
    scraper.log(
        f"Tokens de sessão: authorization={'sim' if tokens_iniciais.get('authorization') else 'NÃO'} | "
        f"x_session={'sim' if tokens_iniciais.get('x_session') else 'NÃO'} | x_user={tokens_iniciais.get('x_user') or '—'}",
        job_id=job_id,
    )
    if not tokens_iniciais.get("authorization") or not tokens_iniciais.get("x_session"):
        # Sem acesso-info o fetch vai 401/403 — aborta cedo com diagnóstico
        # (fonte primária é localStorage['acesso-info'] do login da OP0).
        raise SessionExpiredError(
            "SESSAO_EXPIRADA: tokens ausentes no acesso-info — sessão do portal "
            "não está ativa neste driver; refazendo login"
        )

    # 3. Primeira chamada (start=1) → totalCount + pedidos da página 1
    url_pag1 = montar_url_lista(dict(query, start=1))
    scraper.log(f"Consultando listagem (start=1): {url_pag1}", job_id=job_id)
    payload = _fetch_json(scraper, driver, job_id, url_pag1, tokens_fn)
    if payload is None:
        # Contrato real: 404 'nenhum pedido encontrado' = resultado vazio
        total_count, pedidos = 0, []
        scraper.log("Listagem sem pedidos para os filtros informados (404 vazio).", job_id=job_id)
    else:
        total_count, pedidos = _extrair_total_e_pedidos(payload)
    scraper.log(f"Página 1: {len(pedidos)} pedido(s) | totalCount={total_count}", job_id=job_id)

    todos_pedidos = list(pedidos)

    # 4. Paginar os demais starts (D7) — página 1 já veio. As páginas são
    # independentes (start fixo por página): TODAS em um único lote paralelo
    # no navegador (perf job 28845: 19 páginas sequenciais ≈ 30-60s → 1 lote).
    starts = [s for s in calcular_starts(total_count, PAGE_LIMIT) if s != 1]
    if starts:
        urls_paginas = [montar_url_lista(dict(query, start=s)) for s in starts]
        scraper.log(f"Paginação em lote paralelo: {len(starts)} página(s) restantes...", job_id=job_id)
        mapa_paginas = _fetch_lote_json(scraper, driver, job_id, urls_paginas, tokens_fn)
        for url_pag, payload_pag in mapa_paginas.items():
            if payload_pag is None:
                continue  # 404 vazio na página (dado mudou entre chamadas) — pula
            _, pedidos_pag = _extrair_total_e_pedidos(payload_pag)
            todos_pedidos.extend(pedidos_pag)
        scraper.log(f"Páginação concluída: {len(todos_pedidos)}/{total_count} pedido(s) coletados.", job_id=job_id)

    # 5. Detalhe por pedido (D9) em LOTES PARALELOS no navegador. Sequencial
    # custava N × (round-trip Selenium + fetch + throttle) ≈ 11 min para 199
    # guias (incidentes 28845/28846); em lotes de 24 com 6 concorrentes ≈ 1 min.
    records: List[dict] = []
    detalhes_coletados = 0
    detalhes_vazios = 0
    detalhe_truncado = False
    pedidos_para_detalhe = todos_pedidos[:MAX_GUIAS_DETALHE]
    if len(todos_pedidos) > MAX_GUIAS_DETALHE:
        detalhe_truncado = True
        scraper.log(
            f"Cap de detalhes atingido ({MAX_GUIAS_DETALHE}) — pedidos excedentes "
            f"entrarão como record mínimo (sem procedimentos).",
            level="WARN", job_id=job_id,
        )

    total_pedidos = len(pedidos_para_detalhe)
    if total_pedidos:
        scraper.log(f"Fase de detalhes em lote paralelo: {total_pedidos} pedido(s) "
                    f"({len(dividir_em_lotes(pedidos_para_detalhe, LOTE_TAMANHO_DETALHE))} lote(s) "
                    f"de {LOTE_TAMANHO_DETALHE}, {LOTE_CONCORRENCIA} concorrentes).", job_id=job_id)

    detalhes_map = {}  # url → detalhe dict | None (vazio)
    for indice_lote, lote in enumerate(dividir_em_lotes(pedidos_para_detalhe, LOTE_TAMANHO_DETALHE), start=1):
        urls_lote = [montar_url_detalhe(p.get("numeroPedido"), p.get("numeroAssociado"))
                     for p in lote if p.get("numeroPedido")]
        if not urls_lote:
            continue
        mapa = _fetch_lote_json(scraper, driver, job_id, urls_lote, tokens_fn)
        ok_no_lote = sum(1 for v in mapa.values() if isinstance(v, dict))
        vazios_no_lote = sum(1 for v in mapa.values() if v is None)
        detalhes_coletados += ok_no_lote
        detalhes_vazios += vazios_no_lote
        detalhes_map.update(mapa)
        scraper.log(
            f"Lote {indice_lote}: +{ok_no_lote} detalhe(s), {vazios_no_lote} vazio(s) "
            f"(acumulado {detalhes_coletados}/{total_pedidos}).",
            job_id=job_id,
        )

    for pedido in todos_pedidos:
        numero_pedido = pedido.get("numeroPedido")
        detalhe = None
        if numero_pedido:
            url_det = montar_url_detalhe(numero_pedido, pedido.get("numeroAssociado"))
            detalhe = detalhes_map.get(url_det)
        records.extend(mapear_pedido_para_records(pedido, detalhe))

    if detalhes_vazios:
        scraper.log(f"{detalhes_vazios} detalhe(s) vieram 404-vazio (pedido sem detalhe exposto).", level="WARN", job_id=job_id)

    scraper.log(
        f"OP1 concluída: {len(todos_pedidos)} pedido(s) → {len(records)} record(s) | "
        f"{detalhes_coletados} detalhe(s) | filtros={ {k: (v if k != 'senhaAutorizacao' else '***') for k, v in query.items()} }",
        job_id=job_id,
    )

    # 6. Records + metadados finais. Item com chave '_meta' é IGNORADO pelo
    # guias_sync_service (sem 'guia' → skipped), portanto seguro no result_data.
    records.append({
        "_meta": {
            "total_count": total_count,
            "paginas": len(starts) + 1,
            "guias_detalhe": detalhes_coletados,
            "detalhe_truncado": detalhe_truncado,
            "filtro": {k: (v if k != "senhaAutorizacao" else "***") for k, v in query.items()},
        }
    })
    return records
