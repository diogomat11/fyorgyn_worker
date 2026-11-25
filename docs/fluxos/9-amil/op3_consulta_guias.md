# Fluxo Passo a Passo: Rotina 3 (Consulta de Guias) - Amil


> **NOTA (2026-11-20, IMPL-AMIL-01):** A **consulta de guias** da AMIL está
> implementada em [op1_consulta_guias.md](op1_consulta_guias.md)
> (`Local_worker/Worker/9-amil/op/op1_consulta_guias.py`, rotina canônica
> `op1_consulta`). Este documento permanece placeholder para a operação
> específica do título abaixo.

**Objetivo:** Pesquisar guias já solicitadas ou ativas na Amil para o beneficiário.

## 1. Filtro de Guias
- *A ser desenvolvido*
- Pesquisa por carteirinha ou período.

## 2. Extração de Componentes
- *A ser desenvolvido*
- Parsing da tabela de resultados: Data, Status, Senha de Autorização.

## 3. Retorno e Persistência Multitenant
- *A ser desenvolvido*
- Salvar dados de Guia capturada na aplicação.

## 4. Regras de Isolamento Multitenant (Padrão do Sistema)
Todas as operações de integração com a Amil seguem a arquitetura multitenant da plataforma:
- **Segurança das Operações:** Os robôs recebem o `user_id` correspondente ao prestador criador do job e apenas realizam interações nas contas autorizadas desse usuário.
- **Gravação de Logs e Auditoria:** Os logs de execução gerados pelo scraper são associados diretamente ao `user_id` correspondente.
- **Salvamento de Guias:** As guias e faturamentos gerados são gravados isoladamente no banco de dados vinculados ao respectivo `user_id`, garantindo que um prestador não veja nem modifique dados de outro.
