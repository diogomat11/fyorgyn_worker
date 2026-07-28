import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.constants import CLIENT_DETAIL_URL

def run(scraper, job_data):
    job_id = job_data.get("job_id")
    id_paciente = str(job_data.get("id_paciente", "")).strip()
    agendamentos_pendentes = job_data.get("agendamentos_pendentes") or []
    
    if not id_paciente:
        raise ValueError("id_paciente nao fornecido para OP2 - Consultar Carteirinha")
        
    scraper.log(f"Iniciando OP2 - Consultar Carteirinha para id_paciente={id_paciente}...", job_id=job_id)
    
    url = f"{CLIENT_DETAIL_URL}/{id_paciente}"
    resp = scraper.session.get(url)
    
    if resp.status_code != 200:
        raise ConnectionError(f"Erro ao acessar {url} ({resp.status_code}): {resp.text[:200]}")
        
    html = resp.text
    carteirinhas = []
    
    # Split by class='linha_carteirinha'
    blocks = re.split(r"class=['\"]linha_carteirinha['\"]", html)
    for block in blocks[1:]:
        # Extrair ate o fechamento da div da linha
        sub_block = block.split("</div>\n        </div>", 1)[0] if "</div>\n        </div>" in block else block.split("</div>\r\n</div>", 1)[0]
        
        num_m = re.search(r"class=['\"]col_numero['\"][^>]*>\s*([^<]*)", sub_block)
        col_numero = num_m.group(1).strip() if num_m else ""
        
        pag_m = re.search(r"class=['\"]col_pagamento['\"][^>]*>\s*([^<]*)", sub_block)
        col_pagamento = pag_m.group(1).strip() if pag_m else ""
        
        stat_m = re.search(r"class=['\"]col_status['\"][^>]*>\s*([^<]*)", sub_block)
        col_status = stat_m.group(1).strip() if stat_m else ""
        
        if col_pagamento or col_numero:
            carteirinhas.append({
                "carteirinha": col_numero,
                "convenio_texto": col_pagamento,
                "status": col_status
            })
            
    scraper.log(f"OP2 concluida: {len(carteirinhas)} carteirinhas encontradas para id_paciente={id_paciente}.", job_id=job_id)
    
    return {
        "id_paciente": id_paciente,
        "carteirinhas": carteirinhas,
        "agendamentos_pendentes": agendamentos_pendentes
    }

execute = run
