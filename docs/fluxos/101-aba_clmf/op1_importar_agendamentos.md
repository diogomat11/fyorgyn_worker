# Fluxo OP1 - Importar Agendamentos (ABA CLMF)

> **Classificação do Integrador:**
> - **ID Integrador / Convênio:** `101`
> - **Tipo de Operação:** `agendamento`
> - **Tipo de Processamento Padrão:** `local` / `server`
> - **Alocação no Worker:** Servidores Exclusivos de Agendamento (Portas 9005 e 9006)

Este documento descreve o funcionamento da OP1 (`op1_importar_agendamentos.py`), encarregada de extrair os agendamentos do sistema de origem e retornar ao Hub para atualização.

## Objetivo
Acessar a rota `Schedule.ajax.php` da clínica (ex: ABA CLMF) para extrair os agendamentos que ocorreram no período estipulado, além de buscar os IDs de agendamentos que foram excluídos.

## Parâmetros Aceitos
O dicionário `job_params` (ou payload JSON que instancia o Job) recebe:
- `data_inicio` ou `start_date`: Início do período (ex: `2026-12-14`). Se nulo, pega o 1º dia do mês atual.
- `data_fim` ou `end_date`: Fim do período (ex: `2026-12-19`). Se nulo, pega o dia atual.
- `id_paciente`: Filtro por paciente (padrão `"0"` = Todos).
- **`fixed`**: Indicador de **Agenda Fixa** (padrão `"N"`). Se passado como `"S"`, o worker solicitará ao portal apenas os agendamentos fixos para a semana ou período especificado, alimentando a funcionalidade de Sincronização de Agenda Fixa para autorizações no backend/frontend.

## Lógica Interna
1. Realiza requisição POST (`callback_action = get_atendimentos_replicar_agenda`) injetando os parâmetros `data_inicial`, `data_final`, `pacient_id[]` e `fixed` (variável extraída do request).
2. Faz o parsing dos dados extraindo data, hora, código de faturamento, tipo de atendimento e nome do profissional.
3. Busca nomes de convênios na rota `/pagamentos/home` para fazer o de-para do campo `schedule_pagamento_id`.
4. Realiza uma segunda chamada para `tela_excluir_atendimentos_excluidos` a fim de coletar os `schedule_id` que foram deletados no portal.
5. Retorna o JSON com a lista completa no nó `data` e a lista de excluídos no nó `atendimentos_excluidos`.

## Regras Atendidas pelo Backend Hub após o Retorno
- **Parse Inteligente de Convênio:** A resolução de ID do convênio respeita estritamente a busca por nome real, não caindo no ID 6 (Ipasgo) de forma genérica.
- **Cancelamentos:** Se o array `atendimentos_excluidos` trouxer IDs de agendamentos que já existem na base `Agendamento`, o Hub marcará automaticamente o `Status = 'Excluído'`. Agendamentos excluídos que **não** constem na base serão sumariamente ignorados.
- **Geração de OP2:** Se o paciente não tiver carteirinha vinculada ao convênio, o Backend Hub empilhará os dados recebidos em memória e criará a OP2 de captura de carteirinha em batch para otimizar os fluxos.
