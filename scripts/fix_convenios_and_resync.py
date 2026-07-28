import sys
import os

_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_root = os.path.join(_script_dir, "..", "..", "backend")
sys.path.insert(0, _backend_root)

from database import SessionLocal
from models import Convenio, Carteirinha, Agendamento, Job
from services.guias_sync_service import sync_completed_worker_jobs, _normalize_and_resolve_convenio_id
from sqlalchemy import text

def main():
    db = SessionLocal()
    try:
        print("=== 1. Remapeando carteirinhas e agendamentos invalidos ===")
        # Remap 102 (Sulamérica) -> 8 (SULAMERICA)
        db.query(Carteirinha).filter(Carteirinha.id_convenio == 102).update({Carteirinha.id_convenio: 8})
        db.query(Agendamento).filter(Agendamento.id_convenio == 102).update({Agendamento.id_convenio: 8, Agendamento.nome_convenio: 'SULAMERICA'})

        # Remap 105 (IPASGO - GERAL duplicado) -> 31 (IPASGO - GERAL)
        db.query(Carteirinha).filter(Carteirinha.id_convenio == 105).update({Carteirinha.id_convenio: 31})
        db.query(Agendamento).filter(Agendamento.id_convenio == 105).update({Agendamento.id_convenio: 31, Agendamento.nome_convenio: 'IPASGO - GERAL'})

        # Remap 107 (IPASGO - TEA) -> 6 (IPASGO)
        db.query(Carteirinha).filter(Carteirinha.id_convenio == 107).update({Carteirinha.id_convenio: 6})
        db.query(Agendamento).filter(Agendamento.id_convenio == 107).update({Agendamento.id_convenio: 6, Agendamento.nome_convenio: 'IPASGO'})

        # Remap dummy convenios 28, 33, 35, 41
        for bad_id in [28, 33, 35, 41]:
            target_id, target_name = _normalize_and_resolve_convenio_id(db, None, pagamento_id=bad_id)
            db.query(Carteirinha).filter(Carteirinha.id_convenio == bad_id).update({Carteirinha.id_convenio: target_id})
            db.query(Agendamento).filter(Agendamento.id_convenio == bad_id).update({Agendamento.id_convenio: target_id, Agendamento.nome_convenio: target_name})

        db.commit()

        print("=== 2. Removendo convenios invalidos e duplicados ===")
        bad_ids = [28, 33, 35, 41, 102, 105, 107]
        deleted = db.query(Convenio).filter((Convenio.id_convenio.in_(bad_ids)) | (Convenio.nome.ilike('Convenio_%'))).delete(synchronize_session=False)
        print(f"Removidos {deleted} convenios invalidos/duplicados.")
        db.commit()

        print("=== 3. Atualizando id_convenio 31 para IPASGO - GERAL ===")
        c31 = db.query(Convenio).filter(Convenio.id_convenio == 31).first()
        if c31:
            c31.nome = 'IPASGO - GERAL'
        else:
            db.add(Convenio(id_convenio=31, nome='IPASGO - GERAL'))
        db.commit()

        print("=== 4. Sincronizando sequence convenios_id_convenio_seq ===")
        db.execute(text("SELECT setval('convenios_id_convenio_seq', COALESCE((SELECT MAX(id_convenio) FROM convenios), 1));"))
        db.commit()

        print("=== 5. Resetando consumo dos Jobs (1853, 1854, 1855, 1856, 1857) e reprocessando ===")
        jobs = db.query(Job).filter(Job.id.in_([1853, 1854, 1855, 1856, 1857])).all()
        for j in jobs:
            j.result_consumed = False
        db.commit()

        res = sync_completed_worker_jobs(db)
        print(f"Sincronização concluída: {res}")

        print("\n=== LISTAGEM FINAL DE CONVENIOS ===")
        for c in db.query(Convenio).order_by(Convenio.id_convenio).all():
            print(f"ID: {c.id_convenio} | Nome: {c.nome}")

    except Exception as e:
        db.rollback()
        print(f"[ERRO] {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
