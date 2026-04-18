import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

DB_USER = os.getenv("SUPABASE_DB_USER", "postgres")
DB_PASSWORD = os.getenv("SUPABASE_PASSWORD", "")
DB_HOST = os.getenv("SUPABASE_DB_HOST", "")
DB_PORT = os.getenv("SUPABASE_DB_PORT", "5432")
DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")

URL = os.getenv("DATABASE_URL")
if not URL:
    URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(URL)

def purge_connections():
    with engine.connect() as conn:
        try:
            # Terminate idle connections from other processes
            query = text("""
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = 'postgres' 
                  AND pid <> pg_backend_pid() 
                  AND state in ('idle', 'idle in transaction', 'idle in transaction (aborted)', 'disabled');
            """)
            result = conn.execute(query)
            conn.commit()
            count = result.rowcount
            print(f"Purged {count} ghost database connections from Supabase.")
        except Exception as e:
            print(f"Error purging: {e}")

if __name__ == "__main__":
    purge_connections()
