"""
Reenfileira em massa os jobs do Fature (convênio 1, rotina '1') finalizados como
"Guia não localizada" — lote 2026-10-21 01:00 UTC, ids 19236..20628 (1.008 jobs).

CONTEXTO (2026-10-22): a auditoria provou que o lote inteiro foi vítima da sessão
do Faturi expirada — a API respondia "Authentication failed" (corpo de erro
tratado como lista vazia pela OP1 antiga) → falsas "não localizada". Com a OP1
nova (cascata reg_ans × status + SessionExpiredError + escada de recuperação),
a re-execução deve localizar as guias.

EXECUTE SOMENTE DEPOIS DE restart da frota (worker + dispatcher com código novo).

Uso:
  python scripts/requeue_fature_nao_localizadas.py --dry-run  # apenas inventaria
  python scripts/requeue_fature_nao_localizadas.py             # reenfileira
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Worker"))

from database import SessionLocal  # noqa: E402
from models import Job, Log  # noqa: E402
from sqlalchemy import text  # noqa: E402

dry_run = "--dry-run" in sys.argv

FILTRO = text("""
    id_convenio = 1 AND rotina = '1'
    AND status = 'success'
    AND result_data::text ILIKE '%não localizada%'
""")

db = SessionLocal()
try:
    jobs = db.query(Job).filter(FILTRO).order_by(Job.id.asc()).all()
    print(f"Jobs 'não localizadas' encontrados: {len(jobs)}")
    if not jobs:
        sys.exit(0)
    print(f"  faixa: {jobs[0].id}..{jobs[-1].id} (criados {jobs[0].created_at} → {jobs[-1].created_at})")

    if dry_run:
        print("(dry-run: nenhuma alteração)")
        sys.exit(0)

    agora = datetime.now(timezone.utc)
    ids = [j.id for j in jobs]
    db.query(Job).filter(FILTRO).update({
        "status": "pending",
        "attempts": 0,
        "locked_by": None,
        "error_message": None,
        "result_data": None,
        "result_consumed": False,
        "updated_at": agora,
        # RENOVAR created_at: o retention apaga pending com >24h por created_at —
        # sem isso, jobs antigos reenfileirados são varridos antes de despachar
        # (incidente 2026-10-22: ~566 dos 1.008 reenfileirados foram purgados).
        "created_at": agora,
    }, synchronize_session=False)
    db.add(Log(user_id=jobs[0].user_id, level="INFO",
               message=f"Reenfileirados {len(ids)} jobs do Fature 'não localizadas' para reprocessamento "
                       f"pela OP1 com cascata (reg_ans × status) e recuperação de sessão (ids {ids[0]}..{ids[-1]})."))
    db.commit()
    print(f"{len(ids)} jobs reenfileirados (pending, attempts=0). "
          f"O dispatcher os pegará nos próximos ciclos (15s por dispatch).")
finally:
    db.close()
