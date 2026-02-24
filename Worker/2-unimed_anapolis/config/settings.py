"""
Configurações do SGUCard Unimed Anapolis
URLs, seletores e timeouts centralizados
"""

# === URLs ===
BASE_URL = "https://sgucard.unimedanapolis.com.br"
LOGIN_URL = f"{BASE_URL}/cmagnet/Login.do"

# === Seletores de Login ===
class LoginSelectors:
    INPUT_LOGIN = "login"             # By.ID
    INPUT_PASSWORD = "passwordTemp"   # By.ID
    BUTTON_LOGIN = "Button_DoLogin"   # By.ID

# === Seletores de Navegação (pós-login) ===
class NavSelectors:
    MENU_CENTRO_61 = "#centro_61 img"                   # CSS - Menu principal
    MENU_ITEM_2 = "mainMenuItem2"                        # By.ID
    BUTTON_ROUNDED = ".MagnetoBigRoundedButtonLeft"      # CSS
    SUBMENU_CENTRO_21 = "#centro_21 .MagnetoSubMenuTittle"  # CSS

# === Timeouts (segundos) ===
LOGIN_TIMEOUT = 20
PAGE_LOAD_TIMEOUT = 30
ELEMENT_WAIT_TIMEOUT = 10

# === Janelas ===
POST_LOGIN_WAIT = 4  # Segundos após clicar login
POPUP_CHECK_WAIT = 2  # Segundos para checar popup
