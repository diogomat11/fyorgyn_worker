import sys
import os
import json

# Ajustar path para importar os módulos do Worker
worker_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Worker"))
sys.path.insert(0, worker_dir)

from factory import create_scraper

def test_op12_impressao():
    print("Iniciando Teste Local - OP12_IMPRESSAO_API (IPASGO)")

    # Dados mockados do job
    # IMPORTANTE: Substituir por números de guia válidos para testar
    job_data = {
        "job_id": 999912,
        "operation": 12, # OP12
        "convenio_id": 6, # IPASGO
        "params": json.dumps({
            "guia": "22404010376",           # NumGuiaOperadora (Mock)
            "GuiaPrestador": "22404010376",  # NumGuiaPrestador (Mock)
            "numero_copias": 1
        })
    }

    scraper = None
    try:
        scraper = create_scraper(job_data)
        scraper.setup()
        
        # Carregar dinamicamente o OP12 (pois ele está dentro do scraper config, ou podemos importar direto)
        import importlib
        op12_module = importlib.import_module("6-ipasgo.op.op12_impressao_api")
        
        print(f"Executando op12_impressao_api.execute()...")
        result = op12_module.execute(scraper, job_data)
        
        print("\n=== Resultado Final OP12 ===")
        print(json.dumps(result, indent=2))
        print("=============================\n")

    except Exception as e:
        print(f"Erro ao executar OP12: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if scraper:
            scraper.teardown()

if __name__ == "__main__":
    test_op12_impressao()
