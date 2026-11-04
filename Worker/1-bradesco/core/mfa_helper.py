"""
MFA Bradesco (Faturi) — helper do código interativo (docs/plano_mfa_bradesco.md §8.2).

Canal (D3): o Postgres é a fonte da verdade — o worker grava mfa_required_at/
mfa_expires_at direto em worker.jobs (o hub lê para o modal) e consome o código
digitado com UPDATE...RETURNING atômico. mfa_code é apagado após o consumo e
jamais é logado (D9). O webhook `mfa/required` é best-effort (telemetria).
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from core.exceptions import MfaCancelledError, MfaTimeoutError

MFA_TIMEOUT_S = 300      # prazo por ciclo de solicitação (PO: 5 min)
MFA_POLL_INTERVAL_S = 3  # frequência do polling no banco
MFA_MAX_CYCLES = 2       # ciclos de novo pedido (código inválido faz o portal re-pedir)


def _utcnow():
    return datetime.now(timezone.utc)


def solicitar_codigo(scraper, job_id: int, ciclo: int = 1):
    """Registra no job que o código MFA é esperado do usuário (novo ciclo renova o prazo)."""
    now = _utcnow()
    db = scraper.db
    db.execute(
        text("""
            UPDATE worker.jobs
            SET mfa_required_at = :now,
                mfa_expires_at = :expires,
                mfa_attempts = :attempts,
                mfa_code = NULL,
                mfa_submitted_at = NULL,
                mfa_consumed_at = NULL,
                mfa_cancelled = FALSE
            WHERE id = :job_id
        """),
        {"now": now, "expires": now + timedelta(seconds=MFA_TIMEOUT_S),
         "attempts": ciclo - 1, "job_id": job_id},
    )
    db.commit()
    scraper.log(
        f"Código MFA solicitado ao usuário (ciclo {ciclo}/{MFA_MAX_CYCLES}, "
        f"expira em {MFA_TIMEOUT_S}s)",
        job_id=job_id,
    )
    # Webhook best-effort (telemetria) — falha não é erro: o modal lê o banco.
    try:
        from hub_client import post_hub
        post_hub(
            f"/api/jobs/{job_id}/mfa/required",
            json={"cycle": ciclo, "expires_at": (now + timedelta(seconds=MFA_TIMEOUT_S)).isoformat()},
            timeout=10,
        )
    except Exception:
        pass


def aguardar_codigo(scraper, job_id: int, timeout_s: int = MFA_TIMEOUT_S) -> str:
    """Espera o usuário digitar: polling no banco até o prazo do ciclo.

    Consumo atômico: UPDATE ... WHERE mfa_code IS NOT NULL RETURNING — lê o
    código uma única vez e já o apaga (idempotente; nunca loga o valor).
    Levanta MfaCancelledError (usuário cancelou) ou MfaTimeoutError (prazo).
    """
    db = scraper.db
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        # Consumo atômico: apenas MARCA mfa_consumed_at (consumidor único via
        # mfa_consumed_at IS NULL) e o RETURNING devolve o código ÍNTEGRO —
        # apagar mfa_code no mesmo UPDATE faria o RETURNING devolver NULL sempre
        # (valor pós-update; incidentes 20646/20649: consumo aplicado, código
        # nunca visto pelo loop → MFA_TIMEOUT). O código é apagado depois, no
        # limpar_estado() ao concluir o login (ou expira com o ciclo).
        consumed = db.execute(
            text("""
                UPDATE worker.jobs
                SET mfa_consumed_at = :now
                WHERE id = :job_id AND mfa_code IS NOT NULL
                  AND mfa_consumed_at IS NULL AND mfa_cancelled = FALSE
                RETURNING mfa_code
            """),
            {"now": _utcnow(), "job_id": job_id},
        )
        # Ler o RETURNING ANTES do commit — após commit o Result é invalidado
        # (pooler transacional encerra a sessão no commit).
        row = consumed.fetchone()
        db.commit()
        if row and row[0]:
            scraper.log("Código MFA recebido do usuário", job_id=job_id)
            return str(row[0])

        state = db.execute(
            text("SELECT mfa_cancelled FROM worker.jobs WHERE id = :job_id"),
            {"job_id": job_id},
        )
        db.commit()
        row = state.fetchone()
        if row and row[0]:
            raise MfaCancelledError()

        time.sleep(MFA_POLL_INTERVAL_S)
    raise MfaTimeoutError()


def limpar_estado(scraper, job_id: int):
    """Zera o estado MFA do job (fim do fluxo — login concluído ou encerramento)."""
    db = scraper.db
    db.execute(
        text("""
            UPDATE worker.jobs
            SET mfa_code = NULL, mfa_required_at = NULL, mfa_expires_at = NULL,
                mfa_submitted_at = NULL, mfa_cancelled = FALSE
            WHERE id = :job_id
        """),
        {"job_id": job_id},
    )
    db.commit()
