"""
OP4 – Unimed Goiânia: Exames Finalizados (Relatório de Séries)

Navegação 100% realizada via Selenium (scraper.driver) para manter a sessão
ativa no portal SGURCard e evitar redirecionamentos (type=hashDiff).

Resiliência & Retomada Inteligente:
  - Notifica atividade ao SeleniumManager (touch_activity) para evitar fechamento por idle.
  - Verifica se o driver está ativo antes de cada requisição de detalhe.
  - Se o driver cair ou a conexão for recusada mid-loop:
      * Re-inicia o Chrome driver.
      * Efettua login automático se necessário.
      * Re-aplica o filtro da rotina (datas / guia).
      * Retoma o processamentoEXATAMENTE a partir do item onde ocorreu o erro.
  - Pula itens cujo detalheId já consta inserido na base para o id_lote atual.
"""

import os
import re
import json
import time
import html as html_mod
import urllib.parse
from datetime import datetime, timezone, date
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

# Tamanho do lote de guias enviadas ao hub por entrega parcial (chunks).
# Jobs longos (5k+ guias ≈ horas) não podem depender de uma única resposta
# HTTP no fim — o dispatcher expira em 600s e o resultado se perde.
OP4_CHUNK_SIZE = max(1, int(os.environ.get("OP4_CHUNK_SIZE", "200")))

# Fetch do detalhe via HTTP (requests) reutilizando os cookies do Chrome:
# ~0.3–0.6s/guia contra ~2s/guia do driver.get. Qualquer falha cai para o
# caminho Selenium original (resiliente, com recuperação de sessão).
OP4_HTTP_SLEEP = float(os.environ.get("OP4_HTTP_SLEEP", "0.25"))
OP4_HTTP_TIMEOUT = float(os.environ.get("OP4_HTTP_TIMEOUT", "15"))
_UA_FALLBACK = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")


def _invalidate_http_session(scraper):
    """Descarta a sessão HTTP (após re-login as cookies do portal mudam)."""
    try:
        if getattr(scraper, "_op4_http", None):
            scraper._op4_http.close()
    except Exception:
        pass
    scraper._op4_http = None
    scraper._op4_http_ua = None


def _get_http_session(scraper):
    """requests.Session sincronizada com os cookies do Chrome ativo."""
    import requests as _requests

    sess = getattr(scraper, "_op4_http", None)
    if sess is None:
        sess = _requests.Session()
        ua = getattr(scraper, "_op4_http_ua", None)
        if not ua:
            try:
                ua = scraper.driver.execute_script("return navigator.userAgent;")
            except Exception:
                ua = None
        sess.headers.update({
            "User-Agent": ua or _UA_FALLBACK,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Referer": "https://sgucard.unimedgoiania.coop.br/cmagnet/exames/sadt/finalizadas.do",
        })
        scraper._op4_http = sess
    # Re-sincroniza cookies a cada chamada (barato; portal pode rotacionar)
    try:
        for ck in scraper.driver.get_cookies():
            sess.cookies.set(ck["name"], ck["value"], domain=ck.get("domain") or None)
    except Exception:
        _invalidate_http_session(scraper)
        return None
    return sess


def _looks_like_detalhe(html_str: str) -> bool:
    """Marcadores positivos da página de detalhe (login/erro não têm)."""
    if not html_str:
        return False
    h = html_str[:60000]
    return ("labelinfo" in h) or ("MagnetoDataTD" in h)


def _http_fetch_detalhe(scraper, url: str):
    """
    Busca o HTML de detalhe via HTTP rápido. Retorna o HTML ou None
    (falha/expiração → chamador usa o fallback Selenium).
    """
    try:
        sess = _get_http_session(scraper)
        if sess is None:
            return None
        r = sess.get(url, timeout=OP4_HTTP_TIMEOUT, allow_redirects=True)
        if r.status_code == 200 and _looks_like_detalhe(r.text):
            return r.text
        # Sessão pode ter expirado (login/redirect): re-sincroniza e tenta 1x
        _invalidate_http_session(scraper)
        sess = _get_http_session(scraper)
        if sess is None:
            return None
        r2 = sess.get(url, timeout=OP4_HTTP_TIMEOUT, allow_redirects=True)
        if r2.status_code == 200 and _looks_like_detalhe(r2.text):
            return r2.text
        return None
    except Exception:
        _invalidate_http_session(scraper)
        return None


def _parse_date_br(val) -> "date | None":
    """'18/09/2026' -> date (ou None)."""
    try:
        s = str(val or "").strip()
        if not s:
            return None
        d, m, y = s.split("/")
        return date(int(y), int(m), int(d))
    except Exception:
        return None


def _resolve_lote_id_worker_side(scraper, job_id: int, job_data: dict, params: dict):
    """
    Resolve o id_lote direto no banco com a MESMA regra do hub
    (_resolve_op4_lote: convenio + user + cod_prestador + data_fim).

    Jobs criados via API chegam sem id_lote nos params; sem isso, o mecanismo
    de retomada (existing_detalhe_ids) nunca ativa e cada nova tentativa
    re-processa TODAS as guias do zero.
    """
    if params.get("id_lote") or params.get("id_lote_interno"):
        return params.get("id_lote") or params.get("id_lote_interno")
    if not getattr(scraper, "db", None):
        return None
    try:
        from models import LoteConvenio
        cod_prestador = str(params.get("cod_prestador") or params.get("codigoPrestador") or "2209525").strip()
        dt_fim = _parse_date_br(params.get("data_fim"))
        lote = scraper.db.query(LoteConvenio).filter(
            LoteConvenio.id_convenio == (job_data.get("id_convenio") or 3),
            LoteConvenio.user_id == job_data.get("user_id"),
            LoteConvenio.cod_prestador == cod_prestador,
            LoteConvenio.data_fim == dt_fim
        ).first()
        return lote.id_lote if lote else None
    except Exception as e:
        scraper.log(f"[OP4] Aviso ao resolver lote worker-side: {e}", level="WARN", job_id=job_id)
        return None


def _bump_job_heartbeat(scraper, job_id: int, status: str = "processing"):
    """
    Renova jobs.updated_at (e status) direto no banco, a partir do worker.

    Sem isso, recover_stuck_jobs do dispatcher (threshold em minutos) considera
    o job morto durante execuções longas e o devolve à fila, gerando
    re-disparos em loop e re-scrapes completos.
    """
    if not getattr(scraper, "db", None) or not job_id:
        return
    try:
        from models import Job as WorkerJob
        jb = scraper.db.query(WorkerJob).filter(WorkerJob.id == job_id).first()
        if jb is not None:
            jb.status = status
            jb.updated_at = datetime.now(timezone.utc)
            scraper.db.commit()
    except Exception:
        try:
            scraper.db.rollback()
        except Exception:
            pass


def _finalize_job_row(scraper, job_id: int, result_payload: dict):
    """
    Grava a finalização do job direto no banco (worker.jobs): status=success,
    result_data e result_consumed=False. O loop de sync do hub consome o
    resultado por aí — a entrega deixa de depender da resposta HTTP ao
    dispatcher (que expira em 600s).
    """
    if not getattr(scraper, "db", None) or not job_id:
        return
    try:
        from models import Job as WorkerJob
        jb = scraper.db.query(WorkerJob).filter(WorkerJob.id == job_id).first()
        if jb is not None:
            jb.status = "success"
            jb.locked_by = None
            jb.result_data = result_payload
            jb.result_consumed = False
            jb.updated_at = datetime.now(timezone.utc)
            scraper.db.commit()
    except Exception as e:
        try:
            scraper.db.rollback()
        except Exception:
            pass
        scraper.log(f"[OP4] Falha ao finalizar job row no banco: {e}", level="WARN", job_id=job_id)


def _is_driver_alive(driver) -> bool:
    """Verifica se o Selenium WebDriver está vivo e respondendo."""
    if not driver:
        return False
    try:
        driver.title
        return True
    except Exception:
        return False


def _recover_driver_session(scraper, job_id, s_dt_ini, s_dt_fim, s_nr_guia):
    """
    Recupera a sessão do robô quando o driver é desconectado ou cai mid-loop:
    Re-inicia o driver, realiza login, navega até Exames Finalizados e re-aplica o filtro.
    """
    scraper.log("[OP4] 🔄 Conexão com o robô perdida! Re-iniciando navegador e recuperando sessão...", level="WARN", job_id=job_id)
    # Re-login troca os cookies do portal: sessão HTTP rápida fica inválida
    _invalidate_http_session(scraper)
    try:
        if scraper.driver:
            try: scraper.driver.quit()
            except Exception: pass
    except Exception: pass

    scraper.start_driver()
    scraper.login()

    soup_home = BeautifulSoup(scraper.driver.page_source, "html.parser")
    submenu_input = soup_home.find("input", {"id": "jsonModulosSubmenu"})
    if not submenu_input:
        scraper.driver.get("https://sgucard.unimedgoiania.coop.br/cmagnet/exames/emaberto/lista.do")
        time.sleep(2)
        soup_home = BeautifulSoup(scraper.driver.page_source, "html.parser")
        submenu_input = soup_home.find("input", {"id": "jsonModulosSubmenu"})

    if submenu_input:
        submenu_json = json.loads(html_mod.unescape(submenu_input.get("value", "[]")))
        all_menus = []
        for item in submenu_json:
            all_menus.append(item)
            all_menus.extend(item.get("submenus", []))

        finalizados_entry = next((m for m in all_menus if "finaliz" in m.get("nm_menu", "").lower()), None)
        if finalizados_entry:
            target_url = "https://sgucard.unimedgoiania.coop.br" + finalizados_entry["url_src"].replace("./", "")
            scraper.driver.get(target_url)
            time.sleep(2)

            # Re-aplicar formulário de filtro
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
                    except Exception: pass

                form_elem = scraper.driver.find_element(
                    By.CSS_SELECTOR, "form.ajax-search-filters, form[action*='finalizadas.do']"
                )
                submits = form_elem.find_elements(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
                if submits:
                    submits[0].click()
                else:
                    scraper.driver.execute_script("arguments[0].submit();", form_elem)
                time.sleep(3)
            except Exception as f_err:
                scraper.log(f"[OP4] Erro ao re-aplicar filtro durante recuperação: {f_err}", level="WARN", job_id=job_id)

    scraper.log("[OP4] ✅ Sessão do robô recuperada com sucesso!", job_id=job_id)


def _parse_grid_rows(soup: BeautifulSoup) -> list:
    """
    Extrai linhas da grid de guias finalizadas da tabela MagnetoFormTABLE.
    """
    results = []

    tds = soup.find_all("td", class_="MagnetoDataTD")
    if not tds:
        return results

    tr_set = []
    for td in tds:
        tr = td.find_parent("tr")
        if tr and tr not in tr_set:
            tr_set.append(tr)

    for row in tr_set:
        link = None
        for a in row.find_all("a", href=re.compile(r"cd_guia=")):
            href = a.get("href", "")
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

    Navegação realizada via Selenium (scraper.driver) com resiliência,
    heartbeat de atividade, recuperação automática de sessão e retomada do item faltante.
    """
    job_id = job_data.get("job_id")
    scraper.log("[OP4] Iniciando extração de Exames Finalizados via Selenium", job_id=job_id)

    params = job_data.get("params", {})
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            params = {}

    s_dt_ini = (params.get("data_ini") or "").strip()
    s_dt_fim = (params.get("data_fim") or "").strip()
    s_nr_guia = (params.get("guia") or "").strip()
    id_lote = params.get("id_lote") or params.get("id_lote_interno")

    if not s_dt_ini or not s_dt_fim:
        raise ValueError("[OP4] Parâmetros 'data_ini' e 'data_fim' são obrigatórios.")

    # ── Resolve o lote worker-side (mesma regra do hub) para habilitar retomada ──
    id_lote = _resolve_lote_id_worker_side(scraper, job_id, job_data, params) or id_lote
    if id_lote:
        params["id_lote"] = id_lote

    # ── Mapeamento de itens já processados na base de dados (se houver id_lote) ──
    existing_detalhe_ids = set()
    if hasattr(scraper, "db") and scraper.db and id_lote:
        try:
            from models import FaturamentoLote
            rows_exist = scraper.db.query(FaturamentoLote.detalheId).filter(
                FaturamentoLote.id_lote == id_lote
            ).all()
            existing_detalhe_ids = {r[0] for r in rows_exist if r[0]}
            if existing_detalhe_ids:
                scraper.log(f"[OP4] Encontrados {len(existing_detalhe_ids)} itens já salvos no Lote {id_lote}. Retomando...", job_id=job_id)
        except Exception as db_err:
            scraper.log(f"[OP4] Aviso ao consultar lote existente: {db_err}", level="WARN", job_id=job_id)

    # ── Entrega parcial em chunks (POST /api/jobs/{id}/result/partial no hub) ──
    # Mantém o job vivo (heartbeat) e persiste as guias no lote CONFORME extrai:
    # progresso visível, retomada real entre tentativas e imunidade ao timeout
    # de 600s do dispatcher (a resposta HTTP deixa de ser o único caminho).
    from hub_client import post_hub

    webhook_hint = params.get("webhook_url") or ""
    chunk_buffer = []
    undelivered = []
    delivered_count = 0
    chunk_seq = 0

    def _flush_chunk(force=False):
        nonlocal chunk_buffer, delivered_count, undelivered, chunk_seq, id_lote
        if not chunk_buffer and not force:
            return
        if not chunk_buffer:
            return
        chunk_seq += 1
        chunk, chunk_buffer = chunk_buffer, []
        chunk_params = dict(params)
        if id_lote:
            chunk_params["id_lote"] = id_lote
        payload = {"data": chunk, "params": chunk_params}
        try:
            resp, _base = post_hub(f"/api/jobs/{job_id}/result/partial", json=payload,
                                   timeout=60, extra_base=webhook_hint)
            if resp is not None and resp.status_code == 200:
                body = resp.json() or {}
                if body.get("id_lote"):
                    id_lote = body["id_lote"]
                    params["id_lote"] = id_lote
                delivered_count += len(chunk)
                scraper.log(f"[OP4] Chunk {chunk_seq} entregue ao hub: {len(chunk)} guias "
                            f"(lote {id_lote}, inseridos {body.get('inserted')}, "
                            f"reabsorvidos {body.get('reabsorvidos', 0)}, total entregue {delivered_count}).",
                            job_id=job_id)
            else:
                status_code = resp.status_code if resp is not None else "sem conexão"
                undelivered.extend(chunk)
                scraper.log(f"[OP4] Chunk {chunk_seq} NÃO entregue (hub respondeu {status_code}). "
                            f"Acumulado para entrega final: {len(undelivered)} guias.", level="WARN", job_id=job_id)
        except Exception as chunk_err:
            undelivered.extend(chunk)
            scraper.log(f"[OP4] Erro ao enviar chunk {chunk_seq}: {chunk_err}. "
                        f"Acumulado para entrega final: {len(undelivered)} guias.", level="WARN", job_id=job_id)
        finally:
            _bump_job_heartbeat(scraper, job_id)

    # ── FASE 1: Garantir login via Selenium ──
    if not scraper.driver:
        scraper.start_driver()

    if hasattr(scraper, "touch_activity"):
        scraper.touch_activity()

    scraper.log("[OP4] FASE 1: Efetuando / Verificando Login", job_id=job_id)
    if "sgucard" not in scraper.driver.current_url.lower() or "login" in scraper.driver.current_url.lower():
        scraper.login()

    # ── FASE 2: Obter URL de Exames Finalizados do jsonModulosSubmenu ──
    scraper.log("[OP4] FASE 2: Localizando menu Exames Finalizados", job_id=job_id)
    soup_home = BeautifulSoup(scraper.driver.page_source, "html.parser")
    submenu_input = soup_home.find("input", {"id": "jsonModulosSubmenu"})

    if not submenu_input:
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
    time.sleep(2)

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
            except Exception: pass

        form_elem = scraper.driver.find_element(
            By.CSS_SELECTOR, "form.ajax-search-filters, form[action*='finalizadas.do']"
        )
        submits = form_elem.find_elements(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
        if submits:
            submits[0].click()
        else:
            scraper.driver.execute_script("arguments[0].submit();", form_elem)

        time.sleep(3)
    except Exception as e:
        scraper.log(f"[OP4] Erro ao submeter formulário de filtro: {e}", level="ERROR", job_id=job_id)
        raise e

    # ── FASE 4: Paginação — coletar guias de todas as páginas ──
    all_guias = []
    page = 1
    base_page_url = "https://sgucard.unimedgoiania.coop.br/cmagnet/exames/sadt/finalizadas.do"

    try:
        while True:
            if hasattr(scraper, "touch_activity"):
                scraper.touch_activity()

            # Heartbeat por página: jobs.updated_at fresco durante toda a execução
            _bump_job_heartbeat(scraper, job_id)

            if not _is_driver_alive(scraper.driver):
                _recover_driver_session(scraper, job_id, s_dt_ini, s_dt_fim, s_nr_guia)

            try:
                soup_page = BeautifulSoup(scraper.driver.page_source, "html.parser")
            except Exception as page_err:
                scraper.log(f"[OP4] Erro na página {page}: {page_err}. Tentando recuperar sessão...", level="WARN", job_id=job_id)
                _recover_driver_session(scraper, job_id, s_dt_ini, s_dt_fim, s_nr_guia)
                soup_page = BeautifulSoup(scraper.driver.page_source, "html.parser")

            rows = _parse_grid_rows(soup_page)
            scraper.log(f"[OP4] Página {page}: {len(rows)} guias encontradas na grid", job_id=job_id)
            all_guias.extend(rows)

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
                scraper.log(f"[OP4] Erro de conexão ao navegar para página {page}: {nav_err}. Tentando recuperar...", level="WARN", job_id=job_id)
                _recover_driver_session(scraper, job_id, s_dt_ini, s_dt_fim, s_nr_guia)
                break
    except Exception as e_pagination:
        scraper.log(f"[OP4] Exceção na paginação: {e_pagination}. Total coletado até agora: {len(all_guias)}", level="WARN", job_id=job_id)

    scraper.log(f"[OP4] Total de guias encontradas nas páginas: {len(all_guias)}", job_id=job_id)

    # ── FASE 5: Acessar detalhe de cada guia (Com Retomada e Resiliência) ──
    results = []
    total_guias = len(all_guias)

    for i, guia in enumerate(all_guias, 1):
        if hasattr(scraper, "touch_activity"):
            scraper.touch_activity()

        detalhe_href = guia.get("detalhe_url", "")
        cd_guia = guia.get("cd_guia", "")

        # Pular se os detalhe_ids desta guia já constam na base de dados do lote
        try:
            probable_did1 = int(f"{cd_guia}1")
            probable_did2 = int(f"{cd_guia}2")
            if probable_did1 in existing_detalhe_ids or probable_did2 in existing_detalhe_ids:
                scraper.log(f"[OP4] Detalhe {i}/{total_guias} — guia {guia['guia']} (cd={cd_guia}) JÁ PROCESSADA. Pulando.", job_id=job_id)
                guia_already = dict(guia)
                guia_already.setdefault("series", [{"seq": 1, "data": guia.get("data_atendimento")}])
                guia_already.setdefault("equipe", [])
                results.append(guia_already)
                continue
        except Exception: pass

        if not detalhe_href:
            continue

        detalhe_full = urllib.parse.urljoin(base_page_url, detalhe_href)
        scraper.log(f"[OP4] Detalhe {i}/{total_guias} — guia {guia['guia']} (cd={cd_guia})", job_id=job_id)

        # 1. Checar saúde do driver antes da requisição (o fallback depende dele)
        if not _is_driver_alive(scraper.driver):
            _recover_driver_session(scraper, job_id, s_dt_ini, s_dt_fim, s_nr_guia)

        # 2. Obter o HTML do detalhe: HTTP rápido (cookies do Chrome) com
        #    fallback Selenium resiliente (retry + recuperação de sessão).
        detalhe = None
        fetched_ok = False

        html_fast = _http_fetch_detalhe(scraper, detalhe_full)
        if html_fast is not None:
            try:
                detalhe = _parse_detalhe(html_fast, guia)
                fetched_ok = True
            except Exception as parse_http_err:
                scraper.log(f"[OP4] Parse do HTTP falhou para guia {guia['guia']} "
                            f"({parse_http_err}); usando Selenium.", level="WARN", job_id=job_id)
                detalhe = None
        if fetched_ok:
            time.sleep(OP4_HTTP_SLEEP)

        if not fetched_ok:
            for attempt in range(1, 3):
                try:
                    scraper.driver.get(detalhe_full)
                    time.sleep(1.0)
                    detalhe = _parse_detalhe(scraper.driver.page_source, guia)
                    fetched_ok = True
                    break
                except Exception as err_item:
                    scraper.log(
                        f"[OP4] Tentativa {attempt}/2 falhou para guia {guia['guia']} (Item {i}/{total_guias}): {err_item}. Tentando recuperar sessão...",
                        level="WARN", job_id=job_id
                    )
                    _recover_driver_session(scraper, job_id, s_dt_ini, s_dt_fim, s_nr_guia)

        if fetched_ok and detalhe is not None:
            results.append(detalhe)
            chunk_buffer.append(detalhe)

        if not fetched_ok:
            scraper.log(f"[OP4] Falha definitiva no detalhe da guia {guia['guia']} (Item {i}). Usando fallback.", level="WARN", job_id=job_id)
            guia_fallback = dict(guia)
            guia_fallback.setdefault("series", [])
            guia_fallback.setdefault("equipe", [])
            results.append(guia_fallback)
            chunk_buffer.append(guia_fallback)

        # Entrega parcial: grava no lote (hub) a cada OP4_CHUNK_SIZE guias
        if len(chunk_buffer) >= OP4_CHUNK_SIZE:
            _flush_chunk()

    # ── FASE 6: Entrega final e finalização do job ──
    _flush_chunk()

    total = len(results)
    if not undelivered:
        meta = {"self_persisted": True, "inserted": delivered_count, "updated": 0, "total": total}
        scraper.log(f"[OP4] Finalizado com sucesso. Total de guias detalhadas: {total} "
                    f"({delivered_count} entregues ao hub em {chunk_seq} chunk(s), lote {id_lote}).", job_id=job_id)
        _finalize_job_row(scraper, job_id, {"status": "success", "data": [], "meta": meta, "job_id": job_id})
        return meta
    else:
        scraper.log(f"[OP4] Finalizado com sucesso. Total: {total}; {len(undelivered)} guias pendentes de chunk — "
                    f"gravando payload completo no job para importação via sync do hub.", level="WARN", job_id=job_id)
        _finalize_job_row(scraper, job_id, {"status": "success", "data": results, "job_id": job_id})
        return {"data": results}
