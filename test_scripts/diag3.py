import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

with open("diag3.log", "w", encoding="utf-8") as f:
    def w(msg):
        f.write(msg + "\n")
    
    # Note: column names in agendamentos have mixed case: "Nome_Paciente", "Status"
    # In postgres they need to be quoted
    
    # 1. Who are patients 4319 and 4545 in agendamentos?
    res = db.execute(text("""SELECT id_agendamento, id_paciente, "Nome_Paciente", carteirinha 
                             FROM agendamentos 
                             WHERE id_paciente = 4319 LIMIT 5""")).fetchall()
    w(f"Patient 4319 in agendamentos: {len(res)} rows")
    for r in res:
        w(str(r))
    
    res2 = db.execute(text("""SELECT id_agendamento, id_paciente, "Nome_Paciente", carteirinha 
                              FROM agendamentos 
                              WHERE id_paciente = 4545 LIMIT 5""")).fetchall()
    w(f"\nPatient 4545 in agendamentos: {len(res2)} rows")
    for r in res2:
        w(str(r))
    
    # 2. Carteirinhas for 4319 and 4545
    carts = db.execute(text("SELECT id, id_paciente, paciente, carteirinha FROM carteirinhas WHERE id_paciente IN (4319, 4545)")).fetchall()
    w(f"\nCarteirinhas: {len(carts)} rows")
    for c in carts:
        w(str(c))
    
    # 3. Search agendamentos by carteirinha string
    for c in carts:
        cart_num = c[3]
        res = db.execute(text(f"SELECT id_agendamento, id_paciente, carteirinha FROM agendamentos WHERE carteirinha = '{cart_num}' LIMIT 3")).fetchall()
        w(f"\nCarteirinha {cart_num}: {len(res)} agendamentos")
        for r in res:
            w(str(r))

    # 4. Sample successfully linked appointments 
    linked = db.execute(text("""SELECT id_agendamento, id_paciente, carteirinha, numero_guia, cod_procedimento_aut 
                                FROM agendamentos 
                                WHERE numero_guia IS NOT NULL LIMIT 5""")).fetchall()
    w(f"\nLinked appointments: {len(linked)}")
    for r in linked:
        w(str(r))
    
    # 5. Summary counts
    total = db.execute(text("SELECT COUNT(*) FROM agendamentos")).scalar()
    no_guia = db.execute(text("SELECT COUNT(*) FROM agendamentos WHERE numero_guia IS NULL")).scalar()
    w(f"\nTotal agendamentos: {total}")
    w(f"Sem guia: {no_guia}")
    w(f"Com guia: {total - no_guia}")
    
    # 6. For the linked ones - what are the exact values being matched?
    # Check if id_paciente = 4251 has appointments without a linker
    still_unlinked_4251 = db.execute(text("SELECT COUNT(*) FROM agendamentos WHERE id_paciente = 4251 AND numero_guia IS NULL")).scalar()
    w(f"\nPatient 4251 still unlinked: {still_unlinked_4251}")
    
    # Check how many guias patient 4251 has with valid saldo
    guias_4251 = db.execute(text("SELECT g.id, g.guia, g.codigo_terapia, g.saldo, g.data_autorizacao, g.validade FROM base_guias g WHERE g.carteirinha_id = 1")).fetchall()
    w(f"\nGuias do paciente 4251 (carteirinha_id=1): {len(guias_4251)}")
    for g in guias_4251:
        w(str(g))
