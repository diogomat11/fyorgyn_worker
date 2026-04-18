import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "worker.db")

print(f"Applying migration to Local Worker DB: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column exists first to avoid errors if already migrated
    cursor.execute("PRAGMA table_info(base_guias)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "status_guia" not in columns:
        print("Column 'status_guia' not found. Adding it now...")
        cursor.execute("ALTER TABLE base_guias ADD COLUMN status_guia TEXT DEFAULT 'Autorizado'")
        conn.commit()
        print("Migration successful: Added 'status_guia' to base_guias.")
    else:
        print("Migration skipped: 'status_guia' already exists in base_guias.")
        
    conn.close()
except Exception as e:
    print(f"Migration Failed: {e}")
