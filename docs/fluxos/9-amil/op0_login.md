# OP0 — Login AMIL (credenciado.amil.com.br) — ID Integrador 9, tipo convenio, servidores genéricos 9000-9004

**Status: IMPLEMENTADO e validado E2E no portal real (2026-11-20, headless UC com UA real — 140/140 pedidos coletados).**

## Contrato real do portal (diagnóstico Chrome DevTools 2026-11-20)

| Achado | Impacto na OP |
|---|---|
| **Akamai reprova UA `HeadlessChrome` na edge** (403 "Acesso Negado" antes mesmo do form) | `selenium_manager` injeta UA real quando headless; **preferir `SGUCARD_HEADLESS=false`** |
| **Overlay do OneTrust INTERCEPTA o clique no Entrar** (submit não dispara com banner aberto) | Banner é aceito ANTES de preencher (Selenium click com fallback JS) |
| **Sessão salva: `/login` redireciona direto para `/home`, form NUNCA aparece** (`temForm=false`) | Poll "form OU URL sai de /login" (sem corrida — checagem instantânea dava falso LOGIN_REJEITADO) |
| **Tokens em `localStorage['acesso-info']`** (não em keys com nome 'token'/'session') | Extração primária em `core/session_extractor.py` |
| IDs do form: `login-usuario`, `login-senha`; botão submit dentro de `as-login form fieldset` | Constantes em `config/constants.py` |

## Fluxo implementado (`op/op0_login.py`)

1. `driver.get(LOGIN_URL)` → **poll** até form visível OU URL sair de `/login` (timeout LONG).
2. URL fora de `/login` → **sessão já ativa**: pula credenciais, vai direto ao resumo.
3. Form visível → aceitar OneTrust (`onetrust-accept-btn-handler`, fallback JS) → aguardar 1s.
4. Preencher `login-usuario` / `login-senha` (clear + send_keys).
5. Clicar Entrar (xpath do fieldset, fallback JS em `as-login form fieldset button`).
6. Esperar URL sair de `/login` (LONG) + estabilização (readyState 2× com sleep 3s).
7. Erro visível no `as-login` → `LoginFailedError("LOGIN_REJEITADO: <msg>")` — **fatal** (sem retry; circuit-breaker de login do dispatcher, 15 min).
8. Resumo MASCARADO em `result_data`: `login_ok`, `codigo_usuario`, cookies relevantes (nomes), `autorizacao_presente`, `x_session_presente`, `access_token_prefixo` (8 chars + `...`), `sessao_valida`. **Nunca persistir token/cookie completo.**
9. `driver.last_login = username` (dono da sessão no pool `(id_convenio, user_id)`).

## Onde vivem os tokens (para as demais OPs)

`localStorage['acesso-info']` (JSON):
- `tokenInfo.accessToken` → header `authorization: Bearer <token>` — **rotaciona a cada ~30 min** (`expiresIn: 1800`; o SPA reescreve a chave no refresh) ⇒ as OPs re-leem o storage ANTES DE CADA requisição;
- `sessionToken` → header `x-session` (JWT; payload traz `codigoCredenciadoAmil`, `refreshToken`, `nextRefreshAt`);
- `credenciadoInfo.codigo` → header `x-user` (ex. `67628788`).

Login real do SPA: `POST /credenciadomedico/acesso/login` — body `{"contexto":"amil","username":"<login>","password":"<senha>"}`, accept `application/vnd.amil.credenciado.medico.acesso.v1+json`.

## Riscos e plano B

- **Akamai reprovar mesmo com UA real**: rodar headful (`SGUCARD_HEADLESS=false`) — headful validado no DevTools. O 403-HTML "Acesso Negado" na API vira diagnóstico explícito na OP1.
- **Form nunca aparece com URL presa em `/login`**: OP0 levanta `LOGIN_REJEITADO` com a dica de Akamai quando o `page_source` contém "Acesso Negado".
