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
    
    # Mapeamento auxiliar de nomes de planos para IDs de convênios conhecidos
    CONVENIO_MAP = {
        "ipasgo": 6,
        "unimed": 3,
        "bradesco": 1,
        "cassi": 103,
        "amildental": 107,
        "amil": 107,
    }

    for part in parts[1:]:
        # O id_paciente é o conteúdo até a primeira aspa dupla
        id_paciente = part.split('"')[0]
        bloco_html = part.split('"', 1)[1]
        
        # O nome do paciente fica no primeiro <span class="nome-usuario">
        nome_match = re.search(r'class="nome-usuario"[^>]*>\s*([^<]+)', bloco_html)
        if not nome_match:
            continue
            
        nome_paciente = " ".join(nome_match.group(1).strip().split())
        
        # Extrair Plano se disponível
        plano = ""
        plano_match = re.search(r'Plano:\s*([^<\n\r]+)', bloco_html, re.IGNORECASE)
        if plano_match:
            plano = plano_match.group(1).strip()
            
        # Determinar id_convenio padrão a partir do plano (padrão IPASGO 6 se contiver ipasgo)
        id_convenio = 6  # fallback IPASGO
        plano_lower = plano.lower()
        for k, conv_id in CONVENIO_MAP.items():
            if k in plano_lower:
                id_convenio = conv_id
                break

        pacientes_extraidos.append({
            "id_paciente": id_paciente,
            "paciente": nome_paciente,
            "plano": plano,
            "id_convenio": id_convenio
        })
            
    scraper.log(f"Total de pacientes encontrados (todos os planos): {len(pacientes_extraidos)}", job_id=job_id)
    
    # Retorna o resultado final de pacientes encontrados para o dispatcher salvar
    return pacientes_extraidos
