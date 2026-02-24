import os
from dotenv import load_dotenv

load_dotenv()

PORTAL_URL = "https://portalos.ipasgo.go.gov.br/Portal_Dominio/PrestadorLogin.aspx"
USUARIO = os.getenv("IPASGO_USER", "")
SENHA = os.getenv("IPASGO_PASS", "")

def get_runtime_settings():
    return {
        "IMPORT_GUIAS_URL": os.getenv("IMPORT_GUIAS_URL", "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos"),
        "BROWSER": os.getenv("BROWSER", "chrome"),
        "HEADLESS": os.getenv("HEADLESS", "false"),
        "TIMEOUT": int(os.getenv("TIMEOUT", "20")),
    }

