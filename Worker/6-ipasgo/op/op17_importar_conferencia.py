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


def bootstrap_conferencia_context(driver, scraper, job_id, protocolo, skip_if_same_protocolo=False):
    """Navega ao módulo ConferenciaFaturamento do protocolo e fecha notificações."""
    target_url = f"{CONFERENCIA_BASE_URL}?protocolo={protocolo}"
    if skip_if_same_protocolo:
        try:
            cur_url = driver.current_url or ""
            if "ConferenciaFaturamento" in cur_url and f"protocolo={protocolo}" in cur_url:
                return
        except Exception:
            pass
    try:
        driver.set_page_load_timeout(25)
    except Exception:
        pass
    try:
        driver.get(target_url)
    except Exception as e:
        raise RuntimeError(f"Bloqueio ou timeout ao carregar ConferenciaFaturamento (protocolo {protocolo}): {e}")
    finally:
        try:
            driver.set_page_load_timeout(120)
        except Exception:
            pass
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


def _guia_tem_anexo_ativo(resposta_anexos) -> bool:
    """Retorna True se ListarAnexosGuia trouxe ao menos 1 anexo não excluído."""
    if not isinstance(resposta_anexos, dict):
        return False
    lista = resposta_anexos.get("Data")
    if not isinstance(lista, list):
        return False
    return any(isinstance(a, dict) and not a.get("Excluido", False) for a in lista)


def _consultar_anexos_por_guia(client, scraper, job_id, capa_lote_id, guias, op10) -> dict:
    """
    Para cada guia única da capa, verifica se possui anexo ativo via
    GET /ConferenciaFaturamento/ListarAnexosGuia?capaLoteId={protocolo}&numeroGuiaOperadora={guia}.
    Se o objeto da guia em ObterProcedimentos já trouxer `TemAnexo=True`, aproveita
    sem precisar de request extra; caso contrário consulta o endpoint ListarAnexosGuia.
    Retorna dict {guia_normalizada: bool}.
    """
    mapa = {}
    guias_para_consultar = []
    for g in guias:
        guia_raw = g.get("NumeroGuiaOperadora")
        guia_norm = op10._normalizar_guia(guia_raw)
        if not guia_norm or guia_norm in mapa:
            continue
        if g.get("TemAnexo") is True:
            mapa[guia_norm] = True
        else:
            mapa[guia_norm] = False
            guias_para_consultar.append((guia_norm, str(guia_raw or guia_norm).strip()))

    if guias_para_consultar:
        scraper.log(
            f"OP17 - Verificando anexos (ListarAnexosGuia) de {len(guias_para_consultar)} guia(s)...",
            job_id=job_id,
        )
        for idx, (guia_norm, guia_query) in enumerate(guias_para_consultar, 1):
            try:
                resp_anx = client.get_listar_anexos_guia(capa_lote_id, guia_query)
                if _guia_tem_anexo_ativo(resp_anx):
                    mapa[guia_norm] = True
            except Exception as e:
                scraper.log(
                    f"OP17 - Aviso ao consultar anexos da guia {guia_norm}: {e}",
                    level="WARN",
                    job_id=job_id,
                )
            if idx % 20 == 0:
                time.sleep(0.2)

    com_anexo = sum(1 for v in mapa.values() if v)
    scraper.log(
        f"OP17 - Anexos verificados: {com_anexo} de {len(mapa)} guia(s) possuem anexo ativo.",
        job_id=job_id,
    )
    return mapa


def _normalizar_guia_item(guia, item, op11, op10, anexos_por_guia=None):
    """1 linha normalizada por item (dados da guia embutidos)."""
    op11_date = op11._parse_aspnet_date

    # Regra de negócio: sem DataProcedimento -> Inapto (não habilitado a faturar)
    data_procedimento = op11_date(item.get("DataProcedimento"))
    status_letra = str(item.get("StatusConferencia") or "").strip().upper() or STATUS_PENDENTE
    if data_procedimento is None:
        status_letra = STATUS_INAPTO

    guia_norm = op10._normalizar_guia(guia.get("NumeroGuiaOperadora"))
    tem_anexo = bool(
        (anexos_por_guia or {}).get(guia_norm)
        or guia.get("TemAnexo") is True
    )

    return {
        # guia
        "guia": guia_norm,
        "guia_prestador_faturamento": str(guia.get("NumeroGuiaPrestadorFaturamento") or ""),
        "nome_beneficiario": str(guia.get("NomeBeneficiario") or "").strip(),
        "codigo_beneficiario": str(guia.get("CodigoBeneficiario") or "").strip(),
        "senha": str(guia.get("Senha") or "").strip(),
        "tem_anexo": tem_anexo,
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

    # Paginação futura: se o portal fragmentar, coleta todas as guias primeiro
    todas_guias = list(guias)
    total_paginas = _extrair_total_paginas(response_json)
    if total_paginas:
        for pagina in range(2, total_paginas + 1):
            scraper.log(f"OP17 - Página adicional {pagina}/{total_paginas}...", job_id=job_id)
            resp_pag = client.get_conferencia_procedimentos(protocolo)
            guias_pag = (resp_pag.get("Capa") or {}).get("Guias") or []
            if not guias_pag:
                break
            todas_guias.extend(guias_pag)
            time.sleep(0.3)

    # 3. Consulta ListarAnexosGuia por guia única do lote
    capa_id_query = capa.get("CapaLoteId") or protocolo
    anexos_por_guia = _consultar_anexos_por_guia(
        client, scraper, job_id, capa_id_query, todas_guias, op10
    )

    todas = [
        _normalizar_guia_item(g, i, op11, op10, anexos_por_guia)
        for g in todas_guias
        for i in (g.get("Itens") or [])
    ]

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
