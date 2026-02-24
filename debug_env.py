import sys
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Mimic dispatcher imports
sys.path.append(os.path.join(os.getcwd(), 'Worker'))

try:
    from Worker.database import engine, SQLALCHEMY_DATABASE_URL
except ImportError:
    # Try direct import if running from inside Worker
    sys.path.append(os.getcwd())
    from database import engine, SQLALCHEMY_DATABASE_URL

print(f"CWD: {os.getcwd()}")
print(f"DATABASE_URL Env Var: {os.getenv('DATABASE_URL')}")
print(f"SQLALCHEMY_DATABASE_URL: {SQLALCHEMY_DATABASE_URL}")
print(f"Engine URL: {engine.url}")
print(f"Engine Driver: {engine.driver}")
