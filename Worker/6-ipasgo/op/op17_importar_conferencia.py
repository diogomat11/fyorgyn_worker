"""
OP17 - Importar Faturáveis do novo módulo ConferenciaFaturamento do IPASGO.

O portal substituiu o fluxo antigo (FaturamentoAtendimentos/LoadDetalhes da OP6)
pelo módulo ConferenciaFaturamento, endereçado por PROTOCOLO (capa) do lote.

Fluxo (mesma sessão Selenium da OP0, login garantido pelo scraper):
  1. Bootstrap em ConferenciaFaturamento/Index?protocolo={p} + fechamento de
     notificações (reuso do _close_notification_robust consolidado na OP11);
  2. GET /ConferenciaFaturamento/ObterProcedimentos?protocolo={p}&_={ms}
     (cache-buster = timestamp da requisição). Hoje a resposta traz todas as
     guias de uma vez; se o portal passar a paginar (campos TotalPaginas/
     Pagina), a OP itera — tolerante às duas formas;
  3. Normaliza 1 linha por item (guia + item) e devolve envelope para o hub
     persistir em faturamento_lotes (detalheId = IdServico).

Regra de negócio: item com DataProcedimento vazio recebe status 'I' (Inapto —
não habilitado a faturar).

Params do job:
  - protocolo: capa/protocolo do lote no portal (obrigatório; ex.: 899116)
  - numero_lote: número do lote no portal (ex.: 100557; validado contra o Capa)
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

CONFERENCIA_BASE_URL = "https://novowebplanipasgo.facilinformatica.com.br/ConferenciaFaturamento/Index"

# Domínio do novo portal (StatusConferencia)
STATUS_ACEITO = "A"
STATUS_PENDENTE = "P"
STATUS_RECUSADO = "R"
STATUS_INAPTO = "I"  # DataProcedimento vazio — não habilitado a faturar


def _load_op11_module():
    """Carrega a OP11 para reaproveitar helpers consolidados (padrão OP15/OP10)."""
    spec = importlib.util.spec_from_file_location(
        "op11_import_guias_api", os.path.join(_mod_root, "op", "op11_import_guias_api.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_op10_module():
    """Carrega a OP10 para o _normalizar_guia (zeros à esquerda)."""
    spec = importlib.util.spec_from_file_location(
        "op10_recurso_glosa", os.path.join(_mod_root, "op", "op10_recurso_glosa.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bootstrap_conferencia_context(driver, scraper, job_id, protocolo):
    """Navega ao módulo ConferenciaFaturamento do protocolo e fecha notificações."""
    driver.get(f"{CONFERENCIA_BASE_URL}?protocolo={protocolo}")
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
            scraper.log(f"ConferenciaFaturamento - Notificação fechada na tentativa {attempt + 1}", job_id=job_id)
            break
    time.sleep(1)


def _extrair_total_paginas(response_json):
    """Paginação, se o portal passar a usar (hoje retorna tudo de uma vez)."""
    if not isinstance(response_json, dict):
        return None
    for chave in ("TotalPaginas", "NumeroDePaginas"):
        valor = response_json.get(chave)
        if isinstance(valor, int) and valor > 1:
            return valor
    capa = response_json.get("Capa")
    if isinstance(capa, dict):
        valor = capa.get("TotalPaginas")
        if isinstance(valor, int) and valor > 1:
            return valor
    return None


def _normalizar_guia_item(guia, item, op11, op10):
    """1 linha normalizada por item (dados da guia embutidos)."""
    op11_date = op11._parse_aspnet_date

    # Regra de negócio: sem DataProcedimento -> Inapto (não habilitado a faturar)
    data_procedimento = op11_date(item.get("DataProcedimento"))
    status_letra = str(item.get("StatusConferencia") or "").strip().upper() or STATUS_PENDENTE
    if data_procedimento is None:
        status_letra = STATUS_INAPTO

    return {
        # guia
        "guia": op10._normalizar_guia(guia.get("NumeroGuiaOperadora")),
        "guia_prestador_faturamento": str(guia.get("NumeroGuiaPrestadorFaturamento") or ""),
        "nome_beneficiario": str(guia.get("NomeBeneficiario") or "").strip(),
        "codigo_beneficiario": str(guia.get("CodigoBeneficiario") or "").strip(),
        "senha": str(guia.get("Senha") or "").strip(),
        # item
        "detalheId": item.get("IdServico"),
        "id_detalhe": item.get("IdDetalhe"),
        "cod_procedimento_fat": op11._normalizar_codigo(item.get("CodigoItem")),
        "nome_procedimento": str(item.get("NomeProcedimento") or "").strip(),
        "quantidade": item.get("QtdOriginal"),
        "ValorProcedimento": item.get("ValorOriginal"),
        "dataRealizacao": data_procedimento,
        "data_liberacao": op11_date(item.get("DataLiberacao")),
        "status_conferencia": status_letra,
    }


def run(scraper, job_data):
    driver = scraper.driver
    job_id = job_data.get("job_id")

    protocolo = str(job_data.get("protocolo") or "").strip()
    numero_lote = str(job_data.get("numero_lote") or "").strip()
    id_lote_interno = job_data.get("id_lote_interno")

    if not protocolo:
        raise ValueError(
            "OP17 exige o parâmetro 'protocolo' (capa do lote no novo portal ConferenciaFaturamento)."
        )

    scraper.log(
        f"OP17 - Importando faturáveis do protocolo {protocolo} "
        f"(lote={numero_lote or 'não informado'}, interno={id_lote_interno or 'não informado'})...",
        job_id=job_id
    )

    # 1. Bootstrap do contexto do módulo
    bootstrap_conferencia_context(driver, scraper, job_id, protocolo)
    client = WebPlanClient(
        driver, referer_url=f"{CONFERENCIA_BASE_URL}?protocolo={protocolo}"
    )
    op11 = _load_op11_module()
    op10 = _load_op10_module()

    # 2. ObterProcedimentos (hoje sem paginação; tolerante se o portal paginar)
    response_json = client.get_conferencia_procedimentos(protocolo)
    capa = response_json.get("Capa") if isinstance(response_json, dict) else None
    if not isinstance(capa, dict):
        raise ValueError(f"OP17 - Resposta sem Capa para o protocolo {protocolo}. Verifique o protocolo no portal.")

    guias = capa.get("Guias") or []

    # Confere o número do lote informado com o do portal (quando ambos existem)
    capa_lote = str(capa.get("NumeroLote") or "").strip()
    if numero_lote and capa_lote and numero_lote != capa_lote:
        raise ValueError(
            f"OP17 - Protocolo {protocolo} pertence ao lote {capa_lote}, mas o job informou {numero_lote}."
        )
    if not numero_lote:
        numero_lote = capa_lote

    scraper.log(
        f"OP17 - Capa carregada: protocolo {capa.get('Protocolo')}, lote {capa_lote or '?'}, "
        f"{len(guias)} guia(s) declaradas (TotalGuias={capa.get('TotalGuias')}).",
        job_id=job_id
    )

    todas = [_normalizar_guia_item(g, i, op11, op10) for g in guias for i in (g.get("Itens") or [])]

    # Paginação futura: se o portal fragmentar, itera as demais páginas
    total_paginas = _extrair_total_paginas(response_json)
    if total_paginas:
        for pagina in range(2, total_paginas + 1):
            scraper.log(f"OP17 - Página adicional {pagina}/{total_paginas}...", job_id=job_id)
            resp_pag = client.get_conferencia_procedimentos(protocolo)
            guias_pag = (resp_pag.get("Capa") or {}).get("Guias") or []
            if not guias_pag:
                break
            todas.extend(
                _normalizar_guia_item(g, i, op11, op10) for g in guias_pag for i in (g.get("Itens") or [])
            )
            time.sleep(0.3)

    inaptos = sum(1 for i in todas if i["status_conferencia"] == STATUS_INAPTO)
    scraper.log(
        f"OP17 - Extração concluída: {len(todas)} itens de {len(guias)} guia(s); "
        f"{inaptos} inapto(s) sem data de procedimento.",
        job_id=job_id
    )

    return {
        "status": "importacao_concluida",
        "protocolo": protocolo,
        "numero_lote": numero_lote or None,
        "capa_lote_id": capa.get("CapaLoteId"),
        "id_lote_interno": id_lote_interno,
        "total_guias": len(guias),
        "total_itens": len(todas),
        "total_inaptos": inaptos,
        "itens": todas,
    }
