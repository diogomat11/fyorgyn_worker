# Fluxo Passo a Passo: Rotina 0 (Login) - Unimed Anápolis

**Objetivo:** Autenticar um Scraper no portal da Unimed Anápolis e validar a presença de uma sessão ativa para realização das demais rotinas.

## 1. Carregamento de Credenciais
- O sistema obtém as credenciais (`usuario` e `senha_criptografada`) do banco de dados na tabela `convenios` pelo ID do convênio (2).
- A senha é descriptografada usando a chave `FERNET_SECRET` no ambiente.

## 2. Acesso ao Portal SGUCard
- **Ação:** O Web Scraper acessa a URL `https://sgucard.unimedanapolis.com.br/cmagnet/Login.do`.
- **Ação:** O bot aguarda o carregamento dos elementos de formulário.

## 3. Preenchimento de Dados
- **Usuário:** Preenche o campo de input com ID `login` com a credencial de acesso.
- **Senha:** Preenche o campo de input com ID `passwordTemp` com a senha lida.
- **Ação:** Clica no botão de ID `Button_DoLogin`.

## 4. Validação de Sessão
- O bot aguarda cerca de 2 segundos.
- **Limpeza de Popups:** Executam-se métodos estáticos (`close_alert_if_present` e `close_popup_window`) para matar qualquer aviso Javascript ou janela não solicitada que pule após o login.
- **Check de Sucesso:**
  1. Verifica a presença do Ícone do Menu Principal Home (`centro_61` no CSS). Se presente, **Sucesso**.
  2. Casa não encontre, verifica a presença do Menu Autorizador (`MENU_ITEM_2` pelo ID). Se presente, **Sucesso**.
  3. No Fallback de detecção: Avalia a URL atual. Se o site *NÃO* contiver "Login.do" na barra de endereços, foi redirecionado e é indicativo de **Sucesso**.
- As exceções no bloco de validação geram **Falha Crítica**, retentam logar futuramente, mas naquele momento a sessão é dada como inativa.

## Regras de Negócio e Tratativa de Erros
- Reuso: A sessão aberta ao final do login com sucesso é atrelada a uma instância paralela persistente de Driver gerenciada pelo `SeleniumManager`. Retentativas e navegações em outras rotinas (op1, op2 e op3) re-utilizam esta aba ativa para não ser necessário dar reload no fluxo de autenticação repetidas vezes e bloquear IP.
