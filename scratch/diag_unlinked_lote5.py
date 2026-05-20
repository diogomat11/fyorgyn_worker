import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import SessionLocal
from models import LoteAgendamento, LoteAgendamentoItem, LoteConvenio, FaturamentoLote, Agendamento, BaseGuia
import json

db = SessionLocal()

def diag_unlinked():
    lote_ag_id = 5
    items_ag = db.query(LoteAgendamentoItem).filter_by(id_lote_ag=lote_ag_id, status_conciliacao='Não Conciliado').all()
    print(f"Unlinked items in Lote 5: {len(items_ag)}")
    
    for lai in items_ag:
        ag = db.query(Agendamento).filter_by(id_agendamento=lai.id_agendamento).first()
        if not ag:
            print(f"LAI {lai.id}: Agendamento {lai.id_agendamento} NOT FOUND")
            continue
            
        print(f"\nLAI {lai.id}: Agend {ag.id_agendamento}")
        print(f"  Guia: {ag.numero_guia}")
        print(f"  Data: {ag.data}")
        print(f"  Proced: {ag.cod_procedimento_fat}")
        
        # Check if guia exists in BaseGuia
        if ag.numero_guia:
            guia = db.query(BaseGuia).filter_by(guia=ag.numero_guia).first()
            if guia:
                print(f"  BaseGuia: Found (Auth: {guia.data_autorizacao}, Val: {guia.validade})")
            else:
                print(f"  BaseGuia: NOT FOUND")
        
        # Check if there are candidate faturamento items in Lote 8
        lote_fat_id = 8
        candidates = db.query(FaturamentoLote).filter(
            FaturamentoLote.id_lote == lote_fat_id,
            FaturamentoLote.Guia == ag.numero_guia,
            FaturamentoLote.agendamento_id.is_(None)
        ).all()
        print(f"  Candidates in Lote 8 (by Guia): {len(candidates)}")
        for c in candidates:
             print(f"    - Fat ID {c.id}: Guia={c.Guia}, Data={c.dataRealizacao}, Status={c.StatusConciliacao}")

diag_unlinked()
db.close()
