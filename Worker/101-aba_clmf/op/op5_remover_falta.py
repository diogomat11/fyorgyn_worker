import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.constants import AJAX_SCHEDULE_URL, ACTION_REMOVER_FALTA

def run(scraper, job_data):
    job_id = job_data.get("job_id")
    id_agendamento = job_data.get("id_agendamento")
    id_paciente = job_data.get("id_paciente")
    data_inicial = job_data.get("data_inicial")
    data_final = job_data.get("data_final")
    
    if id_agendamento is None:
        raise ValueError("id_agendamento nao fornecido para OP5")
    if id_paciente is None:
        raise ValueError("id_paciente nao fornecido para OP5")
    
    # Normalize to list
    if isinstance(id_agendamento, (int, str)):
        ids = [str(id_agendamento)]
    else:
        ids = [str(i) for i in id_agendamento]
    
    # Default dates to today if not provided
    if not data_inicial or not data_final:
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        data_inicial = data_inicial or today
        data_final = data_final or today
    
    scraper.log(f"Iniciando OP5 - Remover Falta para {len(ids)} agendamento(s), paciente={id_paciente}...", job_id=job_id)
    
    # Build form data with list_data[] array-style
    form_parts = []
    form_parts.append("callback=Schedule")
    form_parts.append(f"callback_action={ACTION_REMOVER_FALTA}")
    for sid in ids:
        form_parts.append(f"list_data%5B%5D={sid}")
    form_parts.append(f"data_final={data_final}")
    form_parts.append(f"data_inicial={data_inicial}")
    form_parts.append(f"paciente_id={id_paciente}")
    
    form_data = "&".join(form_parts)
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    resp = scraper.session.post(
        AJAX_SCHEDULE_URL,
        data=form_data,
        headers=headers,
        timeout=15
    )
    
    if resp.status_code != 200:
        raise ConnectionError(f"Erro na requisicao de remover falta ({resp.status_code}): {resp.text[:300]}")
    
    try:
        result = resp.json()
    except Exception:
        result = {"raw": resp.text[:500]}
    
    scraper.log(f"OP5 concluida: falta removida de {len(ids)} agendamento(s).", job_id=job_id)
    
    return {
        "status": "success",
        "action": "falta_removida",
        "ids_processados": ids,
        "id_paciente": str(id_paciente),
        "portal_response": str(result)[:200]
    }

execute = run
