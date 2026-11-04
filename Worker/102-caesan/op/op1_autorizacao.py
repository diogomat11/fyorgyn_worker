from __future__ import annotations

import glob
import hashlib
import json
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
    BIOS_WS_CHAVE,
    BIOS_WS_CODDAO_AUTORIZADAS,
    BIOS_WS_CODDAO_PENDENTES,
    BIOS_WS_URL,
    DEFAULT_TIMEOUT,
    ITEM_DESCRICAO_TIMEOUT,
    ITEM_INCLUIR_TIMEOUT,
    LONG_TIMEOUT,
    MAX_ANEXO_BYTES,
    PAUSA_PASSO_FORM,
    PAUSA_POS_ANEXO,
    PAUSA_POS_INCLUIR_ITEM,
    PAUSA_PRE_GRAVAR_PADRAO,
    PAUSA_PRE_INCLUIR_ITEM,
    REGEX_DATA_DDMMAAAA,
    REGEX_DATA_ISO,
    RESULT_NUMERO_REGEX,
    SECRETARIA_PADRAO,
    SHORT_TIMEOUT,
    TABELA_VALUE,
    URL_SP_SADT,
    VAL_CARATER_ELETIVO,
    VAL_INDICACAO_ACIDENTE,
    VAL_RECEM_NATO,
    VAL_TIPO_ATEND_OUTRAS_TERAPIAS,
    VAL_TIPO_CONSULTA,
    X_ALERTA_FALHA,
    X_BOTAO_BUSCA_PROF_NG,
    X_BOTAO_GRAVAR,
    X_BOTAO_GRAVAR_NG,
    X_BOTAO_INCLUIR,
    X_BOTAO_INCLUIR_NG,
    X_BOTAO_PROFISSIONAL,
    X_BOTAO_PROFISSIONAL_NG,
    X_DATA_ATENDIMENTO_NG,
    X_DATA_SOLICITACAO_NG,
    X_INPUT_BUSCA_PROF_NG,
    X_INPUT_CAMINHO_DOC,
    X_INPUT_CAMINHO_DOC_NG,
    X_INPUT_CARTEIRA,
    X_INPUT_CARTEIRA_NG,
    X_INPUT_CODIGO,
    X_INPUT_CODIGO_NG,
    X_INPUT_NOMEBENEF_NG,
    X_INPUT_PROF_SELEC_NG,
    X_INPUT_QUANTIDADE,
    X_INPUT_QUANTIDADE_NG,
    X_INPUT_SECRETARIA,
    X_INPUT_SECRETARIA_NG,
    X_LINHA_PROF_MODAL_NG,
    X_LINHAS_PROCEDIMENTOS_TABELA,
    X_RESULT_NUMERO_CANDIDATES,
    X_RESULT_NUMERO_OFICIAL,
    X_SELECT_CARATER,
    X_SELECT_CARATER_NG,
    X_SELECT_INDICACAO_ACIDENTE,
    X_SELECT_IND_ACIDENTE_NG,
    X_SELECT_RECEM_NATO,
    X_SELECT_RECEM_NATO_NG,
    X_SELECT_TABELA,
    X_SELECT_TABELA_NG,
    X_SELECT_TIPO_ATENDIMENTO,
    X_SELECT_TIPO_ATEND_NG,
    X_SELECT_TIPO_CONSULTA,
    X_SELECT_TIPO_CONSULTA_NG,
    X_TEXTAREA_JUSTIFICATIVA,
    X_TEXTAREA_JUSTIFICATIVA_NG,
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


# ─────────────────────────────────────────────────────────────────────────────
# Infra de localização/diagnóstico
# ─────────────────────────────────────────────────────────────────────────────

def _tipo_efetivo(driver, el) -> str:
    """Tipo real do input: propriedade DOM (autoritativa) com fallback ao atributo."""
    try:
        prop = driver.execute_script("return (arguments[0] && arguments[0].type) || '';", el)
        if prop:
            return str(prop).lower()
    except Exception:
        pass
    return (el.get_attribute("type") or "").lower()


_TIPOS_TEXTO_OK = {"", "text", "search", "tel", "number", "email"}


def _evidencia_falha(driver, scraper, job_id, motivo: str):
    """Screenshot + HTML do contexto atual para diagnóstico remoto (frota)."""
    try:
        pasta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug")
        os.makedirs(pasta, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.join(pasta, f"op1_{stamp}_{job_id or 'nojob'}")
        try:
            driver.save_screenshot(base + ".png")
        except Exception:
            pass
        try:
            with open(base + ".html", "w", encoding="utf-8", errors="replace") as f:
                f.write(driver.page_source or "")
        except Exception:
            pass
        scraper.log(f"[OP1] Evidência da falha salva em {base}.(.png/.html) — {motivo}", level="WARN", job_id=job_id)
    except Exception as e:
        scraper.log(f"[OP1] Falha ao salvar evidência: {e}", level="WARN", job_id=job_id)


def _dump_form_estrutura(driver, scraper, job_id, motivo: str):
    """Loga a estrutura do form (ng-model/placeholder/options de cada campo)."""
    js = (
        "const inp = document.evaluate(arguments[0], document, null, "
        "  XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;"
        "const form = inp && inp.closest('form');"
        "if (!form) return null;"
        "return Array.from(form.querySelectorAll('input, select, textarea, button')).map((ctrl, i) => {"
        "  const opts = ctrl.tagName === 'SELECT'"
        "    ? Array.from(ctrl.options).map(o => (o.value + '=' + o.text.trim())).slice(0, 10) : null;"
        "  return {i: i + 1, tag: ctrl.tagName.toLowerCase(), type: ctrl.type || '',"
        "    ngModel: ctrl.getAttribute('ng-model') || '', ngClick: ctrl.getAttribute('ng-click') || '',"
        "    placeholder: ctrl.placeholder || '', disabled: ctrl.disabled, options: opts};"
        "});"
    )
    try:
        estrutura = driver.execute_script(js, X_DATA_SOLICITACAO_NG)
        if estrutura:
            scraper.log(f"[OP1] Estrutura do formulário ({motivo}): {estrutura}", job_id=job_id)
        else:
            scraper.log(f"[OP1] Estrutura do formulário: form não localizado via {X_DATA_SOLICITACAO_NG} ({motivo})", level="WARN", job_id=job_id)
    except Exception as e:
        scraper.log(f"[OP1] Falha ao extrair estrutura do formulário ({motivo}): {e}", level="WARN", job_id=job_id)


def _localizar(driver, scraper, job_id, candidatos, kind: str, label: str, timeout_seg: float = DEFAULT_TIMEOUT):
    """
    Localiza um campo testando candidatos (ng-model/ng-click do portal → xpath
    absoluto histórico) e VALIDA tag+tipo antes de devolver ('date'|'text'|
    'textarea'|'select'|'button'|'file'). Sem match → evidência + dump +
    PermanentError descritivo (nada é escrito em campo errado).
    """
    deadline = time.time() + timeout_seg
    vistos = set()
    while time.time() < deadline:
        for xp in candidatos:
            try:
                els = driver.find_elements(By.XPATH, xp)
            except Exception:
                continue
            for el in els:
                try:
                    key = el.id
                except Exception:
                    continue
                if key in vistos:
                    continue
                vistos.add(key)
                try:
                    tag = (el.tag_name or "").lower()
                    tipo = _tipo_efetivo(driver, el)
                    if kind == "date" and tag == "input" and tipo == "date":
                        return el
                    if kind == "text" and tag == "input" and tipo in _TIPOS_TEXTO_OK:
                        return el
                    if kind == "textarea" and tag == "textarea":
                        return el
                    if kind == "select" and tag == "select":
                        return el
                    if kind == "button" and (tag == "button" or (tag == "input" and tipo in ("submit", "button"))):
                        return el
                    if kind == "file" and tag == "input" and tipo == "file":
                        return el
                except Exception:
                    continue
        time.sleep(0.5)
    _dump_form_estrutura(driver, scraper, job_id, f"campo '{label}' ({kind}) não localizado")
    _evidencia_falha(driver, scraper, job_id, f"campo '{label}' ({kind}) não localizado")
    raise ValueError(
        f"PermanentError: campo '{label}' ({kind}) não localizado/inválido no portal "
        f"(candidatos testados: {candidatos}) — ver 'Estrutura do formulário' no log e evidência em debug/."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Interações com o portal
# ─────────────────────────────────────────────────────────────────────────────

def _digitar(el, valor: str):
    el.clear()
    el.send_keys(valor)


# ── Modo validação (params['modo_validacao']): execução pausada com screenshot
# + leitura de volta de cada campo — para homologação passo a passo até a
# emissão real da guia. Problemas silenciosos (campo limpo pelo portal, form
# inválido no Gravar) viram erro explícito com diagnóstico.

def _step_validacao(driver, scraper, job_id, modo: bool, passo: str, pausa: float = 2.0):
    if not modo:
        return
    try:
        pasta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug")
        os.makedirs(pasta, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arq = os.path.join(pasta, f"passo_{stamp}_{job_id or 'nojob'}_{re.sub(r'[^a-z0-9]+','_',passo.lower())[:40]}.png")
        driver.save_screenshot(arq)
        scraper.log(f"[OP1][VALIDAÇÃO] passo '{passo}' — screenshot: {os.path.basename(arq)}", job_id=job_id)
    except Exception as e:
        scraper.log(f"[OP1][VALIDAÇÃO] passo '{passo}' — falha ao salvar screenshot: {e}", level="WARN", job_id=job_id)
    time.sleep(pausa)


def _ler_campo(driver, xpath: str) -> str:
    try:
        return (driver.find_element(By.XPATH, xpath).get_attribute("value") or "").strip()
    except Exception:
        return "<campo não encontrado>"


def _cls(driver, xpath: str) -> str:
    try:
        return driver.find_element(By.XPATH, xpath).get_attribute("class") or ""
    except Exception:
        return ""


def _logar_estado_campos(driver, scraper, job_id, modo: bool, contexto: str):
    if not modo:
        return
    estado = {
        "dtpedido": _ler_campo(driver, X_DATA_SOLICITACAO_NG),
        "carater": _ler_campo(driver, X_SELECT_CARATER_NG),
        "carteira": _ler_campo(driver, X_INPUT_CARTEIRA_NG),
        "beneficiario_ok": "user-success" in _cls(driver, X_INPUT_CARTEIRA_NG),
        "tipoexame": _ler_campo(driver, X_SELECT_TIPO_ATEND_NG),
        "profissional": _ler_campo(driver, X_INPUT_PROF_SELEC_NG),
        "dtprovproc": _ler_campo(driver, X_DATA_ATENDIMENTO_NG),
        "secretaria": _ler_campo(driver, X_INPUT_SECRETARIA_NG),
        "justificativa": _ler_campo(driver, X_TEXTAREA_JUSTIFICATIVA_NG)[:60],
        "tabela": _ler_campo(driver, X_SELECT_TABELA_NG),
        "codigo": _ler_campo(driver, X_INPUT_CODIGO_NG),
        "quantidade": _ler_campo(driver, X_INPUT_QUANTIDADE_NG),
    }
    scraper.log(f"[OP1][VALIDAÇÃO] estado dos campos ({contexto}): {estado}", job_id=job_id)


def _campos_invalidos_angular(driver) -> list:
    """Lista ng-model dos campos marcados inválidos pelo Angular — diagnóstico
    pré-Gravar (evita clique perdido em botão desabilitado)."""
    js = (
        "return Array.from(document.querySelectorAll('form .ng-invalid'))"
        ".filter(function(e){return e.getAttribute('ng-model');})"
        ".map(function(e){return e.getAttribute('ng-model');});"
    )
    try:
        return list(driver.execute_script(js) or [])
    except Exception:
        return []


def _clicar_com_retry(driver, scraper, job_id, candidatos, kind, label, tentativas: int = 3):
    """
    Localiza e clica com retry contra stale element (Angular re-renderiza nós
    entre a localização e o clique). Re-localiza a cada tentativa.
    """
    ultimo_erro = None
    for i in range(tentativas):
        el = _localizar(driver, scraper, job_id, candidatos, kind, label)
        try:
            try:
                el.click()
            except Exception:
                driver.execute_script("arguments[0].click();", el)
            return el
        except Exception as e:
            ultimo_erro = e
            scraper.log(f"[OP1] clique em '{label}' falhou ({str(e)[:80]}) — re-localizando ({i+1}/{tentativas})", level="WARN", job_id=job_id)
            time.sleep(1)
    raise ultimo_erro


def _ler_scope_sadt(driver) -> dict:
    """
    Lê o estado detalhado do scope Angular ctrSpSadt sem truncamento de chaves.
    Nota crítica: em ctrSpSadt.js, `$scope.alerta` é uma `function(codigo, conteudo)`
    com propriedades `.titulo`, `.mensagem`, `.complemento` anexadas à própria função.
    `JSON.stringify(fn)` retorna `undefined` em JS (e `JSON.parse(undefined)` lança
    SyntaxError). Por isso usamos `clone()` seguro e extraímos `alerta` explicitamente.
    """
    js = (
        "var el = document.querySelector(\"[ng-controller='ctrSpSadt']\");"
        "var s = el && window.angular && angular.element(el).scope();"
        "if (!s) return {disponivel: false};"
        "function clone(x) {"
        "  if (x === undefined || x === null) return null;"
        "  try {"
        "    var str = JSON.stringify(x);"
        "    return str === undefined ? null : JSON.parse(str);"
        "  } catch (e) { return String(x); }"
        "}"
        "var v1 = s.objVO0481 || {};"
        "var v2 = s.objVO0482 || {};"
        "var v6 = s.objVO0406 || {};"
        "var v3 = s.objVO0306 || {};"
        "var procs = Array.isArray(v1.procedimentos) ? v1.procedimentos : [];"
        "var arqs = Array.isArray(v1.lstarquivos) ? v1.lstarquivos.map(function(a){"
        "  return {filename: (a && a.filename) || null, filetype: (a && a.filetype) || null,"
        "          filesize: (a && a.filesize) || 0,"
        "          base64_len: (a && a.base64) ? String(a.base64).length : 0};"
        "}) : [];"
        "var alertaInfo = null;"
        "if (s.alerta) {"
        "  alertaInfo = {"
        "    titulo: s.alerta.titulo || null,"
        "    mensagem: clone(s.alerta.mensagem),"
        "    complemento: clone(s.alerta.complemento)"
        "  };"
        "}"
        "return {"
        "  disponivel: true,"
        "  dtpedido: v1.dtpedido || null,"
        "  dtprovproc: v1.dtprovproc || null,"
        "  codassociado: v1.codassociado || null,"
        "  caratersolicitacao: v1.caratersolicitacao || null,"
        "  tipoexame: v1.tipoexame || null,"
        "  codtipconsulta: v1.codtipconsulta || null,"
        "  atendimentorn: v1.atendimentorn || null,"
        "  codindacidente: v1.codindacidente || null,"
        "  secretsolic: v1.secretsolic || null,"
        "  indicacao_len: v1.indicacao ? String(v1.indicacao).length : 0,"
        "  codprofissional: v1.codprofissional || v1.inscricao || null,"
        "  nommedico: v1.nommedico || null,"
        "  procedimentos_count: procs.length,"
        "  procedimentos: clone(procs),"
        "  lstarquivos_count: arqs.length,"
        "  lstarquivos_meta: arqs,"
        "  profissional_vo406: clone(v6),"
        "  item_edicao_vo482: clone(v2),"
        "  alertaProcedimento: !!s.alertaProcedimento,"
        "  alertabloqueio: !!s.alertabloqueio,"
        "  alerta: alertaInfo,"
        "  nrguiaunimed: v1.nrguiaunimed || null,"
        "  has_token: !!s.token,"
        "  codprestador: s.codprestador || null,"
        "  codpessoa: v3.codpessoa || null,"
        "  codperfil: v3.codperfil || null,"
        "  usuario_benef: (s.usuario && s.usuario.nombeneficiario) ? String(s.usuario.nombeneficiario) : null,"
        "  carater_opts_len: Array.isArray(s.lstCarSolicitacao) ? s.lstCarSolicitacao.length : 0,"
        "  tipoatend_opts_len: Array.isArray(s.lstTipoAtendimento) ? s.lstTipoAtendimento.length : 0,"
        "  proctuss_opts_len: Array.isArray(s.procTuss) ? s.procTuss.length : 0"
        "};"
    )
    try:
        res = driver.execute_script(js)
        return res if isinstance(res, dict) else {"disponivel": False}
    except Exception as e:
        return {"disponivel": False, "erro": str(e)}


def _resumir_req_bios(req_raw: str) -> str:
    """
    Sanitiza o JSON de requisição do BIOS para log completo sem cortar `procedimentos`
    por causa do payload base64 em `lstarquivos`.
    """
    if not req_raw:
        return ""
    try:
        data = json.loads(req_raw)
        if isinstance(data, dict):
            conteudo = data.get("conteudo")
            if isinstance(conteudo, dict) and isinstance(conteudo.get("lstarquivos"), list):
                arqs_limpos = []
                for arq in conteudo["lstarquivos"]:
                    if isinstance(arq, dict):
                        copia = dict(arq)
                        b64 = copia.get("base64")
                        if isinstance(b64, str):
                            sha = hashlib.sha256(b64.encode("utf-8", errors="ignore")).hexdigest()[:12]
                            copia["base64"] = f"<base64 len={len(b64)} sha256={sha}>"
                        arqs_limpos.append(copia)
                    else:
                        arqs_limpos.append(arq)
                conteudo = dict(conteudo)
                conteudo["lstarquivos"] = arqs_limpos
                data = dict(data)
                data["conteudo"] = conteudo
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        # Fallback regex caso o JSON tenha vindo truncado ou malformado
        return re.sub(
            r'"base64"\s*:\s*"[^"]*"',
            lambda m: f'"base64":"<base64 chars={len(m.group(0))}>"',
            req_raw,
        )


def _preencher_data_texto(driver, el, data_ddmmaaaa: str, scraper, job_id, label: str, ng_model: str = ""):
    """
    Preenche os campos de data (`dtpedido` e `dtprovproc`) do SP-SADT respeitando o contrato
    exato de `ctrSpSadt.js`:
    - No portal real (controller Angular `ctrSpSadt` ativo), `gravarGuia()` converte `dtpedido`
      e `dtprovproc` fatiando ISO `YYYY-MM-DD`:
        `ano = dt.substring(0, 4); mes = dt.substring(5, 7); dia = dt.substring(8, 10);`
        `body.conteudo.dtpedido = dia + "/" + mes + "/" + ano;`
      Portanto, se o scope contiver `DD/MM/YYYY` ('04/11/2026'), `gravarGuia()` fatia os índices
      errados e envia `'26//2/04/1'` ao BIOS! No portal real, o input usa `type='date'` (que exibe
      `04/11/2026` na tela em pt-BR mas armazena `YYYY-MM-DD` = `'2026-11-04'` no DOM e no
      `objVO0481`), produzindo `'04/11/2026'` no payload final do `coddao: 483`.
    - No mock estático (`window.angular` ausente), mantém `type='text'` e `DD/MM/YYYY`.
    """
    try:
        iso_esperado = datetime.strptime(data_ddmmaaaa, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        iso_esperado = data_ddmmaaaa

    tem_angular = bool(_ler_scope_sadt(driver).get("disponivel"))
    campo_vo = ng_model.split(".")[-1] if ng_model else ""

    def _data_valida_lida() -> tuple[bool, str, str]:
        val_dom = ""
        try:
            val_dom = (driver.execute_script("return arguments[0].value || '';", el) or "").strip()
        except Exception:
            pass
        val_scope = ""
        if campo_vo and tem_angular:
            try:
                val_scope = str(driver.execute_script(
                    "var el = document.querySelector(\"[ng-controller='ctrSpSadt']\");"
                    "var s = el && window.angular && angular.element(el).scope();"
                    "return (s && s.objVO0481 && s.objVO0481[arguments[0]]) || '';",
                    campo_vo,
                ) or "").strip()
            except Exception:
                pass
        if tem_angular:
            # No portal Angular real, scope DEVE ser ISO YYYY-MM-DD para gravarGuia() gerar DD/MM/YYYY
            ok_scope = (val_scope == iso_esperado and bool(re.fullmatch(REGEX_DATA_ISO, val_scope)))
            ok_dom = val_dom in (iso_esperado, data_ddmmaaaa)
            return (ok_scope and ok_dom), val_dom, val_scope
        else:
            ok_dom = (val_dom == data_ddmmaaaa and bool(re.fullmatch(REGEX_DATA_DDMMAAAA, val_dom))) or (val_dom == iso_esperado)
            return ok_dom, val_dom, val_scope

    for tentativa in range(1, 4):
        if tem_angular:
            # Portal real (ctrSpSadt): ativa type='date' (como o onfocus nativo do portal),
            # define valor ISO YYYY-MM-DD (exibido como DD/MM/YYYY pelo Chrome) e sincroniza scope.
            try:
                driver.execute_script(
                    "var e = arguments[0], iso = arguments[1], campo = arguments[2];"
                    "try { if (window.jQuery && jQuery(e).unmask) { jQuery(e).unmask(); } } catch(err) {}"
                    "try { e.type = 'date'; } catch(err) {}"
                    "var desc = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');"
                    "if (desc && desc.set) { desc.set.call(e, iso); } else { e.value = iso; }"
                    "e.dispatchEvent(new Event('input', {bubbles: true}));"
                    "e.dispatchEvent(new Event('change', {bubbles: true}));"
                    "var ctrl = document.querySelector(\"[ng-controller='ctrSpSadt']\");"
                    "var s = ctrl && window.angular && angular.element(ctrl).scope();"
                    "if (s && s.objVO0481 && campo) {"
                    "  s.objVO0481[campo] = iso;"
                    "  if (campo === 'dtpedido' && typeof s.verificarData === 'function') {"
                    "    try { s.verificarData(); } catch(err) {}"
                    "  }"
                    "  try { s.$apply(); } catch(err) {}"
                    "}"
                    "e.dispatchEvent(new Event('blur', {bubbles: true}));",
                    el, iso_esperado, campo_vo,
                )
            except Exception:
                pass
        else:
            # Mock sem Angular: neutraliza onfocus->date e preenche DD/MM/YYYY em texto
            try:
                driver.execute_script(
                    "var e = arguments[0];"
                    "e.onfocus = null;"
                    "e.removeAttribute('onfocus');"
                    "if (e.type === 'date') { e.type = 'text'; }",
                    el,
                )
                _digitar(el, data_ddmmaaaa)
                el.send_keys(Keys.TAB)
            except Exception:
                pass

        ok, dom_v, scope_v = _data_valida_lida()
        if ok:
            scraper.log(
                f"[OP1] {label} = {data_ddmmaaaa} (validado tent={tentativa} dom='{dom_v}' scope='{scope_v or dom_v}' -> BIOS receberá '{data_ddmmaaaa}')",
                job_id=job_id,
            )
            return

        scraper.log(
            f"[OP1] {label}: leitura divergente após tentativa {tentativa}/3 "
            f"(esperado='{data_ddmmaaaa}' / iso='{iso_esperado}', dom='{dom_v}', scope='{scope_v}') — corrigindo",
            level="WARN", job_id=job_id,
        )
        time.sleep(0.3)

    _, dom_final, scope_final = _data_valida_lida()
    if not dom_final and not scope_final:
        _evidencia_falha(driver, scraper, job_id, f"{label} limpa pelo portal (verificarData)")
        raise ValueError(
            f"PermanentError: {label} {data_ddmmaaaa} foi limpa/rejeitada pelo portal "
            f"(verificarData) — use data atual/futura"
        )
    _evidencia_falha(driver, scraper, job_id, f"{label} corrompida: dom='{dom_final}' scope='{scope_final}'")
    raise ValueError(
        f"PermanentError: {label} permaneceu inválida/corrompida após 3 tentativas "
        f"(esperado='{data_ddmmaaaa}', dom='{dom_final}', scope='{scope_final}')"
    )


def _select_por_valor(driver, scraper, job_id, el, valor: str, label: str):
    """Seleciona option pelo value real do Angular, dispara change e confere a seleção."""
    sel = Select(el)
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)
    sel.select_by_value(valor)
    try:
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
            el,
        )
    except Exception:
        pass
    escolhido = sel.first_selected_option
    scraper.log(
        f"Select '{label}' → value={valor} ('{(escolhido.text or '').strip()}')",
        job_id=job_id,
    )


def _aguardar_loading_portal(driver, timeout_seg: float = SHORT_TIMEOUT):
    """Aguarda o spinner #loading do portal CAESAN ocultar (display: none)."""
    try:
        WebDriverWait(driver, timeout_seg).until(
            lambda d: d.execute_script(
                "var l = document.getElementById('loading');"
                "return !l || l.style.display === 'none' || l.offsetParent === null;"
            )
        )
    except Exception:
        pass


def _abrir_form_sadt(driver, scraper, job_id):
    """
    Abre o SP-SADT, aguarda o form Angular (âncora: input ng-model
    objVO0481.dtpedido) e aguarda o carregamento inicial das listas do BIOS
    (lstCarSolicitacao, lstTipoAtendimento, procTuss, objVO0306).
    """
    for tentativa in range(1, 4):
        driver.switch_to.default_content()
        driver.get(URL_SP_SADT)
        try:
            WebDriverWait(driver, SHORT_TIMEOUT).until(
                lambda d: d.execute_script("return document.readyState") in ("complete", "interactive")
            )
        except Exception:
            pass
        try:
            WebDriverWait(driver, LONG_TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, X_DATA_SOLICITACAO_NG))
            )
            # Se o controller Angular ctrSpSadt estiver ativo, aguarda as listas iniciais do BIOS carregarem
            def _listas_iniciais_prontas(d):
                st = _ler_scope_sadt(d)
                if not st.get("disponivel"):
                    return True  # mock estático
                return (
                    (st.get("carater_opts_len") or 0) > 0
                    and (st.get("tipoatend_opts_len") or 0) > 0
                    and (st.get("proctuss_opts_len") or 0) > 0
                    and bool(st.get("codpessoa"))
                )
            try:
                WebDriverWait(driver, DEFAULT_TIMEOUT).until(_listas_iniciais_prontas)
            except Exception:
                pass
            _aguardar_loading_portal(driver, SHORT_TIMEOUT)
            return
        except Exception:
            pass
        url = ""
        try:
            url = driver.current_url or ""
        except Exception:
            pass
        scraper.log(
            f"[OP1] SP-SADT: form não carregou (tentativa {tentativa}/3) url={url}",
            level="WARN", job_id=job_id
        )
        _evidencia_falha(driver, scraper, job_id, f"SP-SADT: form não carregou (tentativa {tentativa}/3)")
        if "login" in url.lower():
            raise ValueError("Sessão CAESAN perdida ao abrir SP-SADT (redirecionado ao login)")
        time.sleep(2)
    raise ValueError(f"Timeout: form SP-SADT não carregou após 3 tentativas (âncora: {X_DATA_SOLICITACAO_NG})")


def _selecionar_profissional(driver, scraper, job_id, nome_profissional):
    """
    Modal de profissional (bootstrap, sem iframe): abre via ng-click
    ModalProfissional(), digita o nome + ENTER e clica o botão de busca
    (ng-click buscaProfissionais()), clica a 1ª linha com conteúdo e confere a
    seleção pelo campo objVO0406.nome (preenchido pelo portal). 3 tentativas.
    """
    for tentativa in range(1, 4):
        _clicar_com_retry(driver, scraper, job_id, [X_BOTAO_PROFISSIONAL_NG, X_BOTAO_PROFISSIONAL], "button", "botão do profissional")
        time.sleep(1)

        inp = _localizar(driver, scraper, job_id, [X_INPUT_BUSCA_PROF_NG], "text", "input de busca do profissional")
        inp.clear()
        inp.send_keys(nome_profissional)
        inp.send_keys(Keys.ENTER)

        # Botão de busca do modal (determinístico; ENTER já disparou acima)
        try:
            btn_busca = driver.find_element(By.XPATH, X_BOTAO_BUSCA_PROF_NG)
            btn_busca.click()
        except Exception:
            pass

        linhas = []
        try:
            WebDriverWait(driver, DEFAULT_TIMEOUT).until(
                lambda d: [
                    l for l in d.find_elements(By.XPATH, X_LINHA_PROF_MODAL_NG)
                    if (l.text or "").strip()
                ]
            )
            linhas = [
                l for l in driver.find_elements(By.XPATH, X_LINHA_PROF_MODAL_NG)
                if (l.text or "").strip()
            ]
        except Exception:
            pass

        if not linhas:
            scraper.log(f"[OP1] Profissional: sem resultados na busca (tentativa {tentativa}/3)", level="WARN", job_id=job_id)
            continue

        linha = linhas[0]
        try:
            try:
                linha.click()
            except Exception:
                driver.execute_script("arguments[0].click();", linha)
        except Exception:
            # stale (ngRepeat re-renderizou): re-localiza linhas e re-clica
            time.sleep(1)
            linhas2 = [l for l in driver.find_elements(By.XPATH, X_LINHA_PROF_MODAL_NG) if (l.text or "").strip()]
            if not linhas2:
                raise
            linha = linhas2[0]
            try:
                linha.click()
            except Exception:
                driver.execute_script("arguments[0].click();", linha)
        time.sleep(1)

        # Confirmação autoritativa: o portal preenche objVO0406.nome. Se o clique
        # na linha não registrou (bind no botão interno, variação do portal),
        # clica o botão da linha antes de descartar a tentativa.
        def _nome_preenchido(d):
            el = d.find_element(By.XPATH, X_INPUT_PROF_SELEC_NG)
            return (el.get_attribute("value") or "").strip() or False

        nome_ok = None
        try:
            nome_ok = WebDriverWait(driver, SHORT_TIMEOUT).until(_nome_preenchido)
        except Exception:
            try:
                btn_linha = linha.find_element(By.XPATH, ".//button")
                btn_linha.click()
                time.sleep(1)
                nome_ok = WebDriverWait(driver, SHORT_TIMEOUT).until(_nome_preenchido)
            except Exception:
                pass

        if nome_ok:
            vo406 = _ler_scope_sadt(driver).get("profissional_vo406") or {}
            scraper.log(f"[OP1] Profissional selecionado: {nome_ok} | vo406={vo406}", job_id=job_id)
            return
        scraper.log(f"[OP1] Profissional: campo objVO0406.nome não preenchido após clique (tentativa {tentativa}/3)", level="WARN", job_id=job_id)

    raise ValueError(
        f"PermanentError: Profissional não localizado/selecionável no portal CAESAN: {nome_profissional}"
    )


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


def _descobrir_numero_na_consulta(
    driver, scraper, job_id, carteira: str, cod_prestador, data_solicitacao: str = ""
) -> Optional[str]:
    """
    Último recurso pós-Gravar sem nº direto no #alerta:
    1) Consulta determinística via webservice BIOS (`coddao: 544` = Solicitações Pendentes e
       `coddao: 560` = Solicitações Autorizadas) filtrando por `codassociado == carteira` e
       priorizando `dtpedido == data_solicitacao` (retorna `sequencia` exata da guia criada).
    2) Fallback visual em NOVA ABA (`/solicitacoes-pendentes/` e `/consultar-solicitacoes/`)
       aguardando o spinner `#loading` ocultar antes de ler a tabela.
    """
    from config.constants import URL_CONSULTA_SOLICITACOES

    # 1. Consulta direta ao BIOS (coddao 544 Pendentes + 560 Autorizadas)
    if cod_prestador:
        for coddao_lista, nome_lista in (
            (BIOS_WS_CODDAO_PENDENTES, "Pendentes/544"),
            (BIOS_WS_CODDAO_AUTORIZADAS, "Autorizadas/560"),
        ):
            try:
                payload = json.dumps({
                    "coddao": coddao_lista,
                    "parametros": [BIOS_WS_CHAVE, str(cod_prestador)],
                }).encode("utf-8")
                req = urllib.request.Request(
                    BIOS_WS_URL,
                    data=payload,
                    headers={"Content-Type": "application/json; charset=utf-8"},
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    dados = json.loads(resp.read().decode("utf-8", errors="replace"))
                conteudo = dados.get("conteudo") or []
                itens = conteudo[0] if (conteudo and isinstance(conteudo[0], list)) else (
                    conteudo if isinstance(conteudo, list) else []
                )
                candidatos_mesmo_dia = []
                candidatos_carteira = []
                for item in itens:
                    if not isinstance(item, dict):
                        continue
                    assoc = str(item.get("codassociado") or "").strip()
                    seq = item.get("sequencia")
                    if assoc != str(carteira).strip() or not seq:
                        continue
                    try:
                        seq_int = int(str(seq).strip())
                    except ValueError:
                        continue
                    dt_item = str(item.get("dtpedido") or item.get("dtsolicitacao") or "").strip()
                    if data_solicitacao and dt_item == data_solicitacao:
                        candidatos_mesmo_dia.append(seq_int)
                    candidatos_carteira.append(seq_int)
                escolhido = (
                    max(candidatos_mesmo_dia) if candidatos_mesmo_dia
                    else (max(candidatos_carteira) if candidatos_carteira else None)
                )
                if escolhido:
                    scraper.log(
                        f"[OP1] Nº da guia descoberto no BIOS ({nome_lista}, carteira={carteira}): {escolhido}",
                        job_id=job_id,
                    )
                    return str(escolhido)
            except Exception as e:
                scraper.log(f"[OP1] Aviso ao consultar BIOS {nome_lista} p/ carteira {carteira}: {e}", level="WARN", job_id=job_id)

    # 2. Fallback em nova aba do navegador (preservando o estado do SP-SADT na aba original)
    aba_original = None
    nova_aba = None
    try:
        aba_original = driver.current_window_handle
        handles_antes = set(driver.window_handles)
        driver.execute_script("window.open('about:blank', '_blank');")
        novos = set(driver.window_handles) - handles_antes
        if novos:
            nova_aba = list(novos)[0]
            driver.switch_to.window(nova_aba)
        for url_alvo in ("https://www.caesan.com.br/solicitacoes-pendentes/", URL_CONSULTA_SOLICITACOES):
            try:
                driver.get(url_alvo)
                WebDriverWait(driver, DEFAULT_TIMEOUT).until(
                    lambda d: (d.execute_script("return document.readyState") or "") == "complete"
                )
                _aguardar_loading_portal(driver, DEFAULT_TIMEOUT)
                time.sleep(2)
                linhas = driver.find_elements(By.XPATH, "//table//tbody//tr")
                for linha in linhas:
                    try:
                        texto = (linha.text or "").strip()
                    except Exception:
                        continue
                    if not texto or carteira not in texto:
                        continue
                    for m in re.finditer(RESULT_NUMERO_REGEX, texto):
                        cand = m.group(1)
                        if cand != carteira:
                            scraper.log(
                                f"[OP1] Nº descoberto em {url_alvo} (nova aba, carteira {carteira}): {cand}",
                                job_id=job_id,
                            )
                            return cand
            except Exception:
                continue
        scraper.log(
            f"[OP1] Nº não localizado nas consultas (BIOS 544/560 e páginas) para a carteira {carteira}",
            level="WARN", job_id=job_id,
        )
    except Exception as e:
        scraper.log(f"[OP1] Falha ao consultar solicitações em nova aba p/ descobrir nº: {e}", level="WARN", job_id=job_id)
    finally:
        if nova_aba:
            try:
                driver.close()
            except Exception:
                pass
        if aba_original:
            try:
                driver.switch_to.window(aba_original)
            except Exception:
                pass
    return None


def _capturar_numero_solicitacao(driver, scraper, job_id, carteira: str = "", cod_prestador=None) -> Optional[str]:
    """
    Captura o nº da guia no modal de confirmação #alerta (xpath oficial do
    cliente: 'Guia gravada com sucesso - número da guia: 892706'), com
    fallbacks best-effort.
    """
    try:
        def _texto_alerta(d):
            try:
                el = d.find_element(By.XPATH, X_RESULT_NUMERO_OFICIAL)
                if el.is_displayed() and (el.text or "").strip():
                    return (el.text or "").strip()
            except Exception:
                pass
            # nº pode vir no título do modal (h4.modal-title) ou em outro <p>
            try:
                for xp in ('//*[@id="alerta"]//h4[contains(@class,"modal-title")]',
                           '//*[@id="alerta"]//p',
                           '//*[@id="alerta"]'):
                    for el2 in d.find_elements(By.XPATH, xp):
                        t = (el2.text or "").strip()
                        if t and re.search(RESULT_NUMERO_REGEX, t):
                            return t
            except Exception:
                pass
            return False
        texto = WebDriverWait(driver, 15).until(_texto_alerta)
        m = re.search(RESULT_NUMERO_REGEX, texto)
        if m:
            scraper.log(f"[OP1] Nº da solicitação capturado (#alerta): {m.group(1)}", job_id=job_id)
            return m.group(1)
    except Exception:
        pass
    driver.switch_to.default_content()

    time.sleep(1)

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

    scraper.log(
        "[OP1] Nº da solicitação não veio no texto do modal #alerta — "
        "verificando XHR do BIOS e listagem de solicitações (544/560)",
        level="WARN", job_id=job_id
    )
    _evidencia_falha(driver, scraper, job_id, "modal #alerta sem nº explícito pós-Gravar (conferindo XHR/544)")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# OP1 — Autorização SP-SADT no portal CAESAN
# ─────────────────────────────────────────────────────────────────────────────

def run(scraper: "BaseScraper", job_data: dict) -> dict:
    """Retorna dict no contrato do hub: guia/nº solicitação + status Pendente."""
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
    if tabela not in TABELA_VALUE:
        raise ValueError(
            f"Parâmetro 'tabela' inválido/ausente: '{tabela}'. Use '00' (Tabela Interna/Especiais) ou '22' (Procedimentos/Convencionais)."
        )
    if not carteira:
        raise ValueError("Parâmetro obrigatório ausente: carteira")
    if not codigo:
        raise ValueError("Parâmetro obrigatório ausente: codigo (código do procedimento)")
    if not nome_profissional:
        raise ValueError("Parâmetro obrigatório ausente: nome_profissional")

    secretaria = str(job_data.get("secretaria") or SECRETARIA_PADRAO).strip()

    scraper.log(
        f"[OP1] SP-SADT: carteira={carteira} prof={nome_profissional} tabela={tabela} "
        f"codigo={codigo} qtde={quantidade} data_solic={data_solicitacao} data_atend={data_atendimento}",
        job_id=job_id
    )

    # 1. Abrir formulário SP-SADT e aguardar o form Angular + listas iniciais do BIOS
    _abrir_form_sadt(driver, scraper, job_id)
    st_init = _ler_scope_sadt(driver)
    scraper.log(
        f"[OP1][PASSO 1/12] Formulário SP-SADT e listas BIOS carregados "
        f"(angular={st_init.get('disponivel')}, carater_opts={st_init.get('carater_opts_len')}, "
        f"tipoatend_opts={st_init.get('tipoatend_opts_len')}, procTuss_opts={st_init.get('proctuss_opts_len')}, "
        f"codprestador={st_init.get('codprestador') or st_init.get('codpessoa')})",
        job_id=job_id,
    )

    try:
        return _executar_fluxo_form(scraper, driver, job_data, job_id, carteira, codigo, quantidade,
                                    nome_profissional, secretaria, justificativa, tabela,
                                    data_solicitacao, data_atendimento)
    except ValueError:
        raise
    except Exception as e:
        # Qualquer exceção inesperada deixa evidência (screenshot/HTML) p/ diagnóstico
        _evidencia_falha(driver, scraper, job_id, f"exceção inesperada: {str(e)[:200]}")
        raise


def _executar_fluxo_form(scraper, driver, job_data, job_id, carteira, codigo, quantidade,
                         nome_profissional, secretaria, justificativa, tabela,
                         data_solicitacao, data_atendimento):
    modo = bool(job_data.get("modo_validacao"))
    try:
        iso_solicitacao = datetime.strptime(data_solicitacao, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        iso_solicitacao = data_solicitacao
    try:
        iso_atendimento = datetime.strptime(data_atendimento, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        iso_atendimento = data_atendimento

    # 2. Data de solicitação (no portal real: type='date' + ISO YYYY-MM-DD p/ gravarGuia converter p/ DD/MM/YYYY)
    el = _localizar(driver, scraper, job_id, [X_DATA_SOLICITACAO_NG, '/html/body/div[5]/div[2]/div[2]/form/div[1]/input'], "text", "data_solicitacao")
    _preencher_data_texto(driver, el, data_solicitacao, scraper, job_id, "data_solicitacao", ng_model="objVO0481.dtpedido")
    time.sleep(PAUSA_PASSO_FORM)
    scraper.log(f"[OP1][PASSO 2/12] Data do Pedido validada ({data_solicitacao})", job_id=job_id)
    _step_validacao(driver, scraper, job_id, modo, "apos_data_solicitacao")

    # 3. Caráter da solicitação
    el = _localizar(driver, scraper, job_id, [X_SELECT_CARATER_NG, X_SELECT_CARATER], "select", "caráter da solicitação")
    _select_por_valor(driver, scraper, job_id, el, VAL_CARATER_ELETIVO, "Caráter (Eletivo)")
    time.sleep(PAUSA_PASSO_FORM)
    scraper.log("[OP1][PASSO 3/12] Caráter da Solicitação validado (1 - Eletivo)", job_id=job_id)

    # 4. Carteira: digita + TAB (dispara buscacarencia coddao 551 no portal)
    el = _localizar(driver, scraper, job_id, [X_INPUT_CARTEIRA_NG, X_INPUT_CARTEIRA], "text", "carteira")
    _digitar(el, carteira)
    el.send_keys(Keys.TAB)
    time.sleep(PAUSA_PASSO_FORM)

    # 5. Demais selects de atendimento (com pausa curta entre cada seleção)
    el = _localizar(driver, scraper, job_id, [X_SELECT_TIPO_ATEND_NG, X_SELECT_TIPO_ATENDIMENTO], "select", "tipo de atendimento")
    _select_por_valor(driver, scraper, job_id, el, VAL_TIPO_ATEND_OUTRAS_TERAPIAS, "Tipo de atendimento (Outras Terapias)")
    time.sleep(0.4)
    el = _localizar(driver, scraper, job_id, [X_SELECT_TIPO_CONSULTA_NG, X_SELECT_TIPO_CONSULTA], "select", "tipo de consulta")
    _select_por_valor(driver, scraper, job_id, el, VAL_TIPO_CONSULTA, "Tipo de consulta")
    time.sleep(0.4)
    el = _localizar(driver, scraper, job_id, [X_SELECT_RECEM_NATO_NG, X_SELECT_RECEM_NATO], "select", "recém-nato")
    _select_por_valor(driver, scraper, job_id, el, VAL_RECEM_NATO, "Recém-nato")
    time.sleep(0.4)
    el = _localizar(driver, scraper, job_id, [X_SELECT_IND_ACIDENTE_NG, X_SELECT_INDICACAO_ACIDENTE], "select", "indicação de acidente")
    _select_por_valor(driver, scraper, job_id, el, VAL_INDICACAO_ACIDENTE, "Indicação de acidente")
    time.sleep(PAUSA_PASSO_FORM)
    scraper.log("[OP1][PASSO 5/12] Selects de atendimento/consulta/RN/acidente validados", job_id=job_id)

    # Confere a validação do beneficiário (buscacarencia coddao 551)
    try:
        def _benef_ok(d):
            try:
                st_b = _ler_scope_sadt(d)
                if st_b.get("disponivel") and st_b.get("usuario_benef"):
                    return f"OK:{st_b.get('usuario_benef')}"
                cart_el = d.find_element(By.XPATH, X_INPUT_CARTEIRA_NG)
                cls = cart_el.get_attribute("class") or ""
                val = (cart_el.get_attribute("value") or "").strip()
                if "user-error" in cls or ("user-" in cls and "user-success" not in cls and val == ""):
                    return "ERRO"
                if "user-success" in cls or val:
                    return "OK:" + (val or "")
                benef = d.find_element(By.XPATH, X_INPUT_NOMEBENEF_NG)
                if "ng-not-empty" in (benef.get_attribute("class") or ""):
                    return "OK:benef"
                return False
            except Exception:
                return False
        sinal = WebDriverWait(driver, 15).until(_benef_ok)
        if str(sinal).startswith("ERRO"):
            _evidencia_falha(driver, scraper, job_id, "carteira rejeitada pelo portal (user-error)")
            raise ValueError(
                f"PermanentError: carteira {carteira} rejeitada pelo portal — conferir número/validade"
            )
        scraper.log(f"[OP1][PASSO 4/12] Beneficiário e carteira validados pelo portal ({sinal})", job_id=job_id)
    except ValueError:
        raise
    except Exception:
        scraper.log(
            "[OP1] Beneficiário: sem sinal definitivo de validação em 15s — seguindo "
            "(o botão Gravar só habilita com beneficiário válido)",
            level="WARN", job_id=job_id
        )
    _step_validacao(driver, scraper, job_id, modo, "apos_selects_e_carteira")
    _logar_estado_campos(driver, scraper, job_id, modo, "pós-carteira/selects")

    # 6. Profissional (modal de busca com botão buscaProfissionais())
    _selecionar_profissional(driver, scraper, job_id, nome_profissional)
    time.sleep(PAUSA_PASSO_FORM)
    st_prof = _ler_scope_sadt(driver)
    scraper.log(
        f"[OP1][PASSO 6/12] Profissional validado no form (nome='{st_prof.get('nommedico') or _ler_campo(driver, X_INPUT_PROF_SELEC_NG)}', "
        f"codprofissional={st_prof.get('codprofissional')})",
        job_id=job_id,
    )
    _step_validacao(driver, scraper, job_id, modo, "apos_profissional")

    # 7. Data do atendimento + Secretaria
    el = driver.find_element(By.XPATH, X_DATA_ATENDIMENTO_NG) if driver.find_elements(By.XPATH, X_DATA_ATENDIMENTO_NG) else _localizar(
        driver, scraper, job_id, [X_DATA_ATENDIMENTO_NG, '/html/body/div[5]/div[2]/div[2]/form/div[10]/input'], "text", "data_atendimento"
    )
    _preencher_data_texto(driver, el, data_atendimento, scraper, job_id, "data_atendimento", ng_model="objVO0481.dtprovproc")
    # O portal/mock LIMPA data inválida/passada no blur (verificarData): confere leitura de volta (DD/MM/YYYY ou ISO YYYY-MM-DD)
    lida = _ler_campo(driver, X_DATA_ATENDIMENTO_NG)
    if not lida or not (
        (re.fullmatch(REGEX_DATA_DDMMAAAA, lida) and lida == data_atendimento)
        or (re.fullmatch(REGEX_DATA_ISO, lida) and lida == iso_atendimento)
    ):
        _evidencia_falha(driver, scraper, job_id, f"data_atendimento inválida/limpa pelo portal: '{lida}'")
        raise ValueError(
            f"PermanentError: data_atendimento {data_atendimento} foi limpa/rejeitada pelo portal "
            f"(verificarData, lido='{lida}') — use data atual/futura"
        )

    el = _localizar(driver, scraper, job_id, [X_INPUT_SECRETARIA_NG, X_INPUT_SECRETARIA], "text", "secretaria")
    _digitar(el, secretaria)
    el.send_keys(Keys.TAB)
    time.sleep(PAUSA_PASSO_FORM)
    scraper.log(
        f"[OP1][PASSO 7/12] Data Provável do Procedimento ({data_atendimento}, dom='{lida}') e Secretária ('{secretaria}') validadas",
        job_id=job_id,
    )

    # 8. Justificativa (scroll até o elemento)
    el = _localizar(driver, scraper, job_id, [X_TEXTAREA_JUSTIFICATIVA_NG, X_TEXTAREA_JUSTIFICATIVA], "textarea", "justificativa")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
    time.sleep(0.5)
    texto_just = justificativa or "Autorização de sessões de terapia conforme plano terapêutico."
    _digitar(el, texto_just)
    el.send_keys(Keys.TAB)
    time.sleep(PAUSA_PASSO_FORM)
    scraper.log(f"[OP1][PASSO 8/12] Justificativa Clínica preenchida e validada ({len(texto_just)} chars)", job_id=job_id)
    _step_validacao(driver, scraper, job_id, modo, "apos_justificativa")

    # 9. Preenchimento passo a passo do Procedimento: Tabela -> Código TUSS (lookup coddao 526) -> Quantidade
    el_tab = _localizar(driver, scraper, job_id, [X_SELECT_TABELA_NG, X_SELECT_TABELA], "select", "tabela")
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el_tab)
    except Exception:
        pass
    time.sleep(0.5)
    _select_por_valor(driver, scraper, job_id, el_tab, TABELA_VALUE[tabela], f"Tabela ({tabela})")
    time.sleep(1.0)
    st_tab = _ler_scope_sadt(driver)
    vo482_tab = (st_tab.get("item_edicao_vo482") or {}) if st_tab.get("disponivel") else {}
    scraper.log(
        f"[OP1][PASSO 9a/12] Tabela do procedimento selecionada e validada (tabela='{tabela}', scope_vo482.codtabela='{vo482_tab.get('codtabela')}')",
        job_id=job_id,
    )

    el_cod = _localizar(driver, scraper, job_id, [X_INPUT_CODIGO_NG, X_INPUT_CODIGO], "text", "codigo")
    _digitar(el_cod, codigo)
    # TAB único dispara ng-blur="buscarProcedimentoTussCodigo()" (coddao 526 no BIOS)
    el_cod.send_keys(Keys.TAB)

    t0_tuss = time.time()
    reinvocou_tuss = False

    def _proc_tuss_resolvido(d):
        nonlocal reinvocou_tuss
        st = _ler_scope_sadt(d)
        if not st.get("disponivel"):
            return "SEM_SCOPE"
        vo482 = st.get("item_edicao_vo482") or {}
        if st.get("alertaProcedimento") or st.get("alertabloqueio") or vo482.get("procbloqueado"):
            return f"BLOQUEADO:alertaProcedimento={st.get('alertaProcedimento')},alertabloqueio={st.get('alertabloqueio')},procbloqueado={vo482.get('procbloqueado')}"
        if vo482.get("descricao"):
            return f"OK:{vo482.get('descricao')}"
        # Se após 2.5s ainda não resolveu descricao e não há alerta, dispara buscarProcedimentoTussCodigo() via scope 1 vez
        if (time.time() - t0_tuss) > 2.5 and not reinvocou_tuss:
            reinvocou_tuss = True
            try:
                d.execute_script(
                    "var el = document.querySelector(\"[ng-controller='ctrSpSadt']\");"
                    "var s = el && window.angular && angular.element(el).scope();"
                    "if (s && s.objVO0482) {"
                    "  s.objVO0482.codtabela = arguments[0];"
                    "  s.objVO0482.codprocedimento = arguments[1];"
                    "  if (typeof s.buscarProcedimentoTussCodigo === 'function') { s.buscarProcedimentoTussCodigo(); }"
                    "  try { s.$apply(); } catch(e) {}"
                    "}",
                    tabela, codigo,
                )
            except Exception:
                pass
        return False

    try:
        res_tuss = WebDriverWait(driver, ITEM_DESCRICAO_TIMEOUT).until(_proc_tuss_resolvido)
        if str(res_tuss).startswith("BLOQUEADO:"):
            motivo_bloq = str(res_tuss).split(":", 1)[1]
            _evidencia_falha(driver, scraper, job_id, f"procedimento {codigo} bloqueado/inválido: {motivo_bloq}")
            raise ValueError(
                f"PermanentError: procedimento TUSS {codigo} (tabela {tabela}) rejeitado/bloqueado pelo portal: {motivo_bloq}"
            )
        if str(res_tuss).startswith("OK:"):
            scraper.log(f"[OP1][PASSO 9b/12] Código TUSS {codigo} validado no BIOS (coddao 526): {res_tuss}", job_id=job_id)
    except ValueError:
        raise
    except Exception:
        st_timeout = _ler_scope_sadt(driver)
        vo482_t = st_timeout.get("item_edicao_vo482") or {}
        if st_timeout.get("alertaProcedimento") or st_timeout.get("alertabloqueio") or vo482_t.get("procbloqueado"):
            motivo_bloq = f"alertaProcedimento={st_timeout.get('alertaProcedimento')},alertabloqueio={st_timeout.get('alertabloqueio')}"
            _evidencia_falha(driver, scraper, job_id, f"procedimento {codigo} bloqueado/inválido: {motivo_bloq}")
            raise ValueError(
                f"PermanentError: procedimento TUSS {codigo} (tabela {tabela}) rejeitado/bloqueado pelo portal: {motivo_bloq}"
            )
        scraper.log(
            f"[OP1] Aviso: objVO0482.descricao não populou em {ITEM_DESCRICAO_TIMEOUT}s (vo482={vo482_t}) — conferindo botão Incluir",
            level="WARN", job_id=job_id,
        )
    time.sleep(1.0)

    qtde_int_str = str(int(float(quantidade)))
    el_qtd = _localizar(driver, scraper, job_id, [X_INPUT_QUANTIDADE_NG, X_INPUT_QUANTIDADE], "text", "quantidade")
    _digitar(el_qtd, qtde_int_str)
    el_qtd.send_keys(Keys.TAB)
    try:
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
            el_qtd,
        )
    except Exception:
        pass

    st_vo482_pre = _ler_scope_sadt(driver)
    vo482_pre_inc = (st_vo482_pre.get("item_edicao_vo482") or {}) if st_vo482_pre.get("disponivel") else {
        "codtabela": _ler_campo(driver, X_SELECT_TABELA_NG),
        "codprocedimento": _ler_campo(driver, X_INPUT_CODIGO_NG),
        "qtdsolicitada": _ler_campo(driver, X_INPUT_QUANTIDADE_NG),
    }
    scraper.log(
        f"[OP1][PASSO 9c/12] Campos do procedimento preenchidos e validados antes de Incluir: vo482={vo482_pre_inc} "
        f"(aguardando pausa visual de {PAUSA_PRE_INCLUIR_ITEM}s antes de clicar em Adicionar Procedimento)",
        job_id=job_id,
    )
    time.sleep(PAUSA_PRE_INCLUIR_ITEM)

    _step_validacao(driver, scraper, job_id, modo, "apos_item_campos")
    _logar_estado_campos(driver, scraper, job_id, modo, "pré-Incluir")

    # 10. Clicar em 'Adicionar Procedimento' (ng-disabled até tabela+codigo+descricao+qtde válidos e !procbloqueado)
    btn = _localizar(driver, scraper, job_id, [X_BOTAO_INCLUIR_NG, X_BOTAO_INCLUIR], "button", "botão Incluir")
    try:
        WebDriverWait(driver, SHORT_TIMEOUT).until(
            lambda d: btn.is_enabled() and btn.is_displayed() and not (btn.get_attribute("disabled") or "")
        )
    except Exception:
        st_inc = _ler_scope_sadt(driver)
        _dump_form_estrutura(driver, scraper, job_id, f"botão Incluir permaneceu desabilitado (scope={st_inc})")
        _evidencia_falha(driver, scraper, job_id, "botão Incluir desabilitado (item inválido?)")
        raise ValueError(
            f"PermanentError: botão Incluir desabilitado — item (tabela={tabela}/código={codigo}/qtde={quantidade}) "
            f"rejeitado pelo portal (vo482={st_inc.get('item_edicao_vo482')}, "
            f"alertaProc={st_inc.get('alertaProcedimento')}, bloqueio={st_inc.get('alertabloqueio')})"
        )
    try:
        btn.click()
    except Exception:
        driver.execute_script("arguments[0].click();", btn)

    # Pós-condição obrigatória: o item PRECISA entrar em objVO0481.procedimentos (ou tabela DOM no mock sem scope)
    def _item_incluido_na_lista(d):
        st = _ler_scope_sadt(d)
        if st.get("disponivel"):
            if (st.get("procedimentos_count") or 0) >= 1:
                return f"SCOPE:{st.get('procedimentos_count')}"
            return False
        # Fallback p/ mock sem AngularJS real: checa __estado().itemIncluido ou linhas na tabela
        try:
            est_mock = d.execute_script("return (window.__estado && window.__estado()) || null;")
            if isinstance(est_mock, dict) and est_mock.get("itemIncluido"):
                return "MOCK:itemIncluido"
        except Exception:
            pass
        linhas_proc = d.find_elements(By.XPATH, X_LINHAS_PROCEDIMENTOS_TABELA)
        return f"DOM:{len(linhas_proc)}" if linhas_proc else False

    try:
        sinal_inc = WebDriverWait(driver, ITEM_INCLUIR_TIMEOUT).until(_item_incluido_na_lista)
    except Exception:
        # Fallback: invoca adicionarProcedimento() via scope caso o clique tenha sido perdido em re-render
        try:
            driver.execute_script(
                "var el = document.querySelector(\"[ng-controller='ctrSpSadt']\");"
                "var s = el && window.angular && angular.element(el).scope();"
                "if (s && typeof s.adicionarProcedimento === 'function') { s.adicionarProcedimento(); s.$apply(); }"
            )
            sinal_inc = WebDriverWait(driver, SHORT_TIMEOUT).until(_item_incluido_na_lista)
        except Exception:
            st_falha = _ler_scope_sadt(driver)
            _evidencia_falha(driver, scraper, job_id, "adicionarProcedimento não populou objVO0481.procedimentos")
            raise ValueError(
                f"PermanentError: procedimento {codigo} não entrou na lista objVO0481.procedimentos após clicar Incluir "
                f"(procedimentos_count={st_falha.get('procedimentos_count')}, vo482={st_falha.get('item_edicao_vo482')})"
            )

    st_pos_inc = _ler_scope_sadt(driver)
    procs_incluidos = st_pos_inc.get("procedimentos") if st_pos_inc.get("disponivel") else []
    scraper.log(
        f"[OP1][PASSO 10/12] Procedimento incluído na tabela 'Procedimento(s) TUSS Solicitado(s)' ({sinal_inc}): "
        f"itens={procs_incluidos} (nota: o portal limpa os inputs de edição após transferir o item para a tabela; "
        f"aguardando pausa de {PAUSA_POS_INCLUIR_ITEM}s antes de enviar o anexo)",
        job_id=job_id,
    )
    time.sleep(PAUSA_POS_INCLUIR_ITEM)
    _step_validacao(driver, scraper, job_id, modo, "apos_incluir")

    # 11. Documento (anexo base64 em objVO0481.lstarquivos) + pausa pós-anexo
    caminho_doc_param = (
        job_data.get("caminho_doc") or job_data.get("caminho") or job_data.get("anexo_RM") or ""
    )
    if caminho_doc_param:
        local_doc = _resolve_documento(caminho_doc_param, carteira, scraper, job_id)
        inp = _localizar(driver, scraper, job_id, [X_INPUT_CAMINHO_DOC_NG, X_INPUT_CAMINHO_DOC], "file", "input de documento")
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", inp)
        except Exception:
            pass
        time.sleep(0.5)
        inp.send_keys(local_doc)
        scraper.log(f"[OP1] Documento enviado ao input file: {os.path.basename(local_doc)}", job_id=job_id)
        try:
            driver.execute_script(
                "var i = arguments[0];"
                "i.dispatchEvent(new Event('input', {bubbles: true}));"
                "i.dispatchEvent(new Event('change', {bubbles: true}));",
                inp,
            )
        except Exception:
            pass

        def _anexo_no_model(d):
            try:
                st_a = _ler_scope_sadt(d)
                if not st_a.get("disponivel"):
                    return True
                arqs = st_a.get("lstarquivos_meta") or []
                if len(arqs) >= 1 and (arqs[0].get("base64_len") or 0) > 100:
                    return arqs[0]
                return False
            except Exception:
                return False

        try:
            meta_arq = WebDriverWait(driver, 12).until(_anexo_no_model)
            scraper.log(
                f"[OP1][PASSO 11/12] Anexo processado e convertido para base64 no model: {meta_arq} "
                f"(aguardando pausa de {PAUSA_POS_ANEXO}s antes do Gravar)",
                job_id=job_id,
            )
        except Exception:
            _dump_form_estrutura(driver, scraper, job_id, "anexo não chegou ao model Angular (lstarquivos vazio)")
            _evidencia_falha(driver, scraper, job_id, "anexo não processado pelo portal (lstarquivos=[]) — gravar seria rejeitado")
            raise ValueError(
                "PermanentError: o anexo não foi processado pelo portal (model objVO0481.lstarquivos "
                "permaneceu vazio/sem base64 após a seleção) — o portal recusaria o Gravar sem o documento"
            )
        time.sleep(PAUSA_POS_ANEXO)
        _step_validacao(driver, scraper, job_id, modo, "apos_anexo")
    else:
        scraper.log("[OP1][PASSO 11/12] Sem documento informado — gravando solicitação sem anexo", level="WARN", job_id=job_id)

    # 12. Gravar (ng-disabled form.$invalid) — pré-checagem + Gate Pré-Gravar + pausa pré-Gravar
    def _form_valido(d):
        try:
            invalidos = _campos_invalidos_angular(d)
            return True if not invalidos else invalidos
        except Exception:
            return None

    def _espera_validacao(d):
        r = _form_valido(d)
        return r if r else True
    resultado_validacao = WebDriverWait(driver, DEFAULT_TIMEOUT).until(_espera_validacao)
    if resultado_validacao is not True:
        invalidos = resultado_validacao or []
        _dump_form_estrutura(driver, scraper, job_id, f"form inválido pré-Gravar: {invalidos}")
        _evidencia_falha(driver, scraper, job_id, f"form inválido pré-Gravar: {invalidos}")
        raise ValueError(
            f"PermanentError: form permaneceu inválido pré-Gravar — campos Angular inválidos: {invalidos}"
        )
    _step_validacao(driver, scraper, job_id, modo, "pre_gravar_form_valido")
    _logar_estado_campos(driver, scraper, job_id, modo, "pré-Gravar")

    # Dump completo e estruturado do scope + Gate Pré-Gravar (fail-fast)
    st_pre = _ler_scope_sadt(driver)
    scraper.log(f"[OP1] Scope pré-Gravar (estruturado): {st_pre}", job_id=job_id)

    if st_pre.get("disponivel"):
        erros_gate = []
        dt_ped_s = str(st_pre.get("dtpedido") or "").strip()
        dt_prv_s = str(st_pre.get("dtprovproc") or "").strip()
        if dt_ped_s not in (iso_solicitacao, data_solicitacao):
            erros_gate.append(f"dtpedido inválido/corrompido no scope ('{dt_ped_s}' != '{iso_solicitacao}')")
        if dt_prv_s not in (iso_atendimento, data_atendimento):
            erros_gate.append(f"dtprovproc inválido/corrompido no scope ('{dt_prv_s}' != '{iso_atendimento}')")
        if (st_pre.get("procedimentos_count") or 0) < 1:
            erros_gate.append("objVO0481.procedimentos está vazio (nenhum item incluído)")
        vo406_pre = st_pre.get("profissional_vo406") or {}
        if not (vo406_pre.get("nome") or st_pre.get("nommedico") or _ler_campo(driver, X_INPUT_PROF_SELEC_NG)):
            erros_gate.append(f"profissional não preenchido em objVO0406 ({vo406_pre})")
        if not str(st_pre.get("codassociado") or "").strip():
            erros_gate.append("codassociado vazio no scope")
        if caminho_doc_param and (st_pre.get("lstarquivos_count") or 0) < 1:
            erros_gate.append("lstarquivos vazio no scope apesar de caminho_doc informado")
        if erros_gate:
            _evidencia_falha(driver, scraper, job_id, f"Gate pré-Gravar reprovado: {erros_gate}")
            raise ValueError(f"PermanentError: Gate pré-Gravar reprovado — {'; '.join(erros_gate)}")
    else:
        dt_ped_dom = _ler_campo(driver, X_DATA_SOLICITACAO_NG)
        dt_prv_dom = _ler_campo(driver, X_DATA_ATENDIMENTO_NG)
        if dt_ped_dom not in (data_solicitacao, iso_solicitacao):
            raise ValueError(f"PermanentError: Gate pré-Gravar (DOM) — dtpedido inválido: '{dt_ped_dom}' (esperado '{data_solicitacao}')")
        if dt_prv_dom not in (data_atendimento, iso_atendimento):
            raise ValueError(f"PermanentError: Gate pré-Gravar (DOM) — dtprovproc inválido: '{dt_prv_dom}' (esperado '{data_atendimento}')")

    # Pausa antes do clique no Gravar:
    # - Em modo_validacao: 60s (ou pausa_pre_gravar_segundos quando informado).
    # - Em modo normal: PAUSA_PRE_GRAVAR_PADRAO (2.0s) para garantir estabilização pós-anexo antes do submit.
    _pausa_bruta = job_data.get("pausa_pre_gravar_segundos")
    if _pausa_bruta is None:
        pausa_pre = 60.0 if modo else PAUSA_PRE_GRAVAR_PADRAO
    else:
        try:
            pausa_pre = max(0.0, float(_pausa_bruta))
        except (TypeError, ValueError):
            pausa_pre = 60.0 if modo else PAUSA_PRE_GRAVAR_PADRAO
    if pausa_pre > 0:
        if modo or pausa_pre >= 5.0:
            scraper.log(
                f"[OP1][VALIDAÇÃO] PAUSA de {pausa_pre:.0f}s antes do Gravar — confira o preenchimento "
                f"na tela; o clique só ocorre ao final da pausa",
                job_id=job_id,
            )
            _step_validacao(driver, scraper, job_id, True, "pausa_pre_gravar_inicio", pausa=0.0)
            time.sleep(pausa_pre)
            _step_validacao(driver, scraper, job_id, True, "pausa_pre_gravar_fim", pausa=0.0)
        else:
            time.sleep(pausa_pre)

    try:
        driver.execute_script(
            "var b = document.querySelector('button.cookies-save');"
            "if (b && b.offsetParent !== null) { b.click(); }"
        )
    except Exception:
        pass

    xpath_operacao = str(job_data.get("xpath_botao_gravar") or "").strip()
    candidatos_gravar = ([xpath_operacao] if xpath_operacao else []) + [X_BOTAO_GRAVAR_NG, X_BOTAO_GRAVAR]

    btn = None
    for tentativa in range(1, 4):
        btn = _localizar(driver, scraper, job_id, candidatos_gravar, "button", "botão Gravar")
        ng_click = (btn.get_attribute("ng-click") or "").strip()
        if ng_click == "gravarGuia()":
            break
        if xpath_operacao:
            scraper.log(f"[OP1] Gravar: xpath da operação resolveu ng-click='{ng_click or '(sem ng-click)'}'", level="WARN", job_id=job_id)
            break
        scraper.log(
            f"[OP1] Gravar: elemento com ng-click inesperado '{ng_click}' — re-localizando ({tentativa}/3)",
            level="WARN", job_id=job_id,
        )
        btn = None
        time.sleep(1)
    if btn is None:
        _evidencia_falha(driver, scraper, job_id, "botão Gravar não localizado com ng-click=gravarGuia()")
        raise ValueError("PermanentError: não foi possível localizar o botão Gravar (ng-click=gravarGuia())")
    if xpath_operacao:
        scraper.log(f"[OP1] Gravar: usando xpath da operação ({xpath_operacao})", job_id=job_id)

    # Interceptor de XHR ANTES do clique:
    # 1) Garante que no coddao 483 `dtpedido` e `dtprovproc` nunca saiam corrompidos ('26//2/04/1')
    # 2) Captura URL/status/request(sem base64 gigante)/response para auditoria e extração do nº.
    try:
        driver.execute_script(
            "window.__xhrLog = [];"
            "window.__op1Datas = {dtpedido: arguments[0], dtprovproc: arguments[1]};"
            "var ox = XMLHttpRequest.prototype.open;"
            "XMLHttpRequest.prototype.open = function(m, u){ this.__url = u; return ox.apply(this, arguments); };"
            "var os = XMLHttpRequest.prototype.send;"
            "XMLHttpRequest.prototype.send = function(b){"
            "  var x = this;"
            "  var bodyToSend = b;"
            "  try {"
            "    var raw = (typeof b === 'string') ? b : String(b || '');"
            "    try {"
            "      var obj = JSON.parse(raw);"
            "      if (obj && obj.coddao === 483 && obj.conteudo) {"
            "        var reBr = /^\\d{2}\\/\\d{2}\\/\\d{4}$/;"
            "        if (!reBr.test(String(obj.conteudo.dtpedido || ''))) {"
            "          obj.conteudo.dtpedido = window.__op1Datas.dtpedido;"
            "        }"
            "        if (!reBr.test(String(obj.conteudo.dtprovproc || ''))) {"
            "          obj.conteudo.dtprovproc = window.__op1Datas.dtprovproc;"
            "        }"
            "        bodyToSend = JSON.stringify(obj);"
            "      }"
            "      var logObj = JSON.parse(typeof bodyToSend === 'string' ? bodyToSend : raw);"
            "      if (logObj && logObj.conteudo && Array.isArray(logObj.conteudo.lstarquivos)) {"
            "        logObj.conteudo.lstarquivos = logObj.conteudo.lstarquivos.map(function(a){"
            "          if (!a || typeof a !== 'object') return a;"
            "          var c = Object.assign({}, a);"
            "          if (typeof c.base64 === 'string') c.base64 = '<base64 len=' + c.base64.length + '>';"
            "          return c;"
            "        });"
            "      }"
            "      x.__body = JSON.stringify(logObj);"
            "    } catch(e2) {"
            "      x.__body = raw.replace(/\"base64\"\\s*:\\s*\"[^\"]*\"/g, '\"base64\":\"<stripped>\"').slice(0, 12000);"
            "    }"
            "  } catch (e) {}"
            "  x.addEventListener('load', function(){"
            "    try { window.__xhrLog.push({url: String(x.__url), status: x.status,"
            "      req: String(x.__body || ''),"
            "      resp: String(x.responseText || '').slice(0, 12000)}); } catch (e) {}"
            "  });"
            "  return os.call(this, bodyToSend);"
            "};",
            data_solicitacao, data_atendimento,
        )
    except Exception as e:
        scraper.log(f"[OP1] Interceptor XHR não instalado: {e}", level="WARN", job_id=job_id)

    # Envelopa scope.gravarGuia: normaliza dtpedido/dtprovproc em ISO YYYY-MM-DD antes de
    # `orig.apply` (pois ctrSpSadt.js fatia substring(8,10)+'/'+substring(5,7)+'/'+substring(0,4))
    try:
        driver.execute_script(
            "var el = document.querySelector(\"[ng-controller='ctrSpSadt']\");"
            "var s = el && window.angular && angular.element(el).scope();"
            "var isoPed = arguments[0], isoPrv = arguments[1];"
            "if (s && typeof s.gravarGuia === 'function') {"
            "  window.__gravarCalls = 0; window.__gravarErro = null;"
            "  var orig = s.gravarGuia;"
            "  s.gravarGuia = function(){"
            "    window.__gravarCalls++;"
            "    try {"
            "      if (s.objVO0481) {"
            "        s.objVO0481.dtpedido = isoPed;"
            "        s.objVO0481.dtprovproc = isoPrv;"
            "      }"
            "      return orig.apply(this, arguments);"
            "    }"
            "    catch (e) { window.__gravarErro = String(e && e.stack || e); throw e; }"
            "  };"
            "  s.$apply();"
            "}",
            iso_solicitacao, iso_atendimento,
        )
    except Exception as e:
        scraper.log(f"[OP1] Wrap do gravarGuia não instalado: {e}", level="WARN", job_id=job_id)

    def _gravar_habilitado(d):
        try:
            return btn.is_enabled() and btn.is_displayed() and not (btn.get_attribute("disabled") or "")
        except Exception:
            return False
    try:
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(_gravar_habilitado)
        scraper.log("[OP1][PASSO 12/12] Gravar: botão HABILITADO (disabled removido pelo portal)", job_id=job_id)
    except Exception:
        _dump_form_estrutura(driver, scraper, job_id, "botão Gravar permaneceu desabilitado (form.$invalid)")
        _evidencia_falha(driver, scraper, job_id, "botão Gravar desabilitado — formulário incompleto")
        raise ValueError("PermanentError: botão Gravar desabilitado — formulário permaneceu inválido para o portal")

    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});"
        "arguments[0].click();",
        btn,
    )
    scraper.log("[OP1] Botão Gravar acionado (clique DOM no próprio elemento)", job_id=job_id)

    # Aguarda o envio do coddao 483 concluir (spinner #loading ocultar)
    time.sleep(1.5)
    _aguardar_loading_portal(driver, DEFAULT_TIMEOUT)
    time.sleep(1.5)

    scope_pos = {}
    try:
        scope_pos = _ler_scope_sadt(driver)
        scraper.log(f"[OP1] Scope pós-Gravar: {scope_pos}", job_id=job_id)
    except Exception as e:
        scraper.log(f"[OP1] Leitura do scope falhou: {e}", level="WARN", job_id=job_id)

    xhr_sucesso = False
    xhr_numero = None
    try:
        xhrs = driver.execute_script("return window.__xhrLog || [];")
        for x in xhrs:
            resp = str(x.get("resp") or "")
            req_limpo = _resumir_req_bios(str(x.get("req") or ""))
            scraper.log(
                f"[OP1] XHR pós-Gravar: status={x.get('status')} url={x.get('url')} "
                f"req={req_limpo[:4000]} resp={resp[:4000]}",
                job_id=job_id,
            )
            if "wsbios" in str(x.get("url") or "") and '"codstatus":200' in resp:
                xhr_sucesso = True
                # Tenta extrair nº do JSON da resposta (conteudo ou codigo > 1000)
                try:
                    resp_json = json.loads(resp)
                    if isinstance(resp_json, dict):
                        cod_resp = resp_json.get("codigo")
                        cont_resp = resp_json.get("conteudo")
                        if isinstance(cod_resp, int) and cod_resp >= 10000:
                            xhr_numero = str(cod_resp)
                        elif cont_resp:
                            m_c = re.search(RESULT_NUMERO_REGEX, json.dumps(cont_resp, ensure_ascii=False))
                            if m_c and m_c.group(1) != carteira:
                                xhr_numero = m_c.group(1)
                except Exception:
                    pass
                if not xhr_numero:
                    m = re.search(RESULT_NUMERO_REGEX, resp)
                    if m and m.group(1) != carteira:
                        xhr_numero = m.group(1)
        if not xhrs:
            scraper.log("[OP1] Nenhum XHR capturado pós-Gravar (gravarGuia não fez requisição?)", level="WARN", job_id=job_id)
    except Exception as e:
        scraper.log(f"[OP1] Leitura do XHR log falhou: {e}", level="WARN", job_id=job_id)

    # Também verifica se scope_pos['alerta'] (mensagem/complemento) trouxe o número da guia
    if not xhr_numero and isinstance(scope_pos.get("alerta"), dict):
        alerta_str = json.dumps(scope_pos.get("alerta"), ensure_ascii=False)
        for m_al in re.finditer(RESULT_NUMERO_REGEX, alerta_str):
            if m_al.group(1) != carteira:
                xhr_numero = m_al.group(1)
                scraper.log(f"[OP1] Nº da solicitação extraído de scope.alerta: {xhr_numero}", job_id=job_id)
                break

    if xhr_sucesso:
        scraper.log(f"[OP1] BIOS confirmou: Solicitação realizada com sucesso (nº do XHR/scope: {xhr_numero})", job_id=job_id)
    try:
        wrap = driver.execute_script(
            "return {calls: window.__gravarCalls || 0, erro: window.__gravarErro || null};"
        )
        scraper.log(f"[OP1] gravarGuia: invocações={wrap.get('calls')} erro={str(wrap.get('erro'))[:400] or 'nenhum'}", job_id=job_id)
    except Exception:
        pass
    _step_validacao(driver, scraper, job_id, modo, "apos_gravar", pausa=3.0)

    time.sleep(1.5)
    form_limpo_pos_clique = not _ler_campo(driver, X_INPUT_CARTEIRA_NG)
    if form_limpo_pos_clique:
        scraper.log(
            "[OP1] Form foi limpo após o clique no Gravar — confirmando emissão da guia "
            "antes de concluir (limparForm disfarçado gravaria nada)",
            level="WARN", job_id=job_id,
        )

    # 13. Pós-Gravar: modal #alertafalha VISÍVEL com mensagem (erro do portal) → PermanentError
    def _falha_visivel(d):
        try:
            el = d.find_element(By.XPATH, X_ALERTA_FALHA)
            return el.is_displayed() and (el.text or "").strip()
        except Exception:
            return False
    try:
        msg_falha = WebDriverWait(driver, 3).until(_falha_visivel)
        _evidencia_falha(driver, scraper, job_id, f"portal recusou o Gravar: {str(msg_falha)[:200]}")
        raise ValueError(f"PermanentError: portal recusou o Gravar — {str(msg_falha)[:300]}")
    except ValueError:
        raise
    except Exception:
        pass

    numero_solicitacao = xhr_numero or _capturar_numero_solicitacao(driver, scraper, job_id)

    # Se o BIOS respondeu 200 mas nem o modal nem o XHR trouxeram o número (apenas
    # em ambiente http/https real, não file:// mock), consulta BIOS 544/560 e nova aba
    if not numero_solicitacao and xhr_sucesso:
        try:
            cur_url = (driver.current_url or "").lower()
            if cur_url.startswith(("http://", "https://")):
                cod_prest = (
                    st_pre.get("codprestador")
                    or st_pre.get("codpessoa")
                    or scope_pos.get("codprestador")
                    or scope_pos.get("codpessoa")
                    or job_data.get("cod_prestador")
                )
                numero_solicitacao = _descobrir_numero_na_consulta(
                    driver, scraper, job_id, carteira, cod_prest, data_solicitacao=data_solicitacao
                )
        except Exception:
            pass

    if form_limpo_pos_clique and not numero_solicitacao and not xhr_sucesso:
        _evidencia_falha(driver, scraper, job_id, "form limpo pós-clique sem nº de guia nem sucesso do BIOS")
        raise ValueError(
            "PermanentError: o formulário foi limpo após o clique no Gravar e não houve "
            "confirmação do BIOS nem nº de guia — nenhuma guia foi gerada"
        )

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
            else ("Solicitação realizada com sucesso (BIOS 200); nº não retornado na resposta — consultar via OP2."
                  if xhr_sucesso
                  else "Solicitação gravada no portal CAESAN; nº não capturado — consultar via OP2.")
        ),
    }
    scraper.log(f"[OP1] Resultado: {resultado['status']} | nº={numero_solicitacao}", job_id=job_id)
    return resultado
