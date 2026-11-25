# OP0 — Login ABA CLMF (API do painel novo + SSO) — Integrador 101, tipo agendamento, servidores de agendamento 9005/9006

**Status: IMPLEMENTADO e validado E2E no portal real (2026-11-21, credenciais do banco user 1).**

> **Modelo NOVO (2026-11-21):** o login visual Selenium (`emailAba`/`senhaAba`/`btnEntrarAba`) foi **aposentado pelo portal**. O painel novo (app.) substituiu a autenticação e o sistema antigo (PHP, `_ajax/*`) vive agora na **raiz** do domínio. Referência da implementação: `C:\dev\clmf_hub_basic\worker\Worker\clmf_scraper.py`.

## Modelo de dois domínios (`config/constants.py`)

| Constante | Valor | Papel |
|---|---|---|
| `APP_URL` | `https://app.abalarissamartinsferreira.com.br` | Painel NOVO — autenticação (`/api/auth/login`) e emissão SSO (`/api/sso/emitir`) |
| `BASE_URL` | `https://abalarissamartinsferreira.com.br` | Sistema ANTIGO (PHP, raiz) — todas as URLs de AJAX/telas das OPs (`_ajax/Schedule.ajax.php`, `pagamentos/home`, `schedule/*`, `prontuarios/*`) |
| `SSO_DESTINO` | env `CLMF_SSO_DESTINO` (default `/prontuarios/home/status/1`) | Tela do sistema antigo que o SSO abre — **precisa estar no MENU da conta** (a API recusa com 422 destino fora do menu) |

## Fluxo implementado (`core/scraper.py` → `AbaClmfScraper.login`; OP0 é wrapper fino)

HTTP puro via `requests` — **sem Selenium** no login:

1. **Sonda de sessão** (`is_logged_in`): `GET {BASE_URL}{SSO_DESTINO}` sem seguir redirect — 200 sem redirect = sessão viva (reusa e pula o login). *O `GET /` na raiz NÃO serve de sonda: redireciona para `/_sso/emitir.php` mesmo autenticado (medido no portal real).*
2. **Autenticar no painel novo**: `POST {APP_URL}/api/auth/login` com `{"email", "senha"}` → `{token, usuario}` (Bearer). 401 = credenciais recusadas.
3. **Emitir token SSO de uso único**: `POST {APP_URL}/api/sso/emitir` com `{"destino": SSO_DESTINO}` + `Authorization: Bearer <token>` → `{url, token}`. 422 = destino fora do menu da conta (ajustar `CLMF_SSO_DESTINO`).
4. **Trocar o token por sessão PHP**: POST form `{"token": ...}` na url retornada (como o painel faz em `js/app.js` → `irParaOAntigo`) → sistema antigo cria a sessão (`PHPSESSID`).
5. **Cookies**: apenas os do domínio antigo (`PHPSESSID`, `gf_login`, `userView`) alimentam `scraper.session` (OPs HTTP) e são injetados no driver via CDP (`Network.setCookie`) para OPs que navegam.
6. Sessão do painel em `requests.Session()` **separada** — cookies do app. não poluem o jar das OPs.

## Decisões de implementação

- **`process_job` decide login pela sonda HTTP** (não por contagem de cookies); sessão é reusada quando a sonda passa.
- **Sync Selenium→session removido** — cookies velhos do driver sobrescreviam o PHPSESSID fresco do SSO.
- **Purga anti cross-talk de `config`** no import top-level do scraper (job anterior de outro integrador no mesmo processo deixa `config` DELE em `sys.modules`; idem `1-bradesco`).
- **Timeouts**: `AJAX_TIMEOUT=60` (POSTs de login/SSO e AJAX das OPs), `LOGIN_PROBE_TIMEOUT=10` (sonda).
- **Falha → `LOGIN_REJEITADO`** com diagnóstico (401 credenciais / 422 destino fora do menu / erro de rede) — fatal, sem retry (contrato do circuit breaker de login do dispatcher, cooldown 15 min).

## Retorno da OP0 (`op/op0_login.py`)

`{status: "success", message, cookies: [<nomes>]}` — apenas os **nomes** dos cookies, nunca valores.
