import os
import sys

_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from core.webplan_client import WebPlanClient

def run(scraper, job_data):
    """
    OP14 - Cancelar Lote de Faturamento - IPASGO
    Consome a API CancelarLote e reflete o status no banco local, além de manter os itens bloqueados.
    """
    driver = scraper.driver
    job_id = job_data.get("job_id")
    cod_prestador = job_data.get("cod_prestador") or job_data.get("codigoPrestador") or getattr(scraper, "cod_prestador", "")
    numero_lote = job_data.get("numero_lote")
    id_lote_interno = job_data.get("id_lote_interno")
    
    scraper.log(f"OP14 - Iniciando cancelamento de Lote ({numero_lote}) via API...", job_id=job_id)
    
    if not cod_prestador or not numero_lote:
        raise ValueError("Parâmetros cod_prestador e numero_lote são obrigatórios na OP14.")

    # 1. Garante navegação inicial
    faturamento_url = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/FaturamentoAtendimentos"
    scraper.log(f"OP14 - Navegando para URL de Faturamento: {faturamento_url}", job_id=job_id)
    
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
    
    from time import sleep
    
    # Aguardar carregamento completo da página
    for _ in range(10):
        try:
            if driver.execute_script("return document.readyState;") == "complete":
                break
        except:
            pass
        sleep(1)
    sleep(3)
    
    client = WebPlanClient(driver)
    
    scraper.log(f"OP14 - Enviando requisição para cancelar lote {numero_lote}", job_id=job_id)
    response_data = client.cancelar_lote(numero_lote=numero_lote, codigo_prestador=cod_prestador)
    
    scraper.log(f"OP14 - Resposta de cancelamento: {response_data}", job_id=job_id)
    
    # Atualiza o banco local
    try:
        from models import LoteConvenio, FaturamentoLote
        if id_lote_interno:
            lote_obj = scraper.db.query(LoteConvenio).filter_by(id_lote=id_lote_interno).first()
            if lote_obj:
                lote_obj.status = "Cancelado"
        else:
            lote_obj = scraper.db.query(LoteConvenio).filter_by(numero_lote=numero_lote).first()
            if lote_obj:
                lote_obj.status = "Cancelado"

        # Garante que todos os itens deste lote fiquem marcados como bloqueados/cancelados
        items = scraper.db.query(FaturamentoLote).filter_by(id_lote=lote_obj.id_lote).all() if lote_obj else []
        for item in items:
            item.StatusConciliacao = "bloqueado"

        scraper.db.commit()
        scraper.log(f"Banco local atualizado com sucesso. Lote {numero_lote} cancelado.", job_id=job_id)
    except Exception as e:
        scraper.db.rollback()
        scraper.log(f"Falha ao atualizar status de cancelamento local: {e}", level="ERROR", job_id=job_id)

    return [{"numero_lote": numero_lote, "status": "Cancelado"}]
