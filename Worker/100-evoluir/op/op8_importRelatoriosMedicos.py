import os
import re
import urllib.parse

BASE_URL = "https://sistemaevoluir.com.br/painel/relatorios/relatorio-medico"

# Teto de segurança do modo "todos": 50 páginas x per_page=500 = até 25 mil linhas.
MAX_PAGINAS = 50
PER_PAGE = 500

DATE_RE = re.compile(r'\b(\d{2})/(\d{2})/(\d{4})\b')


def clean_html(text):
    # Remove tags HTML e espaços sobressalentes
    cleaned = re.sub(r'<[^>]+>', ' ', text)
    return " ".join(cleaned.split()).strip()


def _to_iso(date_match):
    """Converte match DD/MM/AAAA para AAAA-MM-DD."""
    d, m, y = date_match
    return f"{y}-{m}-{d}"


def _id_relatorio_from_url(url):
    """Deriva a chave estável do documento a partir do nome do arquivo do PDF.

    Ex.: .../arquivosusuario/4802b81b_ea2a_4003_a626_7f3691e88265.pdf
         -> 4802b81b_ea2a_4003_a626_7f3691e88265
    """
    basename = os.path.basename(urllib.parse.urlparse(url).path)
    return os.path.splitext(basename)[0] or basename


def parse_relatorios_html(html):
    """Extrai os relatórios médicos da tabela da página.

    Colunas esperadas por linha (padrão capturado do portal):
    <td>paciente</td><td>plano</td><td>médico</td><td>data doc</td>
    <td>data validade</td><td><a href="...pdf">[File]</a></td>
    """
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
    relatorios = []

    for row in rows:
        link_match = re.search(r'href="([^"]+)"', row)
        if not link_match:
            continue  # cabeçalho/linha sem arquivo

        url_arquivo = urllib.parse.urljoin(BASE_URL + "/", link_match.group(1))
        id_relatorio = _id_relatorio_from_url(url_arquivo)
        if not id_relatorio:
            continue

        tds = [clean_html(td) for td in re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)]
        if len(tds) < 5:
            continue

        dates = DATE_RE.findall(row)
        data_doc = _to_iso(dates[0]) if len(dates) >= 1 else None
        data_validade = _to_iso(dates[1]) if len(dates) >= 2 else None

        nome_medico = tds[2].strip() or None

        relatorios.append({
            "nome_paciente": tds[0].strip(),
            "plano": tds[1].strip() or None,
            "nome_medico": nome_medico,
            "data": data_doc,
            "data_validade": data_validade,
            "url_arquivo": url_arquivo,
            "id_relatorio": id_relatorio,
        })

    return relatorios


def run(scraper, job_data):
    job_id = job_data.get("job_id") or job_data.get("id") or "standalone"
    paciente_id = (job_data.get("paciente_id") or job_data.get("id_paciente") or "").strip()

    relatorios = {}
    if paciente_id:
        scraper.log(f"Importando relatórios médicos do paciente {paciente_id} no Evoluir...", job_id=job_id)
        url = f"{BASE_URL}?paciente_id={urllib.parse.quote(paciente_id)}&per_page={PER_PAGE}"
        resp = scraper.session.get(url, timeout=30)
        if resp.status_code != 200:
            raise ConnectionError(f"Erro ao acessar relatorio-medico ({resp.status_code}): {resp.text[:200]}")
        for r in parse_relatorios_html(resp.text):
            r["id_paciente"] = paciente_id
            relatorios[r["id_relatorio"]] = r
    else:
        scraper.log("Importando relatórios médicos de TODOS os pacientes (paginado)...", job_id=job_id)
        for page in range(1, MAX_PAGINAS + 1):
            url = f"{BASE_URL}?page={page}&per_page={PER_PAGE}"
            resp = scraper.session.get(url, timeout=30)
            if resp.status_code != 200:
                raise ConnectionError(f"Erro na página {page} do relatorio-medico ({resp.status_code}): {resp.text[:200]}")

            page_rows = parse_relatorios_html(resp.text)
            novos = [r for r in page_rows if r["id_relatorio"] not in relatorios]
            scraper.log(f"Página {page}: {len(page_rows)} linhas, {len(novos)} novas.", job_id=job_id)

            for r in novos:
                relatorios[r["id_relatorio"]] = r

            # Fim da paginação: página vazia ou repetindo o conteúdo da anterior
            # (portal ignorando page/per_page cai aqui na 2ª página).
            if not novos:
                break

    result_list = list(relatorios.values())
    scraper.log(f"Encontrados {len(result_list)} relatórios médicos.", job_id=job_id)
    return result_list
