import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

URL = os.getenv("DATABASE_URL")
if not URL:
    DB_USER = os.getenv("SUPABASE_DB_USER", "postgres")
    DB_PASSWORD = os.getenv("SUPABASE_PASSWORD", "")
    DB_HOST = os.getenv("SUPABASE_DB_HOST", "")
    DB_PORT = os.getenv("SUPABASE_DB_PORT", "5432")
    DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")
    URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(URL)

def reset_all_errors():
    with engine.connect() as conn:
        try:
            # PENDINGS: Reset Error Jobs to Pending with 0 attempts
            query_err = text("UPDATE jobs SET status = 'pending', attempts = 0, locked_by = NULL WHERE status = 'error'")
            res_err = conn.execute(query_err)
            conn.commit()
            print(f"Sucesso! {res_err.rowcount} Jobs em 'Error' foram resetados para 'Pending' com 0 tentativas.")
            
            # GHOST SERVERS: Clear locked_by from success jobs
            query_suc = text("UPDATE jobs SET locked_by = NULL WHERE status = 'success' AND locked_by IS NOT NULL")
            res_suc = conn.execute(query_suc)
            conn.commit()
            print(f"Limpos {res_suc.rowcount} Jobs em 'Success' que ficaram com servidores fantasmas vinculados das versoes antigas.")
            
        except Exception as e:
            print(f"Erro SQL: {e}")

if __name__ == "__main__":
    reset_all_errors()
