# ============================================================
# AMIL — Constantes do Integrador (id_integrador=9, convenio 9)
# Portal: https://credenciado.amil.com.br (SPA + API interna)
# Proteção: Akamai bot-manager (cookies _abck/bm_sz → UC no driver)
# Fonte: docs/plano_amil_op0_op1.md (decisões D4-D9)
# ============================================================

# ── URLs ──
LOGIN_URL = "https://credenciado.amil.com.br/login"
PEDIDOS_URL = "https://credenciado.amil.com.br/pedidos-autorizacao"
API_PEDIDOS = "https://credenciado.amil.com.br/credenciadomedico/pedidos-autorizacao"
PORTAL_ORIGIN = "https://credenciado.amil.com.br"

# ── OP0: Login (SPA as-main-app / as-login) ──
ID_LOGIN = "login-usuario"        # input id do usuário
ID_SENHA = "login-senha"          # input id da senha
ID_COOKIES = "onetrust-accept-btn-handler"  # banner OneTrust (aceitar cookies)
XPATH_BOTAO_ENTRAR = "/html/body/as-main-app/as-login-container/div[1]/div/as-login/div[2]/form/fieldset/button"

# ── OP1: Consulta Guias (API pedidos-autorização) ──
# Content-type vendor exigido pela API (observado no SPA)
ACCEPT_HEADER = "application/vnd.amil.credenciado.medico.pedidos-autorizacao.v1+json"
# Paginação (decisão D7): start=1, 11, 21... (limit=PAGE_LIMIT)
PAGE_LIMIT = 10
# Safety caps (decisão D7): teto de páginas da listagem e de detalhes por job
MAX_PAGINAS = 500
MAX_GUIAS_DETALHE = 2000

# ── Headers de sessão (decisão D4: lidos do storage em runtime, nunca persistidos) ──
# authorization: Bearer <accessToken> (payload do x-session JWT)
# x-session: <JWT> (payload contém accessToken/refreshToken)
# x-user: <codigoUsuario do cookie / cod_prestador>

# ── Cookies relevantes p/ evidência de sessão na OP0 (nomes apenas — nunca valores) ──
COOKIES_RELEVANTES = ("JSESSIONID", "_abck", "bm_sz", "codigoUsuario")

# ── Timeouts (segundos) ──
SHORT_TIMEOUT = 5
DEFAULT_TIMEOUT = 20
LONG_TIMEOUT = 45

# ── Fetch JS (OP1 — padrão do 1-bradesco Fature) ──
FETCH_TIMEOUT_S = 30      # AbortController dentro do navegador
SCRIPT_TIMEOUT_S = 45     # set_script_timeout do Selenium (SEMPRE > FETCH_TIMEOUT_S)
FETCH_RETRIES = 1         # retentativas em 5xx/transiente, backoff 2s
THROTTLE_S = 0.5          # pausa entre requests (anti-rate-limit)
BACKOFF_S = 2             # espera antes do retry transiente

# ── Identificação do integrador (envelope/logs) ──
ID_INTEGRADOR = 9
SIGLA_INTEGRADOR = "AMIL"

# ── Processamento em lote (fetch paralelo no contexto do browser) ──
# Incidente de performance (jobs 28845/28846): detalhes sequenciais
# (N × round-trip Python→chromedriver + fetch + throttle) levavam ~11 min
# para 199 guias. Lote dispara N fetches concorrentes DENTRO do navegador
# (Promise pool) e devolve todos de uma vez — elimina os round-trips.
LOTE_CONCORRENCIA = 6       # fetches simultâneos por lote (mesmo-origin HTTP/2)
LOTE_TAMANHO_DETALHE = 24   # urls de detalhe por lote (24/6 ≈ 4 rodadas)
LOTE_BATCH_TIMEOUT_S = 120  # timeout da chamada batch inteira (set_script_timeout)
