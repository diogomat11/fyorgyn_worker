import os
import sys

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from database import SessionLocal
from models import Procedimento, ProcedimentoFaturamento
from sqlalchemy import text

def fix_procedimentos():
    db = SessionLocal()
    print("Atualizando os códigos TUSS dos procedimentos plantados previamente...")
    
    # 10101012 para Unimed Goiania e Anapolis (Consulta)
    db.query(Procedimento).filter(Procedimento.nome.ilike("%consulta%")).update({"autorizacao": "10101012"}, synchronize_session=False)

    # 2250 para todas as terapias listadas na base importada
    db.query(Procedimento).filter(Procedimento.nome.ilike("%psico%")).update({"autorizacao": "2250005278"}, synchronize_session=False)  # Example generic mapping for tests
    # If we need exact mapping we can query the unique aut codes in Agendamentos
    
    ag_codes = db.execute(text("SELECT DISTINCT cod_procedimento_aut FROM agendamentos WHERE cod_procedimento_aut IS NOT NULL")).fetchall()
    print(f"Códigos encontrados no Agendamentos CSV: {[c[0] for c in ag_codes]}")
    
    # Mapeando os cruciais
    mapping = {
        "2250005170": "TERAPIA OCUPACIONAL",
        "2250005103": "FONOAUDIOLOGIA",
        "2250005278": "PSICOPEDAGOGIA", # Módulo genérico, só pra preencher na Demo
        "10101012": "CONSULTA"
    }
    
    for cod, proc_name in mapping.items():
        # Pra cada um dos convenios ativos 3 e 6
        for conv in [3, 6]:
            proc = db.query(Procedimento).filter(Procedimento.id_convenio == conv, Procedimento.nome.ilike(f"%{proc_name}%")).first()
            if proc:
                proc.autorizacao = cod
                db.add(proc)
            else:
                 # Cria dinamicamente pra nao faltar nada!
                 new_proc = Procedimento(
                     nome=proc_name,
                     codigo_procedimento=cod,
                     autorizacao=cod,
                     faturamento=f"FAT_{cod}",
                     id_convenio=conv
                 )
                 db.add(new_proc)
                 db.flush()
                 
                 new_fat = ProcedimentoFaturamento(
                     id_procedimento=new_proc.id_procedimento,
                     id_convenio=conv,
                     valor=110.0 if conv == 3 else 130.0,
                  )
                 db.add(new_fat)
                 
    db.commit()
    print("Procedimentos e Valores inseridos/atualizados com os Códigos da importação! O Match do PG agora vai acontecer.")

if __name__ == "__main__":
    fix_procedimentos()
