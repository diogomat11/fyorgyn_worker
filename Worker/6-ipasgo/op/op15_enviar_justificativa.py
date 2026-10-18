"""
OP15 - Enviar Justificativa/Observação para guia no regulador do IPASGO (FacPlan).

Fluxo (mesma sessão Selenium da OP0, login garantido pelo scraper):
  1. Bootstrap em GuiasTISS/LocalizarProcedimentos (cookies do módulo);
  2. POST GetGuiaEstaNaEtapaFinalDoRegulacao (verificação, igual ao portal);
  3. POST AddHistoricoObservacao (a justificativa digitada pelo usuário);
  4. Encadeia a OP11 da guia (skip_login) para atualizar o status da
     solicitação no hub — mesmo padrão da OP1.

Params do job:
  - guia: número da guia operadora (obrigatório)
  - guia_prestador: número da guia do prestador (opcional; se ausente, a OP15
    descobre via OP11 antes de enviar)
  - observacao: texto da justificativa (obrigatório)
"""
import os
import sys
import importlib.util
import time

# ── Isolate Environment ──
_mod_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _mod_root not in sys.path:
    sys.path.insert(0, _mod_root)

from core.webplan_client import WebPlanClient

BOOTSTRAP_URL = "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos"


def _bootstrap_localizar_context(driver, scraper, job_id):
    """Navega ao módulo LocalizarProcedimentos e fecha notificações do FacPlan."""
    driver.get(BOOTSTRAP_URL)
    for _ in range(10):
        try:
            if driver.execute_script("return document.readyState;") == "complete":
                break
        except Exception:
            pass
        time.sleep(1)
    time.sleep(2)  # notificações assíncronas renderizarem

    # Reaproveita o fechamento robusta de notificações consolidado na OP11
    spec = importlib.util.spec_from_file_location(
        "op11_import_guias_api", os.path.join(_mod_root, "op", "op11_import_guias_api.py")
    )
    op11_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(op11_mod)
    for attempt in range(5):
        if op11_mod._close_notification_robust(driver, scraper, job_id):
            scraper.log(f"OP15 - Notificação fechada na tentativa {attempt + 1}", job_id=job_id)
            break
    time.sleep(1)


def _rodar_op11_da_guia(scraper, job_data, guia):
    """Executa a OP11 filtrando pela guia operadora e devolve suas linhas."""
    op11_job_data = dict(job_data)
    op11_job_data["guia"] = guia
    op11_job_data["skip_login"] = True
    op11_job_data.pop("data_ini", None)
    op11_job_data.pop("data_fim", None)
    return scraper.execute_op("op11_import_guias_api", op11_job_data) or []


def _descobrir_guia_prestador(scraper, job_data, guia):
    """Descobre o NumeroGuiaPrestador consultando a OP11 pela guia operadora."""
    for item in _rodar_op11_da_guia(scraper, job_data, guia):
        if str(item.get("numero_guia") or "") == str(guia) and item.get("guia_prestador"):
            return str(item["guia_prestador"])
    return None


def run(scraper, job_data):
    driver = scraper.driver
    job_id = job_data.get("job_id")

    guia = str(job_data.get("guia") or job_data.get("numero_guia") or "").strip()
    observacao = str(job_data.get("observacao") or job_data.get("justificativa") or "").strip()
    guia_prestador = str(job_data.get("guia_prestador") or "").strip()

    if not guia:
        raise ValueError("OP15 exige o parâmetro 'guia' (número da guia operadora).")
    if not observacao:
        raise ValueError("OP15 exige o parâmetro 'observacao' (texto da justificativa).")

    scraper.log(
        f"OP15 - Enviando justificativa para a guia {guia} (prestador={guia_prestador or 'a descobrir'})...",
        job_id=job_id
    )

    op11_data = []
    if not guia_prestador:
        scraper.log("OP15 - guia_prestador ausente: consultando OP11 para descobrir...", job_id=job_id)
        guia_prestador = _descobrir_guia_prestador(scraper, job_data, guia)
        if not guia_prestador:
            raise ValueError(
                f"Não foi possível descobrir o número da guia do prestador para a guia {guia} "
                f"(OP11 não retornou resultados com guia_prestador)."
            )
        scraper.log(f"OP15 - guia_prestador descoberto: {guia_prestador}", job_id=job_id)

    _bootstrap_localizar_context(driver, scraper, job_id)
    client = WebPlanClient(driver, referer_url=BOOTSTRAP_URL)

    # 1. Verificação de etapa final do regulamento (mesma sequência do portal)
    try:
        etapa_final = client.post_guia_etapa_final_regulacao(guia, guia_prestador)
        scraper.log(f"OP15 - GetGuiaEstaNaEtapaFinalDoRegulacao: {etapa_final}", job_id=job_id)
    except Exception as etapa_err:
        # Não bloqueia o envio: é uma checagem informativa do portal
        scraper.log(f"OP15 - Etapa final do regulamento indisponível (segue envio): {etapa_err}",
                    level="WARN", job_id=job_id)

    # 2. Inclusão da observação/justificativa
    client.post_add_historico_observacao(
        guia, guia_prestador, observacao,
        libera_pendente_doc=True,
        libera_auditoria_operadora=False,
        libera_aguardando_beneficiario=False,
    )
    scraper.log(f"OP15 - Justificativa enviada para a guia {guia}.", job_id=job_id)

    # 3. Encadeia OP11 pós-envio para atualizar o status/histórico da
    #    solicitação no hub (mesmo padrão da OP1)
    try:
        op11_data = _rodar_op11_da_guia(scraper, job_data, guia)
    except Exception as e:
        scraper.log(f"OP15 - OP11 pós-envio falhou (status não atualizado agora): {e}",
                    level="WARN", job_id=job_id)
        op11_data = []

    return {
        "status": "justificativa_enviada",
        "numero_guia": guia,
        "guia_prestador": guia_prestador,
        "op11_data": op11_data,
    }
