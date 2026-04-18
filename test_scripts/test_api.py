import os, json, requests
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv('Local_worker/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as con:
    users = con.execute(text('SELECT id, username, id_convenio, api_key FROM users')).fetchall()
    
    for u in users:
        print(f"\n--- User id={u[0]}, name={u[1]}, convenio={u[2]} ---")
        r = requests.get(
            'http://127.0.0.1:8000/api/logs/', 
            params={'skip': 0, 'limit': 3}, 
            headers={'Authorization': f'Bearer {u[3]}'}
        )
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            d = r.json()
            print(f"  Total: {d.get('total')}, returned: {len(d.get('data', []))}")
            for log in d.get('data', []):
                print(f"    [{log['level']}] {log['message'][:60]}")
        else:
            print(f"  Error: {r.text[:100]}")
