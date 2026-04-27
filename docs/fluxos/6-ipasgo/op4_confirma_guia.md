# Fluxo Funcional e Arquitetura: Rotina 4 (Confirma Guia / Execução) - IPASGO

**Objetivo:** Executar e confirmar o atendimento (baixa da guia) do Ipasgo, definindo quantidade de sessões realizadas e enviando para faturamento.

## 1. Princípios de Design (Padrão Sênior/PO)
- **Fluxo Sincronizado:** Toda a etapa de Navegação, Limpeza de Filtros e Busca (Etapas 1 a 6.5) é **idêntica estruturalmente à Rotina 5**.
- **Idempotência de Execução:** A rotina avalia visualmente se o botão de execução está acinzentado (`grayscale`) antes de interagir, evitando retrabalho em guias já finalizadas.
- **Processamento Parcial:** É capaz de marcar dinamicamente "X" sessões do modal, não apenas "todas de uma vez".

## 2. Passo a Passo Funcional (Estado Atual)

### 2.1 Preparação e Navegação
- **Validação:** Recebe `numero_guia`, `sessoes_realizadas` (padrão 1) e `data_execucao`.
- **Acesso ao Facplan & Localizar Procedimentos:** Mesmo fluxo robusto do OP5, que lida com Iframes de notificações e âncoras Angular.
- **Busca:** Input e `.clear()` de guias/datas e clique no botão de pesquisar (Etapas 6.1 a 6.5).

### 2.2 Validação de Tabela e Elegibilidade
- Verifica ausência de guia pelo Knockout `data-bind="visible: !possuiProcedimentos() && pesquisaEfetuada()"`.
- Valida o card da guia preenchida no Dom via `data-bind="text: NumeroGuiaOperadora"`.

### 2.3 Acionamento do Modal de Execução
- Localiza o ícone de ação (Detalhar/Executar) usando um XPath estrito `//*[@id="localizarprocedimentos"]/.../i[2]`.
- **Validação de Status Analógico:** Caso o atributo `style` do elemento contenha `grayscale(1)`, o robô registra status **totalmente_executada** e aborta com sucesso (todas as sessões já foram confirmadas ou não há sessões pendentes).
- Caso liberado, despacha o `.click()` e aguarda estabilização do Angular (desaparecimento dos spinners) para abertura do Modal.

### 2.4 Preenchimento e Confirmação de Sessões
- A lógica é iterativa baseando-se no limite `sessoes_realizadas` (parâmetro fornecido).
- Procura o grid interno do modal: `//*[@id="indentificar-confirmar-procedimentos-modal"]//div[contains(@class, "card-body")]/div[contains(@class, "col-xs-")]`.
- Para cada box mapeado ativo (até o limite estabelecido):
  - Verifica se a sessão já está confirmada ignorando se não houver o texto "Não confirmado".
  - Procura e clica no botão de confirmação: `button[@data-bind="visible: HabilitadoConfirmacao"]`.
  - Habilita e limpa o input da carteirinha (`//*[@id="numeroDaCarteiraConfirmacao"]`), enviando o número da `carteira`.
  - Aguarda a notificação do sistema Noty (Angular Toaster) via `//span[@class="noty_text"]` para validar a mensagem de sucesso.
  - Se sucesso, incrementa o contador e fecha o Noty. Se erro, levanta exceção de `PermanentError`.
- Por fim, localiza e clica no botão "Fechar" ou `data-dismiss="modal"` para sair do painel.
  
### 2.5 Tear-Down e Retorno
- Após iterar as sessões, o modal é fechado através do botão "Fechar" (ou botão padrão de `data-dismiss`).
- O log informa a quantidade de sessões executadas com sucesso no lote.
- O Worker retorna `{sucesso: True, sessoes_realizadas_aplicadas: N, numero_guia: '...'}` para o Dispatcher.

## 3. Integração com Milestones (Em Breve)
OP4 compartilhará do **Marco 2** (Refresh de Carga no Painel) para evitar timeouts da UI "Localizar Procedimento", garantindo que falhas de load isoladas não retrocedam toda a jornada ao OP0 (Login).
