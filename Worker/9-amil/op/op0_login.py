"""
OP0 — Login no portal AMIL (credenciado.amil.com.br).

Fluxo (docs/plano_amil_op0_op1.md, T6 — ajustado pelo diagnóstico DevTools de
2026-11-20 no portal real):
  1. driver.get(LOGIN_URL) + POLL 'form OU sessão ativa' (sem corrida: com
     sessão salva no navegador o portal redireciona /login → /home e o form
     NUNCA aparece — temForm=false confirmado);
  2. sessão ativa → extração e retorno direto;
  3. banner OneTrust ANTES de preencher (o overlay do banner INTERCEPTA o
     clique no Entrar — submit não disparava com o banner aberto); click
     Selenium com fallback de click via JS;
  4. preencher login-usuario / login-senha (clear + send_keys);
  5. clicar botão Entrar (XPATH do as-login, fallback JS);
  6. esperar URL sair de '/login' + estabilização (readyState);
     se permaneceu em /login ou há mensagem de erro visível → LoginFailedError
     (prefixo LOGIN_REJEITADO — fatal, sem retry);
  7. extração de sessão/cookies/tokens como EVIDÊNCIA em runtime (decisão D4):
     fonte primária localStorage['acesso-info'] (ver core/session_extractor.py)
     — resumo MASCARADO, nunca o token/cookie completo em result_data;
  8. marca driver.last_login (padrão bradesco: checagem de dono da sessão).
"""
from __future__ import annotations

import os
import sys
import time
from typing import TYPE_CHECKING

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# ── Isolate Environment (mesma defesa do 1-bradesco/102-caesan) ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)]
if sys.path[0] != _mod_root:
    sys.path.insert(0, _mod_root)

from config.constants import (
    LOGIN_URL,
    ID_LOGIN,
    ID_SENHA,
    ID_COOKIES,
    XPATH_BOTAO_ENTRAR,
    COOKIES_RELEVANTES,
    SHORT_TIMEOUT,
    LONG_TIMEOUT,
)
from core.selenium_helpers import (
    preencher_input,
    clicar_elemento,
    elemento_existe,
)
from core.exceptions import LoginFailedError
from core.session_extractor import extrair_tokens_pagina

if TYPE_CHECKING:
    from base_scraper import BaseScraper


def _extrair_tokens(driver) -> dict:
    """Cascata de tokens (a→b→c) — ver core/session_extractor.py (D4)."""
    return extrair_tokens_pagina(driver)


def _capturar_mensagem_erro(driver) -> str:
    """Extrai mensagens de erro VISÍVEIS do componente as-login (span/div de
    erro, alertas). Retorna texto concatenado (máx. 300 chars) ou vazio."""
    try:
        textos = driver.execute_script("""
            var escopo = document.querySelector('as-login') || document.querySelector('form') || document;
            var seletor = [
                '[class*="error"]', '[class*="erro"]', '[role="alert"]',
                '.alert-danger', '.alert', '#input-error'
            ].join(', ');
            var els = escopo.querySelectorAll(seletor);
            var vistos = [];
            els.forEach(function(el) {
                if (!el.offsetParent && el.getClientRects().length === 0) return;  // invisível
                var t = (el.textContent || '').trim();
                if (t && t.length < 400 && vistos.indexOf(t) === -1) vistos.push(t);
            });
            return vistos.slice(0, 3).join(' | ');
        """)
        return (textos or "")[:300]
    except Exception:
        return ""


def _aguardar_form_ou_sessao(driver, scraper, job_id, timeout_s: int = 40):
    """Após driver.get(LOGIN_URL), decide entre 'form de login' e 'sessão já
    ativa' SEM corrida: o SPA demora para bootar — durante o redirect de sessão
    salva a URL pode AINDA estar em /login e o form ainda não renderizou
    (checagem instantânea dava falso LOGIN_REJEITADO — diagnóstico DevTools
    2026-11-20: /login redireciona para /home com temForm=false).

    Poll: form visível OU URL saiu de /login. Retorna True quando o form
    apareceu (seguir com credenciais) e False quando a sessão já está ativa.
    """
    fim = time.time() + timeout_s
    while time.time() < fim:
        try:
            if driver.execute_script(
                "var e = document.getElementById(arguments[0]);"
                "return !!(e && (e.offsetWidth || e.offsetHeight));",
                ID_LOGIN,
            ):
                return True
        except Exception:
            pass
        try:
            if "/login" not in (driver.current_url or "").lower():
                return False
        except Exception:
            pass
        time.sleep(1)
    # Timeout: decide pela URL atual (chamador loga o diagnóstico)
    try:
        return "/login" in (driver.current_url or "").lower()
    except Exception:
        return True


def _aguardar_estabilizacao(driver, job_id, scraper, tentativas: int = 2):
    """Espera o SPA assentar pós-login: readyState=='complete' confirmado em
    2 checagens espaçadas por sleep 3s (rede ociosa aproximada — o SPA Amil
    dispara várias chamadas de boot após o redirect)."""
    for i in range(tentativas):
        try:
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception as e:
            scraper.log(f"readyState não completou na checagem {i + 1}: {e}", level="WARN", job_id=job_id)
        if i < tentativas - 1:
            time.sleep(3)


def _retornar_resumo_sessao(scraper: BaseScraper, driver, job_id) -> list:
    """Extração de sessão/cookies/token como EVIDÊNCIA em runtime (decisão D4)
    e retorno MASCARADO — nunca o token/cookie completo em result_data."""
    cookies = driver.get_cookies() or []
    nomes_cookies = [c.get("name") for c in cookies if c.get("name")]
    relevantes = [n for n in nomes_cookies if n in COOKIES_RELEVANTES or n.startswith("BIGipServer")]

    tokens = _extrair_tokens(driver)
    access_token = tokens.get("authorization")
    # Bearer '<token>' → prefixo dos primeiros 8 chars do TOKEN (não do header)
    prefixo_token = None
    if access_token and access_token.startswith("Bearer "):
        prefixo_token = access_token[len("Bearer "):][:8] + "..."

    scraper.log(
        f"Sessão extraída: {len(cookies)} cookies (relevantes={relevantes or '—'}) | "
        f"authorization={'sim' if access_token else 'não'} | "
        f"x_session={'sim' if tokens.get('x_session') else 'não'} | "
        f"x_user={tokens.get('x_user') or '—'}",
        job_id=job_id,
    )
    return [{
        "login_ok": True,
        "codigo_usuario": tokens.get("x_user") or scraper.cod_prestador,
        "cookies": relevantes or nomes_cookies[:10],
        "autorizacao_presente": bool(access_token),
        "x_session_presente": bool(tokens.get("x_session")),
        "access_token_prefixo": prefixo_token,
        "sessao_valida": True,
    }]


def run(scraper: BaseScraper, job_data: dict) -> list:
    """Executa o login no portal AMIL e devolve o resumo (mascarado) da sessão."""
    job_id = job_data.get("job_id")
    scraper.log("Iniciando OP0 (Login AMIL)", job_id=job_id)
    driver = scraper.driver

    if not scraper.username or not scraper.password:
        raise LoginFailedError(
            "LOGIN_REJEITADO: credenciais ausentes no scraper — configure user_convenios"
        )

    try:
        # 1. Acessar o portal e decidir entre 'form de login' e 'sessão já
        #    ativa' por POLL (sem corrida): com sessão salva no navegador o
        #    portal redireciona /login → /home e o form NUNCA aparece (mesma
        #    defesa do 1-bradesco; diagnóstico DevTools 2026-11-20 confirmou
        #    temForm=false nessa condição).
        driver.get(LOGIN_URL)
        scraper.log(f"Acessando {LOGIN_URL}", job_id=job_id)
        form_apareceu = _aguardar_form_ou_sessao(driver, scraper, job_id, timeout_s=LONG_TIMEOUT)
        url_atual = (driver.current_url or "").lower()

        if "/login" not in url_atual:
            # Sessão AMIL já estava ativa (redirect para /home) — pulando login
            scraper.log("Sessão AMIL já estava ativa — pulando login.", job_id=job_id)
            _aguardar_estabilizacao(driver, job_id, scraper, tentativas=1)
            driver.last_login = scraper.username
            return _retornar_resumo_sessao(scraper, driver, job_id)

        if not form_apareceu:
            # Poll esgotou com a URL presa em /login e form nunca visível:
            # desafio Akamai ('Acesso Negado' — UA headless reprovado na edge)
            # ou página alterada.
            msg = _capturar_mensagem_erro(driver)
            corpo_akamai = "Acesso Negado" in (driver.page_source or "")
            dica = " — Akamai bloqueou a navegação (preferir SGUCARD_HEADLESS=false)" if corpo_akamai else ""
            scraper.log(
                f"Formulário de login não apareceu (url={url_atual}, mensagem={msg or 'nenhuma'}{dica}).",
                level="ERROR", job_id=job_id,
            )
            raise LoginFailedError(
                f"LOGIN_REJEITADO: formulário de login não apareceu (url={url_atual}, "
                f"mensagem={msg or 'nenhuma'}){dica}"
            )

        # 2. Banner de cookies OneTrust ANTES de preencher/clicar: o overlay do
        #    banner INTERCEPTA o clique no Entrar — com o banner aberto o submit
        #    não disparava (diagnóstico DevTools 2026-11-20). Selenium click com
        #    fallback de click via JS (OneTrust pode capturar o elemento).
        try:
            if elemento_existe(driver, By.ID, ID_COOKIES, timeout=SHORT_TIMEOUT):
                try:
                    clicar_elemento(driver, By.ID, ID_COOKIES, timeout=5)
                    acao = "selenium"
                except Exception:
                    driver.execute_script(
                        "var b = document.getElementById(arguments[0]);"
                        "if (b) b.click();",
                        ID_COOKIES,
                    )
                    acao = "js"
                scraper.log(f"Cookies OneTrust aceitos ({acao}).", job_id=job_id)
                time.sleep(1)
        except Exception as e:
            scraper.log(f"Banner OneTrust não clicável (seguindo): {e}", level="WARN", job_id=job_id)

        # 3. Credenciais (preencher_input faz clear antes do send_keys)
        scraper.log(f"Preenchendo login para o usuário: {scraper.username}", job_id=job_id)
        preencher_input(driver, By.ID, ID_LOGIN, scraper.username)
        preencher_input(driver, By.ID, ID_SENHA, scraper.password)

        # 4. Botão Entrar (com fallback de click via JS no mesmo alvo)
        try:
            clicar_elemento(driver, By.XPATH, XPATH_BOTAO_ENTRAR, timeout=15)
            acao_entrar = "selenium"
        except Exception:
            driver.execute_script(
                "var b = document.querySelector('as-login form fieldset button');"
                "if (b) b.click();"
            )
            acao_entrar = "js"
        scraper.log(f"Credenciais enviadas ({acao_entrar}).", job_id=job_id)

        # 5. Aguardar redirecionamento pós-login (URL sai de /login)
        try:
            WebDriverWait(driver, LONG_TIMEOUT).until(
                lambda d: "/login" not in (d.current_url or "").lower()
            )
        except Exception:
            msg = _capturar_mensagem_erro(driver)
            url_atual = driver.current_url or ""
            scraper.log(
                f"Login não efetivou (url={url_atual}, mensagem={msg or 'nenhuma'}).",
                level="ERROR", job_id=job_id,
            )
            raise LoginFailedError(f"LOGIN_REJEITADO: {msg or 'tela de login permaneceu após submit'}")

        _aguardar_estabilizacao(driver, job_id, scraper)

        # Re-checagem pós-estabilização: se o SPA voltou ao login, a sessão
        # não fixou (credencial recusada com redirect tardio).
        url_pos = (driver.current_url or "").lower()
        if "/login" in url_pos:
            msg = _capturar_mensagem_erro(driver)
            raise LoginFailedError(f"LOGIN_REJEITADO: {msg or 'redirecionado de volta ao login após autenticar'}")
        msg_tardia = _capturar_mensagem_erro(driver)
        if msg_tardia:
            scraper.log(f"Mensagem visível pós-login (informativo): {msg_tardia!r}", level="WARN", job_id=job_id)

        # 6. Extração de sessão/cookies/token (resumo mascarado — D4)
        resultado = _retornar_resumo_sessao(scraper, driver, job_id)

        # 7. Marcador de dono da sessão (checagem de user no process_job)
        driver.last_login = scraper.username

        scraper.log("Login AMIL concluído com sucesso.", job_id=job_id)
        return resultado

    except LoginFailedError:
        raise
    except Exception as e:
        scraper.log(f"Erro no login AMIL: {str(e)}", level="ERROR", job_id=job_id)
        raise
