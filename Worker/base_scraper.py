from abc import ABC, abstractmethod
from security_utils import decrypt_password

class BaseScraper(ABC):
    def __init__(self, id_convenio=None, db=None, headless=True, user_id=None):
        self.id_convenio = id_convenio
        self.db = db
        self.headless = headless
        self.driver = None
        self.user_id = user_id
        self.username = None
        self.password = None
        self.cod_prestador = None
        
        # Standard configs
        self.wait_timeout = 20
        self.max_retries = 3

    def _extract_credentials_from_dict(self, data_dict):
        if not data_dict or not isinstance(data_dict, dict):
            return False

        params = data_dict.get("params")
        if isinstance(params, str):
            try:
                import json
                params = json.loads(params)
            except Exception:
                params = None

        merged = {}
        merged.update(data_dict)
        if isinstance(params, dict):
            merged.update(params)

        login_val = merged.get("login") or merged.get("username") or merged.get("usuario")
        if login_val:
            self.username = str(login_val).strip()

        pwd_raw = merged.get("password") or merged.get("senha")
        if not pwd_raw and merged.get("senha_criptografada"):
            try:
                pwd_raw = decrypt_password(merged.get("senha_criptografada"))
            except Exception:
                pass
        if pwd_raw:
            self.password = str(pwd_raw).strip()

        prest_val = (
            merged.get("cod_prestador") or
            merged.get("codigoPrestador") or
            merged.get("prestador")
        )
        if prest_val:
            self.cod_prestador = str(prest_val).strip()

        return bool(self.username and self.password)


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
