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

### 2.3 Atualização no Banco Local
- **LoteConvenio:** Localiza a entidade local e atualiza o status para `"Cancelado"`.
- **FaturamentoLote:** Busca todas as guias associadas a esse lote e define a coluna `StatusConciliacao = "bloqueado"` para cada uma.
- Realiza o commit no banco de dados local.

## 3. Retorno
Retorna o número do lote cancelado e o novo status:
```json
[{
    "numero_lote": "88776655",
    "status": "Cancelado"
}]
```
