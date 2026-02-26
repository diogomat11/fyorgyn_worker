import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

with open("test.log", "w", encoding="utf-8") as f:
    f.write("== Checando drifting de ID de Pacientes ==\n\n")

    ags = db.execute(text("SELECT DISTINCT id_paciente, Nome_Paciente FROM agendamentos WHERE id_paciente IS NOT NULL LIMIT 50")).fetchall()

    drifts = 0
    matches = 0
    for a in ags:
        a_id, a_nome = a
        safe_nome = str(a_nome).replace("'", "")
        carts = db.execute(text(f"SELECT id_paciente, paciente FROM carteirinhas WHERE REPLACE(paciente, '''', '') = '{safe_nome}'")).fetchall()
        for c in carts:
            c_id, c_nome = c
            if str(c_id) != str(a_id):
                f.write(f"DRIFT DETECTADO! Agendamento tem id_paciente={a_id} mas Carteirinha tem id_paciente={c_id} para '{a_nome}'\n")
                drifts += 1
            else:
                matches += 1

    f.write(f"\nFinal: {matches} matchs exatos de ID encontrados. {drifts} drifts identificados.\n")
