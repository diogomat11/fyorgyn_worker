"""
OP21 - Anexar Arquivo ao Recurso de Glosa no módulo RecursoGlosa do IPASGO.

Fluxo (mesma sessão Selenium da OP0, login garantido pelo scraper):
  1. Valida o arquivo local (existe, .pdf, <=5MB);
  2. Bootstrap em GuiasTISS/RecursoGlosa (helper da OP10);
  3. Consulta GET /RecursoGlosa/GetAnexos?chaveCapa={protocolo} (idempotência);
  4. POST multipart /Upload/SendFile (binário do PDF) -> PathFileName temporário no servidor;
  5. POST /RecursoGlosa/SaveFile com payload { param: base64({NumeroProtocolo, PathFileName, FileName}) };
  6. Consulta GET /RecursoGlosa/GetAnexos para validar presença do anexo no portal.

Params do job:
  - protocolo: capa do recurso no portal (obrigatório; ex.: 895854)
  - caminho_arquivo: caminho local do PDF (obrigatório)
  - nome_arquivo: nome original do arquivo (opcional)
  - id_lote_interno: id_lote em lotes_convenio (opcional)
"""
import os
import sys
import importlib.util

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

import importlib
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
    bump_updated_at as _bump_updated_at,
    validar_arquivo as _validar_arquivo_common,
    abortar_fila_protocolo as _abortar_fila_protocolo_common,
    checar_circuit_breaker as _checar_circuit_breaker_common,
)

ROTINAS_OP21 = ["21", "op21_anexar_recurso_glosa"]


def _validar_arquivo(caminho):
    return _validar_arquivo_common(caminho, op_tag="OP21")


def _abortar_fila_protocolo(db, protocolo: str, motivo: str, current_job_id=None):
    return _abortar_fila_protocolo_common(db, protocolo, motivo, rotinas=ROTINAS_OP21, current_job_id=current_job_id)


def _checar_circuit_breaker(db, protocolo: str, current_job_id=None) -> tuple:
    return _checar_circuit_breaker_common(db, protocolo, rotinas=ROTINAS_OP21, current_job_id=current_job_id)


def _load_op10_module():
    """Carrega a OP10 para reusar o bootstrap do módulo RecursoGlosa."""
    spec = importlib.util.spec_from_file_location(
        "op10_recurso_glosa", os.path.join(_mod_root, "op", "op10_recurso_glosa.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(scraper, job_data):
    scraper.max_retries = 1
    driver = scraper.driver
    job_id = job_data.get("job_id") or job_data.get("id")

    protocolo = str(job_data.get("protocolo") or job_data.get("capa") or "").strip()
    id_lote_interno = job_data.get("id_lote_interno")
    caminho_arquivo = job_data.get("caminho_arquivo")

    if not protocolo:
        raise ValueError("OP21 exige o parâmetro 'protocolo' (capa do recurso no portal).")
    if not caminho_arquivo:
        raise ValueError("OP21 exige o parâmetro 'caminho_arquivo'.")

    deve_abortar, total_falhas = _checar_circuit_breaker(getattr(scraper, "db", None), protocolo, current_job_id=job_id)
    if deve_abortar:
        motivo = f"Abortado após falha do portal no protocolo {protocolo}. Reenvio automático após pausa."
        _abortar_fila_protocolo(getattr(scraper, "db", None), protocolo, motivo, current_job_id=job_id)
        raise RuntimeError(motivo)

    _bump_updated_at(getattr(scraper, "db", None), job_id)

    nome_arquivo, bytes_arquivo = _validar_arquivo(caminho_arquivo)

    scraper.log(
        f"OP21 - Anexando '{nome_arquivo}' ({len(bytes_arquivo)/1024:.0f}KB) ao recurso de glosa "
        f"do protocolo {protocolo} (lote interno={id_lote_interno or 'N/A'})...",
        job_id=job_id
    )

    try:
        # 1. Bootstrap do contexto do módulo RecursoGlosa
        op10 = _load_op10_module()
        op10.bootstrap_recurso_glosa_context(driver, scraper, job_id)
        _bump_updated_at(getattr(scraper, "db", None), job_id)
        client = WebPlanClient(driver, referer_url=op10.RECURSO_GLOSA_URL)

        # 2. Idempotência: verifica se o arquivo já está anexado
        anexos_atuais = client.get_anexos_recurso_glosa(protocolo)
        for a in anexos_atuais:
            if str(a.get("Nome") or "").strip().lower() == nome_arquivo.lower() and not a.get("Excluido"):
                scraper.log(
                    f"OP21 - Arquivo '{nome_arquivo}' já consta anexado ao protocolo {protocolo} (Id={a.get('Id')}). Ignorando envio.",
                    job_id=job_id
                )
                return {
                    "status": "anexo_ja_existente",
                    "protocolo": protocolo,
                    "id_lote_interno": id_lote_interno,
                    "arquivo": nome_arquivo,
                    "id_anexo_portal": a.get("Id"),
                }

        # 3. Upload temporário do PDF para obter PathFileName no servidor
        scraper.log(f"OP21 - Fazendo upload de '{nome_arquivo}' para o servidor temporário...", job_id=job_id)
        path_file_name = client.post_upload_temp_recurso_glosa(
            nome_arquivo=nome_arquivo,
            bytes_arquivo=bytes_arquivo
        )
        scraper.log(f"OP21 - Arquivo temporário criado: {path_file_name}", job_id=job_id)
        _bump_updated_at(getattr(scraper, "db", None), job_id)

        # 4. Salvar vínculo do arquivo temporário no recurso de glosa
        scraper.log(f"OP21 - Vinculando arquivo ao protocolo {protocolo}...", job_id=job_id)
        resposta_save = client.post_save_file_recurso_glosa(
            protocolo=protocolo,
            path_file_name=path_file_name,
            file_name=nome_arquivo
        )
        _bump_updated_at(getattr(scraper, "db", None), job_id)

        # 5. Validação pós-envio
        anexos_depois = client.get_anexos_recurso_glosa(protocolo)
        anexo_confirmado = next(
            (a for a in anexos_depois if str(a.get("Nome") or "").strip().lower() == nome_arquivo.lower() and not a.get("Excluido")),
            None
        )

        id_confirmado = anexo_confirmado.get("Id") if anexo_confirmado else None
        scraper.log(
            f"OP21 - Anexo vinculado com sucesso! Protocolo {protocolo}, arquivo '{nome_arquivo}' (IdPortal={id_confirmado}).",
            job_id=job_id
        )

    except Exception as exc:
        err_str = str(exc)
        if _is_sessao_rejeitada(err_str):
            try:
                driver.get("about:blank")
                scraper.log("OP21 - Sessão rejeitada: navegador invalidado; próximo job fará re-login.", job_id=job_id)
            except Exception:
                pass
        if _is_bloqueio_hard(err_str):
            rotulo = _classifica_falha(err_str)
            motivo = f"Abortado após bloqueio ({rotulo}): {err_str[:250]}. Reenvio automático após pausa."
            _abortar_fila_protocolo(getattr(scraper, "db", None), protocolo, motivo, current_job_id=job_id)
        raise

    return {
        "status": "anexo_enviado",
        "protocolo": protocolo,
        "id_lote_interno": id_lote_interno,
        "arquivo": nome_arquivo,
        "path_file_name": path_file_name,
        "id_anexo_portal": id_confirmado,
        "resposta_portal": resposta_save if isinstance(resposta_save, (dict, list)) else str(resposta_save),
    }
