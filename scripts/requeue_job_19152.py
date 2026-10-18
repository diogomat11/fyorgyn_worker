"""
Reenfileira o JOB 19152 (OP4 Unimed Goiânia, janela 18/09→17/10, 5.155 guias).

CONTEXTO (2026-10-18): o job foi extraído com sucesso 2x no worker, mas o
dispatcher expirava o HTTP em 600s antes do fim (~2h40m de execução), marcava
erro, re-despachava em loop (409) e o resultado nunca chegava ao hub — lote
vazio. Com as correções (chunks + heartbeat + finalização worker-side), a
re-execução entrega as guias em lotes parciais no lote 65.

EXECUTE SOMENTE DEPOIS DE:
  1. Deploy do backend (endpoint /api/jobs/{id}/result/partial) — Render e/ou local.
  2. Restart da frota Local_worker (worker + dispatcher com código novo).

Uso:
  python scripts/requeue_job_19152.py            # reseta o job 19152
  python scripts/requeue_job_19152.py --dry-run  # apenas mostra o estado atual
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Worker"))

from database import SessionLocal  # noqa: E402
from models import Job, Log  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

JOB_ID = 19152
dry_run = "--dry-run" in sys.argv

db = SessionLocal()
try:
    job = db.query(Job).filter(Job.id == JOB_ID).first()
    if not job:
        print(f"Job {JOB_ID} não encontrado.")
        sys.exit(1)

    print(f"Job {JOB_ID}: status={job.status} attempts={job.attempts}/{job.max_attempts} "
          f"locked_by={job.locked_by} updated_at={job.updated_at}")

    if dry_run:
        print("(dry-run: nenhuma alteração)")
        sys.exit(0)

    job.status = "pending"
    job.attempts = 0
    job.locked_by = None
    job.error_message = None
    job.result_data = None
    job.updated_at = datetime.now(timezone.utc)
    db.add(Log(job_id=JOB_ID, user_id=job.user_id, level="INFO",
               message="Reenfileirado manualmente após correção do pipeline de entrega (timeout dispatcher + chunks)."))
    db.commit()
    print(f"Job {JOB_ID} reenfileirado (pending, attempts=0). O dispatcher deve pegá-lo no próximo ciclo (≤15s).")
finally:
    db.close()
