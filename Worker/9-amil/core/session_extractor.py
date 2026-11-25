"""
Extração de sessão/tokens do SPA AMIL (credenciado.amil.com.br) — decisão D4.

Fonte primária (contrato CONFIRMADO no portal real via DevTools, 2026-11-20):
  localStorage['acesso-info'] (JSON) →
    - tokenInfo.accessToken  → header authorization (Bearer) — ROTACIONA a cada
      ~30 min (expiresIn: 1800; o SPA reescreve a chave no refresh) ⇒ reler do
      storage ANTES DE CADA requisição;
    - sessionToken           → header x-session (JWT; payload traz
      codigoCredenciadoAmil/accessToken/refreshToken);
    - credenciadoInfo.codigo → header x-user (ex. 67628788).

Cascata de fallback (plano §6 — se o SPA mudar o formato da chave):
  (a) varredura JS de localStorage+sessionStorage por chaves/valores contendo
      'token'/'session'/'amil' (case-insensitive);
  (b) valores com formato JWT (3 partes base64url) têm o payload decodificado
      SEM verificação de assinatura; se o payload tiver 'accessToken', este
      vira o Bearer (o x-session É o JWT de sessão);
  (c) x_user: credenciadoInfo.codigo → cookie 'codigoUsuario' → cod_prestador.

Os tokens existem apenas em RUNTIME (storage do driver do pool) e NUNCA são
persistidos completos: a OP0 grava em result_data apenas um resumo mascarado
(prefixo de 8 chars). Funções puras (sem Selenium) são testáveis diretamente.
"""
import base64
import json

# ── Fonte primária: localStorage['acesso-info'] (contrato real do SPA) ──
# Parse defensivo em JS: qualquer desvio de shape devolve None por campo
# (o Python faz fallback para a cascata antiga).
_LER_ACESSO_INFO_JS = """
var raw = null;
try { raw = window.localStorage.getItem('acesso-info'); } catch (e) { raw = null; }
if (!raw) { return {authorization: null, x_session: null, x_user: null}; }
try {
    var info = JSON.parse(raw);
    var t = info.tokenInfo || {};
    var c = info.credenciadoInfo || {};
    return {
        authorization: t.accessToken ? ('Bearer ' + t.accessToken) : null,
        x_session: info.sessionToken || null,
        x_user: c.codigo || null
    };
} catch (e) {
    return {authorization: null, x_session: null, x_user: null};
}
"""

# Script JS da varredura (cascata a): devolve {'<local|session>:<chave>': valor}
_VARREDURA_STORAGES_JS = """
var achados = {};
function varrer(storage, prefixo) {
    try {
        for (var i = 0; i < storage.length; i++) {
            var k = storage.key(i) || '';
            var v = storage.getItem(k) || '';
            var kl = k.toLowerCase();
            if (kl.indexOf('token') >= 0 || kl.indexOf('session') >= 0 || kl.indexOf('amil') >= 0) {
                if (v) { achados[prefixo + k] = v; }
            }
        }
    } catch (e) { /* storage bloqueado — segue */ }
}
varrer(window.localStorage, 'local:');
varrer(window.sessionStorage, 'session:');
return achados;
"""


# ── Funções puras (testáveis sem Selenium) ──

def _limpar_aspas(valor: str) -> str:
    """Remove aspas envolventes de valores serializados no storage
    (JSON.stringify deixa '"valor"' — mesmo tratamento do bradesco)."""
    v = str(valor).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    return v


def _parece_jwt(valor: str) -> bool:
    """Heurística de formato JWT: 3 segmentos separados por '.' não vazios."""
    partes = str(valor).split(".")
    return len(partes) == 3 and all(partes)


def decodificar_jwt_payload(token: str):
    """Decodifica o payload (segmento do meio) de um JWT SEM verificação de
    assinatura. Retorna dict ou None (formato inválido — silencioso)."""
    if not _parece_jwt(token):
        return None
    try:
        seg = str(token).split(".")[1]
        seg += "=" * (-len(seg) % 4)  # padding do base64url
        raw = base64.urlsafe_b64decode(seg.encode("ascii")).decode("utf-8")
        payload = json.loads(raw)
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def selecionar_tokens_de_acesso_info(info: dict) -> dict:
    """Fonte primária (pura): dado o dict de localStorage['acesso-info'],
    devolve os headers da API — {'authorization', 'x_session', 'x_user'}.

    Shape confirmado no portal (2026-11-20):
      tokenInfo.accessToken → Bearer · sessionToken → x-session ·
      credenciadoInfo.codigo → x-user. Qualquer desvio devolve None no campo
      (o chamador faz fallback para a cascata antiga).
    """
    info = info or {}
    out = {"authorization": None, "x_session": None, "x_user": None}
    token_info = info.get("tokenInfo")
    if isinstance(token_info, dict):
        access = token_info.get("accessToken")
        if isinstance(access, str) and access.strip():
            out["authorization"] = f"Bearer {access.strip()}"
    st = info.get("sessionToken")
    if isinstance(st, str) and st.strip():
        out["x_session"] = st.strip()
    cred = info.get("credenciadoInfo")
    if isinstance(cred, dict):
        codigo = cred.get("codigo")
        if codigo is not None and str(codigo).strip():
            out["x_user"] = str(codigo).strip()
    return out


def selecionar_tokens(achados: dict) -> dict:
    """Cascata (b): dado o dict da varredura JS, seleciona os headers da API.

    Prioridade: JWT cujo payload contém 'accessToken' (é o x-session oficial
    do SPA — o Bearer vive DENTRO do payload). Sem accessToken decodificável,
    qualquer JWT válido vira x_session e authorization fica None (o fetch
    segue com cookies; 401/403 → escada de sessão da OP1).

    Retorna {'authorization': 'Bearer ...'|None, 'x_session': ...|None}.
    """
    authorization = None
    x_session = None
    jwts_com_access = []
    jwts_genericos = []
    for valor in (achados or {}).values():
        v = _limpar_aspas(valor)
        if not _parece_jwt(v):
            continue
        payload = decodificar_jwt_payload(v)
        access = (payload or {}).get("accessToken")
        if isinstance(access, str) and access:
            jwts_com_access.append((v, access))
        else:
            jwts_genericos.append(v)
    if jwts_com_access:
        x_session, access = jwts_com_access[0]
        authorization = f"Bearer {access}"
    elif jwts_genericos:
        x_session = jwts_genericos[0]
    return {"authorization": authorization, "x_session": x_session}


# ── Função com driver (execução) ──

def extrair_tokens_pagina(driver) -> dict:
    """Cascata completa no contexto autenticado do SPA AMIL.

    Fonte primária: localStorage['acesso-info'] (tokens ATUAIS — o accessToken
    rotaciona a cada ~30 min, portanto chamar ANTES DE CADA requisição).
    Fallback: varredura de storage + decodificação de JWT (a→b).

    Retorna {'authorization': 'Bearer ...'|None, 'x_session': ...|None,
    'x_user': ...|None} — o dicionário alimenta diretamente os headers do
    fetch JS da OP1 (authorization/x-session/x-user) e o resumo da OP0.
    """
    resultado = {"authorization": None, "x_session": None, "x_user": None}

    # 1. Fonte primária: acesso-info (contrato real do SPA)
    try:
        primario = driver.execute_script(_LER_ACESSO_INFO_JS) or {}
        if isinstance(primario, dict):
            for k, v in primario.items():
                if v:
                    resultado[k] = v
    except Exception:
        pass  # storage bloqueado/JS falhou — cascata antiga decide

    # 2. Fallback: varredura genérica + JWT (plano §6)
    if not resultado["authorization"] and not resultado["x_session"]:
        try:
            achados = driver.execute_script(_VARREDURA_STORAGES_JS) or {}
            resultado.update({k: v for k, v in selecionar_tokens(achados).items() if v})
        except Exception:
            pass

    # 3. x_user de último recurso: cookie codigoUsuario
    if not resultado["x_user"]:
        try:
            for cookie in driver.get_cookies() or []:
                if str(cookie.get("name", "")).lower() == "codigousuario":
                    resultado["x_user"] = str(cookie.get("value") or "").strip() or None
                    break
        except Exception:
            pass
    return resultado
