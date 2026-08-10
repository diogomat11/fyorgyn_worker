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



def run(scraper, job_data):
    """
    OP6 - Check Baixados - IPASGO
    Consome a API LoadDetalhes via requests.Session autenticado e persiste no banco (Upsert).
    """
    driver = scraper.driver
    job_id = job_data.get("job_id")
    # Changed from loteId to numero_lote to match DB nomenclature
    numero_lote = job_data.get("numero_lote", job_data.get("loteId")) 
    codigo_prestador = job_data.get("codigoPrestador", "").strip() or job_data.get("cod_prestador", "").strip() or job_data.get("prestador", "").strip() or getattr(scraper, "cod_prestador", "")
    
    if not codigo_prestador:
        raise ValueError("O código do prestador não foi informado (payload vazio) e não foi encontrado na tabela user_convenios.")
    
    scraper.log(f"OP6 - Iniciando extração (Lote: {numero_lote}) via WebPlan API...", job_id=job_id)
    
    if not numero_lote:
        raise ValueError("O parâmetro 'numero_lote' é obrigatório para a OP6.")

    # 1. Garante navegação inicial para a página de faturamento conforme solicitado
    faturamento_url = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/FaturamentoAtendimentos"
    scraper.log(f"OP6 - Navegando para URL de Faturamento: {faturamento_url}", job_id=job_id)
    
    # Fechar possíveis alertas antes de navegar
    try:
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(driver, 2).until(EC.alert_is_present())
        driver.switch_to.alert.accept()
    except:
        pass
        
    # Aguarda a aba do WebPlan estabilizar após o login (SSO) antes de forçar a URL
    from time import sleep
    for _ in range(10):
        try:
            if driver.execute_script("return document.readyState;") == "complete":
                if "facilinformatica" in driver.current_url.lower():
                    break
        except:
            pass
        sleep(1)
        
    try:
        driver.get(faturamento_url)
    except Exception as e:
        scraper.log(f"Aviso ao navegar (pode ser alert block): {e}", level="WARN", job_id=job_id)
        try:
            driver.switch_to.alert.accept()
            driver.get(faturamento_url)
        except:
            pass
    
    # 2. Init Client and extract Session
    from time import sleep
    
    # Aguardar carregamento completo da página
    for _ in range(10):
        try:
            if driver.execute_script("return document.readyState;") == "complete":
                break
        except:
            pass
        sleep(1)
    
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
    
    return all_items
