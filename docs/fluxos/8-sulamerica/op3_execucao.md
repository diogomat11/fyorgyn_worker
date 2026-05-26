# Fluxo Passo a Passo: Rotina 3 (Execução) - SulAmérica

**Objetivo:** Confirmar a execução do serviço na SulAmérica (Baixa da Guia).

## 1. Identificação da Guia
- *A ser desenvolvido*
- Localizar a senha da autorização já gerada.

## 2. Inserção de Dados Clínicos Funcionais
- *A ser desenvolvido*
- Apontar dia e hora do procedimento executado.

## 3. Submissão e Faturamento (Isolamento Multitenant)
- *A ser desenvolvido*
- Submeter à operadora para Fatura.

## 4. Regras de Isolamento Multitenant (Padrão do Sistema)
Todas as operações de integração com a SulAmérica seguem a arquitetura multitenant da plataforma:
- **Segurança das Operações:** Os robôs recebem o `user_id` correspondente ao prestador criador do job e apenas realizam interações nas contas autorizadas desse usuário.
- **Gravação de Logs e Auditoria:** Os logs de execução gerados pelo scraper são associados diretamente ao `user_id` correspondente.
- **Salvamento de Guias:** As guias e faturamentos gerados são gravados isoladamente no banco de dados vinculados ao respectivo `user_id`, garantindo que um prestador não veja nem modifique dados de outro.
