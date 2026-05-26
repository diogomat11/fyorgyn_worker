# Fluxo Passo a Passo: Rotina 1 (Consulta) - Unimed Goiânia

**Objetivo:** Similar à Unimed Anápolis, é a vistoria massiva dos pedidos atrelados à conta (Carteirinha) de um titular Goiano no banco do SGUCard, e listagem das referidas pendencias faturais.

## 1. Requisição Biometrica Base (Emulação do Applets)
1. O Bot de Goiânia pula o roteamento de Abas HTML, ele clica objetivamente e direto no ícone verde/botão visual global para Cadastro Eletrônico (ID Genérico `#cadastro_biometria > div > div[2] > span`), na esperança de levantar os popups sem usar as rotas `centro_xx`.
2. Após clicar, chaveia seu Driver Focus para o frame emergente `handles[-1]` e infla o Display.

## 2. Padrão Goiano de Digitação Expresso da Carteirinha (Scripts Form)
1. A Formatação da var `carteirinha` não depende unicamente do SubString clássico, e sim de uma operação RegEx partindo sobre delimitadores textuais (`.` ou `-`). Retornando as exatas 5 partes.
2. Com o intuito de bypassar mecanismos visuais de Goiania e o bloqueio de readonly nos campos, o script executa 3 comandos diretos Javascript Inject transformando os inputs em máscaras literais (`type=text`): `nr_via`, `DS_CARTAO` e `CD_DEPENDENCIA`.
3. Dispara as combinações fracionadas no modelo antigo para a página através dos 3 textfields.
4. **Verificador de Filial:** Se o radical da carteirinha (primeiros 4 números) for distinto de `"0064"`, ele ativará um clique compulsório no botão Validar/Consultar de ID `Button_Consulta` da GUI.

## 3. Mineração da Tabela e Paginação
1. O robô se atraca ao Grid primário HTML de visualização pelas colunas `#s_NR_GUIA`. Trocando a espera de "Conteúdo-Submenu" pela presença concreta na lista gerada no Front-end de Resultados de Goiânia.

2. **Ordenação Temporal:**
   - Efetua clique duplo sucessivo na coluna `"SOLICITAÇÃO"` / `"DATA"`.
   - Adicionando *Dealy* mais prolongado entre sub-cliques da header na versão Goiana (aguardando os Fetchs paralelos - 4 a 3 secundos). 
   - Objetivo: Forçar o descendente (mais novo em cima).

3. **Loop de Varredura Visual Paginada:**
   - Varre `tr` após `tr`. Confirma através da label contida em `/td[6]/span` (com o texto puro na prop text="Autorizado") se a guia é executável.
   - Ponto Diferencial: Verifica corte de Tempo de Vida esticado para as GUIAS autorizadas via `[1]` data HTML. Guias anteriores a marca limite de `"270"` (duzentos e setenta) **Dias** forçam Break e Parada total no sistema (Não captura, cancela script da guia corrente e volta para Menu). 
   - A extração aprofundada ocorre adentrando no hiperlink (`td[4]/a`), baixando dados detalhados (data, senha autorizada, código da Carga). 
   - Desvia das armadilhas da Tabela que fecham a Popup precocemente com um fall-back em JS `history.go(-1)`.

4. **Paginação e Persistência Multitenant:**
    - Usa uma lógica persistentemente estruturada de avanço para a página sub-sequente ao caçar a âncora HTML `Próxima`, submetendo a mesa HTML a um novo Fetch via AJAX. No fim do fluxo o Bot destrói o manipulador e retorna à página Web root.
    - **Regras de Persistência Multitenant no Dispatcher:**
      - O salvamento na central (e no banco do worker) associa todas as guias e logs resultantes ao `user_id` correspondente ao criador do job.
      - **Verificação Global de Guias Existentes:** Busca registros por número de guia e convênio globalmente para evitar duplicidades em chaves únicas.
      - **Adoção e Proteção (Regras de Propriedade):**
        - Se a guia não existir, ela é inserida vinculando o `user_id` do job.
        - Se a guia existir e estiver sem proprietário (`user_id` nulo), o sistema a adota, associando `user_id = job_user_id`.
        - Se a guia existir e pertencer a outro usuário (`user_id != job_user_id`), o processamento é ignorado e um aviso é gerado nos logs locais, prevenindo mutações indesejadas em dados de terceiros (cross-tenant leak).
      - **Isolamento de Carteirinhas:** O relacionamento com a tabela `Carteirinha` é isolado de forma que a associação da carteirinha com a guia só ocorra se ambas pertencerem ao mesmo `user_id` do prestador logado.
