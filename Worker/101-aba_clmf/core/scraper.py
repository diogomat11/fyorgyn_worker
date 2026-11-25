import os
import sys
import importlib.util
from datetime import datetime
import json
import time
import requests
from urllib.parse import urljoin, urlparse

# ── Isolate Environment (Ensure base imports from Worker/ root) ──
_worker_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _worker_root not in sys.path:
    sys.path.insert(0, _worker_root)

# Raiz do módulo 101-aba_clmf + purge anti cross-talk: este import top-level de
# 'config' roda ANTES do execute_op (que purga), então precisa garantir aqui —
# job anterior de OUTRO integrador no mesmo processo deixa 'config' DELE
# cacheado em sys.modules (mesmo mecanismo do 1-bradesco).
_module_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _key in list(sys.modules):
    _mod = sys.modules.get(_key)
    _f = getattr(_mod, "__file__", None)
    if not _f:
        continue
    _parts = os.path.abspath(_f).lower().split(os.sep)
    try:
        _i = next(i for i, p in enumerate(_parts)
                  if p == "worker" and i + 1 < len(_parts) and _parts[i + 1][0].isdigit())
    except StopIteration:
        continue
    del sys.modules[_key]
if _module_root not in sys.path:
    sys.path.insert(0, _module_root)

from base_scraper import BaseScraper
from models import Convenio, JobExecution, UserConvenio
from security_utils import decrypt_password
from database import SessionLocal

from config.constants import (
    APP_URL,
    BASE_URL,
    API_LOGIN_URL,
    API_SSO_EMITIR_URL,
    SSO_DESTINO,
    LOGIN_PROBE_TIMEOUT,
    AJAX_TIMEOUT,
)

class AbaClmfScraper(BaseScraper):
    def __init__(self, id_convenio=101, db=None, headless=True, user_id=None):
        super().__init__(id_convenio, db, headless, user_id)
        self.db = db if db else SessionLocal()
        self.user_id = user_id
        self.username = None
        self.password = None
        self.cod_prestador = None
        self._load_credentials()
        self.module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Hibrido HTTP Requests
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*"
        })
        # Cookies de sessão do sistema antigo (domínio raiz) — fonte da sonda
        # is_logged_in() e das chamadas HTTP diretas das OPs (modelo novo:
        # login via API do painel + SSO, ref. clmf_hub_basic 2026-11-21).
        self.session_cookies = {}

    def is_logged_in(self) -> bool:
        """Sonda HTTP na tela autenticada (SSO_DESTINO) sem seguir redirect:
        com sessão válida responde 200; expirada redireciona para o login.
        (GET / na raiz NÃO serve: redireciona para /_sso/emitir.php mesmo
        autenticado — medido no portal real, 2026-11-21.) Não depende do
        driver. Precedência: cookies do SSO; fallback ao jar da session."""
        cookies = getattr(self, "session_cookies", None) or None
        if not cookies:
            cookies = dict(self.session.cookies) or None
        if not cookies:
            return False
        try:
            resp = requests.get(
                f"{BASE_URL}{SSO_DESTINO}", cookies=cookies,
                allow_redirects=False, timeout=LOGIN_PROBE_TIMEOUT,
                headers={"User-Agent": self.session.headers.get("User-Agent", "Mozilla/5.0")},
            )
            return resp.status_code == 200 and not resp.is_redirect
        except requests.RequestException:
            return False

    def login(self) -> bool:
        """OP0 — Login no portal ABA CLMF (modelo NOVO — ref. clmf_hub_basic,
        fluxo idem ao painel ao abrir uma tela do sistema antigo):
          1. POST api/auth/login no painel (app.) → token Bearer;
          2. POST api/sso/emitir → token SSO de uso único + url do antigo;
          3. POST do token na url → sistema antigo cria a sessão (PHPSESSID).

        Sessão reusada se a sonda indicar autenticação viva. Retorna bool.
        """
        if self.is_logged_in():
            self.log("Sessão ABA_clmf reutilizada — login desnecessário.")
            return True

        if not self.username or not self.password:
            self.log("Credenciais ABA_clmf ausentes — login impossível.", level="ERROR")
            return False

        self.log("Iniciando OP0 — Login (API do painel novo + SSO).")
        try:
            # Sessão SEPARADA para o painel: os cookies do app. não podem
            # poluir o jar das OPs (que chamam o sistema antigo na raiz).
            sessao = requests.Session()
            sessao.headers.update({
                "User-Agent": self.session.headers.get("User-Agent", "Mozilla/5.0")
            })

            # 1) Autenticar no painel novo → token Bearer
            resp = sessao.post(
                API_LOGIN_URL,
                json={"email": self.username, "senha": self.password},
                timeout=AJAX_TIMEOUT,
            )
            if resp.status_code == 401:
                self.log(f"Credenciais recusadas (401): {resp.text[:200]}", level="ERROR")
                return False
            if resp.status_code != 200:
                self.log(f"auth/login HTTP {resp.status_code}: {resp.text[:300]}", level="ERROR")
                return False
            token = (resp.json() or {}).get("token")
            if not token:
                self.log(f"Resposta sem token: {resp.text[:200]}", level="ERROR")
                return False

            # 2) Emitir token SSO de uso único para o sistema antigo
            resp = sessao.post(
                API_SSO_EMITIR_URL, json={"destino": SSO_DESTINO},
                headers={"Authorization": f"Bearer {token}"},
                timeout=AJAX_TIMEOUT,
            )
            if resp.status_code == 422:
                self.log(
                    f"sso/emitir recusou o destino '{SSO_DESTINO}' (422): {resp.text[:300]} — "
                    f"ajuste a env CLMF_SSO_DESTINO com uma tela real do sistema antigo.",
                    level="ERROR",
                )
                return False
            if resp.status_code != 200:
                self.log(f"sso/emitir HTTP {resp.status_code}: {resp.text[:300]}", level="ERROR")
                return False
            sso = resp.json() or {}
            if not sso.get("url") or not sso.get("token"):
                self.log(f"SSO sem url/token: {resp.text[:200]}", level="ERROR")
                return False

            # 3) Trocar o token por sessão PHP no sistema antigo (form POST,
            #    como o painel faz — js/app.js irParaOAntigo)
            sso_url = urljoin(APP_URL + "/", str(sso["url"]))
            resp = sessao.post(sso_url, data={"token": sso["token"]}, timeout=AJAX_TIMEOUT)
            if resp.status_code != 200:
                self.log(f"SSO no sistema antigo HTTP {resp.status_code}: {resp.text[:300]}", level="ERROR")
                return False

            # Cookies de sessão do sistema antigo (PHPSESSID/userView) para
            # reúso nas chamadas HTTP das OPs. Só os do domínio antigo: o
            # painel pode fixar cookies próprios com nomes iguais.
            dominio_antigo = urlparse(BASE_URL).hostname
            self.session_cookies = {
                c.name: c.value for c in sessao.cookies
                if (c.domain or "").lstrip(".") == dominio_antigo
            }
            if "PHPSESSID" not in self.session_cookies:
                self.log(f"SSO concluído sem PHPSESSID (cookies: {list(self.session_cookies)}).", level="WARN")

            # Jar das OPs: SOMENTE os cookies do sistema antigo
            self.session.cookies.clear()
            for name, value in self.session_cookies.items():
                self.session.cookies.set(name, value)

            self._injetar_cookies_driver()
            self.log("Login ABA_clmf realizado com sucesso (API + SSO).")
            return True

        except requests.RequestException as e:
            self.log(f"Erro de rede no login: {e}", level="ERROR")
            return False
        except Exception as e:
            self.log(f"Erro inesperado no login: {e}", level="ERROR")
            return False

    def _injetar_cookies_driver(self):
        """Replica os cookies da sessão HTTP no Chrome via CDP (OPs que navegam
        no driver dependem disso; as OPs HTTP puras não)."""
        if not self.driver or not self.session_cookies:
            return
        try:
            dominio_antigo = urlparse(BASE_URL).hostname
            for name, value in self.session_cookies.items():
                self.driver.execute_cdp_cmd("Network.setCookie", {
                    "name": name, "value": str(value),
                    "domain": dominio_antigo, "path": "/",
                })
            self.log("Cookies de sessão injetados no driver.")
        except Exception as e:
            self.log(f"Falha ao injetar cookies no driver: {e}", level="WARN")

    def _extract_credentials_from_dict(self, data_dict):
        if not data_dict or not isinstance(data_dict, dict):
            return False

        params = data_dict.get("params")
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except Exception:
                params = None

        merged = {}
        merged.update(data_dict)
        if isinstance(params, dict):
            merged.update(params)

        login_val = merged.get("login") or merged.get("username") or merged.get("usuario")
        if login_val:
            self.username = str(login_val).strip()

        pwd_raw = merged.get("password") or merged.get("senha")
        if not pwd_raw and merged.get("senha_criptografada"):
            try:
                pwd_raw = decrypt_password(merged.get("senha_criptografada"))
            except Exception:
                pass
        if pwd_raw:
            self.password = str(pwd_raw).strip()

        prest_val = (
            merged.get("cod_prestador") or
            merged.get("codigoPrestador") or
            merged.get("prestador")
        )
        if prest_val:
            self.cod_prestador = str(prest_val).strip()

        return bool(self.username and self.password)

    def _load_credentials(self, job_data=None):
        try:
            if job_data and self._extract_credentials_from_dict(job_data):
                self.log(f"Credenciais ABA_clmf carregadas via job_data (user_id={self.user_id})")
                return

            if self.user_id and self.db:
                user_conv = self.db.query(UserConvenio).filter(
                    UserConvenio.user_id == self.user_id,
                    UserConvenio.id_convenio == self.id_convenio
                ).first()
                if user_conv and user_conv.login and user_conv.senha_criptografada:
                    self.username = user_conv.login
                    self.password = decrypt_password(user_conv.senha_criptografada)
                    self.cod_prestador = user_conv.cod_prestador
                    self.log(f"Credenciais ABA_clmf carregadas (user_id={self.user_id})")
                    return
            self.log(f"Credenciais ABA_clmf nao encontradas para user_id={self.user_id}", level="WARN")
        except Exception as e:
            self.log(f"ABA_clmf Credential Load Error: {e}", level="ERROR")

    def reload_credentials(self, user_id, job_data=None):
        self.user_id = user_id
        self.username = None
        self.password = None
        self.cod_prestador = None
        self._load_credentials(job_data)

    def start_driver(self):
        pass # Managed by SeleniumManager
        
    def close_driver(self):
        pass # Managed by SeleniumManager

    def log(self, message, level="INFO", job_id=None, carteirinha_id=None):
        job_prefix = f"[Job {job_id}] " if job_id else ""
        print(f"[{level}] {job_prefix}{message}")
        if self.db:
            try:
                from models import Log as LogModel
                log_entry = LogModel(
                    job_id=job_id,
                    carteirinha_id=carteirinha_id,
                    user_id=self.user_id,
                    level=level,
                    message=f"[ABA_clmf] {message}"
                )
                self.db.add(log_entry)
                self.db.commit()
            except Exception:
                try: self.db.rollback()
                except: pass

    def execute_op(self, op_name, job_data):
        op_file = f"{op_name}.py"
        op_path = os.path.join(self.module_path, "op", op_file)
        
        if not os.path.exists(op_path):
            raise FileNotFoundError(f"Operação {op_name} não encontrada em {op_path}")

        # Cross-talk entre integradores: job anterior de OUTRO convênio no mesmo
        # processo deixa 'config' (e módulos dele) cacheado em sys.modules — o
        # import da OP resolveria o pacote errado (ex.: config do 102-caesan
        # servindo o 6-ipasgo → ImportError em X_LOGIN_USERNAME). Purga módulos
        # de QUALQUER Worker/<id>-* antes de carregar a OP (a OP é recarregada
        # do disco; módulos da raiz do Worker ficam de fora).
        for _key in list(sys.modules):
            _mod = sys.modules.get(_key)
            _f = getattr(_mod, "__file__", None)
            if not _f:
                continue
            _parts = os.path.abspath(_f).lower().split(os.sep)
            try:
                _i = next(i for i, p in enumerate(_parts)
                          if p == "worker" and i + 1 < len(_parts) and _parts[i + 1][0].isdigit())
            except StopIteration:
                continue
            del sys.modules[_key]

        spec = importlib.util.spec_from_file_location(op_name, op_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        func = getattr(module, "run", None) or getattr(module, "execute", None)
        if not func:
            raise AttributeError(f"Módulo {op_name} não possui função 'run' ou 'execute'")
            
        return func(self, job_data)

    def process_job(self, rotina, job_data):
        job_id = job_data.get("job_id") or job_data.get("id")
        start_time = datetime.now()
        
        execution = JobExecution(
            job_id=job_id,
            id_convenio=self.id_convenio,
            rotina=str(rotina),
            status="processing",
            start_time=start_time
        )
        self.db.add(execution)
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            self.log(f"Failed to record execution start: {e}", level="ERROR", job_id=job_id)

        # Merge params
        params_raw = job_data.get("params")
        if params_raw:
            if isinstance(params_raw, dict):
                job_data.update(params_raw)
            elif isinstance(params_raw, str):
                try:
                    parsed = json.loads(params_raw)
                    if isinstance(parsed, dict):
                        job_data.update(parsed)
                except Exception as e:
                    self.log(f"Failed to parse job params: {e}", level="WARN", job_id=job_id)

        # Garantir extração de credenciais a partir do job_data/params mesclado (schema isolation)
        self._extract_credentials_from_dict(job_data)
        if not self.username or not self.password:
            self._load_credentials(job_data)

        results = []
        error_msg = None
        error_cat = "scraper_error"

        # Map routines (op0, op1, op2, etc.)
        op_name = rotina if rotina.startswith("op") else f"op{rotina}"

        # Modelo novo: a sessão HTTP é a AUTORIDADE (SSO alimenta self.session
        # e _injetar_cookies_driver replica no Chrome). O sync inverso
        # (Selenium→session) foi removido — cookies velhos do driver
        # sobrescreviam o PHPSESSID válido do SSO.

        for attempt in range(self.max_retries):
            try:
                # Decisão de login pela SONDA HTTP (não pela contagem de cookies —
                # cookies podiam existir com sessão expirada). attempt>0 sempre
                # refaz (a OP falhou; a sessão pode ter morrido no meio).
                need_login = attempt > 0 or not self.is_logged_in()

                if need_login:
                    self.log("Sessão ABA_clmf ausente/expirada. Iniciando login (API + SSO)...", job_id=job_id)
                    if not self.login():
                        raise Exception("LOGIN_REJEITADO: falha no login ABA_clmf (API do painel + SSO)")

                # Execute mapped OP
                results = self.execute_op(op_name, job_data)
                execution.status = "success"
                break
            except Exception as e:
                error_msg = str(e)
                self.log(f"Attempt {attempt+1} failed: {error_msg}", level="ERROR", job_id=job_id)
                if attempt < self.max_retries - 1:
                    time.sleep(3)
                else:
                    execution.status = "error"

        execution.end_time = datetime.now()
        execution.duration_seconds = int((execution.end_time - start_time).total_seconds())
        execution.items_found = len(results) if isinstance(results, list) else 1
        
        if execution.status != "success":
            execution.error_message = error_msg[:1000] if error_msg else "Unknown Error"
            execution.error_category = error_cat
        
        try:
            self.db.commit()
        except: self.db.rollback()
        
        if execution.status == "error":
            raise Exception(f"Job failed internally: {error_msg}")
            
        return results
