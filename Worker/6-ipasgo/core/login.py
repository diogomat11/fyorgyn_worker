from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.settings import PORTAL_URL, USUARIO, SENHA
from config.constants import (
    X_LOGIN_USERNAME,
    X_LOGIN_PASSWORD,
    X_LOGIN_BUTTON,
    X_LOGIN_ERROR_MESSAGE,
    DEFAULT_TIMEOUT,
    X_ALERT_CLOSE,
    X_FACPLAN_LINK,
    X_FACPLAN_LINK_ABS,
)

def _find_any_xpath(wait, candidates):
    last_err = None
    for xp in candidates:
        try:
            return wait.until(EC.presence_of_element_located((By.XPATH, xp)))
        except Exception as e:
            last_err = e
    raise last_err or Exception("nenhum xpath encontrado")

def perform_login(driver, logger):
    if not USUARIO or not SENHA:
        logger.error("USUARIO ou SENHA não configurados (.env)")
        return
    driver.get(PORTAL_URL)
    wait = WebDriverWait(driver, DEFAULT_TIMEOUT)
    try:
        driver.save_screenshot("logs/login.png")
        with open("logs/login_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    except Exception:
        pass
    def find_with_frames(candidates):
        try:
            return _find_any_xpath(wait, candidates)
        except Exception:
            pass
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for i, f in enumerate(frames):
            try:
                driver.switch_to.frame(i)
                # tentativa por espera
                try:
                    el = _find_any_xpath(wait, candidates)
                    return el
                except Exception:
                    # tentativa por varredura de elementos visíveis
                    for xp in candidates:
                        elems = driver.find_elements(By.XPATH, xp)
                        for el in elems:
                            if el.is_displayed() and el.is_enabled():
                                return el
                
            except Exception:
                driver.switch_to.default_content()
                continue
        driver.switch_to.default_content()
        # última tentativa sem frames
        try:
            return _find_any_xpath(wait, candidates)
        except Exception:
            for xp in candidates:
                elems = driver.find_elements(By.XPATH, xp)
                for el in elems:
                    if el.is_displayed() and el.is_enabled():
                        return el
            raise

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
    user_el.send_keys(USUARIO)
    pass_el.send_keys(SENHA)
    btn_el.click()
    try:
        wait.until_not(EC.presence_of_element_located((By.XPATH, X_LOGIN_ERROR_MESSAGE)))
    except Exception:
        pass
    logger.info("login executado")
    try:
        short = WebDriverWait(driver, 5)
        candidates = [
            X_ALERT_CLOSE,
            "//button[contains(@class,'close')]",
            "//span[contains(@class,'fa-times')]",
            "//a[contains(@class,'close')]",
            "//*[@aria-label='Fechar']",
        ]
        el = _find_any_xpath(short, candidates)
        try:
            el.click()
        except Exception:
            driver.execute_script("arguments[0].click();", el)
        logger.info("alerta fechado")
    except Exception:
        pass

    # dump da página pós-login para diagnóstico
    try:
        driver.save_screenshot("logs/post_login.png")
        with open("logs/post_login.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    except Exception:
        pass

    try:
        link = find_with_frames([
            X_FACPLAN_LINK_ABS,
            X_FACPLAN_LINK,
            "//a[contains(.,'Fac') and contains(.,'Plan')]",
            "//a[contains(@href,'Portal_FAC') or contains(@href,'facplan')]",
        ])
        from core.utils import scroll_to, wait as sleep_wait
        scroll_to(driver, link)
        try:
            link.click()
        except Exception:
            driver.execute_script("arguments[0].click();", link)
        sleep_wait(2)
        try:
            driver.switch_to.window(driver.window_handles[-1])
        except Exception:
            pass
        logger.info("facplan aberto e aba focada")
    except Exception:
        # se não achar o facplan, segue fluxo padrão
        pass
