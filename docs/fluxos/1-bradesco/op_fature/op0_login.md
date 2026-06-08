# OP0 - Login no portal Faturamento (Faturi / Orizon)

## Objetivo
Autenticação do prestador no portal de Faturamento da Orizon (Faturi) para consultar guias.

## Portal
- **URL Inicial:** `https://www.orizon.com.br/acesso-restrito.html`
- **Link do Botão:** Acesso via botão "Faturi" (`name="Faturi"`) que redireciona para a tela de autenticação centralizada (Keycloak).

## Credenciais
- Armazenadas em `user_convenios` (colunas `login` e `senha_criptografada`).
- Criptografia: Fernet (via `security_utils.py`).
- Carregadas dinamicamente de acordo com o `user_id` e `id_convenio = 1` do job.

## Fluxo Detalhado
1. Navegar para a página restrita da Orizon.
2. Clicar no botão **Faturi** (`name="Faturi"`) e aguardar redirecionamento para o formulário.
3. Preencher o campo de usuário (`id="username"`) com o login descriptografado.
4. Preencher o campo de senha (`id="password"`) com a senha descriptografada.
5. Clicar no botão **Entrar/Acessar** (`id="kc-login"`).
6. Aguardar 3 segundos para carregamento da página interna.
7. **Tratar Modais/Notificações Iniciais:**
   * O portal costuma exibir avisos flutuantes pós-login (modal com `id="mensagemImg"`).
   * O script executa um ciclo de verificação (máximo de 5 ciclos):
     * Aguarda 5 segundos.
     * Verifica via injeção de JavaScript se `mensagemImg` está visível.
     * Se visível: Executa scroll e clica via JS no botão de fechar (`id="botaoMensagemInicialModalPrestador"`). Caso não encontre, tenta classes de fechar padrão (`.close`, `.btn-close`).
     * Se não estiver visível após dois ciclos, prossegue.

## Retorno
- `[{"status": "success", "message": "Login Faturamento OK"}]` (Login bem-sucedido e sessão ativa).

## Erros Tratados
| Cenário | Comportamento |
|---------|---------------|
| Botão Faturi indisponível | Falha por timeout na seleção do botão (retenta). |
| Modal trava o clique | Tentativa de clique via JavaScript direto no DOM para ignorar sobreposições. |
| Credenciais inválidas | O portal exibe alerta e o script falha na detecção da página interna (retenta). |

## Nota sobre Sessões Simultâneas
O portal Orizon (Bradesco) não permite sessões simultâneas concorrentes com o mesmo login. Caso ocorra uma tentativa de login duplo concomitante, a sessão anterior pode ser derrubada ou o acesso ser bloqueado. 
Para mitigar isso, os jobs OP1 devem preferencialmente rodar com a flag de afinidade estrita (`strict_session_affinity: true`) ativa (padrão para OP1). Isso força o despachante a enfileirar os jobs da mesma credencial no mesmo servidor worker sequencialmente, reaproveitando a sessão ativa no navegador sem realizar novos logins desnecessários.
