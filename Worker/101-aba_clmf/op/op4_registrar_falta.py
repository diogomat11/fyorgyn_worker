import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.constants import AJAX_SCHEDULE_URL, FALTAS_BLOCO_URL, BASE_URL, ACTION_GRAVAR_FALTA

def run(scraper, job_data):
    job_id = job_data.get("job_id")
    id_agendamento = job_data.get("id_agendamento")
    id_paciente = job_data.get("id_paciente")
    tipo_desagendamento = job_data.get("tipo_desagendamento")
    doc_justificativa = job_data.get("doc_justificativa", "")
    
    if id_agendamento is None:
        raise ValueError("id_agendamento nao fornecido para OP4")
    if id_paciente is None:
        raise ValueError("id_paciente (clientId) nao fornecido para OP4")
    if tipo_desagendamento is None:
        raise ValueError("tipo_desagendamento nao fornecido para OP4")
    
    # Normalize to list
    if isinstance(id_agendamento, (int, str)):
        ids = [str(id_agendamento)]
    else:
        ids = [str(i) for i in id_agendamento]
    
    scraper.log(f"Iniciando OP4 - Registrar Falta para {len(ids)} agendamento(s), paciente={id_paciente}, motivo={tipo_desagendamento}...", job_id=job_id)
    
    # 1. GET faltas_bloco page for session
    try:
        resp_page = scraper.session.get(FALTAS_BLOCO_URL, timeout=15)
        if resp_page.status_code != 200:
            scraper.log(f"Aviso: GET faltas_bloco retornou status {resp_page.status_code}", level="WARN", job_id=job_id)
    except Exception as e:
        scraper.log(f"Aviso ao acessar pagina de faltas: {e}", level="WARN", job_id=job_id)
    
    # 2. Build payload - atendimentos is COMMA-SEPARATED
    payload = {
        "callback": "Schedule",
        "callback_action": ACTION_GRAVAR_FALTA,
        "callback_folder": f"{BASE_URL}/",
        "base_redirect": "/faltas_bloco",
        "clientId": str(id_paciente),
        "atendimentos": ",".join(ids),
        "tipoDesagendamento": str(tipo_desagendamento),
        "doc_justificativa": doc_justificativa or ""
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # 3. POST
    resp = scraper.session.post(
        AJAX_SCHEDULE_URL,
        data=payload,
        headers=headers,
        timeout=15
    )
    
    if resp.status_code != 200:
        raise ConnectionError(f"Erro na requisicao de falta ({resp.status_code}): {resp.text[:300]}")
    
    # 4. Parse response
    try:
        result = resp.json()
    except Exception:
        result = {"raw": resp.text[:500]}
    
    scraper.log(f"OP4 concluida: {len(ids)} agendamento(s) registrados como falta.", job_id=job_id)
    
    return {
        "status": "success",
        "action": "falta_registrada",
        "ids_processados": ids,
        "id_paciente": str(id_paciente),
        "tipo_desagendamento": str(tipo_desagendamento),
        "portal_response": str(result)[:200]
    }

execute = run
