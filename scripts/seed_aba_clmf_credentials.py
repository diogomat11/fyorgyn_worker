"""
Seed de credenciais ABA_clmf para user_id=1 e user_id=14.
Executa para inserir o registro na tabela user_convenios.

Uso: python scripts/seed_aba_clmf_credentials.py
"""
import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
_worker_root = os.path.join(_script_dir, "..", "Worker")
sys.path.insert(0, _worker_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(_script_dir, "..", ".env"))

from database import SessionLocal
from models import UserConvenio
from security_utils import encrypt_password

USER_IDS = [1, 14]
ID_CONVENIO = 101  # ABA_clmf
LOGIN = "diogomat11@hotmail.com"
SENHA = "Arju2020@"

def main():
    db = SessionLocal()
    try:
        senha_enc = encrypt_password(SENHA)
        for user_id in USER_IDS:
            existing = db.query(UserConvenio).filter(
                UserConvenio.user_id == user_id,
                UserConvenio.id_convenio == ID_CONVENIO
            ).first()

            if existing:
                existing.login = LOGIN
                existing.senha_criptografada = senha_enc
                print(f"[UPDATE] Credenciais ABA_clmf atualizadas para user_id={user_id}")
            else:
                new_record = UserConvenio(
                    user_id=user_id,
                    id_convenio=ID_CONVENIO,
                    login=LOGIN,
                    senha_criptografada=senha_enc
                )
                db.add(new_record)
                print(f"[INSERT] Credenciais ABA_clmf criadas para user_id={user_id}")

        db.commit()
        print("Credenciais salvas com sucesso.")
    except Exception as e:
        db.rollback()
        print(f"[ERRO] {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
