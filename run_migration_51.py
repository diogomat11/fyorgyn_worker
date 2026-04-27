import sqlite3

db_path = "worker.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.executescript("""
    ALTER TABLE faturamento_lotes RENAME COLUMN loteId TO id_lote;
    DROP INDEX IF EXISTS ix_faturamento_lotes_loteId;
    CREATE INDEX IF NOT EXISTS ix_faturamento_lotes_id_lote ON faturamento_lotes (id_lote);
    """)
    conn.commit()
    print("Migration 51 applied to worker.db successfully.")
except Exception as e:
    print(f"Error: {e}")

conn.close()
