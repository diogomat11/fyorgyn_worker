# Fluxo Funcional e Arquitetura: Rotina 13_poll (Monitorar Lote) - IPASGO

**Objetivo:** Verificar ciclicamente o status do processamento do lote solicitado na `OP13` e, quando finalizado pelo portal, atualizar a base de dados local e iniciar o download das guias do lote (`OP6`).

## 1. Princípios de Design
- **Espera Ativa e Não-Bloqueante:** O job inicia dormindo por 60 segundos antes de interagir com o portal, economizando processamento e evitando chamadas repetitivas e velozes contra a infraestrutura do Ipasgo.
- **Auto-Agendamento Dinâmico:** Se o lote ainda estiver em fase de criação ou carregamento, o script agenda recursivamente um novo Job de polling (`13_poll`) com prioridade rebaixada (15), liberando o slot do Worker para outros jobs no intervalo.

## 2. Passo a Passo Funcional

### 2.1 Cooldown e Autenticação
- **Tempo de Espera:** Aguarda 60 segundos no início da execução.
- **Navegação de Sessão:** Acessa a tela base de faturamento para revalidar a sessão e instanciar o client de requisições. Limpa qualquer notificação na interface do portal (noty alerts).

### 2.2 Consulta na API (LoadLotes)
- Executa a chamada do método `load_lotes` da API WebPlan.
- Inspeciona o lote mais recente no topo do histórico retornado:
  * **Caso Sucesso (Pronto):** Se o status descritivo for `"Aguardando Envio"`, o lote foi processado integralmente. O bot captura o ID numérico gerado pelo Ipasgo.
  * **Caso Fallback (Pronto):** Se o status não for mais `"Criando lote"` ou `"Carregando lote"` e a data final do lote bater com o parâmetro enviado, o bot também assume a conclusão e captura o ID.
  * **Caso Processando:** Se os status indicarem fila de criação, o bot prossegue para o auto-agendamento.

### 2.3 Conclusão do Lote (Lote Pronto - Delegado ao Backend)
Se o ID do lote da API for obtido:
- O worker retorna no JSON de resultado o status `"ready"`, o `lote_id_api` e o `id_lote_interno`.
- O Hub Backend recebe esse resultado via webhook, atualiza o `LoteConvenio` local para `"Aberto"` e cria o job `"6"` (`op6_check_baixados.py`) para baixar as faturas do lote no `backend_worker`.

### 2.4 Reagendamento (Delegado ao Backend)
Se o lote ainda não estiver pronto:
- O worker retorna o status `"processing"`.
- O Hub Backend recebe o webhook de "processing" e agenda um novo job `"13_poll"` no `backend_worker` incrementando a tentativa de polling.

## 3. Retorno
Retorna o dicionário de status do polling:
```json
{
  "status": "ready" ou "processing",
  "lote_id_api": 2026071301,
  "id_lote_interno": 45,
  "cod_prestador": "98271",
  "poll_attempt": 0
}
```
