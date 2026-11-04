# ============================================================
# CAESAN — Constantes do Integrador (id_integrador=102, convenio 16)
# Portal Prestador: https://www.caesan.com.br
# Webservice BIOS:  https://ws2.bios.inf.br/wsbios/service/V1
# ============================================================

# ── URLs ──
URL_LOGIN = "https://www.caesan.com.br/login-prestador/"
URL_SP_SADT = "https://www.caesan.com.br/sp-sadt/"
URL_CONSULTA_SOLICITACOES = "https://www.caesan.com.br/consultar-solicitacoes/"
BIOS_WS_URL = "https://ws2.bios.inf.br/wsbios/service/V1"
PORTAL_ORIGIN = "https://www.caesan.com.br"

# ── Timeouts (segundos) ──
SHORT_TIMEOUT = 5
DEFAULT_TIMEOUT = 20
LONG_TIMEOUT = 45

# ── OP0: Login ──
X_LOGIN_USUARIO = '//*[@id="usuario"]'
X_LOGIN_SENHA = '//*[@id="senha1"]'
X_LOGIN_BOTAO_ACESSAR = '/html/body/div[5]/div[2]/div[1]/button'
# Fallbacks genéricos caso o id mude no portal
X_LOGIN_USUARIO_FALLBACKS = [
    '//input[@id="usuario" or @name="usuario"]',
    '//input[contains(@placeholder,"usuá") or contains(@placeholder,"usa")]',
]
X_LOGIN_SENHA_FALLBACKS = [
    '//input[@id="senha1" or @name="senha1"]',
    '//input[@type="password"]',
]
X_LOGIN_BOTAO_FALLBACKS = [
    '//button[contains(.,"Acessar") or contains(.,"Entrar")]',
    '//button[@type="submit"]',
]

# ── OP1: Autorização SP-SADT ──
# ── MAPEAMENTO OFICIAL (extraído do HTML real do portal em produção, 2026-11-03;
# evidência em 102-caesan/debug/) ──
# O SP-SADT é um form AngularJS: os identificadores estáveis são os próprios
# ng-model/ng-click do portal (primeiro candidato de cada campo) — os xpaths
# absolutos do mapeamento original (divs numerados) ficam como fallback porque
# deslocam quando o portal insere wrappers (banner pós-login).
# Campos de data são input[type=text] (send_keys + TAB; Angular binda por evento).
X_DATA_SOLICITACAO_NG = "//input[@ng-model='objVO0481.dtpedido']"
X_SELECT_CARATER_NG = "//select[@ng-model='objVO0481.caratersolicitacao']"
X_INPUT_CARTEIRA_NG = "//input[@ng-model='objVO0481.codassociado']"
X_INPUT_NOMEBENEF_NG = "//input[@ng-model='usuario.nombeneficiario']"  # hidden: validação da carteira
X_SELECT_TIPO_ATEND_NG = "//select[@ng-model='objVO0481.tipoexame']"
X_SELECT_TIPO_CONSULTA_NG = "//select[@ng-model='objVO0481.codtipconsulta']"
X_SELECT_RECEM_NATO_NG = "//select[@ng-model='objVO0481.atendimentorn']"
X_SELECT_IND_ACIDENTE_NG = "//select[@ng-model='objVO0481.codindacidente']"
X_BOTAO_PROFISSIONAL_NG = "//button[@ng-click='ModalProfissional()']"
X_INPUT_BUSCA_PROF_NG = "//input[@ng-model='buscaProfissional']"
X_BOTAO_BUSCA_PROF_NG = "//button[@ng-click='buscaProfissionais()']"
X_LINHA_PROF_MODAL_NG = "//*[@id='modalProfissional']//table//tbody//tr[td]"  # ngRepeat todo in filteredTodos
X_INPUT_PROF_SELEC_NG = "//input[@ng-model='objVO0406.nome']"  # disabled: preenchido ao selecionar
X_DATA_ATENDIMENTO_NG = "//input[@ng-model='objVO0481.dtprovproc']"
X_INPUT_SECRETARIA_NG = "//input[@ng-model='objVO0481.secretsolic']"
X_TEXTAREA_JUSTIFICATIVA_NG = "//textarea[@ng-model='objVO0481.indicacao']"
X_SELECT_TABELA_NG = "//select[@ng-model='objVO0482.codtabela']"
X_INPUT_CODIGO_NG = "//input[@ng-model='objVO0482.codprocedimento']"
X_INPUT_QUANTIDADE_NG = "//input[@ng-model='objVO0482.qtdsolicitada']"
X_BOTAO_INCLUIR_NG = "//button[@ng-click='adicionarProcedimento()']"
X_INPUT_CAMINHO_DOC_NG = "//input[@ng-model='objVO0481.lstarquivos']"
X_BOTAO_GRAVAR_NG = "//button[@ng-click='gravarGuia()']"

# Values reais das options (ng-options — value='string:<codigo>'; extraídos do HTML):
VAL_CARATER_ELETIVO = "string:1"          # '1 - Eletivo'
VAL_TIPO_ATEND_OUTRAS_TERAPIAS = "string:03"  # 'Outras Terapias'
VAL_TIPO_CONSULTA = "string:4"            # 'Por encaminhamento' (option[2] do mapeamento original)
VAL_RECEM_NATO = "string:0"               # 'Não'
VAL_INDICACAO_ACIDENTE = "string:9"       # 'Não Acidente'
# Tabela: value = 'string:22' (Terapias Convencionais) | 'string:00' (Tabela Interna Caesan/Especiais)
TABELA_VALUE = {"22": "string:22", "00": "string:00"}

# ── Xpaths absolutos históricos (fallback — quebram se o layout deslocar divs) ──

# Xpaths absolutos históricos (fallback — quebram se o layout deslocar divs)
X_FORM_DATA_SOLICITACAO = '/html/body/div[5]/div[2]/div[2]/form/div[1]/input'
X_SELECT_CARATER = '/html/body/div[5]/div[2]/div[2]/form/div[2]/select'
X_OPTION_CARATER_ELETIVO = X_SELECT_CARATER + '/option[2]'
X_INPUT_CARTEIRA = '/html/body/div[5]/div[2]/div[2]/form/div[3]/input[1]'
X_SELECT_TIPO_ATENDIMENTO = '/html/body/div[5]/div[2]/div[2]/form/div[4]/select'
X_OPTION_TIPO_ATEND_OUTRAS_TERAPIAS = X_SELECT_TIPO_ATENDIMENTO + '/option[7]'
X_SELECT_TIPO_CONSULTA = '/html/body/div[5]/div[2]/div[2]/form/div[5]/select'
X_OPTION_TIPO_CONSULTA = X_SELECT_TIPO_CONSULTA + '/option[2]'
X_SELECT_RECEM_NATO = '/html/body/div[5]/div[2]/div[2]/form/div[6]/select'
X_OPTION_RECEM_NATO = X_SELECT_RECEM_NATO + '/option[2]'
X_SELECT_INDICACAO_ACIDENTE = '/html/body/div[5]/div[2]/div[2]/form/div[7]/select'
X_OPTION_INDICACAO_ACIDENTE = X_SELECT_INDICACAO_ACIDENTE + '/option[2]'
X_BOTAO_PROFISSIONAL = '/html/body/div[5]/div[2]/div[2]/form/div[8]/button'
X_MODAL_INPUT_NOME_PROFISSIONAL = '//*[@id="modalProfissional"]/div/div/div[2]/div/div/input'
X_MODAL_LINHA_PROFISSIONAL = '//*[@id="modalProfissional"]/div/div/div[2]/div/div[2]/table/tbody/tr/td[1]'
X_INPUT_DATA_ATENDIMENTO = '/html/body/div[5]/div[2]/div[2]/form/div[10]/input'
X_INPUT_SECRETARIA = '/html/body/div[5]/div[2]/div[2]/form/div[11]/input'
X_TEXTAREA_JUSTIFICATIVA = '/html/body/div[5]/div[2]/div[2]/form/div[13]/textarea'
# Nota: o mapeamento original apontava o select de tabela para o textarea da
# justificativa (div[13]); o select real é div[16]/div[1]/select (usado nas
# options de tabela mapeadas).
X_SELECT_TABELA = '/html/body/div[5]/div[2]/div[2]/form/div[16]/div[1]/select'
X_INPUT_CODIGO = '/html/body/div[5]/div[2]/div[2]/form/div[16]/div[2]/input'
X_INPUT_QUANTIDADE = '/html/body/div[5]/div[2]/div[2]/form/div[16]/div[3]/input'
X_BOTAO_INCLUIR = '/html/body/div[5]/div[2]/div[2]/form/div[17]/button'
X_INPUT_CAMINHO_DOC = '/html/body/div[5]/div[2]/div[2]/form/div[18]/div/div/input'
X_BOTAO_GRAVAR = '/html/body/div[5]/div[2]/div[2]/form/div[19]/button[2]'

# Índices das options (1-based no portal; converter p/ 0-base no Select)
IDX_CARATER_ELETIVO = 2
IDX_TIPO_ATEND_OUTRAS_TERAPIAS = 7
IDX_TIPO_CONSULTA = 2
IDX_RECEM_NATO = 2
IDX_INDICACAO_ACIDENTE = 2
# Tabela CAESAN → índice da option no select (1-based):
#   '22' = Terapias Convencionais (option 2) | '00' = Terapias Especiais (option 6)
TABELA_OPTION_INDEX = {"22": 2, "00": 6}

# Valor fixo do campo secretaria (padrão Evoluir)
SECRETARIA_PADRAO = "JANAINA"

# Modal de confirmação #alerta (sucesso — xpath oficial do cliente) e #alertafalha (erro)
X_ALERTA_FALHA = '//*[@id="alertafalha"]//div[contains(@class,"modal-body")]'

# ── OP1: Captura do número da solicitação após Gravar ──
# Xpath oficial do campo de confirmação do portal:
#   "Guia gravada com sucesso - número da guia: 892706"
X_RESULT_NUMERO_OFICIAL = '//*[@id="alerta"]/div/div/div[2]/p'
# Fallbacks best-effort (sweet-alert / modal / toast) — varridos em ordem
# caso o bloco oficial não esteja presente.
X_RESULT_NUMERO_CANDIDATES = [
    X_RESULT_NUMERO_OFICIAL,
    '//*[@id="alerta"]//p',
    '//div[contains(@class,"sweet-alert")]//h2',
    '//div[contains(@class,"sweet-alert")]//p',
    '//div[contains(@class,"modal")]//div[contains(@class,"modal-body")]',
    '//div[contains(@class,"toast")]',
    '//*[contains(@class,"alert")]',
]
RESULT_NUMERO_REGEX = r'(\d{5,10})'

# ── OP1: Validação de Datas, Pacing Passo a Passo e Procedimentos (AngularJS) ──
REGEX_DATA_DDMMAAAA = r'^\d{2}/\d{2}/\d{4}$'
REGEX_DATA_ISO = r'^\d{4}-\d{2}-\d{2}$'
ITEM_DESCRICAO_TIMEOUT = 15
ITEM_INCLUIR_TIMEOUT = 10
PAUSA_PASSO_FORM = 0.8
PAUSA_PRE_INCLUIR_ITEM = 2.0
PAUSA_POS_INCLUIR_ITEM = 2.5
PAUSA_POS_ANEXO = 2.5
PAUSA_PRE_GRAVAR_PADRAO = 2.0
X_LINHAS_PROCEDIMENTOS_TABELA = "//table//tbody//tr[contains(@ng-repeat,'objVO0481.procedimentos')] | //section[contains(.,'Procedimento(s) TUSS')]/following-sibling::table[1]//tbody//tr[td]"

# ── Anexos (padrão PADROES_ROTINAS §4.2) ──
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_ANEXO_BYTES = 5 * 1024 * 1024  # 5MB

# ── OP2 / Consultas BIOS: Webservice BIOS (ws2.bios.inf.br) ──
BIOS_WS_CODDAO_CONSULTA = 490
BIOS_WS_CODDAO_PENDENTES = 544
BIOS_WS_CODDAO_AUTORIZADAS = 560
BIOS_WS_CHAVE = "W8"
BIOS_TIMEOUT_SEGUNDOS = 60
BIOS_TENTATIVAS = 3

# ── Identificação do integrador (envelope/logs) ──
ID_INTEGRADOR = 102
SIGLA_INTEGRADOR = "CAESAN"
