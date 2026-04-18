# Fluxo Passo a Passo: Rotina 0 (Login) - Unimed Goiânia

**Objetivo:** Autenticar o Scraper no portal específico da Unimed Goiânia.

## 1. Carregamento de Credenciais
- O script carrega as variáveis de acesso `username` e `password` do banco correspondentes ao convênio ID = 3 (Goiânia).

## 2. Acesso ao Portal SGUCard Goiânia
- **Ação:** O Web Scraper acessa explicitamente a URL `https://sgucard.unimedgoiania.coop.br/cmagnet/Login.do` (link Goiano).
- Aguarda até que o elemento do campo de senha (`passwordTemp` por ID) surja dinamicamente na página num tempo limite de 20s.

## 3. Preenchimento de Dados
- **Usuário:** Preenche o campo de input genérico com ID `login` do cooperado. Em adição limpa a string que porventura esteja pré-armazenada via driver.
- **Senha:** Preenche a input mask `passwordTemp` correspondente a credencial.
- **Acionamento:** O script clica fisicamente (`click()`) no input ID `Button_DoLogin`.
- Após o disparo, estipula-se uma espera dura (`time.sleep(4)`) pra aguardar estabilizar Cookies de Sessão.

## 4. Retorno ao Orquestrador
- Não há validação baseada em presença na Homepage Goiana. Sendo executado o bloco limpo (sem levantar exceções de Selenium), considera a execução como **Success** no Worker local, sinalizando "Login performed".
- Todo e qualquer erro orgânico não-tratado levanta uma exception dura que desativará a fila e agendará re-tentativa pelo Queue Dispatcher.
