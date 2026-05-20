import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import SessionLocal
from models import FaturamentoLote
from sqlalchemy import func

db = SessionLocal()

def find_dups():
    lote_id = 8
    # Group by Guia, dataRealizacao, CodigoBeneficiario
    dups = db.query(
        FaturamentoLote.Guia, 
        FaturamentoLote.dataRealizacao, 
        FaturamentoLote.CodigoBeneficiario,
        func.count(FaturamentoLote.id)
    ).filter_by(id_lote=lote_id).group_by(
        FaturamentoLote.Guia, 
        FaturamentoLote.dataRealizacao, 
        FaturamentoLote.CodigoBeneficiario
    ).having(func.count(FaturamentoLote.id) > 1).all()
    
    print(f"Duplicates in Lote 8: {len(dups)}")
    for d in dups[:10]:
        print(f"Guia: {d[0]}, Data: {d[1]}, Benef: {d[2]}, Count: {d[3]}")

find_dups()
db.close()
