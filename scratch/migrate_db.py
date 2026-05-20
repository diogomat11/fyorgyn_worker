import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE faturamento_lotes ADD COLUMN cod_procedimento_fat TEXT"))
        # SQLAlchemy 2.0 requires explicit commit for some drivers
        try: conn.commit()
        except: pass
        print("Column cod_procedimento_fat added to faturamento_lotes.")
    except Exception as e:
        if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
            print("Column already exists.")
        else:
            print(f"Error adding column: {e}")
