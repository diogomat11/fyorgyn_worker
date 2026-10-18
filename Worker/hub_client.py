"""
hub_client — POST ao Hub Backend com cadeia de fallback produção → local.

Mesma semântica do dispatcher.post_hub (BACKEND_API_URL → BACKEND_API_URL_FALLBACK),
reutilizada pelo scraper OP4 para entrega parcial (chunks) direto do worker,
sem depender do dispatcher como único caminho de entrega de resultados.
"""
import os
import logging

import requests

logger = logging.getLogger(__name__)


def hub_bases(extra_from_params=None):
    """Bases do hub SEM o sufixo /api, em ordem de preferência.

    extra_from_params: URL de webhook vinda do params do job
    (ex.: http://host:8000/api/jobs/webhook) — usada como último recurso.
    """
    bases = []
    for var, default in (("BACKEND_API_URL", "http://localhost:8000"),
                         ("BACKEND_API_URL_FALLBACK", "http://127.0.0.1:8000")):
        b = os.environ.get(var, default).rstrip('/')
        if b.endswith('/api'):
            b = b[:-4]
        if b and b not in bases:
            bases.append(b)
    if extra_from_params:
        b = str(extra_from_params).rstrip('/')
        for suffix in ("/api/jobs/webhook", "/jobs/webhook"):
            if b.endswith(suffix):
                b = b[: -len(suffix)]
                break
        if b.endswith('/api'):
            b = b[:-4]
        if b and b not in bases:
            bases.append(b)
    return bases


def post_hub(path, json=None, timeout=30, extra_base=None):
    """POST {path} (COM prefixo /api) no hub, com fallback.

    Retorna (resp, base_usada); resp=None quando todos os destinos falharam.
    Respostas 4xx são válidas (não caem para o fallback); 5xx e erros de
    conexão acionam o próximo destino.
    """
    ultimo = None
    for base in hub_bases(extra_base):
        try:
            r = requests.post(f"{base}{path}", json=json, timeout=timeout)
            if r.status_code < 500:
                return r, base
            ultimo = f"HTTP {r.status_code}"
            logger.warning(f"[hub-fallback] {base}{path} -> HTTP {r.status_code}")
        except Exception as e:
            ultimo = e.__class__.__name__
            logger.warning(f"[hub-fallback] {base}{path} inacessível: {ultimo}")
    return None, None
