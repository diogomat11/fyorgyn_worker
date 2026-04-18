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
    from models import FaturamentoLote
except ImportError:
    # Fallback to backend models if running differently
    backend_path = os.path.join(os.path.dirname(os.path.dirname(_mod_root)), 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    from models import FaturamentoLote

def run(scraper, job_data):
    """
    OP6 - Check Baixados - IPASGO
    Consome a API LoadDetalhes via requests.Session autenticado e persiste no banco (Upsert).
    """
    driver = scraper.driver
    job_id = job_data.get("job_id")
    lote_id = job_data.get("loteId")
    codigo_prestador = job_data.get("codigoPrestador", "")
    
    scraper.log(f"OP6 - Iniciando extração (Lote: {lote_id}) via WebPlan API...", job_id=job_id)
    
    if not lote_id:
        raise ValueError("O parâmetro 'loteId' é obrigatório para a OP6.")

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
    first_page_data = client.post_load_detalhes(lote_id=lote_id, page=0, codigo_prestador=codigo_prestador)
    
    # ── LOG THE PAYLOAD PREVIEW ──
    preview = str(first_page_data)[:150].replace('\n', '')
    scraper.log(f"Raw API Response Preview [Pag 0]: {preview}...", job_id=job_id)
    
    total_pages = extract_total_pages(first_page_data)
    scraper.log(f"Total de páginas a processar: {total_pages}", job_id=job_id)
    
    # Parse first page
    parsed_items = parse_detalhes(first_page_data, lote_id_param=lote_id)
    scraper.log(f"Extraídos {len(parsed_items)} registros da página 0", job_id=job_id)
    all_items = []
    all_items.extend(parsed_items)
    
    # 4. Loop the rest of the pages
    if total_pages > 1:
        for page_num in range(1, total_pages):
            scraper.log(f"Buscando página {page_num} de {total_pages-1}...", job_id=job_id)
            page_data = client.post_load_detalhes(lote_id=lote_id, page=page_num, codigo_prestador=codigo_prestador)
            items = parse_detalhes(page_data, lote_id_param=lote_id)
            scraper.log(f"Extraídos {len(items)} registros da página {page_num}", job_id=job_id)
            all_items.extend(items)
            
    scraper.log(f"OP6 - Extração concluída. Total de {len(all_items)} registros recebidos.", job_id=job_id)
    
    # 5. Save to DB using Upsert (SQLite syntax vs PostgreSQL syntax fallback handling)
    try:
        # Simple bulk loop (if UPSERT is too complex across sqlite/postgres, we merge one by one)
        # Using a loop with merge
        for item in all_items:
            existing = scraper.db.query(FaturamentoLote).filter_by(detalheId=item['detalheId']).first()
            if existing:
                existing.DataRealizacao = item['dataRealizacao']
                existing.Guia = str(item['Guia'])
                existing.StatusConferencia = item['StatusConferencia']
                existing.ValorProcedimento = item['ValorProcedimento']
                existing.CodigoBeneficiario = item['CodigoBeneficiario']
                # Usually we won't rewrite loteId if it can belong to multiple? But the YAML says loteId is a field.
                existing.loteId = item['loteId']
                # A coluna StatusConciliacao foi omitida (gerenciada via trigger de DB futuramente)
            else:
                novo = FaturamentoLote(
                    loteId=item['loteId'],
                    detalheId=item['detalheId'],
                    CodigoBeneficiario=item['CodigoBeneficiario'],
                    dataRealizacao=item['dataRealizacao'],
                    Guia=str(item['Guia']),
                    StatusConferencia=item['StatusConferencia'],
                    ValorProcedimento=item['ValorProcedimento']
                    # A coluna StatusConciliacao foi omitida (gerenciada via trigger de DB futuramente)
                )
                scraper.db.add(novo)
                
        scraper.db.commit()
    except Exception as e:
        scraper.db.rollback()
        raise RuntimeError(f"Database error persisting FaturamentoLotes: {e}")
    
    # Update job output
    return []

