# Fluxo Passo a Passo: Rotina 6 (Envio de Faturamento) - Amil


> **NOTA (2026-11-20, IMPL-AMIL-01):** A **consulta de guias** da AMIL está
> implementada em [op1_consulta_guias.md](op1_consulta_guias.md)
> (`Local_worker/Worker/9-amil/op/op1_consulta_guias.py`, rotina canônica
> `op1_consulta`). Este documento permanece placeholder para a operação
> específica do título abaixo.

**Objetivo:** Transmissão final do lote ou arquivo XML TISS para a operadora Amil.

## 1. Upload do Arquivo (Se XML TISS)
- *A ser desenvolvido*
- Envio do arquivo gerado para o validador TISS do portal Amil.

## 2. Impressão de Capa
- *A ser desenvolvido*
- Confirmação do recebimento, leitura do comprovante (Capa de Lote).

## 3. Desfecho
- *A ser desenvolvido*
- Atualizar status no banco de dados para "Faturado".
