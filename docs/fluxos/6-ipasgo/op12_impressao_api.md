# Fluxo Funcional e Arquitetura: Rotina 12 (Impressão de Guias API/Direto) - IPASGO

**Objetivo:** Obter comprobante impresso da guia no portal IPASGO navegando diretamente para a rota do relatório, sem precisar preencher filtros visuais na interface do Facplan.

## 1. Princípios de Design
- **Abordagem Direta (Estilo API):** Ao invés de usar Selenium para simular digitação e cliques na interface de busca de procedimentos (como faz o antigo OP5), a rotina OP12 injeta as credenciais e navega diretamente para a URL do PDF do relatório utilizando os IDs de banco.
- **Fail Fast:** Verifica preventivamente se os parâmetros cruciais (`guia` e `GuiaPrestador`) existem. Caso contrário, interrompe a execução com um `PermanentError`.
- **Prevenção de Interceptações:** Antes de acessar a rota de impressão em si, acessa a tela base para estabilizar tokens Angular e remover modais sobrepostos.

## 2. Passo a Passo Funcional

### 2.1 Preparação
- Extrai do banco o `numero_guia` (identificador interno IPASGO) e, fundamentalmente, a `GuiaPrestador` (capturada previamente pela OP11). Extrai também `numero_copias`.
- Autenticação administrada pelo wrapper principal da OP0 (login).

### 2.2 Bootstrap (Estabilização de Contexto)
- Navega para `https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos`.
- Aguarda carregamento (readyState == complete).
- Invoca o módulo de fechamento robusto de notificações `_close_notification_robust`, garantindo que banners de alerta ou modais bloqueantes "Noty" sejam sumariamente eliminados para evitar travamentos de iframe.

### 2.3 Relatório (Impressão Direta)
- Sem fazer buscas, injeta a URL formatada no navegador:
  `.../Relatorios/NovaViewRelatorioGuiaSPSADT?NumGuiaOperadora={guia}&NumGuiaPrestador={guia_prestador}`
- Aguarda `readyState` completo mais 3 segundos de folga para a total renderização do documento que contém o PDF incorporado ou o layout de impressão.

### 2.4 Ação Nativa do Sistema Operacional
- Injeta um comando CSS global via JavaScript (`document.body.style.zoom='90%'`) para reajustar possíveis quebras de layout em papel A4.
- Dispara `driver.execute_script("window.print();")`.
- **Controle de Spooler:** Realiza pausas estáticas baseadas no número de `copias_impressas` exigidas, garantindo que o driver da impressora local (Kiosk Mode configurado no Chrome) absorva as chamadas.

### 2.5 Tear-Down
- A aba é natural e o processo apenas gera os logs finais de sucesso.
- Retorna o dicionário serializado `{"numero_guia": guia, "copias_impressas": N, "sucesso": True}` para dar baixa no Job pelo Dispatcher.
