import sys
import os
import time
import requests
import logging
from datetime import datetime, timedelta, timezone


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
from models import Job, Log, PriorityRule
from sqlalchemy.orm import defer

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:8000")
HOSTNAME = socket.gethostname()


# ── Resolução data-driven de tipo_operacao (plano integradores agendamento, D7) ──
# Substitui o hardcode `job.id_convenio in (100, 101)` pela cadeia
# convenios.id_integrador → worker.integradores.tipo_operacao (cache TTL 5min).
_TIPO_OPERACAO_TTL = 300.0
_TIPO_OPERACAO_CACHE = {"map": {}, "expires": 0.0}
_ROTINAS_ATIVAS_CACHE = {"map": {}, "expires": 0.0}


def _mapa_tipo_operacao(db):
    """{id_convenio: tipo_operacao} via convenios.id_integrador → worker.integradores.
    Cache em memória; falha de query → mantém cache anterior (ou {} no 1º ciclo)."""
    now = time.time()
    if _TIPO_OPERACAO_CACHE["map"] and now < _TIPO_OPERACAO_CACHE["expires"]:
        return _TIPO_OPERACAO_CACHE["map"]
    try:
        from models import Convenio, WorkerIntegrador
        convs = db.query(Convenio.id_convenio, Convenio.id_integrador).filter(
            Convenio.id_integrador.isnot(None)).all()
        ints = {i.id_integrador: i.tipo_operacao for i in db.query(WorkerIntegrador).all()}
        mapa = {c[0]: (ints.get(c[1]) or "convenio") for c in convs}
        _TIPO_OPERACAO_CACHE["map"] = mapa
        _TIPO_OPERACAO_CACHE["expires"] = now + _TIPO_OPERACAO_TTL
    except Exception as e:
        logger.warning(f"[tipo_operacao] falha ao recarregar mapeamento (usando cache/legado): {e}")
    return _TIPO_OPERACAO_CACHE["map"]


def _is_job_agendamento(db, job):
    """Job pertence a integrador tipo 'agendamento'? (fallback degradado: legado)."""
    mapa = _mapa_tipo_operacao(db)
    if not mapa:
        return job.id_convenio in (100, 101)
    return mapa.get(job.id_convenio) == "agendamento"


def _rotinas_ativas_por_integrador(db):
    """{id_integrador: set(rotinas ativas)} do catálogo worker.integrador_operacoes (TTL 5min)."""
    now = time.time()
    if _ROTINAS_ATIVAS_CACHE["map"] and now < _ROTINAS_ATIVAS_CACHE["expires"]:
        return _ROTINAS_ATIVAS_CACHE["map"]
    try:
        from models import WorkerIntegradorOperacao
        mapa = {}
        for op in db.query(WorkerIntegradorOperacao).filter(
                WorkerIntegradorOperacao.ativo == True).all():  # noqa: E712
            mapa.setdefault(op.id_integrador, set()).add(op.rotina)
        _ROTINAS_ATIVAS_CACHE["map"] = mapa
        _ROTINAS_ATIVAS_CACHE["expires"] = now + _TIPO_OPERACAO_TTL
    except Exception as e:
        logger.warning(f"[rotinas_ativas] falha ao recarregar catálogo (usando cache): {e}")
    return _ROTINAS_ATIVAS_CACHE["map"]


def _rotina_ativa_integrador(db, job):
    """Guarda de catálogo (camada 3): rotina registrada/ativa para o integrador do job.
    Sem catálogo carregado ou convênio sem integrador → não bloquear (degradado)."""
    rotinas = _rotinas_ativas_por_integrador(db)
    if not rotinas:
        return True
    from models import Convenio
    conv = db.query(Convenio.id_integrador).filter(
        Convenio.id_convenio == job.id_convenio).first()
    if not conv or not conv[0]:
        return True
    ativas = rotinas.get(conv[0])
    return bool(ativas) and job.rotina in ativas




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
        now = datetime.now(job.created_at.tzinfo) if job.created_at and job.created_at.tzinfo else datetime.now(timezone.utc)
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
        rules = db.query(PriorityRule).filter(PriorityRule.is_active == 1).all()
        rules_map = {(r.id_convenio, r.rotina): r for r in rules}
        # Also add fallback (convenio, None) entries
        for r in rules:
            if r.rotina is not None and (r.id_convenio, None) not in rules_map:
                rules_map[(r.id_convenio, None)] = r
        
        from sqlalchemy import or_
        from sqlalchemy.orm import aliased
        
        ParentJob = aliased(Job)
        
        pending_jobs = db.query(Job).options(
            # Egress: não transferir params/result_data no poll de ranking —
            # params é lazy-load por job apenas quando necessário (affinity/dispatch).
            defer(Job.params),
            defer(Job.result_data)
        ).outerjoin(
            ParentJob, Job.depending_id == ParentJob.id
        ).filter(
            Job.status == "pending",
            or_(
                Job.depending_id == None,
                ParentJob.status == 'success'
            )
        ).limit(limit).all()
        
        if not pending_jobs:
            return []
        
        # effective_priority ASC (0 first), then created_at ASC
        scored_jobs = [(calculate_effective_priority(j, rules_map), j.created_at or datetime.now(timezone.utc), j)
                       for j in pending_jobs]
        scored_jobs.sort(key=lambda x: (x[0], x[1]))
        return [j for _, _, j in scored_jobs]
    except Exception as e:
        logger.error(f"Error ranking pending jobs: {e}")
        return db.query(Job).filter(Job.status == "pending") \
                  .order_by(Job.priority.asc(), Job.created_at.asc()).limit(limit).all()


def get_job_login(db, job):
    if not job:
        return None
    import json as _json
    login = None
    if job.params:
        try:
            params_dict = job.params if isinstance(job.params, dict) else _json.loads(job.params)
            if isinstance(params_dict, dict):
                login = params_dict.get("login") or params_dict.get("users_convenio_login")
        except Exception:
            pass
    return login


# Keep for backward compatibility
def get_pending_job(db, allowed_convenio_ids=None):
    jobs = get_ranked_pending_jobs(db, limit=50)
    if allowed_convenio_ids:
        jobs = [j for j in jobs if j.id_convenio in allowed_convenio_ids]
    return jobs[0] if jobs else None


def retry_failed_jobs(db):
    try:
        from datetime import datetime, timedelta, timezone
        # Check for jobs with status='error' and attempts < 3.
        # We explicitly IGNORE locked_by here, because if they are in 'error', the lock is a ghost.
        # Add a 20s cooldown so rapid failures don't instantly loop the queue
        threshold = datetime.now(timezone.utc) - timedelta(seconds=20)
        from sqlalchemy import or_
        failed_jobs = db.query(Job).filter(
            Job.status == "error",
            or_(Job.attempts == None, Job.attempts < 3),
            Job.updated_at < threshold
        ).all()
        
        if failed_jobs:
            logger.info(f"Retrying {len(failed_jobs)} failed jobs...")
            for job in failed_jobs:
                if job.result_data:
                    res_data = job.result_data or {}
                    data_dict = res_data.get("data") if isinstance(res_data.get("data"), dict) else res_data
                    itens_erro = data_dict.get("itens_erro") if isinstance(data_dict, dict) else None
                    if itens_erro and isinstance(itens_erro, list):
                        try:
                            params_dict = dict(job.params or {})
                            params_dict["itens"] = [
                                {
                                    "detalheId": item.get("detalheId"),
                                    "status": item.get("status"),
                                    "dataRealizacao": item.get("dataRealizacao"),
                                    "valorProcedimento": item.get("valorProcedimento", "")
                                }
                                for item in itens_erro if isinstance(item, dict) and item.get("detalheId")
                            ]
                            job.params = params_dict
                            from sqlalchemy.orm.attributes import flag_modified
                            flag_modified(job, "params")
                        except Exception as prune_e:
                            logger.error(f"Erro ao podar params no retry_failed_jobs para job {job.id}: {prune_e}")

                job.status = "pending"
                job.locked_by = None
                job.attempts = job.attempts or 0
                job.updated_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as e:
        logger.error(f"Error retrying failed jobs: {e}")


def cleanup_expired_captures(db):
    """
    REMOVIDO: O worker não acessa o schema public (base_guias / convenios).
    A limpeza de capturas expiradas (timeout de 59min) é responsabilidade do
    Hub Backend, que recebe o timestamp_captura via webhook e gerencia a
    expiração em sua própria base de dados.
    """
    pass

def recover_stuck_jobs(db):
    try:
        from datetime import timedelta
        # If a job is 'processing' for more than 15 minutes, the Generic Worker thread 
        # or Chrome must have entirely died (e.g. OOM Kills, MaxClients crashes) without 
        # reaching the final block to unlock it.
        threshold = datetime.now(timezone.utc) - timedelta(minutes=15)
        stuck_jobs = db.query(Job).filter(
            Job.status == "processing",
            Job.updated_at < threshold
        ).all()
        
        if stuck_jobs:
            logger.info(f"Recovering {len(stuck_jobs)} jobs frozen in 'processing'...")
            for job in stuck_jobs:
                job.status = "error" if (job.attempts or 0) >= 3 else "pending"
                job.locked_by = None
                job.updated_at = datetime.now(timezone.utc)
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

def start_heartbeat_loop(status_map, interval=None, cmd_queue=None, active_workers=None):
    # Egress: heartbeat de 10s gerava ~2 SELECT+UPDATE no Supabas a cada batida por
    # frota. 30s default (env HEARTBEAT_INTERVAL) mantém liveness/comandos restart.
    if interval is None:
        interval = int(os.environ.get("HEARTBEAT_INTERVAL", "30"))
    def loop():
        while True:
            send_heartbeat(status_map, cmd_queue, active_workers)
            time.sleep(interval)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


def _parse_server_urls(server_urls_str):
    """
    Parse server URL configuration into a dict mapping url -> config dict.
    
    Supported formats:
      - Generic: "http://127.0.0.1:9000,http://127.0.0.1:9001"
      - Convenio specific: "http://127.0.0.1:9000:2"
      - Operacao type specific: "http://127.0.0.1:9005:agendamento"
    
    Returns: dict of {url: {"tipo_operacao": str|None, "convenio_ids": list|None}}
    """
    server_convenio_map = {}
    for entry in server_urls_str.split(","):
        entry = entry.strip()
        if not entry:
            continue
        colon_count = entry.count(":")
        if colon_count >= 3:
            url_part, last = entry.rsplit(":", 1)
            last_clean = last.lower()
            if last_clean in ("agendamento", "convenio"):
                server_convenio_map[url_part] = {"tipo_operacao": last_clean, "convenio_ids": None}
            elif last.isdigit():
                conv_id = int(last)
                if url_part not in server_convenio_map:
                    server_convenio_map[url_part] = {"tipo_operacao": None, "convenio_ids": []}
                if isinstance(server_convenio_map[url_part].get("convenio_ids"), list):
                    server_convenio_map[url_part]["convenio_ids"].append(conv_id)
            else:
                server_convenio_map[entry] = {"tipo_operacao": None, "convenio_ids": None}
        else:
            server_convenio_map[entry] = {"tipo_operacao": None, "convenio_ids": None}
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
    for url, cfg in server_convenio_map.items():
        tipo_op = cfg.get("tipo_operacao")
        convs = cfg.get("convenio_ids")
        desc = f"tipo_operacao: {tipo_op}" if tipo_op else f"convenios: {convs if convs else 'ALL GENERIC'}"
        logger.info(f"  {url} -> {desc}")

    server_status_map = {
        url: {
            "status": "idle", 
            "last_job": None, 
            "convenio_ids": server_convenio_map[url].get("convenio_ids"),
            "tipo_operacao": server_convenio_map[url].get("tipo_operacao"),
            "last_convenio_id": None,
            "last_user_id": None,
            "last_login": None
        } for url in servers
    }
    dispatch_stagger_val = stagger

    # Start Heartbeat Thread
    start_heartbeat_loop(server_status_map, cmd_queue=cmd_queue, active_workers=active_workers)


    def call_server(url, job_id, carteirinha, carteirinha_id, id_convenio, rotina, params, status_map, user_id=None):
        db = SessionLocal()
        import json as _json
        try:
            params_dict = params if isinstance(params, dict) else (_json.loads(params) if params else {})
            
            params_str = _json.dumps(params_dict)

            # Skip base_guias sync/save for Bradesco OP1 Fature
            is_bradesco_fature = False
            if id_convenio == 1 and params_dict.get("contexto") == "fature":
                is_bradesco_fature = True

            payload = {
                "job_id": job_id,
                "id_convenio": id_convenio,
                "rotina": rotina,
                "params": params_str,
                "carteirinha_id": carteirinha_id,
                "carteirinha": carteirinha,
                "paciente": "",
                "user_id": user_id
            }
            # Log attempt
            db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="INFO", message=f"Dispatching to {url}"))
            db.commit()

            # Close DB connection to free Supabase pool during long HTTP wait (up to 300s)
            db.close()
            
            try:
                resp = requests.post(f"{url}/process_job", json=payload, timeout=600)
            finally:
                # Re-acquire connection to process results or errors
                db = SessionLocal()
            
            try:
                data = resp.json()
            except ValueError: 
                err_msg = f"Invalid JSON ({resp.status_code}): {resp.text[:200]}"
                db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="ERROR", message=f"Worker Protocol Error: {err_msg}"))
                db.commit()
                raise Exception(err_msg)

            current_job = db.query(Job).filter(Job.id == job_id).first()
            if not current_job: return

            if resp.status_code == 409:
                # Worker is strictly busy. Dispatcher overlapped requests (Race Condition)
                current_job.status = "pending"
                current_job.locked_by = None
                current_job.attempts = max(0, (current_job.attempts or 0) - 1) # Refund the attempt
                db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="WARN", message="Worker Port returned 409 Busy -> Retornando Job para fila Pending."))
                current_job.updated_at = datetime.now(timezone.utc)
                db.commit()
                return

            if data.get("status") == "success":
                current_job.status = "success"
                current_job.locked_by = None
                current_job.result_data = data
                current_job.updated_at = datetime.now(timezone.utc)
                results = data.get("data", [])
                
                # Normaliza results se for dict
                if isinstance(results, dict):
                    if "op11_data" in results and isinstance(results["op11_data"], list):
                        results = results["op11_data"]
                    elif "data" in results and isinstance(results["data"], list):
                        results = results["data"]
                    else:
                        results = [results]
                
                # ── Log the full JSON response from the worker ──
                try:
                    result_json_str = _json.dumps(data, ensure_ascii=False, default=str)[:2000]
                    db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="INFO",
                              message=f"Worker JSON Response: {result_json_str}"))
                    db.commit()
                except Exception:
                    pass
                
                try:
                    # Check if the worker already persisted data internally (OP6, OP7, etc.)
                    worker_meta = data.get("meta", {})
                    if worker_meta.get("self_persisted"):
                        ins = worker_meta.get("inserted", 0)
                        upd = worker_meta.get("updated", 0)
                        tot = worker_meta.get("total", 0)
                        msg = f"Sync complete (Worker). Inserted: {ins}, Updated: {upd}, Total extraídos: {tot}"
                        db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="INFO", message=msg))
                        db.commit()
                    elif not results:
                        # No results and no self_persisted flag — just log empty sync
                        db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="INFO", message="Sync complete. Inserted: 0, Updated: 0 (Worker retornou vazio)"))
                        db.commit()
                    elif is_bradesco_fature:
                        db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="INFO", message="Sync completo. Resultados retornados no payload (gravação em base_guias ignorada para faturamento Bradesco)."))
                        db.commit()
                    elif id_convenio == 100:
                        db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="INFO", message="Sync completo. Resultados da Evoluir salvos no result_data do Job (sincronização efetuada em background pelo backend)."))
                        db.commit()
                    else:
                        # Em vez de fazer o parse e gravação no base_guias localmente no worker,
                        # delegamos a gravação ao backend enviando o resultado via webhook HTTP POST.
                        db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="INFO",
                                   message=f"Job concluído com sucesso. Enviando dados via webhook ao backend para processamento..."))
                        db.commit()
                        
                        try:
                            base_api = str(BACKEND_API_URL).rstrip('/')
                            if base_api.endswith('/api'):
                                base_api = base_api[:-4]
                            webhook_url = f"{base_api}/api/jobs/{job_id}/result"
                            logger.info(f"Sending webhook to {webhook_url}")
                            webhook_resp = requests.post(webhook_url, json=data, timeout=30)
                            if webhook_resp.status_code == 200:
                                db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="INFO",
                                           message=f"Webhook enviado e processado pelo backend com sucesso."))
                            else:
                                db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="WARN",
                                           message=f"Backend retornou status {webhook_resp.status_code} no webhook. O processamento ocorrerá via sync service em background."))
                            db.commit()
                        except Exception as webhook_err:
                            logger.error(f"Erro ao enviar webhook ao backend: {webhook_err}")
                            db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="WARN",
                                       message=f"Falha de conexão ao enviar webhook ao backend: {str(webhook_err)}. O processamento ocorrerá via sync service em background."))
                            db.commit()
                        db.commit()
                except Exception as save_e:
                    logger.error(f"Error saving results: {save_e}")
                    db.rollback()
                    db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="ERROR", message=f"Error saving results: {save_e}"))
                    db.commit()
                    current_job.status = "error"
            else:
                current_job.status = "error"
                current_job.locked_by = None
                current_job.updated_at = datetime.now(timezone.utc)
                err_msg = data.get("message") or data.get("detail") or "Unknown error from server"
                
                # Se o resultado contiver itens_erro, atualiza job.params["itens"] para apenas os que falharam
                res_payload = data.get("data") if isinstance(data.get("data"), dict) else data
                itens_erro = res_payload.get("itens_erro") if isinstance(res_payload, dict) else None
                if itens_erro and isinstance(itens_erro, list):
                    try:
                        params_dict = dict(current_job.params or {})
                        params_dict["itens"] = [
                            {
                                "detalheId": item.get("detalheId"),
                                "status": item.get("status"),
                                "dataRealizacao": item.get("dataRealizacao"),
                                "valorProcedimento": item.get("valorProcedimento", "")
                            }
                            for item in itens_erro if isinstance(item, dict) and item.get("detalheId")
                        ]
                        current_job.params = params_dict
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(current_job, "params")
                        logger.info(f"Job {job_id} params podados para conter apenas {len(params_dict['itens'])} itens com erro.")
                    except Exception as prune_e:
                        logger.error(f"Erro ao podar params do job {job_id}: {prune_e}")

                # Regra de Negócio PO: Interromper Retentativas para erros Fatais (Carteira Inválida)
                if "carteira inv" in err_msg.lower() or "dígito" in err_msg.lower() or "invalida" in err_msg.lower():
                    current_job.attempts = max(3, current_job.attempts or 0)
                
                # Log the full JSON response for debugging
                try:
                    err_json_str = _json.dumps(data, ensure_ascii=False, default=str)[:2000]
                    db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="ERROR",
                              message=f"Worker JSON Response (Error): {err_json_str}"))
                except Exception:
                    pass
                    
                db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="ERROR", message=f"Worker Error: {err_msg}"))
            
            db.commit()
            
        except requests.exceptions.ConnectionError:
            # Expected if the worker slot is physically offline right now
            try:
                current_job = db.query(Job).filter(Job.id == job_id).first()
                if current_job:
                    current_job.status = "error"
                    current_job.locked_by = None
                    current_job.updated_at = datetime.now(timezone.utc)
                    db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="ERROR", message="Worker is Offline (Connection Refused)."))
                    db.commit()
            except: pass
        except Exception as e:
            logger.error(f"Error calling server {url}: {e}")
            try:
                current_job = db.query(Job).filter(Job.id == job_id).first()
                if current_job:
                    current_job.status = "error"
                    current_job.locked_by = None
                    current_job.updated_at = datetime.now(timezone.utc)
                    db.add(Log(job_id=job_id, carteirinha_id=carteirinha_id, user_id=user_id, level="ERROR", message=f"Dispatcher Failed: {str(e)}"))
                    db.commit()
            except: pass
        finally:
            db.close()
            status_map[url]["status"] = "idle"

    while True:
        db = SessionLocal()
        try:
            # 0. Retry failed jobs, sweep dead processing jobs & expired captures
            retry_failed_jobs(db)
            recover_stuck_jobs(db)
            cleanup_expired_captures(db)

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
                ranked_jobs = get_ranked_pending_jobs(db, limit=300)
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
                    """Pick the best idle server for this job using priority rules and operation type isolation."""
                    is_agendamento_job = _is_job_agendamento(db, job)
                    
                    # Filter idle servers strictly by tipo_operacao
                    candidate_servers = []
                    for s in idle_servers:
                        cfg_info = server_convenio_map.get(s, {})
                        srv_tipo = cfg_info.get("tipo_operacao") if isinstance(cfg_info, dict) else None
                        if is_agendamento_job:
                            if srv_tipo == "agendamento":
                                candidate_servers.append(s)
                        else:
                            if srv_tipo != "agendamento":
                                candidate_servers.append(s)
                                
                    if not candidate_servers:
                        return None

                    idle_servers = candidate_servers
                    job_login = get_job_login(db, job)
                    
                    # Determine if strict session affinity should be enforced
                    enforce_affinity = False
                    if job.id_convenio == 1 and job.user_id:
                        import json as _json
                        try:
                            params_dict = job.params if isinstance(job.params, dict) else _json.loads(job.params)
                            if isinstance(params_dict, dict):
                                # Check if parameter is explicitly defined
                                if "strict_session_affinity" in params_dict:
                                    enforce_affinity = bool(params_dict["strict_session_affinity"])
                                elif "strict_session" in params_dict:
                                    enforce_affinity = bool(params_dict["strict_session"])
                                elif "strict_affinity" in params_dict:
                                    enforce_affinity = bool(params_dict["strict_affinity"])
                                else:
                                    # Default to True for Bradesco OP1 (rotina == "1" or "op1...")
                                    rotina_str = str(job.rotina).lower()
                                    if rotina_str == "1" or rotina_str.startswith("op1"):
                                        enforce_affinity = True
                        except Exception:
                            pass
                            
                    # Strict Affinity: force job to run on the server that currently has the user's login session
                    if enforce_affinity:
                        for s_url, s_meta in server_status_map.items():
                            match_user = s_meta.get("last_user_id") == job.user_id
                            match_login = (job_login and s_meta.get("last_login") == job_login)
                            if s_meta.get("last_convenio_id") == 1 and (match_user or match_login):
                                if s_url in idle_servers:
                                    return s_url
                                else:
                                    # Server is busy, must wait to avoid simultaneous logins!
                                    return None

                    # If not enforcing strict affinity, or no active session exists yet for this user/login,
                    # search for the best available idle server.
                    # 1. Prefer idle server with matching login session (if convenio matches)
                    if job.id_convenio == 1 and job_login:
                        for s in idle_servers:
                            s_meta = server_status_map[s]
                            if s_meta.get("last_convenio_id") == 1 and s_meta.get("last_login") == job_login:
                                return s
                    elif job_login:
                        # Para outros convênios, preferir worker com o mesmo convênio, mesmo login e mesmo user_id (para evitar misturar sessões)
                        for s in idle_servers:
                            s_meta = server_status_map[s]
                            if (s_meta.get("last_convenio_id") == job.id_convenio and 
                                s_meta.get("last_login") == job_login and 
                                s_meta.get("last_user_id") == job.user_id):
                                return s

                    # 2. Prefer idle server with NO active session for this convenio (clean slate)
                    for s in idle_servers:
                        s_meta = server_status_map[s]
                        if s_meta.get("last_convenio_id") != job.id_convenio or not s_meta.get("last_login"):
                            bindings = server_convenio_map.get(s)
                            if bindings is None or job.id_convenio in bindings:
                                return s

                    last_conv_match = []
                    for s in idle_servers:
                        # For Bradesco, prefer an idle server that has NO user session, or matches user
                        if server_status_map[s].get("last_convenio_id") == job.id_convenio:
                            if job.id_convenio == 1:
                                # For Bradesco, we can reuse any server (scraper will clear cookies if login changes)
                                pass
                            elif job.user_id and server_status_map[s].get("last_user_id") != job.user_id:
                                continue # Don't hijack another user's session for other convenios
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
                    if server_url is None:
                        logger.info(f"Skipping job {job.id}: Strict session affinity enforced (Server Busy)")
                        continue

                    # ── Guarda de catálogo (camada 3): integradores tipo agendamento
                    #    só despacham rotinas ativas no catálogo worker (fail-fast,
                    #    sem consumir servidor Selenium com job inválido) ──
                    if _is_job_agendamento(db, job) and not _rotina_ativa_integrador(db, job):
                        job.status = "error"
                        job.error_message = (
                            f"Rotina '{job.rotina}' não registrada/ativa no catálogo do integrador "
                            f"(convênio {job.id_convenio})."
                        )
                        db.add(Log(
                            job_id=job.id,
                            user_id=job.user_id,
                            carteirinha_id=job.carteirinha_id,
                            level="ERROR",
                            message=job.error_message
                        ))
                        db.commit()
                        logger.error(f"Job {job.id} rejeitado pela guarda de catálogo: {job.error_message}")
                        continue
                    
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
                        locked_job.attempts = (locked_job.attempts or 0) + 1
                        locked_job.updated_at = datetime.now(locked_job.created_at.tzinfo) if (locked_job.created_at and locked_job.created_at.tzinfo) else datetime.now(timezone.utc)
                        db.commit()

                        print(f"Assigning Job {locked_job.id} (conv={locked_job.id_convenio}) "
                              f"to {server_url} {'(session match)' if session_match else ''}")
                    except Exception as e:
                        logger.error(f"Error locking/assigning job {job.id}: {e}")
                        db.rollback()
                        continue
                    
                    server_status_map[server_url]["status"] = "busy"
                    server_status_map[server_url]["last_convenio_id"] = locked_job.id_convenio
                    server_status_map[server_url]["last_user_id"] = locked_job.user_id
                    server_status_map[server_url]["last_login"] = get_job_login(db, locked_job)
                    dispatched_servers.add(server_url)
                    
                    # Extrai o número da carteirinha de params (worker é 100% stateless)
                    params_dict = locked_job.params or {}
                    if isinstance(params_dict, str):
                        try:
                            import json as _json
                            params_dict = _json.loads(params_dict)
                        except:
                            params_dict = {}
                    _carteirinha_str = (
                        params_dict.get("carteirinha") or 
                        params_dict.get("Carteirinha") or 
                        params_dict.get("carteira") or 
                        params_dict.get("Carteira") or 
                        params_dict.get("codigo_beneficiario") or
                        ""
                    )
                    t = threading.Thread(
                        target=call_server,
                        args=(server_url, locked_job.id, _carteirinha_str,
                              locked_job.carteirinha_id, locked_job.id_convenio,
                              locked_job.rotina, locked_job.params, server_status_map, locked_job.user_id)
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
