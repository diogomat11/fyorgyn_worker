import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Worker"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from database import SessionLocal
from models import Job

def main():
    db = SessionLocal()
    try:
        print("=== Inserindo Job OP1 (Autorização SADT Bradesco) no BD ===")
        
        # PREENCHA COM DADOS REAIS AQUI
        params_op1 = {
            "users_convenio_login": "diogomat11",  # Identifica qual credencial usar (afinidade de sessão)
            "RegistroAns": "005711",
            "cod_prestador": "902446",
            "carteira": "774269017744018",
            "nomeMedico": "ISABELLA LUANNA DE OLIVEIRA MARTINS",
            "ConselhoMedico": "CRM",
            "NumeroRegistroMedico": "28636",
            "UfConselhoMedico": "GO",
            "Cbomedico": "225124",
            "CodigoCid10": "P072",
            "TipoAtendimento": "TERAPIAS",
            "codigoProcedimento": "84250925",
            "qtde_solicitad": 1,
            "caminho_arquivo_RM": r"C:\Users\diogo\Downloads\RM-MAVIE RIBEIRO DE PAIVA-774269017744018.jpeg"
        }
        
        job = Job(
            id_convenio=1, # Bradesco
            rotina="1",    # OP1 - Solicitar Autorização
            user_id=14,    # User ID vinculado na tabela user_convenios
            status="pending",
            priority=0,
            params=params_op1
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        print(f"Job {job.id} inserido com sucesso!")
        print("O Dispatcher (se estiver rodando) vai orquestrá-lo e enviar ao Worker.")
        
    except Exception as e:
        print(f"Erro ao inserir job: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
