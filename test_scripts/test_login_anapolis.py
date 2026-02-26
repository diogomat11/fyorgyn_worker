"""
Teste standalone do login Unimed Anapolis.
Uso: python test_login_anapolis.py
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

from sqlalchemy import text
from database import SessionLocal, engine
from security_utils import encrypt_password

def ensure_credentials():
    """Verifica/insere credenciais no banco."""
    with engine.connect() as con:
        row = con.execute(text(
            "SELECT usuario, senha_criptografada FROM convenios WHERE id_convenio = 2"
        )).fetchone()
        
        if row and row[0] and row[1]:
            print(f"[OK] Credentials already in DB: user={row[0]}")
            return True
        
        print("[INFO] Uploading credentials...")
        senha_enc = encrypt_password("Baet@270424")
        con.execute(
            text("UPDATE convenios SET usuario = :u, senha_criptografada = :p WHERE id_convenio = 2"),
            {"u": "70205235107", "p": senha_enc}
        )
        con.commit()
        print("[OK] Credentials uploaded!")
        return True

def test_login():
    """Testa login no SGUCard Unimed Anapolis."""
    from core.scraper import UnimedAnopolisScraper
    
    db = SessionLocal()
    scraper = UnimedAnopolisScraper(id_convenio=2, db=db, headless=False)
    
    try:
        print("\n[START] Login test (headless=False)...")
        scraper.start_driver()
        
        results = scraper.process_job("op0", {"job_id": None})
        
        print(f"\n{'='*50}")
        print(f"Result: {results}")
        if results and results[0].get("status") == "success":
            print("[PASS] LOGIN TEST PASSED!")
        else:
            print("[FAIL] LOGIN TEST FAILED!")
        print(f"{'='*50}")
        
    finally:
        scraper.close_driver()
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("  TEST: Unimed Anapolis Login (Op0)")
    print("=" * 50)
    
    try:
        ensure_credentials()
        test_login()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
