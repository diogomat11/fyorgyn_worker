import os
import sys
import logging
import re
import time
from sqlalchemy.dialects.postgresql import insert
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from core.webplan_client import WebPlanClient
from config.constants import (
    X_LOCALIZAR_NOTY_CONTAINER,
    X_LOCALIZAR_NOTY_FECHAR,
    X_LOCALIZAR_NOTY_MODAL,
    X_ALERT_CLOSE,
    X_ALERT_CLOSE_STRONG,
    X_ALERT_AVISO_BANNER,
    DEFAULT_TIMEOUT,
)

try:
    from models import Guias, GuiaIpasgo  # Replace with actual model used in worker
except ImportError:
    backend_path = os.path.join(os.path.dirname(os.path.dirname(_mod_root)), 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    # from models import ...

def wait_xpath(driver, xpath, timeout=5):
    try:
        wait = WebDriverWait(driver, timeout)
        return wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
    except Exception:
        return None

def _parse_aspnet_date(date_val):
    """
    Converte timestamps ASP.NET (/Date(1234567890000)/) e strings ISO para datetime.date.
    Suporta:
      - "/Date(1713045600000)/"     → ASP.NET timestamp em milissegundos
      - "/Date(1713045600000-0300)/" → com offset
      - "2026-04-18T00:00:00"       → ISO format
      - "18/04/2026"                → dd/mm/yyyy
    Retorna None se não conseguir parsear.
    """
    if not date_val:
        return None
    
    if isinstance(date_val, str):
        # ASP.NET /Date(...)/ format
        match = re.search(r'/Date\((\d+)([+-]\d{4})?\)/', date_val)
        if match:
            ms = int(match.group(1))
            return datetime.utcfromtimestamp(ms / 1000.0).date()
        
        # ISO format (yyyy-mm-ddTHH:MM:SS)
        clean = date_val.strip()[:10]
        try:
            if "-" in clean and len(clean) == 10:
                return datetime.strptime(clean, "%Y-%m-%d").date()
        except ValueError:
            pass
        
        # dd/mm/yyyy
        try:
            return datetime.strptime(clean, "%d/%m/%Y").date()
        except ValueError:
            pass
    
    return None

def _normalizar_codigo(code_str):
    """
    Remove '.' e '-' de códigos de procedimento/terapia (CodigoAMB).
    Exemplo: "22.50.10-07" → "22501007"
    """
    if not code_str:
        return ""
    return str(code_str).replace(".", "").replace("-", "").strip()

def _close_notification_robust(driver, scraper=None, job_id=None):
    """
    Fecha notificações/modais do FacPlan de forma robusta.
    Replica a lógica consolidada do OP3 usando os XPaths do config/constants.py.
    """
    def _log(msg):
        if scraper:
            scraper.log(msg, job_id=job_id)

    # ── Tentativa 1: Botão genérico button-1 (dialog de notificação do FacPlan) ──
    try:
        btn = driver.find_element(By.ID, "button-1")
        if btn.is_displayed():
            driver.execute_script("arguments[0].click();", btn)
            _log("Notificação fechada via #button-1")
            time.sleep(1)
            return True
    except Exception:
        pass

    # ── Tentativa 1b: button-1 via XPath (caso o ID não resolva diretamente) ──
    try:
        btn = driver.find_element(By.XPATH, '//*[@id="button-1"]')
        if btn.is_displayed():
            driver.execute_script("arguments[0].click();", btn)
            _log("Notificação fechada via XPath #button-1")
            time.sleep(1)
            return True
    except Exception:
        pass

    # ── Tentativa 2: Noty notification closer (X_LOCALIZAR_NOTY_FECHAR) ──
    try:
        noty_container = driver.find_elements(By.XPATH, X_LOCALIZAR_NOTY_CONTAINER)
        if noty_container:
            btn = driver.find_element(By.XPATH, X_LOCALIZAR_NOTY_FECHAR)
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                _log("Notificação fechada via X_LOCALIZAR_NOTY_FECHAR")
                time.sleep(1)
                return True
    except Exception:
        pass

    # ── Tentativa 3: Banner de aviso genérico com botão close ──
    try:
        banner = driver.find_elements(By.XPATH, X_ALERT_AVISO_BANNER)
        if banner:
            btn = driver.find_elements(By.XPATH, X_ALERT_CLOSE)
            if not btn:
                btn = driver.find_elements(By.XPATH, X_ALERT_CLOSE_STRONG)
            if btn:
                try:
                    btn[0].click()
                except Exception:
                    driver.execute_script("arguments[0].click();", btn[0])
                _log("Banner de aviso fechado via X_ALERT_CLOSE")
                time.sleep(1)
                return True
    except Exception:
        pass

    # ── Tentativa 4: Noty modal backdrop ──
    try:
        modal = driver.find_elements(By.XPATH, X_LOCALIZAR_NOTY_MODAL)
        if modal:
            driver.execute_script("arguments[0].style.display='none';", modal[0])
            _log("Noty modal backdrop removido")
            time.sleep(0.5)
            return True
    except Exception:
        pass

    # ── Tentativa 5: Busca em iframes (último recurso) ──
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for i in range(len(iframes)):
            try:
                driver.switch_to.frame(i)
                btn = driver.find_element(By.ID, "button-1")
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    _log(f"Notificação fechada dentro do iframe {i}")
                    time.sleep(1)
                    driver.switch_to.default_content()
                    return True
            except Exception:
                pass
            finally:
                driver.switch_to.default_content()
    except Exception:
        pass

    return False


def _save_rows_local(rows, logger):
    try:
        from database import SessionLocal
        from models import BaseGuia, Carteirinha
        from sqlalchemy import or_
        db_session = SessionLocal()
        try:
            count_inserted = 0
            count_updated = 0
            for row_data in rows:
                if not row_data.get("numero_guia"):
                    continue
                
                guia_num = str(row_data["numero_guia"])
                cod_terapia = row_data.get("codigo_terapia") or ""
                
                # ── Busca em 2 fases para evitar duplicatas ──
                # Fase 1: Match exato (guia + codigo_terapia + id_convenio)
                guia_record = None
                if cod_terapia:
                    guia_record = db_session.query(BaseGuia).filter(
                        BaseGuia.guia == guia_num,
                        BaseGuia.id_convenio == 6,
                        BaseGuia.codigo_terapia == cod_terapia
                    ).first()
                
                # Fase 2: Fallback — registro existente com codigo_terapia NULL/vazio
                # (criado por OP3 que ainda não tinha o código)
                if not guia_record:
                    guia_record = db_session.query(BaseGuia).filter(
                        BaseGuia.guia == guia_num,
                        BaseGuia.id_convenio == 6,
                        or_(
                            BaseGuia.codigo_terapia == None,
                            BaseGuia.codigo_terapia == ""
                        )
                    ).first()
                
                if not guia_record:
                    guia_record = BaseGuia(
                        guia=guia_num,
                        codigo_terapia=cod_terapia,
                        id_convenio=6
                    )
                    db_session.add(guia_record)
                    count_inserted += 1
                else:
                    count_updated += 1
                
                guia_record.status_guia = row_data.get("status_guia")
                guia_record.senha = row_data.get("senha")
                guia_record.nome_terapia = row_data.get("nome_terapia")
                
                if "guia_prestador" in row_data:
                    guia_record.guia_prestador = row_data["guia_prestador"]
                
                if cod_terapia:
                    guia_record.codigo_terapia = cod_terapia
                
                if row_data.get("data_autorizacao"):
                    guia_record.data_autorizacao = row_data["data_autorizacao"]
                
                if row_data.get("validade"):
                    guia_record.validade = row_data["validade"]
                
                if row_data.get("qtde_solicitada") is not None:
                    guia_record.qtde_solicitada = row_data["qtde_solicitada"]
                
                if row_data.get("sessoes_autorizadas") is not None:
                    guia_record.sessoes_autorizadas = row_data["sessoes_autorizadas"]
                
                if row_data.get("codigo_beneficiario"):
                    guia_record.codigo_beneficiario = row_data["codigo_beneficiario"]
                    cart = db_session.query(Carteirinha).filter(Carteirinha.codigo_beneficiario == row_data["codigo_beneficiario"]).first()
                    if cart:
                        guia_record.carteirinha_id = cart.id

            db_session.commit()
            if logger:
                logger.info(f"Salvos {count_inserted} novos, {count_updated} atualizados em base_guias locais (Worker DB)")
        finally:
            db_session.close()
    except Exception as db_err:
        if logger:
            logger.error(f"Erro ao salvar base_guias locais: {db_err}")

def run(scraper, job_data):
    """
    OP11 - Importar Guias via API HTTP - IPASGO
    Substitui a extração via Selenium mantendo o uso da sessão da OP0.
    """
    driver = scraper.driver
    job_id = job_data.get("job_id")
    
    # Extração de parâmetros (com .strip() defensivo contra \r\n do frontend)
    codigo_prestador = job_data.get("codigoPrestador", "").strip()
    carteira = job_data.get("carteira", "").strip()
    codigo_beneficiario = job_data.get("codigoBeneficiario", "").strip()
    guia_str = job_data.get("guia", "").strip()
    data_ini = job_data.get("data_ini", "").strip()
    data_fim = job_data.get("data_fim", "").strip()
    situacao = job_data.get("situacao", "").strip()
    
    scraper.log("OP11 - Iniciando extração de guias via API (WebPlanClient)...", job_id=job_id)
    scraper.log(f"OP11 - Params: prestador='{codigo_prestador}' data_ini='{data_ini}' data_fim='{data_fim}' guia='{guia_str}' benef='{codigo_beneficiario}'", job_id=job_id)
    
    # ══════════════════════════════════════════════════════════════════════
    # 1. Navegação Bootstrap — Garante cookies do módulo GuiasTISS/LocalizarProcedimentos
    # ══════════════════════════════════════════════════════════════════════
    url_bootstrap = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos"
    scraper.log(f"OP11 - Acessando URL Bootstrap para setup de contexto: {url_bootstrap}", job_id=job_id)
    driver.get(url_bootstrap)
    
    # Aguardar carregamento completo da página (readyState + tempo mínimo)
    for _ in range(10):
        try:
            state = driver.execute_script("return document.readyState;")
            if state == "complete":
                break
        except Exception:
            pass
        time.sleep(1)
    time.sleep(2)  # tempo adicional para notificações assíncronas renderizarem
    
    # ══════════════════════════════════════════════════════════════════════
    # 1.1 Fechar notificação do FacPlan (mesmo fluxo do OP3)
    # ══════════════════════════════════════════════════════════════════════
    scraper.log("OP11 - Procurando notificação para fechar...", job_id=job_id)
    notification_closed = False
    for attempt in range(5):
        if _close_notification_robust(driver, scraper, job_id):
            notification_closed = True
            scraper.log(f"OP11 - Notificação fechada na tentativa {attempt + 1}", job_id=job_id)
            break
        time.sleep(1)
    
    if not notification_closed:
        scraper.log("OP11 - Nenhuma notificação detectada (ou já fechada). Prosseguindo...", job_id=job_id)
    
    # Aguardar estabilizar após fechar notificação
    time.sleep(1)
    
    # ══════════════════════════════════════════════════════════════════════
    # 2. Inicialização do Client com Referer correto para LocalizarProcedimentos
    # ══════════════════════════════════════════════════════════════════════
    client = WebPlanClient(driver, referer_url=url_bootstrap)
    
    current_page = 1
    has_next_page = True
    todas_guias_extraidas = []
    
    scraper.log("OP11 - Iniciando loop de paginação...", job_id=job_id)
    
    while has_next_page:
        scraper.log(f"Consultando página {current_page}...", job_id=job_id)
        
        response_json = client.post_consultar_guias(
            page=current_page,
            codigo_prestador=codigo_prestador,
            guia=guia_str,
            data_ini=data_ini,
            data_fim=data_fim,
            carteira=carteira,
            codigo_beneficiario=codigo_beneficiario,
            situacao=situacao
        )
        
        procedimentos = response_json.get("Procedimentos", [])
        
        if not procedimentos or len(procedimentos) == 0:
            scraper.log(f"Página {current_page} retornou 0 procedimentos. Fim da extração.", job_id=job_id)
            has_next_page = False
            break
        
        scraper.log(f"Extraídos {len(procedimentos)} procedimentos da página {current_page}", job_id=job_id)
        
        for item in procedimentos:
            # ══════════════════════════════════════════════════════════════
            # 3. Normalização — Granularidade: 1 linha por (guia + CodigoAMB)
            #
            # Exemplo: Guia 22014292 com 4 CodigoAMBs distintos gera 4 linhas:
            #   22014292 | 0.00.11.18-5 | qtde=30
            #   22014292 | 0.00.40.04-5 | qtde=15
            #   22014292 | 5.00.00.16-0 | qtde=5
            #   22014292 | 0.00.11.19-3 | qtde=30
            # ══════════════════════════════════════════════════════════════
            
            # ── Campos compartilhados (nível raiz da guia) ──
            numero_guia = item.get("NumeroGuiaOperadora")
            if not numero_guia:
                chaves = item.get("ChavesUtLib", [])
                numero_guia = chaves[0] if chaves else None

            # NumeroGuiaPrestador está na raiz de cada procedimento (mesmo nível de NumeroGuiaOperadora)
            numero_guia_prestador = item.get("NumeroGuiaPrestador")

            status_guia = item.get("SituacaoTiss") or ""
            if not status_guia:
                status_guia = item.get("Situacao") or ""
                if not status_guia:
                    situacoes = item.get("Situacoes", [])
                    status_guia = situacoes[0] if situacoes else ""
            
            data_autorizacao = _parse_aspnet_date(item.get("DtLiberacao"))
            
            senha = item.get("Senha") or ""
            if isinstance(senha, str):
                senha = senha.strip()
            
            validade = _parse_aspnet_date(item.get("DataValidadeSenha"))
            has_senha = item.get("HasSenha", False)
            
            estados_aprovados = ["Autorizado", "Liberado", "Parcialmente autorizada"]
            necessita_senha = status_guia in estados_aprovados and has_senha == False
            
            # ── Agrupar Itens por CodigoAMB ──
            itens = item.get("Itens", [])
            
            grupos_por_amb = {}  # { "0.00.11.18-5": [item1, item2, ...], ... }
            for it in itens:
                amb = it.get("CodigoAMB", "")
                if amb not in grupos_por_amb:
                    grupos_por_amb[amb] = []
                grupos_por_amb[amb].append(it)
            
            # Se não há itens, gerar pelo menos 1 linha com dados do nível raiz
            if not grupos_por_amb:
                grupos_por_amb[""] = []
            
            # ── Gerar 1 linha de saída por CodigoAMB ──
            for codigo_amb_raw, itens_do_grupo in grupos_por_amb.items():
                codigo_terapia = _normalizar_codigo(codigo_amb_raw)
                
                # Nome e descrição do primeiro item do grupo
                primeiro_item = itens_do_grupo[0] if itens_do_grupo else {}
                nome_terapia = primeiro_item.get("Descricao", "")
                
                # Contagens escopo do CodigoAMB
                qtde_solicitada = len(itens_do_grupo)
                sessoes_autorizadas = sum(
                    1 for it in itens_do_grupo
                    if str(it.get("Situacao", "")).strip().lower() == "autorizado"
                )
                
                guia_normalizada = {
                    "codigo_beneficiario": item.get("CodigoBenficiario"),
                    "nome_beneficiario": item.get("NomeBeneficiario"),
                    "codigo_prestador": item.get("CodigoPrestador"),
                    "nome_prestador": item.get("NomePrestador"),
                    "numero_guia": numero_guia,
                    "guia_prestador": numero_guia_prestador,
                    "status_guia": status_guia,
                    "codigo_terapia": codigo_terapia,
                    "data_autorizacao": data_autorizacao,
                    "senha": senha,
                    "validade": validade,
                    "nome_terapia": nome_terapia,
                    "qtde_solicitada": qtde_solicitada,
                    "sessoes_autorizadas": sessoes_autorizadas,
                    "necessita_senha": necessita_senha,
                    "has_senha": has_senha,
                    "email_beneficiario": item.get("EmailBeneficiario")
                }
                todas_guias_extraidas.append(guia_normalizada)
        
        current_page += 1
        
    scraper.log(f"OP11 - Extração concluída. Total de linhas (guia+procedimento): {len(todas_guias_extraidas)}", job_id=job_id)
    
    # 4. Persistência — Upsert por chave composta (guia + codigo_terapia + id_convenio)
    _save_rows_local(todas_guias_extraidas, scraper.logger if hasattr(scraper, 'logger') else logging.getLogger())
    
    return todas_guias_extraidas
