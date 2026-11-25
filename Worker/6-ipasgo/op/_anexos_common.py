"""
Helpers comuns para rotinas de upload de anexos no portal IPASGO (OP19 e OP21).

Inclui:
- Circuit breaker / cascata por protocolo
- Detecção e classificação de falhas de portal (bloqueio vs sessão rejeitada)
- Validação física de arquivos (.pdf <= 5MB)
- Keepalive/bump de updated_at para os watchdogs do hub/dispatcher
"""
import os
import re
import json
from datetime import datetime, timezone

MAX_ANEXO_BYTES = 5 * 1024 * 1024
EXTENSOES_PERMITIDAS = (".pdf",)

_RE_FALHA_PORTAL = re.compile(r"\b(401|403|429|500|502|503)\b")
_KEYWORDS_FALHA_PORTAL = (
    "bloqueio", "bloqueado", "sessão rejeitada", "sessao rejeitada",
    "timeout", "rate limit", "too many requests", "limite de requisições",
    "portal indisponível",
)


def is_falha_portal(err_str: str) -> bool:
    """Bloqueio/sessão rejeitada/indisponibilidade: falhas que justificam abortar a fila."""
    low = str(err_str or "").lower()
    return bool(_RE_FALHA_PORTAL.search(low)) or any(k in low for k in _KEYWORDS_FALHA_PORTAL)


def is_bloqueio_hard(err_str: str) -> bool:
    """Bloqueio explícito (403/429/rate-limit): aborta a fila na 1ª ocorrência."""
    low = str(err_str or "").lower()
    return bool(re.search(r"\b(403|429)\b", low)) or any(
        k in low for k in ("bloqueio", "bloqueado", "rate limit", "too many requests", "limite de requisições")
    )


def is_sessao_rejeitada(err_str: str) -> bool:
    """Falhas que indicam sessão Selenium morta / portal instável (401/500/HTML)."""
    low = str(err_str or "").lower()
    return bool(re.search(r"\b(401|500|502|503)\b", low)) or any(
        k in low for k in ("sessão rejeitada", "sessao rejeitada", "retornou html", "timeout", "portal indisponível")
    )


def classifica_falha(err_str: str) -> str:
    """Rótulo para o wrapper do motivo."""
    low = str(err_str or "").lower()
    if re.search(r"\b(403|429)\b", low) or any(
        k in low for k in ("bloqueio", "bloqueado", "rate limit", "too many requests", "limite de requisições")
    ):
        return "bloqueio IPASGO"
    return "sessão rejeitada no portal IPASGO"


def e_cascata(msg: str) -> bool:
    """Job abortado em cascata (não tentado)."""
    low = str(msg or "").lower()
    return low.startswith("abortado em cascata") or low.startswith("abortado -") or "não foi tentado" in low


def bump_updated_at(db, job_id):
    """Renova updated_at do job em execução para evitar timeout nos watchdogs."""
    if not db or not job_id:
        return
    try:
        from models import Job as JobModel
        jb = db.query(JobModel).filter(JobModel.id == job_id).first()
        if jb:
            jb.updated_at = datetime.now(timezone.utc)
            db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def validar_arquivo(caminho, op_tag="OP"):
    """Valida existência, extensão e tamanho. Retorna (nome, bytes) ou levanta ValueError."""
    caminho = str(caminho or "").strip().strip('"')
    if not caminho:
        raise ValueError(f"{op_tag} - Caminho do arquivo não informado.")
    if not os.path.isfile(caminho):
        raise ValueError(f"{op_tag} - Arquivo não encontrado: {caminho}")
    if os.path.isdir(caminho):
        raise ValueError(f"{op_tag} - Recebeu uma pasta ({caminho}); crie 1 job por arquivo PDF.")
    nome = os.path.basename(caminho)
    if not nome.lower().endswith(EXTENSOES_PERMITIDAS):
        raise ValueError(f"{op_tag} - Arquivo '{nome}' não é um PDF.")
    tamanho = os.path.getsize(caminho)
    if tamanho > MAX_ANEXO_BYTES:
        raise ValueError(
            f"{op_tag} - Arquivo '{nome}' tem {tamanho/1024/1024:.1f}MB (limite 5MB)."
        )
    if tamanho == 0:
        raise ValueError(f"{op_tag} - Arquivo '{nome}' está vazio.")
    with open(caminho, "rb") as f:
        return nome, f.read()


def abortar_fila_protocolo(db, protocolo: str, motivo: str, rotinas, current_job_id=None):
    """Marca todos os jobs não concluídos do protocolo como 'error' (attempts=3) e libera workers."""
    if not db or not protocolo:
        return 0
    try:
        from models import Job as JobModel, Worker as WorkerModel
        db.rollback()
        now = datetime.now(timezone.utc)
        jobs = db.query(JobModel).filter(
            JobModel.id_convenio == 6,
            JobModel.rotina.in_(rotinas),
            JobModel.status.in_(["pending", "processing", "running", "error"])
        ).all()
        aborted_ids = []
        count = 0
        for j in jobs:
            jp = j.params if isinstance(j.params, dict) else (json.loads(j.params) if isinstance(j.params, str) and j.params else {})
            if str(jp.get("protocolo") or "").strip() != protocolo:
                continue
            aborted_ids.append(j.id)
            if j.status in ("pending", "processing", "running") or (j.attempts or 0) < 3:
                j.status = "error"
                j.attempts = max(3, j.attempts or 0)
                j.locked_by = None
                if j.id != current_job_id:
                    j.error_message = (
                        f"Abortado em cascata — falha do portal no job #{current_job_id} "
                        f"do protocolo {protocolo}. Este anexo não foi tentado. "
                        "Reenvio automático após pausa."
                    )[:1000]
                elif not j.error_message:
                    j.error_message = motivo[:1000]
                j.updated_at = now
                count += 1
        if aborted_ids:
            workers = db.query(WorkerModel).filter(WorkerModel.current_job_id.in_(aborted_ids)).all()
            for w in workers:
                w.status = "idle"
                w.current_job_id = None
        db.commit()
        return count
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return 0


def checar_circuit_breaker(db, protocolo: str, rotinas, current_job_id=None) -> tuple:
    """Retorna (deve_abortar: bool, total_falhas: int)."""
    if not db or not protocolo:
        return False, 0
    try:
        from models import Job as JobModel
        db.rollback()
        jobs = db.query(JobModel).filter(
            JobModel.id_convenio == 6,
            JobModel.rotina.in_(rotinas)
        ).all()
        falhas = 0
        bloqueio = False
        job_atual_abortado = False
        for j in jobs:
            jp = j.params if isinstance(j.params, dict) else (json.loads(j.params) if isinstance(j.params, str) and j.params else {})
            if str(jp.get("protocolo") or "").strip() != protocolo:
                continue
            if current_job_id and j.id == current_job_id and j.status == "error" and (j.attempts or 0) >= 3:
                job_atual_abortado = True
            if j.status == "error":
                msg = str(j.error_message or "")
                if e_cascata(msg):
                    continue
                if not msg.lower().startswith("abortado -"):
                    falhas += max(1, j.attempts or 1)
                if is_bloqueio_hard(msg):
                    bloqueio = True
                elif (j.attempts or 0) >= 3 and is_falha_portal(msg):
                    bloqueio = True
        return (job_atual_abortado or bloqueio), falhas
    except Exception:
        return False, 0
