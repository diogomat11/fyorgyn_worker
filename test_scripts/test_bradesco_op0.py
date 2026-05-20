"""
Teste direto do OP0 Login Bradesco (sem dispatcher/server).
Abre o Chrome visível e tenta autenticar no Polimed/Orizon.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Worker"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from database import SessionLocal
from factory import ScraperFactory
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

USER_ID = 14
ID_CONVENIO = 1  # Bradesco

def main():
    db = SessionLocal()
    try:
        print("=== Teste OP0 Login Bradesco ===")
        print(f"User ID: {USER_ID}, Convenio: {ID_CONVENIO}")

        # Criar scraper
        scraper = ScraperFactory.get_scraper(
            id_convenio=ID_CONVENIO,
            db=db,
            headless=False,  # Visível para validação
            user_id=USER_ID
        )

        print(f"Scraper criado: {type(scraper).__name__}")
        print(f"Username: {scraper.username}")
        print(f"Cod Prestador: {scraper.cod_prestador}")

        if not scraper.username:
            print("[ERRO] Credenciais não carregadas!")
            return

        # Criar driver (visível)
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-features=PasswordLeakDetection")
        
        # Desativar prompts de salvar senha
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        scraper.driver = driver

        # Executar OP0
        print("\n--- Executando OP0 Login ---")
        result = scraper.execute_op("op0_login", {"job_id": "test_bradesco_login"})
        print(f"\nResultado: {result}")
        print(f"URL atual: {driver.current_url}")
        print("\n=== Login Bradesco concluído! ===")
        print("Pressione ENTER para fechar o navegador...")
        input()

    except Exception as e:
        print(f"\n[ERRO] {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            driver.quit()
        except:
            pass
        db.close()

if __name__ == "__main__":
    main()
