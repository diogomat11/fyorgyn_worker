import os
import sys

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from database import SessionLocal
from models import Procedimento
from sqlalchemy import text

def run_fix():
    db = SessionLocal()
    print("Atualizando a coluna `faturamento` na tabela de procedimentos...")
    
    # Busca dinamicamente e atualiza faturamento pra ser == codigo_procedimento da propria tabela
    try:
        updated = 0
        procs = db.query(Procedimento).all()
        for p in procs:
            if p.faturamento != p.codigo_procedimento:
                p.faturamento = p.codigo_procedimento
                updated += 1
                
        db.commit()
        print(f"[{updated}] procedimentos atualizados. Todas as chaves primarias pareadas no TUSS.")
    except Exception as e:
        db.rollback()
        print(f"Erro ao salvar fix no db: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_fix()
