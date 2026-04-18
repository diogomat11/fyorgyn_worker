from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from .utils import parse_bool

def get_driver(settings):
    headless = parse_bool(settings.get("HEADLESS", "false"))
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1600,900")
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(settings.get("TIMEOUT", 20))
    return driver
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def criar_driver():
    """
    Inicializa o driver Chrome com WebDriverManager.
    Essa instância será compartilhada pelas operações (OPs),
    evitando login repetido.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("start-maximized")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver
