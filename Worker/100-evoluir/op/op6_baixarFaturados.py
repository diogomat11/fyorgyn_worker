import time
import re
from bs4 import BeautifulSoup

def run(scraper, job_data):
    job_id = job_data.get("job_id")
    
    # 1. Obter parâmetros do job
    plano_saude_id = job_data.get("plano_saude_id", "18afb174-a2c2-49ee-93d2-d6e4868817bc")
    data_inicial = job_data.get("data_inicial")
    data_final = job_data.get("data_final")
    paciente_id = job_data.get("paciente_id", 0)
    form_subiu_a_guia = job_data.get("form_subiu_a_guia", "sim")
    
    if not data_inicial or not data_final:
        raise ValueError("Os parâmetros 'data_inicial' e 'data_final' são obrigatórios!")
        
    scraper.log(
        f"Iniciando op6_baixarFaturados: plano_saude_id={plano_saude_id}, "
        f"data_inicial={data_inicial}, data_final={data_final}", 
        job_id=job_id
    )
    
    # 2. Requisitar a URL do relatório de guias que subiram usando o navegador (Selenium)
    url_relatorio = (
        f"https://sistemaevoluir.com.br/painel/relatorios/guias-subiram?"
        f"paciente_id={paciente_id}&plano_saude_id={plano_saude_id}&"
        f"form_subiu_a_guia={form_subiu_a_guia}&data_inicial={data_inicial}&data_final={data_final}"
    )
    
    scraper.log(f"Navegando via navegador (Selenium) para a URL: {url_relatorio}", job_id=job_id)
    try:
        scraper.driver.get(url_relatorio)
    except Exception as e:
        scraper.log(f"Erro ao carregar URL no navegador: {e}", level="ERROR", job_id=job_id)
        raise ConnectionError(f"Falha ao abrir a URL no Chrome: {e}")
        
    # Aguardar o carregamento da tabela
    scraper.log("Aguardando carregamento da tabela de guias na pagina...", job_id=job_id)
    time.sleep(3) # Delay inicial
    
    tbody_loaded = False
    data_ids = []
    
    for attempt in range(8): # Aguarda ate 40 segundos no total
        html_source = scraper.driver.page_source
        
        # Usar regex super rapido para extrair o tbody
        tbody_match = re.search(r'<tbody[^>]*>(.*?)</tbody>', html_source, re.DOTALL | re.IGNORECASE)
        if tbody_match:
            tbody_content = tbody_match.group(1)
            # Extrair data-ids que sao UUIDs do tbody
            uuid_pattern = r'data-id="([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})"'
            temp_ids = re.findall(uuid_pattern, tbody_content)
            
            if len(temp_ids) > 0:
                data_ids = temp_ids
                tbody_loaded = True
                scraper.log(f"Tabela carregada com sucesso! Encontradas {len(data_ids)} guias.", job_id=job_id)
                break
            
        scraper.log(f"Tabela nao carregada ainda (tentativa {attempt + 1}/8). Aguardando...", job_id=job_id)
        time.sleep(5)
        
    if not tbody_loaded:
        scraper.log("Aviso: Tempo limite atingido para carregamento da tabela, ou nao existem guias registradas.", level="WARN", job_id=job_id)
        
    # 3. Sincronizar cookies e CSRF do Selenium para requests.Session
    scraper.log("Sincronizando cookies e tokens da sessao do navegador para chamadas HTTP...", job_id=job_id)
    try:
        selenium_cookies = scraper.driver.get_cookies()
        scraper.session.cookies.clear()
        xsrf_token_val = None
        for cookie in selenium_cookies:
            scraper.session.cookies.set(cookie['name'], cookie['value'])
            if cookie['name'] == 'XSRF-TOKEN':
                import urllib.parse
                xsrf_token_val = urllib.parse.unquote(cookie['value'])
                
        if xsrf_token_val:
            scraper.session.headers.update({"X-XSRF-TOKEN": xsrf_token_val})
            
        # Extrair CSRF token atual da pagina
        html_source = scraper.driver.page_source
        token_match = re.search(r'name="_token"\s+value="([^"]+)"', html_source)
        if not token_match:
            token_match = re.search(r'csrf-token"\s+content="([^"]+)"', html_source)
            
        if token_match:
            scraper.csrf_token = token_match.group(1)
            scraper.log(f"Token CSRF atualizado: {scraper.csrf_token[:10]}...", job_id=job_id)
            
        # Extrair token window.dashboardAuthHeader
        auth_token = scraper.driver.execute_script("return window.dashboardAuthHeader || '';")
        if auth_token:
            scraper.auth_token = auth_token
            scraper.session.headers.update({"Authorization": auth_token})
            
    except Exception as e:
        scraper.log(f"Aviso ao sincronizar cookies/tokens: {e}", level="WARN", job_id=job_id)

    # Garantir IDs únicos mantendo a ordem
    data_ids = list(dict.fromkeys(data_ids))
    total_guias = len(data_ids)
    
    scraper.log(f"Total de data-ids únicos encontrados: {total_guias}", job_id=job_id)
    
    if total_guias == 0:
        scraper.log("Nenhuma guia encontrada no relatório com os filtros aplicados.", job_id=job_id)
        return {
            "status": "success",
            "message": "Nenhuma guia encontrada para faturar",
            "guias_encontradas": 0,
            "guias_atualizadas": 0,
            "falhas": 0,
            "detalhes": []
        }
        
    # 4. Enfileirar requisição POST para cada data-id
    sucessos = 0
    falhas = 0
    resultados = []
    
    # Headers adicionais para requisições de gravação AJAX do Laravel/SPA
    post_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if scraper.csrf_token:
        post_headers["X-CSRF-TOKEN"] = scraper.csrf_token
        
    for idx, d_id in enumerate(data_ids, 1):
        url_post = f"https://sistemaevoluir.com.br/painel/guias/atualizar-status-faturado/{d_id}"
        scraper.log(f"[{idx}/{total_guias}] Atualizando guia faturada: data-id={d_id}...", job_id=job_id)
        
        try:
            # POST enviando {"faturado": "Sim"} como JSON
            resp_post = scraper.session.post(url_post, json={"faturado": "Sim"}, headers=post_headers, timeout=15)
            
            if resp_post.status_code in [200, 201, 204]:
                sucessos += 1
                resultados.append({"data_id": d_id, "status": "success", "status_code": resp_post.status_code})
            else:
                falhas += 1
                scraper.log(f"Falha ao atualizar guia {d_id}. HTTP {resp_post.status_code}: {resp_post.text[:200]}", level="WARN", job_id=job_id)
                resultados.append({"data_id": d_id, "status": "failed", "status_code": resp_post.status_code, "error": resp_post.text[:200]})
                
        except Exception as e:
            falhas += 1
            scraper.log(f"Exceção ao enviar atualização da guia {d_id}: {e}", level="WARN", job_id=job_id)
            resultados.append({"data_id": d_id, "status": "error", "error": str(e)})
            
        # Pequeno delay entre requisições para evitar detecção de flood / sobrecarga do servidor
        time.sleep(0.2)
        
    scraper.log(
        f"Processo de faturamento concluído! Total: {total_guias}, Sucessos: {sucessos}, Falhas: {falhas}", 
        job_id=job_id
    )
    
    return {
        "status": "success",
        "message": f"Faturamento processado. Sucessos: {sucessos}, Falhas: {falhas}",
        "guias_encontradas": total_guias,
        "guias_atualizadas": sucessos,
        "falhas": falhas,
        "detalhes": resultados
    }
