import os
from sqlalchemy import create_engine
import pandas as pd
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

url = os.getenv("DATABASE_URL")
if not url:
    url = f"postgresql://postgres:{os.getenv('SUPABASE_PASSWORD')}@{os.getenv('SUPABASE_DB_HOST')}:5432/postgres"

def main():
    engine = create_engine(url)
    print("--- RECENT JOBS ---")
    try:
        df_jobs = pd.read_sql("SELECT id, id_convenio, status, carteirinha_id, priority, rotina, locked_by FROM jobs ORDER BY id DESC LIMIT 20", engine)
        print(df_jobs.to_string())
    except Exception as e:
        print(e)
    
if __name__ == '__main__':
    main()
