import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import SessionLocal
from models import LoteAgendamento, LoteAgendamentoItem, LoteConvenio, FaturamentoLote, Agendamento, BaseGuia
import json

db = SessionLocal()

def diag_cross_links():
    lote_fat_id = 8
    items_fat = db.query(FaturamentoLote).filter_by(id_lote=lote_fat_id).filter(FaturamentoLote.agendamento_id.isnot(None)).all()
    print(f"Conciliado items in Faturamento Lote 8: {len(items_fat)}")
    
    links_by_ag_lote = {}
    for fat in items_fat:
        # Which ag lote does this agendamento belong to?
        lai = db.query(LoteAgendamentoItem).filter_by(id_agendamento=fat.agendamento_id).first()
        if lai:
            links_by_ag_lote[lai.id_lote_ag] = links_by_ag_lote.get(lai.id_lote_ag, 0) + 1
        else:
            links_by_ag_lote["no_lote_ag"] = links_by_ag_lote.get("no_lote_ag", 0) + 1
            
    print(f"Links to Agendamento Lotes: {links_by_ag_lote}")

diag_cross_links()
db.close()
