# Fluxo Passo a Passo: Rotina 2 (Consultar Solicitação/Guia) - CAESAN

> **Classificação do Integrador:**
> - **ID Integrador (worker):** `102`
> - **ID Convênio (public):** `16` (CAESAN)
> - **Tipo de Operação:** `convenio`
> - **Tipo de Processamento Padrão:** `local`
> - **Alocação no Worker:** Servidores Genéricos (Portas 9000 a 9004)
> - **Rotina catalogada:** `op2_consultar_guia` (`worker.integrador_operacoes`, id_integrador=102)

## Objetivo

Consultar o status de uma solicitação/guia no webservice BIOS e sincronizar no hub: **Autorizado → `base_guias`**; **Pendente/Negado → `solicitacoes`** (mesmo split do IPASGO via `bulk_upsert_guias_from_json`).

## Endpoints

- Página (sessão): `https://www.caesan.com.br/consultar-solicitacoes/`
- Webservice: `POST https://ws2.bios.inf.br/wsbios/service/V1`

## Payload do Webservice (fixo)

```json
{ "coddao": 490, "conteudo": null, "parametros": ["W8", 882989, "8016249"] }
```

- `882989` = nº da solicitação/guia; `"8016249"` = cod_prestador do tenant.
- Sessão: `requests.Session` construída com cookies + User-Agent do driver Selenium logado na OP0 (padrão `WebPlanClient`). Resposta HTML = sessão expirada → retry com re-login.

## Parâmetros (via params do Job)

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `guia` | str/int | Sim | Nº da solicitação/guia (aceita `numero_guia`/`numero_solicitacao`) |
| `cod_prestador` | str | Sim* | Código do prestador (default: credencial do tenant) |
| `login` / `senha_criptografada` | str | Sim | Credenciais (OP0 automática) |

## Fluxo Detalhado

1. OP0 automática se sem sessão; abre `consultar-solicitacoes` (document.readyState complete).
2. `BiosClient(driver).consultar_guia(guia, cod_prestador)` — 3 tentativas; `codstatus != 200` → erro com `mensagem`.
3. Normaliza `conteudo` → lista de records (1 por item de `lstprocedimentos`).

## Campos Extraídos do JSON de Retorno

| Campo BIOS | Record do hub |
|---|---|
| `status` | `status_guia` (Autorizado/Pendente/Negado) |
| `dtautorizacao` | `data_autorizacao` |
| `dtpedido` | `data_solicitacao` |
| `codautorizacao` | `senha` |
| `lstprocedimentos[].codprocedimento` | `codigo_terapia` |
| `lstprocedimentos[].qtdsolicitada` | `qtde_solicitada` |
| `lstprocedimentos[].qtdautorizada` | `sessoes_autorizadas` |

## Retorno (result_data.data)

```json
[
  {
    "guia": "882989",
    "status_guia": "Autorizado",
    "senha": "3201368829895",
    "data_solicitacao": "28/09/2026",
    "data_autorizacao": "28/09/2026",
    "codigo_terapia": "22010040",
    "nome_terapia": "Avaliação Neuropsicológica Infantil",
    "qtde_solicitada": 1,
    "sessoes_autorizadas": 1,
    "codigo_beneficiario": "9804304",
    "carteirinha_id": 123,
    "id_convenio": 16
  }
]
```

## Erros Tratados

| Cenário | Comportamento |
|---|---|
| Sessão expirada (resposta HTML) | `ValueError` → retry do `process_job` com re-login |
| `codstatus != 200` | Erro com a `mensagem` do BIOS |
| `guia` ausente nos params | Erro "Parâmetro obrigatório ausente: guia" |
| Conteúdo vazio | Erro explícito com a mensagem do webservice |
