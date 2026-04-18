import os

def sync():
    backend_env = r'c:\dev\Agenda_hub_MultiConv\backend\.env'
    worker_env = r'c:\dev\Agenda_hub_MultiConv\Local_worker\.env'
    
    db_url = None
    with open(backend_env, 'r') as f:
        for line in f:
            if line.startswith('DATABASE_URL='):
                db_url = line.strip()
                break
    
    if db_url:
        with open(worker_env, 'a') as f:
            f.write('\n' + db_url + '\n')
        print(f"Sync successful: Added {db_url.split('@')[1] if '@' in db_url else 'DATABASE_URL'}")
    else:
        print("DATABASE_URL not found in backend .env")

if __name__ == "__main__":
    sync()
