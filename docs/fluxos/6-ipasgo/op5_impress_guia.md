# Fluxo Funcional e Arquitetura: Rotina 5 (Impressão de Guia) - IPASGO

**Objetivo:** Obter comprovante impresso da guia no portal IPASGO via Facplan de maneira resiliente e validada.

## 1. Princípios de Design (Padrão Sênior/PO)
- **Guard Clauses:** Verificações antecipadas de ausência de parâmetros e timeouts rápidos para falhar graciosamente (Fail Fast).
- **Espera Dinâmica (Explicit Waits):** Não há travamentos fixos não justificados; todos os elementos interativos aguardam presença e visibilidade no DOM via `WebDriverWait`.
- **Fallbacks Nativos:** Preferência absoluta por eventos sintéticos do navegador (`.click()`, `.clear()`), utilizando injeção Javascript (`execute_script`) primariamente para scrolls e apenas como último recurso de fallback.
- **Isolamento Constante (DRY):** XPaths sensíveis extraídos para `config.constants` para fácil manutenção. Isolamento nativo de abas.

## 2. Passo a Passo Funcional (Estado Atual)

### 2.1 Preparação
- Validação no Wrapper: Verifica se o job possui as chaves obrigatórias `numero_guia` e `numero_copias`.
- Login: Fluxo administrado nativamente pelo wrapper IPASGO (ver `op0_login.py`).

### 2.2 Navegação Inicial FacPlan
- **Navegação (Wait & Click):** Clica no link `X_FACPLAN_LINK` (`//*[@href, "facplan"]`).
- **Comutação de Aba (Switch To Window):** Identifica a nova aba gerada pelo FacPlan e joga o foco do Selenium `driver.switch_to.window`.
- **Carga de Interface:** Aguarda o carregamento Angular por meio de overlay/spinners não bloqueantes (`_wait_spinner_until_gone`).

### 2.3 Acesso Direto "Localizar Procedimentos"
- **Redirect Direto:** Navega para a URL limpa base (`/GuiaSpsadt/LocalizarProcedimentos`) caso aplicável ou interage com o Link em tela.
- **Fechamento de Modal:** Analisa sebreposição de aviso e envia Javascript Click (`button-1`) inclusive verificando Iframes `try/except`.

### 2.4 Limpeza de Filtros e Injeção (O Core do Search)
- **Âncora de Renderização (Estabilidade):** Espera pelo XPath estático e forte `/html/body/header/div[5]/h4/strong` e adiciona `2s` finais para liberação da Thread JS do Knouckout.
- **Carteira `beneficiario`:** Se o `<a>` class `remove` da carteira estiver presente, envia um `click()` com 1000ms de delay (Implementação Estilo VBA).
- **Guia `input-text-search`:** Encontra via XPath estrutural `.../input-text-search/div/div/div/input`, executa `.clear().send_keys(guia)`.
- **Datas `idIni` e `idFim`:** Varre inputs marcados usando targetings de `contains(@data-bind)` e excuta `.clear()`.
- **Botão Pesquisar:** Identificável globalmente por `//*[@id="localizar-procedimentos-btn"]`. 
  - **Prevenção ClickIntercepted:** Excuta Scroll Javascript `.scrollIntoView({block: 'center'})` e aguarda 500ms para alinhar à viewport. Dispara o nativo `.click()`.

### 2.5 Resposta e Transição de Aba (Impressão)
- **Spinner Handling:** Repete leitura de carregamento Angular atrelado a evento assincrono gerado pelo Pesquisar. Global Delay de 2s inserido de estabilidade final.
- **Scroll Tabela:** Executa Javascript para fazer rolagem forte da body para acionar renderings de lazy-load da malha tabela.
- **Acesso ao Ícone de Impressão:** Localiza o link ou ícone pelo targeting estrito `//*[@data-bind="css: CssImpressao(), click: $root.escolherRelatorio"]`. 
   - Recebe as mesmas rotinas de `.scrollIntoView`, tentativa de clique `.click()`, possuindo fallback js puro caso falhe no Event Listener nativo. 
- **Nova Aba "GuiaSpsadt" ou Relatório:** O clique gera instância de nova Aba para relatório do pdf.
- **Foco da Aba Impressão:** Foco repassado via `[-1]`.

### 2.6 Ação Nativa de Impressora
- **Ajustes:** Envio de comando css style de zoom de corpo para `90%` de adequação.
- **Comando do OS:** Repete `driver.execute_script("window.print();")` de acordo com a quantidade parametrizada de cópias. Aguardando 2s extras para Spool.
- **Tear-Down:** Fecha com `driver.close()` e retoma à viewport `[0/1]` finalizando o workflow retornando o Result Object `[sucesso: True]`.

## 3. Próximos Passos e Resiliência (Planejamento de Milestones)
Para mitigar quebras inteiriças por timeout da web durante um job local, e reuso do driver, a arquitetura receberá 3 blocos de marcos na execução (ver `implementation_plan.md`), não impactantes a este diagrama feliz, lidando exclusivamente para fluxos de exceção.
