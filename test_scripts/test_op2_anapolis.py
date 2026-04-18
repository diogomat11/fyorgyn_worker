"""
Teste standalone de OP=1 (Consulta Guias) para Unimed Anapolis.
Carteirinha: 0064.8000.387928.00-0
"""
import os
import sys

# Paths
worker_root = os.path.join(os.path.dirname(__file__), 'Local_worker', 'Worker')
sys.path.insert(0, worker_root)
sys.path.insert(0, os.path.join(worker_root, '5-unimed_anapolis'))

from dotenv import load_dotenv
load_dotenv('Local_worker/.env')
load_dotenv('backend/.env')

from database import SessionLocal

def test_op2():
    from core.scraper import UnimedAnopolisScraper
    
    db = SessionLocal()
    scraper = UnimedAnopolisScraper(id_convenio=2, db=db, headless=False)
    
    # Dados do job
    job_data = {
        "job_id": 9999,
        "carteirinha": "0064.8000.387928.00-0",
        "paciente_nome": "GABRIELA NUNES DE OLIVEIRA",
        "params": '{"guias": ["15089518"]}'
    }

    try:
        print("\n[START] Op2 Test (Captura Guias)...")
        scraper.start_driver()
        scraper.login()
        
        # Run Op2
        results = scraper.process_job("2", job_data)
        
        print(f"\n{'='*50}")
        print(f"Results Captured: {len(results)}")
        for r in results:
            print(f"  - Guia: {r.get('numero_guia')} | Status: {r.get('status')} | Data: {r.get('data_autorizacao')}")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Keep open for a moment to see
        # time.sleep(5)
        scraper.close_driver()
        db.close()

if __name__ == "__main__":
    test_op2()
