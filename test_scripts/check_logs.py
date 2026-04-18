import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv('Local_worker/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as con:
    # 1. Check Convenios table
    print("=== Convenios ===")
    convs = con.execute(text("SELECT id_convenio, nome FROM convenios ORDER BY id_convenio")).fetchall()
    for c in convs:
        print(f"  id={c[0]}, nome={c[1]}")

    # 2. Check if PEI trigger exists
    print("\n=== PEI Triggers ===")
    triggers = con.execute(text("""
        SELECT trigger_name, event_manipulation, event_object_table 
        FROM information_schema.triggers 
        WHERE trigger_name LIKE '%pei%'
    """)).fetchall()
    for t in triggers:
        print(f"  {t[0]} ON {t[2]} ({t[1]})")
    if not triggers:
        print("  NO PEI TRIGGERS FOUND!")

    # 3. Check patient_pei table
    print("\n=== Patient PEI (last 5) ===")
    peis = con.execute(text("SELECT id, carteirinha_id, codigo_terapia, pei_semanal, status, validade FROM patient_pei ORDER BY id DESC LIMIT 5")).fetchall()
    for p in peis:
        print(f"  id={p[0]}, cart_id={p[1]}, terapia={p[2]}, pei={p[3]}, status={p[4]}, validade={p[5]}")
    if not peis:
        print("  EMPTY!")

    # 4. Check base_guias for Job 1's carteirinha
    print("\n=== Base Guias for cart_id=2 ===")
    guias = con.execute(text("SELECT id, carteirinha_id, id_convenio, guia, codigo_terapia, qtde_solicitada FROM base_guias WHERE carteirinha_id = 2")).fetchall()
    for g in guias:
        print(f"  id={g[0]}, cart={g[1]}, convenio={g[2]}, guia={g[3]}, terapia={g[4]}, qtde={g[5]}")
    if not guias:
        print("  EMPTY!")

    # 5. Check logs table count
    print("\n=== Logs Summary ===")
    count = con.execute(text("SELECT count(*) FROM logs")).fetchone()
    print(f"  Total logs: {count[0]}")
    latest = con.execute(text("SELECT id, level, message, job_id, carteirinha_id FROM logs ORDER BY id DESC LIMIT 3")).fetchall()
    for l in latest:
        print(f"  id={l[0]}, [{l[1]}] {l[2]}, job={l[3]}, cart={l[4]}")
