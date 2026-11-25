"""
Independent database connection for Worker
Connects directly to Supabase without depending on backend code
"""
import os
import socket
import time
from urllib.parse import urlsplit

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load .env from Worker directory, parent directories, or backend/.env
load_dotenv(os.path.join(os.getcwd(), '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', 'backend', '.env'))

DB_USER = os.getenv("SUPABASE_DB_USER", "postgres")
DB_PASSWORD = os.getenv("SUPABASE_PASSWORD", "")
DB_HOST = os.getenv("SUPABASE_DB_HOST", "db.ourddwzetcbdjnbvamgj.supabase.co")
DB_PORT = os.getenv("SUPABASE_DB_PORT", "5432")
DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")

# Prefer DATABASE_URL when explicitly set: it points to the Supabase POOLER
# (IPv4), required because the direct host db.<ref>.supabase.co is IPv6-only
# and times out on IPv4-only networks. Pooler vai para o modo transação
# (6543): o modo sessão (5432) tem teto rígido de clientes no Supavisor
# (FATAL EMAXCONNSESSION) — os ~15 slots são compartilhados com hub e
# backend_worker, e a disputa derruba a conexão do worker. Nenhum recurso de
# sessão é usado aqui e prepared statements já estão desligados
# (prepare_threshold=None). URLs diretas ficam intocadas.
_DATABASE_URL_ENV = os.getenv("DATABASE_URL", "").strip()
if _DATABASE_URL_ENV:
    if "pooler.supabase.com" in _DATABASE_URL_ENV:
        SQLALCHEMY_DATABASE_URL = _DATABASE_URL_ENV.replace(":5432", ":6543")
    else:
        SQLALCHEMY_DATABASE_URL = _DATABASE_URL_ENV
else:
    if DB_PORT == "6543":
        DB_PORT = "5432"  # transaction mode -> session mode
    SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ── Resolver do host do banco em camadas ─────────────────────────────────────
# O host direto do Supabase é IPv6-only e o resolver do Windows falha
# intermitentemente (getaddrinfo 11001/11004) mesmo com o DNS respondendo —
# o dispatcher/worker então morre com erro vazio e a fila para. Camadas:
# 1) getaddrinfo; 2) dnspython consultando DNS pública direto (bypass do
# resolver do SO); 3) último IP válido em cache (last known good).
_IPS_CACHE = {"ips": None, "expires": 0.0}
_IP_TTL = 300.0
_DNS_PUBLICOS = ("8.8.8.8", "1.1.1.1", "8.8.4.4")
_IP_TURNO = {"i": 0}


def _resolver_todos(hostname):
    """Todos os IPs do host (A records; AAAA só se não houver A). O DNS do
    pooler do Supabase retorna múltiplos IPs e nem todos respondem — fixar
    um único IP fazia threads caírem no IP morto e queimarem connect_timeout
    x3 (~30s) por tentativa."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except Exception:
        return []
    v4 = sorted(set(i[4][0] for i in infos if i[0] == socket.AF_INET))
    if v4:
        return v4
    return sorted(set(i[4][0] for i in infos if i[0] == socket.AF_INET6))


def _dns_direto(hostname):
    """Consulta DNS pública direto por UDP (dnspython), bypass do resolver
    do SO. Retorna todos os registros encontrados."""
    try:
        import dns.resolver
        r = dns.resolver.Resolver(configure=False)
        r.nameservers = list(_DNS_PUBLICOS)
        r.lifetime = 4
        for tipo in ("A", "AAAA"):
            try:
                resp = r.resolve(hostname, tipo)
                if resp:
                    return sorted(set(str(x) for x in resp))
            except Exception:
                continue
    except Exception:
        pass
    return []


def _hosts_do_banco() -> list:
    """IPs candidatos do host do banco, com cache, rotação e fallback em camadas.
    A rotação distribui o ponto de partida: threads distintas começam por IPs
    distintos, e um IP morto custa no máximo um connect_timeout por thread."""
    now = time.time()
    if _IPS_CACHE["ips"] and now < _IPS_CACHE["expires"]:
        ips = _IPS_CACHE["ips"]
    else:
        ips = _resolver_todos(_HOST_DB) or _dns_direto(_HOST_DB)
        if ips:
            _IPS_CACHE["ips"] = ips
            _IPS_CACHE["expires"] = now + _IP_TTL
        elif _IPS_CACHE["ips"]:
            # Nada resolveu agora: usa os últimos IPs conhecidos mesmo expirados —
            # conectar num IP velho tem chance de funcionar; falhar tem certeza.
            ips = _IPS_CACHE["ips"]
        else:
            raise OSError(f"DNS indisponível: impossível resolver {_HOST_DB}")
    i = _IP_TURNO["i"] = (_IP_TURNO["i"] + 1) % len(ips)
    return ips[i:] + ips[:i]


_parsed = urlsplit(SQLALCHEMY_DATABASE_URL)
_HOST_DB = _parsed.hostname or DB_HOST
_DB_PORT_NUM = _parsed.port or 5432
_DB_USER_URL = _parsed.username or DB_USER
_DB_PASS_URL = _parsed.password or DB_PASSWORD
_DB_NAME_URL = (_parsed.path or "/postgres").lstrip("/") or "postgres"

import psycopg2

_PS2_KW = {
    "sslmode": "require",
    "prepare_threshold": None,
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
    "connect_timeout": 5,
}


def _criar_conexao():
    """Creator do pool: conecta por IP tentando TODOS os candidatos em cada
    tentativa (resolver em camadas + rotação). sslmode=require não verifica
    hostname, então conectar por IP mantém o mesmo nível de segurança do DSN."""
    ultimo = None
    for tentativa in range(3):
        try:
            ips = _hosts_do_banco()
        except OSError:
            if ultimo:
                raise
            continue
        for host_ip in ips:
            try:
                return psycopg2.connect(
                    host=host_ip,
                    port=_DB_PORT_NUM,
                    dbname=_DB_NAME_URL,
                    user=_DB_USER_URL,
                    password=_DB_PASS_URL,
                    **_PS2_KW,
                )
            except psycopg2.OperationalError as exc:
                ultimo = exc
                # IP pode ter ficado obsoleto: invalida cache para re-resolver
                _IPS_CACHE["ips"] = None
                _IPS_CACHE["expires"] = 0.0
        time.sleep(0.3 * (tentativa + 1))
    raise ultimo

try:
    with open("db_debug_worker.log", "a") as f:
        f.write(f"DB URL: {_parsed.scheme}://{_parsed.username}@{_parsed.hostname}:{_DB_PORT_NUM}/{_DB_NAME_URL} (via IP cache)\n")
except Exception: pass

engine = create_engine(
    "postgresql://",  # apenas seleção de dialect; conexão real via creator
    creator=_criar_conexao,
    use_native_hstore=False,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=300,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
