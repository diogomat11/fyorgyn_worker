"""
OP1 - Autorizar FacPlan (GuiaSPSADT) — IPASGO
==============================================
Lança autorização de guia SP/SADT no portal FacPlan IPASGO.

Parâmetros esperados no job_data:
    carteira                - Número da carteira (com ou sem . e -)
    paciente_CID            - Indicação clínica / CID
    dataSolicitacao         - Data de solicitação (DD/MM/AAAA, DD-MM-AAAA ou DDMMAAAA)
    codigoProcedimento_aut  - Código TUSS do procedimento
    qtde                    - Quantidade solicitada
    profissional_codigo_ipasgo - Código IPASGO do prof. executante (opcional)
    profissional_CBO        - CBO do profissional 6 dígitos (opcional)
    texto_Justificativa     - Texto para justificativa/observação/auditoria
    anexo_RM                - Pedido médico: URL ou caminho local (opcional)
    anexo_AI                - Avaliação inicial: URL ou caminho local (opcional)
    anexo_RC                - Relatório clínico: URL ou caminho local (obrigatório validar)
"""
from __future__ import annotations

import os
import re
import sys
import time
import tempfile
import urllib.request
from typing import Optional, TYPE_CHECKING

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0:1].isdigit() and p != _mod_root)]
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from config.constants import (
    DEFAULT_TIMEOUT,
    SHORT_TIMEOUT,
    LONG_TIMEOUT,
    X_LOCALIZAR_NOTY_CONTAINER,
    X_LOCALIZAR_NOTY_FECHAR,
    X_LOCALIZAR_NOTY_MODAL,
    X_ALERT_CLOSE,
    X_ALERT_CLOSE_STRONG,
    X_ALERT_AVISO_BANNER,
    # OP1 constants
    X_AUTFACPLAN_URL,
    X_AUTFACPLAN_CLICK_CARTAO,
    X_AUTFACPLAN_INPUT_CARTEIRA,
    X_AUTFACPLAN_NOME_BENEF,
    X_AUTFACPLAN_CARAT_ATEND,
    X_AUTFACPLAN_CARAT_ATEND_OPT2,
    X_AUTFACPLAN_DATA_SOLICIT,
    X_AUTFACPLAN_INDICACAO_CLIN,
    X_AUTFACPLAN_MENU_PROC,
    X_AUTFACPLAN_BTN_INCLUIR_PROC,
    X_AUTFACPLAN_INPUT_COD_PROC,
    X_AUTFACPLAN_INPUT_QT_PROC,
    X_AUTFACPLAN_BTN_CONF_PROC,
    X_AUTFACPLAN_SPAN_MSG_GENERICA,
    X_AUTFACPLAN_MENU_EXEC,
    X_AUTFACPLAN_BTN_INCLUIR_PROF,
    X_AUTFACPLAN_INPUT_GRAU,
    X_AUTFACPLAN_INPUT_COD_PROF,
    X_AUTFACPLAN_INPUT_CBO,
    X_AUTFACPLAN_BTN_CONF_PROF,
    X_AUTFACPLAN_BTN_CANCEL_PROF,
    X_AUTFACPLAN_BTN_EXCLUIR_PROF,
    X_AUTFACPLAN_MENU_JUST,
    X_AUTFACPLAN_INPUT_JUST,
    X_AUTFACPLAN_TITLE_OBS,
    X_AUTFACPLAN_INPUT_OBS,
    X_AUTFACPLAN_TITLE_AUDIT,
    X_AUTFACPLAN_INPUT_AUDIT,
    X_AUTFACPLAN_SELECT_TIPO_ANX,
    X_AUTFACPLAN_TIPO_RM_OPT,
    X_AUTFACPLAN_TIPO_AI_OPT,
    X_AUTFACPLAN_TIPO_RC_OPT,
    X_AUTFACPLAN_INPUT_CAMINHO,
    X_AUTFACPLAN_BTN_INCLUIR_ANX,
    X_AUTFACPLAN_SPINNER_ANX,
    X_AUTFACPLAN_BTN_GRAVAR,
    X_AUTFACPLAN_BTN_CONFIRMAR,
    X_AUTFACPLAN_DIALOG_NUM_GUIA,
    X_AUTFACPLAN_DIALOG_GUIA_PREST,
    X_AUTFACPLAN_DIALOG_DATA_SOL,
    X_AUTFACPLAN_BTN_FECHAR_DIALOG,
)

if TYPE_CHECKING:
    from base_scraper import BaseScraper

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

MAX_ANEXO_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def _parse_tarja_magnetica(carteira: str) -> str:
    """
    Cria a TarjaMagnética a partir do número da carteira.
    Remove '.' e '-', depois constrói:
        ç0113000 + carteira_limpa + último_dígito + =019912=000000000000:
    Exemplo: '667162556' ou '6671625-56' → 'ç01130006671625566=019912=000000000000:'
    """
    clean = re.sub(r"[.\-]", "", str(carteira).strip())
    last_digit = clean[-1] if clean else "0"
    return f"\u00e70113000{clean}{last_digit}=019912=000000000000:"


def _parse_data(data_str: str) -> str:
    """
    Normaliza data de solicitação para DDMMAAAA (sem separadores).
    Aceita: DD/MM/AAAA, DD-MM-AAAA, DDMMAAAA
    """
    cleaned = re.sub(r"[/\-]", "", str(data_str).strip())
    return cleaned  # DDMMAAAA


def _scroll_click(driver, element):
    """Scroll para o elemento e clica, com fallback para JS click."""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    time.sleep(0.3)
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)


def _wait_xpath(driver, xpath: str, timeout: int = DEFAULT_TIMEOUT):
    """Aguarda elemento estar presente no DOM."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )


def _wait_clickable(driver, xpath: str, timeout: int = DEFAULT_TIMEOUT):
    """Aguarda elemento estar clicável."""
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )


def _is_visible(driver, xpath: str, timeout: int = SHORT_TIMEOUT) -> bool:
    """Verifica se elemento está visível (sem lançar exceção)."""
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.XPATH, xpath))
        )
        return el.is_displayed()
    except Exception:
        return False


def _close_notifications(driver, scraper, job_id):
    """Fecha notificações/modais do FacPlan de forma robusta (replica lógica do OP11)."""
    def _log(msg):
        scraper.log(msg, job_id=job_id)

    # button-1 genérico (dialog FacPlan)
    for attempt_xpath in ['//*[@id="button-1"]']:
        try:
            btn = driver.find_element(By.XPATH, attempt_xpath)
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                _log("Notificação fechada via #button-1")
                time.sleep(1)
                return
        except Exception:
            pass

    # Noty notification
    try:
        if driver.find_elements(By.XPATH, X_LOCALIZAR_NOTY_CONTAINER):
            btn = driver.find_element(By.XPATH, X_LOCALIZAR_NOTY_FECHAR)
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                _log("Notificação Noty fechada")
                time.sleep(1)
                return
    except Exception:
        pass

    # Banner de aviso genérico
    try:
        if driver.find_elements(By.XPATH, X_ALERT_AVISO_BANNER):
            for close_xp in [X_ALERT_CLOSE, X_ALERT_CLOSE_STRONG]:
                btns = driver.find_elements(By.XPATH, close_xp)
                if btns:
                    try:
                        btns[0].click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", btns[0])
                    _log("Banner de aviso fechado")
                    time.sleep(1)
                    return
    except Exception:
        pass

    # Noty modal backdrop
    try:
        modal = driver.find_elements(By.XPATH, X_LOCALIZAR_NOTY_MODAL)
        if modal:
            driver.execute_script("arguments[0].style.display='none';", modal[0])
            _log("Noty modal backdrop removido")
            time.sleep(0.5)
    except Exception:
        pass


def _is_profissional_incluido(driver) -> bool:
    try:
        nome_el = driver.find_element(By.ID, "registroProfissionalNome")
        return bool(nome_el.text.strip())
    except Exception:
        return False


def _excluir_profissional_se_existir(driver, scraper, job_id) -> bool:
    """
    Remove o profissional do grid caso exista, aceitando alertas nativos e modais de confirmação.
    """
    xpath_excluir = '//*[@id="excluirProfissional"]'
    try:
        if _is_profissional_incluido(driver):
            scraper.log("[OP1] Detectado profissional já incluído no grid. Removendo...", job_id=job_id)
            
            # 1. Clicar na linha do profissional para selecioná-la (necessário antes de excluir)
            try:
                row = driver.find_element(By.ID, "registroProfissionalItem")
                _scroll_click(driver, row)
                time.sleep(0.5)
            except Exception as row_err:
                scraper.log(f"[OP1] Erro ao selecionar linha do profissional: {row_err}", level="WARN", job_id=job_id)
                
            # 2. Clicar em Remover
            btn_exc = driver.find_element(By.XPATH, xpath_excluir)
            _scroll_click(driver, btn_exc)
            time.sleep(1.5)
            
            # 3. Aceitar confirmação
            # 1. Alerta nativo
            try:
                alert = driver.switch_to.alert
                alert_text = alert.text
                alert.accept()
                scraper.log(f"[OP1] Alerta nativo de exclusão aceito: {alert_text}", job_id=job_id)
                time.sleep(2)
                
                # Check for second alert
                try:
                    alert2 = driver.switch_to.alert
                    alert2.accept()
                    time.sleep(1.5)
                except Exception:
                    pass
            except Exception:
                # 2. Botão de confirmação em modal HTML (Ok, Sim, Confirmar, button-1)
                for btn_xp in [
                    '//button[contains(text(), "OK") or contains(text(), "Ok") or contains(text(), "Sim") or contains(text(), "Confirmar")]',
                    '//*[@id="button-1"]'
                ]:
                    try:
                        btn = driver.find_element(By.XPATH, btn_xp)
                        if btn.is_displayed():
                            driver.execute_script("arguments[0].click();", btn)
                            scraper.log(f"[OP1] Exclusão confirmada via modal: {btn.text}", job_id=job_id)
                            time.sleep(2)
                            break
                    except Exception:
                        pass
            
            # 4. Verificar se sumiu (aguarda até 5s para o grid atualizar e ficar limpo)
            deadline = time.time() + 5
            while time.time() < deadline:
                if not _is_profissional_incluido(driver):
                    scraper.log("[OP1] Profissional anterior excluído com sucesso", job_id=job_id)
                    return True
                time.sleep(0.5)
                
            scraper.log("[OP1] Erro: O profissional não pôde ser excluído do grid (continua preenchido)!", level="ERROR", job_id=job_id)
            return False
        return True
    except Exception as e:
        scraper.log(f"[OP1] Exceção ao tentar excluir profissional: {e}", level="WARN", job_id=job_id)
        return False


def _wait_for_webplan_ready(driver, scraper, job_id):
    """Aguarda a página FacPlan estabilizar após SSO e foca na aba correta."""
    facplan_found = False
    for _ in range(10):
        for handle in driver.window_handles:
            try:
                driver.switch_to.window(handle)
                if "facilinformatica" in driver.current_url.lower() or "facplan" in driver.current_url.lower():
                    facplan_found = True
                    break
            except Exception:
                pass
        if facplan_found:
            try:
                if driver.execute_script("return document.readyState;") == "complete":
                    break
            except Exception:
                pass
        time.sleep(1)


def _resolve_attachment(path_or_url: str, label: str, scraper, job_id) -> Optional[str]:
    """
    Retorna caminho local do arquivo de anexo.
    Se for URL, faz download temporário. Valida extensão e tamanho.
    Retorna None se inválido/ausente.
    """
    if not path_or_url:
        return None

    path_or_url = str(path_or_url).strip()

    # Download temporário se for URL
    local_path = path_or_url
    if path_or_url.lower().startswith("http://") or path_or_url.lower().startswith("https://"):
        scraper.log(f"[OP1] {label}: baixando de URL temporariamente...", job_id=job_id)
        try:
            import urllib.parse
            parsed_url = urllib.parse.urlparse(path_or_url)
            encoded_path = urllib.parse.quote(parsed_url.path)
            encoded_query = urllib.parse.quote(parsed_url.query, safe="=&")
            
            url_to_fetch = urllib.parse.urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                encoded_path,
                parsed_url.params,
                encoded_query,
                parsed_url.fragment
            ))
            
            # Extrai o nome do arquivo codificado da URL
            filename_with_uuid = os.path.basename(parsed_url.path)
            filename_decoded = urllib.parse.unquote(filename_with_uuid)
            
            # Remove o UUID (32 hex + 1 underscore = 33 chars) do início do nome de arquivo local
            if len(filename_decoded) > 33 and filename_decoded[32] == "_":
                try:
                    int(filename_decoded[:32], 16)
                    original_filename = filename_decoded[33:]
                except ValueError:
                    original_filename = filename_decoded
            else:
                original_filename = filename_decoded
                
            # Limpa qualquer caractere proibido pelo SO e remove espaços para evitar problemas
            original_filename = re.sub(r'[\\/*?:"<>|]', '_', original_filename)
            original_filename = original_filename.replace(" ", "")
            
            # Cria pasta temporária e salva com o nome original do arquivo (sem espaços)
            temp_dir = tempfile.mkdtemp()
            local_path = os.path.join(temp_dir, original_filename)
            
            urllib.request.urlretrieve(url_to_fetch, local_path)
            scraper.log(f"[OP1] {label}: download OK → {local_path}", job_id=job_id)
        except Exception as e:
            scraper.log(f"[OP1] {label}: falha no download ({e})", level="WARN", job_id=job_id)
            return None

    # Valida existência
    if not os.path.isfile(local_path):
        scraper.log(f"[OP1] {label}: arquivo não encontrado: {local_path}", level="WARN", job_id=job_id)
        return None

    # Valida extensão
    ext = os.path.splitext(local_path)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        scraper.log(f"[OP1] {label}: extensão inválida ({ext}). Permitidos: {ALLOWED_EXTENSIONS}", level="WARN", job_id=job_id)
        return None

    # Valida tamanho
    size = os.path.getsize(local_path)
    if size > MAX_ANEXO_BYTES:
        scraper.log(f"[OP1] {label}: arquivo muito grande ({size/1024/1024:.1f}MB > 5MB)", level="WARN", job_id=job_id)
        return None

    # Garante que o arquivo tem o sufixo correspondente no nome do arquivo físico para evitar bloqueio por nome duplicado no IPASGO
    current_basename = os.path.basename(local_path)
    # Remove UUID caso ainda exista (por exemplo, se era um arquivo local passado diretamente)
    if len(current_basename) > 33 and current_basename[32] == "_":
        try:
            int(current_basename[:32], 16)
            current_basename = current_basename[33:]
        except ValueError:
            pass

    current_basename = re.sub(r'[\\/*?:"<>|]', '_', current_basename)
    current_basename = current_basename.replace(" ", "")

    base, file_ext = os.path.splitext(current_basename)
    if not file_ext:
        file_ext = ".pdf"

    new_basename = current_basename
    if label == "AI" and not base.endswith("-ANEXOII"):
        new_basename = f"{base}-ANEXOII{file_ext}"
    elif label == "RC" and not base.endswith("-PTS"):
        new_basename = f"{base}-PTS{file_ext}"

    # Copia o arquivo para um diretório temporário com o novo nome se o nome mudou ou se queremos isolar o upload
    if new_basename != os.path.basename(local_path):
        try:
            import shutil
            temp_dir = tempfile.mkdtemp()
            new_local_path = os.path.join(temp_dir, new_basename)
            shutil.copy2(local_path, new_local_path)
            local_path = new_local_path
        except Exception as e:
            scraper.log(f"[OP1] {label}: erro ao copiar arquivo para pasta temporária com sufixo: {e}", level="WARN", job_id=job_id)

    return local_path


def _wait_upload_spinner(driver, scraper, job_id, timeout: int = 30):
    """
    Aguarda o spinner do upload desaparecer (visibility: hidden).
    O spinner visível indica upload em andamento; oculto = concluído.
    """
    scraper.log("[OP1] Aguardando conclusão do upload...", job_id=job_id)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            spinner = driver.find_element(By.XPATH, X_AUTFACPLAN_SPINNER_ANX)
            style = spinner.get_attribute("style") or ""
            if "hidden" in style or not spinner.is_displayed():
                scraper.log("[OP1] Upload concluído (spinner oculto)", job_id=job_id)
                return True
        except Exception:
            # Elemento não existe = upload já concluído
            return True
        time.sleep(1)
    scraper.log("[OP1] Timeout aguardando upload", level="WARN", job_id=job_id)
    return False


def _upload_anexo(driver, scraper, job_id, tipo_xpath: str, local_path: str, label: str):
    """
    Seleciona tipo de anexo no dropdown e envia o arquivo pelo input file.
    """
    scraper.log(f"[OP1] Enviando anexo {label}: {os.path.basename(local_path)}", job_id=job_id)

    # Selecionar tipo de arquivo
    sel_el = _wait_xpath(driver, X_AUTFACPLAN_SELECT_TIPO_ANX)
    _scroll_click(driver, sel_el)
    time.sleep(0.5)
    tipo_opt = _wait_xpath(driver, tipo_xpath, timeout=SHORT_TIMEOUT)
    _scroll_click(driver, tipo_opt)
    time.sleep(0.5)

    # Enviar caminho do arquivo ao input
    input_file = driver.find_element(By.XPATH, X_AUTFACPLAN_INPUT_CAMINHO)
    input_file.send_keys(local_path)
    time.sleep(0.5)

    # Clicar em incluir
    btn_incluir = driver.find_element(By.XPATH, X_AUTFACPLAN_BTN_INCLUIR_ANX)
    _scroll_click(driver, btn_incluir)

    # Aguardar spinner
    _wait_upload_spinner(driver, scraper, job_id)
    scraper.log(f"[OP1] Anexo {label} enviado com sucesso", job_id=job_id)


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def run(scraper: "BaseScraper", job_data: dict) -> dict:
    """
    OP1 — Autorizar FacPlan (GuiaSPSADT) IPASGO.
    Retorna o JSON obtido pelo OP11 com os dados da guia autorizada.
    """
    driver = scraper.driver
    job_id = job_data.get("job_id")
    scraper.log("[OP1] Iniciando autorização FacPlan...", job_id=job_id)

    # ── 1. Extrair e validar parâmetros ──────────────────────────────────────
    # Os parâmetros devem seguir estritamente o formato oficial documentado, sem fallbacks.
    carteira              = str(job_data.get("carteira") or "").strip()
    paciente_cid          = str(job_data.get("paciente_CID") or "").strip()
    data_solicitacao      = str(job_data.get("dataSolicitacao") or "").strip()
    cod_procedimento      = str(job_data.get("codigoProcedimento_aut") or "").strip()
    qtde                  = str(job_data.get("qtde") or "1").strip()
    prof_codigo           = re.sub(r"[\\r\\n\r\n]", "", str(job_data.get("profissional_codigo_ipasgo") or "")).strip()
    prof_cbo              = str(job_data.get("profissional_CBO") or "").strip()
    texto_justificativa   = str(job_data.get("texto_Justificativa") or "").strip()
    anexo_rm_raw          = job_data.get("anexo_RM") or ""
    anexo_ai_raw          = job_data.get("anexo_AI") or ""
    anexo_rc_raw          = job_data.get("anexo_RC") or ""

    if not carteira:
        raise ValueError("Parâmetro 'carteira' é obrigatório para OP1.")
    if not cod_procedimento:
        raise ValueError("Parâmetro 'codigoProcedimento_aut' é obrigatório para OP1.")
    if not data_solicitacao:
        raise ValueError("Parâmetro 'dataSolicitacao' é obrigatório para OP1.")

    # ── 2. TarjaMagnética ────────────────────────────────────────────────────
    tarja = _parse_tarja_magnetica(carteira)
    data_fmt = _parse_data(data_solicitacao)  # DDMMAAAA
    scraper.log(f"[OP1] TarjaMagnética: {tarja}", job_id=job_id)

    # ── 3. Resolver anexos (download de URLs se necessário) ──────────────────
    temp_files = []  # rastrear para limpeza posterior

    def resolve(raw, label):
        path = _resolve_attachment(raw, label, scraper, job_id)
        if path and not str(raw).strip().startswith(path):
            # É um arquivo temporário baixado
            temp_files.append(path)
        return path

    local_rm = resolve(anexo_rm_raw, "RM")
    local_ai = resolve(anexo_ai_raw, "AI")
    local_rc = resolve(anexo_rc_raw, "RC")

    # ── 4. Aguardar WebPlan pronto e navegar ─────────────────────────────────
    # ── 4. Aguardar WebPlan pronto e navegar robustamente ──────────────────
    nav_success = False
    for nav_attempt in range(3):
        try:
            _wait_for_webplan_ready(driver, scraper, job_id)
            _close_notifications(driver, scraper, job_id)
            
            # Tenta fechar alerta nativo se existir
            try:
                driver.switch_to.alert.accept()
            except Exception:
                pass
                
            scraper.log(f"[OP1] Tentando navegar para: {X_AUTFACPLAN_URL} (Tentativa {nav_attempt + 1}/3)...", job_id=job_id)
            driver.get(X_AUTFACPLAN_URL)
            time.sleep(2)
            
            # Verificar se navegou com sucesso
            curr_url = driver.current_url.lower()
            if "viewspsadt" in curr_url or "guia-spsadt" in curr_url or "viewguiaspsadt" in curr_url:
                scraper.log(f"[OP1] Navegado com sucesso para: {driver.current_url}", job_id=job_id)
                nav_success = True
                break
            else:
                scraper.log(f"[OP1] URL atual '{driver.current_url}' não é a de SADT. Tentando novamente...", level="WARN", job_id=job_id)
        except Exception as e:
            scraper.log(f"[OP1] Erro na navegação (tentativa {nav_attempt + 1}): {e}", level="WARN", job_id=job_id)

    if not nav_success:
        raise RuntimeError(f"[OP1] Falha permanente ao navegar para ViewGuiaSPSADT. URL atual: {driver.current_url}")

    # Aguarda carregamento completo da página
    WebDriverWait(driver, LONG_TIMEOUT).until(
        lambda d: d.execute_script("return document.readyState;") == "complete"
    )
    time.sleep(1)

    # ── 5. Fechar notificações ───────────────────────────────────────────────
    _close_notifications(driver, scraper, job_id)

    try:
        # ════════════════════════════════════════════════════════════════════
        # ETAPA 1 — Carteira / Dados iniciais
        # ════════════════════════════════════════════════════════════════════
        scraper.log("[OP1] Etapa 1: Preenchendo carteira...", job_id=job_id)

        # Clicar no campo cartão para ativar input de tarja
        cartao_el = _wait_clickable(driver, X_AUTFACPLAN_CLICK_CARTAO)
        _scroll_click(driver, cartao_el)
        time.sleep(2)

        # Inserir TarjaMagnética via Javascript (para evitar engolir o caractere especial 'ç')
        input_carteira = _wait_xpath(driver, X_AUTFACPLAN_INPUT_CARTEIRA)
        driver.execute_script("arguments[0].value = arguments[1];", input_carteira, tarja)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", input_carteira)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", input_carteira)
        time.sleep(1)
        input_carteira.send_keys(Keys.RETURN)
        time.sleep(2)

        # Verificar se beneficiário foi localizado (campo nomeDoBeneficiario preenchido)
        nome_benef_el = _wait_xpath(driver, X_AUTFACPLAN_NOME_BENEF, timeout=10)
        nome_benef_val = nome_benef_el.get_attribute("value") or nome_benef_el.text or ""
        if not nome_benef_val.strip():
            raise ValueError("PermanentError: Beneficiário não localizado! Carteira inválida ou não cadastrada.")
        scraper.log(f"[OP1] Beneficiário localizado: {nome_benef_val}", job_id=job_id)

        # Caráter de atendimento → opção 2 (Eletivo)
        carat_el = _wait_clickable(driver, X_AUTFACPLAN_CARAT_ATEND)
        _scroll_click(driver, carat_el)
        time.sleep(0.5)
        carat_opt2 = _wait_xpath(driver, X_AUTFACPLAN_CARAT_ATEND_OPT2, timeout=SHORT_TIMEOUT)
        _scroll_click(driver, carat_opt2)
        time.sleep(0.5)

        # Data de solicitação
        data_el = _wait_xpath(driver, X_AUTFACPLAN_DATA_SOLICIT)
        _scroll_click(driver, data_el)
        data_el.clear()
        data_el.send_keys(data_fmt)
        time.sleep(0.5)

        # Indicação clínica (CID)
        if paciente_cid:
            cid_el = _wait_clickable(driver, X_AUTFACPLAN_INDICACAO_CLIN)
            _scroll_click(driver, cid_el)
            time.sleep(0.5)
            cid_el.clear()
            cid_el.send_keys(paciente_cid)
        scraper.log("[OP1] Etapa 1 concluída", job_id=job_id)

        # ════════════════════════════════════════════════════════════════════
        # ETAPA 2 — Procedimento
        # ════════════════════════════════════════════════════════════════════
        scraper.log("[OP1] Etapa 2: Incluindo procedimento...", job_id=job_id)

        # Abrir accordion de procedimentos
        menu_proc = _wait_clickable(driver, X_AUTFACPLAN_MENU_PROC)
        _scroll_click(driver, menu_proc)
        time.sleep(1)

        # Clicar em "Incluir Procedimento"
        btn_incl_proc = _wait_clickable(driver, X_AUTFACPLAN_BTN_INCLUIR_PROC)
        _scroll_click(driver, btn_incl_proc)
        time.sleep(0.5)

        # Código do procedimento
        input_cod = _wait_xpath(driver, X_AUTFACPLAN_INPUT_COD_PROC)
        input_cod.send_keys(cod_procedimento)
        time.sleep(2)
        input_cod.send_keys(Keys.RETURN)
        time.sleep(2)

        # Quantidade
        input_qt = _wait_xpath(driver, X_AUTFACPLAN_INPUT_QT_PROC)
        input_qt.clear()
        input_qt.send_keys(qtde)
        time.sleep(1)

        # Confirmar procedimento
        btn_conf_proc = _wait_xpath(driver, X_AUTFACPLAN_BTN_CONF_PROC)
        _scroll_click(driver, btn_conf_proc)
        time.sleep(2)

        # Verificar mensagem de erro genérica (procedimento inválido)
        if _is_visible(driver, X_AUTFACPLAN_SPAN_MSG_GENERICA, timeout=3):
            try:
                msg_el = driver.find_element(By.XPATH, X_AUTFACPLAN_SPAN_MSG_GENERICA)
                err_msg = msg_el.text.strip()
            except Exception:
                err_msg = "Procedimento não autorizado/inválido"
            raise ValueError(f"PermanentError: {err_msg}")
        scraper.log("[OP1] Etapa 2 concluída", job_id=job_id)

        # ════════════════════════════════════════════════════════════════════
        # ETAPA 3 — Profissional executante (opcional)
        # ════════════════════════════════════════════════════════════════════
        if prof_codigo:
            scraper.log("[OP1] Etapa 3: Incluindo profissional executante...", job_id=job_id)

            prof_ok = False
            for prof_attempt in range(3):
                try:
                    # Abrir accordion de executante
                    menu_exec = _wait_clickable(driver, X_AUTFACPLAN_MENU_EXEC)
                    _scroll_click(driver, menu_exec)
                    time.sleep(1)

                    # Se já houver um profissional inserido no grid, precisamos removê-lo primeiro
                    _excluir_profissional_se_existir(driver, scraper, job_id)

                    # Incluir profissional
                    btn_incl_prof = _wait_xpath(driver, X_AUTFACPLAN_BTN_INCLUIR_PROF)
                    _scroll_click(driver, btn_incl_prof)
                    time.sleep(0.5)

                    # Grau de participação → Abre autocomplete e seleciona "(12) Clínico"
                    grau_el = _wait_xpath(driver, X_AUTFACPLAN_INPUT_GRAU, timeout=SHORT_TIMEOUT)
                    _scroll_click(driver, grau_el)
                    time.sleep(0.5)
                    grau_el.send_keys(Keys.ARROW_DOWN)
                    time.sleep(1.5)
                    
                    menu_items = driver.find_elements(By.CLASS_NAME, "ui-menu-item")
                    grau_clicked = False
                    for item in menu_items:
                        item_text = item.text.strip()
                        if "(12)" in item_text or "Clínico" in item_text or "Clinico" in item_text:
                            try:
                                item.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", item)
                            grau_clicked = True
                            scraper.log(f"[OP1] Grau de participação selecionado: {item_text}", job_id=job_id)
                            break
                    if not grau_clicked:
                        scraper.log("[OP1] Não foi possível encontrar '(12) Clínico' na lista, usando fallback Arrow Down", level="WARN", job_id=job_id)
                        for _ in range(4):
                            grau_el.send_keys(Keys.ARROW_DOWN)
                            time.sleep(0.1)
                        grau_el.send_keys(Keys.RETURN)
                    time.sleep(1)

                    # Código do profissional
                    input_cod_prof = _wait_xpath(driver, X_AUTFACPLAN_INPUT_COD_PROF)
                    input_cod_prof.clear()
                    input_cod_prof.send_keys(prof_codigo)
                    time.sleep(0.5)
                    input_cod_prof.send_keys(Keys.ARROW_DOWN)
                    input_cod_prof.send_keys(Keys.RETURN)
                    time.sleep(1)

                    # CBO — selecionar na lista autocomplete
                    if prof_cbo:
                        input_cbo = _wait_xpath(driver, X_AUTFACPLAN_INPUT_CBO, timeout=SHORT_TIMEOUT)
                        _scroll_click(driver, input_cbo)
                        time.sleep(2)  # aguarda autocomplete carregar
                        cbo_items = driver.find_elements(By.CLASS_NAME, "ui-menu-item")
                        cbo_clicked = False
                        for item in cbo_items:
                            item_text = item.text.strip()
                            # CBO está nos 6 primeiros chars do item (ex: "123456 - Descrição")
                            item_cbo = re.sub(r"\D", "", item_text[:7])
                            if item_cbo == re.sub(r"\D", "", str(prof_cbo)):
                                try:
                                    item.click()
                                except Exception:
                                    driver.execute_script("arguments[0].click();", item)
                                cbo_clicked = True
                                break
                        if not cbo_clicked:
                            scraper.log(f"[OP1] CBO {prof_cbo} não localizado na lista autocomplete", level="WARN", job_id=job_id)
                        time.sleep(1)

                    # Confirmar profissional
                    btn_conf_prof = _wait_xpath(driver, X_AUTFACPLAN_BTN_CONF_PROF, timeout=SHORT_TIMEOUT)
                    _scroll_click(driver, btn_conf_prof)
                    time.sleep(2)

                    # Verificar se houve erro (profissional não está no grid ou formulário de edição continua ativo)
                    time.sleep(1)
                    success_inclusao = _is_profissional_incluido(driver)
                    cancel_visible = _is_visible(driver, X_AUTFACPLAN_BTN_CANCEL_PROF, timeout=1)

                    if cancel_visible and not success_inclusao:
                        scraper.log(
                            f"[OP1] Erro na inclusão do profissional (tentativa {prof_attempt + 1}/3). "
                            "Limpando e tentando novamente...",
                            level="WARN", job_id=job_id
                        )
                        # Cancelar edição em andamento
                        try:
                            btn_cancel = driver.find_element(By.XPATH, X_AUTFACPLAN_BTN_CANCEL_PROF)
                            driver.execute_script("arguments[0].click();", btn_cancel)
                            time.sleep(1.5)
                        except Exception:
                            pass
                        # Excluir registro que pode ter ficado parcial
                        _excluir_profissional_se_existir(driver, scraper, job_id)
                        continue  # Próxima tentativa

                    # Chegou aqui sem erro
                    prof_ok = True
                    scraper.log("[OP1] Etapa 3 concluída — profissional incluído", job_id=job_id)
                    break

                except (ValueError, RuntimeError):
                    raise
                except Exception as e:
                    scraper.log(f"[OP1] Exceção na Etapa 3, tentativa {prof_attempt + 1}: {e}", level="WARN", job_id=job_id)
                    if prof_attempt == 2:
                        raise ValueError("PermanentError: Erro Profissional não cadastrado no IPASGO")
                    time.sleep(2)

            if not prof_ok:
                raise ValueError("PermanentError: Erro Profissional não cadastrado no IPASGO")
        else:
            scraper.log("[OP1] Etapa 3: Profissional não informado — etapa ignorada", job_id=job_id)

        # ════════════════════════════════════════════════════════════════════
        # ETAPA 4 — Justificativa Clínica
        # ════════════════════════════════════════════════════════════════════
        scraper.log("[OP1] Etapa 4: Justificativa clínica...", job_id=job_id)
        menu_just = _wait_clickable(driver, X_AUTFACPLAN_MENU_JUST)
        _scroll_click(driver, menu_just)
        time.sleep(0.5)
        input_just = _wait_xpath(driver, X_AUTFACPLAN_INPUT_JUST)
        input_just.send_keys(texto_justificativa)
        scraper.log("[OP1] Etapa 4 concluída", job_id=job_id)

        # ════════════════════════════════════════════════════════════════════
        # ETAPA 5a — Observação adicional
        # ════════════════════════════════════════════════════════════════════
        scraper.log("[OP1] Etapa 5a: Observação adicional...", job_id=job_id)
        title_obs = _wait_clickable(driver, X_AUTFACPLAN_TITLE_OBS)
        _scroll_click(driver, title_obs)
        time.sleep(1)
        input_obs = _wait_xpath(driver, X_AUTFACPLAN_INPUT_OBS)
        input_obs.send_keys(texto_justificativa)
        scraper.log("[OP1] Etapa 5a concluída", job_id=job_id)

        # ════════════════════════════════════════════════════════════════════
        # ETAPA 5b — Contato auditoria
        # ════════════════════════════════════════════════════════════════════
        scraper.log("[OP1] Etapa 5b: Contato auditoria...", job_id=job_id)
        title_audit = _wait_clickable(driver, X_AUTFACPLAN_TITLE_AUDIT)
        _scroll_click(driver, title_audit)
        time.sleep(1)
        input_audit = _wait_xpath(driver, X_AUTFACPLAN_INPUT_AUDIT)
        input_audit.send_keys(texto_justificativa)
        scraper.log("[OP1] Etapa 5b concluída", job_id=job_id)

        # ════════════════════════════════════════════════════════════════════
        # ETAPA 6 — Anexo RM (Pedido Médico) — opcional
        # ════════════════════════════════════════════════════════════════════
        if local_rm:
            scraper.log("[OP1] Etapa 6: Enviando Pedido Médico (RM)...", job_id=job_id)
            _upload_anexo(driver, scraper, job_id, X_AUTFACPLAN_TIPO_RM_OPT, local_rm, "RM")
        else:
            scraper.log("[OP1] Etapa 6: Pedido Médico (RM) não informado — ignorado", job_id=job_id)

        # ════════════════════════════════════════════════════════════════════
        # ETAPA 7 — Anexo AI (Avaliação Inicial / Justificativa Clínica) — opcional
        # ════════════════════════════════════════════════════════════════════
        if local_ai:
            scraper.log("[OP1] Etapa 7: Enviando Avaliação Inicial (AI)...", job_id=job_id)
            _upload_anexo(driver, scraper, job_id, X_AUTFACPLAN_TIPO_AI_OPT, local_ai, "AI")
        else:
            scraper.log("[OP1] Etapa 7: Avaliação Inicial (AI) não informada — ignorada", job_id=job_id)

        # ════════════════════════════════════════════════════════════════════
        # ETAPA 8 — Anexo RC (Relatório Clínico) — opcional mas recomendado
        # ════════════════════════════════════════════════════════════════════
        if local_rc:
            scraper.log("[OP1] Etapa 8: Enviando Relatório Clínico (RC)...", job_id=job_id)
            _upload_anexo(driver, scraper, job_id, X_AUTFACPLAN_TIPO_RC_OPT, local_rc, "RC")
        else:
            scraper.log("[OP1] Etapa 8: Relatório Clínico (RC) não informado — ignorado", job_id=job_id)

        # ════════════════════════════════════════════════════════════════════
        btn_gravar = _wait_xpath(driver, X_AUTFACPLAN_BTN_GRAVAR)
        _scroll_click(driver, btn_gravar)
        time.sleep(2)  # Aguardar validação local rodar

        # Verificar se alguma inconsistência foi exibida
        erros_visiveis = []
        try:
            lis = driver.find_elements(By.XPATH, '//*[@id="ulValidators"]/li')
            for li in lis:
                if li.is_displayed():
                    txt = li.text.strip()
                    if txt:
                        erros_visiveis.append(txt)
        except Exception as e:
            scraper.log(f"[OP1] Erro ao inspecionar ulValidators: {e}", level="WARN", job_id=job_id)

        if erros_visiveis:
            msg_erro = " | ".join(erros_visiveis)
            scraper.log(f"[OP1] Inconsistências impediram a gravação: {msg_erro}", level="ERROR", job_id=job_id)
            raise ValueError(f"PermanentError: {msg_erro}")

        # Confirmar dialog de gravação
        btn_confirmar = _wait_xpath(driver, X_AUTFACPLAN_BTN_CONFIRMAR, timeout=LONG_TIMEOUT)
        time.sleep(1)
        _scroll_click(driver, btn_confirmar)
        scraper.log("[OP1] Confirmação enviada. Aguardando processamento...", job_id=job_id)

        # Aguardar spinner de processamento (overlay ou spinner global)
        time.sleep(3)
        # Espera a página responder — presença do dialogText indica conclusão
        WebDriverWait(driver, LONG_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, X_AUTFACPLAN_DIALOG_NUM_GUIA))
        )

        # ════════════════════════════════════════════════════════════════════
        # CAPTURAR NÚMERO DA GUIA DO DIÁLOGO DE RESULTADO
        # ════════════════════════════════════════════════════════════════════
        scraper.log("[OP1] Capturando dados da guia no diálogo...", job_id=job_id)

        num_guia_el      = driver.find_element(By.XPATH, X_AUTFACPLAN_DIALOG_NUM_GUIA)
        guia_prest_el    = driver.find_element(By.XPATH, X_AUTFACPLAN_DIALOG_GUIA_PREST)
        try:
            data_sol_el  = driver.find_element(By.XPATH, X_AUTFACPLAN_DIALOG_DATA_SOL)
            data_sol_txt = data_sol_el.text.strip()
        except Exception:
            data_sol_txt = ""

        # Extrai os 8 últimos dígitos do número da guia (conforme VBA: Right(..., 8))
        num_guia_raw  = num_guia_el.text.strip()
        guia_prest_raw= guia_prest_el.text.strip()
        numero_guia   = num_guia_raw[-8:].strip() if len(num_guia_raw) >= 8 else num_guia_raw
        guia_prestador= guia_prest_raw[-20:].strip() if len(guia_prest_raw) >= 20 else guia_prest_raw
        data_solicit  = data_sol_txt[-10:].strip() if len(data_sol_txt) >= 10 else data_sol_txt

        scraper.log(
            f"[OP1] Guia autorizada: #{numero_guia} | Prestador: {guia_prestador} | Data: {data_solicit}",
            job_id=job_id
        )

        # Fechar diálogo
        try:
            btn_fechar = _wait_clickable(driver, X_AUTFACPLAN_BTN_FECHAR_DIALOG, timeout=SHORT_TIMEOUT)
            _scroll_click(driver, btn_fechar)
        except Exception:
            # Fallback: fechar via dialog padrão do FacPlan
            try:
                fechar_id = driver.find_element(By.ID, "fechar")
                driver.execute_script("arguments[0].click();", fechar_id)
            except Exception:
                pass
        time.sleep(2)

        # ════════════════════════════════════════════════════════════════════
        # CHAMAR OP11 — importar dados da guia recém-autorizada
        # ════════════════════════════════════════════════════════════════════
        scraper.log(f"[OP1] Chamando OP11 para importar guia #{numero_guia}...", job_id=job_id)

        op11_job_data = dict(job_data)  # cópia dos parâmetros originais
        op11_job_data["guia"]          = numero_guia   # OP11 filtra pelo campo 'guia' (número da guia operadora)
        op11_job_data["skip_login"]    = True          # WebPlan já está aberto
        op11_job_data["_origem"]       = "op1_autorizar_facplan"
        # Limpar filtros de data para não conflitar com o filtro por guia
        op11_job_data.pop("data_ini", None)
        op11_job_data.pop("data_fim", None)


        try:
            op11_result = scraper.execute_op("op11_import_guias_api", op11_job_data)
        except Exception as e:
            scraper.log(f"[OP1] OP11 retornou erro (guia já autorizada): {e}", level="WARN", job_id=job_id)
            op11_result = []

        # ── Resultado final ──────────────────────────────────────────────────
        result = {
            "status": "autorizado",
            "numero_guia": numero_guia,
            "guia_prestador": guia_prestador,
            "data_solicitacao": data_solicit,
            "beneficiario": nome_benef_val,
            "op11_data": op11_result,
        }
        scraper.log(f"[OP1] Concluído com sucesso. Guia: #{numero_guia}", job_id=job_id)
        return result

    finally:
        # ── Limpeza de arquivos temporários ─────────────────────────────────
        for tmp in temp_files:
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
                    # Remove o diretório pai (temp_dir) se estiver vazio
                    parent_dir = os.path.dirname(tmp)
                    if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
                        os.rmdir(parent_dir)
                    scraper.log(f"[OP1] Arquivo temporário removido: {tmp}", job_id=job_id)
            except Exception:
                pass
