# Fluxo Passo a Passo: Rotina 1 (Elegibilidade) - SulAmérica

**Objetivo:** Validar carteirinha no sistema SulAmérica.

## 1. Consulta
- *A ser desenvolvido*
- Localizar Input de "Elegibilidade" no portal Saúde Online.

## 2. Validação TISS e Persistência Multitenant
- *A ser desenvolvido*
- Resgatar dados de carência, tipo de plano e elegibilidade ativa.

## 3. Regras de Isolamento Multitenant (Padrão do Sistema)
Todas as operações de integração com a SulAmérica seguem a arquitetura multitenant da plataforma:
- **Segurança das Operações:** Os robôs recebem o `user_id` correspondente ao prestador criador do job e apenas realizam interações nas contas autorizadas desse usuário.
- **Gravação de Logs e Auditoria:** Os logs de execução gerados pelo scraper são associados diretamente ao `user_id` correspondente.
- **Salvamento de Guias:** As guias e faturamentos gerados são gravados isoladamente no banco de dados vinculados ao respectivo `user_id`, garantindo que um prestador não veja nem modifique dados de outro.
