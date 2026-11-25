# Fluxo OP15 - Enviar Justificativa para Guia (IPASGO)

**Objetivo:** Enviar uma justificativa/observação para uma guia em regulação no portal FacPlan (NovoWebPlan), encadeando a atualização do status da solicitação no hub.

## Parâmetros Aceitos
- `guia`: número da guia operadora (obrigatório).
- `guia_prestador`: número da guia do prestador (opcional — se ausente, a OP15 descobre via OP11 antes de enviar).
- `observacao`: texto da justificativa (obrigatório).

## Lógica Interna
1. Bootstrap em `GuiasTISS/LocalizarProcedimentos` (cookies do módulo) — mesma sessão Selenium da OP0, login garantido pelo scraper.
2. `POST GetGuiaEstaNaEtapaFinalDoRegulacao` — verificação de etapa, igual ao portal.
3. `POST AddHistoricoObservacao` — grava a justificativa digitada pelo usuário.
4. Encadeia a OP11 da guia (`skip_login`) para atualizar o status da solicitação no hub — mesmo padrão da OP1.

## Retorno
Envelope com o resultado do envio + o resultado do refresh da OP11 (falha do refresh não derruba o job).
