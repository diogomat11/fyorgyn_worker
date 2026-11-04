"""
OP10 - Importar Recurso de Glosa de um lote/protocolo do IPASGO (FacPlan).

Fluxo (mesma sessão Selenium da OP0, login garantido pelo scraper):
  1. Bootstrap em GuiasTISS/RecursoGlosa (cookies do módulo) + fechamento de
     notificações (reuso do _close_notification_robust consolidado na OP11);
  2. GET /RecursoGlosa/Carregar?id={protocolo} — valida acesso à capa e lê o
     total de páginas (Servicos.NumeroDePaginas);
  3. GET /RecursoGlosa/PesquisarServicosLote?idCapa={protocolo}&pagina=N para
     cada página (1..NumeroDePaginas, re-sincronizado a cada resposta);
  4. Normaliza os itens (guia sem zeros à esquerda, CodigoAmb sem '.'/'-') e
     devolve envelope para o hub persistir em recurso_glosa_itens.

Params do job:
  - protocolo: capa/protocolo do lote no portal (obrigatório)
  - id_lote_interno: id_lote em lotes_convenio (usado pelo consumer do hub)
"""
import os
import sys
import importlib.util
import time

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from core.webplan_client import WebPlanClient

RECURSO_GLOSA_URL = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/RecursoGlosa"

# Respiro entre páginas da paginação (mesma política da OP11 por guia)
DELAY_ENTRE_PAGINAS = 0.3


def _load_op11_module():
    """Carrega a OP11 para reaproveitar helpers consolidados (padrão da OP15)."""
    spec = importlib.util.spec_from_file_location(
        "op11_import_guias_api", os.path.join(_mod_root, "op", "op11_import_guias_api.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bootstrap_recurso_glosa_context(driver, scraper, job_id):
    """Navega ao módulo RecursoGlosa e fecha notificações do FacPlan."""
    driver.get(RECURSO_GLOSA_URL)
    for _ in range(10):
        try:
            if driver.execute_script("return document.readyState;") == "complete":
                break
        except Exception:
            pass
        time.sleep(1)
    time.sleep(2)  # notificações assíncronas renderizarem

    op11 = _load_op11_module()
    for attempt in range(5):
        if op11._close_notification_robust(driver, scraper, job_id):
            scraper.log(f"RecursoGlosa - Notificação fechada na tentativa {attempt + 1}", job_id=job_id)
            break
    time.sleep(1)


def _normalizar_guia(guia_raw):
    """
    Remove zeros à esquerda do número da guia (ex.: "024533543" -> "24533543"),
    mantendo ao menos um dígito. Guias não numéricas voltam sem o strip.
    """
    guia = str(guia_raw or "").strip()
    if not guia:
        return ""
    if guia.isdigit():
        stripped = guia.lstrip("0")
        return stripped or "0"
    return guia


def _extrair_numero_paginas(response_json):
    """
    Total de páginas da resposta do portal. Em PesquisarServicosLote a
    paginação está na raiz; em Carregar ela vem dentro de Servicos (dict).
    """
    if not isinstance(response_json, dict):
        return None
    raiz = response_json.get("NumeroDePaginas")
    if isinstance(raiz, int) and raiz > 0:
        return raiz
    servicos = response_json.get("Servicos")
    if isinstance(servicos, dict):
        interno = servicos.get("NumeroDePaginas")
        if isinstance(interno, int) and interno > 0:
            return interno
    return None


def _to_int(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _to_float(valor):
    try:
        if valor is None:
            return None
        return float(valor)
    except (TypeError, ValueError):
        return None


def _normalizar_item_servico(item, op11):
    """Mapeia 1 serviço do portal para a linha normalizada do hub."""
    return {
        "codigo_segurado": str(item.get("CodigoSegurado") or "").strip(),
        "nome_segurado": str(item.get("NomeSegurado") or "").strip(),
        "chave": _to_int(item.get("Chave")),
        "chave_ut_serv": _to_int(item.get("ChaveUtServ")),
        "guia": _normalizar_guia(item.get("Guia")),
        "codigo_amb": op11._normalizar_codigo(item.get("CodigoAmb")),
        "descricao_servico": str(item.get("DescricaoServico") or "").strip(),
        "quantidade_glosada": _to_int(item.get("QuantidadeGlosada")),
        "valor_unitario_glosado": _to_float(item.get("ValorUnitarioGlosado")),
        "valor_recurso": _to_float(item.get("ValorRecurso")),
        "is_detalhe": bool(item.get("IsDetalhe", False)),
        "has_detalhes": bool(item.get("HasDetalhes", False)),
        "justificativa": str(item.get("Justificativa") or "").strip() or None,
    }


def run(scraper, job_data):
    driver = scraper.driver
    job_id = job_data.get("job_id")

    protocolo = str(job_data.get("protocolo") or job_data.get("idCapa") or "").strip()
    id_lote_interno = job_data.get("id_lote_interno")

    if not protocolo:
        raise ValueError("OP10 exige o parâmetro 'protocolo' (capa/protocolo do lote no portal).")

    scraper.log(
        f"OP10 - Importando recurso de glosa do protocolo {protocolo} "
        f"(lote interno={id_lote_interno or 'não informado'})...",
        job_id=job_id
    )

    # 1. Bootstrap do contexto do módulo RecursoGlosa
    bootstrap_recurso_glosa_context(driver, scraper, job_id)
    client = WebPlanClient(driver, referer_url=RECURSO_GLOSA_URL)
    op11 = _load_op11_module()

    # 2. Carregar a capa: valida o acesso ao lote e lê o total de páginas
    capa_json = client.get_recurso_glosa_capa(protocolo)
    numero_paginas = _extrair_numero_paginas(capa_json)
    if numero_paginas is None:
        raise ValueError(
            f"OP10 - Não foi possível determinar o total de páginas do protocolo {protocolo} "
            f"(resposta do Carregar sem NumeroDePaginas). Verifique se o protocolo existe no portal."
        )
    scraper.log(f"OP10 - Capa carregada. Total de páginas: {numero_paginas}", job_id=job_id)

    # 3. Paginação — o NumeroDePaginas é re-sincronizado a cada resposta
    todos_itens = []
    pagina = 1
    while pagina <= numero_paginas:
        scraper.log(f"OP10 - Consultando página {pagina}/{numero_paginas}...", job_id=job_id)
        response_json = client.get_recurso_glosa_servicos(protocolo, pagina=pagina)

        servicos = response_json.get("Servicos", []) if isinstance(response_json, dict) else []
        if not servicos:
            scraper.log(f"OP10 - Página {pagina} retornou 0 serviços. Fim da extração.", job_id=job_id)
            break

        novos = [_normalizar_item_servico(item, op11) for item in servicos]
        todos_itens.extend(novos)
        scraper.log(f"OP10 - Página {pagina}: {len(novos)} serviços extraídos.", job_id=job_id)

        atualizado = _extrair_numero_paginas(response_json)
        if atualizado and atualizado != numero_paginas:
            scraper.log(
                f"OP10 - Total de páginas atualizado pelo portal: {numero_paginas} -> {atualizado}",
                job_id=job_id
            )
            numero_paginas = atualizado

        pagina += 1
        time.sleep(DELAY_ENTRE_PAGINAS)

    scraper.log(
        f"OP10 - Extração concluída: {len(todos_itens)} itens em {pagina - 1} página(s).",
        job_id=job_id
    )

    return {
        "status": "importacao_concluida",
        "protocolo": protocolo,
        "id_lote_interno": id_lote_interno,
        "numero_paginas": numero_paginas,
        "total_itens": len(todos_itens),
        "itens": todos_itens,
    }
