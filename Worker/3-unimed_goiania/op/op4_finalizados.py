"""
OP4 – Unimed Goiânia: Exames Finalizados (Relatório de Séries)

Navegação 100% realizada via Selenium (scraper.driver) para manter a sessão
ativa no portal SGURCard e evitar redirecionamentos (type=hashDiff).

Extrai:
  - guia / cd_guia
  - paciente / carteirinha / data_nascimento / cid / cod_procedimento / biometria
  - equipe : list[dict]
  - series : list[dict] — {seq, data, hora}
"""

import re
import json
import time
import html as html_mod
import urllib.parse
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By


def _parse_grid_rows(soup: BeautifulSoup) -> list:
    """
    Extrai linhas da grid de guias finalizadas da tabela MagnetoFormTABLE.
    """
    results = []

    # Procura a tabela que contém linhas com MagnetoDataTD
    tds = soup.find_all("td", class_="MagnetoDataTD")
    if not tds:
        return results

    # Agrupa por <tr> pai
    tr_set = []
    for td in tds:
        tr = td.find_parent("tr")
        if tr and tr not in tr_set:
            tr_set.append(tr)

    for row in tr_set:
        # Procurar o link principal do Nº da guia (contém cd_guia= e texto com dígitos)
        link = None
        for a in row.find_all("a", href=re.compile(r"cd_guia=")):
            href = a.get("href", "")
            # O link do Nº da guia costuma ter DM_CD_SITUACAO_AUTRIZ ou texto puramente numérico
            txt = a.get_text(strip=True)
            if txt.isdigit() and len(txt) >= 6:
                link = a
                break
            elif not link and "cd_guia=" in href:
                link = a

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

        # Extrair texto das células
        cells = row.find_all("td", class_="MagnetoDataTD")
        texts = [c.get_text(" ", strip=True) for c in cells]
        data_atend = ""
        carteirinha = ""
        paciente = ""
        for t in texts:
            if re.match(r'^\d{2}/\d{2}/\d{4}', t):
                data_atend = t
            elif re.match(r'^\d{4}\.\d{4}\.\d+', t) or (re.match(r'^\d{12,}$', t.replace(".", "").replace("-", "")) and len(t) > 12):
                carteirinha = t
            elif t and not t.isdigit() and len(t) > 4 and t != guia_num and not data_atend:
                # Evita pegar links de ícone
                if not re.search(r'equipe|laudo|detalhe', t, re.I):
                    paciente = t

        results.append({
            "cd_guia": cd_guia,
            "guia": guia_num,
            "data_atendimento": data_atend,
            "carteirinha": carteirinha,
            "paciente": paciente,
            "status_biometria": status_bio,
            "detalhe_url": href,
        })

    return results


def _parse_detalhe(html_str: str, guia_base: dict) -> dict:
    """
    Faz parse do HTML da página de detalhe de uma guia.
    """
    soup = BeautifulSoup(html_str, "html.parser")

    def _label_next(label_text: str) -> str:
        for lab in soup.find_all(["label", "td", "span"]):
            if label_text.lower() in lab.get_text().lower():
                nxt = lab.find_next("span", class_="labelinfo")
                if nxt:
                    return nxt.get_text(" ", strip=True)
        return ""

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
        container = serie_header.find_parent("table") or serie_header.find_parent("td")
        if container:
            for td in container.find_all("td", class_="MagnetoDataTD"):
                txt = td.get_text(strip=True).replace("\xa0", " ").strip()
                m = re.match(r'(\d+)\s*[-–]\s*(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})', txt)
                if m:
                    series.append({
                        "seq": int(m.group(1)),
                        "data": m.group(2),
                        "hora": m.group(3),
                    })

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


def execute(scraper, job_data: dict) -> list:
    """
    OP4 – Exames Finalizados (Unimed Goiânia)

    Executa navegação via Selenium (scraper.driver) para manter a sessão ativa.
    """
    job_id = job_data.get("job_id")
    scraper.log("[OP4] Iniciando extração de Exames Finalizados via Selenium", job_id=job_id)

    params = job_data.get("params", {})
    if isinstance(params, str):
        params = json.loads(params)

    s_dt_ini = (params.get("data_ini") or "").strip()
    s_dt_fim = (params.get("data_fim") or "").strip()
    s_nr_guia = (params.get("guia") or "").strip()

    if not s_dt_ini or not s_dt_fim:
        raise ValueError("[OP4] Parâmetros 'data_ini' e 'data_fim' são obrigatórios.")

    # ── FASE 1: Garantir login via Selenium ──
    if not scraper.driver:
        scraper.start_driver()

    scraper.log("[OP4] FASE 1: Efetuando / Verificando Login", job_id=job_id)
    if "sgucard" not in scraper.driver.current_url.lower() or "login" in scraper.driver.current_url.lower():
        scraper.login()

    # ── FASE 2: Obter URL de Exames Finalizados do jsonModulosSubmenu ──
    scraper.log("[OP4] FASE 2: Localizando menu Exames Finalizados", job_id=job_id)
    soup_home = BeautifulSoup(scraper.driver.page_source, "html.parser")
    submenu_input = soup_home.find("input", {"id": "jsonModulosSubmenu"})

    if not submenu_input:
        # Tentar recarregar home para obter submenu
        scraper.driver.get("https://sgucard.unimedgoiania.coop.br/cmagnet/exames/emaberto/lista.do")
        time.sleep(2)
        soup_home = BeautifulSoup(scraper.driver.page_source, "html.parser")
        submenu_input = soup_home.find("input", {"id": "jsonModulosSubmenu"})

    if not submenu_input:
        raise Exception("[OP4] jsonModulosSubmenu não encontrado — login falhou.")

    submenu_json = json.loads(html_mod.unescape(submenu_input.get("value", "[]")))
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

    target_url = "https://sgucard.unimedgoiania.coop.br" + finalizados_entry["url_src"].replace("./", "")
    scraper.log(f"[OP4] Navegando para Exames Finalizados: {target_url}", job_id=job_id)
    scraper.driver.get(target_url)
    time.sleep(3)

    # ── FASE 3: Preencher formulário de filtro e pesquisar ──
    scraper.log(f"[OP4] FASE 3: Aplicando filtro de {s_dt_ini} a {s_dt_fim}", job_id=job_id)
    try:
        dt_ini_elem = scraper.driver.find_element(By.NAME, "s_dt_ini")
        dt_ini_elem.clear()
        dt_ini_elem.send_keys(s_dt_ini)

        dt_fim_elem = scraper.driver.find_element(By.NAME, "s_dt_fim")
        dt_fim_elem.clear()
        dt_fim_elem.send_keys(s_dt_fim)

        if s_nr_guia:
            try:
                guia_elem = scraper.driver.find_element(By.NAME, "s_nr_guia")
                guia_elem.clear()
                guia_elem.send_keys(s_nr_guia)
            except Exception:
                pass

        form_elem = scraper.driver.find_element(
            By.CSS_SELECTOR, "form.ajax-search-filters, form[action*='finalizadas.do']"
        )
        submits = form_elem.find_elements(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
        if submits:
            submits[0].click()
        else:
            scraper.driver.execute_script("arguments[0].submit();", form_elem)

        time.sleep(4)
    except Exception as e:
        scraper.log(f"[OP4] Erro ao submeter formulário de filtro: {e}", level="ERROR", job_id=job_id)
        raise e

    # ── FASE 4: Paginação — coletar guias ──
    all_guias = []
    page = 1
    base_page_url = "https://sgucard.unimedgoiania.coop.br/cmagnet/exames/sadt/finalizadas.do"

    try:
        while True:
            try:
                soup_page = BeautifulSoup(scraper.driver.page_source, "html.parser")
            except Exception as page_err:
                scraper.log(f"[OP4] Erro ao obter page_source na página {page}: {page_err}. Finalizando coleta de páginas.", level="WARN", job_id=job_id)
                break

            rows = _parse_grid_rows(soup_page)
            scraper.log(f"[OP4] Página {page}: {len(rows)} guias encontradas na grid", job_id=job_id)
            all_guias.extend(rows)

            # Verificar link de próxima página
            prox = soup_page.find("a", class_="MagnetoNavigatorLink", string=re.compile(r"(Pr[oó]x|Next|>>)", re.I))
            if not prox or not prox.get("href"):
                break

            next_href = prox.get("href", "")
            if "javascript" in next_href.lower():
                break

            page += 1
            next_url = urllib.parse.urljoin(base_page_url, next_href)
            scraper.log(f"[OP4] Navegando para página {page}: {next_url}", job_id=job_id)
            try:
                scraper.driver.get(next_url)
                time.sleep(2)
            except Exception as nav_err:
                scraper.log(f"[OP4] Erro de conexão ao navegar para página {page}: {nav_err}. Prosseguindo com {len(all_guias)} guias.", level="WARN", job_id=job_id)
                break
    except Exception as e_pagination:
        scraper.log(f"[OP4] Exceção na paginação: {e_pagination}. Total coletado até agora: {len(all_guias)}", level="WARN", job_id=job_id)

    scraper.log(f"[OP4] Total de guias encontradas nas páginas: {len(all_guias)}", job_id=job_id)

    # ── FASE 5: Acessar detalhe de cada guia ──
    results = []
    for i, guia in enumerate(all_guias, 1):
        detalhe_href = guia.get("detalhe_url", "")
        if not detalhe_href:
            continue

        detalhe_full = urllib.parse.urljoin(base_page_url, detalhe_href)
        scraper.log(f"[OP4] Detalhe {i}/{len(all_guias)} — guia {guia['guia']} (cd={guia['cd_guia']})", job_id=job_id)
        try:
            scraper.driver.get(detalhe_full)
            time.sleep(1.5)
            detalhe = _parse_detalhe(scraper.driver.page_source, guia)
            results.append(detalhe)
        except Exception as e:
            scraper.log(f"[OP4] Erro ao buscar detalhe da guia {guia['guia']}: {e}", level="WARN", job_id=job_id)
            guia_fallback = dict(guia)
            guia_fallback.setdefault("series", [])
            guia_fallback.setdefault("equipe", [])
            results.append(guia_fallback)

    scraper.log(f"[OP4] Finalizado com sucesso. Total de guias detalhadas: {len(results)}", job_id=job_id)
    return results
