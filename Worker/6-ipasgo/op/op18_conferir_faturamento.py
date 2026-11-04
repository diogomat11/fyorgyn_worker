"""
OP18 - Confirmar Item/Data no novo módulo ConferenciaFaturamento do IPASGO.

Substitui a OP7 (FaturamentoAtendimentos/ModificarDetalhe, descontinuado).
Para cada item envia, na mesma operação (comportamento do novo portal):
  1. POST /ConferenciaFaturamento/ConferirItem (idServico, idDetalhe, status)
  2. POST /ConferenciaFaturamento/EditarDataRealizacao (codigoPrestador SEM DV,
     idServico, idDetalhe, dataRealizacao dd/MM/yyyy) — quando houver data

Params do job (unitário OU batch — a conciliação usa batch):
  - protocolo: capa do lote no portal (obrigatório; bootstrap)
  - codigoPrestador: código do prestador (com ou sem DV; normalizado sem DV)
  - idServico / status ('Aceito'|'Recusado'|'Pendente') / dataRealizacao (dd/MM/yyyy)
  - OU itens: [{idServico, status, dataRealizacao?, idDetalhe?}, ...]
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

# Respiro entre itens (mesma política anti-ban da OP7)
DELAY_ENTRE_ITENS = 0.5

# Mapa de status aceitos pelo domínio do novo portal
STATUS_PORTAL = {
    "Aceito": "Aceito",
    "Recusado": "Recusado",
    "Pendente": "Pendente",
    # formas alternativas que podem chegar do hub
    "A": "Aceito",
    "R": "Recusado",
    "P": "Pendente",
    "67": "Aceito",     # legado: 67=Conferido
    "82": "Recusado",   # legado: 82=Removido
    "78": "Pendente",   # legado: 78=Não Conferido
}


def _load_op17_module():
    """Carrega a OP17 para reusar o bootstrap do módulo ConferenciaFaturamento."""
    spec = importlib.util.spec_from_file_location(
        "op17_importar_conferencia", os.path.join(_mod_root, "op", "op17_importar_conferencia.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _codigo_prestador_sem_dv(codigo):
    """O EditarDataRealizacao usa o código sem dígito verificador ('01889' de '01889-2')."""
    codigo = str(codigo or "").strip()
    return codigo.split("-", 1)[0] if codigo else codigo


def _normalizar_item_entrada(item):
    """Valida 1 item do job e devolve {idServico, idDetalhe, status_portal, data_br}."""
    id_servico = item.get("idServico", item.get("detalheId"))
    if id_servico is None:
        raise ValueError("OP18 - Item sem 'idServico'.")

    status_raw = str(item.get("status") or "").strip()
    status_portal = STATUS_PORTAL.get(status_raw) or STATUS_PORTAL.get(status_raw.upper())
    if not status_portal:
        raise ValueError(
            f"OP18 - Status inválido '{status_raw}' para o item {id_servico} "
            "(use Aceito/Recusado/Pendente)."
        )

    return {
        "idServico": id_servico,
        "idDetalhe": item.get("idDetalhe") or item.get("id_detalhe"),
        "status_portal": status_portal,
        "data_br": str(item.get("dataRealizacao") or "").strip() or None,
    }


def run(scraper, job_data):
    driver = scraper.driver
    job_id = job_data.get("job_id")

    protocolo = str(job_data.get("protocolo") or "").strip()
    if not protocolo:
        raise ValueError("OP18 exige o parâmetro 'protocolo' (capa do lote no portal).")

    codigo_prestador = _codigo_prestador_sem_dv(
        job_data.get("codigoPrestador") or job_data.get("cod_prestador")
        or getattr(scraper, "cod_prestador", "")
    )

    # Unitário OU batch (conciliação)
    itens_raw = job_data.get("itens")
    if not itens_raw:
        itens_raw = [{k: job_data.get(k) for k in ("idServico", "idDetalhe", "status", "dataRealizacao")}]
    if not isinstance(itens_raw, list) or not itens_raw:
        raise ValueError("OP18 exige 'idServico/status' unitário ou 'itens' (batch).")

    itens = [_normalizar_item_entrada(i) for i in itens_raw]

    scraper.log(
        f"OP18 - Conferindo {len(itens)} item(ns) no protocolo {protocolo} "
        f"(prestador={codigo_prestador or 'não informado'})...",
        job_id=job_id
    )

    # Bootstrap do contexto do módulo (helper da OP17)
    op17 = _load_op17_module()
    op17.bootstrap_conferencia_context(driver, scraper, job_id, protocolo)
    client = WebPlanClient(driver, referer_url=f"{op17.CONFERENCIA_BASE_URL}?protocolo={protocolo}")

    itens_sucesso = []
    itens_erro = []

    for item in itens:
        try:
            # 1. Conferência do item
            client.post_conferir_item(
                item["idServico"], item["status_portal"], id_detalhe=item["idDetalhe"]
            )

            # 2. Data de realização junto com a confirmação (quando informada)
            if item["data_br"] and codigo_prestador:
                client.post_editar_data_realizacao(
                    codigo_prestador, item["idServico"], item["data_br"],
                    id_detalhe=item["idDetalhe"],
                )

            itens_sucesso.append(item["idServico"])
            scraper.log(
                f"OP18 - Item {item['idServico']} conferido ({item['status_portal']}"
                + (f", data {item['data_br']}" if item["data_br"] else "")
                + ").",
                job_id=job_id,
            )
        except Exception as e:
            scraper.log(
                f"OP18 - ERRO no item {item['idServico']}: {e}",
                level="ERROR", job_id=job_id,
            )
            itens_erro.append({
                "idServico": item["idServico"],
                "status": item["status_portal"],
                "dataRealizacao": item["data_br"],
                "erro": str(e)[:300],
            })

        time.sleep(DELAY_ENTRE_ITENS)

    scraper.log(
        f"OP18 - Concluído: {len(itens_sucesso)} sucesso(s), {len(itens_erro)} erro(s).",
        job_id=job_id
    )

    return {
        "status": "success" if not itens_erro else "partial",
        "protocolo": protocolo,
        "itens_sucesso": itens_sucesso,
        "itens_erro": itens_erro,
        "sucesso_count": len(itens_sucesso),
        "erro_count": len(itens_erro),
    }
