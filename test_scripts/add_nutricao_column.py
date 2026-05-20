import sys
import os

# Adiciona a pasta backend ao path para podermos importar
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from database import engine
from sqlalchemy import text

def add_nutricao_column():
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE relatorios_medicos_extracao ADD COLUMN carga_nutricao INTEGER;"))
            print("Coluna 'carga_nutricao' adicionada com sucesso!")
        except Exception as e:
            if "already exists" in str(e).lower() or "já existe" in str(e).lower():
                print("A coluna 'carga_nutricao' já existe no banco de dados.")
            else:
                print(f"Erro ao adicionar coluna: {e}")

if __name__ == "__main__":
    add_nutricao_column()
