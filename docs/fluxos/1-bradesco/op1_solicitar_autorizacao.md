# OP1 - Solicitar Autorização SADT (Bradesco)

## Objetivo
Preencher o formulário completo de solicitação de autorização SADT no portal Polimed/Orizon e capturar o retorno (guia prestador + status).

## Portal
- **URL:** `https://www.polimed.com.br/autorize/prestadores/iframe/senha/solicitacao_senha_externa`

## Parâmetros (via `params` do Job)
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `RegistroAns` | str | Sim | `005711` ou `421715` |
| `cod_prestador` | str | Sim* | `935102` (Psico/Fono) ou `902446` (TO/Fisio) |
| `carteira` | str | Sim | Número da carteirinha do beneficiário |
| `nomeMedico` | str | Sim | Nome do profissional solicitante |
| `ConselhoMedico` | str | Sim | Sigla do conselho (ex: CRP, CRFa) |
| `NumeroRegistroMedico` | str | Sim | Número do registro no conselho |
| `UfConselhoMedico` | str | Sim | UF do conselho (ex: GO) |
| `Cbomedico` | str | Sim | CBO do profissional |
| `CodigoCid10` | str | Sim | Código CID-10 |
| `TipoAtendimento` | str | Sim | `"pequenos atendimentos"` ou `"TERAPIAS"` |
| `codigoProcedimento` | str | Sim | Código do procedimento |
| `qtde_solicitad` | int | Sim | Quantidade solicitada |
| `caminho_arquivo_RM` | str | Sim | Caminho absoluto do arquivo RM |

> *`cod_prestador` usa o valor do `user_convenios` como fallback quando não informado nos params.

## Regras de Negócio

### cod_prestador por Área
| cod_prestador | Áreas | TipoAtendimento |
|---------------|-------|-----------------|
| `935102` | Psicologia, Fonoaudiologia | pequenos atendimentos |
| `902446` | TO, Fisioterapia, Psicomotricidade | TERAPIAS |

### RegistroAns
O Bradesco opera com dois registros ANS possíveis: `005711` e `421715`.

## Fluxo Detalhado
1. Navegar para URL da OP1
2. Selecionar operadora (RegistroAns)
3. Selecionar rádio "Carteira" e preencher número
4. Atendimento RN = "Não"
5. Tipo contratado solicitante → "Código na operadora"
6. Preencher código prestador
7. Preencher dados do profissional (nome, conselho, registro, UF, CBO)
8. Selecionar caráter "Eletivo"
9. Pesquisar CID10 (popup → selecionar primeiro resultado)
10. Selecionar tipo de atendimento
11. Selecionar regime e indicador de acidente
12. Preencher matrícula prestador executante
13. Preencher código e quantidade do procedimento
14. Upload do arquivo RM (anexar documento)
15. Enviar solicitação
16. Capturar retorno na janela de resultado

## Retorno
```json
[{
    "guia_prestador": "123456",
    "status_guia": "Autorizado",
    "numero_guia": "123456",
    "codigo_terapia": "30301033",
    "qtde_solicitada": 48,
    "cod_prestador": "935102"
}]
```

Dados persistidos automaticamente pelo Dispatcher em `base_guias`.

## Erros Tratados
| Cenário | Comportamento |
|---------|---------------|
| Parâmetro obrigatório ausente | `ValueError` imediato |
| CID inválido/não localizado | Erro com descrição — não retenta |
| TipoAtendimento desconhecido | `ValueError` — não retenta |
| Janela resultado não abriu | Erro — retenta |
| Upload falhou | Exceção — retenta |
