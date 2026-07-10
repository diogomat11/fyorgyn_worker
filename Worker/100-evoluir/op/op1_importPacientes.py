import re

def run(scraper, job_data):
    job_id = job_data.get("job_id")
    scraper.log("Iniciando extração de pacientes no Evoluir...", job_id=job_id)
    
    url = "https://sistemaevoluir.com.br/painel/cadastros/pacientes?per_page=500"
    
    # 1. Requisição GET com a sessão logada
    resp = scraper.session.get(url)
    if resp.status_code != 200:
        raise ConnectionError(f"Erro ao acessar listagem de pacientes ({resp.status_code}): {resp.text[:200]}")
        
    html = resp.text
    
    # 2. Parsing das linhas de pacientes usando split e regex
    # Cada bloco de paciente começa com 'data-id="'
    parts = html.split('data-id="')
    pacientes_extraidos = []
    
    scraper.log(f"Processando {len(parts) - 1} registros potenciais do HTML...", job_id=job_id)
    
    for part in parts[1:]:
        # O id_paciente é o conteúdo até a primeira aspa dupla
        id_paciente = part.split('"')[0]
        bloco_html = part.split('"', 1)[1]
        
        # O nome do paciente fica no primeiro <span class="nome-usuario">
        # Mas vamos filtrar as tags child se houver
        nome_match = re.search(r'class="nome-usuario"[^>]*>\s*([^<]+)', bloco_html)
        if not nome_match:
            continue
            
        nome_paciente = nome_match.group(1).strip()
        
        # Filtro de Plano = Ipasgo
        # O HTML tem label "Plano:" e valor "Ipasgo" em seguida no mesmo bloco
        is_ipasgo = False
        plano_match = re.search(r'Plano:.*?Ipasgo', bloco_html, re.DOTALL | re.IGNORECASE)
        if plano_match:
            is_ipasgo = True
            
        if is_ipasgo:
            # Limpeza do nome do paciente contra espaços extras
            nome_paciente = " ".join(nome_paciente.split())
            
            pacientes_extraidos.append({
                "id_paciente": id_paciente,
                "paciente": nome_paciente,
                "id_convenio": 6 # IPASGO
            })
            
    scraper.log(f"Total de pacientes IPASGO encontrados: {len(pacientes_extraidos)}", job_id=job_id)
    
    # Retorna o resultado final de pacientes encontrados para o dispatcher salvar
    return pacientes_extraidos
