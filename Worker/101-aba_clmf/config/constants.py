# ============================================
# ABA_CLMF (101) - CONFIG / CONSTANTS.PY
# Seletores, URLs e mapeamentos do portal ABA
# ============================================

# URLs
BASE_URL = "https://abalarissamartinsferreira.com.br"
LOGIN_URL = f"{BASE_URL}/"
AJAX_SCHEDULE_URL = f"{BASE_URL}/_ajax/Schedule.ajax.php"
CLIENT_DETAIL_URL = f"{BASE_URL}/clients/create"  # + /{id_paciente}

# Login Selectors (Selenium)
LOGIN_FIELD_EMAIL = 'user_email'          # name="user_email"
LOGIN_FIELD_PASSWORD = 'user_password'    # name="user_password"
LOGIN_BUTTON_XPATH = "/html/body/div[1]/div/form/button"

# Timeouts
DEFAULT_TIMEOUT = 15
LONG_TIMEOUT = 30
SHORT_TIMEOUT = 5

# Unidades permitidas (regra geral)
ALLOWED_UNIT_IDS = {1, 3, 5}

# schedule_pagamento_id -> id_convenio (vinculo direto)
PAGAMENTO_ID_MAP = {
    3: 3,    # Unimed Goiania
    6: 6,    # IPASGO
    8: 8,    # Sulamerica
    9: 9,    # Amil
    21: 21,  # UNIMED INTERCAMBIO
    31: 31,  # IPASGO GERAL
}

# Mapeamento col_pagamento (nome texto) -> id_convenio (para busca de carteirinhas)
CONVENIO_NAME_MAP = {
    "unimed goiania": 3,
    "unimed goiânia": 3,
    "unimed goiania guia": 3,
    "unimed goiânia guia": 3,
    "ipasgo": 6,
    "ipasgo geral": 6,
    "ipasgo tea": 6,
}

# Mapeamento schedule_status -> Status agendamento
STATUS_MAP = {
    "0": "A Confirmar",
    "1": "Confirmado",
    "2": "Falta",
    "3": "Excluído",
}

# URLs de Workflow
CONFIRMAR_ATENDIMENTO_URL = f"{BASE_URL}/schedule/confirmar_atendimento"
FALTAS_BLOCO_URL = f"{BASE_URL}/schedule/faltas_bloco"

# Situações (OP3)
SITUACAO_CONFIRMADO = 1
SITUACAO_REMOVER_CONFIRMACAO = 0

# Callback Actions
ACTION_CONFIRMAR = "update_confirmar_atendimento"
ACTION_GRAVAR_FALTA = "gravarFaltaBloco"
ACTION_REMOVER_FALTA = "remove_falta_block"
