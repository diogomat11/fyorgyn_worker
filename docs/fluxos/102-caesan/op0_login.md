# Fluxo Passo a Passo: Rotina 0 (Login) - CAESAN

> **Classificação do Integrador:**
> - **ID Integrador (worker):** `102`
> - **ID Convênio (public):** `16` (CAESAN)
> - **Tipo de Operação:** `convenio`
> - **Tipo de Processamento Padrão:** `local`
> - **Alocação no Worker:** Servidores Genéricos (Portas 9000 a 9004)
> - **Rotina interna:** `op0_login` (não catalogada no `worker.integrador_operacoes`; executada automaticamente quando a sessão expira)

## Objetivo

Autenticar no portal do prestador CAESAN e extrair sessão/cookies/token para as rotinas subsequentes (OP1 e OP2). Executada automaticamente pelo `process_job` do scraper quando a URL corrente não está no domínio `caesan.com.br`.

## Portal

- URL: `https://www.caesan.com.br/login-prestador/`

## Parâmetros (via params do Job)

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `login` | str | Sim* | Usuário do portal (injetado do `user_convenios` pelo hub) |
| `senha_criptografada` | str | Sim* | Senha Fernet (injetada do `user_convenios`) |
| `cod_prestador` | str | Não | Código do prestador (usado pela OP2) |

\* Se ausentes no job, o scraper busca em `public.user_convenios` por `(user_id, id_convenio=16)`.

## Fluxo Detalhado

1. `driver.get(URL_LOGIN)` e aguarda carregamento (fallbacks de xpath além dos mapeados).
2. Mapeia campo usuário `#usuario` — `clear()` + `send_keys(login)`.
3. Mapeia campo senha `#senha1` — `clear()` + `send_keys(senha)`.
4. Clica no botão Acessar (`/html/body/div[5]/div[2]/div[1]/button`).
5. Aguarda redirecionamento (URL sem `login`); permanência na tela de login → erro permanente (credencial inválida).
6. Extrai cookies + tokens (nomes) → `scraper.session_meta` (metadados apenas; **valores sensíveis não vão para logs/result_data** — MODULARITY_GUIDE §4).
7. Fecha alertas/modais residuais.

## Retorno

```json
{ "status": "success", "message": "Login CAESAN efetuado e sessão extraída", "url_final": "...", "cookies_count": 4 }
```

## Erros Tratados

| Cenário | Comportamento |
|---|---|
| Credenciais ausentes (job e user_convenios) | `PermanentError: Credenciais CAESAN ausentes` |
| Login recusado (continua na tela de login) | `PermanentError: Login CAESAN recusado` |
| XPath fora de sincronia | Exceção → retry do `process_job` (3 tentativas com re-login) |
