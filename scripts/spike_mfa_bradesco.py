"""
SPIKE-01 (docs/plano_mfa_bradesco.md — FASE 0) — Verificação de MFA no login Bradesco.

Abre Chrome VISÍVEL (headless off), replica o login de um dos portais e observa a
tela pós-submit para classificar: MFA solicitado / sessão já logada / erro / login OK.
Se a tela de código MFA aparecer, o OPERADOR digita o código manualmente na janela do
Chrome (o script apenas espera e monitora até a tela avançar).

Uso (a partir de Local_worker/):
  python scripts/spike_mfa_bradesco.py            # portal AUTORIZE (Polimed/Orizon)
  python scripts/spike_mfa_bradesco.py fature     # portal FATURAMENTO (Faturi/Keycloak)

Saídas em ../scratch/spike_mfa/:
  <portal>_pos_submit.html   — tela logo após o submit (fonte dos seletores MFA)
  <portal>_final.html        — tela final (login concluído / MFA / erro)
  <portal>_relatorio.txt     — linha do tempo + veredito

Notas:
  - Fecha o Chrome com quit() SEM logoff (nunca clica em "Sair" — direção D8 do plano).
  - Chrome em --incognito (padrão do SeleniumManager): cookies NÃO persistem entre
    execuções — se o MFA não aparecer mesmo com driver novo, é indício forte de
    validação 1x/dia server-side (não cookie de dispositivo).
"""
import os
import sys
import time
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_script_dir = os.path.dirname(os.path.abspath(__file__))
_worker_root = os.path.join(_script_dir, "..", "Worker")
sys.path.insert(0, _worker_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(_script_dir, "..", ".env"))

from database import SessionLocal
from models import UserConvenio
from security_utils import decrypt_password
from selenium_manager import SeleniumManager
from selenium.webdriver.common.by import By

# ── Config ──
PORTAL = (sys.argv[1] if len(sys.argv) > 1 else "autorize").lower()
USER_ID = int(os.getenv("BRADESCO_SPIKE_USER_ID", "14"))
ID_CONVENIO = 1
MFA_WAIT_S = int(os.getenv("BRADESCO_SPIKE_MFA_WAIT", "300"))  # espera operador
OUT_DIR = os.path.abspath(os.path.join(_script_dir, "..", "..", "scratch", "spike_mfa"))
os.makedirs(OUT_DIR, exist_ok=True)

AUTORIZE_URL = "https://www.polimed.com.br/autenticadorOrizon/loginAutenticador"
FATURE_URL = "https://www.orizon.com.br/acesso-restrito.html"

# Heurística de tela MFA (SPIKE: ainda sem seletores oficiais — DEV-01 do plano)
INPUT_HINTS = ["codigo", "código", "token", "otp", "verificacao", "verificação",
               "digito", "dígito", "code", "chave"]
TEXT_HINTS = ["código de verificação", "codigo de verificação", "código de segurança",
              "codigo de segurança", "código enviado", "codigo enviado", "token de acesso",
              "verificação em duas etapas", "verificacao em duas etapas", "foi enviado para",
              "autenticação adicional", "autenticacao adicional", "one-time", "senha única"]
EXCLUDE_INPUTS = ["usuario.login", "senha", "username", "password", "login", "cnpj",
                  "submit", "button", "checkbox", "radio", "file", "email"]

timeline = []


def ts(msg):
    linha = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(linha, flush=True)
    timeline.append(linha)


def dump_html(driver, nome):
    path = os.path.join(OUT_DIR, nome)
    try:
        with open(path, "w", encoding="utf-8", errors="replace") as f:
            f.write(driver.page_source or "")
        ts(f"HTML salvo: {path}")
    except Exception as e:
        ts(f"Falha ao salvar HTML {nome}: {e}")


def creds():
    db = SessionLocal()
    try:
        uc = db.query(UserConvenio).filter(
            UserConvenio.user_id == USER_ID,
            UserConvenio.id_convenio == ID_CONVENIO
        ).first()
        if not uc or not uc.login or not uc.senha_criptografada:
            raise SystemExit(f"[ERRO] user_convenios sem credenciais para user_id={USER_ID} convenio={ID_CONVENIO}")
        return uc.login, decrypt_password(uc.senha_criptografada), uc.cod_prestador
    finally:
        db.close()


def visivel(el):
    try:
        return el.is_displayed() and el.get_attribute("type") not in ("hidden",)
    except Exception:
        return False


def classify(driver):
    """Classifica a tela atual: mfa | sessao_ja_logada | erro_login | login_ok | aguardando."""
    try:
        url = (driver.current_url or "").lower()
    except Exception:
        url = ""

    # Erro de credencial (indicadores do op0_login + span.erro-titulo observado no portal
    # em 2026-10-20: "Usuário ou senha inválido(s). Verifique e tente novamente.")
    for xp in ("//div[contains(@class,'alert-danger')]",
               "//span[contains(@class,'erro-titulo')]",
               "//*[contains(text(),'Usuário ou senha inválido')]"):
        try:
            if driver.find_elements(By.XPATH, xp) and visivel(driver.find_element(By.XPATH, xp)):
                return "erro_login", "alert-danger/credencial inválida"
        except Exception:
            pass

    # Sessão já logada em outro dispositivo (tratamento existente do op0_login)
    derrubar = "//*[contains(text(),'derrubar') or contains(text(),'desconectar') or contains(text(),'encerrar a outra') or contains(text(),'Forçar')]"
    try:
        els = driver.find_elements(By.XPATH, derrubar)
        if els and visivel(els[0]):
            return "sessao_ja_logada", els[0].text[:80]
    except Exception:
        pass

    # Login concluído: botão Sair/Desconectar visível ou saiu da URL de login
    try:
        sair = driver.find_elements(By.XPATH, "//*[contains(text(),'Sair') or contains(text(),'Desconectar')]")
        if any(visivel(e) for e in sair):
            return "login_ok", "botão Sair/Desconectar visível"
    except Exception:
        pass
    if "loginautenticador" not in url and "orizon.com.br" in url and "acesso-restrito" not in url:
        return "login_ok", f"URL fora do login: {url[:90]}"

    # Tela MFA: input suspeito visível (name/id/placeholder com hint, maxlength 4-8)
    try:
        for el in driver.find_elements(By.TAG_NAME, "input"):
            if not visivel(el):
                continue
            tipo = (el.get_attribute("type") or "").lower()
            if tipo in ("hidden", "submit", "button", "checkbox", "radio", "file"):
                continue
            ident = " ".join(filter(None, [el.get_attribute("name"), el.get_attribute("id"),
                                           el.get_attribute("placeholder")])).lower()
            if any(x in ident for x in EXCLUDE_INPUTS):
                continue
            if any(h in ident for h in INPUT_HINTS):
                return "mfa", f"input suspeito: ident='{ident}' type={tipo}"
            try:
                ml = el.get_attribute("maxlength")
                if ml and ml.isdigit() and 4 <= int(ml) <= 8 and tipo in ("text", "tel", "number", "password"):
                    return "mfa", f"input numérico curto: ident='{ident}' maxlength={ml}"
            except Exception:
                pass
    except Exception:
        pass

    # Texto da página com frase típica de envio de código
    try:
        body = (driver.find_element(By.TAG_NAME, "body").text or "").lower()
        for h in TEXT_HINTS:
            if h in body:
                return "mfa", f"texto na página: '{h}'"
    except Exception:
        pass

    return "aguardando", ""


def submit_autorize(driver, login, senha):
    driver.get(AUTORIZE_URL)
    ts(f"Navegou para {AUTORIZE_URL}")
    time.sleep(2)
    from selenium.webdriver.support.ui import WebDriverWait
    WebDriverWait(driver, 15).until(lambda d: d.find_elements(By.NAME, "usuario.login"))
    d = driver.find_element(By.NAME, "usuario.login"); d.clear(); d.send_keys(login)
    p = driver.find_element(By.ID, "senha"); p.clear(); p.send_keys(senha)
    driver.find_element(By.XPATH, "//*[@id='formLogin']/button").click()
    ts("Credenciais submetidas (Acessar).")


def submit_fature(driver, login, senha):
    driver.get(FATURE_URL)
    ts(f"Navegou para {FATURE_URL}")
    time.sleep(2)
    from selenium.webdriver.support.ui import WebDriverWait
    WebDriverWait(driver, 15).until(lambda d: d.find_elements(By.NAME, "Faturi"))
    driver.find_element(By.NAME, "Faturi").click()
    ts("Botão Faturi clicado.")
    WebDriverWait(driver, 15).until(lambda d: d.find_elements(By.ID, "username"))
    u = driver.find_element(By.ID, "username"); u.clear(); u.send_keys(login)
    p = driver.find_element(By.ID, "password"); p.clear(); p.send_keys(senha)
    driver.find_element(By.ID, "kc-login").click()
    ts("Credenciais submetidas (kc-login).")


def main():
    login, senha, prestador = creds()
    ts(f"SPIKE-01 Bradesco — portal={PORTAL} user_id={USER_ID} login={login} prestador={prestador}")
    ts("Chrome: VISÍVEL (headless off), --incognito (driver novo = cookies zerados)")

    manager = SeleniumManager(max_drivers=1)
    driver = manager.get_driver(ID_CONVENIO, headless=False, user_id=USER_ID)

    veredito = {"estado": "desconhecido", "evidencia": ""}
    try:
        if PORTAL == "fature":
            submit_fature(driver, login, senha)
        else:
            submit_autorize(driver, login, senha)

        time.sleep(3)
        dump_html(driver, f"{PORTAL}_pos_submit.html")

        mfa_avisado = False
        deadline = time.time() + MFA_WAIT_S
        while time.time() < deadline:
            estado, evid = classify(driver)
            url = (driver.current_url or "")[:100]

            if estado == "sessao_ja_logada":
                ts(f"SESSÃO JÁ LOGADA detectada ({evid}) — clicando para forçar (comportamento atual do op0_login)...")
                try:
                    driver.find_element(By.XPATH, "//*[contains(text(),'derrubar') or contains(text(),'desconectar') or contains(text(),'encerrar a outra') or contains(text(),'Forçar')]").click()
                except Exception as e:
                    ts(f"Falha ao clicar em derrubar: {e}")
                time.sleep(3)
                continue

            if estado == "mfa" and not mfa_avisado:
                mfa_avisado = True
                deadline = time.time() + MFA_WAIT_S  # renova o prazo para digitação
                ts("=" * 70)
                ts(">>> TELA DE CÓDIGO MFA DETECTADA <<<")
                ts(f">>> evidência: {evid}")
                ts(">>> DIGITE O CÓDIGO NA JANELA DO CHROME ABERTA (manualmente).")
                ts(f">>> Aguardando até {MFA_WAIT_S}s pela digitação/avanço da tela...")
                ts("=" * 70)
                dump_html(driver, f"{PORTAL}_mfa.html")

            if estado == "login_ok":
                veredito = {"estado": "login_ok", "evidencia": evid}
                ts(f"LOGIN CONCLUÍDO — {evid} | URL: {url}")
                break

            if estado == "erro_login":
                veredito = {"estado": "erro_login", "evidencia": evid}
                ts(f"ERRO DE LOGIN — {evid} | URL: {url}")
                break

            time.sleep(5)
        else:
            if mfa_avisado:
                veredito = {"estado": "mfa_timeout_operador", "evidencia": "MFA apareceu e não foi digitado a tempo"}
                ts("Timeout aguardando digitação do código MFA.")
            else:
                veredito = {"estado": "inconclusivo", "evidencia": "tela não classificada no prazo"}
                ts("Estado final não classificado (aguardando).")

        dump_html(driver, f"{PORTAL}_final.html")
    finally:
        rel = os.path.join(OUT_DIR, f"{PORTAL}_relatorio.txt")
        with open(rel, "w", encoding="utf-8") as f:
            f.write("\n".join(timeline) + "\n")
        ts(f"VEREDITO: {veredito['estado']} — {veredito['evidencia']}")
        ts(f"Relatório: {rel}")
        ts("Fechando Chrome com quit() SEM logoff (nunca clicamos em 'Sair').")
        try:
            driver.quit()
        except Exception:
            pass

    print(f"\n===== RESULTADO SPIKE ({PORTAL}) =====")
    print(f"estado  : {veredito['estado']}")
    print(f"evidencia: {veredito['evidencia']}")
    print(f"mfa_pedido: {'SIM' if mfa_avisado else 'NÃO'}")


if __name__ == "__main__":
    main()
