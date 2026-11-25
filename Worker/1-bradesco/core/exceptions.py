"""
Exceções do integrador Bradesco (1-bradesco) — mensagens estáveis usadas pelo
dispatcher para classificar erros fatais (sem retry) e pelo scraper para a
escada de recuperação de sessão.

Padrão de mensagens (dispatcher.py regra fatal):
  - MFA_*      → código OTP expira; retry automático inútil → fatal
  - SessionExpiredError → tratada pela escada (re-login → reciclar driver)
"""


class MfaError(Exception):
    """Base dos erros de MFA — o scraper NÃO retenta (código OTP expira)."""
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class SessionExpiredError(Exception):
    """Sessão do portal (Faturi/Keycloak) expirou durante a operação.

    O core/scraper.py trata com a escada de recuperação:
    1ª ocorrência → re-login no mesmo driver (attempt seguinte);
    2ª consecutiva → reciclar o driver (quit + Chrome novo) e re-login.
    """
    def __init__(self, message="Sessão do portal expirada (Authentication failed)"):
        super().__init__(message)
        self.message = message


class MfaTimeoutError(MfaError):
    """Usuário não digitou o código MFA dentro do prazo do ciclo (300s)."""
    def __init__(self, message="MFA_TIMEOUT: tempo esgotado aguardando o código de verificação do usuário"):
        super().__init__(message)


class MfaCancelledError(MfaError):
    """Usuário cancelou a digitação do código MFA no modal."""
    def __init__(self, message="MFA_CANCELLED: digitação cancelada pelo usuário"):
        super().__init__(message)


class MfaMaxCyclesError(MfaError):
    """Código MFA inválido em todos os ciclos disponíveis (máx. 2)."""
    def __init__(self, message="MFA_MAX_CYCLES: código de verificação inválido em todas as tentativas"):
        super().__init__(message)


class LoginFailedError(Exception):
    """O portal REJEITOU as credenciais (mensagem capturada da própria página).

    Fatal — SEM retry: repetir a mesma senha só multiplica tentativas erradas
    no portal e pode BLOQUEAR a conta (incidente: usuário bloqueado por
    retries com senha antiga snapshotada nos params). A mensagem original do
    portal (ex.: "Usuário ou senha inválidos", "conta bloqueada") é incluída
    para o usuário corrigir no frontend.
    """
    def __init__(self, message):
        super().__init__(message)
        self.message = message
