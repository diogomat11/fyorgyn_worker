import sys
import os
import json
from datetime import datetime, timedelta

# Append Local_worker path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Worker.factory import ScraperFactory
import importlib.util

def run():
    print("Iniciando scraper Ipasgo para dump...")
    scraper = ScraperFactory.get_scraper(6, headless=True)
    
    # Load WebPlanClient manually
    worker_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_file = os.path.join(worker_dir, "Worker", "6-ipasgo", "core", "webplan_client.py")
    spec = importlib.util.spec_from_file_location("webplan_client", target_file)
    webplan_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(webplan_module)
    WebPlanClient = webplan_module.WebPlanClient
    
    # Simulate a fake job to get login
    fake_job = {"id": 9999, "rotina": "0"}
    try:
        scraper.login()
        print("Login concluído. Extraindo guias...")
        
        # Setup context
        scraper.driver.get("https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos")
        import time
        time.sleep(3)
        
        # Create client
        client = WebPlanClient(scraper.driver, "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos")
        
        # Query yesterday to today
        dt_fim = datetime.now().strftime("%d/%m/%Y")
        dt_ini = (datetime.now() - timedelta(days=2)).strftime("%d/%m/%Y")
        
        resp = client.post_consultar_guias(
            page=1,
            data_ini=dt_ini,
            data_fim=dt_fim
        )
        
        dump_file = os.path.join(os.path.dirname(__file__), "op11_dump.json")
        with open(dump_file, "w", encoding="utf-8") as f:
            json.dump(resp, f, ensure_ascii=False, indent=2)
            
        print(f"Dump salvo em {dump_file}")
        
    except Exception as e:
        print(f"Erro no teste: {e}")
    finally:
        if hasattr(scraper, 'driver'):
            scraper.driver.quit()

if __name__ == "__main__":
    run()
