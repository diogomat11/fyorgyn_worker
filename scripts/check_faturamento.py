import os
import sys

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from database import SessionLocal
from models import Procedimento, ProcedimentoFaturamento, Agendamento

def check_db():
    db = SessionLocal()
    print("--- PROCEDIMENTOS ---")
    procs = db.query(Procedimento).all()
    for p in procs:
        print(f"ID:{p.id_procedimento} | Cod:{p.codigo_procedimento} | Fat:{p.faturamento} | Nome:{p.nome}")
        
    print("\n--- AGENDAMENTOS SEM COD FAT ---")
    ags = db.query(Agendamento).filter(Agendamento.cod_procedimento_fat == 'sim').limit(5).all()
    for a in ags:
         print(f"ID:{a.id_agendamento} | Pac:{a.Nome_Paciente} | Fat:{a.cod_procedimento_fat} | Aut:{a.cod_procedimento_aut} | Guia:{a.numero_guia} | Status:{a.Status}")
         
    print(f"\nTotal Agendamentos: {db.query(Agendamento).count()}")
    print(f"Agendamentos com Guia: {db.query(Agendamento).filter(Agendamento.numero_guia != None).count()}")
    print(f"Agendamentos com 'sim' no Fat: {db.query(Agendamento).filter(Agendamento.cod_procedimento_fat == 'sim').count()}")

if __name__ == "__main__":
    check_db()
