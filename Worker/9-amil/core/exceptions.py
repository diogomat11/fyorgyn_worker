"""
Exceções do integrador AMIL (9-amil) — mensagens estáveis usadas pelo
dispatcher para classificar erros fatais (sem retry) e pelo scraper para a
escada de recuperação de sessão (mesmo padrão do 1-bradesco).

IMPORTANTE: o core/scraper.py NÃO pode confiar em isinstance destas classes —
execute_op purga sys.modules e recarrega a OP do disco a cada job, então a
LoginFailedError que a OP levanta é uma classe DIFERENTE da importada aqui.
A classificação no process_job é pelo PREFIXO da mensagem:
  - "LOGIN_REJEITADO:"  → fatal, sem retry (credencial recusada pelo portal)
  - "SESSAO_EXPIRADA:"  → escada de recuperação (re-login → reciclar driver)
"""


class LoginFailedError(Exception):
    """O portal REJEITOU as credenciais (mensagem capturada da própria página).

    Fatal — SEM retry: repetir a mesma senha só multiplica tentativas erradas
    no portal e pode BLOQUEAR a conta (lição do incidente Bradesco). A mensagem
    original do portal é incluída para o usuário corrigir no frontend.
    Prefixo obrigatório: "LOGIN_REJEITADO: <mensagem do portal>".
    """
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class SessionExpiredError(Exception):
    """Sessão do portal AMIL expirou durante a operação (URL caiu em /login,
    elemento de login visível ou API devolveu 401/403).

    O core/scraper.py trata com a escada de recuperação:
    1ª ocorrência → re-login no mesmo driver (attempt seguinte);
    2ª consecutiva → reciclar o driver (quit + Chrome novo) e re-login.
    Prefixo obrigatório: "SESSAO_EXPIRADA: <detalhe>".
    """
    def __init__(self, message="SESSAO_EXPIRADA: sessão do portal AMIL expirada"):
        super().__init__(message)
        self.message = message
