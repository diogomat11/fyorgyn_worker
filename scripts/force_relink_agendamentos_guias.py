import os
import sys

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from database import SessionLocal
from models import Agendamento, BaseGuia
from sqlalchemy import func

def force_relink():
    db = SessionLocal()
    print("Iniciando limpeza e engatilhamento dos Agendamentos e Guias...")
    
    try:
        # 1. Limpar Agendamentos com Faturamento = 'sim' (lixo da importacao antiga)
        updated_sim = db.query(Agendamento).filter(Agendamento.cod_procedimento_fat == 'sim').update({
            Agendamento.cod_procedimento_fat: None,
            Agendamento.nome_procedimento: None,
            Agendamento.valor_procedimento: None
        }, synchronize_session=False)
        db.commit()
        print(f"Limpos {updated_sim} registros de agendamento que possuiam lixo no cod_faturamento='sim'.")

        # 2. Touch em TODOS os agendamentos sem guia
        # Isso faz o trigger BEFORE UPDATE disparar, o qual auto-preenchera o cod_procedimento_fat com o TUSS.
        updated_ags = db.query(Agendamento).filter(Agendamento.numero_guia == None).update({
            Agendamento.data_update: func.now()
        }, synchronize_session=False)
        db.commit()
        print(f"Toque (Touch) dado em {updated_ags} agendamentos. Os triggers de faturamento foram processados pelo Postgres.")

        # 3. Touch nas Guias com Saldo Positivo
        # Isso acorda o trigger da tabela base_guias que vasculhara os Agendamentos em busca dos sem-guia.
        updated_guias = db.query(BaseGuia).filter(
            BaseGuia.saldo > 0,
            BaseGuia.status_guia.notin_(['Cancelada', 'Negada'])
        ).update({
            BaseGuia.updated_at: func.now()
        }, synchronize_session=False)
        db.commit()
        print(f"Toque (Touch) dado em {updated_guias} Guias com saldo restante. As triggers de vinculacao assimilaram os novos Agendamentos limpos.")

        print("Operacao de engatilhamento em massa concluida com sucesso!")

    except Exception as e:
        db.rollback()
        print(f"Erro durante forcar o relink: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    force_relink()
