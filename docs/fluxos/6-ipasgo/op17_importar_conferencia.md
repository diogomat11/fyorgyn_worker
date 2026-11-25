# Fluxo OP17 - Importar Faturáveis do ConferenciaFaturamento (IPASGO)

**Objetivo:** Importar os faturáveis do novo módulo `ConferenciaFaturamento` do IPASGO, que substituiu o fluxo antigo (`FaturamentoAtendimentos/LoadDetalhes` da OP6). O módulo é endereçado por **PROTOCOLO (capa) do lote**.

## Parâmetros Aceitos
- `protocolo`: capa/protocolo do lote no portal (obrigatório; ex.: 899116).
- `numero_lote`: número do lote no portal (ex.: 100557; validado contra o Capa).
- `id_lote_interno`: `id_lote` em `lotes_convenio` (usado pelo consumer do hub).

## Lógica Interna
1. Bootstrap em `ConferenciaFaturamento/Index?protocolo={p}` + fechamento de notificações (reuso do `_close_notification_robust` consolidado na OP11) — mesma sessão Selenium da OP0.
2. `GET /ConferenciaFaturamento/ObterProcedimentos?protocolo={p}&_={ms}` (cache-buster = timestamp da requisição). Hoje a resposta traz todas as guias de uma vez; se o portal passar a paginar (campos `TotalPaginas`/`Pagina`), a OP itera — tolerante às duas formas.
3. Normaliza **1 linha por item** (guia + item) e devolve envelope para o hub persistir em `faturamento_lotes` (`detalheId = IdServico`).

## Regras de Negócio
- Item com `DataProcedimento` vazio recebe status **`'I'` (Inapto** — não habilitado a faturar).

## Retorno
Envelope com a lista de itens normalizados por guia+item, referenciando `protocolo`, `numero_lote` e `id_lote_interno`.
