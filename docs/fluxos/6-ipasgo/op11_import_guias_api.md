# Fluxo Funcional e Arquitetura: Rotina 11 (Importação de Guias API) - IPASGO

**Objetivo:** Extrair guias do IPASGO (Facplan) utilizando chamadas HTTP diretas (API) no lugar de varredura de interface via Selenium, proporcionando extrema velocidade e resiliência, e populando os dados consolidados no banco de dados.

## 1. Princípios de Design
- **Reaproveitamento de Sessão (Cookies):** A rotina se beneficia do fluxo de login (OP0) que já autenticou o Chrome. Os cookies são extraídos do navegador gerenciado pelo Selenium e repassados para a classe `WebPlanClient` (em `core/webplan_client.py`), que executa as requisições nativas de HTTP.
- **Navegação Bootstrap:** Antes de disparar as chamadas JSON, o Selenium navega até a rota base (`/GuiasTISS/LocalizarProcedimentos`) para que o Angular (no frontend original do Facplan) carregue eventuais tokens de validação na sessão. Os modais/notificações também são fechados preventivamente caso apareçam.
- **Extração Total via Paginação:** A rotina laça as requisições do endpoint `/LocalizarProcedimentos/Localizar` iterando as páginas (`page=1`, `page=2`, etc.) até a API retornar um array vazio de procedimentos.

## 2. Passo a Passo Funcional

### 2.1 Preparação e Inicialização
- **Parâmetros:** O Job extrai os parâmetros `guia`, `codigo_prestador`, `data_ini`, `data_fim`, `carteira`, `codigo_beneficiario`, `situacao`. Se for modo "Total", ignora datas pré-configuradas e foca no mês todo.
- **Login e Bootstrap:** 
  - Abre a tela base (`LocalizarProcedimentos`).
  - Lida com pop-ups e *noty_text* repetindo a lógica robusta usada em OPs de navegação (`_close_notification_robust`).
- **Injeção do Client HTTP:** 
  - Instancia `WebPlanClient(driver)`. O `WebPlanClient` consome os cookies do driver para montar o objeto de Requests do Python.

### 2.2 Consulta API Paginada
- O script realiza um laço `while has_next_page:` acessando o endpoint `POST /LocalizarProcedimentos/Localizar`.
- Envia os parâmetros traduzidos do modelo interno da clínica para o payload JSON do Facplan (ex: datas formatadas, e uso de strings vazias para parâmetros omitidos).
- Ao receber a resposta, o JSON é desmembrado. O array raiz chama-se `Procedimentos`. Cada procedimento pode possuir múltiplos `Itens`.

### 2.3 Normalização de Dados (Data Transformation)
Para evitar duplicação ou falta de informações críticas, a OP11 converte os nós da API no seguinte esquema relacional:
- **Campos Raiz:** Extrai `NumeroGuiaOperadora`, `NumeroGuiaPrestador`, `Situacao` ou `SituacaoTiss`, dados de autorização e de beneficiário (`CodigoBenficiario`, `NomeBeneficiario`).
- **Validação de Senha (`necessita_senha`):** Calculado com a regra de negócio do convênio: Se a situação for "Autorizado", "Liberado" ou "Parcialmente autorizada" **E** não houver senha no sistema (`HasSenha=False`), marca `necessita_senha=True`.
- **Granularidade por Procedimento (Terapia):**
  - O array de `Itens` internos da guia é agrupado de acordo com o `CodigoAMB` (tipo da terapia, p. ex., "0.00.40.04-5").
  - Cada grupo único gera **uma linha** de saída para o banco. O código AMB é higienizado (`_normalizar_codigo`) removendo pontos e traços.
  - Soma as quantidades baseadas na quantidade total de itens (sessões solicitadas) e quantos deles têm status `"Autorizado"` (sessões autorizadas).

### 2.4 Persistência e Retorno (Isolamento Multitenant)
- Todos os registros normalizados entram em uma matriz `todas_guias_extraidas`.
- A função interna `_save_rows_local` faz a persistência usando `SessionLocal()` do SQLAlchemy, aplicando regras estritas de isolamento por `user_id` (prestador logado):
  - **Identificação do Proprietário:** O parâmetro `job_user_id` é repassado no salvamento de cada registro da tabela `BaseGuia`.
  - **Verificação Global de Conflito de Chave Única:** A busca por registros existentes é feita de forma global (sem restringir a query por `user_id` no filtro do banco de dados). Isso garante que o sistema identifique se a guia já pertence a outro usuário antes de tentar gravá-la.
  - **Adoção e Proteção (Regras de Propriedade):**
    - Se a guia **não existir**: é criada uma nova associada ao `user_id` do job atual.
    - Se a guia **existir e estiver órfã** (`user_id` nulo): o sistema a adota, associando `user_id = job_user_id`.
    - Se a guia **existir e pertencer a outro usuário** (`user_id != job_user_id`): a gravação e modificação são puladas (ignoradas) e um alerta é registrado no log. Isso impede vazamento ou modificações cruzadas de guias de terceiros (cross-tenant leak).
  - **Vínculo de Carteirinhas:** O relacionamento com a tabela `Carteirinha` é restrito pelo `user_id`. Uma carteirinha só é vinculada à guia se ambas pertencerem ao mesmo `user_id` do prestador ativo.
- Ao final, retorna ao dispatcher `todas_guias_extraidas`, o qual efetuará a gravação na API central (Supabase) sob o contexto exclusivo de segurança do `user_id` do job correspondente.
