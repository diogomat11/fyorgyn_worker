import os
import sys
import json

_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from core.webplan_client import WebPlanClient

def run(scraper, job_data):
    """
    OP13_poll - Polling de criação de Lote (execução rápida ~5s)
    Verifica LoadLotes UMA vez. Se lote pronto -> atualiza banco + cria Job OP6.
    Se ainda processando -> cria outro Job OP13_poll (auto-retry sem limite).
    """
    driver = scraper.driver
    job_id = job_data.get("job_id")
    cod_prestador = job_data.get("cod_prestador") or job_data.get("codigoPrestador") or getattr(scraper, "cod_prestador", "")
    data_fim = job_data.get("data_fim")
    data_fim_iso = job_data.get("data_fim_iso", "")
    id_lote_interno = job_data.get("id_lote_interno")
    poll_attempt = int(job_data.get("poll_attempt", 0))
    
    scraper.log(f"OP13_poll - Tentativa #{poll_attempt + 1} para Lote interno {id_lote_interno}. Aguardando 1 minuto...", job_id=job_id)
    from time import sleep
    sleep(60)
    
    if not cod_prestador:
        raise ValueError("Parâmetro cod_prestador é obrigatório no OP13_poll.")

    # 1. Navegação para o WebPlan (necessária para cookies da API)
    faturamento_url = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/FaturamentoAtendimentos"
    
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
    sleep(2)
    
    # Fechar possíveis notificações
    try:
        btn1 = driver.find_elements("id", "button-1")
        if btn1 and btn1[0].is_displayed():
            driver.execute_script("arguments[0].click();", btn1[0])
        notys = driver.find_elements("css selector", ".noty_close")
        for noty in notys:
            if noty.is_displayed():
                driver.execute_script("arguments[0].click();", noty)
    except:
        pass
    
    # 2. Verifica LoadLotes UMA vez
    client = WebPlanClient(driver)
    scraper.log(f"OP13_poll - Consultando LoadLotes (Prestador: {cod_prestador})...", job_id=job_id)
    
    lotes_data = client.load_lotes(codigo_prestador=cod_prestador)
    
    lote_id_api = None
    status_atual = "desconhecido"
    
    if isinstance(lotes_data, dict):
        permite_gerar = lotes_data.get("PermiteGerarLote", True)
        lotes_list = lotes_data.get("Lotes", [])
        
        if lotes_list:
            primeiro_lote = lotes_list[0]
            data_final_lote = primeiro_lote.get("DataFinal", "")
            status_desc = primeiro_lote.get("StatusDescricao", "")
            status_atual = status_desc
            
            # Lote pronto: "Aguardando Envio"
            if status_desc == "Aguardando Envio":
                lote_id_api = primeiro_lote.get("Id")
                scraper.log(f"OP13_poll - Lote gerado! ID: {lote_id_api}, Status: {status_desc}", job_id=job_id)
            
            # Fallback: DataFinal bate e não está mais em processamento
            elif data_fim_iso and data_fim_iso in data_final_lote and status_desc not in ["Criando lote", "Carregando lote"]:
                lote_id_api = primeiro_lote.get("Id")
                scraper.log(f"OP13_poll - Lote detectado via DataFinal match! ID: {lote_id_api}, Status: {status_desc}", job_id=job_id)
            else:
                scraper.log(f"OP13_poll - Lote ainda processando. Status: {status_desc}. PermiteGerar: {permite_gerar}", job_id=job_id)
        else:
            scraper.log(f"OP13_poll - Nenhum lote encontrado. PermiteGerar: {permite_gerar}", job_id=job_id)
    else:
        scraper.log(f"OP13_poll - Resposta inesperada do LoadLotes: {type(lotes_data)}", level="WARN", job_id=job_id)
    
    # 3. Retornar status do lote encontrado ou processando
    if lote_id_api:
        scraper.log(f"OP13_poll - Lote pronto! ID: {lote_id_api}", job_id=job_id)
        return {
            "status": "ready",
            "lote_id_api": lote_id_api,
            "id_lote_interno": id_lote_interno,
            "cod_prestador": cod_prestador
        }
    
    scraper.log(f"OP13_poll - Lote ainda processando (status atual: {status_atual})", job_id=job_id)
    return {
        "status": "processing",
        "lote_id_api": None,
        "id_lote_interno": id_lote_interno,
        "cod_prestador": cod_prestador,
        "poll_attempt": poll_attempt
    }
