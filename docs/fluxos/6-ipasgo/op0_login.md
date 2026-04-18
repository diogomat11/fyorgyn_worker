# Fluxo Passo a Passo: Rotina 0 (Login) - IPASGO

**Objetivo:** Autenticar o Scraper no portal do Ipasgo e preparar a sessão principal (FacPlan).

## 1. Carregamento de Credenciais
- O Scraper resgata usuário e senha diretamente do banco de dados (Convênio ID 6).

## 2. Acesso ao Portal Ipasgo
- Acessa o link raiz do site e escaneia a página atrás de inputs de username e password e o botão Entrar (suporta `iframes`).
- Injeta o usuário e senha e aguarda a autenticação.

## 3. Gestão de Alertas / Sessão
- Após logar, verifica ativamente e fecha qualquer modal temporário/faixa de alerta no Dashboard principal.
- Identifica se o link do sistema legado **FacPlan** está visível na tela e clica nele.
- Quando o popup do FacPlan é disparado em nova aba, o Selenium captura a lista de guias (`driver.switch_to.window`), assumindo controle do novo contexto. Esta aba focada no FacPlan está pronta para uso subseqüente.
