"""
OP16 - Enviar Justificativas de Recurso de Glosa ao IPASGO (FacPlan).

Fluxo (mesma sessão Selenium da OP0, login garantido pelo scraper):
  1. Bootstrap em GuiasTISS/RecursoGlosa (helper da OP10);
  2. POST /RecursoGlosa/SalvarDigitacaoParcialmente em chunks (o endpoint é de
     digitação parcial: aceita salvamentos incrementais);
  3. Encadeia a OP10 do protocolo (skip_login) para atualizar o estado do lote
     no hub — falha não derruba o job (mesmo padrão da OP15 -> OP11).

Params do job:
  - protocolo: capa/protocolo do lote no portal (obrigatório)
  - id_lote_interno: id_lote em lotes_convenio (usado pelo consumer do hub)
  - servicos: lista de {chave, chave_ut_serv, quantidade_glosada,
    valor_recurso, justificativa} montada pelo hub a partir do banco
    (justificativa vinculada aos itens no frontend).

Payload enviado ao portal (mesma forma do exemplo real):
  {"Capa": 895854, "Servicos": [{"Chave": ..., "ChaveUtServ": ...,
   "QuantidadeGlosada": ..., "ValorRecurso": ..., "Justificativa": "..."}],
   "PesquisarRecursosSalvos": false}
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

# O portal salva a digitação parcialmente: fatiamos serviços grandes em blocos
CHUNK_SERVICOS = 200
DELAY_ENTRE_CHUNKS = 0.5


def _load_op10_module():
    """Carrega a OP10 para reaproveitar o bootstrap do módulo RecursoGlosa."""
    spec = importlib.util.spec_from_file_location(
        "op10_recurso_glosa", os.path.join(_mod_root, "op", "op10_recurso_glosa.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalizar_valor(valor):
    """Mantém o formato do portal: inteiro quando o valor é redondo (130, não 130.0)."""
    if valor is None:
        return None
    numero = round(float(valor), 2)
    return int(numero) if numero.is_integer() else numero


def _normalizar_servico_envio(servico):
    """
    Converte 1 serviço vindo do job (snake_case) para o payload do portal
    (PascalCase). valor_recurso nulo -> valor_unitario_glosado x quantidade
    (fallback já calculado pelo hub; mantido aqui como rede de segurança).
    """
    chave = int(servico["chave"])
    chave_ut_serv = int(servico.get("chave_ut_serv") or chave)
    quantidade = int(servico.get("quantidade_glosada") or 1)

    valor_recurso = servico.get("valor_recurso")
    if valor_recurso in (None, "", 0):
        valor_unitario = servico.get("valor_unitario_glosado") or 0
        valor_recurso = round(float(valor_unitario) * quantidade, 2)

    return {
        "Chave": chave,
        "ChaveUtServ": chave_ut_serv,
        "QuantidadeGlosada": quantidade,
        "ValorRecurso": _normalizar_valor(valor_recurso),
        "Justificativa": str(servico.get("justificativa") or "").strip(),
    }


def _rodar_op10_do_protocolo(scraper, job_data, protocolo):
    """Executa a OP10 do protocolo para atualizar o estado no hub."""
    op10_job_data = dict(job_data)
    op10_job_data["protocolo"] = protocolo
    op10_job_data["skip_login"] = True
    return scraper.execute_op("op10_recurso_glosa", op10_job_data) or {}


def run(scraper, job_data):
    driver = scraper.driver
    job_id = job_data.get("job_id")

    protocolo = str(job_data.get("protocolo") or job_data.get("capa") or "").strip()
    id_lote_interno = job_data.get("id_lote_interno")
    servicos_raw = job_data.get("servicos") or []

    if not protocolo:
        raise ValueError("OP16 exige o parâmetro 'protocolo' (capa do lote no portal).")
    if not isinstance(servicos_raw, list) or not servicos_raw:
        raise ValueError("OP16 exige o parâmetro 'servicos' (lista com chave e justificativa).")

    servicos = [_normalizar_servico_envio(s) for s in servicos_raw]
    sem_justificativa = [s for s in servicos if not s["Justificativa"]]
    if sem_justificativa:
        chaves = ", ".join(str(s["Chave"]) for s in sem_justificativa[:5])
        raise ValueError(
            f"OP16 - {len(sem_justificativa)} serviço(s) sem justificativa (chaves: {chaves}...). "
            "Vincule uma justificativa antes de enviar."
        )

    scraper.log(
        f"OP16 - Enviando {len(servicos)} justificativa(s) de recurso de glosa "
        f"para a capa {protocolo} (lote interno={id_lote_interno or 'não informado'})...",
        job_id=job_id
    )

    # 1. Bootstrap do contexto do módulo RecursoGlosa (helper da OP10)
    op10 = _load_op10_module()
    op10.bootstrap_recurso_glosa_context(driver, scraper, job_id)
    client = WebPlanClient(driver, referer_url=op10.RECURSO_GLOSA_URL)

    # 2. Envio em chunks (salvamento parcial do portal)
    enviados = 0
    total_chunks = (len(servicos) + CHUNK_SERVICOS - 1) // CHUNK_SERVICOS
    for i in range(0, len(servicos), CHUNK_SERVICOS):
        chunk = servicos[i:i + CHUNK_SERVICOS]
        client.post_salvar_digitacao_parcialmente(
            capa=protocolo, servicos=chunk, pesquisar_recursos_salvos=False
        )
        enviados += len(chunk)
        scraper.log(
            f"OP16 - Chunk {i // CHUNK_SERVICOS + 1}/{total_chunks}: "
            f"{len(chunk)} serviço(s) salvos no portal.",
            job_id=job_id
        )
        time.sleep(DELAY_ENTRE_CHUNKS)

    scraper.log(f"OP16 - Justificativas enviadas: {enviados}/{len(servicos)}.", job_id=job_id)

    # 3. Encadeia OP10 pós-envio para atualizar o estado do lote no hub
    op10_data = {}
    try:
        op10_data = _rodar_op10_do_protocolo(scraper, job_data, protocolo)
    except Exception as e:
        scraper.log(f"OP16 - OP10 pós-envio falhou (itens não atualizados agora): {e}",
                    level="WARN", job_id=job_id)

    return {
        "status": "justificativas_enviadas",
        "capa": protocolo,
        "id_lote_interno": id_lote_interno,
        "servicos_enviados": enviados,
        "op10_data": op10_data,
    }
