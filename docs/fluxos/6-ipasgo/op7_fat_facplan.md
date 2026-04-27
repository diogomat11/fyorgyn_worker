# Fluxo Funcional e Arquitetura: Rotina 7 (Faturamento Facplan) - IPASGO

**Objetivo:** Submeter as contas conferidas ao processo de faturamento final (modificação de status do detalhe) via requisições HTTP (API) da classe `WebPlanClient`, aplicando as baixas individualmente no lote em aberto.

## 1. Princípios de Design
- **Abordagem API Direta:** Substitui a navegação intensiva por UI. Após a ancoragem do Facplan, o robô consome o método `modificar_detalhe` do `WebPlanClient` repassando o novo Status.
- **Transação Mista:** Executa o faturamento de forma síncrona no provedor (IPASGO) e, em caso de sucesso (`HTTP 200/Validação`), atualiza imediatamente o reflexo deste status no banco local SQLite/PostgreSQL, evitando descasamento de dados.

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

### 2.4 Persistência e Sincronização Local
- Uma vez validada a etapa de rede, a rotina faz o `Update` no Banco de Dados.
- Tenta recuperar da tabela `FaturamentoLote` o registro que bata exatamente com o `detalheId`.
- Caso exista:
  - Sobrescreve a coluna `StatusConferencia` com o novo código.
  - Formata e sobrescreve a coluna `dataRealizacao` (`dd/mm/yyyy` -> Objeto Date).
  - Aciona `scraper.db.commit()` e informa o sucesso no Log.
- Caso o `detalheId` seja um órfão não rastreado no banco local, emite um Log nível de `WARN`, não interrompendo a rotina pois o faturamento no IPASGO já ocorreu.

### 2.5 Tear-Down
- Se houver falha de banco de dados, dá `rollback()`.
- O worker finaliza retornando array vazio `[]` garantindo que o status do Job transacione para Concluído.
