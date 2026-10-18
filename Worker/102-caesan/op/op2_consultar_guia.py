from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import TYPE_CHECKING

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

# ── Isolate Environment (Fix Crosstalk) ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path = [p for p in sys.path if not ("Worker" in p and os.path.basename(p)[0].isdigit() and p != _mod_root)]
if sys.path[0] != _mod_root:
    sys.path.insert(0, _mod_root)

from config.constants import DEFAULT_TIMEOUT, URL_CONSULTA_SOLICITACOES
from core.bios_client import BiosClient

if TYPE_CHECKING:
    from base_scraper import BaseScraper


def _normalizar_procedimento(proc: dict, base: dict) -> dict:
    """Converte um item de lstprocedimentos no record do contrato do hub.

    Quantidades castadas para int (BIOS devolve floats; o hub faz _parse_int
    que não aceita '1.0')."""
    def _to_int(val):
        try:
            return int(float(val or 0))
        except (TypeError, ValueError):
            return 0

    record = dict(base)
    record.update({
        "codigo_terapia": str(proc.get("codprocedimento", "")).strip(),
        "nome_terapia": proc.get("descricao"),
        "qtde_solicitada": _to_int(proc.get("qtdsolicitada")),
        "sessoes_autorizadas": _to_int(proc.get("qtdautorizada")),
    })
    return record


def run(scraper: "BaseScraper", job_data: dict) -> list[dict]:
    """
    OP2 — Consultar solicitação/guia no webservice BIOS.

    Fluxo: OP0 (sessão) → página consultar-solicitacoes → POST
    {"coddao":490,"parametros":["W8",<guia>,<prestador>]}.
    Retorna lista de records no contrato do hub (bulk_upsert_guias_from_json):
    Autorizado → base_guias; Pendente/Negado → solicitacoes.
    """
    job_id = job_data.get("job_id")
    guia = str(
        job_data.get("guia")
        or job_data.get("numero_guia")
        or job_data.get("numero_solicitacao")
        or ""
    ).strip()
    if not guia:
        raise ValueError("Parâmetro obrigatório ausente: guia (número da solicitação)")

    cod_prestador = (
        getattr(scraper, "cod_prestador", None)
        or job_data.get("cod_prestador")
        or job_data.get("codigoPrestador")
    )
    if not cod_prestador:
        raise ValueError("Parâmetro obrigatório ausente: cod_prestador (credencial do tenant)")

    driver = scraper.driver

    # 1. Página de consulta (garante sessão/domínio + cookies atualizados)
    driver.get(URL_CONSULTA_SOLICITACOES)
    WebDriverWait(driver, DEFAULT_TIMEOUT).until(
        lambda d: (d.execute_script("return document.readyState") or "") == "complete"
    )
    scraper.log(f"[OP2] Página de consulta carregada — consultando guia {guia} (prestador {cod_prestador})", job_id=job_id)

    # 2. POST no webservice BIOS com a sessão do Selenium
    client = BiosClient(driver)
    data = client.consultar_guia(guia, cod_prestador)

    conteudo = data.get("conteudo") or {}
    if not isinstance(conteudo, dict) or not conteudo:
        raise ValueError(f"BIOS retornou conteúdo vazio para a guia {guia}: {data.get('mensagem')}")

    status = str(conteudo.get("status") or "").strip() or "Pendente"
    base = {
        "guia": str(conteudo.get("sequencia") or guia).strip(),
        "status_guia": status,
        "senha": str(conteudo.get("codautorizacao") or "").strip() or None,
        "data_solicitacao": conteudo.get("dtpedido"),
        "data_autorizacao": conteudo.get("dtautorizacao"),
        "codigo_beneficiario": str(conteudo.get("codassociado") or "").strip() or None,
        "beneficiario": conteudo.get("beneficiario"),
        "guia_prestador": None,
        "carteirinha_id": job_data.get("carteirinha_id"),
        "carteira": job_data.get("carteira") or job_data.get("carteirinha"),
        "id_convenio": job_data.get("id_convenio"),
        "observacao": conteudo.get("observacao"),
        "timestamp_captura": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "tipo": conteudo.get("tipo"),
        "plano": conteudo.get("nomplano"),
        "medico": conteudo.get("nommedico"),
        "secretaria_solicitante": conteudo.get("secretsolic"),
    }

    procedimentos = conteudo.get("lstprocedimentos") or []
    if procedimentos:
        records = [_normalizar_procedimento(p, base) for p in procedimentos]
    else:
        records = [dict(base)]

    scraper.log(
        f"[OP2] Guia {guia}: status='{status}' | {len(records)} procedimento(s) | "
        f"dtautorizacao={conteudo.get('dtautorizacao')}",
        job_id=job_id
    )
    return records
