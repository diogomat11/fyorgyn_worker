import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

query = """
SELECT a.id_agendamento, 
       a.id_paciente as a_pac, c.id_paciente as c_pac,
       a.id_convenio as a_conv, g.id_convenio as g_conv,
       a.cod_procedimento_aut as a_proc, g.codigo_terapia as g_proc,
       a.data as a_data, g.data_autorizacao as g_data_aut, g.validade as g_validade,
       g.id as guia_id, g.saldo
FROM agendamentos a
JOIN carteirinhas c ON a.id_paciente = c.id_paciente
JOIN base_guias g ON g.carteirinha_id = c.id 
                 AND a.id_convenio = g.id_convenio 
                 AND a.cod_procedimento_aut = g.codigo_terapia
WHERE a.numero_guia IS NULL 
  AND a."Status" NOT IN ('Falta', 'Cancelado')
  AND g.status_guia NOT IN ('Cancelada', 'Negada')
  AND a.data >= g.data_autorizacao
  AND a.data <= g.validade
  AND g.saldo > 0
LIMIT 10
"""

try:
    res = db.execute(text(query)).fetchall()
    print("Matches perfeitos:")
    for r in res:
        print(r)
    print(f"Total encontrados na amostragem: {len(res)}")
    
    # Check what is failing by dropping conditions
    print("\n--- Diagnosticando falhas ---")
    
    # 1. Base Matches (Ignoring dates and status/saldo)
    q1 = """
    SELECT COUNT(*) 
    FROM agendamentos a
    JOIN carteirinhas c ON a.id_paciente = c.id_paciente
    JOIN base_guias g ON g.carteirinha_id = c.id 
                     AND a.id_convenio = g.id_convenio 
                     AND a.cod_procedimento_aut = g.codigo_terapia
    """
    c1 = db.execute(text(q1)).scalar()
    print(f"Agendamentos que batem Paciente + Convenio + Terapia com uma Guia: {c1}")
    
    # 2. Add Status check
    q2 = q1 + " WHERE a.\"Status\" NOT IN ('Falta', 'Cancelado') AND g.status_guia NOT IN ('Cancelada', 'Negada')"
    c2 = db.execute(text(q2)).scalar()
    print(f" + Verificacao de Status Validos: {c2}")
    
    # 3. Add Date check
    q3 = q2 + " AND a.data >= g.data_autorizacao AND a.data <= g.validade"
    c3 = db.execute(text(q3)).scalar()
    print(f" + Verificacao de Data (Entre Autorizacao e Validade): {c3}")
    
    # 4. Add Saldo check
    q4 = q3 + " AND g.saldo > 0"
    c4 = db.execute(text(q4)).scalar()
    print(f" + Verificacao de Saldo > 0 (O que a Trigger ve e atualiza): {c4}")

except Exception as e:
    print("ERRO:", e)
