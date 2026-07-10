def run(scraper, job_data):
    job_id = job_data.get("job_id")
    id_relatorio = job_data.get("id_relatorio")
    nova_data = job_data.get("data") # Formato esperado: DD/MM/AAAA
    
    if not id_relatorio or not nova_data:
        raise ValueError("Os parâmetros 'id_relatorio' e 'data' (DD/MM/AAAA) são obrigatórios!")
        
    scraper.log(f"Iniciando atualização de data do PTS {id_relatorio} para '{nova_data}'...", job_id=job_id)
    
    # 1. Obter dados atuais do PTS
    get_url = f"https://sistemaevoluir.com.br/api/ptscassi-ipasgo/{id_relatorio}"
    resp_get = scraper.session.get(get_url)
    if resp_get.status_code != 200:
        raise ConnectionError(f"Erro ao obter dados do PTS ({resp_get.status_code}): {resp_get.text[:200]}")
        
    data_json = resp_get.json()
    
    # Se o retorno for encapsulado em 'data' ou semelhante
    pts_data = data_json.get("data") if isinstance(data_json.get("data"), dict) else data_json
    
    # 2. Montar o payload para a requisição PUT (enviada como POST com _method=PUT)
    # Precisamos do token CSRF capturado na OP0
    if not scraper.csrf_token:
        raise ValueError("Token CSRF não disponível! Execute a OP0_Login previamente.")
        
    # Os campos requeridos pela API Evoluir (conforme enviado na especificação)
    payload = {
        "_token": scraper.csrf_token,
        "_method": "PUT",
        "paciente_id": pts_data.get("paciente_id"),
        "patologia_id": pts_data.get("patologia_id"),
        "medico_solicitante": pts_data.get("medico_solicitante"),
        "data": nova_data, # A nova data do PTS
        "profissional_id": pts_data.get("profissional_id"),
        "diagnostico": pts_data.get("diagnostico"),
        "meta_estabelecida": pts_data.get("meta_estabelecida"),
        "tempo_meses": pts_data.get("tempo_meses"),
        "numero_sessoes_semanais": pts_data.get("numero_sessoes_semanais"),
        "justificativa_clinica": pts_data.get("justificativa_clinica"),
        "evolucao_paciente": pts_data.get("evolucao_paciente")
    }
    
    # 3. Executar o POST de atualização
    put_url = f"https://sistemaevoluir.com.br/api/ptscassi-ipasgo/{id_relatorio}"
    
    # Enviar como x-www-form-urlencoded (data=payload)
    resp_put = scraper.session.post(put_url, data=payload)
    
    if resp_put.status_code not in [200, 201, 204]:
        raise ConnectionError(f"Erro ao atualizar data do PTS ({resp_put.status_code}): {resp_put.text[:300]}")
        
    scraper.log(f"PTS {id_relatorio} atualizado com sucesso para a data '{nova_data}'!", job_id=job_id)
    return {"status": "success", "message": f"PTS {id_relatorio} atualizado para {nova_data}"}
