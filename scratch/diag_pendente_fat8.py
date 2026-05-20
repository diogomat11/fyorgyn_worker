import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import SessionLocal
from models import LoteAgendamento, LoteAgendamentoItem, LoteConvenio, FaturamentoLote, Agendamento, BaseGuia
import json

db = SessionLocal()

def diag_pendente_fat():
    lote_fat_id = 8
    items_fat = db.query(FaturamentoLote).filter_by(id_lote=lote_fat_id, StatusConciliacao='pendente').limit(20).all()
    print(f"Pendente items in Lote 8 (first 20):")
    
    for fat in items_fat:
        print(f"\nFat ID {fat.id}: Guia={fat.Guia}, Data={fat.dataRealizacao}")
        
        # Look for agendamento candidates (any lote)
        candidates = db.query(Agendamento).filter_by(numero_guia=fat.Guia).all()
        print(f"  Agendamento candidates (by Guia): {len(candidates)}")
        for ag in candidates:
            # Check if this ag is in Lote 5
            lai = db.query(LoteAgendamentoItem).filter_by(id_agendamento=ag.id_agendamento, id_lote_ag=5).first()
            in_lote5 = "YES" if lai else "NO"
            
            # Check if this ag is already linked to another fat item
            linked_fat = db.query(FaturamentoLote).filter_by(agendamento_id=ag.id_agendamento).first()
            linked_info = f"Linked to Fat {linked_fat.id}" if linked_fat else "UNLINKED"
            
            print(f"    - Agend {ag.id_agendamento}: Data={ag.data}, Lote5={in_lote5}, Link={linked_info}")

diag_pendente_fat()
db.close()
