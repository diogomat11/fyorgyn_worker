# Fluxo Passo a Passo: Rotina 1 (Consulta) - Unimed Anápolis

**Objetivo:** Executar de maneira enfileirada a verificação das guias de exames de uma *Carteirinha* na base do SGUCard, e armazenar os dados crus retornados para uso das fases posteriores de autorização e execução (op2 e op3).

## 1. Navegação Base até Fila SADTs
1. **Verificação Inicial:** O sistema checa se a rota visual de Menu (`MENU_CENTRO_61`) está disposta na tela. Caso sim, clica lá primeiro (Dashboard principal).
2. **Entrada de Operação:** Clica em Autorizador (`MENU_ITEM_2`).
3. **Manejo de Janelas:** Fecha compulsivamente quaisquer popups abertos inesperados sem interação, focando sempre na janela principal `[0]`.
4. **Listagem:** Clica no sub-menu de "SADTs em aberto" de seletor `#centro_3 .MagnetoSubMenuTittle`. Aguarda 3 segundos.

## 2. Invocação da Biometria e Identificação do Paciente
1. Mapeia a presença do formulário com botões de biometria ou clique em "Novo Exame".
2. **Nova Janela:** O SGUCard costuma abrir um visualizador em PopUp com inputs embutidos quando clica-se em Novo Exame. O foco do web scraper é mudado rigorosamente para a última janela abrida (`handles[-1]`).
3. O código da carteirinha enviada pelo Hub é particionado em sub-múltiplos: `x1`(4 char), `x2`(4), `x3`(6), `x4`(2), `x5`(Restante).
4. Clica-se em Ignorar Leitor de Cartão Biométrico (`//*[@id="ignora-cartao"]`).
5. Abre o Cadastro de Beneficiários e inicia os preenchimentos parciais:
    - O prefixo da carteira `x1` entra no campo Input `[1]`.
    - Clica no `<input>` Master de benefício e despacha o restante dos campos numéricos consolidados (`x2+x3+x4+x5`).
6. Clica em Verificar.

## 3. Validação Preventiva da Carteirinha
- Cria-se um loop inteligente de espera dinâmica de "Smart Wait" por até 5 segundos procurando dois indicadores de bloqueio na interface Web:
  1. *Javascript Alert*: Tenta capturar avisos JS no navegador com textos sobrepondo "inválido", "dígito" ou "carteira".
  2. *Retorno HTML Típico*: Lê a resposta `<td/>` de erro, avaliando strings como "invalido", etc.
  3. Caso encare erro, o sistema abortará e lançará um **PermanentError**: Não retenta mais de forma orgânica, impedindo processamento zumbi de credencial inoperante.

- **Fluxo Condicional de Atualização de Cliente Externo:** O sistema analisa a variável `x1`. Se **não for Unimed local (exemplo diferente de prefixo 0178)**: 
    - Ele pode clicar e dar check em botões adicionais para puxar base e atualizar na Anápolis, chamados `Button_Update` ou `Button_Insert`. O bot dá até dois cliques se ele não carregar a resposta pra forçar o sync do site inter-unimeds.

## 4. Raspagem de Guias pela Tabela (Formulário `conteudo-submenu`)
1. Aguarda aparecer a lista de exames/guias e confirma a validade pela extensão total das `<tr/>` na table. Caso seja `len(1)` o paciente não possui guias.
2. **Ordenação Temporal:**
   - Clica sobre a aba superior listada pela Label **"SOLICITA" ou "DATA"**.
   - O SGUCard dá PostBack.
   - O Bot recalcula a página, acha a coluna de novo e dá um SEGUNDO clique, forçando em vez do crescente forçar "Mais Recentes para Trás".
3. **Leitura Paginada:**
   - Entra num Loop que processará linhas contendo Status Válidos: `AUTORIZADO`, `EM ESTUDO`, ou similares, categorizando com tags para o Banco do AgendaHub.
   - Existe uma Restrinção Rigorosa temporal: guias mais velhas que `180` dias (calculado em tempo real com `datetime`) abortam a busca imediatamente da listagem.
   - Pós Validação, o WebScraper entra profundamente no "Detalhe" clicando no link âncora `<a>` da guia correspondente. Confere excessão interna de `label_error_redeAtendPrestEspec` (Negado por Rede restrita sem Autorização prévia).
   - Extrai na visualização de detalhes as faturas, senha, cod de validade, qtd solicitada, etc, e clica em **Voltar**.
   - Interage com botão de texto `"Próxima"` na Footer da página se houver mais de uma aba de registros.
   
## 5. Acabamento
- Consolida o log interno. Associa esse array imenso ao modelo de dados do Hub. Fecha a janela do Popup biométrico remanescente e aloca o fluxo no index do WebBrowser, pronto pro Dispatcher concluir como Trabalho `success`.
