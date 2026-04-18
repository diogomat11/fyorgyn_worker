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
- Localiza o ícone de ação (Engrenagem/Executar) usando `data-bind="click: $root.abrirModalConfirmarProcedimentos"`.
- **Validação de Status Analógico:** Caso o elemento contenha o estilo CSS `grayscale(1)`, o robô registra status **totalmente_executada** e aborta com sucesso (Guia já baixada).
- Caso liberado, despacha o `.click()` e aguarda estabilização do Angular para preenchimento do Modal `.noty_modal`.

### 2.4 Preenchimento de Sessões
- A lógica é iterativa baseando-se no limite `sessoes_realizadas`.
- Procura o grid interno do modal: `//*[@id="indentificar-confirmar-procedimentos-modal"]//div[contains(@class, "card-body")]/div[contains(@class, "col-xs-")]`.
- Para cada box mapeado ativo:
  - Limpa e preenche o input de data atrelado a ele com `data_execucao`.
  - Sinaliza o checkbox `(input[type="checkbox"])` via JS Click simulado `arguments[0].click()`.
  
### 2.5 Confirmação Final e Tear-Down
- Mapeia o botão verde "Confirmar Procedimentos" via `//*[@id="btn_confirmar"]` ou texto semântico.
- Aguarda timeout do Spinner de carregamento assíncrono.
- Fecha Iframes residuais. Retorna objeto contendo a `guia`, cópias/sessoes efetivadas e `sucesso: True`.

## 3. Integração com Milestones (Em Breve)
OP4 compartilhará do **Marco 2** (Refresh de Carga no Painel) para evitar timeouts da UI "Localizar Procedimento", garantindo que falhas de load isoladas não retrocedam toda a jornada ao OP0 (Login).
