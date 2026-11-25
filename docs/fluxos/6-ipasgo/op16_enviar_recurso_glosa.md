# Fluxo OP16 - Enviar Justificativas de Recurso de Glosa (IPASGO)

**Objetivo:** Enviar as justificativas de recurso de glosa dos itens de um lote ao portal FacPlan (NovoWebPlan), a partir dos dados vinculados no frontend.

## Parâmetros Aceitos
- `protocolo`: capa/protocolo do lote no portal (obrigatório).
- `id_lote_interno`: `id_lote` em `lotes_convenio` (usado pelo consumer do hub).
- `servicos`: lista de `{chave, chave_ut_serv, quantidade_glosada, valor_recurso, justificativa}` montada pelo hub a partir do banco (justificativa vinculada aos itens no frontend).

## Lógica Interna
1. Bootstrap em `GuiasTISS/RecursoGlosa` (helper da OP10) — mesma sessão Selenium da OP0.
2. `POST /RecursoGlosa/SalvarDigitacaoParcialmente` em **chunks** — o endpoint é de digitação parcial e aceita salvamentos incrementais.
3. Encadeia a OP10 do protocolo (`skip_login`) para atualizar o estado do lote no hub — falha não derruba o job (mesmo padrão da OP15 → OP11).

Payload enviado ao portal:
```json
{ "Capa": 895854,
  "Servicos": [{ "Chave": "...", "ChaveUtServ": "...", "QuantidadeGlosada": 1,
                 "ValorRecurso": 0, "Justificativa": "..." }],
  "PesquisarRecursosSalvos": false }
```

## Retorno
Envelope com o resultado do salvamento parcial + o refresh da OP10.
