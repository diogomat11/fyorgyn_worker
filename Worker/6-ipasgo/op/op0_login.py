from __future__ import annotations
import time
from typing import TYPE_CHECKING
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import sys

# ── Isolate Environment (Fix Crosstalk) ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)]
if sys.path[0] != _mod_root:
    sys.path.insert(0, _mod_root)

from config.constants import (
    X_LOGIN_USERNAME,
    X_LOGIN_PASSWORD,
    X_LOGIN_BUTTON,
    X_LOGIN_ERROR_MESSAGE,
    DEFAULT_TIMEOUT,
    X_ALERT_CLOSE,
)

if TYPE_CHECKING:
    from base_scraper import BaseScraper


def _find_any_xpath(wait, candidates):
    last_err = None
    for xp in candidates:
        try:
            return wait.until(EC.presence_of_element_located((By.XPATH, xp)))
        except Exception as e:
            last_err = e
    raise last_err or Exception("nenhum xpath encontrado")


def run(scraper: BaseScraper, job_data: dict) -> list[dict]:
    """
    Executa o login no portal IPASGO.
    Usa o scraper._get_credential() para pegar login e senha do banco.
    """
    job_id = job_data.get("job_id")
    usuario = getattr(scraper, "username", None)
    senha = getattr(scraper, "password", None)

    if not usuario or not senha:
        scraper.log("Credenciais IPASGO não encontradas / não configuradas para este conveniado", level="ERROR", job_id=job_id)
        raise ValueError("PermanentError: Credenciais IPASGO ausentes")

    driver = scraper.driver
    
    scraper.log("Limpando abas residuais. Mantendo apenas aba Portal primária...", job_id=job_id)
    try:
        main_h = driver.window_handles[0]
        for h in driver.window_handles[1:]:
             driver.switch_to.window(h)
             driver.close()
        driver.switch_to.window(main_h)
    except Exception as e:
        scraper.log(f"Aviso ao limpar abas: {e}", level="WARN", job_id=job_id)

    # URL inicial do IPASGO listada na configuração (ou fallback hardcoded)
    portal_url = "https://portalos.ipasgo.go.gov.br/Portal_Dominio/Common.PrestadorLogin.aspx" 
    try:
        from config.settings import PORTAL_URL
        if PORTAL_URL:
            portal_url = PORTAL_URL
    except ImportError:
        pass
    
    driver.get(portal_url)
    scraper.log(f"Acessando portal IPASGO: {portal_url}", job_id=job_id)
    
    wait = WebDriverWait(driver, DEFAULT_TIMEOUT)
    
    def find_with_frames(candidates):
        try:
            return _find_any_xpath(wait, candidates)
        except Exception:
            pass
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for i, f in enumerate(frames):
            try:
                driver.switch_to.frame(i)
                try:
                    el = _find_any_xpath(wait, candidates)
                    return el
                except Exception:
                    for xp in candidates:
                        elems = driver.find_elements(By.XPATH, xp)
                        for el in elems:
                            if el.is_displayed() and el.is_enabled():
                                return el
            except Exception:
                driver.switch_to.default_content()
                continue
        driver.switch_to.default_content()
        try:
            return _find_any_xpath(wait, candidates)
        except Exception:
            for xp in candidates:
                elems = driver.find_elements(By.XPATH, xp)
                for el in elems:
                    if el.is_displayed() and el.is_enabled():
                        return el
            raise

    # 1. Preencher Credenciais
    try:
        user_el = find_with_frames([
            X_LOGIN_USERNAME,
            "//input[@type='text' and contains(@name,'user')]",
            "//input[contains(@id,'user') or contains(@name,'user') or contains(@placeholder,'usuário') or contains(@placeholder,'usuario')]",
        ])
        pass_el = find_with_frames([
            X_LOGIN_PASSWORD,
            "//input[@type='password']",
            "//input[contains(@id,'pass') or contains(@name,'pass') or contains(@placeholder,'senha')]",
        ])
        btn_el = find_with_frames([
            X_LOGIN_BUTTON,
            "//button[@type='submit']",
            "//input[@type='submit']",
            "//button[contains(.,'Entrar') or contains(.,'Login')]",
        ])
        
        user_el.clear()
        pass_el.clear()
        user_el.send_keys(usuario)
        pass_el.send_keys(senha)
        btn_el.click()
        
        try:
            wait.until_not(EC.presence_of_element_located((By.XPATH, X_LOGIN_ERROR_MESSAGE)))
        except Exception:
            pass
            
        scraper.log("Login submetido com sucesso no portal IPASGO", job_id=job_id)
        
    except Exception as e:
        scraper.log(f"Falha ao encontrar/preencher formulário de login (provavelmente xpath out of sync): {str(e)}", level="ERROR", job_id=job_id)
        raise e

    # Fechar possíveis alertas/modais iniciais
    try:
        short = WebDriverWait(driver, 5)
        candidates_close = [
            X_ALERT_CLOSE,
            "//button[contains(@class,'close')]",
            "//span[contains(@class,'fa-times')]",
            "//a[contains(@class,'close')]",
            "//*[@aria-label='Fechar']",
        ]
        el = _find_any_xpath(short, candidates_close)
        try:
            el.click()
        except Exception:
            driver.execute_script("arguments[0].click();", el)
        scraper.log("Alerta/modal fechado na home", job_id=job_id)
    except Exception:
        pass

    # Acesso opcional ao FACPLAN caso disponível no Dashboard
    try:
        link = find_with_frames([
            "/html/body/form/div[3]/div/div[2]/div/div[2]/div/div/span/div[5]/div/div[2]/div[2]/div/div/div[2]/table/tbody/tr[2]/td/div/a",
            "//a[contains(.,'Fac') and contains(.,'Plan')]",
            "//a[contains(@href,'Portal_FAC') or contains(@href,'facplan')]",
        ])
        
        driver.execute_script("arguments[0].scrollIntoView(true);", link)
        time.sleep(1)
        
        try:
            link.click()
        except Exception:
            driver.execute_script("arguments[0].click();", link)
            
        time.sleep(2)
        try:
            driver.switch_to.window(driver.window_handles[-1])
        except Exception:
            pass
        scraper.log("Facplan aberto e aba focada no IPASGO", job_id=job_id)
        
    except Exception:
        scraper.log("Página do Facplan não processada automaticamente no login (Acesso será feito nas rotinas subsequentes)", level="WARN", job_id=job_id)
        pass

    return []
