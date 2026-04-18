import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv('Local_worker/.env')
load_dotenv('backend/.env')
db_url = os.getenv('DATABASE_URL')
print(f"DB URL: {db_url[:30]}...")
engine = create_engine(db_url)

with engine.connect() as con:
    print("=== Convenios ===")
    rows = con.execute(text("SELECT id_convenio, nome, usuario, senha_criptografada IS NOT NULL as has_pwd FROM convenios ORDER BY id_convenio")).fetchall()
    for r in rows:
        print(f"  id={r[0]}, nome={r[1]}, user={r[2]}, has_pwd={r[3]}")
