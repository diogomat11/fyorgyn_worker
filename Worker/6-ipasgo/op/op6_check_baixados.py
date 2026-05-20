import os
import sys
import logging
from sqlalchemy.dialects.postgresql import insert

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from core.webplan_client import WebPlanClient
from core.webplan_parser import parse_detalhes, extract_total_pages

# We must import the FaturamentoLote model. 
# We'll try to import from worker models.
try:
    from models import FaturamentoLote, LoteConvenio
except ImportError:
    # Fallback to backend models if running differently
    backend_path = os.path.join(os.path.dirname(os.path.dirname(_mod_root)), 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    from models import FaturamentoLote, LoteConvenio

def run(scraper, job_data):
    """
    OP6 - Check Baixados - IPASGO
    Consome a API LoadDetalhes via requests.Session autenticado e persiste no banco (Upsert).
    """
    driver = scraper.driver
    job_id = job_data.get("job_id")
    # Changed from loteId to numero_lote to match DB nomenclature
    numero_lote = job_data.get("numero_lote", job_data.get("loteId")) 
    codigo_prestador = job_data.get("codigoPrestador", "") or getattr(scraper, "cod_prestador", "")
    
    if not codigo_prestador:
        raise ValueError("O código do prestador não foi informado (payload vazio) e não foi encontrado na tabela user_convenios.")
    
    scraper.log(f"OP6 - Iniciando extração (Lote: {numero_lote}) via WebPlan API...", job_id=job_id)
    
    if not numero_lote:
        raise ValueError("O parâmetro 'numero_lote' é obrigatório para a OP6.")

    # 1. Garante navegação inicial para a página de faturamento conforme solicitado
    faturamento_url = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/FaturamentoAtendimentos"
    scraper.log(f"OP6 - Navegando para URL de Faturamento: {faturamento_url}", job_id=job_id)
    
    # Fechar possíveis alertas antes de navegar
    try:
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(driver, 2).until(EC.alert_is_present())
        driver.switch_to.alert.accept()
    except:
        pass
        
    # Aguarda a aba do WebPlan estabilizar após o login (SSO) antes de forçar a URL
    from time import sleep
    for _ in range(10):
        try:
            if driver.execute_script("return document.readyState;") == "complete":
                if "facilinformatica" in driver.current_url.lower():
                    break
        except:
            pass
        sleep(1)
        
    try:
        driver.get(faturamento_url)
    except Exception as e:
        scraper.log(f"Aviso ao navegar (pode ser alert block): {e}", level="WARN", job_id=job_id)
        try:
            driver.switch_to.alert.accept()
            driver.get(faturamento_url)
        except:
            pass
    
    # 2. Init Client and extract Session
    from time import sleep
    
    # Aguardar carregamento completo da página
    for _ in range(10):
        try:
            if driver.execute_script("return document.readyState;") == "complete":
                break
        except:
            pass
        sleep(1)
    
    sleep(3) # Wait for page and cookies to settle
    client = WebPlanClient(driver)
    
    # 3. First call (Page 0) to get NumberOfPages
    scraper.log("Consultando Página 0 para obter metadados...", job_id=job_id)
    first_page_data = client.post_load_detalhes(lote_id=numero_lote, page=0, codigo_prestador=codigo_prestador)
    
    # ── LOG THE PAYLOAD PREVIEW ──
    preview = str(first_page_data)[:150].replace('\n', '')
    scraper.log(f"Raw API Response Preview [Pag 0]: {preview}...", job_id=job_id)
    
    total_pages = extract_total_pages(first_page_data)
    scraper.log(f"Total de páginas a processar: {total_pages}", job_id=job_id)
    
    # Parse first page
    parsed_items = parse_detalhes(first_page_data, lote_id_param=numero_lote)
    scraper.log(f"Extraídos {len(parsed_items)} registros da página 0", job_id=job_id)
    all_items = []
    all_items.extend(parsed_items)
    
    # 4. Loop the rest of the pages
    if total_pages > 1:
        for page_num in range(1, total_pages):
            scraper.log(f"Buscando página {page_num} de {total_pages-1}...", job_id=job_id)
            page_data = client.post_load_detalhes(lote_id=numero_lote, page=page_num, codigo_prestador=codigo_prestador)
            items = parse_detalhes(page_data, lote_id_param=numero_lote)
            scraper.log(f"Extraídos {len(items)} registros da página {page_num}", job_id=job_id)
            all_items.extend(items)
            
    scraper.log(f"OP6 - Extração concluída. Total de {len(all_items)} registros recebidos.", job_id=job_id)
    
    # 5. Save to DB using Bulk Upsert for maximum performance
    try:
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)
        
        # 1. Obter id_lote interno apenas uma vez
        id_lote_interno = job_data.get("id_lote_interno")
        lote_interno_id = None
        
        if id_lote_interno:
            lote_interno = scraper.db.query(LoteConvenio).filter_by(id_lote=id_lote_interno).first()
            if lote_interno:
                lote_interno.numero_lote = int(numero_lote)
                lote_interno.status = "Aberto"
                lote_interno_id = lote_interno.id_lote
                
        if not lote_interno_id:
            lote_interno = scraper.db.query(LoteConvenio).filter(
                LoteConvenio.numero_lote == int(numero_lote),
                LoteConvenio.id_convenio == 6
            ).first()
            
            if lote_interno:
                lote_interno_id = lote_interno.id_lote
            else:
                # ── Multi-Tenant e Datas ──
                data_inicio_lote = None
                data_fim_lote = None
                if all_items:
                    try:
                        from datetime import datetime
                        datas = []
                        for item in all_items:
                            dt_str = item.get('dataRealizacao', '')
                            if dt_str:
                                # Tenta parsear, assumindo ISO format ou prefixo
                                dt = datetime.fromisoformat(dt_str.split('T')[0])
                                datas.append(dt.date())
                        if datas:
                            data_inicio_lote = min(datas)
                            data_fim_lote = max(datas)
                    except Exception as e:
                        scraper.log(f"Erro ao extrair datas do lote: {e}", job_id=job_id)

                novo_lote = LoteConvenio(
                    id_convenio=6,
                    numero_lote=int(numero_lote),
                    cod_prestador=codigo_prestador,
                    status="Aberto",
                    user_id=getattr(scraper, 'user_id', None),
                    data_inicio=data_inicio_lote,
                    data_fim=data_fim_lote
                )
                scraper.db.add(novo_lote)
                scraper.db.flush()
                lote_interno_id = novo_lote.id_lote
                scraper.log(f"LoteInterno criado com sucesso (ID Interno: {lote_interno_id})", job_id=job_id)
            
        # 2. Bulk fetch de todos os detalheIds retornados
        detalhe_ids = [item['detalheId'] for item in all_items if 'detalheId' in item]
        existing_items = {}
        
        chunk_size = 900 # Limite de IN clauses no SQLite
        for i in range(0, len(detalhe_ids), chunk_size):
            chunk = detalhe_ids[i:i+chunk_size]
            db_items = scraper.db.query(FaturamentoLote).filter(FaturamentoLote.detalheId.in_(chunk)).all()
            for db_item in db_items:
                existing_items[db_item.detalheId] = db_item
                
        count_inserted = 0
        count_updated = 0
        count_reconciliacao = 0
        novos_itens = []
        # IDs de lotes de agendamento que precisam re-conciliar
        lotes_ag_para_reconciliar = set()

        # 3. Processamento em Memória
        for item in all_items:
            det_id = item['detalheId']
            existing = existing_items.get(det_id)

            new_data_realizacao = item['dataRealizacao']
            new_status = item.get('StatusConferencia', 0)

            if existing:
                # ── Detectar mudanças que invalidam a conciliação ──
                data_mudou = str(existing.dataRealizacao) != str(new_data_realizacao)
                # Status 67 = Conferido; qualquer outro valor indica não-conferido/removido
                status_era_conferido = existing.StatusConferencia == 67
                status_mudou = existing.StatusConferencia != new_status

                deve_desvincular = (
                    existing.agendamento_id is not None and
                    (data_mudou or (status_era_conferido and status_mudou))
                )

                if deve_desvincular:
                    scraper.log(
                        f"OP6 - Detalhe {det_id}: mudança detectada "
                        f"(data_mudou={data_mudou}, status_mudou={status_mudou}). "
                        f"Desvinculando conciliação e marcando para re-conciliação.",
                        job_id=job_id
                    )
                    # Reverter no LoteAgendamentoItem (savepoint para isolar falha)
                    try:
                        from models import LoteAgendamentoItem, LoteAgendamento
                        lai = scraper.db.query(LoteAgendamentoItem).filter(
                            LoteAgendamentoItem.id_faturamento_lote == existing.id
                        ).first()
                        if lai:
                            lotes_ag_para_reconciliar.add(lai.id_lote_ag)
                            lai.status_conciliacao = "Não Conciliado"
                            lai.id_faturamento_lote = None
                    except Exception as ex:
                        # Rollback para recuperar a transação — sem isso o PostgreSQL
                        # rejeita todas as queries seguintes com InFailedSqlTransaction
                        scraper.db.rollback()
                        scraper.log(f"Aviso: falha ao reverter LoteAgendamentoItem (detalhe {det_id}): {ex}", level="WARN", job_id=job_id)

                    existing.agendamento_id = None
                    existing.StatusConciliacao = "pendente"
                    count_reconciliacao += 1


                # Aplicar novos valores do IPASGO
                existing.dataRealizacao = new_data_realizacao
                existing.Guia = str(item['Guia']) if item.get('Guia') else ''
                existing.StatusConferencia = new_status
                existing.ValorProcedimento = item.get('ValorProcedimento', 0.0)
                existing.CodigoBeneficiario = item.get('CodigoBeneficiario', '')
                existing.cod_procedimento_fat = item.get('cod_procedimento_fat', '')
                existing.updated_at = now_utc
                if lote_interno_id:
                    existing.id_lote = lote_interno_id
                count_updated += 1
            else:
                novo = FaturamentoLote(
                    detalheId=det_id,
                    CodigoBeneficiario=item.get('CodigoBeneficiario', ''),
                    dataRealizacao=new_data_realizacao,
                    Guia=str(item['Guia']) if item.get('Guia') else '',
                    StatusConferencia=new_status,
                    ValorProcedimento=item.get('ValorProcedimento', 0.0),
                    cod_procedimento_fat=item.get('cod_procedimento_fat', ''),
                    id_lote=lote_interno_id,
                    StatusConciliacao="pendente",
                    updated_at=now_utc,
                    user_id=getattr(scraper, 'user_id', None)
                )
                novos_itens.append(novo)
                count_inserted += 1

        # 4. Bulk Insert dos novos
        if novos_itens:
            scraper.db.bulk_save_objects(novos_itens)

        scraper.db.commit()
        scraper.log(
            f"Persistência Concluída (Bulk): {count_inserted} inseridos, "
            f"{count_updated} atualizados, {count_reconciliacao} desvinculados para re-conciliação.",
            job_id=job_id
        )

        # 5. Chamar a conciliação automática do backend para lotes afetados
        #    process_conciliacao_bg já gerencia sua própria SessionLocal, Fase 1+2 e cria Jobs OP7.
        if lotes_ag_para_reconciliar:
            try:
                import sys as _sys, os as _os
                _backend_path = _os.path.normpath(
                    _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..', '..', 'backend')
                )
                if _backend_path not in _sys.path:
                    _sys.path.insert(0, _backend_path)
                from routes.conciliacao import process_conciliacao_bg
                from models import LoteAgendamento

                for id_lote_ag in lotes_ag_para_reconciliar:
                    lote_ag = scraper.db.query(LoteAgendamento).filter(
                        LoteAgendamento.id_lote_ag == id_lote_ag
                    ).first()
                    if not lote_ag or not lote_ag.id_lote_convenio:
                        scraper.log(
                            f"OP6 - LoteAg {id_lote_ag} sem lote_convenio vinculado, pulando re-conciliação.",
                            job_id=job_id
                        )
                        continue
                    scraper.log(
                        f"OP6 - Chamando conciliação automática para LoteAg={id_lote_ag} "
                        f"/ LoteConvenio={lote_ag.id_lote_convenio}...",
                        job_id=job_id
                    )
                    process_conciliacao_bg(
                        lote_ag.id_lote_convenio,
                        id_lote_ag,
                        getattr(scraper, 'user_id', None)
                    )
                    scraper.log(
                        f"OP6 - Re-conciliação concluída para LoteAg={id_lote_ag}.",
                        job_id=job_id
                    )
            except Exception as ex:
                scraper.log(f"Aviso: falha ao executar re-conciliação automática: {ex}", level="WARN", job_id=job_id)


    except Exception as e:
        scraper.db.rollback()
        raise RuntimeError(f"Database error persisting FaturamentoLotes: {e}")

    # Return meta for Dispatcher logging (OP6 persists internally)
    return {
        "self_persisted": True,
        "inserted": count_inserted,
        "updated": count_updated,
        "total": len(all_items),
        "reconciliacao_triggered": count_reconciliacao
    }

