from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import sys
from contextlib import asynccontextmanager

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Add parent directory for backend imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from factory import ScraperFactory
from selenium_manager import SeleniumManager
from database import SessionLocal
import threading
import time
from datetime import datetime, timedelta

app = FastAPI()
sel_manager = SeleniumManager(max_drivers=1)  # Only 1 Chrome per worker to avoid leaks
last_activity_time = datetime.now()
job_lock = threading.Lock()  # Strict Concurrency Lock

def maintain_driver_lifecycle():
    while True:
        time.sleep(60) # Check every minute
        sel_manager.cleanup_idle()

# Start background thread
threading.Thread(target=maintain_driver_lifecycle, daemon=True).start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Cleanup on shutdown
    with sel_manager.lock:
        for cid in list(sel_manager.drivers.keys()):
            sel_manager.close_driver(cid)

app = FastAPI(lifespan=lifespan)

from typing import Optional, Any
import json as _json

class JobRequest(BaseModel):
    job_id: int
    id_convenio: int
    rotina: Optional[str] = None
    params: Optional[Any] = None  # Accept str or dict
    carteirinha_id: int
    carteirinha: str
    paciente: str = ""
    start_date: str = None
    end_date: str = None

    def get_params_str(self) -> Optional[str]:
        """Always returns params as a JSON string or None."""
        if self.params is None:
            return None
        if isinstance(self.params, dict):
            return _json.dumps(self.params)
        return str(self.params)

@app.get("/")
async def health_check():
    return {
        "status": "ok", 
        "drivers_active": list(sel_manager.drivers.keys())
    }

@app.post("/restart")
def restart_drivers():
    print(">>> Received manual restart request. Closing all drivers...")
    with sel_manager.lock:
        for cid in list(sel_manager.drivers.keys()):
            sel_manager.close_driver(cid)
    return {"status": "success", "message": "All drivers closed and pool cleared"}

@app.post("/process_job")
def process_job(job: JobRequest):
    # Prevent Dispatcher Timeouts/Overlaps from injecting 2 jobs into the SAME Chrome Window
    if not job_lock.acquire(blocking=False):
        print(f">>> REJECTED OVERLAP: Worker is already processing a job! Rejecting Job {job.job_id}")
        raise HTTPException(status_code=409, detail="Worker is currently busy processing another job. Try again later.")

    db = None
    try:
        db = SessionLocal()
        print(f">>> Received Job {job.job_id} for Convenio {job.id_convenio}, Routine {job.rotina}")
        
        # 1. Get/Create Driver for this convenio
        # SeleniumManager maintains sessions keyed by id_convenio.
        # If two jobs for the same convenio arrive, they share the session (logged-in Chrome).
        # Session affinity is handled by the dispatcher which prefers idle servers
        # that already have a session for the requested convenio.
        is_headless = os.environ.get("SGUCARD_HEADLESS", "true").lower() == "true"
        
        driver = sel_manager.get_driver(job.id_convenio, headless=is_headless)
        
        # 2. Get Scraper Instance (generic — determined by job.id_convenio)
        scraper = ScraperFactory.get_scraper(job.id_convenio, db=db, headless=is_headless)
        scraper.driver = driver  # Inject driver
        
        # 3. Process
        print(f">>> Starting routine {job.rotina}...")
        job_data = job.model_dump()
        job_data["params"] = job.get_params_str()

        if hasattr(scraper, 'process_job'):
             results = scraper.process_job(job.rotina, job_data)
        else:
             # Fallback
             results = scraper.process_carteirinha(
                job.carteirinha, 
                job_id=job.job_id, 
                carteirinha_db_id=job.carteirinha_id
             )
             
        print(f">>> Returning {len(results) if results else 0} items for Job {job.job_id}")
        return {"status": "success", "data": results, "job_id": job.job_id}
        
    except Exception as e:
        print(f"Error processing job: {e}")
        return {"status": "error", "message": str(e), "job_id": job.job_id}
    finally:
        if db:
            try: db.close()
            except: pass
        job_lock.release()

def run_server(port=8000, log_queue=None):
    os.environ["PORT"] = str(port)
    uvicorn.run(app, host="0.0.0.0", port=port)

# run_server_with_convenio kept for backward compat — servers are generic now
run_server_with_convenio = run_server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    run_server(port)
