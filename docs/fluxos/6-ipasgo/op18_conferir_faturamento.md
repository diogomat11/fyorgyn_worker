# Fluxo OP18 - Confirmar Item/Data no ConferenciaFaturamento (IPASGO)

**Objetivo:** Confirmar cada item/data do lote no novo módulo `ConferenciaFaturamento`. **Substitui a OP7** (`FaturamentoAtendimentos/ModificarDetalhe`, descontinuado).

## Parâmetros Aceitos
Unitário OU batch (a conciliação usa batch):
- `protocolo`: capa do lote no portal (obrigatório; bootstrap).
- `codigoPrestador`: código do prestador (com ou sem DV; normalizado sem DV).
- **Unitário:** `idServico`, `status` (`'Aceito'` | `'Recusado'` | `'Pendente'`), `dataRealizacao` (dd/MM/yyyy).
- **Batch:** `itens: [{idServico, status, dataRealizacao?, idDetalhe?}, ...]`.

## Lógica Interna
Para cada item, na mesma operação (comportamento do novo portal), mesma sessão Selenium da OP0:
1. `POST /ConferenciaFaturamento/ConferirItem` — `(idServico, idDetalhe, status)`.
2. `POST /ConferenciaFaturamento/EditarDataRealizacao` — `(codigoPrestador SEM DV, idServico, idDetalhe, dataRealizacao dd/MM/yyyy)`, quando houver data.

Pausa de `DELAY_ENTRE_ITENS = 0.5s` entre itens (mesma política anti-ban da OP7).

## Retorno
Resumo por item (sucesso/erro individual) — item com falha não aborta os demais.
