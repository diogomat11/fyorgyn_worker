# Fluxo Passo a Passo: Rotina 4 (Exames Finalizados) - Unimed Goiânia

**Objetivo:** Extração massiva e detalhada das guias finalizadas (SADT) no portal SGURCard da Unimed Goiânia, com relatório de séries temporais de atendimento, resiliência de sessão, auto-recuperação e deduplicação idempotente no banco de dados (`faturamento_lotes`).

---

## 1. Autenticação e Navegação via Selenium
1. **Sessão Persistente no Navegador:** 
   - A rotina opera inteiramente através do `scraper.driver` (Selenium) para manter o contexto de sessão ativo.
   - Navega para a home do SGURCard e extrai as URLs dinâmicas com os respectivos `dynaHash` a partir do campo `jsonModulosSubmenu`.
2. **Localização do Menu:**
   - Navega para a URL da seção "Exames Finalizados" (`/cmagnet/exames/sadt/finalizadas.do?CD_MENU=...&dynaHash=...`).

---

## 2. Formulário de Filtro e Pesquisa
1. **Preenchimento dos Parâmetros:**
   - Preenche os campos `s_dt_ini` e `s_dt_fim` no formato `DD/MM/YYYY`.
   - Se informado, preenche o filtro opcional de número de guia `s_nr_guia`.
2. **Submissão:**
   - Executa a submissão do formulário `form.ajax-search-filters` e aguarda o carregamento da grid `table.MagnetoFormTABLE`.

---

## 3. Coleta e Paginação das Guias
1. **Extração das Linhas da Grid:**
   - Varre as células `td.MagnetoDataTD` identificando o código da guia (`cd_guia`), número da guia (`guia`), data de atendimento, carteirinha do beneficiário, nome do paciente e o hiperlink de detalhe `detalhe_url`.
2. **Paginação Avançada:**
   - Navega pelas páginas subsequentes buscando a âncora `MagnetoNavigatorLink` (ex.: "Próxima" / ">>").
   - Resolve URLs relativas utilizando `urllib.parse.urljoin` e mantém o `dynaHash` de navegação atualizado.

---

## 4. Extração do Detalhe das Guias (Resiliência & Retomada)
1. **Verificação de Itens Existentes:**
   - Se o parâmetro `id_lote` estiver associado, o robô consulta o banco de dados (`faturamento_lotes`) e pula automaticamente o acesso individual às guias cujos `detalheId`s já tenham sido gravados previamente.
2. **Heartbeat de Atividade (`touch_activity`):**
   - A cada guia processada, o robô notifica o `SeleniumManager`, garantindo que a rotina de limpeza de inatividade (`cleanup_idle`) não encerre o navegador em execuções longas.
3. **Resiliência e Auto-Recuperação de Sessão:**
   - Testa a saúde do robô via `_is_driver_alive(driver)`.
   - Caso o navegador caia ou a conexão seja recusada durante a varredura:
     1. Re-inicializa o ChromeDriver.
     2. Refaz o login no portal.
     3. Re-aplica os filtros da pesquisa.
     4. Retoma a extração **a partir do item exato que falhou**, sem reiniciar a coleta do zero.
4. **Extração de Dados Detalhados:**
   - Acessa a página de detalhe da guia e extrai:
     - `carteirinha` (normalizada, removendo nomes anexados).
     - `cod_procedimento`, `CID`, `data_nascimento`.
     - **Equipe Médica:** profissional, conselho, número de registro, UF e CBO.
     - **Séries Temporais:** lista de séries contendo `seq`, `data` e `hora` de realização.

---

## 5. Ingestão e Deduplicação no Backend Hub
1. **Criação Antecipada do `LoteConvenio`:**
   - Ao solicitar a rotina OP4, o Backend Hub garante a criação antecipada de um registro na tabela `lotes_convenio` (`id_convenio = 3`, `status = Aberto`, `cod_prestador`).
2. **Identificador Único (`detalheId`):**
   - Cada série temporal de uma guia gera um `detalhe_id` único no formato inteiro: `int(cd_guia + str(seq))` (ex.: `cd_guia = 68864313`, `seq = 1` $\rightarrow$ `detalhe_id = 688643131`).
3. **Idempotência no Banco de Dados:**
   - O backend realiza a deduplicação em memória (nível de payload) e verifica a existência prévia na tabela `faturamento_lotes`.
   - Insere apenas registros inéditos vinculados ao `id_lote` correspondente.
