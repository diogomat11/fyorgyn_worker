"""
OP6 — Atualizar Relatorio Clinico Mensal (RC) e baixar PDF
Convenio: ABA_CLMF (101) | Portal: https://abalarissamartinsferreira.com.br

Replica fiel de clmf_hub_basic/worker/Worker/clmf_scraper.py:166-462 (CLMFScraper.atualizar_rc
+ helpers _post_gravar_rc / _post_gerar_pdf / _download_pdf), adaptada ao padrao BaseScraper
do Agenda_hub_MultiConv (funcao run(scraper, job_data); uso de scraper.driver para Selenium
e scraper.session para requests, com cookies ja sincronizados em op0_login).

Fluxo:
    1. Garantir login ativo (chama op0_login se sessao expirada)
    2. Validar/converter data_RC de dd/MM/yyyy -> yyyy-MM-dd
    3. Navegar ao prontuario do paciente
    4. Extrair do DOM: nome, carteirinha limpa, justificativa, evolucao, ipasgo_id
    5. Protecao anti-wipeout: se justificativa E evolucao vazias -> abortar
    6. POST AJAX gravar RC (callback_action=gravar)
    7. POST AJAX gerar PDF (callback_action=gerarRelatorio) -> extrair 'caminho'
    8. Baixar PDF em {caminho_pasta}/{nome_padrao}

Retorna:
    {"status": "success", "op": "op6_atualizar_rc", "id_convenio": 101,
     "paciente": <nome>, "id_paciente": <id>, "data_RC": "yyyy-MM-dd",
     "pdf_caminho": <path>, "pdf_nome": <nome>}

Em caso de erro:
    {"status": "error", "op": "op6_atualizar_rc", "id_convenio": 101,
     "message": <msg>, "code": <CODE_*>}

Referencias:
    - Plano: Prompts_implantacoes/Contextos/2026_07_28_Plano_OP5_CLMF_Valida_Prestador.md (RF-F1)
    - Origem: clmf_hub_basic/worker/Worker/clmf_scraper.py:166-462
"""
import os
import re
import sys
from datetime import datetime
from urllib.parse import urlencode

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.constants import (
    AJAX_RC_URL, PRONTUARIO_URL_TEMPLATE, CALLBACK_RC,
    ACTION_GRAVAR_RC, ACTION_GERAR_RELATORIO,
    LOGIN_READY_XPATH,
    DOM_NOME_FOLLOWING_STRONG_XPATH, DOM_CARTEIRINHA_ID,
    DOM_JUSTIFICATIVA_ID, DOM_EVOLUCAO_ID,
    CODE_WIPEOUT_BLOCK, CODE_AJAX_FAIL, CODE_PDF_NOT_GENERATED,
    CODE_DOWNLOAD_FAIL, CODE_INVALID_DATE, CODE_EXTRACT_FAIL,
)


def _is_logged_in(scraper) -> bool:
    """Verifica se a sessao Selenium ainda esta autenticada no portal."""
    if not scraper.driver:
        return False
    try:
        WebDriverWait(scraper.driver, 3).until(
            EC.presence_of_element_located((By.XPATH, LOGIN_READY_XPATH))
        )
        return True
    except Exception:
        return False


def _ensure_login(scraper, job_id) -> bool:
    """Garante login ativo; chama op0_login se necessario."""
    if _is_logged_in(scraper):
        return True
    scraper.log("Sessao expirada. Executando op0_login antes da OP6...", job_id=job_id)
    try:
        scraper.execute_op("op0_login", {"job_id": job_id})
        return _is_logged_in(scraper)
    except Exception as e:
        scraper.log(f"Falha no login antes da OP6: {e}", level="ERROR", job_id=job_id)
        return False


def _post_gravar_rc(scraper, id_paciente, id_profissional, id_especialidade,
                    justificativa, evolucao_ipasgo, data_rc_iso, ipasgo_id, job_id) -> dict:
    """Envia o formulario AJAX de gravacao do RC via scraper.session (cookies sincronizados)."""
    payload = {
        "callback": CALLBACK_RC,
        "callback_action": ACTION_GRAVAR_RC,
        "arr_relatorio[0][ipasgo_id]": ipasgo_id,
        "arr_relatorio[0][ipasgo_profissional_atendimento]": id_especialidade,
        "arr_relatorio[0][ipasgo_justificativa_periodo_tratamento]": justificativa,
        "arr_relatorio[0][ipasgo_evolucao_paciente]": evolucao_ipasgo,
        "arr_relatorio[0][ipasgo_data]": data_rc_iso,
        "arr_relatorio[0][client_id]": id_paciente,
        "arr_relatorio[0][user_id]": id_profissional,
    }
    encoded_payload = urlencode(payload)
    scraper.log(f"  [POST gravar RC] {AJAX_RC_URL}", job_id=job_id)
    scraper.log(f"  [POST gravar RC] data={encoded_payload}", job_id=job_id)
    try:
        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        resp = scraper.session.post(AJAX_RC_URL, data=encoded_payload, headers=headers, timeout=30)
        resp.raise_for_status()
        scraper.log(f"  -> AJAX gravar RC HTTP {resp.status_code}", job_id=job_id)
        return {"status": "success", "http_status": resp.status_code}
    except Exception as e:
        scraper.log(f"  -> Falha no POST gravar RC: {e}", level="ERROR", job_id=job_id)
        return {"status": "error", "message": f"Falha no POST AJAX do RC: {e}"}


def _post_gerar_pdf(scraper, ipasgo_id, job_id) -> dict:
    """Envia AJAX para compilar/gerar o PDF no servidor; retorna o 'caminho' do PDF."""
    payload = {
        "callback": CALLBACK_RC,
        "callback_action": ACTION_GERAR_RELATORIO,
        "ipasgo_id": ipasgo_id,
    }
    encoded_payload = urlencode(payload)
    scraper.log(f"  [POST gerar PDF] data={encoded_payload}", job_id=job_id)
    try:
        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        resp = scraper.session.post(AJAX_RC_URL, data=encoded_payload, headers=headers, timeout=30)
        resp.raise_for_status()
        scraper.log(f"  -> AJAX gerar PDF response: {resp.text}", job_id=job_id)
        data = resp.json()
        if "caminho" in data:
            return {"status": "success", "caminho": data["caminho"]}
        return {"status": "error", "message": f"Resposta sem 'caminho': {resp.text}"}
    except Exception as e:
        scraper.log(f"  -> Falha ao gerar PDF no servidor: {e}", level="ERROR", job_id=job_id)
        return {"status": "error", "message": f"Falha ao gerar o PDF no servidor: {e}"}


def _download_pdf(scraper, pdf_url, caminho_pasta, nome_padrao, job_id) -> dict:
    """Baixa o PDF via scraper.session e salva em {caminho_pasta}/{nome_padrao}."""
    try:
        os.makedirs(caminho_pasta, exist_ok=True)
    except Exception as e:
        scraper.log(f"  -> Falha ao criar pasta {caminho_pasta}: {e}", level="ERROR", job_id=job_id)
        return {"status": "error", "message": f"Falha ao criar pasta de destino: {e}"}

    destino = os.path.join(caminho_pasta, nome_padrao)
    # Apagar arquivo existente (mesmo nome) antes de baixar
    if os.path.exists(destino):
        try:
            os.remove(destino)
            scraper.log(f"  -> Arquivo existente removido: {destino}", job_id=job_id)
        except Exception:
            pass

    try:
        resp = scraper.session.get(pdf_url, timeout=60, stream=True)
        resp.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        scraper.log(f"  -> PDF salvo em: {destino}", job_id=job_id)
        return {"status": "success", "path": destino}
    except Exception as e:
        scraper.log(f"  -> Falha ao baixar PDF ({pdf_url}): {e}", level="ERROR", job_id=job_id)
        return {"status": "error", "message": f"Falha ao baixar PDF ({pdf_url}): {e}"}


def run(scraper, job_data):
    """
    OP6 — Atualizar RC (Relatorio Clinico Mensal) + baixar PDF.
    Assinatura canonica run(scraper, job_data); chamada pelo AbaClmfScraper.process_job
    quando rotina == 'op6_atualizar_rc'.

    Params esperados em job_data (ou job_data['params']):
        id_paciente      (int|str) - obrigatorio
        id_profissional  (int|str) - obrigatorio
        AbrevEsp         (str)     - obrigatorio (ex: "PSI", "FONO", "TO")
        id_especialidade (int|str) - obrigatorio
        data_RC          (str)     - obrigatorio, formato dd/MM/yyyy
        caminho_pasta    (str)     - obrigatorio, pasta local de destino do PDF
        nome_padrao      (str)     - obrigatorio, nome final do arquivo PDF
        carteira         (str)     - opcional, fallback de carteirinha
        paciente         (str)     - opcional, fallback de nome do paciente
    """
    job_id = job_data.get("job_id") or job_data.get("id")
    scraper.log(
        f"Iniciando OP6 (atualizar_rc) | id_paciente={job_data.get('id_paciente')} | "
        f"AbrevEsp={job_data.get('AbrevEsp')} | data_RC={job_data.get('data_RC')}",
        job_id=job_id
    )

    # 1. Garantir login ativo
    if not _ensure_login(scraper, job_id):
        return {
            "status": "error", "op": "op6_atualizar_rc", "id_convenio": 101,
            "message": "Falha no login antes da OP6", "code": CODE_AJAX_FAIL
        }

    # 2. Validar params obrigatorios
    required = ["id_paciente", "id_profissional", "AbrevEsp", "id_especialidade",
                "data_RC", "caminho_pasta", "nome_padrao"]
    missing = [k for k in required if not job_data.get(k)]
    if missing:
        msg = f"Params obrigatorios ausentes na OP6: {missing}"
        scraper.log(msg, level="ERROR", job_id=job_id)
        return {"status": "error", "op": "op6_atualizar_rc", "id_convenio": 101,
                "message": msg, "code": CODE_EXTRACT_FAIL}

    id_paciente = str(job_data["id_paciente"])
    id_profissional = str(job_data["id_profissional"])
    id_especialidade = str(job_data["id_especialidade"])
    data_rc_input = str(job_data["data_RC"]).strip()

    # 3. Converter data_RC de dd/MM/yyyy -> yyyy-MM-dd
    try:
        data_rc_iso = datetime.strptime(data_rc_input, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        msg = f"Formato de data_RC invalido: {data_rc_input} (esperado dd/MM/yyyy)"
        scraper.log(msg, level="ERROR", job_id=job_id)
        return {"status": "error", "op": "op6_atualizar_rc", "id_convenio": 101,
                "message": msg, "code": CODE_INVALID_DATE}

    # 4. Navegar ao prontuario do paciente
    prontuario_url = PRONTUARIO_URL_TEMPLATE.format(id_paciente=id_paciente)
    scraper.log(f"  -> Navegando para {prontuario_url}", job_id=job_id)
    scraper.driver.get(prontuario_url)

    try:
        # 5a. Extrair nome exato do paciente no portal
        nome_paciente_raw = ""
        try:
            nome_el = scraper.driver.find_element(By.XPATH, DOM_NOME_FOLLOWING_STRONG_XPATH)
            nome_paciente_raw = nome_el.text.strip()
        except NoSuchElementException:
            match = re.search(
                r'<span class="legend">Nome:</span>\s*<strong>(.*?)</strong>',
                scraper.driver.page_source, re.IGNORECASE
            )
            if match:
                nome_paciente_raw = match.group(1).strip()

        if not nome_paciente_raw:
            nome_paciente_raw = (job_data.get("paciente") or "").strip()
            scraper.log(
                f"  -> Nome nao extraido do DOM, usando fallback: '{nome_paciente_raw}'",
                level="WARN", job_id=job_id
            )
        nome_paciente_raw = " ".join(nome_paciente_raw.split())

        # 5b. Extrair carteirinha limpa
        carteirinha_raw = ""
        try:
            carteirinha_el = scraper.driver.find_element(By.ID, DOM_CARTEIRINHA_ID)
            carteirinha_raw = carteirinha_el.get_attribute("value") or ""
        except Exception:
            pass
        carteirinha_clean = re.sub(r"[\s.\-]", "", carteirinha_raw)
        scraper.log(f"  -> carteirinha_clean: '{carteirinha_clean}'", job_id=job_id)

        # 5c. Extrair justificativa
        justificativa = ""
        try:
            justificativa = scraper.driver.execute_script(
                f"return (document.getElementById('{DOM_JUSTIFICATIVA_ID}') || {{}}).value || '';"
            )
            if not justificativa:
                justificativa = scraper.driver.execute_script(
                    f"return (document.getElementById('{DOM_JUSTIFICATIVA_ID}') || {{}}).textContent || '';"
                )
        except Exception:
            pass
        if not justificativa:
            match = re.search(
                rf'<textarea[^>]*id=["\']{DOM_JUSTIFICATIVA_ID}["\'][^>]*>(.*?)</textarea>',
                scraper.driver.page_source, re.IGNORECASE | re.DOTALL
            )
            if match:
                justificativa = match.group(1)
        justificativa = (justificativa or "").strip()

        # 5d. Extrair evolucao
        evolucao_ipasgo = ""
        try:
            evolucao_ipasgo = scraper.driver.execute_script(
                f"return (document.getElementById('{DOM_EVOLUCAO_ID}') || {{}}).value || '';"
            )
            if not evolucao_ipasgo:
                evolucao_ipasgo = scraper.driver.execute_script(
                    f"return (document.getElementById('{DOM_EVOLUCAO_ID}') || {{}}).textContent || '';"
                )
        except Exception:
            pass
        if not evolucao_ipasgo:
            match = re.search(
                rf'<textarea[^>]*id=["\']{DOM_EVOLUCAO_ID}["\'][^>]*>(.*?)</textarea>',
                scraper.driver.page_source, re.IGNORECASE | re.DOTALL
            )
            if match:
                evolucao_ipasgo = match.group(1)
        evolucao_ipasgo = (evolucao_ipasgo or "").strip()

        # 5e. Extrair ipasgo_id (id interno do registro de RC)
        ipasgo_id = "2"
        try:
            extracted_id = scraper.driver.execute_script(
                "return document.querySelector('input[name=\"arr_relatorio[0][ipasgo_id]\"]')?.value || "
                "document.getElementById('ipasgo_id')?.value || "
                "document.querySelector('input[name=\"ipasgo_id\"]')?.value;"
            )
            if extracted_id:
                ipasgo_id = str(extracted_id).strip()
        except Exception:
            pass
        scraper.log(f"  -> ipasgo_id extraido: {ipasgo_id}", job_id=job_id)

        # 6. Protecao anti-wipeout: abortar se ambos vazios
        if not justificativa and not evolucao_ipasgo:
            msg = ("Atencao: Justificativa e Evolucao estao VAZIAS no portal. "
                   "Abortando POST para nao sobrescrever com vazio.")
            scraper.log(f"  -> {msg}", level="ERROR", job_id=job_id)
            return {"status": "error", "op": "op6_atualizar_rc", "id_convenio": 101,
                    "message": msg, "code": CODE_WIPEOUT_BLOCK}

    except TimeoutException:
        msg = f"Timeout ao carregar prontuario do paciente {id_paciente}"
        scraper.log(f"  -> {msg}", level="ERROR", job_id=job_id)
        return {"status": "error", "op": "op6_atualizar_rc", "id_convenio": 101,
                "message": msg, "code": CODE_EXTRACT_FAIL}
    except Exception as e:
        msg = f"Erro ao extrair dados do prontuario: {e}"
        scraper.log(f"  -> {msg}", level="ERROR", job_id=job_id)
        return {"status": "error", "op": "op6_atualizar_rc", "id_convenio": 101,
                "message": msg, "code": CODE_EXTRACT_FAIL}

    # 7. POST AJAX gravar RC
    scraper.log("  -> Enviando POST AJAX para gravar RC...", job_id=job_id)
    ajax_result = _post_gravar_rc(
        scraper, id_paciente, id_profissional, id_especialidade,
        justificativa, evolucao_ipasgo, data_rc_iso, ipasgo_id, job_id
    )
    if ajax_result.get("status") == "error":
        return {"status": "error", "op": "op6_atualizar_rc", "id_convenio": 101,
                "message": ajax_result.get("message", "Falha gravar RC"), "code": CODE_AJAX_FAIL}

    # 8. POST AJAX gerar PDF
    scraper.log("  -> Enviando POST AJAX para gerar PDF...", job_id=job_id)
    gerar_result = _post_gerar_pdf(scraper, ipasgo_id, job_id)
    if gerar_result.get("status") == "error":
        return {"status": "error", "op": "op6_atualizar_rc", "id_convenio": 101,
                "message": gerar_result.get("message", "Falha gerar PDF"), "code": CODE_PDF_NOT_GENERATED}

    # 9. Montar URL do PDF (encode de espacos)
    caminho_sufix = gerar_result.get("caminho", "")
    caminho_sufix_encoded = caminho_sufix.replace(" ", "%20")
    from config.constants import BASE_URL
    pdf_url = BASE_URL + caminho_sufix_encoded
    scraper.log(f"  -> PDF URL retornada pelo backend: {pdf_url}", job_id=job_id)

    # 10. Baixar PDF
    nome_padrao = str(job_data["nome_padrao"]).strip()
    caminho_pasta = str(job_data["caminho_pasta"]).strip()
    download_result = _download_pdf(scraper, pdf_url, caminho_pasta, nome_padrao, job_id)
    if download_result.get("status") == "error":
        return {"status": "error", "op": "op6_atualizar_rc", "id_convenio": 101,
                "message": download_result.get("message", "Falha download PDF"), "code": CODE_DOWNLOAD_FAIL}

    pdf_path = download_result.get("path", "")
    scraper.log(f"  OK OP6 concluida. Arquivo: {nome_padrao}", job_id=job_id)
    return {
        "status": "success",
        "op": "op6_atualizar_rc",
        "id_convenio": 101,
        "message": f"RC gravado e PDF baixado: {nome_padrao}",
        "paciente": nome_paciente_raw,
        "id_paciente": id_paciente,
        "data_RC": data_rc_iso,
        "pdf_caminho": pdf_path,
        "pdf_nome": nome_padrao,
    }


# Alias para compat com execute_op (que procura run ou execute)
execute = run
