import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.constants import AJAX_SCHEDULE_URL, CONFIRMAR_ATENDIMENTO_URL, SITUACAO_CONFIRMADO, ACTION_CONFIRMAR

def run(scraper, job_data):
    job_id = job_data.get("job_id")
    # id_agendamento can be int or list of ints
    id_agendamento = job_data.get("id_agendamento")
    num_situacao = job_data.get("num_situacao", SITUACAO_CONFIRMADO)
    
    if id_agendamento is None:
        raise ValueError("id_agendamento não fornecido para OP3")
    
    # Normalize to list
    if isinstance(id_agendamento, (int, str)):
        ids = [str(id_agendamento)]
    else:
        ids = [str(i) for i in id_agendamento]
    
    scraper.log(f"Iniciando OP3 - Confirmar Agendamento (situacao={num_situacao}) para {len(ids)} agendamento(s)...", job_id=job_id)
    
    # 1. Navigate to confirmar page to ensure session is valid
    try:
        resp_page = scraper.session.get(CONFIRMAR_ATENDIMENTO_URL, timeout=15)
        if resp_page.status_code != 200:
            scraper.log(f"Aviso: GET confirmar_atendimento retornou status {resp_page.status_code}", level="WARN", job_id=job_id)
    except Exception as e:
        scraper.log(f"Aviso ao acessar pagina de confirmacao: {e}", level="WARN", job_id=job_id)
    
    # 2. Build payload - schedule_id[] is array-style
    payload = {
        "callback": "Schedule",
        "callback_action": ACTION_CONFIRMAR,
        "situacao": str(num_situacao)
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # Build form data with multiple schedule_id[] entries
    form_parts = []
    form_parts.append(f"callback=Schedule")
    form_parts.append(f"callback_action={ACTION_CONFIRMAR}")
    for sid in ids:
        form_parts.append(f"schedule_id%5B%5D={sid}")
    form_parts.append(f"situacao={num_situacao}")
    
    form_data = "&".join(form_parts)
    
    # 3. POST
    resp = scraper.session.post(
        AJAX_SCHEDULE_URL,
        data=form_data,
        headers=headers,
        timeout=15
    )
    
    if resp.status_code != 200:
        raise ConnectionError(f"Erro na requisicao de confirmacao ({resp.status_code}): {resp.text[:300]}")
    
    # 4. Validate response
    try:
        result = resp.json()
    except Exception:
        result = {"raw": resp.text[:500]}
    
    trigger = result.get("trigger", "") if isinstance(result, dict) else ""
    trigger_lower = trigger.lower() if trigger else resp.text.lower()
    
    action_desc = "confirmado" if num_situacao == SITUACAO_CONFIRMADO else "confirmacao removida"
    
    if "sucesso" in trigger_lower or "confirmado" in trigger_lower or "tudo certo" in trigger_lower:
        scraper.log(f"OP3 concluida com sucesso: {len(ids)} agendamento(s) {action_desc}.", job_id=job_id)
        return {
            "status": "success",
            "action": action_desc,
            "ids_processados": ids,
            "num_situacao": num_situacao,
            "portal_response": trigger[:200] if trigger else None
        }
    else:
        scraper.log(f"OP3 resposta inesperada do portal: {trigger[:200] if trigger else resp.text[:200]}", level="WARN", job_id=job_id)
        return {
            "status": "success",
            "action": action_desc,
            "ids_processados": ids,
            "num_situacao": num_situacao,
            "portal_response": trigger[:200] if trigger else resp.text[:200],
            "warning": "Resposta do portal nao contem texto de confirmacao esperado"
        }

execute = run
