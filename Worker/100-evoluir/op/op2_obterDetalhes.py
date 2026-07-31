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
    
    # Tipos de documento que NÃO são carteirinhas de convênio (não usar como número do plano)
    _TIPOS_DOCUMENTO_PESSOAL = {'cpf', 'rg', 'passaporte', 'cnh', 'certidao', 'cnpj'}

    def _extrair_numero_convenio(campo):
        """Extrai o número string de um campo que pode ser str, dict ou list.
        Retorna None se o campo for um documento pessoal (CPF, RG, etc.)."""
        if campo is None:
            return None
        if isinstance(campo, str):
            return campo.strip() or None
        if isinstance(campo, dict):
            tipo = (campo.get("tipo") or "").lower().strip()
            numero = str(campo.get("numero") or "").strip()
            if tipo in _TIPOS_DOCUMENTO_PESSOAL:
                return None  # CPF/RG não é número de carteirinha
            return numero or None
        if isinstance(campo, list):
            # Priorizar item com tipo que NÃO seja documento pessoal
            for item in campo:
                if isinstance(item, dict):
                    tipo = (item.get("tipo") or "").lower().strip()
                    numero = str(item.get("numero") or "").strip()
                    if tipo not in _TIPOS_DOCUMENTO_PESSOAL and numero:
                        return numero
            # Fallback: primeiro item com numero que não seja CPF
            for item in campo:
                if isinstance(item, dict):
                    numero = str(item.get("numero") or "").strip()
                    if numero and len(numero) > 8:  # Carteirinhas têm mais de 8 dígitos
                        return numero
        return None

    # 1. Tentar campos raiz em ordem de prioridade
    carteirinha = None
    for campo_nome in ("carteirinha", "carteira", "codigo_beneficiario", "matricula", "numero_carteirinha"):
        val = data.get(campo_nome)
        if val:
            resultado = _extrair_numero_convenio(val)
            if resultado:
                carteirinha = resultado
                break

    # 2. Tentar sub-objeto "dados"
    if not carteirinha and isinstance(data.get("dados"), dict):
        dados = data["dados"]
        for campo_nome in ("carteirinha", "carteira", "codigo_beneficiario", "matricula"):
            val = dados.get(campo_nome)
            if val:
                resultado = _extrair_numero_convenio(val)
                if resultado:
                    carteirinha = resultado
                    break

    # 3. Tentar array "documentos" — buscar por tipo de convênio/plano
    if not carteirinha:
        docs = data.get("documentos") or []
        if isinstance(data.get("dados"), dict):
            docs = docs or data["dados"].get("documentos") or []
        if isinstance(docs, list):
            carteirinha = _extrair_numero_convenio(docs)

    # 4. Tentar array "convenios" — buscar número de carteirinha dentro do plano
    if not carteirinha:
        convs = data.get("convenios") or []
        if isinstance(convs, list):
            for conv in convs:
                if isinstance(conv, dict):
                    for campo_nome in ("numero_carteirinha", "carteirinha", "matricula", "codigo_beneficiario"):
                        val = conv.get(campo_nome)
                        if val and isinstance(val, str) and val.strip():
                            carteirinha = val.strip()
                            break
                if carteirinha:
                    break

    # 2. Extrair patologia do array patologias
    patologia = None
    patologias_list = data.get("patologias") or []
    if not patologias_list and isinstance(data.get("dados"), dict):
        patologias_list = data["dados"].get("patologias") or []
    if isinstance(patologias_list, list):
        for pat in patologias_list:
            if isinstance(pat, dict):
                patologia = pat.get("nome") or pat.get("cid") or pat.get("descricao")
                if patologia:
                    patologia = str(patologia).strip()
                    break

    result = {
        "id_paciente": id_paciente,
        "carteirinha": carteirinha,
        "patologia": patologia
    }
    
    scraper.log(f"Detalhes extraídos: carteirinha='{carteirinha}' patologia='{patologia}'", job_id=job_id)
    return result
