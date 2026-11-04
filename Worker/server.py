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
import traceback
from datetime import datetime, timezone

from fastapi.encoders import jsonable_encoder

def _finalize_job_row(db, job_id: int, response: dict):
    """
    Grava o estado final do job DIRETAMENTE em worker.jobs.

    Incidente 2026-10-30 (job 23603, IPASGO OP11): quando o job demora mais
    que o timeout HTTP do dispatcher (600s), a resposta do worker vai para uma
    conexão já fechada e ninguém atualizava a linha — o job ficava 'processing'
    por horas (recover do dispatcher = 180min; reclaim do hub pula worker vivo).

    O UPDATE é condicional (status='processing'): primeiro que escreve ganha.
    Se o dispatcher recebeu a resposta em tempo hábil, ele já gravou o estado e
    o update aqui não altera nada — sem corrida.
    """
    from models import Job as JobModel
    from sqlalchemy import update
    try:
        db.rollback()  # descarta estado sujo da sessão compartilhada com o scraper
        now = datetime.now(timezone.utc)
        # Normaliza para tipos JSON (datas → ISO), igual ao que o HTTP entregaria
        payload = jsonable_encoder(response)
        if response.get("status") == "success":
            stmt = (
                update(JobModel)
                .where(JobModel.id == job_id, JobModel.status == "processing")
                .values(
                    status="success",
                    result_data=payload,
                    result_consumed=False,  # o sync loop do hub (15s) consome
                    locked_by=None,
                    updated_at=now,
                )
            )
        else:
            err = (response.get("message") or "Unknown error from worker")[:1000]
            stmt = (
                update(JobModel)
                .where(JobModel.id == job_id, JobModel.status == "processing")
                .values(
                    status="error",
                    error_message=err,
                    locked_by=None,
                    updated_at=now,
                )
            )
        result = db.execute(stmt)
        db.commit()
        if result.rowcount:
            print(f">>> Job {job_id} finalizado no banco pelo worker (status={response.get('status')}).")
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f">>> Falha ao finalizar job {job_id} no banco: {e}")

class JobRequest(BaseModel):
    job_id: int
    id_convenio: int
    rotina: Optional[str] = None
    params: Optional[Any] = None  # Accept str or dict
    carteirinha_id: Optional[int] = None
    carteirinha: Optional[str] = None
    paciente: str = ""
    start_date: str = None
    end_date: str = None
    user_id: Optional[int] = None

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
    driver_key = (job.id_convenio, job.user_id)
    try:
        db = SessionLocal()
        sel_manager.set_processing(driver_key, True)
        print(f">>> Received Job {job.job_id} for Convenio {job.id_convenio}, Routine {job.rotina}")
        
        # 1. Get/Create Driver for this convenio
        # SeleniumManager maintains sessions keyed by id_convenio.
        # If two jobs for the same convenio arrive, they share the session (logged-in Chrome).
        # Session affinity is handled by the dispatcher which prefers idle servers
        # that already have a session for the requested convenio.
        is_headless = os.environ.get("SGUCARD_HEADLESS", "true").lower() == "true"
        
        driver = sel_manager.get_driver(job.id_convenio, headless=is_headless, user_id=job.user_id)
        
        # 2. Prepare job data payload (antes do factory: o envelope pode carregar
        #    o id_integrador que resolve o pacote do integrador no Local_worker)
        job_data = job.model_dump()
        job_data["params"] = job.get_params_str()

        id_integrador = None
        try:
            _p = job.params if isinstance(job.params, dict) else (_json.loads(job.params) if job.params else {})
            if isinstance(_p, dict):
                id_integrador = _p.get("id_integrador")
        except Exception:
            id_integrador = None

        # 3. Get Scraper Instance (resolvido por id_integrador do envelope;
        #    fallback legado por id_convenio para jobs antigos sem carimbo)
        scraper = ScraperFactory.get_scraper(job.id_convenio, db=db, headless=is_headless, user_id=job.user_id, id_integrador=id_integrador)
        scraper.driver = driver  # Inject driver

        # Force-reload credentials for this specific tenant job
        if hasattr(scraper, 'reload_credentials'):
            if getattr(scraper, 'user_id', None) != job.user_id or not getattr(scraper, 'username', None):
                print(f">>> Reloading credentials for user_id={job.user_id} (scraper had user_id={getattr(scraper, 'user_id', None)})")
                try:
                    scraper.reload_credentials(job.user_id, job_data=job_data)
                except TypeError:
                    scraper.reload_credentials(job.user_id)

        if hasattr(scraper, 'process_job'):
             results = scraper.process_job(job.rotina, job_data)
        else:
             # Fallback
             results = scraper.process_carteirinha(
                job.carteirinha, 
                job_id=job.job_id, 
                carteirinha_db_id=job.carteirinha_id
             )
             
        # Handle both list (normal ops) and dict (self-persisting ops like OP6)
        if isinstance(results, dict) and results.get("self_persisted"):
            meta = results
            print(f">>> Job {job.job_id} self-persisted: {meta.get('inserted', 0)} inserted, {meta.get('updated', 0)} updated")
            resp = {"status": "success", "data": [], "meta": meta, "job_id": job.job_id}
            _finalize_job_row(db, job.job_id, resp)
            return resp

        # Handle dict results that carry a list under "data" plus extra metadata
        # (ex.: op1_consulta da Unimed Goiania devolve {"data": [...], "valida_prestador": {...}}).
        # O envelope raiz recebe as chaves extras (valida_prestador) para que o Hub
        # possa ler res_data.get("valida_prestador") no consumer do webhook.
        if isinstance(results, dict) and isinstance(results.get("data"), list):
            envelope = {"status": "success", "job_id": job.job_id}
            envelope.update(results)  # inclui "data" e quaisquer chaves extras
            print(f">>> Returning {len(envelope.get('data'))} items for Job {job.job_id} (dict payload)")
            _finalize_job_row(db, job.job_id, envelope)
            return envelope

        print(f">>> Returning {len(results) if results else 0} items for Job {job.job_id}")
        resp = {"status": "success", "data": results, "job_id": job.job_id}
        _finalize_job_row(db, job.job_id, resp)
        return resp

    except Exception as e:
        print(f"Error processing job: {e}")
        traceback.print_exc()
        resp = {"status": "error", "message": str(e), "job_id": job.job_id}
        _finalize_job_row(db, job.job_id, resp)
        return resp
    finally:
        sel_manager.set_processing(driver_key, False)
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
