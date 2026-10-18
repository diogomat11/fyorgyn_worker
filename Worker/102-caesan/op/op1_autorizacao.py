from __future__ import annotations

import glob
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

# ── Isolate Environment (Fix Crosstalk) ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)]
if sys.path[0] != _mod_root:
    sys.path.insert(0, _mod_root)

from config.constants import (
    ALLOWED_EXTENSIONS,
    DEFAULT_TIMEOUT,
    IDX_CARATER_ELETIVO,
    IDX_INDICACAO_ACIDENTE,
    IDX_RECEM_NATO,
    IDX_TIPO_ATEND_OUTRAS_TERAPIAS,
    IDX_TIPO_CONSULTA,
    MAX_ANEXO_BYTES,
    RESULT_NUMERO_REGEX,
    SECRETARIA_PADRAO,
    SHORT_TIMEOUT,
    TABELA_OPTION_INDEX,
    URL_SP_SADT,
    X_BOTAO_GRAVAR,
    X_BOTAO_INCLUIR,
    X_BOTAO_PROFISSIONAL,
    X_FORM_DATA_SOLICITACAO,
    X_INPUT_CAMINHO_DOC,
    X_INPUT_CARTEIRA,
    X_INPUT_CODIGO,
    X_INPUT_DATA_ATENDIMENTO,
    X_INPUT_QUANTIDADE,
    X_INPUT_SECRETARIA,
    X_MODAL_INPUT_NOME_PROFISSIONAL,
    X_MODAL_LINHA_PROFISSIONAL,
    X_RESULT_NUMERO_CANDIDATES,
    X_SELECT_CARATER,
    X_SELECT_INDICACAO_ACIDENTE,
    X_SELECT_RECEM_NATO,
    X_SELECT_TABELA,
    X_SELECT_TIPO_ATENDIMENTO,
    X_SELECT_TIPO_CONSULTA,
    X_TEXTAREA_JUSTIFICATIVA,
)

if TYPE_CHECKING:
    from base_scraper import BaseScraper

# Técnica (planilha) → código de tabela do portal
TECNICA_TABELA_MAP = {
    "convencionais": "22",
    "especiais": "00",
}


def _parse_data(data_str) -> str:
    """Normaliza a data para dd/mm/aaaa (formato do portal)."""
    if not data_str:
        return datetime.now().strftime("%d/%m/%Y")
    if isinstance(data_str, datetime):
        return data_str.strftime("%d/%m/%Y")
    val = str(data_str).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(val.split(" ")[0], fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return val


def _select_option(driver, scraper, job_id, select_xpath: str, index_1based: int, label: str):
    """Clica no select e escolhe a option pelo índice (1-based, como mapeado no portal)."""
    el = WebDriverWait(driver, DEFAULT_TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, select_xpath))
    )
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)
    Select(el).select_by_index(index_1based - 1)
    scraper.log(f"Select '{label}' → option[{index_1based}]", job_id=job_id)


def _resolve_documento(caminho: str, carteira: str, scraper, job_id) -> Optional[str]:
    """
    Resolve o caminho local do documento (RC) para upload:
    - URL http(s) → download temporário (PADROES_ROTINAS §4.2);
    - caminho completo de arquivo → valida extensão/tamanho;
    - diretório → localiza o RC do paciente pelo padrão RC-*<carteira>*.
    """
    if not caminho:
        return None
    caminho = str(caminho).strip()

    local_path = caminho
    if caminho.lower().startswith(("http://", "https://")):
        scraper.log(f"[OP1] Documento: baixando de URL temporariamente...", job_id=job_id)
        try:
            parsed = urllib.parse.urlparse(caminho)
            filename = urllib.parse.unquote(os.path.basename(parsed.path)) or "documento.pdf"
            filename = re.sub(r'[\\/*?:"<>|]', '_', filename).replace(" ", "")
            temp_dir = tempfile.mkdtemp()
            local_path = os.path.join(temp_dir, filename)
            urllib.request.urlretrieve(caminho, local_path)
            scraper.log(f"[OP1] Documento: download OK → {local_path}", job_id=job_id)
        except Exception as e:
            scraper.log(f"[OP1] Documento: falha no download ({e})", level="ERROR", job_id=job_id)
            raise ValueError(f"Falha ao baixar documento da URL: {caminho}")

    # Diretório: procura o RC da carteira (padrão NOME_DOC: RC-<carteira>-<paciente>-<abrev>)
    if os.path.isdir(local_path):
        padroes = [f"RC-*{carteira}*", f"*{carteira}*.pdf", f"RC-*{carteira}*.*"]
        for padrao in padroes:
            matches = [
                p for p in glob.glob(os.path.join(local_path, padrao))
                if os.path.splitext(p)[-1].lower() in ALLOWED_EXTENSIONS
            ]
            if matches:
                local_path = sorted(matches)[0]
                scraper.log(f"[OP1] Documento localizado no diretório: {local_path}", job_id=job_id)
                break
        else:
            raise ValueError(
                f"Nenhum documento RC encontrado para a carteira {carteira} em {caminho} "
                f"(padrões: {padroes})"
            )

    if not os.path.isfile(local_path):
        raise ValueError(f"Documento não encontrado: {local_path}")

    ext = os.path.splitext(local_path)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extensão inválida para o documento ({ext}). Permitidos: {sorted(ALLOWED_EXTENSIONS)}")

    size = os.path.getsize(local_path)
    if size > MAX_ANEXO_BYTES:
        raise ValueError(f"Documento muito grande ({size/1024/1024:.1f}MB > 5MB)")

    return local_path


def _capturar_numero_solicitacao(driver, scraper, job_id) -> Optional[str]:
    """
    PENDÊNCIA: xpath oficial do frame de confirmação ainda não enviado.
    Best-effort: varre candidatos (sweet-alert/modal/toast/alert nativo) e
    extrai o primeiro número de 5-10 dígitos encontrado.
    """
    time.sleep(2)

    try:
        alert = driver.switch_to.alert
        texto = alert.text or ""
        alert.accept()
        m = re.search(RESULT_NUMERO_REGEX, texto)
        if m:
            scraper.log(f"[OP1] Nº da solicitação capturado de alert nativo: {m.group(1)}", job_id=job_id)
            return m.group(1)
    except Exception:
        pass

    for xp in X_RESULT_NUMERO_CANDIDATES:
        try:
            for el in driver.find_elements(By.XPATH, xp):
                texto = (el.text or "").strip()
                if texto:
                    m = re.search(RESULT_NUMERO_REGEX, texto)
                    if m:
                        scraper.log(f"[OP1] Nº da solicitação capturado ({xp}): {m.group(1)}", job_id=job_id)
                        return m.group(1)
        except Exception:
            continue

    scraper.log(
        "[OP1] Nº da solicitação NÃO capturado (xpath do frame de confirmação pendente) — "
        "job gravado com status 'submetido'; usar OP2 para recuperar o número",
        level="WARN", job_id=job_id
    )
    return None


def run(scraper: "BaseScraper", job_data: dict) -> dict:
    """
    OP1 — Autorização SP-SADT no portal CAESAN.
    Retorna dict no contrato do hub: guia/nº solicitação + status Pendente.
    """
    job_id = job_data.get("job_id")
    driver = scraper.driver

    carteira = str(
        job_data.get("carteira") or job_data.get("Carteira") or job_data.get("carteirinha") or ""
    ).strip()
    nome_profissional = str(job_data.get("nome_profissional") or job_data.get("Profissional_nome") or "").strip()
    justificativa = str(job_data.get("justificativa") or job_data.get("texto_Justificativa") or "").strip()
    codigo = str(job_data.get("codigo") or job_data.get("codigoProcedimento_aut") or job_data.get("codigo_procedimento") or "").strip()
    quantidade = str(job_data.get("quantidade") or job_data.get("qtde") or job_data.get("qtde_solicitada") or "1").strip()

    data_solicitacao = _parse_data(job_data.get("data_solicitacao") or job_data.get("dataSolicitacao"))
    data_atendimento = _parse_data(job_data.get("data_atendimento") or data_solicitacao)

    # Tabela: '22' (Convencionais) | '00' (Especiais) — derivável da Técnica da planilha
    tabela = str(job_data.get("tabela") or "").strip()
    if not tabela:
        tecnica = str(job_data.get("tecnica") or "").lower()
        for chave, cod in TECNICA_TABELA_MAP.items():
            if chave in tecnica:
                tabela = cod
                break
    if tabela not in TABELA_OPTION_INDEX:
        raise ValueError(
            f"Parâmetro 'tabela' inválido/ausente: '{tabela}'. Use '00' (Terapias Especiais) ou '22' (Terapias Convencionais)."
        )
    if not carteira:
        raise ValueError("Parâmetro obrigatório ausente: carteira")
    if not codigo:
        raise ValueError("Parâmetro obrigatório ausente: codigo (código do procedimento)")

    secretaria = str(job_data.get("secretaria") or SECRETARIA_PADRAO).strip()

    scraper.log(
        f"[OP1] SP-SADT: carteira={carteira} prof={nome_profissional or 'N/D'} tabela={tabela} "
        f"codigo={codigo} qtde={quantidade} data_solic={data_solicitacao} data_atend={data_atendimento}",
        job_id=job_id
    )

    # 1. Abrir formulário SP-SADT e aguardar carregamento
    driver.get(URL_SP_SADT)
    WebDriverWait(driver, DEFAULT_TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, X_FORM_DATA_SOLICITACAO))
    )
    scraper.log("[OP1] Formulário SP-SADT carregado", job_id=job_id)

    # 2. Data de solicitação
    el = driver.find_element(By.XPATH, X_FORM_DATA_SOLICITACAO)
    el.clear()
    el.send_keys(data_solicitacao)
    el.send_keys(Keys.TAB)

    # 3. Selects fixos do fluxo (índices mapeados no portal)
    _select_option(driver, scraper, job_id, X_SELECT_CARATER, IDX_CARATER_ELETIVO, "Caráter da solicitação (Eletivo)")
    _select_option(driver, scraper, job_id, X_SELECT_TIPO_ATENDIMENTO, IDX_TIPO_ATEND_OUTRAS_TERAPIAS, "Tipo de atendimento (Outras Terapias)")
    _select_option(driver, scraper, job_id, X_SELECT_TIPO_CONSULTA, IDX_TIPO_CONSULTA, "Tipo de consulta")
    _select_option(driver, scraper, job_id, X_SELECT_RECEM_NATO, IDX_RECEM_NATO, "Recém-nato")
    _select_option(driver, scraper, job_id, X_SELECT_INDICACAO_ACIDENTE, IDX_INDICACAO_ACIDENTE, "Indicação de acidente")

    # 4. Carteira (TAB dispara validação do beneficiário)
    el = driver.find_element(By.XPATH, X_INPUT_CARTEIRA)
    el.clear()
    el.send_keys(carteira)
    el.send_keys(Keys.TAB)
    time.sleep(1)

    # 5. Profissional (modal de busca)
    btn = WebDriverWait(driver, DEFAULT_TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, X_BOTAO_PROFISSIONAL))
    )
    try:
        btn.click()
    except Exception:
        driver.execute_script("arguments[0].click();", btn)
    time.sleep(1)

    if not nome_profissional:
        raise ValueError("Parâmetro obrigatório ausente: nome_profissional")

    inp = WebDriverWait(driver, DEFAULT_TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, X_MODAL_INPUT_NOME_PROFISSIONAL))
    )
    inp.clear()
    inp.send_keys(nome_profissional)
    time.sleep(1)

    try:
        linha = WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, X_MODAL_LINHA_PROFISSIONAL))
        )
    except Exception:
        raise ValueError(
            f"PermanentError: Profissional não cadastrado no portal CAESAN: {nome_profissional}"
        )
    if not (linha.text or "").strip():
        raise ValueError(
            f"PermanentError: Profissional não cadastrado no portal CAESAN: {nome_profissional}"
        )
    try:
        linha.click()
    except Exception:
        driver.execute_script("arguments[0].click();", linha)
    time.sleep(1)
    scraper.log(f"[OP1] Profissional selecionado: {nome_profissional}", job_id=job_id)

    # 6. Data do atendimento + Secretaria
    el = driver.find_element(By.XPATH, X_INPUT_DATA_ATENDIMENTO)
    el.clear()
    el.send_keys(data_atendimento)
    el.send_keys(Keys.TAB)

    el = driver.find_element(By.XPATH, X_INPUT_SECRETARIA)
    el.clear()
    el.send_keys(secretaria)

    # 7. Justificativa (scroll até o elemento)
    el = driver.find_element(By.XPATH, X_TEXTAREA_JUSTIFICATIVA)
    driver.execute_script("arguments[0].scrollIntoView(true);", el)
    time.sleep(0.5)
    el.clear()
    el.send_keys(justificativa or "Autorização de sessões de terapia conforme plano terapêutico.")

    # 8. Tabela + código + quantidade
    _select_option(driver, scraper, job_id, X_SELECT_TABELA, TABELA_OPTION_INDEX[tabela], f"Tabela ({tabela})")

    el = driver.find_element(By.XPATH, X_INPUT_CODIGO)
    el.clear()
    el.send_keys(codigo)
    el.send_keys(Keys.TAB)

    el = driver.find_element(By.XPATH, X_INPUT_QUANTIDADE)
    el.clear()
    el.send_keys(str(int(float(quantidade))))

    # 9. Incluir item
    btn = WebDriverWait(driver, DEFAULT_TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, X_BOTAO_INCLUIR))
    )
    try:
        btn.click()
    except Exception:
        driver.execute_script("arguments[0].click();", btn)
    time.sleep(1)

    # 10. Documento (caminho local resolvido ou URL baixada)
    caminho_doc_param = (
        job_data.get("caminho_doc") or job_data.get("caminho") or job_data.get("anexo_RM") or ""
    )
    if caminho_doc_param:
        local_doc = _resolve_documento(caminho_doc_param, carteira, scraper, job_id)
        inp = driver.find_element(By.XPATH, X_INPUT_CAMINHO_DOC)
        inp.send_keys(local_doc)
        scraper.log(f"[OP1] Documento anexado: {os.path.basename(local_doc)}", job_id=job_id)
    else:
        scraper.log("[OP1] Sem documento informado — gravando solicitação sem anexo", level="WARN", job_id=job_id)

    # 11. Gravar
    btn = WebDriverWait(driver, DEFAULT_TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, X_BOTAO_GRAVAR))
    )
    try:
        btn.click()
    except Exception:
        driver.execute_script("arguments[0].click();", btn)
    scraper.log("[OP1] Botão Gravar acionado", job_id=job_id)

    # 12. Capturar nº da solicitação (xpath pendente — best-effort)
    numero_solicitacao = _capturar_numero_solicitacao(driver, scraper, job_id)

    status = "submetido" if not numero_solicitacao else "pendente"
    resultado = {
        "status": status,
        "status_guia": "Pendente",
        "guia": str(numero_solicitacao) if numero_solicitacao else f"Solicitação #{job_id}",
        "numero_solicitacao": str(numero_solicitacao) if numero_solicitacao else None,
        "carteira": carteira,
        "carteirinha_id": job_data.get("carteirinha_id"),
        "codigo_terapia": codigo,
        "qtde_solicitada": int(float(quantidade)),
        "data_solicitacao": data_solicitacao,
        "data_atendimento": data_atendimento,
        "profissional": nome_profissional,
        "tabela": tabela,
        "id_convenio": job_data.get("id_convenio"),
        "observacao": (
            "Solicitação gravada no portal CAESAN; nº capturado." if numero_solicitacao
            else "Solicitação gravada no portal CAESAN; nº ainda não capturado (xpath pendente) — consultar via OP2."
        ),
    }
    scraper.log(f"[OP1] Resultado: {resultado['status']} | nº={numero_solicitacao}", job_id=job_id)
    return resultado
