"""
OP0 - Login no portal Faturamento (Faturi / Orizon)
Autentica o usuário no portal de faturamento.
"""
from __future__ import annotations
import time
from typing import TYPE_CHECKING
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import sys

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)]
if sys.path[0] != _mod_root:
    sys.path.insert(0, _mod_root)

from core.selenium_helpers import (
    aguardar_elemento,
    preencher_input,
    clicar_elemento,
    elemento_existe,
)
from core.exceptions import MfaMaxCyclesError
from core import mfa_helper

if TYPE_CHECKING:
    from base_scraper import BaseScraper

# Tela de código MFA do Faturi (Keycloak) — seletores fornecidos pelo PO (2026-10-21)
MFA_INPUT_BY = By.ID
MFA_INPUT = "code"
MFA_SUBMIT_XPATH = '//*[@id="kc-form-buttons"]/input'

def run(scraper: BaseScraper, job_data: dict) -> list:
    """
    Executa o login no portal de Faturamento da Orizon.
    """
    job_id = job_data.get("job_id")
    scraper.log("Iniciando OP0 (Login Faturamento)", job_id=job_id)
    driver = scraper.driver

    try:
        driver.get("https://www.orizon.com.br/acesso-restrito.html")
        scraper.log("Acessando página inicial de acesso restrito...", job_id=job_id)

        # Clicar no botão 'Faturi'
        clicar_elemento(driver, By.NAME, "Faturi", timeout=15)
        scraper.log("Botão Faturi clicado, aguardando tela de login...", job_id=job_id)

        # Sessão já ativa? Com o usuário autenticado, o portal pula o formulário
        # e vai direto à área logada — #username nunca aparece (incidentes de
        # retry/20652: a 2ª visita à página explodia no timeout do elemento).
        try:
            aguardar_elemento(driver, By.ID, "username", timeout=10)
        except Exception:
            url_atual = (driver.current_url or "").lower()
            if "fature" in url_atual or "prestador" in url_atual:
                scraper.log("Sessão do Faturi já estava ativa — pulando login.", job_id=job_id)
                _tratar_mensagens_iniciais(scraper, driver, job_id)
                return [{"status": "success", "message": "Login Faturi OK (sessão já ativa)"}]
            raise

        # Preencher credenciais
        scraper.log(f"Preenchendo login para o usuário: {scraper.username}", job_id=job_id)
        preencher_input(driver, By.ID, "username", scraper.username)
        preencher_input(driver, By.ID, "password", scraper.password)

        # Clicar em acessar
        clicar_elemento(driver, By.XPATH, '//*[@id="kc-login"]')
        scraper.log("Credenciais enviadas.", job_id=job_id)

        # Aguardar carregamento da página interna
        time.sleep(3)

        # Verificação de MFA (PO 2026-10-21): o portal pede um código enviado ao
        # usuário (validade de 24h no servidor). Se a tela aparecer, o código é
        # solicitado ao dono do job via banco (modal no frontend) — ver mfa_helper.
        _handle_mfa_if_needed(scraper, driver, job_id)

        # Tratar notificações modais (mensagemImg) que aparecem após login
        _tratar_mensagens_iniciais(scraper, driver, job_id)

        scraper.log("Login de faturamento concluído com sucesso.", job_id=job_id)
        return [{"status": "success", "message": "Login Faturamento OK"}]

    except Exception as e:
        scraper.log(f"Erro no login de faturamento: {str(e)}", level="ERROR", job_id=job_id)
        raise


def _handle_mfa_if_needed(scraper: BaseScraper, driver, job_id):
    """Se a tela de código MFA (#code) estiver visível, conduz o fluxo interativo:
    solicita o código ao usuário (banco → modal), preenche, confirma e valida.

    Sucesso = campo #code deixa de existir após a confirmação. Código rejeitado =
    tela permanece → novo ciclo (máx. mfa_helper.MFA_MAX_CYCLES → MfaMaxCyclesError).
    MfaTimeoutError/MfaCancelledError propagam do helper (erros fatais, sem retry).
    """
    if not elemento_existe(driver, MFA_INPUT_BY, MFA_INPUT, timeout=5):
        return  # Sem MFA — segue o fluxo normal do login

    scraper.log("Tela de código MFA detectada no Faturi", job_id=job_id)
    for ciclo in range(1, mfa_helper.MFA_MAX_CYCLES + 1):
        mfa_helper.solicitar_codigo(scraper, job_id, ciclo)
        codigo = mfa_helper.aguardar_codigo(scraper, job_id)

        campo = driver.find_element(MFA_INPUT_BY, MFA_INPUT)
        campo.clear()
        campo.send_keys(codigo)
        clicar_elemento(driver, By.XPATH, MFA_SUBMIT_XPATH, timeout=10)
        scraper.log("Código MFA informado no portal. Aguardando validação...", job_id=job_id)

        time.sleep(4)
        _dump_html_pos_codigo(driver, ciclo)

        if not elemento_existe(driver, MFA_INPUT_BY, MFA_INPUT, timeout=5):
            scraper.log(f"Código MFA validado pelo portal (ciclo {ciclo})", job_id=job_id)
            mfa_helper.limpar_estado(scraper, job_id)
            return

        scraper.log(
            "Código MFA rejeitado — a tela de código continua visível",
            level="WARN", job_id=job_id,
        )
        if ciclo >= mfa_helper.MFA_MAX_CYCLES:
            raise MfaMaxCyclesError()

    raise MfaMaxCyclesError()


def _dump_html_pos_codigo(driver, ciclo: int):
    """Salva o HTML pós-confirmação do código (material para refinar o mapeamento
    das mensagens de erro do Keycloak na primeira execução real). Best-effort."""
    try:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "scratch", "spike_mfa"))
        os.makedirs(root, exist_ok=True)
        path = os.path.join(root, f"fature_mfa_pos_codigo_ciclo{ciclo}.html")
        with open(path, "w", encoding="utf-8", errors="replace") as f:
            f.write(driver.page_source or "")
    except Exception:
        pass


def _tratar_mensagens_iniciais(scraper: BaseScraper, driver, job_id=None):
    """
    Aguarda e fecha modais de notificação (id='mensagemImg') que aparecem
    após o login no portal Faturamento.
    
    O modal tipicamente demora ~5s para aparecer e pode surgir 2x consecutivas.
    Lógica:
      1. Aguarda 5s
      2. Verifica via JS se mensagemImg tem display:block
      3. Se sim → scroll + click no botão fechar, volta ao passo 1
      4. Se não → aguarda mais 5s e verifica novamente
      5. Se ainda não → modal não existe, segue em frente
    """
    scraper.log("Iniciando verificação de modais pós-login...", job_id=job_id)
    
    modais_fechados = 0
    max_ciclos = 5  # Máximo de verificações (cobre até 2 modais + 1 verificação final)
    
    for ciclo in range(max_ciclos):
        # Aguarda 5s para o modal ter tempo de aparecer
        time.sleep(5)
        
        try:
            # Verificar via JS se o elemento mensagemImg existe e está com display:block
            is_visible = driver.execute_script("""
                var el = document.getElementById('mensagemImg');
                if (!el) return false;
                var style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' && el.offsetParent !== null;
            """)
            
            if is_visible:
                scraper.log(f"Modal mensagemImg detectado (ciclo {ciclo + 1}). Fechando...", job_id=job_id)
                
                # Scroll até o botão e clicar via JS para garantir
                clicked = driver.execute_script("""
                    var btn = document.getElementById('botaoMensagemInicialModalPrestador');
                    if (btn) {
                        btn.scrollIntoView({behavior: 'instant', block: 'center'});
                        btn.click();
                        return true;
                    }
                    return false;
                """)
                
                if clicked:
                    modais_fechados += 1
                    scraper.log(f"Modal fechado com sucesso (total fechados: {modais_fechados})", job_id=job_id)
                    # Aguarda 2s para a animação de fechamento antes do próximo ciclo
                    time.sleep(2)
                    continue  # Volta ao início do loop para verificar se aparece outro
                else:
                    scraper.log("Modal visível mas botão 'botaoMensagemInicialModalPrestador' não encontrado. Tentando fallback...", level="WARN", job_id=job_id)
                    # Fallback: tentar fechar por qualquer botão de fechar dentro do modal
                    driver.execute_script("""
                        var modals = document.querySelectorAll('.modal.show .close, .modal[style*="display: block"] .close, .modal .btn-close');
                        if (modals.length > 0) modals[0].click();
                    """)
                    time.sleep(2)
                    continue
            else:
                if modais_fechados > 0:
                    # Já fechamos pelo menos um modal e agora não apareceu mais — concluído
                    scraper.log(f"Nenhum modal adicional detectado após {modais_fechados} fechamento(s). Prosseguindo.", job_id=job_id)
                    break
                elif ciclo == 0:
                    # Primeira verificação sem modal — esperar mais um ciclo para confirmar
                    scraper.log("Modal não detectado no primeiro ciclo. Aguardando mais 5s para confirmar...", job_id=job_id)
                    continue
                else:
                    # Segunda verificação ou superior sem modal — seguro prosseguir
                    scraper.log("Nenhum modal detectado após verificação adicional. Prosseguindo.", job_id=job_id)
                    break
                    
        except Exception as e:
            scraper.log(f"Erro ao verificar/fechar modal mensagemImg (ciclo {ciclo + 1}): {e}", level="WARN", job_id=job_id)
            if modais_fechados > 0:
                break  # Já fechou algum, provavelmente ok
            continue  # Tentar novamente
    
    if modais_fechados > 0:
        scraper.log(f"Total de modais fechados: {modais_fechados}", job_id=job_id)
    else:
        scraper.log("Nenhum modal mensagemImg apareceu após login.", job_id=job_id)

