"""
Script de teste local para Rotina 3 (Execução) Unimed Anápolis.
Executa o op3_execucao.py com dados mockados para verificar o fluxo Selenium.

Uso:
  cd c:\\dev\\Agenda_hub_MultiConv\\Local_worker
  python test_scripts/test_op3_anapolis.py
"""
import sys, os

# Ajusta sys.path para encontrar os módulos do Worker
_worker_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _worker_dir)
sys.path.insert(0, os.path.join(_worker_dir, "Worker"))
sys.path.insert(0, os.path.join(_worker_dir, "Worker", "2-unimed_anapolis"))

import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class MockLogger:
    """Logger simples que imprime no terminal."""
    def log(self, msg, level="INFO", job_id=None, **kwargs):
        prefix = f"[{level}]"
        print(f"{prefix} {msg}")


class MockScraper(MockLogger):
    """Scraper mock para testes locais do op3."""
    def __init__(self, headless=False):
        self.id_convenio = 2
        self.driver = None
        self.headless = headless

    def start_driver(self):
        opts = Options()
        if self.headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(options=opts)

    def login(self):
        """Realiza login no SGUCard Anápolis."""
        from Worker.database import SessionLocal
        from Worker.models import Convenio
        from Worker.security_utils import decrypt_password

        db = SessionLocal()
        try:
            conv = db.query(Convenio).filter(Convenio.id_convenio == 2).first()
            if not conv:
                raise Exception("Convênio 2 (Anápolis) não encontrado no banco.")
            usuario = conv.usuario
            senha = decrypt_password(conv.senha_criptografada)
        finally:
            db.close()

        self.driver.get("https://sgucard.unimedanapolis.com.br/cmagnet/Login.do")
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        wait = WebDriverWait(self.driver, 20)
        wait.until(EC.presence_of_element_located((By.ID, "login"))).send_keys(usuario)
        self.driver.find_element(By.ID, "passwordTemp").send_keys(senha)
        self.driver.find_element(By.ID, "Button_DoLogin").click()
        time.sleep(4)
        self.log("Login concluído.")


# ── Parâmetros do Job Mockado ────────────────────────────────────────────────
# Edite estes valores para o agendamento a ser testado:
TEST_JOB_DATA = {
    "job_id": 9999,
    "carteirinha": "0064.8000.038792.00-0",
    "params": json.dumps({
        "agendamento_id": 9999,
        "numero_guia":    "15703377",
        "nome_profissional": "FERNANDA BARROS ATAIDE HELRIGER",
        "conselho":       "CRP",
        "data_hora":      "28/02/2026 14:00",
        "cod_procedimento_fat": "2250005278"
    })
}


if __name__ == "__main__":
    scraper = MockScraper(headless=False)
    scraper.start_driver()

    try:
        scraper.log("=== TESTE OP3 EXECUÇÃO UNIMED ANÁPOLIS ===")
        scraper.login()
        time.sleep(2)

        import importlib.util
        _op3_path = os.path.join(_worker_dir, "Worker", "2-unimed_anapolis", "op", "op3_execucao.py")
        spec = importlib.util.spec_from_file_location("op3_execucao", _op3_path)
        op3_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(op3_mod)
        execute = op3_mod.execute
        result = execute(scraper, TEST_JOB_DATA)
        scraper.log(f"=== RESULTADO: {result} ===")
    except Exception as e:
        scraper.log(f"=== ERRO: {e} ===", level="ERROR")
        import traceback
        traceback.print_exc()
    finally:
        input("Pressione ENTER para fechar o browser...")
        scraper.driver.quit()
