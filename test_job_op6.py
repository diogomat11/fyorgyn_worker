import sys
import os
import json

# Setup env
_mod_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "Worker"))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

try:
    from database import SessionLocal
    from models import Job, Carteirinha
except ImportError as e:
    print(f"Error importing DB/Models: {e}")
    sys.exit(1)

def insert_test_job():
    db = SessionLocal()

    # Get a dummy carteirinha or create one
    cart = db.query(Carteirinha).first()
    if not cart:
        cart = Carteirinha(carteirinha="MOCK_TEST_OP6", id_convenio=6)
        db.add(cart)
        db.commit()

    # Create job OP6
    job = Job(
        carteirinha_id=cart.id,
        id_convenio=6,
        rotina="6",
        params=json.dumps({"loteId": 77795, "codigoPrestador": "00632-2"}),
        status="pending",
        priority=0
    )
    db.add(job)
    db.commit()
    
    print(f"✅ Job criado com sucesso! ID: {job.id}")
    print("Agora você já pode testar o worker iniciando-o e aguardando processar o OP6.")
    
if __name__ == "__main__":
    insert_test_job()
