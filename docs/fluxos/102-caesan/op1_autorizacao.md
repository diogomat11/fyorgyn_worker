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
- **Layout com iframes**: o carregamento do SP-SADT após o clique no menu é lento e a tabela de resultados do profissional fica em **iframe** — a OP1 gerencia o contexto do driver (busca o formulário em qualquer frame; após selecionar o profissional volta ao contexto do formulário).

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

> **Mapeamento oficial (2026-11-03, extraído do HTML real do portal via evidência `102-caesan/debug/`):** o SP-SADT é um form **AngularJS** — os identificadores estáveis são os próprios `ng-model`/`ng-click` do portal (usados como candidato primário de cada campo; os xpaths absolutos históricos ficam como fallback). Fatos do HTML real: campos de data são `input[type=text]` (digitar dd/mm/aaaa + TAB); selects têm **values Angular** (`string:1` = "1 - Eletivo", `string:03` = "Outras Terapias", `string:4` = "Por encaminhamento", `string:0` = "Não", `string:9` = "Não Acidente"; tabela `string:22`/`string:00`); o modal de profissional é **bootstrap sem iframe** (busca: input `ng-model='buscaProfissional'` + botão `ng-click='buscaProfissionais()'`; seleção confirmada pelo preenchimento de `objVO0406.nome`); a validação da carteira preenche o hidden `usuario.nombeneficiario`; Incluir/Gravar são `ng-disabled` até o form ficar válido. Todo campo é validado (tag+tipo) antes de escrever; em falha: log `Estrutura do formulário` + screenshot/HTML em `debug/`. Simulação: `scratch/mock_caesan/simulate_op1.py` (mock espelho do portal, variantes com/sem banner).

1. `driver.get(URL_SP_SADT)` com **retry 3×** (readyState + aguarda o form por até 45s e aguarda as listas iniciais do BIOS: `lstCarSolicitacao`, `lstTipoAtendimento`, `procTuss`, `objVO0306`).
2. Preenche **data_solicitacao** via `_preencher_data_texto`: no portal real (`ctrSpSadt.js`), `gravarGuia()` converte `dtpedido` e `dtprovproc` fatiando ISO `YYYY-MM-DD` (`substring(8,10)+'/'+substring(5,7)+'/'+substring(0,4)`); portanto o input opera como `type='date'` (exibindo `DD/MM/YYYY` na tela em pt-BR e armazenando `YYYY-MM-DD` no DOM e em `scope.objVO0481.dtpedido`), garantindo que o BIOS receba `DD/MM/YYYY` no `coddao: 483` (e nunca `'26//2/04/1'`). Pausa `PAUSA_PASSO_FORM` (`0.8s`).
3. Selects (por `value` Angular, com `change` explícito e pausa): caráter → `string:1` (Eletivo); carteira + TAB; tipo_atendimento → `string:03` (Outras Terapias); tipo_consulta → `string:4`; recém-nato → `string:0`; indicação de acidente → `string:9`.
4. Preenche **carteira** + TAB (dispara `buscacarencia` `coddao: 551` no portal; aguarda `scope.usuario.nombeneficiario` ou classe `user-success`).
5. Botão profissional → modal (`ModalProfissional()`): `send_keys(nome_profissional)` + **ENTER** + botão `buscaProfissionais()`; clica a 1ª linha e valida o preenchimento de `objVO0406.nome` e `objVO0481.codprofissional`; 3 tentativas, senão `PermanentError`.
6. Preenche **data_atendimento** (ISO `YYYY-MM-DD` no scope do portal real p/ `gravarGuia()` produzir `DD/MM/YYYY`) e **secretaria** + TAB.
7. Scroll até a **justificativa** + `send_keys` + TAB.
8. **Procedimento passo a passo com pausas**:
   - Seleciona **tabela** por value (`string:22`/`string:00`), pausa `1.0s` e valida `objVO0482.codtabela`.
   - Preenche **código** + TAB único (dispara `buscarProcedimentoTussCodigo()` `coddao: 526` e aguarda `objVO0482.descricao` popular via `_ler_scope_sadt`, abortando se `alertaProcedimento`/`alertabloqueio`/`procbloqueado`).
   - Preenche **quantidade** + TAB, valida `objVO0482.qtdsolicitada` e aguarda **`PAUSA_PRE_INCLUIR_ITEM` (`2.0s`)** com os 3 campos visíveis na tela antes de clicar em Adicionar Procedimento.
9. Clica **Adicionar Procedimento** (`adicionarProcedimento()`), **valida pós-condição** (`objVO0481.procedimentos.length >= 1`, logando o item inserido na tabela `Procedimento(s) TUSS Solicitado(s)`) e aguarda **`PAUSA_POS_INCLUIR_ITEM` (`2.5s`)** antes de iniciar o envio do anexo.
10. Resolve `caminho_doc` (URL→temp / diretório→glob `RC-*<carteira>*` / arquivo), `send_keys` no input de arquivo, aguarda `objVO0481.lstarquivos.length >= 1` com `base64_len > 100` e aguarda **`PAUSA_POS_ANEXO` (`2.5s`)**.
11. **Gate pré-Gravar (fail-fast) + Pausa pré-Gravar (`2.0s` padrão / `60s` em `modo_validacao`)**: inspeciona o scope (`_ler_scope_sadt`, tratando `$scope.alerta` como função com propriedades `.titulo`/`.mensagem`/`.complemento`) e aborta antes do clique se `dtpedido`/`dtprovproc`, `procedimentos`, profissional ou anexo falharem. Clica **Gravar** (`gravarGuia()`) com wrapper + interceptor XHR que blinda `dtpedido`/`dtprovproc` em `DD/MM/YYYY` no `coddao: 483` e sanitiza o `base64` de `lstarquivos` nos logs.
12. **Captura do nº da solicitação**: no XHR do BIOS / `scope.alerta`, no modal `#alerta` (`//*[@id="alerta"]/div/div/div[2]/p`), ou consultando diretamente o webservice BIOS (`coddao: 544` Solicitações Pendentes e `coddao: 560` Solicitações Autorizadas filtrando por `codassociado == carteira`) e fallback em **nova aba** (`solicitacoes-pendentes` / `consultar-solicitacoes`); apenas com nº capturado o status é `pendente` (sem nº → `submetido` para reconciliação via OP2).

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
| Profissional não cadastrado no portal | `PermanentError` após 3 tentativas de busca/seleção no modal |
| Campo mapeado não é mais o controle esperado (ex.: texto → date nativo) | `PermanentError` com diagnóstico (tag/type/id/name) + **dump da estrutura do formulário no log** para remapear o xpath — nenhum valor é enviado a campo errado |
| Documento não encontrado/inválido (>5MB, extensão) | Erro do job com mensagem explícita |
| Nº da solicitação não capturado | Status `submetido`; job success com `numero_solicitacao: null` (fallback OP2) |

## Regras de Isolamento Multitenant (Padrão do Sistema)

- Credenciais por `(user_id, id_convenio=16)` em `user_convenios` (Fernet).
- Logs em `worker.logs` prefixados `[CAESAN]` com `user_id` do job.
- Resultado persistido no hub com `user_id` do job (`solicitacoes`/`base_guias`).
