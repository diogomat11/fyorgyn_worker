# OP0 - Login Polimed/Orizon (Bradesco)

## Objetivo
Autenticação no portal Polimed/Orizon para acesso às funcionalidades de autorização do Bradesco.

## Portal
- **URL:** `https://www.polimed.com.br/autenticadorOrizon/loginAutenticador`

## Credenciais
- Armazenadas em `user_convenios` (colunas `login` e `senha_criptografada`)
- Criptografia: Fernet (via `security_utils.py`)
- Carregadas automaticamente pelo `BradescoScraper._load_credentials()`

## Fluxo
1. Limpar abas residuais do Chrome
2. Navegar para a URL do portal
3. Aguardar carregamento da página
4. Preencher campo usuário (`name="usuario.login"`)
5. Preencher campo senha (`id="senha"`)
6. Clicar botão de login (`xpath="//*[@id='formLogin']/button"`)
7. Aguardar carregamento pós-login
8. Validar ausência de mensagens de erro

## Retorno
- `[]` (lista vazia — login é operação de sessão)

## Erros Tratados
| Cenário | Comportamento |
|---------|---------------|
| Credenciais ausentes | `PermanentError` — não retenta |
| Login inválido | `PermanentError` — detectado via mensagem de erro na tela |
| Timeout carregamento | Exceção padrão — retenta até `max_retries` |

## Reutilização
O `BradescoScraper.process_job()` chama `login()` automaticamente quando:
- É a primeira execução (sessão nova)
- A URL atual indica tela de login
- Uma tentativa anterior falhou (retry)
