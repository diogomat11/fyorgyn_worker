"""
Helper de validacao de vinculo de prestador para Unimed Goiania (id_convenio=3).

Consulta a API getErrosSapia do portal sgucard.unimedgoiania.coop.br para cada guia
e classifica o vinculo do prestador em "Guia Valida" ou mensagem de erro.

Replica de clmf_hub_basic/worker/Worker/ImportBaseGuias.py:372-447 (Layer 2 verification),
adaptada como modulo independente para integracao no op1_consulta do Agenda_hub_MultiConv.

Especificacao do JSON retornado (valida_prestador_replication_prompt.yaml):
    {
        "codigo_procedimento": "<codigo>",
        "Vinculo_prestador": "Guia Valida" | "<mensagem_erro_unimed>"
    }

Regras case-sensitive (Gotchas do YAML):
    - Chave "Vinculo_prestador": V maiusculo, p minusculo.
    - Valor "Guia Valida" sem acento (sem til no 'a') quando definido pelo helper.
"""
import requests

# Endpoint da API de verificacao de erros da Unimed Goiania
GET_ERROS_SAPIA_URL = "https://sgucard.unimedgoiania.coop.br/cmagnet/servlet/getErrosSapia"
VINCULO_VALIDA = "Guia Válida"  # mantem acento conforme clmf_hub_basic (compat frontend)


def validar_vinculo_prestador(session, cd_guia, timeout=10):
    """
    Consulta getErrosSapia para uma guia e retorna o dict de validacao.

    Args:
        session: requests.Session com cookies sincronizados do Selenium (autenticados).
        cd_guia: codigo da guia (parametro cdGuia da API).
        timeout: timeout HTTP em segundos.

    Returns:
        dict no formato {"codigo_procedimento": None, "Vinculo_prestador": <str>}.
        Obs.: codigo_procedimento nao e determinado aqui (caller deve preencher);
        so Vinculo_prestador e classificado por esta funcao.

    Casos:
        - {"erros": []}                    -> "Guia Válida"
        - {"erros": [{"msg": "..."}]}      -> mensagem do primeiro erro
        - HTTP != 200                      -> "Erro ao validar (HTTP <status>)"
        - Falha JSON                      -> "Erro ao validar (JSON invalido)"
        - Excecao de rede                  -> "Erro ao validar (<excecao>)"
    """
    if not cd_guia:
        return {"codigo_procedimento": None, "Vinculo_prestador": "Erro ao validar (cdGuia ausente)"}

    url = f"{GET_ERROS_SAPIA_URL}?cdGuia={cd_guia}"
    try:
        resp = session.get(url, timeout=timeout)
    except Exception as e:
        return {"codigo_procedimento": None, "Vinculo_prestador": f"Erro ao validar ({e})"}

    if resp.status_code != 200:
        return {"codigo_procedimento": None,
                "Vinculo_prestador": f"Erro ao validar (HTTP {resp.status_code})"}

    try:
        data = resp.json()
    except Exception:
        return {"codigo_procedimento": None, "Vinculo_prestador": "Erro ao validar (JSON invalido)"}

    erros = data.get("erros") or []
    if isinstance(erros, list) and len(erros) > 0:
        primeiro = erros[0] if isinstance(erros[0], dict) else {}
        msg = primeiro.get("msg", "Erro de rede identificado")
        return {"codigo_procedimento": None, "Vinculo_prestador": msg}

    # Sem erros -> guia valida
    return {"codigo_procedimento": None, "Vinculo_prestador": VINCULO_VALIDA}


def extrair_cd_guia_da_url(current_url):
    """
    Extrai o parametro CD_GUIA da URL atual do driver.

    Args:
        current_url: scraper.driver.current_url (string).

    Returns:
        str com o cdGuia, ou None se nao encontrado.
    """
    if not current_url or "CD_GUIA=" not in current_url.upper():
        return None
    # Case-insensitive split
    idx = current_url.upper().find("CD_GUIA=")
    resto = current_url[idx + len("CD_GUIA="):]
    # cdGuia termina no proximo & ou fim da string
    cd = resto.split("&")[0]
    return cd.strip() or None


def classificar_tipo_json(guias_validadas):
    """
    Classifica o resultado agregado em tipo_json conforme especificacao YAML.

    Args:
        guias_validadas: dict no formato {<numero_guia>: {"codigo_procedimento": ..., "Vinculo_prestador": ...}}

    Returns:
        str: "All Sucess" | "Thered" | "Null"
        (Grafia EXATA conforme Gotcha #1 do YAML - manter "All Sucess" com erro de digitacao).

    Regras:
        - Sem guias                                    -> "Null"
        - Todas as guias com Vinculo_prestador == "Guia Válida" -> "All Sucess"
        - Ao menos uma guia com Vinculo != "Guia Válida"        -> "Thered"
    """
    if not guias_validadas:
        return "Null"

    todas_validas = True
    for attr in guias_validadas.values():
        vinculo = (attr or {}).get("Vinculo_prestador", "")
        if vinculo != VINCULO_VALIDA:
            todas_validas = False
            break

    return "All Sucess" if todas_validas else "Thered"


def montar_valida_prestador_json(guias_validadas):
    """
    Monta o JSON completo {tipo_json, guias} para anexar ao result_data do job.

    Args:
        guias_validadas: dict {<numero_guia>: {"codigo_procedimento": ..., "Vinculo_prestador": ...}}

    Returns:
        dict no formato final:
            {"tipo_json": "All Sucess"|"Thered"|"Null", "guias": {...}}
    """
    return {
        "tipo_json": classificar_tipo_json(guias_validadas),
        "guias": guias_validadas or {},
    }


def marcar_procedimento_habilitado(guias_validadas, procedimentos_habilitados):
    """
    Adiciona o flag 'procedimento_habilitado' (bool) em cada guia do dict,
    com base na lista de codigos habilitados recebida do Hub via params.

    Compatibilidade: se procedimentos_habilitados for None/vazio, nao altera o dict
    (worker trata ausencia da lista como "nao filtrar").

    Args:
        guias_validadas: dict {<numero_guia>: {"codigo_procedimento": ..., ...}}
        procedimentos_habilitados: lista de codigos_procedimento (str) ou None.

    Returns:
        O mesmo dict (mutado in-place) com 'procedimento_habilitado' em cada guia.
    """
    if not procedimentos_habilitados:
        return guias_validadas
    hab_set = {str(p) for p in procedimentos_habilitados}
    for attr in guias_validadas.values():
        if not isinstance(attr, dict):
            continue
        codigo = str(attr.get("codigo_procedimento") or "")
        attr["procedimento_habilitado"] = codigo in hab_set
    return guias_validadas
