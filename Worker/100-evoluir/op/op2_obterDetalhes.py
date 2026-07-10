def run(scraper, job_data):
    job_id = job_data.get("job_id")
    id_paciente = job_data.get("id_paciente")
    
    if not id_paciente:
        raise ValueError("O parâmetro 'id_paciente' é obrigatório para obter detalhes!")
        
    scraper.log(f"Obtendo detalhes do paciente {id_paciente}...", job_id=job_id)
    
    url = f"https://sistemaevoluir.com.br/api/usuario/{id_paciente}?perfil=paciente"
    
    resp = scraper.session.get(url)
    if resp.status_code != 200:
        raise ConnectionError(f"Erro ao obter dados do paciente ({resp.status_code}): {resp.text[:200]}")
        
    data = resp.json()
    
    # 1. Extrair carteirinha de forma flexível (tenta vários campos comuns)
    carteirinha = (
        data.get("carteirinha") or 
        data.get("carteira") or 
        data.get("codigo_beneficiario") or 
        data.get("documento") or 
        data.get("matricula")
    )
    
    if not carteirinha and "dados" in data and isinstance(data["dados"], dict):
        carteirinha = (
            data["dados"].get("carteirinha") or 
            data["dados"].get("carteira") or 
            data["dados"].get("codigo_beneficiario")
        )
        
    if carteirinha:
        carteirinha = str(carteirinha).strip()
        
    # 2. Extrair patologia do array patologias
    patologia = None
    patologias_list = data.get("patologias") or (data.get("dados", {}).get("patologias") if isinstance(data.get("dados"), dict) else [])
    if patologias_list and isinstance(patologias_list, list):
        first_pat = patologias_list[0]
        if isinstance(first_pat, dict):
            patologia = first_pat.get("nome")
            
    if patologia:
        patologia = str(patologia).strip()
        
    result = {
        "id_paciente": id_paciente,
        "carteirinha": carteirinha,
        "patologia": patologia
    }
    
    scraper.log(f"Detalhes extraídos: carteirinha='{carteirinha}' patologia='{patologia}'", job_id=job_id)
    return result
