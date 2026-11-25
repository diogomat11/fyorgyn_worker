# Fluxo OP19 - Anexar Arquivo à Guia no ConferenciaFaturamento (IPASGO)

**Objetivo:** Anexar um PDF à guia no módulo `ConferenciaFaturamento` do IPASGO (Conferência de Faturamento). Ref: `docs/plano_conferencia_faturamento_ipasgo.md` · Release 2026-11-05.

## Parâmetros Aceitos
- `protocolo`: capa do lote no portal (obrigatório; ex.: 903505).
- `numeroGuiaOperadora`: guia da anexação (obrigatório; ex.: 24768401).
- `senha`: senha da guia (11 dígitos; derivada do nome do arquivo pelo hub).
- `caminho_arquivo`: caminho local do PDF (obrigatório).

## Lógica Interna
1. Valida o arquivo local (existe, `.pdf`, **≤ 5MB** — mesmo limite do `op1_autorizar`).
2. Bootstrap em `ConferenciaFaturamento/Index?protocolo={p}` (helper da OP17) — mesma sessão Selenium da OP0.
3. `POST multipart /ConferenciaFaturamento/AnexarArquivoGuia?capaLoteId={protocolo}&numeroGuiaOperadora={guia}` com o PDF no campo `arquivo` (filename original preservado).

## Tratamento de Falhas (`op/_anexos_common.py` — compartilhado com a OP21)
- Bloqueio (403/429) e instabilidade/sessão (401/500) classificados; **circuit-breaker em memória** (3 falhas consecutivas); keepalive de heartbeat; tratamento de cascata.

## Retorno
Resultado da anexação com metadados do arquivo enviado.
