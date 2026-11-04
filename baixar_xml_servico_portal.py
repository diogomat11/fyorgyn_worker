"""
Spike: baixar o XML TISS de um lote gerado pelo próprio portal (FacPlan/IPASGO).

Fluxo: login OP0 (sessão Selenium) -> LoadLotes (descobre o lote e seus campos)
-> POST /Relatorios/GetXmlServico (ou variante Assync) e inspeção da resposta.

Uso: python baixar_xml_servico_portal.py [codigo_prestador] [id_lote] [user_id]
"""
import json
import os
import sys
import time

WORKER_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Worker")
IPASGO_ROOT = os.path.join(WORKER_ROOT, "6-ipasgo")
for p in (WORKER_ROOT, IPASGO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

CODIGO_PRESTADOR = sys.argv[1] if len(sys.argv) > 1 else "00632-2"
ID_LOTE = sys.argv[2] if len(sys.argv) > 2 else "94651"
USER_ID = int(sys.argv[3]) if len(sys.argv) > 3 else 1

BASE = "https://novowebplanipasgo.facilinformatica.com.br"


def main():
    from selenium_manager import SeleniumManager
    from core.scraper import IpasgoScraper

    mgr = SeleniumManager()
    driver = mgr.get_driver(6, headless=True, user_id=USER_ID)
    scraper = IpasgoScraper(id_convenio=6, headless=True, user_id=USER_ID)
    scraper.driver = driver
    scraper._load_credentials()
    print("[1] Fazendo login (OP0)...")
    scraper.login()
    print("[1] Login OK. URL:", driver.current_url[:80])

    from core.webplan_client import WebPlanClient
    driver.get(BASE + "/FaturamentoAtendimentos")
    time.sleep(3)
    client = WebPlanClient(driver)
    session = client.session

    # ── 2. LoadLotes: achar o lote e inspecionar TODOS os campos ──
    print(f"[2] LoadLotes prestador={CODIGO_PRESTADOR} lote={ID_LOTE}...")
    lotes = []
    for page in range(4):
        resp = session.post(
            BASE + "/FaturamentoAtendimentos/LoadLotes",
            data={"page": page, "quantidadePorPagina": 50,
                  "codigoPrestador": CODIGO_PRESTADOR, "login": ""},
            timeout=60,
        )
        lotes_raw = resp.json()
        if isinstance(lotes_raw, str):
            lotes_raw = json.loads(lotes_raw)
        pagina = lotes_raw.get("Lotes") if isinstance(lotes_raw, dict) else lotes_raw
        if not pagina:
            break
        lotes.extend(pagina)
    print(f"[2] {len(lotes)} lote(s) carregados.")

    alvo = None
    if ID_LOTE == "antigo":
        # lote processado mais antigo (mais provável de ter demonstrativo publicado)
        processados = [l for l in lotes if l.get("DataProcessamento") and l.get("CodigoFatura")]
        processados.sort(key=lambda l: str(l.get("DataProcessamento")))
        alvo = processados[0] if processados else None
        if alvo:
            print("[2] Lote mais antigo processado:", alvo.get("Id"), alvo.get("DataProcessamento"),
                  "fatura", alvo.get("CodigoFatura"))
    else:
        for lote in lotes:
            if str(lote.get("Id")) == str(ID_LOTE):
                alvo = lote
                break
    if alvo is None:
        print("[2] Lote não encontrado. Campos do 1º lote:", )
        if lotes:
            print(json.dumps(lotes[0], ensure_ascii=False, indent=1, default=str)[:1500])
        raise SystemExit(1)
    id_lote_label = str(alvo.get("Id"))
    print("[2] Lote encontrado — campos completos:")
    print(json.dumps(alvo, ensure_ascii=False, indent=1, default=str)[:2000])

    # ── 2b. DemonstrativoCobranca/GetCobrancas: lista de cobranças do prestador ──
    print("[2b] GetCobrancas do prestador...")
    cobrancas = None
    try:
        r = session.get(BASE + "/DemonstrativoCobranca/GetCobrancas",
                        params={"codigoPrestador": str(alvo.get("CodigoPrestador") or CODIGO_PRESTADOR),
                                "page": 0, "quantidadePorPagina": 30},
                        headers={"Accept": "application/json", "Referer": BASE + "/Relatorios"},
                        timeout=60)
        print("    -> HTTP", r.status_code, "|", r.headers.get("Content-Type", ""))
        corpo = r.json()
        if isinstance(corpo, str):
            corpo = json.loads(corpo)
        texto = json.dumps(corpo, ensure_ascii=False, default=str)
        print("    -> corpo (800):", texto[:800])
        cobrancas = corpo
    except Exception as e:
        print("    -> ERRO:", str(e)[:200])

    # ── 3. GetXmlServico — tentativas com combinações plausíveis ──
    id_lote_label = str(alvo.get("Id"))
    candidatos_fatura = [alvo.get("CodigoFatura"), alvo.get("Id"), id_lote_label]
    candidatos_protocolo = ["", alvo.get("Protocolo"), "895854"]
    cod_prest_opcoes = [CODIGO_PRESTADOR, str(alvo.get("CodigoPrestador") or "")]
    tipos_prestador = [alvo.get("TipoPrestador"), 1, 2]

    # enriquecer candidatos com ids vindos das cobranças (mesma fatura/valor)
    if isinstance(cobrancas, dict):
        lista = cobrancas.get("Cobrancas") or cobrancas.get("itens") or cobrancas.get("Data") or []
        if isinstance(lista, list):
            for cob in lista[:30]:
                if not isinstance(cob, dict):
                    continue
                if abs(float(cob.get("Valor") or 0) - float(alvo.get("Valor") or 0)) < 0.01:
                    print("    -> cobrança casando com o valor do lote:", json.dumps(cob, ensure_ascii=False, default=str)[:400])
                    for k in ("CodigoFatura", "FaturaId", "Id", "Codigo"):
                        if cob.get(k):
                            candidatos_fatura.insert(0, cob[k])
                    if cob.get("Protocolo"):
                        candidatos_protocolo.insert(0, cob["Protocolo"])

    tentativas = []
    for fatura in dict.fromkeys(filter(None, candidatos_fatura)):
        for prestador in dict.fromkeys(cod_prest_opcoes):
            for protocolo in dict.fromkeys(candidatos_protocolo):
                for tipo in dict.fromkeys([t for t in tipos_prestador if t is not None]):
                    tentativas.append((fatura, prestador, protocolo, tipo))

    headers = {"X-Requested-With": "XMLHttpRequest",
               "Accept": "application/json, text/javascript, */*; q=0.01",
               "Referer": BASE + "/Relatorios"}

    for fatura, prestador, protocolo, tipo in tentativas[:10]:
        payload = {"codigoFatura": fatura, "codigoPrestador": prestador,
                   "tipoPrestador": tipo, "protocolo": protocolo}
        print(f"[3] GetXmlServico {payload} ...")
        try:
            r = session.post(BASE + "/Relatorios/GetXmlServico", data=payload,
                             headers=headers, timeout=300)
            ct = r.headers.get("Content-Type", "")
            corpo = r.text[:500].replace("\n", " ")
            print(f"    -> HTTP {r.status_code} | {ct} | {corpo}")
            if r.status_code == 200 and "xml" in ct.lower() and len(r.content) > 1000:
                saida = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     f"exports_xml/lote_{id_lote_label}_portal.xml")
                os.makedirs(os.path.dirname(saida), exist_ok=True)
                with open(saida, "wb") as f:
                    f.write(r.content)
                print("    -> XML SALVO EM:", saida, f"({len(r.content)} bytes)")
                return saida
            if r.status_code == 200 and "json" in ct.lower():
                try:
                    d = r.json()
                    if isinstance(d, str):
                        d = json.loads(d)
                    print("    -> JSON:", json.dumps(d, ensure_ascii=False, default=str)[:600])
                except Exception:
                    pass
        except Exception as e:
            print("    -> ERRO:", str(e)[:200])

    print("[3] Sem sucesso no síncrono. Tentando Assync...")
    guid = None
    primeira = tentativas[0] if tentativas else (id_lote_label, CODIGO_PRESTADOR, "", 1)
    fatura, prestador, protocolo, tipo = primeira
    try:
        r = session.post(BASE + "/Relatorios/GetXmlServicoAssync",
                         data={"codigoFatura": fatura, "codigoPrestador": prestador,
                               "tipoPrestador": tipo, "protocolo": protocolo},
                         headers=headers, timeout=120)
        print("    -> Assync:", r.status_code, r.text[:300])
        d = r.json()
        if isinstance(d, str):
            d = json.loads(d)
        guid = (d or {}).get("Guid") or (d or {}).get("guid") or (d or {}).get("Data")
    except Exception as e:
        print("    -> Assync ERRO:", str(e)[:200])

    if guid:
        for i in range(30):
            time.sleep(4)
            r = session.post(BASE + "/Relatorios/CheckXmlServicoAssync",
                             data={"guid": guid}, headers=headers, timeout=60)
            print(f"    -> Check {i+1}:", r.status_code, r.text[:200].replace("\n", " "))
            if r.status_code == 200 and len(r.content) > 1000 and "xml" in r.headers.get("Content-Type", "").lower():
                saida = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     f"exports_xml/lote_{id_lote_label}_portal.xml")
                os.makedirs(os.path.dirname(saida), exist_ok=True)
                with open(saida, "wb") as f:
                    f.write(r.content)
                print("    -> XML SALVO EM:", saida)
                return saida
            if r.status_code == 200:
                try:
                    d = r.json()
                    if isinstance(d, str):
                        d = json.loads(d)
                    if isinstance(d, dict) and (d.get("Completed") or d.get("Concluido")):
                        print("    -> Concluído sem corpo:", json.dumps(d, default=str)[:400])
                        break
                except Exception:
                    pass
    print("[4] DemonstrativoPagamento/Pesquisar (mapear demonstrativos)...")
    try:
        r = session.get(BASE + "/DemonstrativoPagamento/Pesquisar",
                        params={"codigoPrestador": str(alvo.get("CodigoPrestador") or CODIGO_PRESTADOR),
                                "page": 0, "quantidadePorPagina": 10},
                        headers={"Accept": "application/json", "Referer": BASE + "/DemonstrativoPagamento"},
                        timeout=60)
        corpo = r.text[:400].replace("\n", " ")
        print(f"    -> HTTP {r.status_code} | {corpo}")
        if r.status_code == 200 and r.text.strip().startswith("{"):
            d = r.json()
            if isinstance(d, str):
                d = json.loads(d)
            texto = json.dumps(d, ensure_ascii=False, default=str)
            print("    -> corpo (600):", texto[:600])
            itens = (d or {}).get("Demonstrativos") or (d or {}).get("itens") or []
            if isinstance(itens, list) and itens:
                demo = itens[0]
                demo_id = demo.get("Id") or demo.get("Codigo") or demo.get("Protocolo")
                if demo_id is not None:
                    r2 = session.get(BASE + "/DemonstrativoPagamento/XmlPagamento",
                                     params={"id": demo_id},
                                     headers={"Referer": BASE + "/DemonstrativoPagamento"},
                                     timeout=120)
                    print(f"    -> XmlPagamento(id={demo_id}): HTTP {r2.status_code} | "
                          f"{r2.headers.get('Content-Type', '')} | {len(r2.content)} bytes | "
                          f"{r2.text[:200].replace(chr(10), ' ')}")
    except Exception as e:
        print("    -> ERRO:", str(e)[:200])

    print("[FIM] Sem XML obtido — inspecionar respostas acima.")


if __name__ == "__main__":
    main()
