✅ CHECKLIST DE IMPLEMENTAÇÃO
🔹 Arquitetura

- [x] Separar convênios em pastas independentes
- [x] Criar dispatcher com loop de 5s
- [x] Implementar pool de ChromeDrivers (SeleniumManager)
- [x] Permitir troca de convênio sem reiniciar driver

🔹 Prioridades

- [x] Criar tabela de prioridades (priority_rules)
- [x] Implementar escalonamento por tempo (Dynamic Scoring)
- [x] Garantir desempate por JOB mais antigo
- [x] Prioridade 0 sempre absoluta

🔹 Banco de Dados

- [x] Criar novas tabelas propostas
- [x] Indexar por convênio, rotina e status
- [x] Criar histórico de execução

🔹 Selenium

- [x] Headless configurável por servidor
- [x] Timeouts inteligentes
- [x] Retry controlado por tipo de erro

🔹 Segurança

- [x] Criptografia de credenciais
- [x] Logs sem dados sensíveis
- [x] Controle de acesso por convênio

🔹 Dependências de Jobs e Captura (QA)

- [ ] Arquitetura Preservada: Base de Guias e Scrappers não-monolíticos confirmados (`architecture_guidelines.md`).
- [ ] Timeout Scraper (Unimed GO): Scraper exclui local se Timestamp + 59m < Now + 2m.
- [ ] Bloqueio UI: Botão Capturar Bloqueado p/ IPASGO (ID 6).
- [ ] Dispatcher: Job de Execução com `depending` aguarda Job de Captura dar 'sucesso'.
- [ ] UI Confirmação (Unimed GO): Dialog Sim/Não validado.
- [ ] Status Agendamento: Tabela `agendamentos.execucao_status` alimentada corretamente após execução.