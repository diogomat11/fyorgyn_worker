import os
import sys
import json

_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from core.webplan_client import WebPlanClient

def run(scraper, job_data):
    """
    OP13 - Criar Lote de Faturamento - IPASGO (Fire-and-Forget)
    Envia a requisição GerarLote ao WebPlan e retorna imediatamente.
    Cria um Job OP13_poll para monitorar quando o lote estiver pronto.
    """
    driver = scraper.driver
    job_id = job_data.get("job_id")
    cod_prestador = job_data.get("cod_prestador") or job_data.get("codigoPrestador") or getattr(scraper, "cod_prestador", "")
    data_fim = job_data.get("data_fim")
    id_lote_interno = job_data.get("id_lote_interno")
    
    scraper.log(f"OP13 - Iniciando criação de Lote via WebPlan API...", job_id=job_id)
    
    if not cod_prestador or not data_fim:
        raise ValueError("Parâmetros cod_prestador e data_fim são obrigatórios na OP13.")

    # 1. Navegação inicial
    faturamento_url = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/FaturamentoAtendimentos"
    scraper.log(f"OP13 - Navegando para URL de Faturamento: {faturamento_url}", job_id=job_id)
    
    try:
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(driver, 2).until(EC.alert_is_present())
        driver.switch_to.alert.accept()
    except:
        pass
        
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
    
    for _ in range(10):
        try:
            if driver.execute_script("return document.readyState;") == "complete":
                break
        except:
            pass
        sleep(1)
    sleep(3)
    
    client = WebPlanClient(driver)
    
    # 2. Enviar requisição GerarLote (fire-and-forget)
    scraper.log(f"OP13 - Enviando requisição GerarLote (Prestador {cod_prestador}, Fim {data_fim})", job_id=job_id)
    try:
        response_data = client.gerar_lote(codigo_prestador=cod_prestador, data_fim=data_fim)
        scraper.log(f"OP13 - Resposta GerarLote: {response_data}", job_id=job_id)
    except Exception as e:
        if "API Error GerarLote" in str(e):
            raise Exception(f"OP13 Falhou ao Gerar Lote: {e}")
        scraper.log(f"Aviso ao chamar GerarLote: {e}. Poll job verificará.", level="WARN", job_id=job_id)
    
    # 3. Atualizar LoteConvenio para status "Criando"
    if id_lote_interno:
        try:
            from models import LoteConvenio
            lote_obj = scraper.db.query(LoteConvenio).filter_by(id_lote=id_lote_interno).first()
            if lote_obj:
                lote_obj.status = "Criando"
                scraper.db.commit()
                scraper.log(f"OP13 - LoteConvenio {id_lote_interno} atualizado para 'Criando'", job_id=job_id)
        except Exception as e:
            scraper.db.rollback()
            scraper.log(f"Falha ao atualizar LoteConvenio: {e}", level="ERROR", job_id=job_id)
    
    # 4. Criar Job OP13_poll para monitorar a conclusão
    try:
        from models import Job
        convenio_id = 6
        if id_lote_interno:
            from models import LoteConvenio
            lote_obj = scraper.db.query(LoteConvenio).filter_by(id_lote=id_lote_interno).first()
            if lote_obj:
                convenio_id = lote_obj.id_convenio

        # Formata data_fim para ISO (01/05/2026 -> 2026-05-01)
        parts = data_fim.split('/')
        data_fim_iso = f"{parts[2]}-{parts[1]}-{parts[0]}" if len(parts) == 3 else data_fim

        poll_params = {
            "cod_prestador": cod_prestador,
            "data_fim": data_fim,
            "data_fim_iso": data_fim_iso,
            "id_lote_interno": id_lote_interno,
            "poll_attempt": 0
        }
        
        new_job = Job(
            id_convenio=convenio_id,
            rotina="13_poll",
            params=json.dumps(poll_params),
            status="pending",
            priority=10,
            user_id=getattr(scraper, 'user_id', None)
        )
        scraper.db.add(new_job)
        scraper.db.commit()
        scraper.log(f"OP13 - Job OP13_poll criado. Monitoramento iniciado.", job_id=job_id)
    except Exception as e:
        scraper.db.rollback()
        scraper.log(f"Falha ao criar Job OP13_poll: {e}", level="ERROR", job_id=job_id)

    scraper.log(f"OP13 - Requisição enviada com sucesso. Worker liberado.", job_id=job_id)
    return {"self_persisted": True, "inserted": 0, "updated": 0, "total": 0}

