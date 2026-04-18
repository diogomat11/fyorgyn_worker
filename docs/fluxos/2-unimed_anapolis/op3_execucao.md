# Fluxo Passo a Passo: Rotina 3 (Execução/Faturamento) - Unimed Anápolis

**Objetivo:** Consolidar a baixa integral da guia em posse da fatura e vinculação do profissional clínico com exatidão da Carga Horária e procedimentos, efetivando o ato assistencial.
*Nota: Requisito Crítico do Job - A Captura (Rotina 2) DEVE obrigatoriamente ter transitado no status de Success, sendo travado internamente via ID no Queue Manager do Dispatcher.*

## 1. Entrada do Procedimento Execural
- Assegura-se de fechar lixos visuais do browser.
- Entra no Menu da Interface > Autorizador > SADTs abertos conforme a OP2.
- Aciona a caixa Global de Busca pela Variável `numero_guia` passada pelo payload de Job do back-end. Confirma presença da guia isolada perfeitamente visível.

## 2. Parâmetros do Atendimento
1. Com a guia achada, clica no ID em Link Hipertexto para detalhar.
2. Aguarda carrego sincrônico do formulário completo de Guia SP/SADT.
3. No Menu Dropdown HTML de Tipo de Atendimento (`DM_TP_ATEND_SADT`): Localizar e assinar visivelmente `"03 - Outras Terapias"`.
4. No Menu Regime de Atendimento (`DM_REGIME_ATEND`): Localiza e marca a Tag `"01 - Ambulatorial"`.
5. Procura-se pelo campo de data e hora do serviço `dt_serie_1`. O sistema limpa, força clique de mouse, empurra os atalhos de strings passados da agenda no layout de `"dd/mm/aaaa hh:mm"`.
6. Termina a triagem Base pressionando o botão Action Formulario: `Button_Gravar`. O Driver processará eventuais Alertas.

## 3. Vínculo do Médico e do Conselho
1. Volta-se a tela base da edição e Clica-se no Ícone de Vínculo de Profissional, o qual na Anápolis, é apontado estaticamente na malha CSS `.grid-menu:nth-child(1) img` da tabela.
2. Na nova view da malha, clica no botão redondo lateral indicativo de "Nova Participação".
3. Identifica e seleciona a Lupa em desenho vector "Localizar Prestador" abrindo via SGUCard uma **Segunda Aba / Janela** do Navegador em Fundo de Operação.
4. **Window Focus Switch:** Transfere controle de Driver diretamente à segunda PopUp.
5. Usa-se a Label passada em `nome_profissional`, limpando e escrevendo no input "Buscar Prestador" `s_nm_prestador`.
6. **Parse do Conselho**: O Conselho Clínico vindo pela API (Ex: `CRP`) é mapeado a Label extensa pelo Scraper. Preenche-se em Select a option correspondente ao `conselho`. E clica na Categoria Exata de Busca Textual contendo: *"Prestador Externo"*.
7. Efetua a filtragem (`Button_DoSearch`).

## 4. Escolha Visual do Resultado de Identidade Clínico
1. A Lupa lista resultados e o webScraper é construído simulando uma procura exata nos seletores em grade:
   - Ele rastreia se nos atributos HTML existirá tag metadata `<a data-nm-prest="NOME">`, ou clica rudemente no iterador via fallback XPath em `tr[3]/td[2]/a`.
2. O click efetuado fará com que o Script da PopUp se *Auto Destrua/Feche*.
3. Ejetado de forma forçada, o Worker se redireciona compulsoriamente pra `janela[0]` inicial da Edição para validar cadastro, contornando travas do Chromedriver.

## 5. Especificações Procedimentais Clínicas Finais
1. Efetua a ação clique no componente "Cadastrar" Botão Insert da View.
2. Em Título/Grau de Participação (`DM_GRAU_PARTIC_1`) define o cargo do médico usando match em `"12 - Clínico"`.
3. Informa no Combo Box (`NR_SEQ_ITEM_1`) buscando exato correspondente interno advindo da requisição em Web para o campo `cod_procedimento_fat` do tipo Procedimentos Clínicos do Agendamento. (Ex: `"2250005170"`).
4. Clica em enviar (`Button_Submit`) Gravar Ficha.

## 6. O Fechamento Definitivo ("Finalizar Parcial")
1. Clica de novo no Header da Guia, em `"Dados da Guia SP/SADT"`.
2. Aguarda processar view state.
3. Aciona ação principal do Layout: `"Finalizar Parcial"` (`Button_Parcial`).
4. **Verificador do JS Alerta / PopUp Nativo Avançado**: 
   - A operadora SGUCard invoca janela estática ou modal de *Confirmação Final*. 
   - O Driver tentará ir pra Window -1. Sendo janela nativa acha-a e aciona em fim o famoso botão final com id de `'btn_confirmar'`.
   - Se for DOM falso (Ajax modal), o scraper usa except pra se atrelar ao id DOM root `btn_confirmar` original na mesma janela que estava.
5. Se esse clique não lançar Panic Errors na Console do WebDriver, a baixa faturação terá sua confirmação de recebimento assinada. O banco do Agenda Hub receberá na coluna `executado_status` a menção de "sucesso". Termina job.
