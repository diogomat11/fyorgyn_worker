import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("== Diagnosticando Base_Guias ==")
guias = db.execute(text("SELECT g.id, g.guia, c.id_paciente, g.id_convenio, g.codigo_terapia, g.data_autorizacao, g.validade, g.saldo FROM base_guias g JOIN carteirinhas c ON g.carteirinha_id = c.id")).fetchall()
print(f"Existem {len(guias)} guias.")

print("\n== Procurando Agendamentos Elegiveis por Guia ==")
for g in guias:
    g_id, guia, g_pac, g_conv, g_terapia, g_dautorizacao, g_dvalidade, g_saldo = g
    print(f"\nGuia {guia} (paciente: {g_pac}, convenio: {g_conv}, terapia: {g_terapia}, {g_dautorizacao} a {g_dvalidade}, saldo: {g_saldo})")
    
    # Check just by patient
    pac_match = db.execute(text(f"SELECT COUNT(*) FROM agendamentos WHERE id_paciente = {g_pac}")).scalar()
    
    # Check by patient and convenio
    conv_match = db.execute(text(f"SELECT COUNT(*) FROM agendamentos WHERE id_paciente = {g_pac} AND id_convenio = {g_conv}")).scalar()
    
    # Check by patient, convenio and terapia
    terapia_match = db.execute(text(f"SELECT COUNT(*) FROM agendamentos WHERE id_paciente = {g_pac} AND id_convenio = {g_conv} AND cod_procedimento_aut = '{g_terapia}'")).scalar()
    
    # Check by date
    if g_dautorizacao and g_dvalidade:
        date_match = db.execute(text(f"SELECT COUNT(*) FROM agendamentos WHERE id_paciente = {g_pac} AND id_convenio = {g_conv} AND cod_procedimento_aut = '{g_terapia}' AND data >= '{g_dautorizacao}' AND data <= '{g_dvalidade}'")).scalar()
    else:
        date_match = "N/A (Datas de Guia Ausentes)"
        
    print(f"  - Agendamentos do mesmo paciente: {pac_match}")
    print(f"  - Mesmo paciente + convenio: {conv_match}")
    print(f"  - Mesmo pac + conv + terapia: {terapia_match}")
    print(f"  - Mesmo pac + conv + terapia + na data: {date_match}")
