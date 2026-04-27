import os
import sqlite3

db_path = "worker.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# We only execute the table creation. The 'convenio_operacoes' doesn't exist in worker.db usually.
# Worker.db has: base_guias, carteirinhas, convenios, faturamento_lotes, fichas, job_executions, jobs, logs, priority_rules
# It does NOT have convenio_operacoes, so we omit that part.
cursor.executescript("""
CREATE TABLE IF NOT EXISTS lotes_convenio (
    id_lote INTEGER PRIMARY KEY AUTOINCREMENT,
    id_convenio INTEGER,
    numero_lote INTEGER,
    cod_prestador TEXT,
    status TEXT DEFAULT 'Aberto',
    data_inicio DATE,
    data_fim DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_lotes_convenio_numero_lote ON lotes_convenio(numero_lote);
""")

conn.commit()
conn.close()

print("Migration 50 applied to worker.db successfully.")
