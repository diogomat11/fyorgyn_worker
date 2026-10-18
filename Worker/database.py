"""
Independent database connection for Worker
Connects directly to Supabase without depending on backend code
"""
import os
from urllib.parse import urlsplit

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load .env from Worker directory, parent directories, or backend/.env
load_dotenv(os.path.join(os.getcwd(), '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', 'backend', '.env'))

DB_USER = os.getenv("SUPABASE_DB_USER", "postgres")
DB_PASSWORD = os.getenv("SUPABASE_PASSWORD", "")
DB_HOST = os.getenv("SUPABASE_DB_HOST", "db.ourddwzetcbdjnbvamgj.supabase.co")
DB_PORT = os.getenv("SUPABASE_DB_PORT", "5432")
DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")

# Prefer DATABASE_URL when explicitly set: it points to the Supabase POOLER
# (IPv4), required because the direct host db.<ref>.supabase.co is IPv6-only
# and times out on IPv4-only networks. Force port 5432 (session mode), safe
# for SQLAlchemy ORM. Falls back to the SUPABASE_DB_* variables otherwise.
_DATABASE_URL_ENV = os.getenv("DATABASE_URL", "").strip()
if _DATABASE_URL_ENV:
    SQLALCHEMY_DATABASE_URL = _DATABASE_URL_ENV.replace(":6543", ":5432")
else:
    if DB_PORT == "6543":
        DB_PORT = "5432"  # transaction mode -> session mode
    SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

try:
    _parsed = urlsplit(SQLALCHEMY_DATABASE_URL)
    with open("db_debug_worker.log", "a") as f:
        f.write(f"DB URL: {_parsed.scheme}://{_parsed.username}@{_parsed.hostname}:{_parsed.port or 5432}/{_parsed.path.lstrip('/')}\n")
except Exception: pass

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
