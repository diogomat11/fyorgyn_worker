"""
OP19 - Anexar Arquivo à Guia no módulo ConferenciaFaturamento do IPASGO.

Fluxo (mesma sessão Selenium da OP0, login garantido pelo scraper):
  1. Valida o arquivo local (existe, .pdf, <=5MB — mesmo limite do op1_autorizar);
  2. Bootstrap em ConferenciaFaturamento/Index?protocolo={p} (helper da OP17);
  3. POST multipart /ConferenciaFaturamento/AnexarArquivoGuia
     ?capaLoteId={protocolo}&numeroGuiaOperadora={guia} com o PDF no campo
     'arquivo' (filename original preservado).

Params do job:
  - protocolo: capa do lote no portal (obrigatório; ex.: 903505)
  - numeroGuiaOperadora: guia da anexação (obrigatório; ex.: 24768401)
  - senha: senha da guia (11 dígitos; derivada do nome do arquivo pelo hub)
  - caminho_arquivo: caminho local do PDF (obrigatório)
"""
import os
import re
import sys
import importlib.util

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

import json
import importlib
from datetime import datetime, timezone
import core.webplan_client as _wc_mod
importlib.reload(_wc_mod)
from core.webplan_client import WebPlanClient
import op._anexos_common as _anexos
importlib.reload(_anexos)
from op._anexos_common import (
    MAX_ANEXO_BYTES,
    EXTENSOES_PERMITIDAS,
    is_falha_portal as _is_falha_portal,
    is_bloqueio_hard as _is_bloqueio_hard,
    is_sessao_rejeitada as _is_sessao_rejeitada,
    classifica_falha as _classifica_falha,
    e_cascata as _e_cascata,
    bump_updated_at as _bump_updated_at,
    validar_arquivo as _validar_arquivo_common,
    abortar_fila_protocolo as _abortar_fila_protocolo_common,
    checar_circuit_breaker as _checar_circuit_breaker_common,
)

ROTINAS_OP19 = ["19", "op19_anexar_arquivo_guia"]


def _validar_arquivo(caminho):
    return _validar_arquivo_common(caminho, op_tag="OP19")


def _abortar_fila_protocolo(db, protocolo: str, motivo: str, current_job_id=None):
    return _abortar_fila_protocolo_common(db, protocolo, motivo, rotinas=ROTINAS_OP19, current_job_id=current_job_id)


def _checar_circuit_breaker(db, protocolo: str, current_job_id=None) -> tuple:
    return _checar_circuit_breaker_common(db, protocolo, rotinas=ROTINAS_OP19, current_job_id=current_job_id)


def _load_op17_module():
    """Carrega a OP17 para reusar o bootstrap do módulo ConferenciaFaturamento."""
    spec = importlib.util.spec_from_file_location(
        "op17_importar_conferencia", os.path.join(_mod_root, "op", "op17_importar_conferencia.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module



def run(scraper, job_data):
    scraper.max_retries = 1
    driver = scraper.driver
    job_id = job_data.get("job_id") or job_data.get("id")

    protocolo = str(job_data.get("protocolo") or "").strip()
    numero_guia = str(job_data.get("numeroGuiaOperadora") or job_data.get("guia") or "").strip()
    senha = str(job_data.get("senha_guia") or job_data.get("senha") or "").strip()
    caminho_arquivo = job_data.get("caminho_arquivo")

    if not protocolo:
        raise ValueError("OP19 exige o parâmetro 'protocolo' (capa do lote no portal).")
    if not numero_guia:
        raise ValueError("OP19 exige o parâmetro 'numeroGuiaOperadora' (guia).")

    deve_abortar, total_falhas = _checar_circuit_breaker(getattr(scraper, "db", None), protocolo, current_job_id=job_id)
    if deve_abortar:
        motivo = f"Abortado após 3 tentativas/falha do portal no protocolo {protocolo}. Reenvio automático após pausa."
        _abortar_fila_protocolo(getattr(scraper, "db", None), protocolo, motivo, current_job_id=job_id)
        raise RuntimeError(motivo)

    # Renova updated_at entre as fases (login/bootstrap/upload) para os
    # watchdogs não abortarem um job saudável em execução.
    _bump_updated_at(getattr(scraper, "db", None), job_id)

    nome_arquivo, bytes_arquivo = _validar_arquivo(caminho_arquivo)

    scraper.log(
        f"OP19 - Anexando '{nome_arquivo}' ({len(bytes_arquivo)/1024:.0f}KB) à guia {numero_guia} "
        f"do protocolo {protocolo}...",
        job_id=job_id
    )

    try:
        # Bootstrap do contexto do módulo (helper da OP17)
        op17 = _load_op17_module()
        op17.bootstrap_conferencia_context(driver, scraper, job_id, protocolo, skip_if_same_protocolo=True)
        _bump_updated_at(getattr(scraper, "db", None), job_id)
        client = WebPlanClient(driver, referer_url=f"{op17.CONFERENCIA_BASE_URL}?protocolo={protocolo}")

        resposta = client.post_anexar_arquivo_guia(
            capa_lote_id=protocolo,
            numero_guia=numero_guia,
            nome_arquivo=nome_arquivo,
            bytes_arquivo=bytes_arquivo,
        )
    except Exception as exc:
        err_str = str(exc)
        # Sessão rejeitada/portal instável: a sessão Selenium provavelmente morreu
        # e o 1º attempt do próximo job reutiliza o driver sem re-logar se a URL
        # ainda "parece IPASGO" (o scraper só re-loga no retry). Invalida a
        # navegação para forçar re-login imediato no próximo job deste slot —
        # sem isso, um slot inteiro queima anexos reutilizando sessão podre.
        if _is_sessao_rejeitada(err_str):
            try:
                driver.get("about:blank")
                scraper.log("OP19 - Sessão rejeitada: navegador invalidado; próximo job fará re-login.", job_id=job_id)
            except Exception:
                pass
        # Cascata imediata apenas para bloqueio hard (403/429/rate-limit). Falhas
        # soft (401/500/timeout) seguem o ciclo natural de 3 tentativas do
        # dispatcher, que faz a cascata na exaustão (attempts >= 3).
        if _is_bloqueio_hard(err_str):
            rotulo = _classifica_falha(err_str)
            motivo = f"Abortado após 3 tentativas ({rotulo}): {err_str[:250]}. Reenvio automático após pausa."
            _abortar_fila_protocolo(getattr(scraper, "db", None), protocolo, motivo, current_job_id=job_id)
        raise

    scraper.log(
        f"OP19 - Anexo enviado: guia {numero_guia}, arquivo '{nome_arquivo}'.",
        job_id=job_id
    )

    return {
        "status": "anexo_enviado",
        "protocolo": protocolo,
        "guia": numero_guia,
        "senha": senha or None,
        "arquivo": nome_arquivo,
        "bytes": len(bytes_arquivo),
        "resposta_portal": resposta if isinstance(resposta, (dict, list)) else str(resposta),
    }
