"""
Upload de credenciais criptografadas para a tabela convenios.
Insere usuario e senha_criptografada para Unimed Anapolis (id_convenio=2).
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'Local_worker', 'Worker'))

from dotenv import load_dotenv
load_dotenv('Local_worker/.env')
load_dotenv('backend/.env')

from sqlalchemy import create_engine, text
from security_utils import encrypt_password

DB_URL = os.getenv('DATABASE_URL')
engine = create_engine(DB_URL)

# Credenciais extraídas do script original sgucard_anapolis.py
USUARIO = "70205235107"
SENHA = "Baet@270424"

print(f"DB: {DB_URL[:30]}...")
print(f"User: {USUARIO}")
print(f"Encrypting password...")

senha_enc = encrypt_password(SENHA)
print(f"Encrypted (len={len(senha_enc)})")

with engine.connect() as con:
    # Update convenio id=2 (UNIMED ANAPOLIS)
    result = con.execute(
        text("UPDATE convenios SET usuario = :usr, senha_criptografada = :pwd WHERE id_convenio = 2"),
        {"usr": USUARIO, "pwd": senha_enc}
    )
    con.commit()
    
    if result.rowcount == 1:
        print("[OK] Credentials uploaded for UNIMED ANAPOLIS (id=2)")
    else:
        print(f"[WARN] Updated {result.rowcount} rows (expected 1)")
    
    # Verify
    row = con.execute(text("SELECT id_convenio, nome, usuario, senha_criptografada IS NOT NULL as has_pwd FROM convenios WHERE id_convenio = 2")).fetchone()
    print(f"  Verify: id={row[0]}, nome={row[1]}, user={row[2]}, has_pwd={row[3]}")
