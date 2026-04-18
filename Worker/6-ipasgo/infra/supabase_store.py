import os
import json
import requests

def _env():
    return {
        "url": os.getenv("SUPABASE_URL", "").rstrip("/"),
        "key": os.getenv("SUPABASE_SERVICE_KEY", ""),
        "schema": os.getenv("SUPABASE_SCHEMA", "public"),
    }

def save_rows(rows, logger):
    env = _env()
    if not env["url"] or not env["key"]:
        logger.warning("supabase não configurado no .env (SUPABASE_URL/SUPABASE_SERVICE_KEY)")
        return
    endpoint = f"{env['url']}/rest/v1/base_guias?on_conflict=numero_guia"
    headers = {
        "apikey": env["key"],
        "Authorization": f"Bearer {env['key']}",
        "Content-Type": "application/json",
        "Accept-Profile": env["schema"],
        "Content-Profile": env["schema"],
        "Prefer": "return=representation,resolution=merge-duplicates",
    }
    try:
        if not rows:
            return
        r = requests.post(endpoint, headers=headers, json=rows, timeout=15)
        if r.status_code >= 300:
            logger.error(f"falha ao salvar no supabase: {r.status_code} {r.text}")
        else:
            logger.info(f"salvos {len(rows)} registros em base_guias")
    except Exception as e:
        logger.error(f"erro de integração supabase: {e}")

def log_import_page(info, logger):
    env = _env()
    if not env["url"] or not env["key"]:
        return
    endpoint = f"{env['url']}/rest/v1/import_guias_log"
    headers = {
        "apikey": env["key"],
        "Authorization": f"Bearer {env['key']}",
        "Content-Type": "application/json",
        "Accept-Profile": env["schema"],
        "Content-Profile": env["schema"],
        "Prefer": "return=minimal",
    }
    try:
        r = requests.post(endpoint, headers=headers, data=json.dumps(info), timeout=20)
        if r.status_code >= 300:
            logger.warning(f"falha ao registrar log: {r.status_code} {r.text}")
    except Exception as e:
        logger.warning(f"erro ao registrar log: {e}")

def get_last_log(op, data_inicio, data_fim, logger):
    env = _env()
    if not env["url"] or not env["key"]:
        return None
    endpoint = f"{env['url']}/rest/v1/import_guias_log"
    headers = {
        "apikey": env["key"],
        "Authorization": f"Bearer {env['key']}",
        "Accept-Profile": env["schema"],
    }
    params = {
        "op": f"eq.{op}",
        "data_inicio": f"eq.{data_inicio}" if data_inicio else None,
        "data_fim": f"eq.{data_fim}" if data_fim else None,
        "select": "pagina,created_at",
        "order": "pagina.desc",
        "limit": "1",
    }
    # remove None values
    params = {k: v for k, v in params.items() if v is not None}
    try:
        r = requests.get(endpoint, headers=headers, params=params, timeout=15)
        if r.status_code >= 300:
            logger.warning(f"falha ao consultar log: {r.status_code} {r.text}")
            return None
        data = r.json() if r.text else []
        if data:
            item = data[0]
            return {
                "pagina": int(item.get("pagina") or 0),
                "created_at": item.get("created_at"),
            }
        return None
    except Exception as e:
        logger.warning(f"erro ao consultar log: {e}")
        return None

def clear_log(op, data_inicio, data_fim, logger):
    env = _env()
    if not env["url"] or not env["key"]:
        return False
    endpoint = f"{env['url']}/rest/v1/import_guias_log"
    headers = {
        "apikey": env["key"],
        "Authorization": f"Bearer {env['key']}",
        "Accept-Profile": env["schema"],
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    params = {
        "op": f"eq.{op}",
        "data_inicio": f"eq.{data_inicio}" if data_inicio else None,
        "data_fim": f"eq.{data_fim}" if data_fim else None,
    }
    params = {k: v for k, v in params.items() if v is not None}
    try:
        r = requests.delete(endpoint, headers=headers, params=params, timeout=20)
        return r.status_code < 300
    except Exception:
        return False
