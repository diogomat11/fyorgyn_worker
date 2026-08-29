# ============================================
# CONFIG / CONSTANTS.PY
# ============================================

# ===========================
# LOGIN PAGE
# ===========================
# IPASGO Prestador (OutSystems)

X_LOGIN_USERNAME = '//*[@id="wtUserNameInput2"]'
X_LOGIN_PASSWORD = '//*[@id="wtPasswordInput"]'
X_LOGIN_BUTTON   = '//*[@id="wtLoginButton"]'

# Mensagens de erro / validação
X_LOGIN_ERROR_MESSAGE = '//*[contains(@class, "error") or contains(@id, "msgErro")]'
X_LOGIN_LOADING       = '//*[contains(@class, "loading") or contains(@id, "loader")]'


# ===========================
# MENU / HOME
# ===========================
X_MENU_OP_IMPORT_GUIAS = '//a[contains(@href, "importar-guias") or contains(text(), "Importação")]'
X_MENU_OP_AUTORIZACAO  = '//a[contains(text(), "Autorização")]'
X_MENU_OP_FATURAMENTO  = '//a[contains(text(), "Faturamento")]'
X_MENU_OP_AGENDAMENTO  = '//a[contains(text(), "Agendamento")]'


# ===========================
# IMPORTAÇÃO DE GUIAS – TELA PRINCIPAL
# ===========================
X_IMPORT_BTN_UPLOAD = '//input[@type="file" and contains(@id, "upload")]'
X_IMPORT_BTN_PROCESSAR = '//button[contains(text(), "Processar") or @id="btnProcessar"]'
X_IMPORT_TABELA_RESULTADOS = '//table[contains(@class, "resultados") or contains(@id, "tabelaResultados")]'

# Feedback visual
X_IMPORT_ALERT_SUCESSO = '//*[contains(@class, "alert-success")]'
X_IMPORT_ALERT_ERRO = '//*[contains(@class, "alert-danger") or contains(@class, "alert-error")]'
X_ALERT_CLOSE = '//*[contains(@class,"close") or contains(@class,"fechar") or contains(@class,"fa-times") or @id="alertClose" or @aria-label="Fechar"]'
# Link que abre módulo principal (FacPlan) em nova aba
# NOTA: escopo //a — sem ele o //*[contains(...)] casa os ANCESTRAIS do link
# (divs/tabela) primeiro e o clique vai para o elemento errado.
X_FACPLAN_LINK = '//a[contains(@href, "facplan") or contains(@href, "FacPlan") or contains(@href, "webplan") or contains(@href, "WebPlan") or contains(., "FacPlan") or contains(., "FACPLAN") or contains(., "WebPlan") or contains(., "Webplan")]'
# Absoluto pós-fechamento do frame de notificação (DOM reorganiza div[4]→div[2],
# div[6]→div[7]) — atualizado em 2026-08-29
X_FACPLAN_LINK_ABS = '/html/body/form/div[3]/div/div[2]/div/div[2]/div/div/span/div[7]/div/div[2]/div[2]/div/div/div[2]/table/tbody/tr[2]/td/div/a'


# ===========================
# LOCALIZAR PROCEDIMENTOS – FILTRO
# ===========================
# Preencher com os XPaths exatos da página LocalizarProcedimentos
X_LOCALIZAR_MENU_FATURAMENTO = '//*[@id="menuPrincipal"]/div/div[5]/a'
X_LOCALIZAR_NOTY_CONTAINER = '//*[@id="noty_top_layout_container"]'
X_LOCALIZAR_NOTY_FECHAR = '/html/body/ul/li/div/div[2]/button[2]'
X_LOCALIZAR_NOTY_MODAL = '//*[contains(@class,"noty_modal")]'

X_LOCALIZAR_DATA_INICIO = '/html/body/main/div[2]/div[1]/div[2]/div[1]/div[3]/input-periodo-data/div/div[1]/div/div/input | //input[contains(@data-bind, "idIni")] | //input-periodo-data//input[1]'
X_LOCALIZAR_DATA_FIM = '/html/body/main/div[2]/div[1]/div[2]/div[1]/div[3]/input-periodo-data/div/div[2]/div/div/input | //input[contains(@data-bind, "idFim")] | //input-periodo-data//input[2]'
X_LOCALIZAR_CARTEIRA = '/html/body/main/div[1]/div[1]/div[2]/div[1]/div[1]/div[3]/input | /html/body/main/div[2]/div[1]/div[2]/div[1]/div[1]/div[3]/input'
X_LOCALIZAR_GUIA = '/html/body/main/div[1]/div[1]/div[2]/div[1]/div[1]/div[4]/input | /html/body/main/div[2]/div[1]/div[2]/div[1]/div[1]/div[4]/input'
X_LOCALIZAR_BTN_PESQUISAR = '//*[@id="localizar-procedimentos-btn"]'
X_LOCALIZAR_TABELA_CONTAINER = '//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]'
X_LOCALIZAR_ROW_PACIENTE_FMT = '//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]/div[{i}]/div/div/div/div[2]/div[1]/div[1]/span'
X_LOCALIZAR_ROW_GUIA_FMT = '//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]/div[{i}]/div/div/div/div[2]/div[2]/div/div[2]/div[1]/div[1]/span'
X_LOCALIZAR_ROW_COD_BENEF_FMT = '//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]/div[{i}]/div/div/div/div[2]/div[1]/div[1]/strong[2]'
X_LOCALIZAR_ROW_SENHA_FMT = '//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]/div[{i}]/div/div/div/div[2]/div[2]/div/div[2]/div[1]/div[3]/span'
X_LOCALIZAR_ROW_SITUACAO_FMT = '//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]/div[{i}]/div/div/div/div[2]/div[2]/div/div[2]/div[2]/div[3]/span'
X_LOCALIZAR_ROW_DATA_SOL_FMT = '//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]/div[{i}]/div/div/div/div[2]/div[2]/div/div[2]/div[2]/div[4]/span'
X_LOCALIZAR_ROW_DATA_AUT_FMT = '//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]/div[{i}]/div/div/div/div[2]/div[2]/div/div[2]/div[1]/div[4]/span'
X_LOCALIZAR_ROW_COD_PROC_FMT = '//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]/div[{i}]/div/div/div/div[2]/div[2]/div/div[1]/div/div[2]/div/div/div'
X_LOCALIZAR_ROW_BTN_DET_FMT = '//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]/div[{i}]/div/div/div/div[2]/div[2]/div/div[1]/div/div[1]/div[2]/div/i[1]'
X_LOCALIZAR_DET_QT_SOL = '//*[@id="itens-guia"]/div/div/div[2]/div/div[2]/table/tbody/tr[1]/td[2]'
X_LOCALIZAR_DET_QT_AUT = '//*[@id="itens-guia"]/div/div/div[2]/div/div[2]/table/tbody/tr[1]/td[4]'
X_LOCALIZAR_DET_MODAL_FECHAR = '//*[@id="detalhes-itens-guia-modal"]/div/div/div[3]/button'
X_LOCALIZAR_BTN_NEXT = '//a[@aria-label="prox"]'
X_LOCALIZAR_FIRST_GUIA = '//*[@id="localizarprocedimentos"]/div[2]/div/div[2]/div/div[2]/div[1]/div/div/div/div[2]/div[2]/div/div[2]/div[1]/div[1]/span'

# Avisos / banners durante carregamento
X_ALERT_AVISO_BANNER = '//*[contains(@class,"alert") and (contains(.,"Aviso") or contains(.,"Aguarde o término da solicitação"))]'
X_LOADING_OVERLAY = '//*[@id="divLoadingOverlay"]'
X_ALERT_CLOSE_STRONG = '/html/body/ul/li/div/div/span/h4/i'

# ===========================
# POPUP / MODAL CONFIRMAÇÃO
# ===========================
X_MODAL_CONFIRMAR = '//button[contains(text(), "Confirmar") or @id="btnConfirmar"]'
X_MODAL_CANCELAR = '//button[contains(text(), "Cancelar") or @id="btnCancelar"]'
X_MODAL_CONTENT = '//*[contains(@class, "modal-content")]'


# ===========================
# ELEMENTOS GERAIS
# ===========================
X_LOADING_GLOBAL = '//*[contains(@class,"spinner") or contains(@id,"loading")]'
X_BOTOES_SALVAR = '//button[contains(text(), "Salvar")]'
X_BOTOES_OK = '//button[contains(text(), "OK") or contains(text(), "Ok")]'

# Paginação
X_PAGINA_PROXIMA = '//a[contains(@class, "next") or contains(text(), "Próximo")]'
X_PAGINA_ANTERIOR = '//a[contains(@class, "prev") or contains(text(), "Anterior")]'

# Busca
X_CAMPO_BUSCA = '//input[contains(@placeholder, "Buscar") or contains(@id,"search")]'
X_BOTAO_BUSCAR = '//button[contains(text(), "Buscar") or contains(@id,"btnSearch")]'



# ===========================
# OP1 - AUTORIZAR FACPLAN (GuiaSPSADT)
# ===========================
X_AUTFACPLAN_URL               = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/GuiaSPSADT/ViewGuiaSPSADT"

# Etapa 1 — Carteira / Dados iniciais
X_AUTFACPLAN_CLICK_CARTAO      = '//*[@id="div_numeroDaCarteira"]/div/i'
X_AUTFACPLAN_INPUT_CARTEIRA    = '//*[@id="cartao"]'
X_AUTFACPLAN_NOME_BENEF        = '//*[@id="nomeDoBeneficiario"]'
X_AUTFACPLAN_CARAT_ATEND       = '//*[@id="caraterAtendimento"]'
X_AUTFACPLAN_CARAT_ATEND_OPT2  = '//*[@id="caraterAtendimento"]/option[2]'
X_AUTFACPLAN_DATA_SOLICIT      = '/html/body/main/div[2]/div[1]/div[7]/div[2]/div/input'
X_AUTFACPLAN_INDICACAO_CLIN    = '//*[@id="indicacaoClinica"]'

# Etapa 2 — Procedimento
X_AUTFACPLAN_MENU_PROC         = '//*[@id="ui-accordion-accordion-header-2"]'
X_AUTFACPLAN_BTN_INCLUIR_PROC  = '//*[@id="incluirProcedimento"]'
X_AUTFACPLAN_INPUT_COD_PROC    = '//*[@id="registroProcedimentoCodigo"]/input'
X_AUTFACPLAN_INPUT_QT_PROC     = '//*[@id="registroProcedimentoQuantidade"]/input'
X_AUTFACPLAN_BTN_CONF_PROC     = '//*[@id="confirmarEdicaoDeProcedimento"]'
X_AUTFACPLAN_SPAN_MSG_GENERICA = '//*[@id="spanTextoMensagemGenerica"]'

# Etapa 3 — Profissional executante
X_AUTFACPLAN_MENU_EXEC         = '//*[@id="ui-accordion-accordion-header-3"]'
X_AUTFACPLAN_BTN_INCLUIR_PROF  = '//*[@id="incluirProfissional"]'
X_AUTFACPLAN_INPUT_GRAU        = '//*[@id="registroProfissionalGrauParticipacao"]/input'
X_AUTFACPLAN_INPUT_COD_PROF    = '//*[@id="registroProfissionalCodigo"]/input'
X_AUTFACPLAN_INPUT_CBO         = '//*[@id="registroProfissionalCodCBO"]/input'
X_AUTFACPLAN_BTN_CONF_PROF     = '//*[@id="confirmarEdicaoDeProfissional"]'
X_AUTFACPLAN_BTN_CANCEL_PROF   = '//*[@id="cancelarEdicaoDeProfissional"]'
X_AUTFACPLAN_BTN_EXCLUIR_PROF  = '//*[@id="excluirProfissional"]'

# Etapa 4 — Justificativa Clínica
X_AUTFACPLAN_MENU_JUST         = '//*[@id="ui-accordion-accordion-header-4"]'
X_AUTFACPLAN_INPUT_JUST        = '//*[@id="observacao"]'

# Etapa 5a — Observação adicional
X_AUTFACPLAN_TITLE_OBS         = '//*[@id="informacoesAdicionaisTitle"]'
X_AUTFACPLAN_INPUT_OBS         = '//*[@id="observacaoAdicional"]'

# Etapa 5b — Contato auditoria
X_AUTFACPLAN_TITLE_AUDIT       = '//*[@id="contatoAuditoriaTitle"]'
X_AUTFACPLAN_INPUT_AUDIT       = '//*[@id="contatoAuditoriaJustificativa"]'

# Etapas 6/7/8 — Anexos
X_AUTFACPLAN_SELECT_TIPO_ANX   = '//*[@id="tipoAnexoGuiaUpload"]'
X_AUTFACPLAN_TIPO_RM_OPT       = '//*[@id="tipoAnexoGuiaUpload"]/option[47]'  # Pedido médico (RM)
X_AUTFACPLAN_TIPO_AI_OPT       = '//*[@id="tipoAnexoGuiaUpload"]/option[35]'  # Avaliação inicial (AI)
X_AUTFACPLAN_TIPO_RC_OPT       = '//*[@id="tipoAnexoGuiaUpload"]/option[57]'  # Relatório clínico (RC)
X_AUTFACPLAN_INPUT_CAMINHO     = '//*[@id="upload_form"]/div/input[1]'
X_AUTFACPLAN_BTN_INCLUIR_ANX   = '//*[@id="upload_form"]/div/input[2]'
X_AUTFACPLAN_SPINNER_ANX       = '//*[@id="upload_form"]/div/img'

# Gravar + Confirmar
X_AUTFACPLAN_BTN_GRAVAR        = '//*[@id="btnGravar"]'
X_AUTFACPLAN_BTN_CONFIRMAR     = '/html/body/div[8]/div[3]/div/button[1]'

# Diálogo de resultado após gravação
X_AUTFACPLAN_DIALOG_NUM_GUIA   = '//*[@id="dialogText"]/div[2]'
X_AUTFACPLAN_DIALOG_GUIA_PREST = '//*[@id="dialogText"]/div[3]'
X_AUTFACPLAN_DIALOG_DATA_SOL   = '//*[@id="dialogText"]/div[4]'
X_AUTFACPLAN_BTN_FECHAR_DIALOG = '/html/body/div[8]/div[1]/button'


# ===========================
# TIMEOUTS / CONFIG
# ===========================
DEFAULT_TIMEOUT = 20
LONG_TIMEOUT = 45
SHORT_TIMEOUT = 5

