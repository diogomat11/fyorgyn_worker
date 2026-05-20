"""
Script para inserir um Job real de teste (OP0 - Login Bradesco) no banco de dados.
O Dispatcher deverá capturar esse job e enviar para um Worker processar.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Worker"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from database import SessionLocal
from models import Job
from datetime import datetime

def main():
    db = SessionLocal()
    try:
        print("=== Inserindo Job OP0 (Login Bradesco) no BD ===")
        
        job = Job(
            id_convenio=1,
            rotina="0",
            user_id=14,
            status="pending",
            priority=0,  # Alta prioridade para pegar rápido
            params={"job_id": "teste_dispatcher_bradesco_op0", "rotina_nome": "op0_login"}
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        print(f"Job {job.id} inserido com sucesso!")
        print("O Dispatcher (se estiver rodando) deverá capturá-lo em breve e repassar para um Worker.")
        
    except Exception as e:
        print(f"Erro ao inserir job: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
