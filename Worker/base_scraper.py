from abc import ABC, abstractmethod
from selenium import webdriver

class BaseScraper(ABC):
    def __init__(self, id_convenio=None, db=None, headless=True, user_id=None):
        self.id_convenio = id_convenio
        self.db = db
        self.headless = headless
        self.driver = None
        self.user_id = user_id
        
        # Standard configs
        self.wait_timeout = 20
        self.max_retries = 3


    @abstractmethod
    def start_driver(self):
        pass

    @abstractmethod
    def close_driver(self):
        pass

    @abstractmethod
    def login(self):
        pass

    @abstractmethod
    def process_job(self, rotina, job_data):
        """
        Executa a rotina especificada para o job.
        """
        pass
