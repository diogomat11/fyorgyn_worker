# MultiConv Backend API Documentation

Esta documentação descreve os principais endpoints da API servida pelo backend (FastAPI), com foco especial na integração com o Worker local para disparar operações (Jobs).

## Endpoints de Jobs

Os jobs são enfileirados no banco central (PostgreSQL) usando o endpoint `/jobs/`. O Local Worker escuta novos jobs e executa as rotinas de acordo com o `id_convenio` e a `rotina`.

### Criação de Jobs

**POST** `/jobs/`

Cria um ou múltiplos jobs de acordo com o tipo e a rotina especificada.

#### Corpo da Requisição (Payload JSON)

```json
{
  "type": "single | multiple | all | temp",
  "rotina": "string (ex: '1', 'captura', '6', 'op6_check_baixados')",
  "params": "string (JSON stringificado)",
  "id_convenio": "int",
  "carteirinha_ids": ["int"]
}
```

#### Parâmetros de `params` por Rotina (IPASGO `id_convenio = 6`)

A seguir, a documentação dos parâmetros injetados dentro de `params` (que devem ser salvos como uma string JSON no backend) para as rotinas do Convênio IPASGO:

##### OP3 - Importar Guias (`rotina: '3' | 'op3_import_guias'`)
- **`start_date`** (string/opcional): Data de início (YYYY-MM-DD).
- **`end_date`** (string/opcional): Data de fim (YYYY-MM-DD).
- **`carteira`** (string/opcional): Filtro por carteirinha do paciente.
- **`numero_guia`** (string/opcional): Filtro específico por número da guia.

##### OP6 - Check Baixados (`rotina: '6' | 'op6_check_baixados'`)
Rotina responsável por consumir a WebPlan API para listar detalhes baixados de um lote específico.
- **`loteId`** (string/obrigatório): O ID do lote de faturamento gerado ou disponível no IPASGO.
- **`codigoPrestador`** (string/opcional): Código opcional do prestador logado.

##### OP7 - Faturamento Facplan (`rotina: '7' | 'op7_fat_facplan'`)
Rotina responsável por alterar o status e faturar os detalhes de guias previamente baixadas/conferidas.
- **`detalheId`** (string/obrigatório): O ID referenciando o item detalhado da guia faturada.
- **`status` / `statusConferencia`** (string/obrigatório): O código do status de conferência (ex: "67" para Glosado, "69" para Acatado, "1" para Não Conferido).
- **`dataRealizacao`** (string/obrigatório): Data no formato "DD/MM/YYYY".
- **`valorProcedimento`** (string/opcional): Valor atualizado do procedimento.
