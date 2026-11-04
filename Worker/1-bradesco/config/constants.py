# ============================================
# BRADESCO - CONFIG / CONSTANTS.PY
# XPaths e seletores do portal Polimed/Orizon
# ============================================

# ===========================
# LOGIN PAGE (Polimed/Orizon)
# ===========================
LOGIN_FIELD_USERNAME = 'usuario.login'   # Seletor: name="usuario.login"
LOGIN_FIELD_PASSWORD_ID = 'senha'        # Seletor: id="senha"
LOGIN_BUTTON_XPATH = "//*[@id='formLogin']/button"

# ===========================
# OP1 - SOLICITAR AUTORIZAÇÃO SADT
# ===========================

# Seleção de operadora
X_SELECT_EMS = "//*[@id='select_Ems']"

# Dados do beneficiário
X_RADIO_CARTEIRA = "radio_carteira"  # id
X_INPUT_CARTEIRA = "//*[@id='numeroCarteiraBeneficiario']"

# Atendimento RN
X_ATENDIMENTO_RN_NAO = "//*[@id='atendimentoRN']/option[2]"

# Contratado solicitante
X_TIPO_CONTRATADO_SOLICITANTE_ID = "tipoContratadoSolicitante"
X_TIPO_CONTRATADO_OPT_COD_OPERADORA = "//*[@id='tipoContratadoSolicitante']/option[5]"
X_CODIGO_OPERADORA_ID = "codigoOperadora"

# Profissional solicitante
X_NOME_PROFISSIONAL_ID = "nomeProfissionalSolicitante"
X_CONSELHO_PROFISSIONAL_ID = "siglaConselhoProfissionalSolicitante"
X_NUMERO_CONSELHO_ID = "numeroConselhoProfissionalSolicitante"
X_UF_CONSELHO_ID = "ufConselhoProfissionalSolicitante"
X_CBO_PROFISSIONAL_ID = "CBOSprofissionalSolicitante"

# Caráter e CID
X_RADIO_ELETIVA = "//*[@id='radioCaraterSolicitacaoEletiva']"
X_IMG_PESQUISA_CID_ID = "imgPesquisaCid"

# Popup CID10
X_CID_DESCRICAO_ID = "descricao"
X_CID_BTN_PESQUISAR = "//*[@id='formCids']/table/tbody/tr[4]/td/table[1]/tbody/tr/td[3]/input"
X_CID_PRIMEIRO_RESULTADO = "//*[@id='tabelaDeCids']/tbody/tr[2]/td[1]/a"

# Tipo atendimento
X_TIPO_ATENDIMENTO_PEQUENOS = "//*[@id='tipoAtendimento']/option[4]"
X_TIPO_ATENDIMENTO_TERAPIAS = "//*[@id='tipoAtendimento']/option[8]"

# Regime e Acidente
X_REGIME_ATENDIMENTO = "//*[@id='regimeAtendimento']/option[3]"
X_INDICADOR_ACIDENTE = "//*[@id='indicadorAcidente']/option[2]"

# Prestador executante
X_MATRICULA_EXECUTANTE_ID = "matriculaPrestadorContratadoExecutante"

# Procedimento
X_CODIGO_PROCEDIMENTO_ID = "codigoProcedimento"
X_QTD_PROCEDIMENTO_ID = "quantidadeProcedimento"

# Upload
X_UPLOAD_CONTAINER_ID = "tdUploadArquivo"
X_INPUT_FILE_ID = "inputFile0"
X_TIPO_ARQUIVO_OPT = "//*[@id='tipoArquivo']/option[4]"
X_BTN_ANEXAR_ID = "btnAnexarSadt"

# Envio
X_INDICACAO_CLINICA_ID = "indicacaoClinica"
X_BTN_ENVIAR_ID = "enviar"

# Retorno (janela resultado)
X_GUIA_PRESTADOR = "/html/body/table[2]/tbody/tr[4]/td/table/tbody/tr[9]/td[2]/label"
X_STATUS_PROCEDIMENTO_ID = "status_procedimento_descricao_1"

# ===========================
# REGISTRO ANS - Bradesco
# ===========================
REGISTRO_ANS_OPTIONS = ["005711", "421715"]

# ===========================
# OP1 FATURE - CONSULTA DE GUIAS (GetGuiasLote) — PO 2026-10-21
# Cascata reg_ans × status_guia + timeouts em camadas
# ===========================
FATURE_API_BASE = "https://rest-guia-fature-apicast-production.api.ocppr.orizon.com.br/api"
FATURE_OPERADORA_ID = 48
# Ordem de tentativa por status: prioriza 5 (faturada/exportada), depois os demais
FATURE_STATUS_GUIA_ORDEM = [5, 101, 102, 103, 4, 3, 403]
# REG ANS alternativo quando o do job não localiza (Bradesco Nacional 5711 / Saúde 421715)
FATURE_REG_ANS_FALLBACK = ["421715"]
# Timeout do fetch DENTRO do navegador (AbortController cancela o GET → status 0)
FATURE_FETCH_TIMEOUT_S = 20
# Timeout do Selenium esperando o callback do JS — SEMPRE maior que o fetch timeout
FATURE_SCRIPT_TIMEOUT_S = 30
# Retentativas por request em erro transiente (rede/429/5xx), com backoff 2s
FATURE_FETCH_RETRIES = 1
# Pausa entre requests da cascata (anti-429)
FATURE_THROTTLE_S = 0.5

# ===========================
# COD_PRESTADOR por área
# ===========================
COD_PRESTADOR_MAP = {
    "pequenos atendimentos": "935102",   # Psicologia, Fonoaudiologia
    "TERAPIAS": "902446",                # TO, Fisioterapia, Psicomotricidade
}

# ===========================
# TIMEOUTS
# ===========================
DEFAULT_TIMEOUT = 20
LONG_TIMEOUT = 45
SHORT_TIMEOUT = 5
