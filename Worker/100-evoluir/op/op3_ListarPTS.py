import re
import urllib.parse

def clean_html(text):
    # Remove tags HTML e espaços sobressalentes
    cleaned = re.sub(r'<[^>]+>', ' ', text)
    return " ".join(cleaned.split()).strip()

def run(scraper, job_data):
    job_id = job_data.get("job_id")
    paciente = job_data.get("paciente") or job_data.get("paciente_nome") or job_data.get("nome_paciente")
    
    if not paciente:
        raise ValueError("O parâmetro 'paciente' (nome) é obrigatório para listar PTS!")
        
    scraper.log(f"Listando PTS para o paciente '{paciente}' no Evoluir...", job_id=job_id)
    
    # Codificar nome para query string
    search_query = urllib.parse.quote_plus(paciente)
    url = f"https://sistemaevoluir.com.br/painel/cadastros/ptscassi-ipasgo?per_page=10&search={search_query}"
    
    resp = scraper.session.get(url)
    if resp.status_code != 200:
        raise ConnectionError(f"Erro ao buscar PTS do paciente ({resp.status_code}): {resp.text[:200]}")
        
    html = resp.text
    
    # 1. Encontrar as linhas <tr> da tabela
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
    relatorios = []
    
    scraper.log(f"Processando {len(rows)} linhas da tabela de relatórios...", job_id=job_id)
    
    for row in rows:
        # Procurar pelo data-id do relatório
        id_match = re.search(r'data-id="([^"]+)"', row)
        if not id_match:
            continue  # Provavelmente linha de cabeçalho
            
        id_relatorio = id_match.group(1)
        
        # Extrair textos de todas as colunas <td>
        tds = [clean_html(td) for td in re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)]
        
        # Procurar por uma data formatada DD/MM/AAAA na linha
        data_match = re.search(r'\b(\d{2})/(\d{2})/(\d{4})\b', row)
        data_str = None
        if data_match:
            # Converter de DD/MM/AAAA para AAAA-MM-DD para o banco
            d, m, y = data_match.groups()
            data_str = f"{y}-{m}-{d}"
            
        # Determinar se tem Anexo II na linha
        has_anexo_ii = "imprimirAnexoII" in row
        
        # Identificar nome do profissional (primeiro td na linha)
        nome_prof_val = tds[0].strip() if len(tds) > 0 else None
        
        # Identificar nome do paciente na linha para verificação (geralmente primeiro ou segundo td)
        nome_na_linha = paciente
        if len(tds) > 1:
            # O nome do paciente geralmente está no primeiro ou segundo td
            # Vamos usar o mais longo ou o que contiver parte do nome
            for td_val in tds[:3]:
                if any(part.lower() in td_val.lower() for part in paciente.split()[:2]):
                    nome_na_linha = td_val
                    break
        
        # 2. Gerar registros de relatórios
        # A URL do PDF no Evoluir
        url_pts = f"https://sistemaevoluir.com.br/painel/cadastros/ptscassi-ipasgo/pdf/{id_relatorio}"
        relatorios.append({
            "id_relatorio": id_relatorio,
            "nome_paciente": nome_na_linha,
            "tipo_relatorio": "PTS",
            "url_arquivo": url_pts,
            "data": data_str,
            "nome_profissional": nome_prof_val
        })
        
        if has_anexo_ii:
            url_anexo2 = f"https://sistemaevoluir.com.br/painel/cadastros/ptscassi-ipasgo/pdf/ii/{id_relatorio}"
            relatorios.append({
                "id_relatorio": id_relatorio,
                "nome_paciente": nome_na_linha,
                "tipo_relatorio": "ANEXO-II",
                "url_arquivo": url_anexo2,
                "data": data_str,
                "nome_profissional": nome_prof_val
            })
            
    # Remover duplicados agrupando por (id_relatorio, tipo_relatorio)
    unique_relatorios = {}
    for r in relatorios:
        key = (r["id_relatorio"], r["tipo_relatorio"])
        unique_relatorios[key] = r
        
    result_list = list(unique_relatorios.values())
    scraper.log(f"Encontrados {len(result_list)} relatórios (PTS / Anexo II) para o paciente.", job_id=job_id)
    
    return result_list
