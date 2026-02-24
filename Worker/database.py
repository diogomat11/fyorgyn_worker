"""
Independent database connection for Worker
Connects directly to Supabase without depending on backend code
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load .env from Worker directory or parent directory
load_dotenv(os.path.join(os.getcwd(), '.env')) # Priority: CWD (near exe)
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_USER = os.getenv("SUPABASE_DB_USER", "postgres")
DB_PASSWORD = os.getenv("SUPABASE_PASSWORD", "")
DB_HOST = os.getenv("SUPABASE_DB_HOST", "")
DB_PORT = os.getenv("SUPABASE_DB_PORT", "5432")
DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")

# Prioritize DATABASE_URL if available
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

try:
    with open("db_debug_worker.log", "a") as f:
        f.write(f"DB URL: {SQLALCHEMY_DATABASE_URL}\n")
except: pass

from sqlalchemy.pool import NullPool

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=NullPool,
    pool_pre_ping=True,
    connect_args={"prepare_threshold": None}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
