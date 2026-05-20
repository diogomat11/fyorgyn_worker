import os
import sys
import json
from datetime import datetime

# Adicionar a pasta do backend e do worker ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal
from models import Job
from security_utils import encrypt_password
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', 'backend', '.env'))

def run():
    db = SessionLocal()
    try:
        user_id = 14  # Usuário teste
        id_convenio = 1 # Bradesco

        # Criptografa a senha para que o scraper.py possa descriptografar normalmente
        senha_crip = encrypt_password("Artju2020@")

        # Job 1
        job1_params = {
            "contexto": "fature",
            "login": "diogomat11",
            "senha_criptografada": senha_crip,
            "guia": "1735183101",
            "reg_ans": "005711",
            "dataInicio": "01/03/2026",
            "dataFim": "19/05/2026",
            "prestador_id": "225529"
        }

        job1 = Job(
            user_id=user_id,
            id_convenio=id_convenio,
            rotina="1",
            params=job1_params,
            status="pending",
            created_at=datetime.now()
        )
        db.add(job1)

        # Job 2
        job2_params = {
            "contexto": "fature",
            "login": "diogomat11",
            "senha_criptografada": senha_crip,
            "guia": "1709230996",
            "reg_ans": "005711",
            "dataInicio": "01/03/2026",
            "dataFim": "19/05/2026",
            "prestador_id": "225529"
        }

        job2 = Job(
            user_id=user_id,
            id_convenio=id_convenio,
            rotina="1",
            params=job2_params,
            status="pending",
            created_at=datetime.now()
        )
        db.add(job2)

        db.commit()
        print(f"2 Jobs criados com sucesso! IDs: {job1.id}, {job2.id}")
        print("Agora você pode rodar o Local_worker para processá-los.")

    except Exception as e:
        print(f"Erro ao criar jobs: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run()
