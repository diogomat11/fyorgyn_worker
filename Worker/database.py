"""
Independent database connection for Worker
Connects directly to Supabase without depending on backend code
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load .env from Worker directory, parent directories, or backend/.env
load_dotenv(os.path.join(os.getcwd(), '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', 'backend', '.env'), override=True)

DB_USER = os.getenv("SUPABASE_DB_USER", "postgres")
DB_PASSWORD = os.getenv("SUPABASE_PASSWORD", "")
DB_HOST = os.getenv("SUPABASE_DB_HOST", "db.ourddwzetcbdjnbvamgj.supabase.co")
DB_PORT = os.getenv("SUPABASE_DB_PORT", "5432")
DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")

if DB_HOST and "supabase.co" in DB_HOST and DB_PASSWORD:
    SQLALCHEMY_DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
else:
    SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URL:
        SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    if SQLALCHEMY_DATABASE_URL and ":6543" in SQLALCHEMY_DATABASE_URL:
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(":6543", ":5432")

try:
    with open("db_debug_worker.log", "a") as f:
        f.write(f"DB URL: {SQLALCHEMY_DATABASE_URL}\n")
except: pass

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    use_native_hstore=False,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=300,
    pool_pre_ping=True,
    connect_args={
        "prepare_threshold": None,
        "sslmode": "require",
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
