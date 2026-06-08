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

### 2.3 Conclusão do Lote (Lote Pronto)
Se o ID do lote da API for obtido:
1. **Atualização do Lote local:** Localiza o `LoteConvenio` e vincula o `numero_lote = lote_id_api` e define o status para `"Aberto"`.
2. **Criação da OP6 (Download de Guias):** Agenda um Job de rotina `"6"` (`op6_check_baixados.py`) para varrer e associar as guias geradas ao lote correspondente no banco local.

### 2.4 Reagendamento (Lote em Fila)
Se o lote ainda não estiver pronto:
- Cria um novo `Job` de rotina `"13_poll"` com os mesmos parâmetros e incrementa o contador `poll_attempt` para nova tentativa em 1 minuto.

## 3. Retorno
Retorna indicando se houve sincronia com sucesso no ciclo atual:
```json
{
    "self_persisted": true,
    "inserted": 0,
    "updated": 1, // Se finalizado e atualizado localmente
    "total": 1
}
```
