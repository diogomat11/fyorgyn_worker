import os
import sys
import logging
import time
from sqlalchemy.dialects.postgresql import insert

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from core.webplan_client import WebPlanClient

try:
    from models import Guias, GuiaIpasgo  # Replace with actual model used in worker
except ImportError:
    backend_path = os.path.join(os.path.dirname(os.path.dirname(_mod_root)), 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    # from models import ...

def run(scraper, job_data):
    """
    OP11 - Importar Guias via API HTTP - IPASGO
    Substitui a extração via Selenium mantendo o uso da sessão da OP0.
    """
    driver = scraper.driver
    job_id = job_data.get("job_id")
    
    # Extração de parâmetros
    codigo_prestador = job_data.get("codigoPrestador", "")
    carteira = job_data.get("carteira", "")
    codigo_beneficiario = job_data.get("codigoBeneficiario", "")
    guia_str = job_data.get("guia", "")
    data_ini = job_data.get("data_ini", "")
    data_fim = job_data.get("data_fim", "")
    situacao = job_data.get("situacao", "")
    
    scraper.log("OP11 - Iniciando extração de guias via API (WebPlanClient)...", job_id=job_id)
    
    # 1. Navegação de Bootstrap (Garante que os cookies do módulo GuiasTISS sejam inicializados)
    url_bootstrap = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos"
    scraper.log(f"OP11 - Acessando URL Bootstrap para setup de contexto: {url_bootstrap}", job_id=job_id)
    driver.get(url_bootstrap)
    time.sleep(3) # Wait for redirects / cookies
    
    # 2. Inicialização do Client
    client = WebPlanClient(driver)
    
    current_page = 1
    has_next_page = True
    todas_guias_extraidas = []
    
    scraper.log("OP11 - Iniciando loop de paginação...", job_id=job_id)
    
    while has_next_page:
        scraper.log(f"Consultando página {current_page}...", job_id=job_id)
        
        response_json = client.post_consultar_guias(
            page=current_page,
            codigo_prestador=codigo_prestador,
            guia=guia_str,
            data_ini=data_ini,
            data_fim=data_fim,
            carteira=carteira,
            codigo_beneficiario=codigo_beneficiario,
            situacao=situacao
        )
        
        procedimentos = response_json.get("Procedimentos", [])
        
        if not procedimentos or len(procedimentos) == 0:
            scraper.log(f"Página {current_page} retornou 0 procedimentos. Fim da extração.", job_id=job_id)
            has_next_page = False
            break
        
        scraper.log(f"Extraídos {len(procedimentos)} procedimentos da página {current_page}", job_id=job_id)
        
        for item in procedimentos:
            # 3. Normalização
            chaves = item.get("ChavesUtLib", [])
            numero_guia = chaves[0] if chaves else None
            
            situacoes = item.get("Situacoes", [])
            situacao_tiss = situacoes[0] if situacoes else None
            
            has_senha = item.get("HasSenha", False)
            
            # Regra Refinada: Necessita Senha
            estados_aprovados = ["Autorizado", "Liberado", "Parcialmente autorizada"]
            necessita_senha = False
            if situacao_tiss in estados_aprovados and has_senha == False:
                necessita_senha = True
                
            guia_normalizada = {
                "codigo_beneficiario": item.get("CodigoBenficiario"),
                "nome_beneficiario": item.get("NomeBeneficiario"),
                "codigo_prestador": item.get("CodigoPrestador"),
                "nome_prestador": item.get("NomePrestador"),
                "numero_guia": numero_guia,
                "situacao": situacao_tiss,
                "necessita_senha": necessita_senha,
                "has_senha": has_senha,
                "codigo_amb": item.get("CodigoAMB"),
                "email_beneficiario": item.get("EmailBeneficiario")
            }
            todas_guias_extraidas.append(guia_normalizada)
        
        current_page += 1
        
    scraper.log(f"OP11 - Extração concluída. Total de guias capturadas: {len(todas_guias_extraidas)}", job_id=job_id)
    
    # 4. TODO: Implementação de banco de dados (Upsert bulk) - Depends on mapping the exact SQLAlchemy Model
    # for guia in todas_guias_extraidas:
    #     scraper.db.merge(GuiaIPASGO(...)) 
    # scraper.db.commit()
    
    return todas_guias_extraidas
