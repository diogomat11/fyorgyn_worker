import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv('Local_worker/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as con:
    con.execute(text("UPDATE jobs SET status='pending', attempts=0, locked_by=NULL, updated_at=NOW() WHERE id = 1"))
    con.commit()
    job = con.execute(text("SELECT id, status, attempts, locked_by FROM jobs WHERE id=1")).fetchone()
    print(f"Job 1 reset: status={job[1]}, attempts={job[2]}, locked_by={job[3]}")
