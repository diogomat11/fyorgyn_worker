"""
OP20 - Validar e Extrair CodigoBeneficiario (IPASGO)

Fluxo:
1. Reutiliza a sessão autenticada da OP0 (IpasgoScraper.login).
2. Faz bootstrap em /GuiasTISS/LocalizarProcedimentos e fecha notificações
   exatamente como a OP11 (_close_notification_robust).
3. Injeta interceptador em XMLHttpRequest/fetch para capturar o payload de
   POST /LocalizarProcedimentos/Localizar (camada L3).
4. Para cada carteirinha do lote (isolado ao user_id do job):
   - Limpa o componente <beneficiario> (Selectize).
   - Digita a carteirinha no input do Selectize.
   - Aguarda carregamento do Selectize:
     * Se 1 item foi selecionado automaticamente (div.itemSelected[data-value]
       e input.inputSelectize.selectized[value]), lê L1 + L2.
     * Se abriu dropdown com múltiplas opções (.selectize-dropdown-content .option),
       compara o número da carteirinha entre parênteses "(<carteirinha>) NOME NASC: ..."
       e o nome do paciente com a carteirinha enviada, seleciona a opção correspondente
       e confirma.
     * Opcionalmente (ou quando houve desempate / fallback) aciona o botão Pesquisar
       (#localizar-procedimentos-btn) para extrair/confirmar "CodigoBeneficiario"
       diretamente do corpo da requisição POST /LocalizarProcedimentos/Localizar (L3).
5. Preserva o formato exato de CodigoBeneficiario retornado pelo portal
   (ex.: "040473-0", tamanho variável, sem remover hífen ou zeros à esquerda).
"""
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [
    p for p in sys.path
    if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)
]
if not sys.path or sys.path[0] != _mod_root:
    sys.path.insert(0, _mod_root)

from config.constants import (
    X_LOCALIZAR_CARTEIRA,
    X_LOCALIZAR_BTN_PESQUISAR,
    X_LOCALIZAR_DATA_INICIO,
    X_LOCALIZAR_DATA_FIM,
    CSS_BENEF_HIDDEN_INPUT,
    CSS_BENEF_ITEM_SELECTED,
    CSS_BENEF_REMOVE_BTN,
    CSS_BENEF_TEXT_INPUT,
    CSS_BENEF_DROPDOWN_OPTIONS,
    X_REMOVE_CARTEIRA_BENEF,
)
from op.op11_import_guias_api import _close_notification_robust

URL_LOCALIZAR_PROCEDIMENTOS = (
    "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos"
)

_TITLE_REGEX = re.compile(
    r"^\s*\(\s*([^)]+?)\s*\)\s*(.*?)(?:\s+NASC\s*:\s*(\d{2}/\d{2}/\d{4}))?\s*$",
    re.IGNORECASE,
)


def _normalizar_digitos(valor) -> str:
    """Retorna apenas os dígitos de uma carteirinha/identificador."""
    if not valor:
        return ""
    return "".join(ch for ch in str(valor) if ch.isdigit())


def _normalizar_digitos_sem_zeros(valor) -> str:
    """Retorna apenas dígitos sem zeros à esquerda (para comparação tolerante)."""
    d = _normalizar_digitos(valor)
    return d.lstrip("0") or ("0" if d else "")


def _normalizar_nome(nome) -> str:
    """Remove acentos, converte para maiúsculas e colapsa espaços."""
    if not nome:
        return ""
    s = str(nome).upper().strip()
    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(s.split())


def _parse_titulo_beneficiario(titulo: str) -> dict:
    """
    Faz parse do title/texto do Selectize:
      "(667372070) HEITOR SOUZA LYRA NASC: 22/05/2020"
    Retorna:
      {"carteirinha_titulo": "667372070", "nome": "HEITOR SOUZA LYRA", "nascimento": "22/05/2020"}
    """
    if not titulo:
        return {"carteirinha_titulo": "", "nome": "", "nascimento": ""}
    texto = " ".join(str(titulo).replace("×", " ").split())
    m = _TITLE_REGEX.match(texto)
    if not m:
        return {"carteirinha_titulo": "", "nome": texto, "nascimento": ""}
    return {
        "carteirinha_titulo": (m.group(1) or "").strip(),
        "nome": (m.group(2) or "").strip(),
        "nascimento": (m.group(3) or "").strip(),
    }


def _escolher_opcao_selectize(opcoes: list, carteirinha_alvo: str, paciente_alvo: str = "") -> dict:
    """
    Dado um conjunto de opções do Selectize:
      [{"valor": "040473-0", "titulo": "(667372070) HEITOR SOUZA LYRA NASC: 22/05/2020"}, ...]
    compara com a carteirinha enviada (e nome do paciente como desempate).

    Retorna:
      {
        "status": "OK" | "MULTIPLOS" | "SEM_CORRESPONDENCIA",
        "escolhida": {"valor": ..., "titulo": ...} | None,
        "candidatas": [...]
      }
    """
    if not opcoes:
        return {"status": "SEM_CORRESPONDENCIA", "escolhida": None, "candidatas": []}

    alvo_dig = _normalizar_digitos(carteirinha_alvo)
    alvo_sem_zero = _normalizar_digitos_sem_zeros(carteirinha_alvo)
    alvo_nome = _normalizar_nome(paciente_alvo)

    # Deduplicar opções pelo par (valor, titulo) mantendo ordem
    vistas = set()
    opcoes_unicas = []
    for op in opcoes:
        val = str(op.get("valor") or "").strip()
        tit = str(op.get("titulo") or "").strip()
        if not val:
            continue
        chave = (val, tit)
        if chave not in vistas:
            vistas.add(chave)
            opcoes_unicas.append({"valor": val, "titulo": tit})

    if not opcoes_unicas:
        return {"status": "SEM_CORRESPONDENCIA", "escolhida": None, "candidatas": []}

    # Se todas as opções apontam para o MESMO CodigoBeneficiario (valor), não há ambiguidade
    valores_distintos = {op["valor"] for op in opcoes_unicas}
    if len(valores_distintos) == 1:
        return {
            "status": "OK",
            "escolhida": opcoes_unicas[0],
            "candidatas": opcoes_unicas,
        }

    # 1. Filtrar por casamento exato do número entre parênteses com a carteirinha enviada
    casam_carteirinha = []
    for op in opcoes_unicas:
        parsed = _parse_titulo_beneficiario(op["titulo"])
        op_dig = _normalizar_digitos(parsed["carteirinha_titulo"])
        op_sem_zero = _normalizar_digitos_sem_zeros(parsed["carteirinha_titulo"])
        if alvo_dig and op_dig and (op_dig == alvo_dig or op_sem_zero == alvo_sem_zero):
            casam_carteirinha.append(op)

    if len(casam_carteirinha) == 1:
        return {
            "status": "OK",
            "escolhida": casam_carteirinha[0],
            "candidatas": casam_carteirinha,
        }

    # Se mais de 1 opção casou pela carteirinha (ou nenhuma casou porque o nº entre
    # parênteses é outra matrícula), tentar desempatar pelo nome do paciente
    pool_nome = casam_carteirinha if len(casam_carteirinha) > 1 else opcoes_unicas
    if alvo_nome:
        casam_nome = []
        for op in pool_nome:
            parsed = _parse_titulo_beneficiario(op["titulo"])
            nome_op = _normalizar_nome(parsed["nome"])
            if nome_op and nome_op == alvo_nome:
                casam_nome.append(op)
        if len(casam_nome) == 1:
            return {
                "status": "OK",
                "escolhida": casam_nome[0],
                "candidatas": casam_nome,
            }
        if len(casam_nome) > 1:
            valores_nome = {op["valor"] for op in casam_nome}
            if len(valores_nome) == 1:
                return {
                    "status": "OK",
                    "escolhida": casam_nome[0],
                    "candidatas": casam_nome,
                }
            return {
                "status": "MULTIPLOS",
                "escolhida": casam_nome[0],
                "candidatas": casam_nome,
            }

    if len(casam_carteirinha) > 1:
        return {
            "status": "MULTIPLOS",
            "escolhida": casam_carteirinha[0],
            "candidatas": casam_carteirinha,
        }

    return {
        "status": "SEM_CORRESPONDENCIA",
        "escolhida": None,
        "candidatas": opcoes_unicas,
    }


def _injetar_hook_localizar(driver):
    """
    Injeta interceptador JS em XMLHttpRequest e window.fetch para capturar
    o último payload JSON enviado para /LocalizarProcedimentos/Localizar.
    Idempotente: só instala o wrapper uma vez por carregamento de documento.
    """
    js = """
    if (!window.__hookLocalizarInstalled) {
        window.__hookLocalizarInstalled = true;
        window.__lastLocalizarPayload = null;
        window.__capLocalizarList = [];

        const origOpen = XMLHttpRequest.prototype.open;
        const origSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function(method, url) {
            this.__reqUrl = String(url || '');
            this.__reqMethod = String(method || '');
            return origOpen.apply(this, arguments);
        };

        XMLHttpRequest.prototype.send = function(body) {
            try {
                if (this.__reqUrl && this.__reqUrl.indexOf('LocalizarProcedimentos/Localizar') !== -1 && body) {
                    let parsed = null;
                    if (typeof body === 'string') {
                        try { parsed = JSON.parse(body); } catch (e) { parsed = { raw: body }; }
                    }
                    window.__lastLocalizarPayload = parsed;
                    window.__capLocalizarList.push({
                        ts: Date.now(),
                        url: this.__reqUrl,
                        payload: parsed
                    });
                }
            } catch (e) {}
            return origSend.apply(this, arguments);
        };

        if (window.fetch) {
            const origFetch = window.fetch;
            window.fetch = function(input, init) {
                try {
                    const url = typeof input === 'string' ? input : (input && input.url ? input.url : '');
                    if (url.indexOf('LocalizarProcedimentos/Localizar') !== -1 && init && init.body) {
                        let parsed = null;
                        if (typeof init.body === 'string') {
                            try { parsed = JSON.parse(init.body); } catch (e) { parsed = { raw: init.body }; }
                        }
                        window.__lastLocalizarPayload = parsed;
                        window.__capLocalizarList.push({
                            ts: Date.now(),
                            url: url,
                            payload: parsed
                        });
                    }
                } catch (e) {}
                return origFetch.apply(this, arguments);
            };
        }
    }
    """
    try:
        driver.execute_script(js)
    except Exception:
        pass


def _limpar_beneficiario(driver):
    """
    Limpa qualquer seleção anterior no componente <beneficiario> (Selectize)
    usando tanto a API JS do Selectize quanto o clique no botão 'remove' (×).
    """
    js_clear = """
    try {
        window.__lastLocalizarPayload = null;
        const hiddenInput = document.querySelector("beneficiario input.inputSelectize.selectized")
                         || document.querySelector("input.inputSelectize.selectized");
        if (hiddenInput && hiddenInput.selectize) {
            hiddenInput.selectize.clear(true);
            hiddenInput.selectize.clearOptions();
            hiddenInput.selectize.close();
        }
        const removes = document.querySelectorAll("beneficiario .selectize-input .itemSelected a.remove, beneficiario .selectize-input a");
        removes.forEach(a => { try { a.click(); } catch (e) {} });
        const txt = document.querySelector("beneficiario .selectize-input input[type='text'], beneficiario .selectize-input input");
        if (txt) {
            txt.value = '';
        }
        return true;
    } catch (e) {
        return false;
    }
    """
    try:
        driver.execute_script(js_clear)
    except Exception:
        pass

    try:
        removes = driver.find_elements(By.XPATH, X_REMOVE_CARTEIRA_BENEF)
        for r in removes:
            if r.is_displayed():
                try:
                    r.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", r)
                time.sleep(0.15)
    except Exception:
        pass


def _localizar_input_carteira(driver):
    """Encontra o input de texto do Selectize dentro de <beneficiario>."""
    try:
        elems = driver.find_elements(By.CSS_SELECTOR, CSS_BENEF_TEXT_INPUT)
        for el in elems:
            if el.is_enabled():
                return el
    except Exception:
        pass

    try:
        elems = driver.find_elements(By.XPATH, X_LOCALIZAR_CARTEIRA)
        for el in elems:
            if el.is_enabled():
                return el
    except Exception:
        pass
    return None


def _ler_estado_selectize(driver) -> dict:
    """
    Lê em uma única chamada JS:
      - hiddenValue: input.inputSelectize.selectized[value]
      - itemSelected: {valor, titulo} de div.itemSelected
      - dropdownOptions: lista [{valor, titulo}] das opções visíveis/carregadas no Selectize
      - isLoading: se .selectize-control tem classe 'loading'
    """
    js = """
    const root = document.querySelector("beneficiario") || document;
    const hidden = root.querySelector("input.inputSelectize.selectized");
    const hiddenValue = hidden ? (hidden.value || "") : "";
    const control = root.querySelector(".selectize-control");
    const isLoading = control ? control.classList.contains("loading") : false;

    const itemEl = root.querySelector(".selectize-input .itemSelected, .selectize-input [data-value]");
    let itemSelected = null;
    if (itemEl) {
        const val = itemEl.getAttribute("data-value") || "";
        const tit = itemEl.getAttribute("title") || itemEl.innerText || "";
        if (val) {
            itemSelected = { valor: val.trim(), titulo: tit.replace(/×/g, '').trim() };
        }
    }

    const opts = [];
    const optEls = root.querySelectorAll(".selectize-dropdown-content .option[data-value]");
    optEls.forEach(el => {
        const val = (el.getAttribute("data-value") || "").trim();
        const tit = (el.getAttribute("title") || el.innerText || "").trim();
        if (val) {
            opts.push({ valor: val, titulo: tit });
        }
    });

    if (opts.length === 0 && hidden && hidden.selectize && hidden.selectize.options) {
        const sOpts = hidden.selectize.options;
        Object.keys(sOpts).forEach(k => {
            const o = sOpts[k] || {};
            const val = String(o.Codigo || o.codigo || o.value || k || "").trim();
            const tit = String(o.Descricao || o.descricao || o.text || o.title || "").trim();
            if (val) {
                opts.push({ valor: val, titulo: tit });
            }
        });
    }

    return {
        hiddenValue: hiddenValue.trim(),
        itemSelected: itemSelected,
        dropdownOptions: opts,
        isLoading: Boolean(isLoading)
    };
    """
    try:
        res = driver.execute_script(js)
        if isinstance(res, dict):
            return res
    except Exception:
        pass
    return {
        "hiddenValue": "",
        "itemSelected": None,
        "dropdownOptions": [],
        "isLoading": False,
    }


def _selecionar_opcao_no_selectize(driver, valor_alvo: str) -> bool:
    """
    Seleciona uma opção específica (data-value == valor_alvo) no Selectize,
    tentando clique direto no elemento .option e API JS selectize.setValue.
    """
    js = """
    const targetVal = String(arguments[0] || '').trim();
    if (!targetVal) return false;
    const root = document.querySelector("beneficiario") || document;

    const optEls = root.querySelectorAll(".selectize-dropdown-content .option[data-value]");
    for (const el of optEls) {
        if ((el.getAttribute("data-value") || "").trim() === targetVal) {
            el.click();
            return true;
        }
    }

    const hidden = root.querySelector("input.inputSelectize.selectized");
    if (hidden && hidden.selectize) {
        hidden.selectize.setValue(targetVal, false);
        hidden.selectize.close();
        return true;
    }
    return false;
    """
    try:
        return bool(driver.execute_script(js, valor_alvo))
    except Exception:
        return False


def _extrair_codigo_via_pesquisar(driver) -> str:
    """
    Camada L3: Clica no botão Pesquisar (#localizar-procedimentos-btn) com o
    hook XHR/fetch ativo e lê "CodigoBeneficiario" do payload enviado para
    /LocalizarProcedimentos/Localizar.
    """
    _injetar_hook_localizar(driver)
    try:
        driver.execute_script("window.__lastLocalizarPayload = null;")
    except Exception:
        pass

    try:
        btn = driver.find_element(By.XPATH, X_LOCALIZAR_BTN_PESQUISAR)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        try:
            btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn)
    except Exception:
        return ""

    deadline = time.time() + 4.0
    while time.time() < deadline:
        try:
            payload = driver.execute_script("return window.__lastLocalizarPayload;")
            if isinstance(payload, dict) and payload.get("CodigoBeneficiario") is not None:
                cod = str(payload.get("CodigoBeneficiario") or "").strip()
                return cod
        except Exception:
            pass
        time.sleep(0.2)

    return ""


def _preencher_datas_curtas_bootstrap(driver):
    """
    Preenche um intervalo curto de 2 dias em Dt.Liberação Inicial/Final
    para que um eventual clique em Pesquisar (L3) seja aceito rapidamente pelo portal.
    """
    hoje = datetime.now()
    dt_ini = (hoje - timedelta(days=2)).strftime("%d/%m/%Y")
    dt_fim = hoje.strftime("%d/%m/%Y")
    js = """
    try {
        const inputs = document.querySelectorAll("input-periodo-data input");
        if (inputs && inputs.length >= 2) {
            if (!inputs[0].value) {
                inputs[0].value = arguments[0];
                inputs[0].dispatchEvent(new Event('change', { bubbles: true }));
            }
            if (!inputs[1].value) {
                inputs[1].value = arguments[1];
                inputs[1].dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
    } catch (e) {}
    """
    try:
        driver.execute_script(js, dt_ini, dt_fim)
    except Exception:
        pass


def _bootstrap_pagina_localizar(driver, scraper, job_id):
    """
    Navega para LocalizarProcedimentos, fecha notificações (como OP11),
    verifica se o componente <beneficiario> carregou e instala o hook XHR/fetch.
    """
    scraper.log(f"OP20 - Acessando URL Bootstrap: {URL_LOCALIZAR_PROCEDIMENTOS}", job_id=job_id)
    driver.get(URL_LOCALIZAR_PROCEDIMENTOS)

    for _ in range(12):
        try:
            if driver.execute_script("return document.readyState;") == "complete":
                break
        except Exception:
            pass
        time.sleep(1)
    time.sleep(2)

    # Se caiu na tela de login, refaz login via OP0 e reabre URL
    curr_url = (driver.current_url or "").lower()
    if "login" in curr_url or ("ipasgo" in curr_url and "facilinformatica" not in curr_url):
        scraper.log("OP20 - Sessão expirada detectada no bootstrap. Executando login (OP0)...", job_id=job_id)
        scraper.login()
        driver.get(URL_LOCALIZAR_PROCEDIMENTOS)
        time.sleep(3)

    # Fechar notificações exatamente como OP11
    for attempt in range(5):
        if _close_notification_robust(driver, scraper, job_id):
            scraper.log(f"OP20 - Notificação fechada na tentativa {attempt + 1}", job_id=job_id)
            break
        time.sleep(0.8)

    time.sleep(0.8)

    # Verificar se o input do beneficiário está presente
    inp = _localizar_input_carteira(driver)
    if not inp:
        scraper.log("OP20 - Input de beneficiário não localizado na 1ª tentativa; aplicando refresh...", level="WARN", job_id=job_id)
        driver.refresh()
        time.sleep(3)
        _close_notification_robust(driver, scraper, job_id)
        inp = _localizar_input_carteira(driver)
        if not inp:
            raise RuntimeError("Não foi possível localizar o campo Beneficiário em LocalizarProcedimentos.")

    _injetar_hook_localizar(driver)
    _preencher_datas_curtas_bootstrap(driver)


def _validar_uma_carteirinha(driver, scraper, job_id, item: dict, confirmar_l3: bool = False) -> dict:
    """
    Executa a extração em 3 camadas (L1, L2, L3) para uma carteirinha.
    """
    cart_id = item.get("carteirinha_id") or item.get("id")
    cart_str = str(item.get("carteirinha") or item.get("carteira") or "").strip()
    paciente = str(item.get("paciente") or "").strip()
    codigo_atual = item.get("codigo_beneficiario")
    if codigo_atual is not None:
        codigo_atual = str(codigo_atual).strip() or None

    resultado = {
        "carteirinha_id": cart_id,
        "carteirinha": cart_str,
        "paciente": paciente,
        "codigo_atual": codigo_atual,
        "codigo_portal": None,
        "titulo": None,
        "fonte": None,
        "opcoes": [],
        "status": "ERRO",
        "erro": None,
    }

    if not cart_str:
        resultado["status"] = "NAO_ENCONTRADA"
        resultado["erro"] = "Carteirinha vazia"
        return resultado

    _limpar_beneficiario(driver)
    time.sleep(0.2)

    inp = _localizar_input_carteira(driver)
    if not inp:
        raise RuntimeError("Input de beneficiário indisponível na página.")

    # Digitar apenas dígitos (ou string limpa) no Selectize
    cart_digitos = _normalizar_digitos(cart_str) or cart_str
    try:
        driver.execute_script("arguments[0].focus();", inp)
    except Exception:
        pass

    inp.send_keys(cart_digitos)

    # Aguardar Selectize consultar e popular itemSelected ou dropdownOptions (até 7.5s)
    estado = _ler_estado_selectize(driver)
    deadline = time.time() + 7.5
    seen_loading = estado.get("isLoading", False)
    while time.time() < deadline:
        time.sleep(0.3)
        estado = _ler_estado_selectize(driver)
        if estado.get("isLoading"):
            seen_loading = True
            continue
        if estado.get("itemSelected") or estado.get("hiddenValue"):
            break
        if estado.get("dropdownOptions"):
            # Aguarda mais 0.25s para estabilizar todas as opções
            time.sleep(0.25)
            estado = _ler_estado_selectize(driver)
            break
        # Se já passou 2.5s sem loading e sem opções, tenta enviar espaço/enter leve ou encerrar espera
        if seen_loading and not estado.get("isLoading"):
            break

    hidden_val = estado.get("hiddenValue") or ""
    item_sel = estado.get("itemSelected")
    opcoes = estado.get("dropdownOptions") or []
    resultado["opcoes"] = opcoes

    veio_de_desempate = False

    # Caso A: 1 item já selecionado automaticamente pelo Selectize
    if item_sel or hidden_val:
        val_l1 = hidden_val or (item_sel.get("valor") if item_sel else "")
        val_l2 = (item_sel.get("valor") if item_sel else "") or hidden_val
        titulo_l2 = (item_sel.get("titulo") if item_sel else "") or ""

        if val_l1 and val_l2 and val_l1 != val_l2:
            # Divergência entre input hidden e div.itemSelected -> confirmar via L3 (Pesquisar)
            cod_l3 = _extrair_codigo_via_pesquisar(driver)
            if cod_l3 and cod_l3 in (val_l1, val_l2):
                resultado["codigo_portal"] = cod_l3
                resultado["titulo"] = titulo_l2
                resultado["fonte"] = "L3_DESEMPATE_DOM"
                resultado["status"] = "OK"
                return resultado
            resultado["codigo_portal"] = val_l1
            resultado["titulo"] = titulo_l2
            resultado["fonte"] = "L1!=L2"
            resultado["status"] = "CONFLITO"
            resultado["erro"] = f"Divergência DOM: input='{val_l1}' vs itemSelected='{val_l2}' (L3='{cod_l3}')"
            return resultado

        codigo_extraido = val_l1 or val_l2
        resultado["codigo_portal"] = codigo_extraido
        resultado["titulo"] = titulo_l2
        resultado["fonte"] = "L1+L2"
        resultado["status"] = "OK"

    # Caso B: Dropdown com opções (múltiplas ou 1 opção aguardando clique)
    elif opcoes:
        veio_de_desempate = True
        decisao = _escolher_opcao_selectize(opcoes, cart_str, paciente)
        status_dec = decisao["status"]
        escolhida = decisao["escolhida"]
        resultado["opcoes"] = decisao["candidatas"] or opcoes

        if status_dec == "OK" and escolhida:
            _selecionar_opcao_no_selectize(driver, escolhida["valor"])
            time.sleep(0.3)
            estado_pos = _ler_estado_selectize(driver)
            val_dom = estado_pos.get("hiddenValue") or (estado_pos.get("itemSelected") or {}).get("valor") or escolhida["valor"]
            tit_dom = (estado_pos.get("itemSelected") or {}).get("titulo") or escolhida.get("titulo") or ""
            resultado["codigo_portal"] = val_dom
            resultado["titulo"] = tit_dom
            resultado["fonte"] = "L2_DROPDOWN"
            resultado["status"] = "OK"
        elif status_dec == "MULTIPLOS":
            # Duplicidade real no portal para a mesma carteirinha/paciente:
            # ainda assim selecionamos a 1ª candidata e confirmamos no Pesquisar (L3)
            # para registrar o código retornado, mantendo o alerta em opcoes/status
            if escolhida:
                _selecionar_opcao_no_selectize(driver, escolhida["valor"])
                time.sleep(0.3)
                resultado["codigo_portal"] = escolhida["valor"]
                resultado["titulo"] = escolhida.get("titulo")
            resultado["fonte"] = "L2_MULTIPLOS"
            resultado["status"] = "MULTIPLOS"
            resultado["erro"] = f"{len(decisao['candidatas'])} cadastros distintos encontrados no portal para a mesma carteirinha."
        else:
            resultado["fonte"] = "L2_SEM_MATCH"
            resultado["status"] = "SEM_CORRESPONDENCIA"
            resultado["erro"] = "Opções retornadas pelo portal não correspondem à carteirinha/paciente."
            return resultado
    else:
        resultado["status"] = "NAO_ENCONTRADA"
        resultado["fonte"] = "DOM_VAZIO"
        return resultado

    # Camada L3: clicar em Pesquisar quando veio de desempate no dropdown ou quando solicitado
    if resultado["status"] in ("OK", "MULTIPLOS") and (veio_de_desempate or confirmar_l3):
        cod_l3 = _extrair_codigo_via_pesquisar(driver)
        if cod_l3:
            if resultado["codigo_portal"] and cod_l3 != resultado["codigo_portal"]:
                resultado["status"] = "CONFLITO"
                resultado["erro"] = f"DOM='{resultado['codigo_portal']}' difere do payload Pesquisar L3='{cod_l3}'"
                resultado["fonte"] = f"{resultado['fonte']}+L3_CONFLITO"
            else:
                resultado["codigo_portal"] = cod_l3
                resultado["fonte"] = f"{resultado['fonte']}+L3"

    return resultado


def run(scraper, job_data):
    """
    Executa a OP20 (Validação e Extração de CodigoBeneficiario no IPASGO).
    Suporta tanto lista de carteirinhas em `job_data["carteirinhas"]` (lote/chunk)
    quanto execução unitária via `job_data["carteirinha"]` / `job_data["Carteira"]`.
    """
    driver = scraper.driver
    job_id = job_data.get("job_id") or job_data.get("id")

    modo = str(job_data.get("modo") or "validar_e_atualizar").strip().lower()
    confirmar_l3 = bool(job_data.get("confirmar_pesquisar", False))

    # Montar lista de itens a processar
    lista_carteirinhas = job_data.get("carteirinhas")
    if not isinstance(lista_carteirinhas, list) or not lista_carteirinhas:
        cart_unit = (
            job_data.get("carteirinha")
            or job_data.get("carteira")
            or job_data.get("Carteira")
            or ""
        )
        if cart_unit:
            lista_carteirinhas = [{
                "carteirinha_id": job_data.get("carteirinha_id"),
                "carteirinha": str(cart_unit).strip(),
                "paciente": job_data.get("paciente") or job_data.get("Paciente") or "",
                "codigo_beneficiario": job_data.get("codigo_beneficiario"),
            }]
        else:
            raise ValueError("OP20: Nenhuma carteirinha informada no job (esperado 'carteirinhas' ou 'carteira').")

    total = len(lista_carteirinhas)
    scraper.log(
        f"OP20 - Iniciando validação de CodigoBeneficiario para {total} carteirinha(s) (modo={modo})...",
        job_id=job_id,
    )

    _bootstrap_pagina_localizar(driver, scraper, job_id)

    resultados = []
    contagem = {
        "OK": 0,
        "MULTIPLOS": 0,
        "SEM_CORRESPONDENCIA": 0,
        "CONFLITO": 0,
        "NAO_ENCONTRADA": 0,
        "ERRO": 0,
    }

    for idx, item in enumerate(lista_carteirinhas, start=1):
        # Refresh preventivo a cada 50 carteirinhas para evitar degradação de memória do DOM/Selectize
        if idx > 1 and (idx - 1) % 50 == 0:
            scraper.log(f"OP20 - Refresh preventivo de sessão após {idx - 1} itens...", job_id=job_id)
            _bootstrap_pagina_localizar(driver, scraper, job_id)

        cart_num = item.get("carteirinha") or item.get("carteira") or ""
        try:
            res_item = _validar_uma_carteirinha(
                driver, scraper, job_id, item, confirmar_l3=confirmar_l3
            )
        except Exception as e:
            scraper.log(
                f"OP20 - Erro no item {idx}/{total} (carteirinha={cart_num}): {e}. Tentando re-bootstrap...",
                level="WARN",
                job_id=job_id,
            )
            try:
                _bootstrap_pagina_localizar(driver, scraper, job_id)
                res_item = _validar_uma_carteirinha(
                    driver, scraper, job_id, item, confirmar_l3=confirmar_l3
                )
            except Exception as e2:
                res_item = {
                    "carteirinha_id": item.get("carteirinha_id") or item.get("id"),
                    "carteirinha": str(cart_num),
                    "paciente": item.get("paciente") or "",
                    "codigo_atual": item.get("codigo_beneficiario"),
                    "codigo_portal": None,
                    "titulo": None,
                    "fonte": None,
                    "opcoes": [],
                    "status": "ERRO",
                    "erro": str(e2),
                }

        st = res_item.get("status", "ERRO")
        contagem[st] = contagem.get(st, 0) + 1
        resultados.append(res_item)

        if idx % 10 == 0 or idx == total or st != "OK":
            scraper.log(
                f"OP20 [{idx}/{total}] cart={cart_num} -> status={st} "
                f"codigo_portal={res_item.get('codigo_portal')} (atual={res_item.get('codigo_atual')})",
                job_id=job_id,
            )

    scraper.log(
        f"OP20 - Concluído: total={total} | OK={contagem['OK']} | "
        f"MULTIPLOS={contagem['MULTIPLOS']} | NAO_ENCONTRADA={contagem['NAO_ENCONTRADA']} | "
        f"SEM_CORRESPONDENCIA={contagem['SEM_CORRESPONDENCIA']} | CONFLITO={contagem['CONFLITO']} | ERRO={contagem['ERRO']}",
        job_id=job_id,
    )

    return {
        "status": "validacao_concluida",
        "modo": modo,
        "total": total,
        "resumo": contagem,
        "itens": resultados,
    }
