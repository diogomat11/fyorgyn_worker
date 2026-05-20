import os
import sys
import time

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from core.webplan_client import WebPlanClient

def _wait_for_page_ready(driver, timeout=15):
    """Aguarda document.readyState == 'complete' e que a URL seja do FacPlan."""
    for _ in range(timeout):
        try:
            ready = driver.execute_script("return document.readyState;") == "complete"
            on_facplan = "facilinformatica" in driver.current_url.lower()
            if ready and on_facplan:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False

def _ensure_facplan_session(driver, scraper, job_id):
    """
    Garante que o browser esteja na página do FacPlan (FaturamentoAtendimentos) e com
    sessão autenticada. Tenta login caso necessário. Retorna True se bem-sucedido.
    """
    from selenium.common.exceptions import NoAlertPresentException

    faturamento_url = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/FaturamentoAtendimentos"

    # Fechar qualquer alerta pendente
    for _ in range(5):
        try:
            alert = driver.switch_to.alert
            scraper.log(f"OP7 - Fechando alerta: {alert.text}", level="WARN", job_id=job_id)
            alert.accept()
            time.sleep(1)
        except NoAlertPresentException:
            break

    # Navegar para a página de faturamento
    try:
        driver.get(faturamento_url)
    except Exception as e:
        scraper.log(f"OP7 - Aviso ao navegar (possível alerta bloqueando): {e}", level="WARN", job_id=job_id)
        try:
            driver.switch_to.alert.accept()
            driver.get(faturamento_url)
        except Exception:
            pass

    # Aguardar carregamento completo
    _wait_for_page_ready(driver, timeout=20)
    time.sleep(3)  # Tempo extra para cookies do FacPlan serem estabelecidos

    # Verificar se fomos redirecionados para login (sessão expirada)
    current = driver.current_url.lower()
    if "logon" in current or "login" in current or "facilinformatica" not in current:
        scraper.log("OP7 - Sessão expirada detectada. Refazendo login...", level="WARN", job_id=job_id)
        scraper.login()
        time.sleep(3)
        try:
            driver.get(faturamento_url)
        except Exception:
            pass
        _wait_for_page_ready(driver, timeout=20)
        time.sleep(3)

    final_url = driver.current_url.lower()
    if "facilinformatica" not in final_url:
        scraper.log(f"OP7 - Falha ao estabelecer sessão no FacPlan. URL atual: {driver.current_url}", level="ERROR", job_id=job_id)
        return False

    scraper.log(f"OP7 - Sessão FacPlan OK. URL: {driver.current_url}", job_id=job_id)
    return True

def run(scraper, job_data):
    """
    OP7 - Fat Facplan - IPASGO
    Objetivo: Submeter as contas conferidas ao processo de faturamento final (fechamento de lote)
    via API direta webplan_client.
    """
    driver = scraper.driver
    job_id = job_data.get("job_id")
    
    # Aceita tanto envio unitário quanto envio em lote (itens)
    itens_batch = job_data.get("itens", [])
    
    # Se não for array, transforma o unitário em um array de 1 item para reaproveitar a lógica
    if not itens_batch:
        detalhe_id = job_data.get("detalheId")
        status = job_data.get("status") or job_data.get("statusConferencia")
        data_realizacao = job_data.get("dataRealizacao")
        valor_procedimento = job_data.get("valorProcedimento", "")
        
        if detalhe_id and status and data_realizacao:
            itens_batch.append({
                "detalheId": detalhe_id,
                "status": status,
                "dataRealizacao": data_realizacao,
                "valorProcedimento": valor_procedimento
            })
            
    if not itens_batch:
        raise ValueError("Parâmetros detalheId, status e dataRealizacao (ou array 'itens') são obrigatórios na OP7.")

    scraper.log(f"OP7 - Faturamento Facplan iniciado para {len(itens_batch)} itens.", job_id=job_id)

    # 0. Garantir sessão FacPlan autenticada ANTES de criar o WebPlanClient
    if not _ensure_facplan_session(driver, scraper, job_id):
        raise RuntimeError("OP7 Falhou: não foi possível estabelecer sessão autenticada no FacPlan.")

    # 1. Criar client APÓS garantir sessão — cookies serão capturados com a sessão válida
    client = WebPlanClient(driver)
    
    sucesso_count = 0
    erro_count = 0
    from models import FaturamentoLote
    from datetime import datetime

    # 2. Executa requisições em loop
    for index, item in enumerate(itens_batch, 1):
        detalhe_id = item.get("detalheId")
        status = item.get("status")
        data_realizacao = item.get("dataRealizacao")
        valor_procedimento = item.get("valorProcedimento", "")
        
        if not detalhe_id:
            continue
            
        scraper.log(f"[{index}/{len(itens_batch)}] ModificarDetalhe para {detalhe_id} (Status: {status})...", job_id=job_id)
        
        try:
            client.modificar_detalhe(
                detalhe_id=detalhe_id,
                status=status,
                data_realizacao=data_realizacao,
                valor_procedimento=valor_procedimento
            )
            
            # Atualiza o banco de dados
            existing = scraper.db.query(FaturamentoLote).filter_by(detalheId=detalhe_id).first()
            if existing:
                existing.StatusConferencia = status
                if data_realizacao:
                    existing.dataRealizacao = datetime.strptime(data_realizacao, "%d/%m/%Y").date()
                scraper.db.commit()
            
            sucesso_count += 1
            
            # Atualiza contagem do Job a cada 100 itens para feedback visual
            if index % 100 == 0 and job_id:
                try:
                    # Tenta atualizar items_found (depende do scraper suportar)
                    from models import JobExecution
                    je = scraper.db.query(JobExecution).filter_by(job_id=job_id).first()
                    if je:
                        je.items_found = sucesso_count
                        scraper.db.commit()
                except:
                    pass
                
            time.sleep(0.5) # Delay conservador anti-ban
            
        except Exception as e:
            scraper.db.rollback()
            scraper.log(f"Falha no item {detalhe_id}: {e}", level="ERROR", job_id=job_id)
            erro_count += 1
            
    # Ao final atualiza contagem final
    if job_id:
        try:
            from models import JobExecution
            je = scraper.db.query(JobExecution).filter_by(job_id=job_id).first()
            if je:
                je.items_found = sucesso_count
                scraper.db.commit()
        except:
            pass
        
    scraper.log(f"OP7 Finalizada: {sucesso_count} sucessos, {erro_count} erros.", job_id=job_id)
    
    if erro_count > 0 and erro_count == len(itens_batch):
        raise RuntimeError("Todos os itens falharam no fechamento de faturamento.")
        
    return []

