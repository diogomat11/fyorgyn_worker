import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import SessionLocal
from models import LoteAgendamento, LoteAgendamentoItem, LoteConvenio, FaturamentoLote
import json

db = SessionLocal()

def diag():
    lote_ag_id = 5
    lote_fat_id = 8
    
    lote_ag = db.query(LoteAgendamento).filter_by(id_lote_ag=lote_ag_id).first()
    lote_fat = db.query(LoteConvenio).filter_by(id_lote=lote_fat_id).first()
    
    print(f"--- Lote Agendamento {lote_ag_id} ---")
    if lote_ag:
        items_ag = db.query(LoteAgendamentoItem).filter_by(id_lote_ag=lote_ag_id).all()
        print(f"Total itens: {len(items_ag)}")
        status_counts = {}
        for it in items_ag:
            status_counts[it.status_conciliacao] = status_counts.get(it.status_conciliacao, 0) + 1
        print(f"Status counts: {status_counts}")
    else:
        print("Lote Agendamento não encontrado")

    print(f"\n--- Lote Faturamento {lote_fat_id} ---")
    if lote_fat:
        items_fat = db.query(FaturamentoLote).filter_by(id_lote=lote_fat_id).all()
        print(f"Total itens: {len(items_fat)}")
        print(f"Numero Lote (WebPlan): {lote_fat.numero_lote}")
        status_counts = {}
        for it in items_fat:
            st = it.StatusConciliacao or "None"
            status_counts[st] = status_counts.get(st, 0) + 1
        print(f"Status counts: {status_counts}")
    else:
        print("Lote Faturamento não encontrado")

    # Sample keys
    print("\n--- Amostra de chaves (Top 10 Agendamentos) ---")
    if lote_ag:
        items_ag = db.query(LoteAgendamentoItem).filter_by(id_lote_ag=lote_ag_id).limit(10).all()
        for it in items_ag:
            # Need to fetch patient_id or something? The model has id_agendamento
            # Let's see what LoteAgendamentoItem has
            print(f"AG ID {it.id}: AgendID={it.id_agendamento}, Status={it.status_conciliacao}")

diag()
db.close()
