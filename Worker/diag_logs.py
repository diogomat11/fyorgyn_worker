import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Job, Log, ServerConfig
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))
URL = os.getenv("DATABASE_URL")
if not URL:
    URL = f"postgresql://postgres:{os.getenv('SUPABASE_PASSWORD')}@{os.getenv('SUPABASE_DB_HOST')}:5432/postgres"

engine = create_engine(URL)
SessionLocal = sessionmaker(bind=engine)

db = SessionLocal()
print("--- RECENT LOGS ---")
for log in db.query(Log).order_by(Log.id.desc()).limit(30).all():
    print(f"[{log.level}] {log.message}")

print("\n--- JOB STATUS ---")
for job in db.query(Job).order_by(Job.updated_at.desc()).limit(10).all():
    print(f"Job {job.id} | Conv {job.id_convenio} | {job.rotina} | {job.status} | Atmpt {job.attempts} | Lock {job.locked_by}")

print("\n--- SERVER STATUS ---")
for s in db.query(ServerConfig).all():
    print(f"{s.server_url} | {s.status}")

db.close()
