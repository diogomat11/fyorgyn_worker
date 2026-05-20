"""
Seed de credenciais Bradesco para user_id=14.
Executa uma única vez para inserir o registro na tabela user_convenios.

Uso: python scripts/seed_bradesco_credentials.py
"""
import os
import sys

# Resolve paths
_script_dir = os.path.dirname(os.path.abspath(__file__))
_worker_root = os.path.join(_script_dir, "..", "Worker")
sys.path.insert(0, _worker_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(_script_dir, "..", ".env"))

from database import SessionLocal
from models import UserConvenio
from security_utils import encrypt_password

# ── Dados de entrada ──
USER_ID = 14
ID_CONVENIO = 1  # Bradesco
LOGIN = "diogomat11"
SENHA = "Artju2020@"
COD_PRESTADOR_DEFAULT = "935102"  # Psicologia / Fonoaudiologia

def main():
    db = SessionLocal()
    try:
        # Verificar se já existe
        existing = db.query(UserConvenio).filter(
            UserConvenio.user_id == USER_ID,
            UserConvenio.id_convenio == ID_CONVENIO
        ).first()

        senha_enc = encrypt_password(SENHA)

        if existing:
            existing.login = LOGIN
            existing.senha_criptografada = senha_enc
            existing.cod_prestador = COD_PRESTADOR_DEFAULT
            print(f"[UPDATE] Credenciais Bradesco atualizadas para user_id={USER_ID}")
        else:
            new_record = UserConvenio(
                user_id=USER_ID,
                id_convenio=ID_CONVENIO,
                login=LOGIN,
                senha_criptografada=senha_enc,
                cod_prestador=COD_PRESTADOR_DEFAULT
            )
            db.add(new_record)
            print(f"[INSERT] Credenciais Bradesco criadas para user_id={USER_ID}")

        db.commit()
        print(f"  login={LOGIN}")
        print(f"  cod_prestador={COD_PRESTADOR_DEFAULT}")
        print(f"  senha_criptografada={senha_enc[:20]}...")
        print("OK")

    except Exception as e:
        db.rollback()
        print(f"[ERRO] {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
