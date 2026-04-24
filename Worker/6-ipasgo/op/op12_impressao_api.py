"""
Op 12 — Impressão de Guias (IPASGO) via Navegação Direta (Estilo API)

Versão aprimorada de OP5:
- Ignora cliques de interface em LocalizarProcedimentos.
- Acessa o relatório de impressão diretamente pela URL alvo, após login e bootstrap da sessão.
- Aciona a impressão (kiosk/print).

Parâmetros (devem constar no job_data):
- guia (Número da Guia Operadora)
- GuiaPrestador (Número da Guia Prestador)
- numero_copias (Opcional, padrão = 1)
"""

import os
import sys
import time
import json
from selenium.webdriver.common.by import By

# ── Isolate Environment (Fix Crosstalk) ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from config.constants import (
    X_LOCALIZAR_NOTY_CONTAINER,
    X_LOCALIZAR_NOTY_FECHAR,
    X_LOCALIZAR_NOTY_MODAL,
    X_ALERT_CLOSE,
    X_ALERT_CLOSE_STRONG,
    X_ALERT_AVISO_BANNER
)

def _close_notification_robust(driver, scraper=None, job_id=None):
    """
    Fecha notificações/modais do FacPlan de forma robusta.
    Replica a lógica consolidada do OP3/OP11.
    """
    def _log(msg):
        if scraper:
            scraper.log(msg, job_id=job_id)

    # Tentativa 1: Botão genérico button-1 (dialog de notificação do FacPlan)
    try:
        btn = driver.find_element(By.ID, "button-1")
        if btn.is_displayed():
            driver.execute_script("arguments[0].click();", btn)
            _log("Notificação fechada via #button-1")
            time.sleep(1)
            return True
    except Exception:
        pass

    # Tentativa 1b: button-1 via XPath
    try:
        btn = driver.find_element(By.XPATH, '//*[@id="button-1"]')
        if btn.is_displayed():
            driver.execute_script("arguments[0].click();", btn)
            _log("Notificação fechada via XPath #button-1")
            time.sleep(1)
            return True
    except Exception:
        pass

    # Tentativa 2: Noty notification closer
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

    # Tentativa 3: Banner de aviso genérico com botão close
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

    # Tentativa 4: Noty modal backdrop
    try:
        modal = driver.find_elements(By.XPATH, X_LOCALIZAR_NOTY_MODAL)
        if modal:
            driver.execute_script("arguments[0].style.display='none';", modal[0])
            _log("Noty modal backdrop removido")
            time.sleep(0.5)
            return True
    except Exception:
        pass

    # Tentativa 5: Busca em iframes (último recurso)
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


def execute(scraper, job_data):
    driver = scraper.driver
    job_id = job_data.get("job_id")

    params_str = job_data.get("params", "")
    p = {}
    if params_str:
        try:
            p = json.loads(params_str) if isinstance(params_str, str) else params_str
        except Exception:
            pass
    else:
        p = job_data

    # Extrai Parâmetros da OP12
    # cod_prestador é ignorado na impressão diretamente
    guia = p.get("guia", "").strip()
    guia_prestador = p.get("GuiaPrestador", "").strip()
    numero_copias = int(p.get("numero_copias") or p.get("copias") or 1)

    if not guia or not guia_prestador:
        msg = "PermanentError: Parâmetros obrigatórios 'guia' e/ou 'GuiaPrestador' ausentes para OP12."
        scraper.log(msg, level="ERROR", job_id=job_id)
        raise ValueError(msg)

    scraper.log(f"OP12 - Iniciado. GuiaOperadora: {guia} | GuiaPrestador: {guia_prestador} | Cópias: {numero_copias}", job_id=job_id)

    # O login já é garantido pelo scraper.py antes de chamar a operação.

    # Passo 2: Navegação Bootstrap (Localizar Procedimentos para carregar o contexto)
    url_bootstrap = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos"
    scraper.log(f"OP12 - Acessando URL Bootstrap: {url_bootstrap}", job_id=job_id)
    driver.get(url_bootstrap)

    # Aguardar carregamento da página
    for _ in range(10):
        try:
            if driver.execute_script("return document.readyState;") == "complete":
                break
        except Exception:
            pass
        time.sleep(1)
    time.sleep(2)

    # Passo 3: Fechar Notificações
    scraper.log("OP12 - Procurando e fechando notificações...", job_id=job_id)
    notification_closed = False
    for attempt in range(4):
        if _close_notification_robust(driver, scraper, job_id):
            notification_closed = True
            scraper.log(f"OP12 - Notificação fechada na tentativa {attempt + 1}", job_id=job_id)
            break
        time.sleep(1)
    
    if not notification_closed:
        scraper.log("OP12 - Nenhuma notificação ou já fechada.", job_id=job_id)
    time.sleep(1)

    # Passo 4: Navegar diretamente para URL de impressão (NovaViewRelatorioGuiaSPSADT)
    url_impressao = f"https://novowebplanipasgo.facilinformatica.com.br/Relatorios/NovaViewRelatorioGuiaSPSADT?NumGuiaOperadora={guia}&NumGuiaPrestador={guia_prestador}"
    scraper.log(f"OP12 - Navegando para URL do Relatório: {url_impressao}", job_id=job_id)
    driver.get(url_impressao)

    # Aguardar renderização do relatório
    for _ in range(10):
        try:
            if driver.execute_script("return document.readyState;") == "complete":
                break
        except Exception:
            pass
        time.sleep(1)
    
    scraper.log("OP12 - Relatório carregado. Aguardando 3 segundos de estabilização...", job_id=job_id)
    time.sleep(3)

    # Passo 5: Imprimir (Estilo Kiosk Mode / Print Automation)
    scraper.log("OP12 - Ajustando zoom para 90% antes da impressão...", job_id=job_id)
    try:
        driver.execute_script("document.body.style.zoom='90%'")
        time.sleep(1)
    except Exception as e:
        scraper.log(f"OP12 - Falha ao definir zoom (ignorável): {e}", level="WARN", job_id=job_id)

    scraper.log(f"OP12 - Disparando window.print() para {numero_copias} cópia(s)...", job_id=job_id)
    for i in range(numero_copias):
        try:
            scraper.log(f"OP12 - Solicitando impressão {i+1}/{numero_copias}...", job_id=job_id)
            driver.execute_script("window.print();")
            time.sleep(2) # Pausa entre cópias para o SO processar o spooler
        except Exception as e:
            scraper.log(f"OP12 - Erro ao acionar impressão: {e}", level="ERROR", job_id=job_id)
            raise

    scraper.log("OP12 - Impressão concluída com sucesso.", job_id=job_id)
    
    return [{"numero_guia": guia, "copias_impressas": numero_copias, "sucesso": True}]
