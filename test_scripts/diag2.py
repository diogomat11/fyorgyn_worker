import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

with open("diag2.log", "w", encoding="utf-8") as f:
    def w(msg):
        print(msg)
        f.write(msg + "\n")
    
    # Check the patients 4319 and 4545 — do they appear in agendamentos?
    w("=== Patient 4319 in agendamentos? ===")
    try:
        res = db.execute(text("SELECT id_agendamento, id_paciente, Nome_Paciente, carteirinha FROM agendamentos WHERE id_paciente = 4319 LIMIT 5")).fetchall()
        w(f"Found {len(res)} rows with id_paciente=4319")
        for r in res:
            w(str(r))
    except Exception as e:
        w(f"ERROR: {e}")
    
    w("\n=== Patient 4545 in agendamentos? ===")
    try:
        res = db.execute(text("SELECT id_agendamento, id_paciente, Nome_Paciente, carteirinha FROM agendamentos WHERE id_paciente = 4545 LIMIT 5")).fetchall()
        w(f"Found {len(res)} rows with id_paciente=4545")
        for r in res:
            w(str(r))
    except Exception as e:
        w(f"ERROR: {e}")
    
    # Check carteirinhas for 4319 and 4545
    w("\n=== Carteirinhas for patients 4319 and 4545 ===")
    try:
        res = db.execute(text("SELECT id, id_paciente, paciente, carteirinha FROM carteirinhas WHERE id_paciente IN (4319, 4545)")).fetchall()
        for r in res:
            w(str(r))
    except Exception as e:
        w(f"ERROR: {e}")
    
    # Try to find these patients by carteirinha number (cross-reference)
    w("\n=== Searching agendamentos for carteirinha values matching these patients ===")
    try:
        carts = db.execute(text("SELECT carteirinha FROM carteirinhas WHERE id_paciente IN (4319, 4545)")).fetchall()
        for c in carts:
            cart_num = c[0]
            res = db.execute(text(f"SELECT id_agendamento, id_paciente, Nome_Paciente, carteirinha FROM agendamentos WHERE carteirinha = '{cart_num}' LIMIT 5")).fetchall()
            if res:
                w(f"Carteirinha {cart_num}: {len(res)} agendamentos encontrados: {[r[1] for r in res]}")
            else:
                w(f"Carteirinha {cart_num}: ZERO agendamentos - paciente possivelmente ausente na agenda")
    except Exception as e:
        w(f"ERROR: {e}")

    # Check what is different between patient 4251 (who HAS links) vs 4319/4545
    w("\n=== Sample of the agendamentos that DID get linked (patient 4251) ===")
    try:
        res = db.execute(text("SELECT id_agendamento, id_paciente, carteirinha, numero_guia, cod_procedimento_aut FROM agendamentos WHERE numero_guia IS NOT NULL LIMIT 5")).fetchall()
        for r in res:
            w(str(r))
    except Exception as e:
        w(f"ERROR: {e}")
