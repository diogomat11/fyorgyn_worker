import os
import sys
import logging
from sqlalchemy.dialects.postgresql import insert

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from core.webplan_client import WebPlanClient
from core.webplan_parser import parse_detalhes, extract_total_pages

# We must import the FaturamentoLote model. 
# We'll try to import from worker models.
try:
    from models import FaturamentoLote, LoteConvenio
except ImportError:
    # Fallback to backend models if running differently
    backend_path = os.path.join(os.path.dirname(os.path.dirname(_mod_root)), 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    from models import FaturamentoLote, LoteConvenio

def run(scraper, job_data):
    """
    OP6 - Check Baixados - IPASGO
    Consome a API LoadDetalhes via requests.Session autenticado e persiste no banco (Upsert).
    """
    driver = scraper.driver
    job_id = job_data.get("job_id")
    # Changed from loteId to numero_lote to match DB nomenclature
    numero_lote = job_data.get("numero_lote", job_data.get("loteId")) 
    codigo_prestador = job_data.get("codigoPrestador", "")
    
    scraper.log(f"OP6 - Iniciando extração (Lote: {numero_lote}) via WebPlan API...", job_id=job_id)
    
    if not numero_lote:
        raise ValueError("O parâmetro 'numero_lote' é obrigatório para a OP6.")

    # 1. Garante navegação inicial para a página de faturamento conforme solicitado
    faturamento_url = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/FaturamentoAtendimentos"
    scraper.log(f"OP6 - Navegando para URL de Faturamento: {faturamento_url}", job_id=job_id)
    driver.get(faturamento_url)
    
    # 2. Init Client and extract Session
    from time import sleep
    sleep(3) # Wait for page and cookies to settle
    client = WebPlanClient(driver)
    
    # 3. First call (Page 0) to get NumberOfPages
    scraper.log("Consultando Página 0 para obter metadados...", job_id=job_id)
    first_page_data = client.post_load_detalhes(lote_id=numero_lote, page=0, codigo_prestador=codigo_prestador)
    
    # ── LOG THE PAYLOAD PREVIEW ──
    preview = str(first_page_data)[:150].replace('\n', '')
    scraper.log(f"Raw API Response Preview [Pag 0]: {preview}...", job_id=job_id)
    
    total_pages = extract_total_pages(first_page_data)
    scraper.log(f"Total de páginas a processar: {total_pages}", job_id=job_id)
    
    # Parse first page
    parsed_items = parse_detalhes(first_page_data, lote_id_param=numero_lote)
    scraper.log(f"Extraídos {len(parsed_items)} registros da página 0", job_id=job_id)
    all_items = []
    all_items.extend(parsed_items)
    
    # 4. Loop the rest of the pages
    if total_pages > 1:
        for page_num in range(1, total_pages):
            scraper.log(f"Buscando página {page_num} de {total_pages-1}...", job_id=job_id)
            page_data = client.post_load_detalhes(lote_id=numero_lote, page=page_num, codigo_prestador=codigo_prestador)
            items = parse_detalhes(page_data, lote_id_param=numero_lote)
            scraper.log(f"Extraídos {len(items)} registros da página {page_num}", job_id=job_id)
            all_items.extend(items)
            
    scraper.log(f"OP6 - Extração concluída. Total de {len(all_items)} registros recebidos.", job_id=job_id)
    
    # 5. Save to DB using Bulk Upsert for maximum performance
    try:
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)
        
        # 1. Obter id_lote interno apenas uma vez
        lote_interno_id = None
        lote_interno = scraper.db.query(LoteConvenio).filter(
            LoteConvenio.numero_lote == str(numero_lote),
            LoteConvenio.cod_prestador == codigo_prestador,
            LoteConvenio.id_convenio == 6
        ).first()
        
        if lote_interno:
            lote_interno_id = lote_interno.id_lote
        else:
            scraper.log(f"AVISO: LoteInterno não encontrado para numero_lote={numero_lote}, cod_prestador={codigo_prestador}. Itens ficarão sem id_lote local.", job_id=job_id)
            
        # 2. Bulk fetch de todos os detalheIds retornados
        detalhe_ids = [item['detalheId'] for item in all_items if 'detalheId' in item]
        existing_items = {}
        
        chunk_size = 900 # Limite de IN clauses no SQLite
        for i in range(0, len(detalhe_ids), chunk_size):
            chunk = detalhe_ids[i:i+chunk_size]
            db_items = scraper.db.query(FaturamentoLote).filter(FaturamentoLote.detalheId.in_(chunk)).all()
            for db_item in db_items:
                existing_items[db_item.detalheId] = db_item
                
        count_inserted = 0
        count_updated = 0
        novos_itens = []
        
        # 3. Processamento em Memória
        for item in all_items:
            det_id = item['detalheId']
            existing = existing_items.get(det_id)
            
            if existing:
                existing.dataRealizacao = item['dataRealizacao']
                existing.Guia = str(item['Guia']) if item.get('Guia') else ''
                existing.StatusConferencia = item.get('StatusConferencia', 0)
                existing.ValorProcedimento = item.get('ValorProcedimento', 0.0)
                existing.CodigoBeneficiario = item.get('CodigoBeneficiario', '')
                existing.updated_at = now_utc
                if lote_interno_id:
                    existing.id_lote = lote_interno_id
                count_updated += 1
            else:
                novo = FaturamentoLote(
                    detalheId=det_id,
                    CodigoBeneficiario=item.get('CodigoBeneficiario', ''),
                    dataRealizacao=item['dataRealizacao'],
                    Guia=str(item['Guia']) if item.get('Guia') else '',
                    StatusConferencia=item.get('StatusConferencia', 0),
                    ValorProcedimento=item.get('ValorProcedimento', 0.0),
                    id_lote=lote_interno_id,
                    StatusConciliacao="pendente",
                    updated_at=now_utc
                )
                novos_itens.append(novo)
                count_inserted += 1
                
        # 4. Bulk Insert dos novos
        if novos_itens:
            scraper.db.bulk_save_objects(novos_itens)
            
        scraper.db.commit()
        scraper.log(f"Persistência Concluída (Bulk): {count_inserted} inseridos, {count_updated} atualizados.", job_id=job_id)
    except Exception as e:
        scraper.db.rollback()
        raise RuntimeError(f"Database error persisting FaturamentoLotes: {e}")
    
    # Update job output
    return []

