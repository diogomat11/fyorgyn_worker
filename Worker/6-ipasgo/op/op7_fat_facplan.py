import os
import sys

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from core.webplan_client import WebPlanClient

def run(scraper, job_data):
    """
    OP7 - Fat Facplan - IPASGO
    Objetivo: Submeter as contas conferidas ao processo de faturamento final (fechamento de lote)
    via API direta webplan_client.
    """
    driver = scraper.driver
    job_id = job_data.get("job_id")
    
    # Parâmetros necessários para a OP7
    # Geralmente processa um único detalheId por job, ou recebe uma lista no params.
    # Exemplo: { "detalheId": 1234, "status": 67, "dataRealizacao": "25/08/2025" }
    detalhe_id = job_data.get("detalheId")
    status = job_data.get("status") or job_data.get("statusConferencia")
    data_realizacao = job_data.get("dataRealizacao")
    valor_procedimento = job_data.get("valorProcedimento", "")
    
    scraper.log(f"OP7 - Faturamento Facplan iniciado para detalheId {detalhe_id}", job_id=job_id)
    
    if not detalhe_id or not status or not data_realizacao:
        raise ValueError("Parâmetros detalheId, status e dataRealizacao são obrigatórios na OP7.")

    # 0. Garante navegação inicial para a página de faturamento conforme fluxo da OP6
    faturamento_url = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/FaturamentoAtendimentos"
    scraper.log(f"OP7 - Navegando para URL base: {faturamento_url}", job_id=job_id)
    driver.get(faturamento_url)
    
    from time import sleep
    sleep(3) # Wait for page and cookies to settle

    # 1. Garante sessão ativa recuperando cookies
    client = WebPlanClient(driver)
    
    # 2. Executa requisição
    scraper.log(f"Enviando ModificarDetalhe para {detalhe_id} (Status: {status})...", job_id=job_id)
    response_data = client.modificar_detalhe(
        detalhe_id=detalhe_id,
        status=status,
        data_realizacao=data_realizacao,
        valor_procedimento=valor_procedimento
    )
    
    # 3. Validação de sucesso
    scraper.log(f"Detalhe {detalhe_id} faturado com sucesso na API IPASGO.", job_id=job_id)
    
    # Atualiza o banco de dados conforme regra do projeto
    try:
        from models import FaturamentoLote
        from datetime import datetime
        existing = scraper.db.query(FaturamentoLote).filter_by(detalheId=detalhe_id).first()
        if existing:
            existing.StatusConferencia = status
            if data_realizacao:
                # API format requested dd/mm/yyyy
                existing.dataRealizacao = datetime.strptime(data_realizacao, "%d/%m/%Y").date()
            scraper.db.commit()
            scraper.log(f"Banco local atualizado com sucesso. StatusConferencia={status}", job_id=job_id)
        else:
            scraper.log(f"Atenção: detalheId {detalhe_id} não encontrado na tabela faturamento_lotes local.", level="WARN", job_id=job_id)
    except Exception as e:
        scraper.db.rollback()
        scraper.log(f"Falha ao persistir status modificado no banco: {e}", level="ERROR", job_id=job_id)
    
    return []

