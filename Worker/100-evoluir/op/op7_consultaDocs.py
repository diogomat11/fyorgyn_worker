import os
import re
import unicodedata
import pandas as pd

def is_target_tipo_file(tipo_file_raw):
    """Retorna True se o tipo_file for um dos 4 relatórios/planos desejados."""
    if not tipo_file_raw:
        return False
    tf = str(tipo_file_raw).strip().lower()
    # Normalizar acentos
    tf_norm = "".join(c for c in unicodedata.normalize('NFD', tf) if unicodedata.category(c) != 'Mn')
    
    targets = [
        "relatorio inicial de avaliacao",
        "relatorio evolucao",
        "relatorio reavaliacao",
        "plano terapeutico"
    ]
    return any(t in tf_norm for t in targets)

def run(scraper, job_data):
    job_id = job_data.get("job_id") or job_data.get("id") or "standalone"
    user_id = job_data.get("user_id") or getattr(scraper, 'user_id', None)
    
    scraper.log("Iniciando OP_consultaDocs (extração de relatórios e planos terapêuticos)...", job_id=job_id)

    # 1. Obter lista de pacientes com id_paciente do banco para este user_id
    pacientes_map = {}
    if scraper.db:
        try:
            from models import Carteirinha
            query = scraper.db.query(Carteirinha).filter(Carteirinha.id_paciente.isnot(None))
            if user_id:
                query = query.filter(Carteirinha.user_id == user_id)
            rows = query.all()
            for r in rows:
                if r.id_paciente and r.id_paciente.strip():
                    pacientes_map[r.id_paciente.strip()] = {
                        "id_paciente": r.id_paciente.strip(),
                        "paciente": r.paciente or "",
                        "carteirinha": r.carteirinha or r.codigo_beneficiario or ""
                    }
        except Exception as e:
            scraper.log(f"Aviso ao consultar carteirinhas no banco: {e}", level="WARN", job_id=job_id)

    # Fallback se não encontrou no banco via query
    if not pacientes_map and isinstance(job_data.get("id_pacientes"), list):
        for pid in job_data["id_pacientes"]:
            pacientes_map[str(pid)] = {"id_paciente": str(pid), "paciente": "", "carteirinha": ""}

    scraper.log(f"Encontrados {len(pacientes_map)} pacientes para consulta de documentos API...", job_id=job_id)

    documentos_extraidos = []

    # 2. Consultar a API de arquivos para cada paciente
    for idx, (id_pac, p_info) in enumerate(pacientes_map.items(), 1):
        url = f"https://sistemaevoluir.com.br/api/usuario-arquivos?usuario_id={id_pac}&per_page=150"
        try:
            resp = scraper.session.get(url, timeout=30)
            if resp.status_code != 200:
                scraper.log(f"[{idx}/{len(pacientes_map)}] Erro ({resp.status_code}) ao consultar arquivos do paciente {id_pac}", level="WARN", job_id=job_id)
                continue

            res_json = resp.json()
            items = []
            if isinstance(res_json, dict):
                items = res_json.get("data") or []
            elif isinstance(res_json, list):
                items = res_json

            count_pac_docs = 0
            for item in items:
                if not isinstance(item, dict):
                    continue
                tipo_file = item.get("tipo_file")
                if is_target_tipo_file(tipo_file):
                    doc_rec = {
                        "id_paciente": id_pac,
                        "nome_paciente": p_info["paciente"],
                        "carteirinha": p_info["carteirinha"],
                        "tipo_file": tipo_file,
                        "data_arquivo": item.get("data_arquivo_relatorio") or "",
                        "profissional_nome": item.get("profissional_nome") or "",
                        "especialidade_nome": item.get("especialidade_nome") or "",
                        "titulo": item.get("titulo") or "",
                        "url_arquivo": item.get("path_avatar") or item.get("path") or "",
                        "id_documento": item.get("id") or ""
                    }
                    documentos_extraidos.append(doc_rec)
                    count_pac_docs += 1

            if count_pac_docs > 0:
                scraper.log(f"[{idx}/{len(pacientes_map)}] {p_info['paciente']}: {count_pac_docs} documentos elegíveis encontrados.", job_id=job_id)

        except Exception as e:
            scraper.log(f"[{idx}/{len(pacientes_map)}] Exceção ao consultar paciente {id_pac}: {e}", level="ERROR", job_id=job_id)

    scraper.log(f"Total geral de documentos elegíveis extraídos: {len(documentos_extraidos)}", job_id=job_id)

    # 3. Gerar arquivo Excel (.xlsx) para download
    excel_filename = f"evoluir_docs_job_{job_id}.xlsx"
    
    # Garantir diretório uploads existente
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    uploads_dir = os.path.join(root_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    excel_filepath = os.path.join(uploads_dir, excel_filename)
    excel_rel_url = f"/uploads/{excel_filename}"

    if documentos_extraidos:
        df = pd.DataFrame(documentos_extraidos)
        # Reordenar e renomear colunas para apresentação profissional
        col_map = {
            "id_paciente": "ID Paciente",
            "nome_paciente": "Nome Paciente",
            "carteirinha": "Carteirinha",
            "tipo_file": "Tipo de Arquivo",
            "data_arquivo": "Data do Relatório",
            "profissional_nome": "Profissional",
            "especialidade_nome": "Especialidade",
            "titulo": "Título",
            "url_arquivo": "URL do Arquivo (PDF/Imagem)",
            "id_documento": "ID Documento"
        }
        df_export = df.rename(columns=col_map)
        df_export.to_excel(excel_filepath, index=False)
        scraper.log(f"Arquivo Excel gerado com sucesso: {excel_filepath}", job_id=job_id)
    else:
        # Gerar excel vazio com colunas
        df_export = pd.DataFrame(columns=[
            "ID Paciente", "Nome Paciente", "Carteirinha", "Tipo de Arquivo",
            "Data do Relatório", "Profissional", "Especialidade", "Título", "URL do Arquivo (PDF/Imagem)", "ID Documento"
        ])
        df_export.to_excel(excel_filepath, index=False)

    return {
        "status": "success",
        "total_documentos": len(documentos_extraidos),
        "total_pacientes_consultados": len(pacientes_map),
        "excel_url": excel_rel_url,
        "data": documentos_extraidos
    }
