import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.constants import AJAX_SCHEDULE_URL, ALLOWED_UNIT_IDS, STATUS_MAP

def run(scraper, job_data):
    job_id = job_data.get("job_id")
    scraper.log("Iniciando OP1 - Importar Agendamentos ABA_clmf...", job_id=job_id)
    
    # Extrair parâmetros
    data_inicio = job_data.get("data_inicio") or job_data.get("start_date")
    data_fim = job_data.get("data_fim") or job_data.get("end_date")
    id_paciente = str(job_data.get("id_paciente", "0")).strip()
    
    if not data_inicio:
        data_inicio = datetime.now().strftime("%Y-%m-%01") # Inicio do mes atual
    if not data_fim:
        data_fim = datetime.now().strftime("%Y-%m-%d")
        
    scraper.log(f"Parametros: data_inicio={data_inicio}, data_fim={data_fim}, id_paciente={id_paciente}", job_id=job_id)
    
    # Payload POST form-encoded
    payload = {
        "callback": "Schedule",
        "callback_action": "get_atendimentos_replicar_agenda",
        "callback_folder": "../",
        "schedule_local_id": "0",
        "data_inicial": data_inicio,
        "data_final": data_fim,
        "fixed": job_data.get("fixed", "N"),
        "especialidade_id[]": "0",
        "professional_id[]": "0",
        "pacient_id[]": id_paciente
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    resp = scraper.session.post(AJAX_SCHEDULE_URL, data=payload, headers=headers)
    if resp.status_code != 200:
        raise ConnectionError(f"Erro na requisicao HTTP a Schedule.ajax.php ({resp.status_code}): {resp.text[:200]}")
        
    try:
        items = resp.json()
    except Exception as e:
        raise ValueError(f"Resposta de Schedule.ajax.php nao e um JSON valido: {resp.text[:300]}")
        
    if not isinstance(items, list):
        scraper.log(f"Resposta recebida nao e uma lista de agendamentos. Tipo: {type(items)}", level="WARN", job_id=job_id)
        return []
        
    agendamentos_processados = []
    
    for item in items:
        if not isinstance(item, dict):
            continue
            
        local_id_str = str(item.get("schedule_local_id", "")).strip()
        try:
            local_id = int(local_id_str)
        except ValueError:
            local_id = 0
            
        # Regra Geral: Ignorar se schedule_local_id nao estiver em {1, 3, 5}
        if local_id not in ALLOWED_UNIT_IDS:
            continue
            
        schedule_id = str(item.get("schedule_id", "")).strip()
        if not schedule_id:
            continue
            
        # Extract date and time
        date_start_str = str(item.get("schedule_date_start", "")).strip()
        data_val = None
        hora_val = None
        if " " in date_start_str:
            parts = date_start_str.split(" ")
            data_val = parts[0]
            hora_val = parts[1]
        else:
            data_val = date_start_str
            hora_val = str(item.get("schedule_date_start_time", "00:00:00")).strip()
            
        status_code = str(item.get("schedule_status", "0")).strip()
        status_text = STATUS_MAP.get(status_code, "A Confirmar")
        
        user_name = str(item.get("user_name", "")).strip()
        user_lastname = str(item.get("user_lastname", "")).strip()
        nome_prof = f"{user_name} {user_lastname}".strip()
        
        cod_fat = str(item.get("schedule_codigo_faturamento", "")).strip()
        
        mapped_item = {
            "id_agendamento": int(schedule_id),
            "id_paciente": str(item.get("schedule_pacient_id", "")).strip(),
            "id_unidade": local_id,
            "schedule_pagamento_id": item.get("schedule_pagamento_id"),
            "data": data_val,
            "hora_inicio": hora_val,
            "sala": str(item.get("schedule_room_id", "")).strip(),
            "Id_profissional": str(item.get("professional_id", "")).strip(),
            "Nome_profissional": nome_prof,
            "Nome_Paciente": str(item.get("client_nome", "")).strip(),
            "Tipo_atendimento": str(item.get("especialidade_name", "")).strip(),
            "cod_procedimento_aut": cod_fat,
            "cod_procedimento_fat": cod_fat,
            "Status": status_text
        }
        
        agendamentos_processados.append(mapped_item)
        
    # Extrair mapeamento de nomes de convênios/pagamentos de /pagamentos/home
    pagamentos_map = {}
    try:
        scraper.log("Buscando listagem de pagamentos em /pagamentos/home para extrair nomes de convênios...", job_id=job_id)
        pag_resp = scraper.session.get("https://abalarissamartinsferreira.com.br/pagamentos/home", timeout=15)
        if pag_resp.status_code == 200:
            pag_resp.encoding = pag_resp.apparent_encoding or "utf-8"
            html_text = pag_resp.text
            import re
            import html as html_lib
            rows = re.findall(r'<tr[^>]*>.*?</tr>', html_text, re.DOTALL)
            for r in rows:
                id_match = re.search(r'pagamentos/create/(\d+)', r) or re.search(r'pagamentos/create_faturamento/(\d+)', r)
                if id_match:
                    pid = int(id_match.group(1))
                    tds = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL)
                    if len(tds) >= 2:
                        name = re.sub(r'<[^<]+?>', '', tds[1]).strip()
                        name = html_lib.unescape(name)
                        name = ' '.join(name.split())
                        if name:
                            pagamentos_map[pid] = name
            scraper.log(f"Mapeados {len(pagamentos_map)} convênios de /pagamentos/home.", job_id=job_id)
        else:
            scraper.log(f"Erro ao obter /pagamentos/home: status={pag_resp.status_code}", level="WARN", job_id=job_id)
    except Exception as e:
        scraper.log(f"Erro ao buscar mapeamento de pagamentos: {e}", level="WARN", job_id=job_id)

    # Injetar nome do convênio em cada item
    for item in agendamentos_processados:
        pid = item.get("schedule_pagamento_id")
        if pid is not None:
            try:
                pid_int = int(pid)
                item["convenio_nome"] = pagamentos_map.get(pid_int)
            except (ValueError, TypeError):
                item["convenio_nome"] = None
        else:
            item["convenio_nome"] = None

    # 2a Requisicao: Buscar Atendimentos Excluidos no periodo
    atendimentos_excluidos_ids = []
    try:
        scraper.log(f"Buscando atendimentos excluidos em Schedule.ajax.php para {data_inicio} a {data_fim}...", job_id=job_id)
        payload_excluidos = {
            "callback": "Schedule",
            "callback_action": "tela_excluir_atendimentos_excluidos",
            "data_inicial": data_inicio,
            "data_final": data_fim,
            "paciente_id": "0",
            "profissional_id": "0"
        }
        resp_excl = scraper.session.post(AJAX_SCHEDULE_URL, data=payload_excluidos, headers=headers)
        if resp_excl.status_code == 200:
            import re
            try:
                excl_json = resp_excl.json()
                if isinstance(excl_json, list):
                    for ex in excl_json:
                        if isinstance(ex, dict) and ex.get("schedule_id"):
                            try:
                                atendimentos_excluidos_ids.append(int(ex["schedule_id"]))
                            except (ValueError, TypeError): pass
                elif isinstance(excl_json, dict):
                    raw_str = str(excl_json)
                    found = re.findall(r'schedule_id["\']?\s*[:=]\s*["\']?(\d+)', raw_str)
                    for sid in found:
                        atendimentos_excluidos_ids.append(int(sid))
            except Exception:
                raw_str = resp_excl.text
                found = re.findall(r'schedule_id["\']?\s*[:=]\s*["\']?(\d+)', raw_str)
                for sid in found:
                    atendimentos_excluidos_ids.append(int(sid))
        scraper.log(f"Encontrados {len(atendimentos_excluidos_ids)} agendamentos excluidos no portal.", job_id=job_id)
    except Exception as e:
        scraper.log(f"Aviso ao buscar atendimentos excluidos: {e}", level="WARN", job_id=job_id)

    scraper.log(f"OP1 concluida: {len(agendamentos_processados)} agendamentos validos e {len(atendimentos_excluidos_ids)} excluidos extraidos.", job_id=job_id)
    
    return {
        "data": agendamentos_processados,
        "atendimentos_excluidos": atendimentos_excluidos_ids
    }

execute = run

