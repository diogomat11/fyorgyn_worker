import os
import sys

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from database import SessionLocal
from models import Agendamento
from sqlalchemy import text

def touch_again():
    db = SessionLocal()
    print("Iniciando toque (touch) final nos Agendamentos...")
    try:
        sql = """
            UPDATE agendamentos 
            SET data_update = NOW() 
            WHERE numero_guia IS NULL 
            AND "Status" NOT IN ('Falta', 'Cancelado')
        """
        result = db.execute(text(sql))
        db.commit()
        print(f"Toque (Touch) dado. A nova trigger AFTER os fará buscar as Guias com Saldo ativamente!")
    except Exception as e:
        db.rollback()
        print(f"Erro no touch de agendamentos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    touch_again()
