# Fluxo OP21 - Anexar Arquivos ao Recurso de Glosa (IPASGO)

**Objetivo:** Anexar PDFs a um protocolo de recurso de glosa no portal NovoWebPlan (upload por protocolo, não por guia). Ref: `docs/plano_anexos_recurso_glosa_ipasgo.md` · Release 2026-11-06.

## Parâmetros Aceitos
- `protocolo`: capa/protocolo do lote no portal (obrigatório — o hub associa ao lote).
- `caminho_arquivo`: caminho local do PDF (obrigatório; validado pelo hub na criação do job).

## Lógica Interna (3 etapas com o portal)
1. `GET RecursoGlosa/GetAnexos?chaveCapa={protocolo}` — **idempotência**: se o arquivo já foi anexado, não reenvia.
2. `POST Upload/SendFile` — multipart com campo `file`; gera caminho temporário no servidor IIS (`C:\\inetpub\\wwwroot\\...\\Uploads\\Temp\\...`).
3. `POST RecursoGlosa/SaveFile` — payload `{"param": "<base64>"}` onde o base64 codifica `{"NumeroProtocolo":..., "PathFileName":..., "FileName":...}`.
4. Validação pós-salvamento: novo `GetAnexos` confirma a inclusão do anexo.

## Diferenças da OP19
- Não exige padrão de senha/guia no nome do arquivo — aceita qualquer `.pdf` válido **≤ 5MB**.

## Tratamento de Falhas (`op/_anexos_common.py`)
- Bloqueio (403/429) → `_abortar_fila_protocolo` aborta os jobs do protocolo com motivo classificado (reenvio automático após pausa).
- Sessão rejeitada → navegador invalidado (`about:blank`); próximo job faz re-login.
- Circuit-breaker em memória (3 falhas consecutivas) + keepalive de heartbeat.

## Endpoints do Hub
`POST /recurso-glosa/lotes/{id}/anexos/analisar` · `POST .../anexos` · `GET .../anexos/status` · `POST .../anexos/reprocessar` · `POST .../anexos/abortar` (modal **Anexos** em `RecursoGlosa.jsx`).
