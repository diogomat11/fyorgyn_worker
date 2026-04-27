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

### 2.4 Persistência de Dados (Upsert)
- O script realiza uma iteração unitária (`for item in all_items`) sobre os registros para atualizar o banco de dados via SQLAlchemy (`scraper.db`).
- **Lógica de Match:** Busca na tabela `FaturamentoLote` se o registro já existe pela chave `detalheId`.
- **Update (Se existir):** Atualiza as chaves: `DataRealizacao`, `Guia`, `StatusConferencia`, `ValorProcedimento`, `CodigoBeneficiario` e `loteId`.
- **Insert (Se novo):** Insere um novo objeto de `FaturamentoLote` na base de dados.
- Realiza um `.commit()` massivo para garantir transação atômica. Se houver falha de integridade, executa `.rollback()` e levanta erro crítico.

### 2.5 Tear-Down
- A operação retorna uma lista vazia `[]` em sucesso, pois a sua obrigação era popular/sincronizar o banco de dados diretamente sem necessidade de devolução para o dispatcher processar tabelas paralelas.
