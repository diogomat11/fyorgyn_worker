# ============================================
# ABA_CLMF (101) - CONFIG / CONSTANTS.PY
# Seletores, URLs e mapeamentos do portal ABA
# ============================================

import os

# URLs — modelo de DOIS domínios (portal mudou; ref. clmf_hub_basic 2026-11-21)
# Painel novo (app.): autenticação via API (Bearer) — o login visual antigo
# (emailAba/senhaAba/btnEntrarAba) foi aposentado pelo portal. A sessão do
# sistema antigo (PHP, na RAIZ) nasce da troca de um token SSO de uso único
# (mesmo fluxo do botão "irParaOAntigo" do painel: js/app.js).
APP_URL = "https://app.abalarissamartinsferreira.com.br"          # painel novo
BASE_URL = "https://abalarissamartinsferreira.com.br"             # sistema antigo (PHP)
LOGIN_URL = f"{APP_URL}/"                                         # tela de login do painel
API_LOGIN_URL = f"{APP_URL}/api/auth/login"       # POST {email, senha} → {token, usuario}
API_SSO_EMITIR_URL = f"{APP_URL}/api/sso/emitir"  # POST {destino} + Bearer → {url, token}
# Tela pós-SSO: precisa estar no MENU da conta (a API valida — 422 "Tela não
# encontrada no seu menu."). Ajustável por env para contas com permissões
# diferentes (CLMF_SSO_DESTINO).
SSO_DESTINO = os.getenv("CLMF_SSO_DESTINO", "/prontuarios/home/status/1")
LOGIN_PROBE_TIMEOUT = 10          # sonda GET / sem seguir redirect (is_logged_in)
AJAX_TIMEOUT = 60                 # POSTs de login/SSO e chamadas AJAX das OPs

AJAX_SCHEDULE_URL = f"{BASE_URL}/_ajax/Schedule.ajax.php"
CLIENT_DETAIL_URL = f"{BASE_URL}/clients/create"  # + /{id_paciente}
PAGAMENTOS_HOME_URL = f"{BASE_URL}/pagamentos/home"

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

# ─── OP6: Atualizar RC (Relatorio Clinico Mensal) ──────────────────────────
# Replica de clmf_hub_basic/worker/Worker/clmf_scraper.py
AJAX_RC_URL = f"{BASE_URL}/_ajax/RelatorioMensalIpasgo.ajax.php"
PRONTUARIO_URL_TEMPLATE = f"{BASE_URL}/prontuarios/prontuario/{{id_paciente}}"
ACTION_GRAVAR_RC = "gravar"
ACTION_GERAR_RELATORIO = "gerarRelatorio"
CALLBACK_RC = "RelatorioMensalIpasgo"

# Seletor indicando login ativo (titulo do menu de clientes)
LOGIN_READY_TITLE = "Ver CLIENTES"
LOGIN_READY_XPATH = f'//*[@title="{LOGIN_READY_TITLE}"]'

# IDs de elementos do DOM do prontuario (extracao RC)
DOM_NOME_FOLLOWING_STRONG_XPATH = "//span[contains(text(), 'Nome:')]/following-sibling::strong"
DOM_CARTEIRINHA_ID = "amil_client_carteirinha"
DOM_JUSTIFICATIVA_ID = "ipasgo_justificativa_periodo_tratamento"
DOM_EVOLUCAO_ID = "ipasgo_evolucao_paciente"

# Codigos de erro especificos da OP6
CODE_WIPEOUT_BLOCK = "WIPEOUT_BLOCK"
CODE_AJAX_FAIL = "AJAX_FAIL"
CODE_PDF_NOT_GENERATED = "PDF_NOT_GENERATED"
CODE_DOWNLOAD_FAIL = "DOWNLOAD_FAIL"
CODE_INVALID_DATE = "INVALID_DATE"
CODE_EXTRACT_FAIL = "EXTRACT_FAIL"
