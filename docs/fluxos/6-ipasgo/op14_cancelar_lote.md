# Fluxo Funcional e Arquitetura: Rotina 14 (Cancelar Lote) - IPASGO

**Objetivo:** Cancelar um Lote de Faturamento ativo diretamente na API do portal do Ipasgo (WebPlan), atualizar o status local do lote e marcar as guias atreladas a ele como bloqueadas para conciliação.

## 1. Princípios de Design
- **Consistência de Estado Local:** O cancelamento no portal invalida o lote. Para refletir isso na conciliação local e evitar reenvios acidentais, a rotina limpa os bloqueios e sinaliza que os atendimentos do lote estão livres ou inutilizados.
- **Rollback de Guias:** Altera o status de conciliação das guias vinculadas para impedir que fiquem presas em lote inválido.

## 2. Passo a Passo Funcional

### 2.1 Preparação de Parâmetros e Sessão
- **Parâmetros:** Requer `cod_prestador` e `numero_lote` (ID do lote gerado pelo Ipasgo). O parâmetro `id_lote_interno` é opcional e serve para precisão na busca local.
- **Autenticação:** O Selenium navega até a rota de faturamento do WebPlan, aceitando quaisquer alertas nativos que bloqueiem a troca de tela.

### 2.2 Chamada de Invalidação (CancelarLote)
- O script invoca o client `WebPlanClient` e executa a chamada `cancelar_lote` passando o número do lote e código do prestador.
- A API do Ipasgo recebe o comando e realiza a desestruturação do lote no servidor deles.

### 2.3 Processamento de Resultados (Sem Acesso ao Banco Público)
- O script não interage com o banco de dados do Hub. Ele apenas efetua a chamada de cancelamento no portal e retorna o resultado da operação.
- A lógica de atualizar o `LoteConvenio` local para `"Cancelado"` e atualizar o `StatusConciliacao` das guias para `"bloqueado"` é delegada ao Hub Backend ao receber o webhook de retorno.

## 3. Retorno
Retorna indicando o sucesso do cancelamento e os metadados do lote:
```json
{
  "status": "success",
  "message": "Lote cancelado com sucesso no portal.",
  "numero_lote": "88776655",
  "id_lote_interno": 45
}
```
