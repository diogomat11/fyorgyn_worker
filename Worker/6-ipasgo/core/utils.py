# core/utils.py
from loguru import logger as _logger
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime

def get_logger():
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    _logger.remove()
    _logger.add("logs/app.log", rotation="1 week", enqueue=True, backtrace=True, diagnose=False)
    _logger.add(lambda msg: print(msg, end=""))
    return _logger

def parse_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}

def wait(seconds):
    time.sleep(seconds)

def find_xpath(driver, xpath, timeout=20):
    wait_obj = WebDriverWait(driver, timeout)
    return wait_obj.until(EC.presence_of_element_located((By.XPATH, xpath)))

def scroll_to(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior:'instant', block:'center'});", element)
    except Exception:
        pass

def parse_date(s):
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    raise ValueError("data inválida")
import time
from selenium.webdriver.common.by import By


def wait(seconds: int):
    time.sleep(seconds)


def find(driver, xpath: str):
    return driver.find_element(By.XPATH, xpath)


def scroll_to(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
