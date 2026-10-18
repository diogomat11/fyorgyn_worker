import os
from dotenv import load_dotenv

load_dotenv()

# Portal do prestador CAESAN (fonts de verdade dos xpaths: config/constants.py)
PORTAL_URL = "https://www.caesan.com.br/login-prestador/"

# Credenciais de fallback via env (o padrão do projeto é user_convenios no banco)
USUARIO = os.getenv("CAESAN_USER", "")
SENHA = os.getenv("CAESAN_PASS", "")


def get_runtime_settings():
    return {
        "BROWSER": os.getenv("BROWSER", "chrome"),
        "HEADLESS": os.getenv("HEADLESS", "false"),
        "TIMEOUT": int(os.getenv("TIMEOUT", "20")),
    }
