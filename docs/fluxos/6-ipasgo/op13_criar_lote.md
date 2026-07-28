# Fluxo Funcional e Arquitetura: Rotina 13 (Criar Lote) - IPASGO

**Objetivo:** Solicitar a geração de um novo Lote de Faturamento de Atendimentos no portal Ipasgo (WebPlan) de forma assíncrona (Fire-and-Forget) e programar o monitoramento de sua criação.

## 1. Princípios de Design
- **Execução Desacoplada (Polling):** A geração do lote no portal Ipasgo é uma operação pesada que pode demorar vários minutos. Em vez de prender o Worker em uma única execução longa, a `OP13` dispara a solicitação na API (`WebPlanClient`) e agenda um job secundário de monitoramento (`13_poll`), liberando o Worker imediatamente.
- **Transição de Estados:** O status do lote é atualizado para `"Criando"` no Hub Backend após o processamento do retorno do webhook.

## 2. Passo a Passo Funcional

### 2.1 Validação e Preparação
- **Parâmetros:** O Job exige os parâmetros `cod_prestador` (código do prestador no Ipasgo) e `data_fim` (data limite para inclusão de guias no lote, formato `DD/MM/YYYY`). Também recebe opcionalmente o `id_lote_interno` (ID da entidade local do lote).
- **Navegação:** O Selenium navega para a rota base de faturamento: `/GuiasTISS/FaturamentoAtendimentos`, fechando alertas nativos do navegador durante o processo.

### 2.2 Chamada de API FacPlan (GerarLote)
- Utiliza a classe `WebPlanClient` (com cookies herdados da sessão do driver) para enviar a requisição `POST` ao endpoint de geração de lote da operadora.
- Se a chamada retornar sucesso ou erro não-fatal, o bot avança para o agendamento do polling.

### 2.3 Processamento de Resultados (Sem Acesso ao Banco Público)
- O script não interage com o banco de dados do Hub. Ele apenas efetua a chamada no portal FacPlan e retorna o payload com o resultado do envio para o dispatcher.

### 2.4 Agendamento de Monitoramento (Delegado ao Backend)
- O worker não agenda o job `13_poll` diretamente no banco do dispatcher.
- Ao receber o webhook de sucesso contendo o resultado da criação, o Hub Backend altera o status local de `LoteConvenio` para `"Criando"` e cria a tarefa de polling no `backend_worker` para monitorar a conclusão.

## 3. Retorno
Retorna um dicionário indicando sucesso na chamada e os metadados do lote:
```json
{
  "status": "success",
  "message": "GerarLote request sent successfully.",
  "id_lote_interno": 45,
  "cod_prestador": "98271",
  "data_fim": "13/07/2026"
}
```
