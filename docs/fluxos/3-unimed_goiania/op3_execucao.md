# Fluxo Passo a Passo: Rotina 3 (Execução/Faturamento) - Unimed Goiânia

**Objetivo:** Consolidar a fatura, assim como o Anápolis, executando as guias de procedência. As maiores diferenças residem no gerenciamento Web do Scraper frente ao Formulário e restrições de tempo para fechar as sessões de Guias abertas ou exauridas em captura da praça Goiania.

## 1. Barreiras de Entrada Precoce (Segurança Timeout via BD)
1. Antes do Robot carregar qualquer pacote Visual Selenium, ele interage na Raiz com o Banco SQL interno do Agendahub apontando o `GuiaBase` do número atrelado. 
2. Ele retira e lê a Propriedade de `"timestamp_captura"`. Analisa a regra de expiração com uma janela estressante local: *"Falta Menos de 2 minutos para esbarrar nos 59 Minutos pre-estipulados pela Unimed da Data Guardada?"*.
3. Se o limite estiver violado:
   - Limpa o rastro com `None` no banco para dar clear.
   - Levanta Request HTTP Rest na API Backend URL Central para Retro-Requisitar reexecução forçada da referida **Captura (op2)** com nova fila encadeada (`depending_id`).  
   - Suicida esse Job momentâneo para ele migrar pra `Adiado` até reescrever na Rede.

## 2. Inserção Procedimental
1. Clica e procura a mesma interface "Detalhamento" de Guia Anápolis.
2. Com o Form exposto, seleciona Categoria Dropdown ("03") e Regime Tipo Ambulatorial ("01").
3. **Ponto Crítico de Manipulação Dom-JS**: Na interface legada Goiana, frequentemente as Views travam (bloqueio web de `Data`). O WebScraper injeta dinamicamente o Snippet JavaScript via Motor do Chromium para apagar forçadamente do Inspecionar Elementos do input Data 2 Atributos nativos: `readonly` e `disabled`. Apenas então enviando as Chaves via SendText das Datas (`data_hora`).
4. **Ausência da Ação Base - Omissão Voluntária**: Em contraponto Anápolis, onde salva-se esse bloco, A Rotina Goiania propositalmente aborta o Click no Form action de id `Button_Gravar`. Deixando livre processamento em bloco posterior unificado de Salvamento nativo sem Refreshing de PopUps chatas.

## 3. Vínculo Clínico Profissional
1. Pressiona via Seletor HTML e XPath único do portal Goiano o Lápis de Vínculo: `//*[@id="1"]/td[15]/span/a/span`.
2. Diferenciando-se das rotinas de teste comuns, a operação implanta Teste Físico para avaliar Janelas Modais contendo Exceções enviadas pela própria SGU (Ex: CRM bloqueados, Erros sistêmicos). Procura pela `<div>` `//*[@id="msgs_conf_consulta"]/div[2]`. Caso possua Label Text, a Exception vira Crítica lançando falha "Erro de negócio" nos logs. 
3. Caso sadio, avança pra clicar e abrir a View de Procura em Botões Circulares ("Nova Participação").
4. Engatilha Lupa "Localizar Profissional", desprendendo nova tela de popup em Front de Abertura `handles+1`.
5. Digita a Identidade em Substring Text (`s_nm_prestador`). Converte via prefixos de array de Conselho regional o ID numérico listável "CREFITO / CRP / CRM" através da Option Form no campo `<SELECT>` HTML correspondente.
6. Adiciona Tag Restrita `"Prestador Externo"` e aciona Filter Search Global. 
7. Encontra Listagem do retorno da Interface: Acessa e confia primariamente nas tags escondidas meta HTML  `<a data-nm-prest="NOME ALVO">`. Caso inoperante caça na Raiz rudimentar pela `tr[3]/td[2]/A_href`. 
8. Confirma seleção fechando visualização em popup instantâneo. Puxa e restabelece a visão no Root.
9. Cadastra Grau via Select ID Interno (`"12"`) para Classificação em Consultório/Geral. E Adiciona Codificação Bruta do Item Faturamento correspondente. Aciona Confirm/Submit do Processo para salvar a Etapa 3.

## 4. O Fechamento Definitivo ("Finalizar Parcial")
1. Clica em Voltar pra "Dados da Guia SP/SADT". 
2. Realiza o disparo final em Action do Botão `Button_Parcial` ativando o encerramento do pacote final pra pagamento pela Unimed.
3. Busca ou por tela Subsequente Modadal, ou mesmo na folha original de formulário da view atual o botão Confirmar Assinatura (`btn_confirmar`). Desativa Alertas e atualiza Banco pra "sucesso"!
