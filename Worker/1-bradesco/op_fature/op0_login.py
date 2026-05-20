"""
OP0 - Login no portal Faturamento (Faturi / Orizon)
Autentica o usuário no portal de faturamento.
"""
from __future__ import annotations
import time
from typing import TYPE_CHECKING
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import sys

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)]
if sys.path[0] != _mod_root:
    sys.path.insert(0, _mod_root)

from core.selenium_helpers import (
    aguardar_elemento,
    preencher_input,
    clicar_elemento,
    elemento_existe,
)

if TYPE_CHECKING:
    from base_scraper import BaseScraper

def run(scraper: BaseScraper, job_data: dict) -> list:
    """
    Executa o login no portal de Faturamento da Orizon.
    """
    scraper.log("Iniciando OP0 (Login Faturamento)")
    driver = scraper.driver

    try:
        driver.get("https://www.orizon.com.br/acesso-restrito.html")
        scraper.log("Acessando página inicial de acesso restrito...")

        # Clicar no botão 'Faturi'
        clicar_elemento(driver, By.NAME, "Faturi", timeout=15)
        scraper.log("Botão Faturi clicado, aguardando tela de login...")

        # Aguardar o campo de username
        aguardar_elemento(driver, By.ID, "username", timeout=15)
        
        # Preencher credenciais
        scraper.log(f"Preenchendo login para o usuário: {scraper.username}")
        preencher_input(driver, By.ID, "username", scraper.username)
        preencher_input(driver, By.ID, "password", scraper.password)

        # Clicar em acessar
        clicar_elemento(driver, By.XPATH, '//*[@id="kc-login"]')
        scraper.log("Credenciais enviadas.")

        # Aguardar carregamento da página interna (ex: buscar um elemento comum do fature)
        # O prompt indica aguardar até que a página carregue e verificar o modal
        time.sleep(3)

        # Tratar notificações ou frames modais
        _tratar_mensagens_iniciais(scraper, driver)

        scraper.log("Login de faturamento concluído com sucesso.")
        return [{"status": "success", "message": "Login Faturamento OK"}]

    except Exception as e:
        scraper.log(f"Erro no login de faturamento: {str(e)}", level="ERROR")
        raise


def _tratar_mensagens_iniciais(scraper: BaseScraper, driver):
    """
    Verifica se existem notificações modais como o id="mensagemImg"
    e as fecha clicando em id="botaoMensagemInicialModalPrestador".
    """
    max_tentativas = 3
    for _ in range(max_tentativas):
        try:
            # Verifica se o modal de mensagem está visível (style="display: block" ou similar, ausência de display: none)
            mensagem_img = elemento_existe(driver, By.ID, "mensagemImg", timeout=2)
            if mensagem_img and mensagem_img.is_displayed():
                scraper.log("Mensagem inicial (modal) detectada. Tentando fechar...")
                
                # Rolar para o botão e clicar
                btn_fechar = driver.find_element(By.ID, "botaoMensagemInicialModalPrestador")
                driver.execute_script("arguments[0].scrollIntoView(true);", btn_fechar)
                time.sleep(1)
                btn_fechar.click()
                
                # Aguarda um pouco e verifica de novo no próximo loop
                time.sleep(2)
            else:
                break # Nenhuma mensagem visível
        except Exception as e:
            scraper.log(f"Erro ao tratar modal inicial (pode ser ignorado se não existir): {e}", level="WARN")
            break
