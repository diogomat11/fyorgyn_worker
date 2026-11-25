# Fluxo OP20 - Validar e Extrair CodigoBeneficiario (IPASGO)

**Objetivo:** Validar carteirinhas e extrair o `CodigoBeneficiario` real do portal para cada carteirinha do lote (isolado ao `user_id` do job). Ref: `docs/plano_validar_codigo_beneficiario_ipasgo.md`.

## Lógica Interna
1. Reutiliza a sessão autenticada da OP0 (`IpasgoScraper.login`).
2. Bootstrap em `/GuiasTISS/LocalizarProcedimentos` e fechamento de notificações, exatamente como a OP11 (`_close_notification_robust`).
3. Injeta interceptador em `XMLHttpRequest`/`fetch` para capturar o payload do `POST /LocalizarProcedimentos/Localizar` (camada L3).
4. Para cada carteirinha:
   - Limpa o componente `<beneficiario>` (Selectize) e digita a carteirinha no input.
   - **1 item selecionado automaticamente** (`div.itemSelected[data-value]` + `input.inputSelectize.selectized[value]`) → lê L1 + L2.
   - **Dropdown com múltiplas opções** (`.selectize-dropdown-content .option`) → compara o número entre parênteses `(<carteirinha>) NOME NASC: ...` e o nome do paciente, seleciona a opção correspondente e confirma.
   - **Desempate/fallback:** aciona o botão Pesquisar (`#localizar-procedimentos-btn`) e extrai/confirma o `CodigoBeneficiario` do corpo da requisição interceptada (L3).

## Regras de Negócio
- O formato exato do `CodigoBeneficiario` é preservado (ex.: `040473-0`, tamanho variável, **sem remover hífen ou zeros à esquerda**).

## Retorno
Por carteirinha: validação (achada/não achada/ambígua), `CodigoBeneficiario` extraído e o nome confirmado.
