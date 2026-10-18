"""
Client HTTP do webservice BIOS (ws2.bios.inf.br/wsbios/service/V1) usado pela
OP2 do integrador CAESAN.

Padrão WebPlanClient (6-ipasgo): ponte Selenium → requests.Session copiando
cookies + User-Agent do driver logado na OP0. Resposta HTML = sessão expirada.
"""
import json
import logging
import time

import requests

from config.constants import (
    BIOS_TIMEOUT_SEGUNDOS,
    BIOS_TENTATIVAS,
    BIOS_WS_CHAVE,
    BIOS_WS_CODDAO_CONSULTA,
    BIOS_WS_URL,
    PORTAL_ORIGIN,
    URL_CONSULTA_SOLICITACOES,
)


class BiosClient:
    def __init__(self, driver):
        self.driver = driver
        self.session = self.get_authenticated_session()

    def get_authenticated_session(self):
        """Captura cookies do Selenium e converte num requests.Session()."""
        selenium_cookies = self.driver.get_cookies()
        try:
            user_agent = self.driver.execute_script("return navigator.userAgent;")
        except Exception:
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

        session = requests.Session()
        session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": PORTAL_ORIGIN,
            "Referer": URL_CONSULTA_SOLICITACOES,
        })

        for cookie in selenium_cookies:
            domain = cookie.get("domain", "www.caesan.com.br")
            session.cookies.set(cookie["name"], cookie["value"], domain=domain)

        return session

    def refresh_session(self):
        """Recaptura os cookies do Selenium (após navegação relevante)."""
        self.session = self.get_authenticated_session()

    def consultar_guia(self, numero_guia, cod_prestador):
        """
        OP2 — POST de consulta de solicitação/guia.

        Payload fixo: {"coddao":490,"conteudo":null,"parametros":["W8",<guia>,<prestador>]}
        onde <guia> = número da solicitação/guia e <prestador> = cod_prestador.
        """
        payload = {
            "coddao": BIOS_WS_CODDAO_CONSULTA,
            "conteudo": None,
            "parametros": [BIOS_WS_CHAVE, int(numero_guia), str(cod_prestador)],
        }

        for attempt in range(BIOS_TENTATIVAS):
            try:
                resp = self.session.post(BIOS_WS_URL, json=payload, timeout=BIOS_TIMEOUT_SEGUNDOS)

                if "text/html" in resp.headers.get("Content-Type", ""):
                    raise ValueError(
                        f"Sessão rejeitada na OP2 BIOS (retornou HTML). Status: {resp.status_code}. URL: {resp.url}"
                    )

                resp.raise_for_status()
                data = resp.json()

                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except Exception:
                        pass

                codstatus = data.get("codstatus")
                if codstatus != 200:
                    raise ValueError(
                        f"BIOS respondeu codstatus={codstatus}: "
                        f"{(data.get('mensagem') or {}).get('mensagem', data.get('mensagem'))}"
                    )

                return data
            except ValueError:
                # Sessão expirada / erro funcional: relança para o retry da process_job relogar
                raise
            except Exception as e:
                logging.error(f"Erro na OP2 BIOS (guia {numero_guia}, tentativa {attempt+1}): {e}")
                if attempt == BIOS_TENTATIVAS - 1:
                    raise
                time.sleep(3)
