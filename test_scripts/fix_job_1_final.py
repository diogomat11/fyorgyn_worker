import os
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found")
    exit(1)

engine = create_engine(db_url)
con = engine.connect()

try:
    print("Updating Job 1...")
    # Set proper routine, priority, and ensure created_at is not null
    con.execute(text("UPDATE jobs SET rotina = 'consulta_guias', priority = 1, status='pending', locked_by=NULL, attempts=0, created_at=COALESCE(created_at, NOW()) WHERE id = 1"))
    
    print("Inserting/Updating Priority Rule for Unimed (3)...")
    # Ensure rule exists
    result = con.execute(text("SELECT id FROM priority_rules WHERE id_convenio = 3 AND rotina = 'consulta_guias'"))
    if not result.fetchone():
        con.execute(text("INSERT INTO priority_rules (id_convenio, rotina, base_priority, weight_per_day, is_active) VALUES (3, 'consulta_guias', 10, 1.0, 1)"))
        print("Rule inserted.")
    else:
        print("Rule already exists.")
        
    con.commit()
    print("Commit successful.")
    
    # Verification
    row = con.execute(text("SELECT id, status, rotina, priority, created_at FROM jobs WHERE id = 1")).fetchone()
    print(f"Job 1 Status: {row}")

except Exception as e:
    print(f"Error: {e}")
finally:
    con.close()
