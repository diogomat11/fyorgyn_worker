import re
from bs4 import BeautifulSoup

def run(scraper, job_data):
    job_id = job_data.get("job_id")
    scraper.log("Iniciando importação do corpo clínico do Evoluir (OP5)...", job_id=job_id)
    
    # 1. Obter especialidades
    scraper.log("Buscando lista de especialidades...", job_id=job_id)
    resp_specs = scraper.session.get("https://sistemaevoluir.com.br/painel/cadastros/especialidades")
    if resp_specs.status_code != 200:
        raise ConnectionError(f"Erro ao buscar especialidades ({resp_specs.status_code}): {resp_specs.text[:200]}")
        
    soup_specs = BeautifulSoup(resp_specs.text, "html.parser")
    especialidades_map = {}
    for row in soup_specs.find_all("div", class_="user-row"):
        data_id = row.get("data-id")
        nome_div = row.find("div", class_="nome-usuario")
        if data_id and nome_div:
            especialidades_map[data_id] = nome_div.text.strip()
            
    scraper.log(f"Encontradas {len(especialidades_map)} especialidades.", job_id=job_id)
    
    # 2. Obter profissionais
    scraper.log("Buscando lista de profissionais (per_page=100)...", job_id=job_id)
    resp_profs = scraper.session.get("https://sistemaevoluir.com.br/painel/cadastros/profissionais?per_page=100")
    if resp_profs.status_code != 200:
        raise ConnectionError(f"Erro ao buscar profissionais ({resp_profs.status_code}): {resp_profs.text[:200]}")
        
    soup_profs = BeautifulSoup(resp_profs.text, "html.parser")
    profissionais = []
    
    for row in soup_profs.find_all("div", class_="user-row"):
        id_prof = row.get("data-id")
        if not id_prof:
            continue
            
        nome_prof = None
        btn = row.find("button", class_="btn-disponibilidade-grade")
        if btn:
            nome_prof = btn.get("data-nome")
        if not nome_prof:
            nome_span = row.find("span", class_="nome-usuario")
            if nome_span:
                nome_prof = nome_span.text.strip()
                
        cpf = None
        for span in row.find_all("span", class_="idade-usuario"):
            if "Documento:" in span.text:
                text_val = span.text.replace("Documento:", "").strip()
                cpf = " ".join(text_val.split()).strip()
                break
                
        profissionais.append({
            "id_profissional": id_prof,
            "nome_profissional": nome_prof,
            "cpf": cpf
        })
        
    scraper.log(f"Encontrados {len(profissionais)} profissionais na lista básica. Buscando detalhes...", job_id=job_id)
    
    # 3. Obter detalhes de cada profissional
    for idx, p in enumerate(profissionais, 1):
        id_prof = p["id_profissional"]
        scraper.log(f"[{idx}/{len(profissionais)}] Detalhando {p['nome_profissional']} ({id_prof})...", job_id=job_id)
        
        api_url = f"https://sistemaevoluir.com.br/api/usuario/{id_prof}?perfil=profissionais"
        resp_api = scraper.session.get(api_url)
        if resp_api.status_code != 200:
            scraper.log(f"Erro ao obter detalhes de {id_prof} ({resp_api.status_code})", level="WARN", job_id=job_id)
            p["registro"] = None
            p["especialidades"] = []
            continue
            
        try:
            detail = resp_api.json()
        except Exception as e:
            scraper.log(f"Erro ao decodificar JSON para {id_prof}: {e}", level="WARN", job_id=job_id)
            p["registro"] = None
            p["especialidades"] = []
            continue
            
        # Extrair apenas números do campo conselho
        conselho_raw = detail.get("conselho") or ""
        conselho_numbers = "".join(re.findall(r'\d+', str(conselho_raw)))
        p["registro"] = conselho_numbers if conselho_numbers else None
        
        # Mapear especialidades
        detail_specs = detail.get("especialidades") or []
        p_specs = []
        for spec_uuid in detail_specs:
            spec_name = especialidades_map.get(spec_uuid)
            if spec_name:
                p_specs.append(spec_name)
        p["especialidades"] = p_specs
        
    scraper.log("Processo de extração do corpo clínico concluído com sucesso!", job_id=job_id)
    return profissionais
