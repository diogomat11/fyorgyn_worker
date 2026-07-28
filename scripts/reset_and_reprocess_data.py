import sys
import os

_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_root = os.path.join(_script_dir, "..", "..", "backend")
sys.path.insert(0, _backend_root)

from database import SessionLocal
from models import Convenio, Carteirinha, Agendamento, Job
from services.guias_sync_service import sync_completed_worker_jobs
from sqlalchemy import text

def main():
    db = SessionLocal()
    try:
        print("=== 1. Removendo agendamentos da data 23/07/2026 ===")
        del_ag = db.query(Agendamento).filter(Agendamento.data == '2026-07-23').delete(synchronize_session=False)
        print(f"Removidos {del_ag} agendamentos da data 23/07/2026.")
        db.commit()

        print("=== 2. Removendo carteirinhas com id_convenio 101 ou registradas em 23/07 ===")
        del_cart = db.query(Carteirinha).filter((Carteirinha.id_convenio == 101) | (Carteirinha.created_at >= '2026-07-23')).delete(synchronize_session=False)
        print(f"Removidas {del_cart} carteirinhas vinculadas ao 101 ou criadas em 23/07.")
        db.commit()

        print("=== 3. Resetando sequence convenios_id_convenio_seq ===")
        db.execute(text("SELECT setval('convenios_id_convenio_seq', COALESCE((SELECT MAX(id_convenio) FROM convenios), 1));"))
        db.commit()

        print("=== 4. Resetando result_consumed = False para Job 1854 e TODOS os jobs de OP2 ===")
        jobs = db.query(Job).filter((Job.id == 1854) | ((Job.id_convenio == 101) & (Job.rotina.in_(['op2_consultar_carteirinha', 'op2'])))).all()
        for j in jobs:
            j.result_consumed = False
        db.commit()
        print(f"Resetados {len(jobs)} jobs para consumo pelo backend sync.")

        print("=== 5. Reprocessando sincronizacao do zero ===")
        res = sync_completed_worker_jobs(db)
        print(f"Sincronização concluída: {res}")

        print("\n=== LISTAGEM FINAL DE CONVENIOS ===")
        for c in db.query(Convenio).order_by(Convenio.id_convenio).all():
            print(f"ID: {c.id_convenio:<4} | Nome: {c.nome}")

        print("\n=== VERIFICACAO DA BASE DE DADOS ===")
        tot_23 = db.query(Agendamento).filter(Agendamento.data == '2026-07-23').count()
        tot_sem_cart = db.query(Agendamento).filter((Agendamento.carteirinha == None) | (Agendamento.carteirinha == '')).count()
        tot_cart_101 = db.query(Carteirinha).filter(Carteirinha.id_convenio == 101).count()
        print(f"Total Agendamentos em 23/07/2026: {tot_23} (Esperado: 809)")
        print(f"Agendamentos sem carteirinha: {tot_sem_cart}")
        print(f"Carteirinhas com id_convenio=101: {tot_cart_101} (Esperado: 0)")

    except Exception as e:
        db.rollback()
        print(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
