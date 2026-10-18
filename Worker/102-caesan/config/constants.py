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

# ── OP1: Autorização SP-SADT (índices conforme mapeamento do portal) ──
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

# ── OP1: Captura do número da solicitação após Gravar ──
# PENDÊNCIA: xpath oficial do frame de confirmação ainda não enviado.
# Candidatos best-effort (sweet-alert / modal / toast) — varridos em ordem.
X_RESULT_NUMERO_CANDIDATES = [
    '//div[contains(@class,"sweet-alert")]//h2',
    '//div[contains(@class,"sweet-alert")]//p',
    '//div[contains(@class,"modal")]//div[contains(@class,"modal-body")]',
    '//div[contains(@class,"toast")]',
    '//*[contains(@class,"alert")]',
]
RESULT_NUMERO_REGEX = r'(\d{5,10})'

# ── Anexos (padrão PADROES_ROTINAS §4.2) ──
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_ANEXO_BYTES = 5 * 1024 * 1024  # 5MB

# ── OP2: Webservice BIOS (ws2.bios.inf.br) ──
BIOS_WS_CODDAO_CONSULTA = 490
BIOS_WS_CHAVE = "W8"
BIOS_TIMEOUT_SEGUNDOS = 60
BIOS_TENTATIVAS = 3

# ── Identificação do integrador (envelope/logs) ──
ID_INTEGRADOR = 102
SIGLA_INTEGRADOR = "CAESAN"
