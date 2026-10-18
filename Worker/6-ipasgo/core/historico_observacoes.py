"""
Histórico de Observações de guias no regulador do IPASGO (FacPlan).

Funções puras (sem Selenium/requests) compartilhadas entre OP11 (leitura do
histórico de guias não autorizadas) e OP15 (envio de justificativa).

Endpoints atendidos (base novowebplanipasgo.facilinformatica.com.br):
- GET  /LocalizarProcedimentos/GetHistoricoObservacao?param=<base64>&_=ts
- POST /LocalizarProcedimentos/GetGuiaEstaNaEtapaFinalDoRegulacao (form)
- POST /LocalizarProcedimentos/AddHistoricoObservacao (json)

O `param` do GET é o Base64 do JSON:
  {"NumeroGuiaOperadora":"26106190","NumeroGuiaPrestador":"00631201102692873601"}
(ambos os números como string; o padding '=' vai URL-encoded como %3D).
"""
import base64
import json
import re
from datetime import datetime, timezone

# ASP.NET: "/Date(1791314605000)/" (ms desde epoch, opcionalmente com offset)
_ASPNET_DATE_RE = re.compile(r'/Date\((\d+)([+-]\d{4})?\)/')


def build_historico_param(numero_guia_operadora, numero_guia_prestador):
    """Monta o valor do query param `param` do GetHistoricoObservacao.

    O portal serializa sem espaços (separadores compactos) — testado contra a
    requisição real: base64 de {"NumeroGuiaOperadora":"26106190","NumeroGuiaPrestador":"00631201102692873601"}.
    """
    payload = json.dumps(
        {
            "NumeroGuiaOperadora": str(numero_guia_operadora),
            "NumeroGuiaPrestador": str(numero_guia_prestador),
        },
        separators=(",", ":"),
    )
    return base64.b64encode(payload.encode("utf-8")).decode("ascii")


def parse_aspnet_datetime(value):
    """Converte '/Date(1791314605000)/' em datetime; None se inválido.

    O timestamp do ASP.NET é UTC em milissegundos; o portal exibe no fuso de
    Brasília (-03), então normalizamos para -03:00 para a exibição bater com o
    site (ex.: 1791314605000 → 2026-10-06T16:23:25-03:00).
    """
    if not value:
        return None
    match = _ASPNET_DATE_RE.search(str(value))
    if not match:
        return None
    ms = int(match.group(1))
    dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    from datetime import timedelta
    return dt.astimezone(timezone(timedelta(hours=-3)))


def normalizar_historico(itens):
    """Normaliza a lista crua do GetHistoricoObservacao para o formato interno.

    Saída: lista ordenada por data_hora DESC (mais recente primeiro), cada item:
    {data_hora (ISO), usuario, login, observacao (HTML original),
     libera_pendente_doc, libera_auditoria_operadora,
     libera_aguardando_beneficiario}
    """
    if not isinstance(itens, list):
        return []

    normalizados = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        dt = parse_aspnet_datetime(item.get("DataHora"))
        normalizados.append({
            "data_hora": dt.isoformat() if dt else None,
            "usuario": item.get("Usuario"),
            "login": item.get("Login"),
            "observacao": item.get("Observacao"),
            "libera_pendente_doc": bool(item.get("LiberaPendenteDoc", False)),
            "libera_auditoria_operadora": bool(item.get("LiberaAuditoriaOperadora", False)),
            "libera_aguardando_beneficiario": bool(item.get("LiberaAguardandoBeneficiario", False)),
        })

    normalizados.sort(
        key=lambda x: x.get("data_hora") or "",
        reverse=True,
    )
    return normalizados
