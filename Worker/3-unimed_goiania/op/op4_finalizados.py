"""
OP4 – Unimed Goiânia: Exames Finalizados (Relatório de Séries)

Fluxo 100% HTTP via requests.Session (sem Selenium).
Os dynaHashes são extraídos em cada etapa do HTML retornado
e são válidos durante toda a sessão HTTP ativa.

Saída normalizada (campos principais):
  - guia          : número da guia (ex: "70138883")
  - cd_guia       : id interno da guia no portal (ex: "68864313")
  - paciente      : nome do beneficiário
  - carteirinha   : código do cartão
  - data_atendimento
  - data_nascimento
  - cid
  - cod_procedimento
  - status_biometria
  - equipe        : list[dict] — profissionais vinculados
  - series        : list[dict] — {seq, data, hora}
"""

import re
import json
import html as html_mod
import urllib.parse
from bs4 import BeautifulSoup

BASE_URL = "https://sgucard.unimedgoiania.coop.br/cmagnet"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


# ─────────────────────────── helpers ───────────────────────────

def _extract_dyna(text: str, context: str = "") -> str:
    """Extrai o primeiro dynaHash encontrado em uma string de URL/action."""
    m = re.search(r'[?&;]dynaHash=([a-f0-9]{32})', text)
    if not m:
        raise ValueError(f"[OP4] dynaHash não encontrado {('em: ' + context) if context else ''}")
    return m.group(1)


def _parse_grid_rows(soup: BeautifulSoup) -> list:
    """
    Extrai linhas da grid de guias finalizadas.
    Cada linha retorna:
      cd_guia, guia, data_atendimento, carteirinha, paciente,
      status_biometria, detalhe_url (relativo)
    """
    results = []
    table = soup.find("table", {"id": re.compile(r"MagnetoData", re.I)})
    if not table:
        # fallback: qualquer tabela com MagnetoDataTD
        table = soup.find("table", class_=re.compile(r"Magneto", re.I))
    if not table:
        return results

    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td", class_="MagnetoDataTD")
        if len(cells) < 3:
            continue

        # Célula do Nº guia tem link com cd_guia e dynaHash
        link = None
        for cell in cells:
            a = cell.find("a", href=re.compile(r"cd_guia="))
            if a:
                link = a
                break
        if not link:
            continue

        href = link.get("href", "")
        m_cdg = re.search(r'cd_guia=(\d+)', href)
        if not m_cdg:
            continue
        cd_guia = m_cdg.group(1)

        guia_num = link.get_text(strip=True)

        # Biometria — img com alt descritivo
        status_bio = ""
        img = row.find("img", alt=True)
        if img:
            alt = img["alt"].lower()
            if "sucesso" in alt:
                status_bio = "sucesso"
            elif "problema" in alt or "erro" in alt or "falha" in alt:
                status_bio = "erro"
            elif "ignorada" in alt or "ignore" in alt:
                status_bio = "ignorada"
            else:
                status_bio = alt[:40]

        # Restante das células (data, carteirinha, paciente)
        texts = [c.get_text(" ", strip=True) for c in cells]
        data_atend = ""
        carteirinha = ""
        paciente = ""
        for t in texts:
            if re.match(r'\d{2}/\d{2}/\d{4}', t):
                data_atend = t
            elif re.match(r'\d{4}\.\d{4}\.\d+', t) or re.match(r'\d{12,}', t.replace(".", "").replace("-", "")):
                carteirinha = t
            elif t and not t.isdigit() and len(t) > 5 and t != guia_num:
                paciente = t

        results.append({
            "cd_guia": cd_guia,
            "guia": guia_num,
            "data_atendimento": data_atend,
            "carteirinha": carteirinha,
            "paciente": paciente,
            "status_biometria": status_bio,
            "detalhe_url": href,  # relativo, ex: /cmagnet/exames/sadt/detalhe_guia.do?...
        })
    return results


def _parse_detalhe(html_str: str, guia_base: dict) -> dict:
    """
    Faz parse do HTML da página de detalhe de uma guia.
    Retorna dict normalizado com equipe e series.
    """
    soup = BeautifulSoup(html_str, "html.parser")

    def _label_next(label_text: str) -> str:
        """Busca valor em span.labelinfo após um label com texto dado."""
        for lab in soup.find_all(["label", "td", "span"]):
            if label_text.lower() in lab.get_text().lower():
                nxt = lab.find_next("span", class_="labelinfo")
                if nxt:
                    return nxt.get_text(" ", strip=True)
        return ""

    # Carteirinha + paciente (primeiro span.labelinfo com formato nnn.nnnn.nn... - NOME)
    carteirinha = guia_base.get("carteirinha", "")
    paciente = guia_base.get("paciente", "")
    first_label = soup.find("span", class_="labelinfo")
    if first_label:
        txt = first_label.get_text(" ", strip=True)
        if " - " in txt:
            parts = txt.split(" - ", 1)
            carteirinha = parts[0].strip() or carteirinha
            paciente = parts[1].strip() or paciente

    data_nasc = _label_next("Data de Nascimento") or _label_next("Nasc")
    cid = _label_next("Indicação") or _label_next("CID") or _label_next("Indicacao")
    cod_proc = ""

    # Código do procedimento: td com 10 dígitos numéricos
    for td in soup.find_all("td", class_="MagnetoDataTD"):
        t = td.get_text(strip=True).replace("\xa0", "").replace(" ", "")
        if re.match(r'^\d{8,15}$', t) and len(t) >= 8:
            cod_proc = t
            break

    # ── Equipe ──
    equipe = []
    equipe_header = soup.find("td", string=re.compile(r"Identifica.*Equipe", re.I))
    if equipe_header:
        parent_table = equipe_header.find_parent("table")
        if parent_table:
            eq_rows = parent_table.find_all("tr")
            header_found = False
            for row in eq_rows:
                if "Identifica" in row.get_text():
                    header_found = True
                    continue
                if not header_found:
                    continue
                cells = [c.get_text(strip=True) for c in row.find_all("td", class_="MagnetoDataTD")]
                if len(cells) >= 6:
                    equipe.append({
                        "seq": cells[0],
                        "tipo": cells[1],
                        "cod_profissional": cells[2],
                        "nome_profissional": cells[3],
                        "conselho": cells[4],
                        "registro": cells[5],
                        "uf_conselho": cells[6] if len(cells) > 6 else "",
                        "cbo": cells[7] if len(cells) > 7 else "",
                    })

    # ── Séries ──
    series = []
    serie_header = soup.find(string=re.compile(r"Data de Procedimentos em S.rie", re.I))
    if serie_header:
        # Achar tabela próxima
        container = serie_header.find_parent("table") or serie_header.find_parent("td")
        if container:
            for td in container.find_all("td", class_="MagnetoDataTD"):
                txt = td.get_text(strip=True).replace("\xa0", " ").strip()
                # Formato: "1 - 08/08/2026 09:56" ou "1 - &nbsp;"
                m = re.match(r'(\d+)\s*[-–]\s*(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})', txt)
                if m:
                    series.append({
                        "seq": int(m.group(1)),
                        "data": m.group(2),
                        "hora": m.group(3),
                    })

    # Primeiro profissional da equipe para campos legados
    prof0 = equipe[0] if equipe else {}

    return {
        "cd_guia": guia_base["cd_guia"],
        "guia": guia_base["guia"],
        "data_atendimento": guia_base.get("data_atendimento", ""),
        "carteirinha": carteirinha,
        "paciente": paciente,
        "data_nascimento": data_nasc,
        "cid": cid,
        "cod_procedimento": cod_proc,
        "status_biometria": guia_base.get("status_biometria", ""),
        "nome_profissional": prof0.get("nome_profissional", ""),
        "conselho": prof0.get("conselho", ""),
        "registro": prof0.get("registro", ""),
        "uf_conselho": prof0.get("uf_conselho", ""),
        "cbo": prof0.get("cbo", ""),
        "equipe": equipe,
        "series": series,
    }


# ─────────────────────── login HTTP ────────────────────────────

def _login_http(scraper) -> BeautifulSoup:
    """
    Realiza login via requests.Session no portal SGURCard.
    Retorna a soup da página pós-login (que contém jsonModulosSubmenu).
    """
    import requests as _req

    if not hasattr(scraper, "session") or scraper.session is None:
        scraper.session = _req.Session()

    scraper.session.headers.update(HEADERS)

    # 1) GET Login.do → extrair dynaHash do form action
    r = scraper.session.get(f"{BASE_URL}/Login.do", timeout=30)
    r.encoding = "iso-8859-1"
    soup = BeautifulSoup(r.text, "html.parser")

    form = soup.find("form", action=re.compile(r"Login\.do"))
    if not form:
        raise Exception("[OP4] Form de login não encontrado na página.")
    dyna_login = _extract_dyna(form["action"], "form Login.do")

    # 2) POST login
    payload = {
        "ccsForm": "Login",
        "LOGIN": scraper.username,
        "SENHA": scraper.password,
        "dynaHash": dyna_login,
    }
    r2 = scraper.session.post(
        f"{BASE_URL}/Login.do?ccsForm=Login&dynaHash={dyna_login}",
        data=payload,
        timeout=30,
    )
    r2.encoding = "iso-8859-1"

    if "Sair" not in r2.text and "logout" not in r2.text.lower():
        raise Exception(
            "[OP4] Login HTTP falhou. Verifique credenciais ou se o portal exige CAPTCHA."
        )

    return BeautifulSoup(r2.text, "html.parser")


# ─────────────────────── main execute ──────────────────────────

def execute(scraper, job_data: dict) -> list:
    """
    OP4 – Exames Finalizados (Unimed Goiânia)

    Parâmetros esperados em job_data['params']:
      - data_ini      : "DD/MM/YYYY"
      - data_fim      : "DD/MM/YYYY"
      - guia          : número da guia (opcional, filtro extra)
      - login         : login do portal
      - senha_criptografada : senha criptografada (descriptografada pelo scraper)
    """
    job_id = job_data.get("job_id")
    scraper.log("[OP4] Iniciando extração de Exames Finalizados via HTTP", job_id=job_id)

    params = job_data.get("params", {})
    if isinstance(params, str):
        params = json.loads(params)

    s_dt_ini = (params.get("data_ini") or "").strip()
    s_dt_fim = (params.get("data_fim") or "").strip()
    s_nr_guia = (params.get("guia") or "").strip()

    if not s_dt_ini or not s_dt_fim:
        raise ValueError("[OP4] Parâmetros 'data_ini' e 'data_fim' são obrigatórios.")

    # ── FASE 1: Login HTTP ──
    scraper.log("[OP4] FASE 1: Login HTTP", job_id=job_id)
    soup_home = _login_http(scraper)

    # ── FASE 2: Extrair URL de Exames Finalizados do submenu ──
    scraper.log("[OP4] FASE 2: Extraindo URL de Exames Finalizados do menu", job_id=job_id)
    submenu_input = soup_home.find("input", {"id": "jsonModulosSubmenu"})
    if not submenu_input:
        raise Exception("[OP4] jsonModulosSubmenu não encontrado — login pode ter falhado.")

    submenu_json = json.loads(html_mod.unescape(submenu_input.get("value", "[]")))
    # Flatten: o JSON pode ter nível duplo (modulos -> submenus)
    all_menus = []
    for item in submenu_json:
        all_menus.append(item)
        all_menus.extend(item.get("submenus", []))

    finalizados_entry = next(
        (m for m in all_menus if "finaliz" in m.get("nm_menu", "").lower()),
        None
    )
    if not finalizados_entry:
        raise Exception("[OP4] Menu 'Exames Finalizados' não encontrado no submenu.")

    url_finalizados = "https://sgucard.unimedgoiania.coop.br" + finalizados_entry["url_src"]
    scraper.log(f"[OP4] URL finalizados: {url_finalizados}", job_id=job_id)

    # ── FASE 3: Carregar página sem filtro → extrair dynaHash do form ──
    scraper.log("[OP4] FASE 3: Carregando página de finalizados", job_id=job_id)
    r = scraper.session.get(url_finalizados, timeout=30)
    r.encoding = "iso-8859-1"
    soup_lista = BeautifulSoup(r.text, "html.parser")

    filtro_form = soup_lista.find("form", class_=re.compile(r"ajax-search-filter", re.I))
    if not filtro_form:
        filtro_form = soup_lista.find("form", action=re.compile(r"finalizadas\.do"))
    if not filtro_form:
        raise Exception("[OP4] Formulário de filtro não encontrado na página de finalizados.")

    dyna_filtro = _extract_dyna(filtro_form.get("action", ""), "form filtro finalizadas")

    # ── FASE 4: Aplicar filtro ──
    scraper.log(f"[OP4] FASE 4: Aplicando filtro {s_dt_ini} a {s_dt_fim}", job_id=job_id)
    filtro_params = {
        "s_dt_ini": s_dt_ini,
        "s_dt_fim": s_dt_fim,
        "s_nr_guia": s_nr_guia,
        "s_busca": "1",
        "fgPermiteInativo": "1",
        "dynaHash": dyna_filtro,
    }
    # Reusa query string da URL original de finalizados para manter CD_MENU, z, etc.
    parsed = urllib.parse.urlparse(url_finalizados)
    base_qs = dict(urllib.parse.parse_qsl(parsed.query))
    base_qs.update(filtro_params)
    filtro_url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(base_qs)))

    r = scraper.session.get(filtro_url, timeout=30)
    r.encoding = "iso-8859-1"

    # ── FASE 5: Paginação — coletar TODOS os detalhe_urls ──
    all_guias = []
    page = 1
    while True:
        soup_page = BeautifulSoup(r.text, "html.parser")
        rows = _parse_grid_rows(soup_page)
        scraper.log(f"[OP4] Página {page}: {len(rows)} guias encontradas", job_id=job_id)
        all_guias.extend(rows)

        # Próxima página
        prox = soup_page.find("a", class_="MagnetoNavigatorLink", string=re.compile(r"(Pr[oó]x|Next|>>)", re.I))
        if not prox or not prox.get("href"):
            break
        page += 1
        next_url = "https://sgucard.unimedgoiania.coop.br" + prox["href"]
        scraper.log(f"[OP4] Navegando para página {page}", job_id=job_id)
        r = scraper.session.get(next_url, timeout=30)
        r.encoding = "iso-8859-1"

    scraper.log(f"[OP4] Total de guias coletadas: {len(all_guias)}", job_id=job_id)

    # ── FASE 6: Detalhe de cada guia ──
    # Os dynaHashes por linha são válidos durante a sessão (server-side session-scoped).
    # Coletamos todos ANTES de buscar os detalhes para garantir que a paginação
    # não interfira nos hashes já obtidos.
    results = []
    for i, guia in enumerate(all_guias, 1):
        detalhe_href = guia.get("detalhe_url", "")
        if not detalhe_href:
            continue

        if detalhe_href.startswith("http"):
            detalhe_full = detalhe_href
        else:
            detalhe_full = "https://sgucard.unimedgoiania.coop.br" + detalhe_href

        scraper.log(f"[OP4] Detalhe {i}/{len(all_guias)} — guia {guia['guia']} (cd={guia['cd_guia']})", job_id=job_id)
        try:
            r_det = scraper.session.get(detalhe_full, timeout=30)
            r_det.encoding = "iso-8859-1"
            detalhe = _parse_detalhe(r_det.text, guia)
            results.append(detalhe)
        except Exception as e:
            scraper.log(f"[OP4] Erro no detalhe da guia {guia['guia']}: {e}", level="WARN", job_id=job_id)
            # Inclui o que foi coletado na listagem, sem detalhe
            guia_fallback = dict(guia)
            guia_fallback.setdefault("series", [])
            guia_fallback.setdefault("equipe", [])
            results.append(guia_fallback)

    scraper.log(f"[OP4] Concluído. {len(results)} guias processadas.", job_id=job_id)
    return results
