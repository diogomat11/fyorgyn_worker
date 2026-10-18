from __future__ import annotations

import os
import sys
import time
from typing import TYPE_CHECKING

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Isolate Environment (Fix Crosstalk) ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)]
if sys.path[0] != _mod_root:
    sys.path.insert(0, _mod_root)

from config.constants import (
    X_LOGIN_BOTAO_ACESSAR,
    X_LOGIN_BOTAO_FALLBACKS,
    X_LOGIN_SENHA,
    X_LOGIN_SENHA_FALLBACKS,
    X_LOGIN_USUARIO,
    X_LOGIN_USUARIO_FALLBACKS,
    DEFAULT_TIMEOUT,
    SHORT_TIMEOUT,
)
from config import settings

if TYPE_CHECKING:
    from base_scraper import BaseScraper


def _find_any(wait, candidates, driver=None):
    """Localiza o primeiro xpath válido dentre candidatos (com fallback de visibilidade)."""
    last_err = None
    for xp in candidates:
        try:
            return wait.until(EC.presence_of_element_located((By.XPATH, xp)))
        except Exception as e:
            last_err = e
    if driver is not None:
        for xp in candidates:
            try:
                for el in driver.find_elements(By.XPATH, xp):
                    if el.is_displayed() and el.is_enabled():
                        return el
            except Exception:
                continue
    raise last_err or Exception("nenhum xpath encontrado")


def run(scraper: BaseScraper, job_data: dict) -> dict:
    """
    OP0 — Login no portal do prestador CAESAN.
    Extrai sessão/cookies/token após o login (metadados ficam no scraper;
    valores sensíveis não vão para result_data/logs — MODULARITY_GUIDE §4).
    """
    job_id = job_data.get("job_id")
    usuario = getattr(scraper, "username", None)
    senha = getattr(scraper, "password", None)

    if not usuario or not senha:
        scraper.log("Credenciais CAESAN não encontradas / não configuradas para este tenant", level="ERROR", job_id=job_id)
        raise ValueError("PermanentError: Credenciais CAESAN ausentes")

    driver = scraper.driver

    portal_url = settings.PORTAL_URL
    driver.get(portal_url)
    scraper.log(f"Acessando portal CAESAN: {portal_url}", job_id=job_id)

    wait = WebDriverWait(driver, DEFAULT_TIMEOUT)

    # 1. Aguardar carregamento e mapear campos de login
    user_el = _find_any(wait, [X_LOGIN_USUARIO] + X_LOGIN_USUARIO_FALLBACKS, driver)
    pass_el = _find_any(wait, [X_LOGIN_SENHA] + X_LOGIN_SENHA_FALLBACKS, driver)
    btn_el = _find_any(wait, [X_LOGIN_BOTAO_ACESSAR] + X_LOGIN_BOTAO_FALLBACKS, driver)

    # 2. Limpar, preencher credenciais e submeter
    try:
        user_el.clear()
        pass_el.clear()
        user_el.send_keys(usuario)
        pass_el.send_keys(senha)
        try:
            btn_el.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn_el)
        scraper.log("Login submetido no portal CAESAN", job_id=job_id)
    except Exception as e:
        scraper.log(f"Falha ao preencher formulário de login (xpath out of sync?): {e}", level="ERROR", job_id=job_id)
        raise

    # 3. Aguardar redirecionamento pós-login (sai da tela de login)
    time.sleep(2)
    try:
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            lambda d: "login" not in (d.current_url or "").lower()
        )
    except Exception:
        # Ainda na tela de login → credencial inválida ou captcha
        scraper.log(
            "Login não efetivou (continua na tela de login) — verifique credenciais CAESAN",
            level="ERROR", job_id=job_id
        )
        raise ValueError("PermanentError: Login CAESAN recusado (usuário/senha inválidos ou página alterada)")

    # 4. Extrair sessão/cookies/token (metadados apenas; nada sensível em logs)
    try:
        cookies = driver.get_cookies()
        token_names = [c["name"] for c in cookies if "token" in c["name"].lower()]
        scraper.session_meta = {
            "url": driver.current_url,
            "cookies": [c["name"] for c in cookies],
            "tokens": token_names,
            "extracted_at": time.time(),
        }
        scraper.log(
            f"Sessão extraída: url={driver.current_url} | {len(cookies)} cookies | tokens={token_names or '—'}",
            job_id=job_id
        )
    except Exception as e:
        scraper.log(f"Aviso ao extrair sessão/cookies: {e}", level="WARN", job_id=job_id)

    # 5. Fechar alertas/modais residuais
    try:
        short = WebDriverWait(driver, SHORT_TIMEOUT)
        el = _find_any(short, [
            '//button[contains(@class,"close")]',
            '//*[@aria-label="Fechar" or @data-dismiss="modal"]',
        ], driver)
        try:
            el.click()
        except Exception:
            driver.execute_script("arguments[0].click();", el)
    except Exception:
        pass

    return {
        "status": "success",
        "message": "Login CAESAN efetuado e sessão extraída",
        "url_final": scraper.session_meta.get("url") if scraper.session_meta else None,
        "cookies_count": len(scraper.session_meta.get("cookies", [])) if scraper.session_meta else 0,
    }
