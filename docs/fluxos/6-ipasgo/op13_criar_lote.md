# Fluxo Funcional e Arquitetura: Rotina 13 (Criar Lote) - IPASGO

**Objetivo:** Solicitar a geração de um novo Lote de Faturamento de Atendimentos no portal Ipasgo (WebPlan) de forma assíncrona (Fire-and-Forget) e programar o monitoramento de sua criação.

## 1. Princípios de Design
- **Execução Desacoplada (Polling):** A geração do lote no portal Ipasgo é uma operação pesada que pode demorar vários minutos. Em vez de prender o Worker em uma única execução longa, a `OP13` dispara a solicitação na API (`WebPlanClient`) e agenda um job secundário de monitoramento (`13_poll`), liberando o Worker imediatamente.
- **Transição de Estados:** O lote local é colocado em estado `"Criando"` até que o processo seja concluído.

## 2. Passo a Passo Funcional

### 2.1 Validação e Preparação
- **Parâmetros:** O Job exige os parâmetros `cod_prestador` (código do prestador no Ipasgo) e `data_fim` (data limite para inclusão de guias no lote, formato `DD/MM/YYYY`). Também recebe opcionalmente o `id_lote_interno` (ID da entidade local do lote).
- **Navegação:** O Selenium navega para a rota base de faturamento: `/GuiasTISS/FaturamentoAtendimentos`, fechando alertas nativos do navegador durante o processo.

### 2.2 Chamada de API FacPlan (GerarLote)
- Utiliza a classe `WebPlanClient` (com cookies herdados da sessão do driver) para enviar a requisição `POST` ao endpoint de geração de lote da operadora.
- Se a chamada retornar sucesso ou erro não-fatal, o bot avança para o agendamento do polling.

### 2.3 Atualização de Status Local
- Localiza o registro correspondente na tabela `LoteConvenio` (via `id_lote_interno`) e altera o status para `"Criando"`.
- Salva as alterações no banco de dados local (`Worker/database.py`).

### 2.4 Agendamento de Monitoramento (`13_poll`)
- Cria um novo Job na fila local (`Job`) com:
  * `id_convenio = 6`
  * `rotina = "13_poll"`
  * `priority = 10`
  * `params`: Dicionário contendo as credenciais, o lote interno, a data final formatada e `poll_attempt = 0`.
- O Dispatcher detectará este novo job e o processará para monitorar o status do processamento do lote.

## 3. Retorno
Retorna um status de persistência interna com contagem zerada de registros diretos (pois o processamento real de guias ocorrerá após o lote estar gerado):
```json
{
    "self_persisted": true,
    "inserted": 0,
    "updated": 0,
    "total": 0
}
```
