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
        self.drivers = {}  # convenio_id -> driver_instance
        self.last_activity = {} # convenio_id -> datetime
        self.max_drivers = max_drivers
        self.lock = threading.Lock()
        self.inactivity_limit = timedelta(minutes=20)

    def get_driver(self, id_convenio, headless=True):
        with self.lock:
            # 1. Check if we already have a driver for this convenio
            if id_convenio in self.drivers:
                driver = self.drivers[id_convenio]
                if self._is_alive(driver):
                    self.last_activity[id_convenio] = datetime.now()
                    return driver
                else:
                    print(f">>> Driver for convenio {id_convenio} is dead. Removing from pool.")
                    self.close_driver(id_convenio)

            # 2. Check pool capacity
            if len(self.drivers) >= self.max_drivers:
                # Try to repurpose the oldest idle driver instead of evicting and closing it
                oldest_cid = min(self.last_activity, key=self.last_activity.get)
                driver = self.drivers[oldest_cid]
                if self._is_alive(driver):
                    print(f">>> Repurposing oldest driver (Convenio {oldest_cid}) for Convenio {id_convenio}.")
                    del self.drivers[oldest_cid]
                    del self.last_activity[oldest_cid]
                    
                    self.drivers[id_convenio] = driver
                    self.last_activity[id_convenio] = datetime.now()
                    return driver
                else:
                    self.close_driver(oldest_cid)

            # 3. Create new driver
            print(f">>> Creating new driver for convenio {id_convenio}...")
            driver = self._create_new_driver(headless)
            self.drivers[id_convenio] = driver
            self.last_activity[id_convenio] = datetime.now()
            return driver

    def _create_new_driver(self, headless):
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--kiosk-printing")
        if headless:
            chrome_options.add_argument("--headless")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        return driver

    def _is_alive(self, driver):
        try:
            # Simple check to see if driver is responding
            driver.title
            return True
        except:
            return False

    def close_driver(self, id_convenio):
        # Already assume we have the lock or it's called internally
        if id_convenio in self.drivers:
            try:
                self.drivers[id_convenio].quit()
            except:
                pass
            del self.drivers[id_convenio]
            if id_convenio in self.last_activity:
                del self.last_activity[id_convenio]

    def _evict_oldest(self):
        if not self.last_activity:
            return
        # Find convenio with oldest activity
        oldest_cid = min(self.last_activity, key=self.last_activity.get)
        print(f">>> Evicting oldest driver (Convenio {oldest_cid}) to make room.")
        self.close_driver(oldest_cid)

    def cleanup_idle(self):
        """Closes drivers that have been idle for too long."""
        with self.lock:
            now = datetime.now()
            to_close = []
            for cid, last_time in self.last_activity.items():
                if now - last_time > self.inactivity_limit:
                    to_close.append(cid)
            
            for cid in to_close:
                print(f">>> Closing inactive driver for convenio {cid}.")
                self.close_driver(cid)
