# Fluxo Passo a Passo: Rotina 2 (Autorização) - SulAmérica

**Objetivo:** Solicitar autorização de procedimentos ou exames na SulAmérica.

## 1. Entrada de Solicitação Médico/TISS
- *A ser desenvolvido*
- Enviar CPT, CRM e códigos AMB.

## 2. Processamento e Resposta (Isolamento Multitenant)
- *A ser desenvolvido*
- Geração da numeração da Guia TISS local e extração do ID SulAmérica e Senha.

## 3. Regras de Isolamento Multitenant (Padrão do Sistema)
Todas as operações de integração com a SulAmérica seguem a arquitetura multitenant da plataforma:
- **Segurança das Operações:** Os robôs recebem o `user_id` correspondente ao prestador criador do job e apenas realizam interações nas contas autorizadas desse usuário.
- **Gravação de Logs e Auditoria:** Os logs de execução gerados pelo scraper são associados diretamente ao `user_id` correspondente.
- **Salvamento de Guias:** As guias e faturamentos gerados são gravados isoladamente no banco de dados vinculados ao respectivo `user_id`, garantindo que um prestador não veja nem modifique dados de outro.
