import sys
import os
import time
import requests
import logging
from datetime import datetime, timedelta


import socket
import threading

# Fix for noconsole mode where stdout/stderr are None
class FileLogStream:
    def __init__(self, filename):
        self.filename = filename
        try: self.log_file = open(filename, "a", encoding="utf-8")
        except: self.log_file = None
    def write(self, data):
        try:
            if self.log_file:
                    self.log_file.write(data)
                    self.log_file.flush()
        except: pass
    def flush(self):
        try: 
            if self.log_file: self.log_file.flush()
        except: pass
    def isatty(self): return False

if sys.stdout is None: sys.stdout = FileLogStream("dispatcher_debug.log")
if sys.stderr is None: sys.stderr = FileLogStream("dispatcher_err.log")

# Use local Worker modules (independent of backend)
from database import SessionLocal
from models import Job, BaseGuia, Log, Carteirinha, PriorityRule

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:8000")
HOSTNAME = socket.gethostname()




class QueueLogger:
    def __init__(self, queue, prefix="Dispatcher"):
        self.queue = queue
        self.prefix = prefix
    def write(self, message):
        if message.strip():
            self.queue.put(f"[{self.prefix}] {message.strip()}")
    def flush(self):
        pass
    def isatty(self):
        return False


def calculate_effective_priority(job, rules_map):
    """
    Calculate the effective priority for a job at the current moment.
    
    Rule: effective_priority = max(0, base_priority - floor(age_minutes / escalation_minutes))
    
    - Lower value = HIGHER priority (0 = top of queue)
    - Without a rule: effective_priority = 0 (always top)
    - With base_priority=2, escalation_minutes=10:
        t=0min  -> eff=2
        t=10min -> eff=1 
        t=20min -> eff=0  <- top of queue
    """
    rule = rules_map.get((job.id_convenio, job.rotina))
    # Fallback: match by convenio only (any rotina)
    if not rule:
        rule = rules_map.get((job.id_convenio, None))
    
    if not rule:
        return 0  # No rule = always top priority
    base_priority_attr = getattr(rule, 'base_priority', 2)
    base = base_priority_attr if base_priority_attr is not None else 2
    escalation = getattr(rule, 'escalation_minutes', 10) or 10
    
    try:
        now = datetime.now(job.created_at.tzinfo) if job.created_at and job.created_at.tzinfo else datetime.utcnow()
        if job.created_at:
            age_minutes = (now - job.created_at).total_seconds() / 60.0
        else:
            age_minutes = 0
    except Exception:
        age_minutes = 0
    
    steps = int(age_minutes / escalation)
    return max(0, base - steps)

# Keep calculate_job_score as alias so existing code doesn't break
calculate_job_score = calculate_effective_priority

def get_ranked_pending_jobs(db, limit=20):
    """
    Fetch and rank ALL pending jobs by EFFECTIVE priority (ASC — 0 first = highest priority).
    Uses time-based escalation: effective_priority = max(0, base - floor(age_min / escalation_min)).
    Jobs at the same effective priority are ordered by created_at ASC (oldest first).
    """
    try:
        rules = db.query(PriorityRule).filter(PriorityRule.is_active == True).all()
        rules_map = {(r.id_convenio, r.rotina): r for r in rules}
        # Also add fallback (convenio, None) entries
        for r in rules:
            if r.rotina is not None and (r.id_convenio, None) not in rules_map:
                rules_map[(r.id_convenio, None)] = r
        
        pending_jobs = db.query(Job).filter(Job.status == "pending").limit(limit).all()
        if not pending_jobs:
            return []
        
        # effective_priority ASC (0 first), then created_at ASC
        scored_jobs = [(calculate_effective_priority(j, rules_map), j.created_at or datetime.utcnow(), j)
                       for j in pending_jobs]
        scored_jobs.sort(key=lambda x: (x[0], x[1]))
        return [j for _, _, j in scored_jobs]
    except Exception as e:
        logger.error(f"Error ranking pending jobs: {e}")
        return db.query(Job).filter(Job.status == "pending") \
                  .order_by(Job.priority.asc(), Job.created_at.asc()).limit(limit).all()


# Keep for backward compatibility
def get_pending_job(db, allowed_convenio_ids=None):
    jobs = get_ranked_pending_jobs(db, limit=50)
    if allowed_convenio_ids:
        jobs = [j for j in jobs if j.id_convenio in allowed_convenio_ids]
    return jobs[0] if jobs else None


def retry_failed_jobs(db):
    try:
        from datetime import datetime, timedelta
        # Check for jobs with status='error' and attempts < 3.
        # We explicitly IGNORE locked_by here, because if they are in 'error', the lock is a ghost.
        # Add a 20s cooldown so rapid failures don't instantly loop the queue
        threshold = datetime.utcnow() - timedelta(seconds=20)
        failed_jobs = db.query(Job).filter(
            Job.status == "error",
            Job.attempts < 3,
            Job.updated_at < threshold
        ).all()
        
        if failed_jobs:
            logger.info(f"Retrying {len(failed_jobs)} failed jobs...")
            for job in failed_jobs:
                job.status = "pending"
                job.locked_by = None
                job.updated_at = datetime.utcnow()
            db.commit()
    except Exception as e:
        logger.error(f"Error resetting failed jobs: {e}")

def recover_stuck_jobs(db):
    try:
        from datetime import timedelta
        # If a job is 'processing' for more than 15 minutes, the Generic Worker thread 
        # or Chrome must have entirely died (e.g. OOM Kills, MaxClients crashes) without 
        # reaching the final block to unlock it.
        threshold = datetime.utcnow() - timedelta(minutes=15)
        stuck_jobs = db.query(Job).filter(
            Job.status == "processing",
            Job.updated_at < threshold
        ).all()
        
        if stuck_jobs:
            logger.info(f"Recovering {len(stuck_jobs)} jobs frozen in 'processing'...")
            for job in stuck_jobs:
                job.status = "error" if job.attempts >= 3 else "pending"
                job.locked_by = None
                job.updated_at = datetime.utcnow()
            db.commit()
    except Exception as e:
        logger.error(f"Error recovering stuck jobs: {e}")

def send_heartbeat(status_map, cmd_queue=None, active_workers=None):
    """
    Sends heatbeat for each worker/slot.
    """
    try:
        for url, meta in status_map.items():
            # Derive a unique name for this slot
            try:
                port = url.split(":")[-1]
            except:
                port = "0"
            
            if active_workers is not None and int(port) not in active_workers:
                continue
                
            worker_name = f"{HOSTNAME}-{port}"
            
            # Check if worker is actually reachable
            real_status = "offline"
            try:
                # Short timeout check
                hr = requests.get(url, timeout=1)
                if hr.status_code == 200:
                    real_status = meta["status"] # Trust internal state if reachable
            except:
                # Unreachable. Distinguish Crash vs Stop based on active_workers dict
                is_expected = False
                if active_workers:
                    try:
                        # Keys in active_workers are likely ints (port)
                        is_expected = active_workers.get(int(port), False)
                    except:
                        pass
                
                if is_expected:
                    real_status = "error" # Should be running, but isn't -> CRASH
                else:
                    real_status = "offline" # NOT expected -> Offline

            payload = {
                "hostname": worker_name,
                "status": real_status,
                "current_job_id": meta.get("last_job") if meta["status"] == "busy" else None,
                "meta": {"url": url, "type": "slot"}
            }
            
            try:
                resp = requests.post(f"{BACKEND_API_URL}/workers/heartbeat", json=payload, timeout=5)
                # ...
                data = resp.json()
                
                if data.get("command") == "restart":
                     # ... existing logic ...
                     if cmd_queue:
                         cmd_queue.put(("RESTART", int(port)))
                     else:
                         try: requests.post(f"{url}/restart", timeout=10)
                         except: pass

            except Exception as req_e:
                pass

    except Exception as e:
        logger.error(f"Heartbeat Loop Error: {e}")

def start_heartbeat_loop(status_map, interval=10, cmd_queue=None, active_workers=None):
    def loop():
        while True:
            send_heartbeat(status_map, cmd_queue, active_workers)
            time.sleep(interval)
    
    t = threading.Thread(target=loop, daemon=True)
    t.start()


def _parse_server_urls(server_urls_str):
    """
    Parse server URL configuration into a dict mapping url -> id_convenio list.
    
    Supported formats:
      - Legacy (no convenio): "http://127.0.0.1:9000,http://127.0.0.1:9001"
        -> All servers accept all jobs (backward compatible)
      - New (with convenio): "http://127.0.0.1:9000:2,http://127.0.0.1:9001:2,http://127.0.0.1:9002:3"
        -> Servers are filtered to only process jobs for their convenio
    
    Disambiguation: a standard http URL has exactly 2 colons (http: + host:port).
    If there are 3 or more colons, the LAST segment is the convenio id.
    
    Returns: dict of {url: [id_convenio, ...] or None}
    """
    server_convenio_map = {}
    for entry in server_urls_str.split(","):
        entry = entry.strip()
        if not entry:
            continue
        # Count colons. Standard http://host:port has exactly 2 colons.
        # http://host:port:convenio_id has 3 colons.
        colon_count = entry.count(":")
        if colon_count >= 3:
            # Has convenio suffix: split off the last segment
            url_part, last = entry.rsplit(":", 1)
            if last.isdigit():
                conv_id = int(last)
                if url_part not in server_convenio_map:
                    server_convenio_map[url_part] = []
                server_convenio_map[url_part].append(conv_id)
            else:
                # Malformed — treat as no convenio
                server_convenio_map[entry] = None
        else:
            # Standard URL — no convenio suffix, accepts all jobs
            server_convenio_map[entry] = None
    return server_convenio_map



def run_dispatcher(server_urls_str=None, stagger=15, log_queue=None, cmd_queue=None, active_workers=None):
    if log_queue:
        sys.stdout = QueueLogger(log_queue, "Dispatcher")
        sys.stderr = QueueLogger(log_queue, "Dispatcher ERR")

    logger.info("Starting Dispatcher...")
    
    raw_urls_str = server_urls_str or os.environ.get("API_SERVER_URLS", "http://127.0.0.1:8000")
    
    # Parse URL->convenio mapping
    server_convenio_map = _parse_server_urls(raw_urls_str)
    servers = list(server_convenio_map.keys())
    
    logger.info(f"Dispatcher configured with {len(servers)} server(s):")
    for url, convs in server_convenio_map.items():
        logger.info(f"  {url} -> convenios: {convs if convs else 'ALL'}")

    server_status_map = {url: {"status": "idle", "last_job": None, "convenio_ids": server_convenio_map[url]} for url in servers}
    dispatch_stagger_val = stagger

    # Start Heartbeat Thread
    start_heartbeat_loop(server_status_map, cmd_queue=cmd_queue, active_workers=active_workers)





    # Define call_server outside loop to avoid redefinition, but it needs access to server_status_map
    # easier to keep it inside or pass map as arg. Let's pass map as arg or use closure here.
    
    def call_server(url, job_id, carteirinha, carteirinha_id, id_convenio, rotina, params, status_map):
        db = SessionLocal()
        import json as _json
        try:
            # Ensure params is serialized as a JSON string (not a dict)
            # SQLAlchemy on PostgreSQL JSONB columns may return a dict instead of str
            if isinstance(params, dict):
                params_str = _json.dumps(params)
            elif isinstance(params, str):
                params_str = params
            else:
                params_str = None

            payload = {
                "job_id": job_id,
                "id_convenio": id_convenio,
                "rotina": rotina,
                "params": params_str,
                "carteirinha_id": carteirinha_id,
                "carteirinha": carteirinha,
                "paciente": "" 
            }
            # Log attempt
            db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, level="INFO", message=f"Dispatching to {url}"))
            db.commit()

            # Close DB connection to free Supabase pool during long HTTP wait (up to 300s)
            db.close()
            
            try:
                resp = requests.post(f"{url}/process_job", json=payload, timeout=300)
            finally:
                # Re-acquire connection to process results or errors
                db = SessionLocal()
            
            try:
                data = resp.json()
            except ValueError: 
                err_msg = f"Invalid JSON ({resp.status_code}): {resp.text[:200]}"
                db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, level="ERROR", message=f"Worker Protocol Error: {err_msg}"))
                db.commit()
                raise Exception(err_msg)

            current_job = db.query(Job).filter(Job.id == job_id).first()
            if not current_job: return

            if resp.status_code == 409:
                # Worker is strictly busy. Dispatcher overlapped requests (Race Condition)
                current_job.status = "pending"
                current_job.locked_by = None
                current_job.attempts = max(0, current_job.attempts - 1) # Refund the attempt
                db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, level="WARN", message="Worker Port returned 409 Busy -> Retornando Job para fila Pending."))
                current_job.updated_at = datetime.utcnow()
                db.commit()
                return

            if data.get("status") == "success":
                current_job.status = "success"
                current_job.locked_by = None
                current_job.updated_at = datetime.utcnow()
                results = data.get("data", [])
                
                try:
                    count_inserted = 0
                    count_updated = 0
                    
                    def parse_date(date_str):
                        if not date_str or not isinstance(date_str, str): return None
                        try: return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
                        except: return None
                        
                    def parse_int_safe(val, default=0):
                        try:
                            clean = str(val).strip()
                            if not clean: return default
                            return int(clean)
                        except:
                            return default

                    for item in results:
                        try:
                            qtd_solic_val = parse_int_safe(item.get("qtde_solicitada"), 0)
                            qtd_aut_val = parse_int_safe(item.get("qtde_autorizada"), 0)
                            guia_num = str(item.get("numero_guia", "")).strip()
                            data_auth_parsed = parse_date(item.get("data_autorizacao"))
                            validade_parsed = parse_date(item.get("validade_senha"))
                            senha_val = str(item.get("senha", "")).strip() if item.get("senha") else None
                            
                            existing_guia = db.query(BaseGuia).filter(
                                BaseGuia.carteirinha_id == carteirinha_id,
                                BaseGuia.id_convenio == id_convenio,
                                BaseGuia.guia == guia_num
                            ).first()
                            
                            status_guia_val = str(item.get("status_guia", "Autorizado")).strip()

                            if existing_guia:
                                existing_guia.data_autorizacao = data_auth_parsed
                                existing_guia.senha = senha_val
                                existing_guia.status_guia = status_guia_val
                                existing_guia.validade = validade_parsed
                                existing_guia.codigo_terapia = item.get("codigo_terapia")
                                existing_guia.qtde_solicitada = qtd_solic_val
                                existing_guia.sessoes_autorizadas = qtd_aut_val
                                existing_guia.updated_at = datetime.utcnow()
                                count_updated += 1
                            else:
                                # Apenas guias AUTORIZADAS ou EM ESTUDO podem ser inseridas como novas
                                if status_guia_val.upper() not in ["AUTORIZADO", "EM ESTUDO"]:
                                    continue
                                
                                new_guia = BaseGuia(
                                    id_convenio=id_convenio,
                                    carteirinha_id=carteirinha_id,
                                    guia=guia_num,
                                    data_autorizacao=data_auth_parsed,
                                    senha=senha_val,
                                    status_guia=status_guia_val,
                                    validade=validade_parsed,
                                    codigo_terapia=item.get("codigo_terapia"),
                                    qtde_solicitada=qtd_solic_val,
                                    sessoes_autorizadas=qtd_aut_val,
                                    created_at=datetime.utcnow()
                                )
                                db.add(new_guia)
                                count_inserted += 1
                        except Exception as item_e:
                            import traceback
                            trace_str = traceback.format_exc()
                            logger.error(f"Error processing item: {item_e}\n{trace_str}")
                            db.add(Log(
                                job_id=job_id, 
                                carteirinha_id=carteirinha_id, 
                                level="ERROR", 
                                message=f"Item falhou guia {item.get('numero_guia')}: {item_e} | Payload: {str(item)[:200]}"
                            ))
                            db.commit()

                    db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, level="INFO", message=f"Sync complete. Inserted: {count_inserted}, Updated: {count_updated}"))
                    db.commit()
                except Exception as save_e:
                    logger.error(f"Error saving results: {save_e}")
                    db.rollback()
                    db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, level="ERROR", message=f"Error saving results: {save_e}"))
                    db.commit()
                    current_job.status = "error"
            else:
                current_job.status = "error"
                current_job.locked_by = None
                current_job.updated_at = datetime.utcnow()
                err_msg = data.get("message") or data.get("detail") or "Unknown error from server"
                
                # Regra de Negócio PO: Interromper Retentativas para erros Fatais (Carteira Inválida)
                if "carteira inv" in err_msg.lower() or "dígito" in err_msg.lower() or "invalida" in err_msg.lower():
                    current_job.attempts = max(3, current_job.attempts)
                    
                db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, level="ERROR", message=f"Worker Error: {err_msg}"))
            
            db.commit()
            
        except requests.exceptions.ConnectionError:
            # Expected if the worker slot is physically offline right now
            try:
                current_job = db.query(Job).filter(Job.id == job_id).first()
                if current_job:
                    current_job.status = "error"
                    current_job.locked_by = None
                    current_job.updated_at = datetime.utcnow()
                    db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, level="ERROR", message="Worker is Offline (Connection Refused)."))
                    db.commit()
            except: pass
        except Exception as e:
            logger.error(f"Error calling server {url}: {e}")
            try:
                current_job = db.query(Job).filter(Job.id == job_id).first()
                if current_job:
                    current_job.status = "error"
                    current_job.locked_by = None
                    current_job.updated_at = datetime.utcnow()
                    db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, level="ERROR", message=f"Dispatcher Failed: {str(e)}"))
                    db.commit()
            except: pass
        finally:
            db.close()
            status_map[url]["status"] = "idle"

    while True:
        db = SessionLocal()
        try:
            # 0. Retry failed jobs & sweep dead processing jobs
            retry_failed_jobs(db)
            recover_stuck_jobs(db)

            # 1. Check available servers
            available_servers = []
            for url, meta in server_status_map.items():
                if meta["status"] != "idle":
                    continue
                try:
                    port = int(url.split(":")[-1])
                    is_active = active_workers.get(port, False) if active_workers else True
                except:
                    is_active = True
                if is_active:
                    # Also consider double checking if it is up, but heartbeat handles that
                    available_servers.append(url)
            with open("dispatcher_debug.txt", "a") as f:
                # f.write(f"{datetime.now()} - DEBUG: Available: {len(available_servers)}\n")
                pass

            if not available_servers:
                pass
            else:
                # ── Orchestrated Dispatch: Effective Priority + Session Affinity + Server Configs ──
                # Jobs ranked by effective_priority ASC (0 = highest priority).
                # For EACH job, find the BEST idle server using:
                #   1. Server with a matching server_config (preferred convenio/rotina) AND existing session
                #   2. Server with matching server_config only
                #   3. Server with matching last_convenio_id (session affinity) only
                #   4. Any idle server (fallback)
                ranked_jobs = get_ranked_pending_jobs(db, limit=len(available_servers) * 2)
                dispatched_servers = set()
                
                # Load server preference configs for this cycle
                try:
                    from models import ServerConfig
                    srv_cfgs = db.query(ServerConfig).filter(ServerConfig.is_active == True).all()
                    # Map: server_url -> config row
                    srv_cfg_map = {c.server_url: c for c in srv_cfgs}
                except Exception:
                    srv_cfg_map = {}
                
                def pick_server(job, idle_servers):
                    """Pick the best idle server for this job using priority rules."""
                    
                    last_conv_match = []
                    for s in idle_servers:
                        if server_status_map[s].get("last_convenio_id") == job.id_convenio:
                            # Verify if this URL has an explicit hardcoded Convenio restriction from ENV
                            bindings = server_convenio_map.get(s)
                            if bindings is None or job.id_convenio in bindings:
                                last_conv_match.append(s)
                    
                    cfg_match = []
                    for s in idle_servers:
                        cfg = srv_cfg_map.get(s)
                        if cfg:
                            if cfg.id_convenio == job.id_convenio and (cfg.rotina is None or cfg.rotina == job.rotina):
                                cfg_match.append(s)
                        else:
                            # If no DB config, check ENV hardcoded list
                            bindings = server_convenio_map.get(s)
                            if bindings is not None and job.id_convenio in bindings:
                                cfg_match.append(s)
                    
                    # 1. Best: specific config match + session match
                    both = [s for s in cfg_match if s in last_conv_match]
                    if both: return both[0]
                    
                    # 2. Good: specific config match only
                    if cfg_match: return cfg_match[0]
                    
                    # 3. OK: session affinity only (and is allowed to take it)
                    if last_conv_match: return last_conv_match[0]
                    
                    # 4. Fallback: Any idle server that isn't hard-restricted to another convenio
                    for s in idle_servers:
                        bindings = server_convenio_map.get(s)
                        if bindings is None:
                            return s
                            
                    # 5. Last resort (should technically not happen if jobs are filtered correctly)
                    return idle_servers[0]
                
                for job in ranked_jobs:
                    idle = [s for s in available_servers if s not in dispatched_servers]
                    if not idle:
                        break
                    
                    server_url = pick_server(job, idle)

                    
                    # --- Anti double-dispatch: row-level lock ---
                    try:
                        try:
                            from sqlalchemy import select as sa_select
                            locked_job = db.execute(
                                sa_select(Job)
                                .where(Job.id == job.id)
                                .where(Job.status == "pending")
                                .with_for_update(skip_locked=True)
                            ).scalars().first()
                        except Exception:
                            locked_job = job  # Fallback if FOR UPDATE not supported

                        if locked_job is None:
                            logger.info(f"Job {job.id} already taken by another process, skipping.")
                            continue

                        # Determine if session matches for logging
                        session_match = server_status_map[server_url].get("last_convenio_id") == job.id_convenio
                        
                        with open("dispatcher_debug.txt", "a") as f:
                            affinity = "(session match)" if session_match else "(new session)"
                            f.write(f"{datetime.now()} - Assigning job {locked_job.id} "
                                    f"(conv={locked_job.id_convenio}) to {server_url} {affinity}\n")
                        
                        # Mark job + server as taken
                        locked_job.status = "processing"
                        locked_job.locked_by = server_url
                        locked_job.attempts += 1
                        locked_job.updated_at = datetime.now(locked_job.created_at.tzinfo) if locked_job.created_at.tzinfo else datetime.utcnow()
                        db.commit()

                        print(f"Assigning Job {locked_job.id} (conv={locked_job.id_convenio}) "
                              f"to {server_url} {'(session match)' if session_match else ''}")
                    except Exception as e:
                        logger.error(f"Error locking/assigning job {job.id}: {e}")
                        db.rollback()
                        continue
                    
                    server_status_map[server_url]["status"] = "busy"
                    server_status_map[server_url]["last_convenio_id"] = locked_job.id_convenio
                    dispatched_servers.add(server_url)
                    
                    # Spawn thread to call worker server
                    t = threading.Thread(
                        target=call_server,
                        args=(server_url, locked_job.id, locked_job.carteirinha_rel.carteirinha,
                              locked_job.carteirinha_id, locked_job.id_convenio,
                              locked_job.rotina, locked_job.params, server_status_map)
                    )
                    t.start()
                    
                    # 1 second delay to let the worker startup Chrome before rapidly dispatching next
                    time.sleep(1)
        except Exception as e:
            logger.error(f"Dispatcher Loop Error: {e}")
            try:
                import traceback
                with open("dispatcher_debug.txt", "a") as f:
                    f.write(f"{datetime.now()} - ERROR: {e}\n")
                    f.write(traceback.format_exc() + "\n")
            except: pass
        finally:
            if db:
                try: db.close()
                except: pass
            time.sleep(15)

if __name__ == "__main__":
    run_dispatcher()
