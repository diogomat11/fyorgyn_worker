import os
from dotenv import load_dotenv

load_dotenv()

# Portal de Autorização (Polimed/Orizon)
PORTAL_URL = "https://www.polimed.com.br/autenticadorOrizon/loginAutenticador"

# URL da OP1 - Solicitar Autorização SADT
OP1_URL = "https://www.polimed.com.br/autorize/prestadores/iframe/senha/solicitacao_senha_externa"

def get_runtime_settings():
    return {
        "BROWSER": os.getenv("BROWSER", "chrome"),
        "HEADLESS": os.getenv("HEADLESS", "false"),
        "TIMEOUT": int(os.getenv("TIMEOUT", "20")),
    }
