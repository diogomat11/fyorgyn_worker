import os
import sys

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from database import engine
from sqlalchemy import text

def touch_records():
    print("Iniciando rotina de Toque/Atualização em massa...")
    
    with engine.begin() as conn:
        print("1. Atualizando Agendamentos (Dispara trg_agendamento_define_cod_faturamento)")
        # Isso vai preencher o cod_procedimento_fat, id_procedimento e valor para os 601 agendamentos recém inseridos
        conn.execute(text("UPDATE agendamentos SET data_update = NOW()"))
        
        print("2. Inicializando Saldo (Demais Convênios)")
        # A Trigger só inicializa para Demais no INSERT. Como essas guias já existiam, atribuimos manualmente:
        conn.execute(text("UPDATE base_guias SET saldo = COALESCE(qtde_solicitada, 0) WHERE id_convenio NOT IN (3, 6)"))
        
        print("3. Atualizando Base Guias (Dispara trg_define_saldo_guia e trg_vincula_guia_a_agendamento)")
        # Isso ativará o recálculo do saldo das Unimeds e, em seguida, disparará a engrenagem de alocação de guias para os agendamentos!
        conn.execute(text("UPDATE base_guias SET updated_at = NOW()"))

    print("Rotina de Toque finalizada! As triggers do banco orquestraram os vínculos e faturamentos sob o capô.")

if __name__ == "__main__":
    touch_records()
