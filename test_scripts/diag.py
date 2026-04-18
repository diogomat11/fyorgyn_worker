import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

with open("diag.log", "w", encoding="utf-8") as f:
    
    def w(msg):
        print(msg)
        f.write(msg + "\n")
    
    # 1. Check carteirinha_id in base_guias
    res = db.execute(text("SELECT id, guia, carteirinha_id FROM base_guias")).fetchall()
    w("=== BASE_GUIAS carteirinha_id ===")
    for r in res:
        w(str(r))
    
    # 2. Check if those carteirinha_ids exist in carteirinhas
    w("\n=== Verificando se carteirinha_id existe na tabela carteirinhas ===")
    for r in res:
        g_id, guia, cart_id = r
        if cart_id is None:
            w(f"Guia {guia}: carteirinha_id = NULL! A trigger vai falhar ao tentar SELECT id_paciente.")
        else:
            exists = db.execute(text(f"SELECT id, id_paciente FROM carteirinhas WHERE id = {cart_id}")).fetchone()
            if not exists:
                w(f"Guia {guia}: carteirinha_id={cart_id} nao existe na tabela carteirinhas!")
            else:
                w(f"Guia {guia}: carteirinha_id={cart_id} -> id_paciente={exists[1]} OK")
    
    # 3. Sample unlinked appointments  
    w("\n=== Amostra de Agendamentos SEM guia ===")
    ags = db.execute(text("SELECT id_agendamento, id_paciente, id_convenio, cod_procedimento_aut, Nome_Paciente FROM agendamentos WHERE numero_guia IS NULL LIMIT 10")).fetchall()
    for a in ags:
        w(str(a))
    
    # 4. Summary of patients in base_guias vs agendamentos
    w("\n=== Pacientes em base_guias (via carteirinhas) ===")
    pac_guias = db.execute(text("SELECT DISTINCT c.id_paciente, c.paciente FROM carteirinhas c JOIN base_guias g ON g.carteirinha_id = c.id")).fetchall()
    for p in pac_guias:
        w(str(p))
    
    w("\n=== Pacientes em agendamentos ===")
    pac_ags = db.execute(text("SELECT DISTINCT id_paciente, Nome_Paciente FROM agendamentos LIMIT 20")).fetchall()
    for p in pac_ags:
        w(str(p))
    
    # 5. Check if any appointment patients match guide patients
    w("\n=== Cruzamento por id_paciente ===")
    cross = db.execute(text("""
        SELECT DISTINCT a.id_paciente, a.Nome_Paciente, COUNT(g.id) as num_guias
        FROM agendamentos a
        JOIN carteirinhas c ON c.id_paciente = a.id_paciente
        JOIN base_guias g ON g.carteirinha_id = c.id
        GROUP BY a.id_paciente, a.Nome_Paciente
    """)).fetchall()
    w(f"Pacientes com guias E agendamentos: {len(cross)}")
    for p in cross:
        w(str(p))
