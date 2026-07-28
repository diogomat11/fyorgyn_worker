# Fluxo Funcional e Arquitetura: Rotina 7 (Faturamento Facplan) - IPASGO

**Objetivo:** Submeter as contas conferidas ao processo de faturamento final (modificação de status do detalhe) via requisições HTTP (API) da classe `WebPlanClient`, aplicando as baixas individualmente no lote em aberto.

## 1. Princípios de Design
- **Abordagem API Direta:** Substitui a navegação intensiva por UI. Após a ancoragem do Facplan, o robô consome o método `modificar_detalhe` do `WebPlanClient` repassando o novo Status.
- **Retorno Stateless:** Executa o faturamento de forma síncrona no provedor (IPASGO) e retorna os resultados de sucesso e falha no payload de retorno do Job, delegando qualquer persistência no banco de dados para o webhook do Hub Backend.

## 2. Passo a Passo Funcional

### 2.1 Validação de Parâmetros
- A rotina extrai os metadados do `job_data` contendo:
  - `detalheId`: ID interno primário da conta gerado pelo Ipasgo.
  - `status` ou `statusConferencia`: Código que reflete o alvo da transição (ex: Enviar, Faturar, etc).
  - `dataRealizacao`: A data da execução ou fatura.
  - `valorProcedimento`: (Opcional).
- Rejeita com `ValueError` imediatamente se `detalhe_id`, `status` ou `data_realizacao` estiverem ausentes.

### 2.2 Bootstrap (Navegação Âncora)
- Navega via Selenium para a URL mestre do lote: `https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/FaturamentoAtendimentos`.
- Realiza uma espera natural (`sleep(3)`) para garantir que os cookies de sessão de transação do Facplan estejam alinhados ao host (evitando erro 403 Forbidden nas APIs internas).

### 2.3 Comunicação Client HTTP (Faturamento)
- Inicializa a classe `WebPlanClient(driver)` para absorver os cookies estabilizados.
- Aciona `client.modificar_detalhe(...)` injetando o payload final para a FacilInformatica. Esta requisição sela as modificações ou faturamento na conta do lado do Ipasgo.

### 2.4 Processamento de Resultados (Sem Acesso ao Banco Público)
- O script não interage com o banco de dados do Hub. Ele executa as chamadas ao FacPlan em loop para cada um dos itens informados e armazena os sucessos e falhas em memória.
- As atualizações correspondentes de `StatusConferencia` nos faturamentos locais (`FaturamentoLote`) são delegadas ao Hub Backend, que realiza as alterações nas tabelas correspondentes ao receber o webhook de retorno.

### 2.5 Tear-Down
- Ao final, a rotina retorna um dicionário detalhado contendo a contagem total de sucessos e falhas, os identificadores de itens bem-sucedidos (`itens_sucesso`) e a lista detalhada de falhas com os erros específicos (`itens_erro`).
- O dispatcher recebe esse dicionário de resultados e o envia no webhook para que o backend persista os status no banco de dados público.
