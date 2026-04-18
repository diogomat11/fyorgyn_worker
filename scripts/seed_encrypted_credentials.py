import os
import sys
from dotenv import load_dotenv

# Load .env BEFORE any other imports to ensure ENCRYPTION_KEY is available
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# Add Worker path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Worker'))

from database import SessionLocal
from models import Convenio
from security_utils import encrypt_password

def seed_credentials():
    db = SessionLocal()
    try:
        credentials = [
            {"id": 1, "name": "IPASGO", "user": "03859062143", "pass": "HRE8055"},
            {"id": 2, "name": "UNIMED", "user": "REC2209525", "pass": "Unimed@2025"},
        ]
        for cred in credentials:
            print(f">>> Processing {cred['name']}...")
            conv = db.query(Convenio).filter(Convenio.id_convenio == cred["id"]).first()
            if not conv:
                conv = Convenio(id_convenio=cred["id"], nome=cred["name"])
                db.add(conv)
            
            conv.usuario = cred["user"]
            print(f">>> Encrypting password for {cred['name']}...")
            try:
                enc = encrypt_password(cred["pass"])
                print(f">>> Encryption success. Result type: {type(enc)}")
                conv.senha_criptografada = enc
            except Exception as ee:
                print(f"!!! Encryption failed for {cred['name']}: {ee}")
                traceback.print_exc()
                raise ee
                
            print(f">>> Updated credentials for {cred['name']} (Encrypted)")
            
        print(">>> Committing to DB...")
        db.commit()
        print(">>> Seeding completed successfully.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"!!! Error seeding credentials: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_credentials()
