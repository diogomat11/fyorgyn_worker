import os
import sys
import csv
from datetime import datetime

# Permite importar do backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from database import SessionLocal
from models import (
    Agendamento, CorpoClinico, Convenio, Carteirinha, 
    Procedimento, ProcedimentoFaturamento
)

def run_import(csv_path: str):
    db = SessionLocal()
    agendamentos_added = 0
    profissionais_added = 0
    
    try:
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                # 1. Normalizar Data e Hora
                # Data: DD/MM/YYYY -> Date object
                try:
                    data_obj = datetime.strptime(row['data'], '%d/%m/%Y').date()
                except ValueError:
                    data_obj = None
                    
                # Hora: HH:MM:SS -> Time object
                try:
                    hora_obj = datetime.strptime(row['hora_inicio'], '%H:%M:%S').time()
                except ValueError:
                    hora_obj = None

                # 2. Descobrir id_convenio
                nome_convenio_csv = row['nome_convenio'].strip()
                convenio = db.query(Convenio).filter(Convenio.nome.ilike(f"%{nome_convenio_csv}%")).first()
                id_convenio_val = convenio.id_convenio if convenio else None
                
                # 3. Tratar Profissional no Corpo Clinico
                id_prof_csv = int(row['Id_profissional']) if row['Id_profissional'].isdigit() else None
                nome_prof_csv = row['Nome_profissional'].strip()
                
                if id_prof_csv:
                    prof_db = db.query(CorpoClinico).filter(CorpoClinico.id_profissional == id_prof_csv).first()
                    if not prof_db:
                        new_prof = CorpoClinico(
                            id_profissional=id_prof_csv,
                            nome=nome_prof_csv,
                            status="ativo"
                        )
                        db.add(new_prof)
                        db.flush()
                        profissionais_added += 1

                # 4. Encontrar a Carteirinha Ativa para o Paciente
                id_paciente_csv = int(row['id_paciente']) if row['id_paciente'].isdigit() else None
                id_carteirinha_val = None
                carteirinha_nome_val = row['carteirinha'].strip() # fallback
                
                if id_paciente_csv and id_convenio_val:
                    # Busca carteirinha ativa na relação paciente / convenio
                    cart_bd = db.query(Carteirinha).filter(
                        Carteirinha.id_paciente == id_paciente_csv,
                        Carteirinha.id_convenio == id_convenio_val,
                        Carteirinha.status == 'Ativo'
                    ).first()
                    
                    if not cart_bd:
                        # Se não tiver ativo, pega a primeira que encontrar dessa relação
                        cart_bd = db.query(Carteirinha).filter(
                            Carteirinha.id_paciente == id_paciente_csv,
                            Carteirinha.id_convenio == id_convenio_val
                        ).first()
                        
                    if cart_bd:
                        id_carteirinha_val = cart_bd.id
                        carteirinha_nome_val = cart_bd.carteirinha

                # 5. Extração de Procedimento e Valores
                cod_aut = row.get('cod_procedimento_aut', '').strip()
                id_proc_val = None
                cod_fat_val = None
                nome_proc_val = None
                valor_proc_val = 0.0
                
                if cod_aut and id_convenio_val:
                    proc = db.query(Procedimento).filter(
                        Procedimento.codigo_procedimento == cod_aut,
                        Procedimento.id_convenio == id_convenio_val
                    ).first()
                    
                    if proc:
                        id_proc_val = proc.id_procedimento
                        cod_fat_val = proc.faturamento
                        nome_proc_val = proc.nome
                        
                        proc_fat = db.query(ProcedimentoFaturamento).filter(
                            ProcedimentoFaturamento.id_procedimento == proc.id_procedimento,
                            ProcedimentoFaturamento.id_convenio == id_convenio_val
                        ).first()
                        
                        if proc_fat:
                            valor_proc_val = proc_fat.valor

                # 6. Criar Agendamento
                novo_agendamento = Agendamento(
                    id_agendamento=int(row['id_agendamento']) if row['id_agendamento'].isdigit() else None,
                    id_paciente=id_paciente_csv,
                    id_unidade=int(row['id_unidade']) if row['id_unidade'].isdigit() else None,
                    id_carteirinha=id_carteirinha_val,
                    carteirinha=carteirinha_nome_val,
                    Nome_Paciente=row['Nome_Paciente'],
                    id_convenio=id_convenio_val,
                    nome_convenio=nome_convenio_csv,
                    data=data_obj,
                    hora_inicio=hora_obj,
                    sala=row.get('sala'),
                    Id_profissional=id_prof_csv,
                    Nome_profissional=nome_prof_csv,
                    Tipo_atendimento=row.get('Tipo_atendimento'),
                    id_procedimento=id_proc_val,
                    cod_procedimento_fat=cod_fat_val,
                    nome_procedimento=nome_proc_val,
                    valor_procedimento=valor_proc_val,
                    cod_procedimento_aut=cod_aut,
                    Status=row.get('Status', 'A Confirmar')
                )
                
                db.merge(novo_agendamento)
                agendamentos_added += 1

        db.commit()
        print(f"Sucesso! Foram checados/adicionados {profissionais_added} novos profissionais.")
        print(f"Foram processados {agendamentos_added} agendamentos a partir do CSV.")

    except Exception as e:
        db.rollback()
        print(f"Erro durante importação do CSV: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    csv_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'modelos_csv', 'csv_agendamentos.csv'))
    if os.path.exists(csv_file):
        print(f"Encontrado CSV: {csv_file}. Iniciando...")
        run_import(csv_file)
    else:
        print(f"Arquivo CSV não encontrado em: {csv_file}")
