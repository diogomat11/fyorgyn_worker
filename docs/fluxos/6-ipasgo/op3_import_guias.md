# Rotina 3: Importação de Guias IPASGO (FacPlan - Localizar Procedimentos)

## 📌 Objetivo
Acessar a página `LocalizarProcedimentos` do portal FacPlan do IPASGO, limpar o formulário atual, aplicar filtros com base nos dados do Agendamento enviados pelo Dispatcher, listar as guias e coletar os procedimentos que encontram-se no status "Autorizado" ou "Em Estudo" processando e salvando de forma paginada no banco de dados.

## 🔀 Acesso à Plataforma e Gestão de Abas
O portal legado do IPASGO e o FacPlan (SPA Angular) rodam em infraestruturas e abas separadas:
1. Começamos a rotina lendo o ambiente de navegação. 
2. Caso já estejamos no Portal IPASGO logados via rotina Anterior (`op0`), o script busca entre todas as abas (`window_handles`) se a string `facplan` já consta carregada.
3. Se a aba não existe, abrimos via ação de navegação natural e trocamos o foco da janela ativa do Selenium para ela, apontando para `/GuiasTISS/LocalizarProcedimentos`.
4. Se o FacPlan redirecionar para Login por expiração, `op0` é re-ativado como contingência.

## 🛠 Lógica de Injeção de Filtros e Hierarquia (Knockout/Angular)
Os campos do formulário reativo não possuem IDs rígidos, mas são atrelados utilizando `data-bind` do framework KnockoutJS (ex: `attr:{ id: idIni }`). Os localizadores XPath primários na nossa base buscam primariamente por essa substring com a regra: `//input[contains(@data-bind, 'id...')].`

Para evitar concorrência e erro de limites do portal, uma rígida **Hierarquia Mutuamente Exclusiva** é aplicada no momento de limpar o formulário e injetar parâmetros do *Job*:

### 1. Pesquisa por Número da Guia (Prioridade Máxima) 🥇
- Se o Agendamento enviar o parâmetro `numero_guia`, **TODOS os demais campos são apagados na tela** usando um loop de `.clear()`. O sistema entende que a pesquisa é direta e focada.
- **Campos Limpos:** `carteira`, `dataInicio`, `dataFim`.
- **Campo Preenchido:** `numero_guia`.

### 2. Pesquisa por Carteira + Intervalo de Datas 🥈
- Caso enviar a `carteira`, é mandatório existir um intervalo de datas junto no Job. Se não tiver, o bot aborta por segurança.
- A plataforma impõe limites (geralmente até 1 ano de intervalo com busca de carteirinha).
- **Campos Limpos:** `numero_guia`.
- **Campos Preenchidos:** `carteira` enviada do Job, `dataInicio` (convertida DD/MM/YYYY) e `dataFim` (convertida DD/MM/YYYY).

### 3. Pesquisa Apenas por Intervalo de Datas 🥉
- Processamento massivo de rotina diária sem guias específicas e sem pacientes atrelados.
- **Limitação do IPASGO:** Pesquisas puramente temporais sem carteirinha demandam um intervalo **máximo rigoroso de 30 dias** entre data inicial e final. 
- **Campos Limpos:** `numero_guia`, `carteira`.
- **Campos Preenchidos:** `dataInicio` e `dataFim`.

> *Nota de Interação: O Selenium aciona o comando `.clear()` nativo nos inputs da página para resetar os valores que já vêm preenchidos previamente pelo portal com "D-30".*

## 📜 Paginação e Coleta de Procedimentos (Extração de Dados)
1. **Acionamento:** Botão `Pesquisar` é disparado. Wait explícito de desaparecimento da cortina de bloqueio com _Spinner de Carregamento_ do Angular é ativado com tolerâncias amplas.
2. **Navegação na DOM:** 
   - Ao invés de usar `table > tr`, a listagem das guias é feita em uma complexa árvore de *CSS grid/flex divs*.
   - A âncora principal de cada linha (iterador `i`) é: `//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]/div[{i}]`
3. **Extração Direta (Campos Visíveis na Linha `i`):**
   - **Paciente:** `.../div[2]/div[1]/div[1]/span`
   - **Cod. Beneficiário:** Extraído diretamente do texto interno (`.text`) do container `strong` do Paciente.
   - **Guia:** `.../div[2]/div[2]/div/div[2]/div[1]/div[1]/span`
   - **Senha:** `.../div[2]/div[2]/div/div[2]/div[1]/div[3]/span`
   - **Situação:** `.../div[2]/div[2]/div/div[2]/div[2]/div[3]/span`
   - **Data Solicitação:** `.../div[2]/div[2]/div/div[2]/div[2]/div[4]/span`
   - **Data Autorização:** `.../div[2]/div[2]/div/div[2]/div[1]/div[4]/span`
   - **Cod. Procedimento:** `.../div[2]/div[2]/div/div[1]/div/div[2]/div/div/div`
4. **Extração Indireta por Popup (Detalhes Adicionais):**
   - Como *Qtde Solicitada* e *Qtde Autorizada* não aparecem no card principal, o bot rastreia o ícone de detalhes: `.../div[2]/div[2]/div/div[1]/div/div[1]/div[2]/div/i[1]`.
   - Clica no botão e aciona o popup `detalhes-itens-guia-modal`.
   - Lê a mini-tabela (`tr[1]/td[2]` e `td[4]`) e aperta em Fechar.
5. **Commit por Página:**
   - Para extrema resiliência, caso o FacPlan caia na página 5 de 20, as 4 primeiras inserções no banco foram garantidas. Ao terminar todas as `rows` da página 1, ela é avaliada: apenas linhas concluídas e em estado _AUTORIZADO / EM ESTUDO_ são gravadas no banco do _Worker Local_. 
   - Apenas neste instante o Job aciona a lógica nativa de avanço (`click_next_page`).
6. Ao falhar em encontrar um botão próximo válido ou não transacionar o index da primeira guia rastreada, o Loop assume fim das páginas, consolida a lista principal e retorna ao Dispatcher.
