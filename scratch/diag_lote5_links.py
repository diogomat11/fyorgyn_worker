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
    
    print(f"--- Lote Agendamento {lote_ag_id} ---")
    items_ag = db.query(LoteAgendamentoItem).filter_by(id_lote_ag=lote_ag_id).all()
    print(f"Total itens: {len(items_ag)}")
    
    # Check what fat lotes they are linked to
    fat_links = {}
    for it in items_ag:
        if it.id_faturamento_lote:
            # Get the lote_id from the faturamento item
            fat_item = db.query(FaturamentoLote).filter_by(id=it.id_faturamento_lote).first()
            if fat_item:
                fat_links[fat_item.id_lote] = fat_links.get(fat_item.id_lote, 0) + 1
            else:
                fat_links["orphan_item"] = fat_links.get("orphan_item", 0) + 1
        else:
            fat_links["unlinked"] = fat_links.get("unlinked", 0) + 1
            
    print(f"Links by Faturamento Lote ID: {fat_links}")

    print(f"\n--- Lote Faturamento {lote_fat_id} ---")
    items_fat = db.query(FaturamentoLote).filter_by(id_lote=lote_fat_id).all()
    print(f"Total itens: {len(items_fat)}")
    
    conc_counts = {}
    for it in items_fat:
        st = it.StatusConciliacao or "None"
        conc_counts[st] = conc_counts.get(st, 0) + 1
    print(f"Status counts: {conc_counts}")

diag()
db.close()
