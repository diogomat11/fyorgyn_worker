import sys
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Mocking the context
sys.path.append(os.path.join(os.getcwd(), "Local_worker", "Worker"))
sys.path.append(os.path.join(os.getcwd(), "backend"))

from Local_worker.Worker.models import Job, PriorityRule
from Local_worker.Worker.dispatcher import calculate_job_score
from Local_worker.Worker.database import SessionLocal

def test_scoring():
    db = SessionLocal()
    try:
        print("Fetching pending jobs...")
        pending_jobs = db.query(Job).filter(Job.status == "pending").all()
        print(f"Found {len(pending_jobs)} pending jobs.")
        
        rules = db.query(PriorityRule).filter(PriorityRule.is_active == 1).all()
        rules_map = {(r.id_convenio, r.rotina): r for r in rules}
        print(f"Rules map: {rules_map}")

        for job in pending_jobs:
            print(f"Scoring Job {job.id}: Conv={job.id_convenio}, Rot={job.rotina}, Pri={job.priority}, Created={job.created_at}")
            try:
                score = calculate_job_score(job, rules_map)
                print(f"Score: {score}")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"CRASH scoring job {job.id}: {e}")
                
    except Exception as e:
        print(f"General error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_scoring()
