"""OP0 — Login no portal ABA CLMF (modelo NOVO — ref. clmf_hub_basic 2026-11-21).

O fluxo real mora no core/scraper.py (`AbaClmfScraper.login`): HTTP puro, sem
login visual Selenium (aposentado pelo portal):
  1. POST api/auth/login no painel (app.) → token Bearer;
  2. POST api/sso/emitir → token SSO de uso único + url do antigo;
  3. POST do token na url → sistema antigo cria a sessão (PHPSESSID).
Cookies do domínio antigo alimentam `scraper.session` (OPs HTTP) e são
injetados no driver via CDP (OPs que navegam).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run(scraper, job_data):
    job_id = job_data.get("job_id")

    scraper.log("Iniciando login no portal ABA_clmf (API + SSO)...", job_id=job_id)

    if not scraper.username or not scraper.password:
        raise ValueError("Credenciais da ABA_clmf não carregadas!")

    if scraper.login():
        return {
            "status": "success",
            "message": "Logado no portal ABA_clmf (API do painel + SSO) — sessão HTTP pronta.",
            "cookies": sorted(scraper.session_cookies.keys()),
        }

    raise Exception(
        "LOGIN_REJEITADO: falha no login ABA_clmf — credenciais recusadas (401), "
        "destino SSO fora do menu (422) ou erro de rede. Ver CLMF_SSO_DESTINO."
    )


execute = run
