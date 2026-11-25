# OP1 — Consulta de Guias (pedidos de autorização) AMIL

**Status: IMPLEMENTADO e validado E2E no portal real (2026-11-20): range 2026-10-31..2026-11-14 → 140 pedidos / 14 páginas / 140 detalhes, records idênticos à captura de referência.**

## API (contrato CONFIRMADO no portal real — Chrome DevTools 2026-11-20)

### Listagem
```
GET https://credenciado.amil.com.br/credenciadomedico/pedidos-autorizacao
    ?codigoCredenciado=67628788
    &identificacao=<senha|guia|carteirinha>      (opcional — filtro unificado)
    &dataAutorizacaoDe=YYYY-MM-DD&dataAutorizacaoAte=YYYY-MM-DD  (sem identificador)
    &start=1&limit=10&sort=-numeroPedido
Headers:
    accept: application/vnd.amil.credenciado.medico.pedidos-autorizacao.v1+json
    authorization: Bearer <tokenInfo.accessToken>
    x-session: <sessionToken JWT>
    x-user: <credenciadoInfo.codigo>
    content-type: application/json
    credentials: include (cookies Akamai/JSESSIONID)
```

### Detalhe
```
GET /credenciadomedico/pedidos-autorizacao/{numeroPedido}?numeroAssociado={numeroAssociado}
(mesmos headers) → numeroGuia "…seq001", pedidoConfirmado, validadeSenhaAutorizacao,
procedimentosMedicos[], pacotesAutorizados[], anexos etc.
```

### Comportamentos confirmados

| Caso | Resposta da API | Tratamento no worker |
|---|---|---|
| Resultado VAZIO | **404** JSON `messageKey: integracao.pedido.autorizacao.nao.encontrado` | **Não é erro** — lista vazia, job success (sem retry) |
| Sessão inválida | 401/403 JSON | `SessionExpiredError` → escada de re-login do core |
| Bloqueio Akamai | **403 HTML** `<!doctype html>… Acesso Negado` | `SessionExpiredError` com diagnóstico (UA headless → preferir headful); re-login renova o sensor `_abck` |
| Transiente | 0/429/5xx | 1 retry com backoff 2s |
| Rotação de token | `tokenInfo.expiresIn: 1800` | Tokens re-extraídos do `acesso-info` **antes de cada requisição** |

### Filtro `identificacao` (D6 revisada)

O campo da UI é **"Identificador (Número da carteirinha, senha ou número do pedido) - Opcional"**
→ query param `identificacao`. Com identificador a API **DESCARTA as datas** (o próprio SPA não as envia).
O nome `senhaAutorizacao` (hipótese original) **não existe** — retorna 400 `pedido.nao.encontrato`.

Precedência implementada (`montar_params_busca`): **senha > guia > carteirinha → `identificacao` (sem datas)**; sem identificador → `dataAutorizacaoDe/Ate` obrigatórios.

### Paginação (D7)

`start` começa em **1** e avança `limit` a `limit` (1, 11, 21, …); nº de páginas = `ceil(totalCount/limit)`
(resposta traz `totalCount`, sem campo de páginas). NÃO depender de `links.next` (href aponta para base
distinta). Caps de segurança: `MAX_PAGINAS=500`, `MAX_GUIAS_DETALHE=2000`.

### Performance — fetch em lote paralelo (validado E2E 2026-11-21)

As páginas restantes e os detalhes vão em **lotes paralelos DENTRO do navegador**
(`_LOTE_JS` — Promise pool, AbortController por fetch): um único round-trip Selenium
devolve o lote inteiro, eliminando N viagens Python→chromedriver individuais.

| Parâmetro | Valor | Efeito |
|---|---|---|
| `LOTE_CONCORRENCIA` | 6 | fetches simultâneos por lote (burst normal de SPA; Akamai aceita — E2E 199/199 sem bloqueio) |
| `LOTE_TAMANHO_DETALHE` | 24 | urls por lote de detalhe (24/6 ≈ 4 rodadas de rede) |
| `LOTE_BATCH_TIMEOUT_S` | 120 | timeout da chamada batch (set_script_timeout = timeout+10) |

**Medido (199 guias, 20 páginas, 199 detalhes)**: OP0 login 27s + OP1 124s = **total ~2,5 min**
(sequencial antes: ~12 min — coleta 30s + detalhes ~11 min). Tokens re-extraídos a cada lote
(rotação de 30 min); 401/403 aborta o lote com `SESSAO_EXPIRADA` (escada do core); transientes
têm 1 retry em lote; 404-vazio por item = vazio (sem retry).

## Records para o hub (contrato `guias_sync_service`)

1 record por item de `detalhe.sequenciaPrincipal.procedimentosMedicos` (sem detalhe → record mínimo):

| JSON AMIL | Campo do record |
|---|---|
| `numeroPedido` | `guia` |
| `detalhe.numeroGuia` | `guia_prestador` (ex. `538503088seq001`) |
| `numeroAssociado` | `carteirinha` + `codigo_beneficiario` |
| `nomeAssociado` | `paciente` |
| `situacao` | `status_guia` (hub normaliza: Autorizado/Cancelado/Em análise) |
| `senhaAutorizacao` | `senha` |
| `dataSolicitacao`/`dataAutorizacao`/`dataValidade` | `data_solicitacao`/`data_autorizacao`/`validade` ([:10]) |
| `proc.codigo`/`proc.nome` | `codigo_terapia`/`nome_terapia` |
| `proc.quantidadeSolicitada`/`quantidadeAutorizada` | `qtde_solicitada`/`sessoes_autorizadas` |
| `detalhe.pedidoConfirmado` | `status_token` (coluna base_guias, migration 0120) |
| `detalhe.sequenciaPrincipal.pacotesAutorizados[0].codigo` | `codigo_faturamento` → hub cadastra vínculo em `procedimentos.faturamento` (**dentro de `sequenciaPrincipal`**, não na raiz — incidente job 28845) |
| `detalhe.validadeSenhaAutorizacao` | prioridade sobre `dataValidade` para `validade` |

Último item do retorno: `{"_meta": {total_count, paginas, guias_detalhe, detalhe_truncado, filtro}}`
— ignorado pelo sync (sem `guia`); a chave `senhaAutorizacao` do filtro vem mascarada nos logs/meta.

## Operação

- Rotina: `1` / `op1_consulta` / `op1_consulta_guias`; params do job: `senha` **ou** `carteirinha` **ou** `guia` **ou** `data_ini`+`data_fim`; `cod_prestador` injetado pelo hub.
- Sessão: OP1 abre `PEDIDOS_URL`; se cair em `/login` → `SESSAO_EXPIRADA` → core refaz OP0 no mesmo driver (afinidade strict).
- Throttle 0,5s entre requisições; ~140 guias ≈ 3 min (280 requests).
