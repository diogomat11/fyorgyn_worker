import os
from dotenv import load_dotenv

load_dotenv()

# Portal do prestador AMIL (fonte de verdade das URLs: config/constants.py)
PORTAL_URL = "https://credenciado.amil.com.br/login"

# Credenciais de fallback via env (o padrão do projeto é user_convenios no banco)
USUARIO = os.getenv("AMIL_USER", "")
SENHA = os.getenv("AMIL_PASS", "")


def get_runtime_settings():
    return {
        "BROWSER": os.getenv("BROWSER", "chrome"),
        "HEADLESS": os.getenv("HEADLESS", "false"),
        "TIMEOUT": int(os.getenv("TIMEOUT", "20")),
    }
