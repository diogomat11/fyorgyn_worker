import os
import sys

_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from core.webplan_client import WebPlanClient

def run(scraper, job_data):
    """
    OP13 - Criar Lote de Faturamento - IPASGO
    Consome a API SalvarLote e persiste no banco o numero do lote.
    """
    driver = scraper.driver
    job_id = job_data.get("job_id")
    cod_prestador = job_data.get("cod_prestador")
    data_fim = job_data.get("data_fim")
    id_lote_interno = job_data.get("id_lote_interno")
    
    scraper.log(f"OP13 - Iniciando criação de Lote via WebPlan API...", job_id=job_id)
    
    if not cod_prestador or not data_fim:
        raise ValueError("Parâmetros cod_prestador e data_fim são obrigatórios na OP13.")

    # 1. Garante navegação inicial
    faturamento_url = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/FaturamentoAtendimentos"
    scraper.log(f"OP13 - Navegando para URL de Faturamento: {faturamento_url}", job_id=job_id)
    driver.get(faturamento_url)
    
    from time import sleep
    sleep(3)
    
    client = WebPlanClient(driver)
    
    scraper.log(f"OP13 - Enviando requisição para criar lote (Prestador {cod_prestador}, Fim {data_fim})", job_id=job_id)
    response_data = client.criar_novo_lote(codigo_prestador=cod_prestador, data_fim=data_fim)
    
    scraper.log(f"OP13 - Resposta: {response_data}", job_id=job_id)
    
    # Extrair LoteId retornado pela API (ajustar conforme payload real retornado pelo Facil)
    # Supondo que retorne {"LoteId": 1234}
    lote_id_api = None
    if isinstance(response_data, dict):
        lote_id_api = response_data.get("LoteId") or response_data.get("loteId") or response_data.get("Id")
        
    if not lote_id_api:
        # Se não retornar um ID óbvio, talvez precisemos fazer um refresh e buscar o último lote aberto
        scraper.log("Aviso: LoteId não encontrado na resposta direta. É recomendável implementar busca do lote recém criado.", level="WARN", job_id=job_id)
    else:
        scraper.log(f"OP13 - Lote criado com sucesso no IPASGO: {lote_id_api}", job_id=job_id)
    
    # Atualiza o banco local
    if id_lote_interno:
        try:
            from models import LoteConvenio
            lote_obj = scraper.db.query(LoteConvenio).filter_by(id_lote=id_lote_interno).first()
            if lote_obj:
                if lote_id_api:
                    lote_obj.numero_lote = lote_id_api
                lote_obj.status = "Aberto"
                scraper.db.commit()
                scraper.log(f"Banco local atualizado com sucesso. Lote interno {id_lote_interno}", job_id=job_id)
            else:
                scraper.log(f"Lote interno {id_lote_interno} não encontrado na base.", level="WARN", job_id=job_id)
        except Exception as e:
            scraper.db.rollback()
            scraper.log(f"Falha ao atualizar LoteConvenio local: {e}", level="ERROR", job_id=job_id)

    return [{"lote_id_api": lote_id_api}]
