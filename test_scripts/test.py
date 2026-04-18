import sys
sys.path.append('backend')
import traceback
from database import SessionLocal
from sqlalchemy import text
db=SessionLocal()
try:
    db.execute(text("UPDATE base_guias SET updated_at = NOW() WHERE saldo > 0"))
    db.commit()
except Exception as e:
    with open("err.txt", "w", encoding="utf-8") as f:
        f.write(str(e))
