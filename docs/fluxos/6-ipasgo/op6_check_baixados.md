# Fluxo Funcional e Arquitetura: Rotina 6 (Check Baixados / Extração de Lote) - IPASGO

**Objetivo:** Consumir a API de lotes do IPASGO (LoadDetalhes) para extrair os detalhes de faturamento (guias baixadas) de um lote específico e gravá-los no banco de dados local.

## 1. Princípios de Design
- **Abordagem Híbrida (UI Bootstrap + API):** A rotina aproveita a sessão do navegador mantida pelo Selenium (OP0). Ela navega até a tela de faturamento para inicializar o contexto de segurança/Angular no backend do IPASGO e, em seguida, sequestra os cookies para realizar chamadas HTTP super-rápidas via `WebPlanClient`.
- **Extração Paginada:** O robô identifica a quantidade de páginas do lote dinamicamente na primeira requisição e realiza o loop subsequente para as páginas restantes.

## 2. Passo a Passo Funcional

### 2.1 Preparação e Inicialização
- **Validação de Parâmetros:** Requer obrigatoriamente a presença da variável `loteId` e opcionalmente `codigoPrestador`.
- **Navegação Bootstrap:**
  - Redireciona a aba do navegador diretamente para `https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/FaturamentoAtendimentos`.
  - Aguarda 3 segundos para a estabilização de cookies e renderização da página.

### 2.2 Consulta Paginada de Detalhes do Lote
- **Injeção do Client HTTP:** Inicializa o `WebPlanClient` repassando o objeto driver (Selenium) para clonar os cookies.
- **Requisição Base (Página 0):** 
  - Realiza o `POST` chamando o endpoint de carregamento de detalhes.
  - O JSON de resposta é enviado ao parser `extract_total_pages` para obter a quantidade total de abas da paginação.
  - O conteúdo da página inicial é parseado extraindo os itens com foco em `{ detalheId, dataRealizacao, Guia, StatusConferencia, ValorProcedimento, CodigoBeneficiario, loteId }`.

### 2.3 Varredura Restante (Looping)
- Baseado em `total_pages > 1`, o script itera da `Página 1` até a última página extraindo e anexando todos os registros na lista em memória (`all_items`).

### 2.4 Processamento de Resultados (Sem Acesso ao Banco Público)
- O script apenas acumula todos os registros extraídos em uma lista em memória (`all_items`) de forma 100% stateless, sem realizar interações diretas com as tabelas de faturamento no banco de dados local.
- As atualizações de status, gravações de lotes e acionamentos de conciliação são delegados ao Hub Backend, que executa essa lógica ao processar o webhook de retorno.

### 2.5 Tear-Down
- A operação retorna a lista completa de itens extraídos (`all_items`) no JSON de resultados, que é enviado pelo dispatcher para o webhook do backend.
