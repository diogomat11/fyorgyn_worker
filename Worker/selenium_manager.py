import threading
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class SeleniumManager:
    """
    Manages a pool of Selenium drivers to optimize resource usage.
    Handles creation, health checks, and lifecycle of drivers per convenio.
    """
    def __init__(self, max_drivers=3):
        self.drivers = {}  # (id_convenio, user_id) -> driver_instance
        self.last_activity = {} # (id_convenio, user_id) -> datetime
        self.max_drivers = max_drivers
        self.lock = threading.Lock()
        self.inactivity_limit = timedelta(minutes=10) # Reduzido para 10 min por exigência de segurança (ex: Bradesco)

    def get_driver(self, id_convenio, headless=True, user_id=None):
        with self.lock:
            key = (id_convenio, user_id)
            # 1. Check if we already have a driver for this key
            if key in self.drivers:
                driver = self.drivers[key]
                if self._is_alive(driver):
                    self.last_activity[key] = datetime.now()
                    return driver
                else:
                    print(f">>> Driver for key {key} is dead. Removing from pool.")
                    self.close_driver(key)

            # 2. Check pool capacity
            if len(self.drivers) >= self.max_drivers:
                # Evict oldest idle driver (LRU)
                self._evict_oldest()

            # 3. Create new driver
            print(f">>> Creating new driver for convenio {id_convenio} (user_id={user_id})...")
            driver = self._create_new_driver(headless)
            driver.current_user_id = user_id
            self.drivers[key] = driver
            self.last_activity[key] = datetime.now()
            return driver

    def _create_new_driver(self, headless):
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--kiosk-printing")
        chrome_options.add_argument("--disable-features=PasswordLeakDetection")
        chrome_options.add_argument("--incognito")  # Impede balões nativos de "Salvar Senha" ou "Senha Vazada"
        chrome_options.add_argument("--remote-allow-origins=*")
        
        # Desativar prompts de salvar senha do navegador
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        if headless:
            chrome_options.add_argument("--headless=new")
        
        max_attempts = 3
        last_err = None
        for attempt in range(1, max_attempts + 1):
            try:
                driver = webdriver.Chrome(options=chrome_options)
                driver.maximize_window()
                return driver
            except Exception as e:
                last_err = e
                print(f">>> Erro na tentativa {attempt}/{max_attempts} ao criar Chrome Driver: {e}")
                time.sleep(1)
        raise last_err


    def _is_alive(self, driver):
        try:
            # Simple check to see if driver is responding
            driver.title
            return True
        except:
            return False

    def close_driver(self, key):
        # Already assume we have the lock or it's called internally
        keys_to_close = []
        if isinstance(key, tuple):
            if key in self.drivers:
                keys_to_close.append(key)
        else:
            # key is id_convenio (legacy call), find all keys for this convenio
            for k in list(self.drivers.keys()):
                if isinstance(k, tuple) and k[0] == key:
                    keys_to_close.append(k)
                elif k == key:
                    keys_to_close.append(k)

        for k in keys_to_close:
            driver = self.drivers[k]
            id_convenio = k[0] if isinstance(k, tuple) else k
            try:
                # Logoff gracioso para convênios sensíveis a sessão presa (ex: Bradesco)
                if id_convenio == 1 and self._is_alive(driver):
                    try:
                        from selenium.webdriver.common.by import By
                        sair_btn = driver.find_elements(By.ID, "sair")
                        if sair_btn:
                            sair_btn[0].click()
                            time.sleep(2) # Aguarda o servidor registrar o logoff
                    except Exception as logoff_err:
                        print(f">>> Erro no logoff gracioso do Bradesco: {logoff_err}")
                        
                driver.quit()
            except:
                pass
            if k in self.drivers:
                del self.drivers[k]
            if k in self.last_activity:
                del self.last_activity[k]

    def _evict_oldest(self):
        if not self.last_activity:
            return
        # Find key with oldest activity
        oldest_key = min(self.last_activity, key=self.last_activity.get)
        print(f">>> Evicting oldest driver (Key {oldest_key}) to make room.")
        self.close_driver(oldest_key)

    def cleanup_idle(self):
        """Closes drivers that have been idle for too long."""
        with self.lock:
            now = datetime.now()
            to_close = []
            for key, last_time in self.last_activity.items():
                if now - last_time > self.inactivity_limit:
                    to_close.append(key)
            
            for key in to_close:
                print(f">>> Closing inactive driver for key {key}.")
                self.close_driver(key)
