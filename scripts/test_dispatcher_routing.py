import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Worker'))
from database import SessionLocal
from models import Job, ServerConfig

def get_server_map():
    db = SessionLocal()
    confs = db.query(ServerConfig).all()
    print("----- ServerConfigs no DB -----")
    for c in confs:
        print(f"URL: {c.server_url}, IS_ACTIVE: {c.is_active}, CONVENIO: {c.id_convenio}, ROTINA: {c.rotina}")
    
    print("\n----- Dispatcher URL Resolution Test -----")
    env_urls = "http://127.0.0.1:9000,http://127.0.0.1:9001" # Default without mapping
    
    from dispatcher import _parse_server_urls
    print("Parse (Sem Sufixos):", _parse_server_urls(env_urls))
    
    env_urls_fixed = "http://127.0.0.1:9000:2,http://127.0.0.1:9001:3"
    print("Parse (Com Sufixos):", _parse_server_urls(env_urls_fixed))

get_server_map()
