# Fluxo Passo a Passo: Rotina 1 (Autorização SP-SADT) - CAESAN

> **Classificação do Integrador:**
> - **ID Integrador (worker):** `102`
> - **ID Convênio (public):** `16` (CAESAN)
> - **Tipo de Operação:** `convenio`
> - **Tipo de Processamento Padrão:** `local`
> - **Alocação no Worker:** Servidores Genéricos (Portas 9000 a 9004)
> - **Rotina catalogada:** `op1_autorizacao` (`worker.integrador_operacoes`, id_integrador=102)

## Objetivo

Solicitar autorização SP-SADT no portal do prestador CAESAN (formulário completo, com profissional, procedimento e documento), deixando a solicitação **pendente** no portal (mesmo ciclo do IPASGO: pendente → solicitação no hub; autorizado → guia).

## Portal

- Login: `https://www.caesan.com.br/login-prestador/` (OP0 automática)
- Formulário: `https://www.caesan.com.br/sp-sadt/`

## Parâmetros (via params do Job — normalizados pela `CaesanSolicitacaoStrategy`)

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `carteira` | str | Sim | Nº de carteirinha do beneficiário |
| `codigo` | str | Sim | Código do procedimento (ex.: 50000470) |
| `nome_profissional` | str | Sim | Nome para a busca no modal de profissionais |
| `tabela` | str | Sim | `'22'` (Terapias Convencionais) ou `'00'` (Terapias Especiais); derivável de `tecnica` |
| `quantidade` | int | Sim (default 1) | Quantidade de sessões |
| `data_solicitacao` | str | Não (default hoje) | dd/mm/aaaa ou ISO |
| `data_atendimento` | str | Não (default data_solicitacao) | dd/mm/aaaa ou ISO |
| `justificativa` | str | Não | Texto do campo justificativa |
| `caminho_doc` | str | Não | Caminho local, diretório (glob `RC-*<carteira>*`) ou URL http(s) do documento (baixado em tempfile — PADROES_ROTINAS §4.2) |
| `secretaria` | str | Não (default `JANAINA`) | Valor do campo secretaria |
| `login` / `senha_criptografada` / `cod_prestador` | str | Sim | Credenciais do tenant (injetadas pela strategy/hub) |

## Fluxo Detalhado

1. OP0 automática se sem sessão; `driver.get(URL_SP_SADT)`; aguarda campo data_solicitacao.
2. Preenche **data_solicitacao** (dd/mm/aaaa) + TAB.
3. Selects (índices fixos mapeados): caráter → **option 2 (Eletivo)**; tipo_atendimento → **option 7 (Outras Terapias)**; tipo_consulta → option 2; recém-nato → option 2; indicação de acidente → option 2.
4. Preenche **carteira** + TAB (dispara validação do beneficiário; aguarda 1s).
5. Botão profissional → modal: `send_keys(nome_profissional)`; aguarda linha da tabela; **linha vazia/ausente = `PermanentError: Profissional não cadastrado`**; clique na linha.
6. Preenche **data_atendimento** e **secretaria**.
7. Scroll até a **justificativa** + `send_keys`.
8. Select **tabela** por índice (`'00'`→option 2, `'22'`→option 6); preenche **código** e **quantidade**.
9. Clica **Incluir** (aguarda 1s).
10. Resolve `caminho_doc` (URL→temp / diretório→glob `RC-*<carteira>*` / arquivo) e `send_keys` no input de arquivo (valida extensão pdf/jpg/png e ≤5MB). Ausente → WARN e segue sem anexo.
11. Clica **Gravar** (`div[19]/button[2]`).
12. **Captura do nº da solicitação** no frame de confirmação — **PENDÊNCIA: xpath oficial ainda não enviado**; best-effort (alert nativo + candidatos sweet-alert/modal/toast com regex `\d{5,10}`); sem sucesso → status `submetido` e nº recuperável via OP2.

> Nota de mapeamento: o prompt original apontava o select de tabela para o xpath do textarea da justificativa (`div[13]`); o select real usado é `div[16]/div[1]/select` (mesmo das options de tabela mapeadas).

## Retorno (result_data.data → consumer hub)

```json
{
  "status": "pendente",
  "status_guia": "Pendente",
  "guia": "882989",
  "numero_solicitacao": "882989",
  "carteira": "17134403",
  "carteirinha_id": 123,
  "codigo_terapia": "50000470",
  "qtde_solicitada": 4,
  "data_solicitacao": "01/10/2026",
  "data_atendimento": "01/10/2026",
  "profissional": "LARA BIANKA FARIA LIMA",
  "tabela": "22",
  "id_convenio": 16,
  "observacao": "Solicitação gravada no portal CAESAN; nº capturado."
}
```

O hub (`guias_sync_service`, caminho genérico) grava como **solicitação pendente** e vincula à `Solicitacao` criada no agendamento do job (match por `job_id`).

## Erros Tratados

| Cenário | Comportamento |
|---|---|
| Params obrigatórios ausentes (carteira/codigo/nome_profissional/tabela) | 400 na strategy (form/importação) ou erro no worker |
| Profissional não cadastrado no portal | `PermanentError` (linha rejeitada) |
| Documento não encontrado/inválido (>5MB, extensão) | Erro do job com mensagem explícita |
| Nº da solicitação não capturado | Status `submetido`; job success com `numero_solicitacao: null` |

## Regras de Isolamento Multitenant (Padrão do Sistema)

- Credenciais por `(user_id, id_convenio=16)` em `user_convenios` (Fernet).
- Logs em `worker.logs` prefixados `[CAESAN]` com `user_id` do job.
- Resultado persistido no hub com `user_id` do job (`solicitacoes`/`base_guias`).
