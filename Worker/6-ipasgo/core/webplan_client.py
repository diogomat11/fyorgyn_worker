import requests
import time
import json
import logging

from core.historico_observacoes import build_historico_param

class WebPlanClient:
    def __init__(self, driver, referer_url=None):
        """
        Inicia o client HTTP baseado em requisições a partir de um driver Selenium logado na OP0.
        referer_url: URL de Referer a usar nos headers (deve corresponder à página que o Selenium navegou).
        """
        self.driver = driver
        self.referer_url = referer_url or "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/FaturamentoAtendimentos"
        self.session = self.get_authenticated_session()

    def get_authenticated_session(self):
        """
        Captura os cookies do Selenium e converte num objeto requests.Session().
        """
        # Extrai User-Agent e cookies da sessão ativa atual
        selenium_cookies = self.driver.get_cookies()
        try:
            user_agent = self.driver.execute_script("return navigator.userAgent;")
        except:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        session = requests.Session()
        
        # Mimetiza perfeitamente o request de um navegador legítimo
        session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://novowebplanipasgo.facilinformatica.com.br",
            "Referer": self.referer_url
        })
        
        for cookie in selenium_cookies:
            # We explicitly set the domain parameter to prevent requests from ignoring it
            domain = cookie.get('domain', 'novowebplanipasgo.facilinformatica.com.br')
            # remove starting dot if present for standard requests behavior although requests handles it
            session.cookies.set(cookie['name'], cookie['value'], domain=domain)
            
        return session

    def refresh_session(self):
        """
        Recaptura os cookies do Selenium e atualiza a sessão HTTP.
        Deve ser chamado após qualquer navegação relevante para garantir que
        os cookies do FacPlan (sessão autenticada) estejam presentes.
        """
        self.session = self.get_authenticated_session()

    def post_consultar_guias(self, page=1, codigo_prestador="", guia="", data_ini="", data_fim="", carteira="", codigo_beneficiario="", situacao=""):
        """
        OP11 - POST para busca de guias no endpoint LocalizarProcedimentos/Localizar
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/LocalizarProcedimentos/Localizar"
        
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos"
        }
        
        payload = {
            "CodigoPrestador": str(codigo_prestador) if codigo_prestador else "",
            "NumeroGuia": str(guia) if guia else None,
            "NumeroGuiaPrestador": None,
            "DtLiberacaoInicial": str(data_ini) if data_ini else "",
            "DtLiberacaoFinal": str(data_fim) if data_fim else "",
            "Page": page,
            "Ordenacao": "DataLiberacao",
            "DestacarOPME": False,
            "PesquisarTotalItens": True,
            "DtAlteracaoInicial": "",
            "DtAlteracaoFinal": "",
            "CodigoEmpresaMedica": "",
            "NumeroCarteira": str(carteira) if carteira else "",
            "CodigoBeneficiario": str(codigo_beneficiario) if codigo_beneficiario else "",
            "Situacao": str(situacao) if situacao else ""
        }
        
        for attempt in range(3):
            try:
                resp = self.session.post(url, headers=headers, json=payload, timeout=60)
                
                if 'text/html' in resp.headers.get('Content-Type', ''):
                    raise ValueError(f"Sessão Rejeitada na OP11 (Retornou HTML). Status: {resp.status_code}. URL: {resp.url}")
                    
                resp.raise_for_status()
                data = resp.json()
                
                if isinstance(data, str):
                    try:
                        import json
                        data = json.loads(data)
                    except:
                        pass
                        
                return data
            except Exception as e:
                logging.error(f"Erro na OP11 (Consultar Guias - Página {page}): {e}")
                if attempt == 2:
                    raise e
                time.sleep(3)

    def post_load_detalhes(self, lote_id, page=0, status=[67, 78, 82], codigo_prestador=""):
        """
        Faz a consulta da página solicitada e retorna o dicionário JSON
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/FaturamentoAtendimentos/LoadDetalhes"
        
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        payload = {
            "loteId": lote_id,
            "status": status,
            "page": page,
            "quantidadePorPagina": "100",
            "filtroDetalhesBeneficiario": "",
            "filtroDetalhesSenhaGuia": "",
            "filtroDetalhesMedExec": "",
            "filtroExibirNaoConfirmados": False,
            "ordenaPor": "DataLiberacao",
            "codigoPrestador": str(codigo_prestador)
        }
        
        for attempt in range(3):
            try:
                # Add timeout para fallback caso o portal trave
                resp = self.session.post(url, headers=headers, json=payload, timeout=60)
                
                # Facil generally redirects to login if unauth
                if 'text/html' in resp.headers.get('Content-Type', ''):
                    raise ValueError(f"Sessão Rejeitada (Retornou HTML). Status: {resp.status_code}. URL: {resp.url}")
                    
                resp.raise_for_status()
                data = resp.json()
                
                # Unwrap double-serialized JSON strings (common in .NET WebPlan)
                if isinstance(data, str):
                    try:
                        import json
                        data = json.loads(data)
                    except:
                        pass
                
                # Check HasError rule
                if isinstance(data, dict) and data.get("HasError", False):
                    raise ValueError(f"API Error: {data.get('ErrorMessage')}")
                    
                return data
            except Exception as e:
                logging.error(f"Erro no LoadDetalhes (Lote {lote_id}, Página {page}): {e}")
                if attempt == 2:
                    raise e
                time.sleep(3)

    def modificar_detalhe(self, detalhe_id, status, data_realizacao, valor_procedimento=""):
        """
        POST para a modificação e fechamento (OP7)
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/FaturamentoAtendimentos/ModificarDetalhe"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        payload = {
            "detalheId": detalhe_id,
            "status": status,
            "dataRealizacao": data_realizacao,
            "valorOutrasDespesas": 0,
            "atualizarValorProcedimento": "false",
            "valorProcedimento": valor_procedimento
        }
        
        for attempt in range(3):
            try:
                resp = self.session.post(url, headers=headers, data=payload, timeout=60)
                
                if 'text/html' in resp.headers.get('Content-Type', ''):
                    if attempt < 2:
                        # Session likely expired — refresh cookies and retry
                        logging.warning(f"ModificarDetalhe retornou HTML (sessão expirada?). Refrescando sessão e retentando...")
                        self.refresh_session()
                        time.sleep(2)
                        continue
                    raise ValueError(f"OP7 Sessão Rejeitada (Retornou HTML). Status: {resp.status_code}. URL: {resp.url}")
                    
                resp.raise_for_status()
                data = resp.json()
                
                # Unwrap double-serialized JSON strings
                if isinstance(data, str):
                    try:
                        import json
                        data = json.loads(data)
                    except:
                        pass
                
                if isinstance(data, dict) and data.get("HasError", False):
                    raise ValueError(f"API Error OP7 ModificarDetalhe: {data.get('ErrorMessage')}")
                return data
            except Exception as e:
                logging.error(f"Erro no ModificarDetalhe (Detalhe {detalhe_id}): {e}")
                if attempt == 2:
                    raise e
                time.sleep(3)

    def gerar_lote(self, codigo_prestador, data_fim):
        """
        OP13 - POST para criar um novo lote de faturamento.
        Endpoint: /FaturamentoAtendimentos/GerarLote
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/FaturamentoAtendimentos/GerarLote"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        payload = {
            "codigoPrestador": codigo_prestador,
            "dataFinal": data_fim
        }
        
        # O GerarLote pode demorar bastante e dar timeout. Aumentamos o timeout ou lidamos com o polling
        for attempt in range(3):
            try:
                resp = self.session.post(url, headers=headers, data=payload, timeout=600)
                if 'text/html' in resp.headers.get('Content-Type', ''):
                    raise ValueError(f"Sessão Rejeitada (Retornou HTML). Status: {resp.status_code}. URL: {resp.url}")
                
                resp.raise_for_status()
                data = resp.json()
                
                if isinstance(data, str):
                    try:
                        import json
                        data = json.loads(data)
                    except:
                        pass
                        
                if isinstance(data, dict) and data.get("HasError", False):
                    raise ValueError(f"API Error GerarLote: {data.get('ErrorMessage')}")
                return data
            except Exception as e:
                logging.error(f"Erro no GerarLote: {e}")
                if attempt == 2:
                    raise e
                time.sleep(3)

    def load_lotes(self, codigo_prestador, page=0, quantidade=10):
        """
        Load Lotes para verificar o status e capturar o ID recém gerado.
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/FaturamentoAtendimentos/LoadLotes"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        payload = {
            "page": page,
            "quantidadePorPagina": quantidade,
            "codigoPrestador": codigo_prestador,
            "login": ""
        }
        
        for attempt in range(3):
            try:
                resp = self.session.post(url, headers=headers, data=payload, timeout=60)
                if 'text/html' in resp.headers.get('Content-Type', ''):
                    raise ValueError(f"Sessão Rejeitada (Retornou HTML). Status: {resp.status_code}")
                
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, str):
                    import json
                    data = json.loads(data)
                return data
            except Exception as e:
                logging.error(f"Erro no LoadLotes: {e}")
                if attempt == 2:
                    raise e
                time.sleep(3)
                
    def cancelar_lote(self, numero_lote, codigo_prestador):
        """
        OP14 - POST para cancelar um lote
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/FaturamentoAtendimentos/CancelarLote"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        payload = {
            "loteId": numero_lote
        }
        
        for attempt in range(3):
            try:
                resp = self.session.post(url, headers=headers, data=payload, timeout=60)
                if 'text/html' in resp.headers.get('Content-Type', ''):
                    raise ValueError(f"Sessão Rejeitada (Retornou HTML). Status: {resp.status_code}. URL: {resp.url}")
                
                resp.raise_for_status()
                data = resp.json()
                
                if isinstance(data, str):
                    try:
                        import json
                        data = json.loads(data)
                    except:
                        pass
                        
                if isinstance(data, dict) and data.get("HasError", False):
                    raise ValueError(f"API Error CancelarLote: {data.get('ErrorMessage')}")
                return data
            except Exception as e:
                logging.error(f"Erro no CancelarLote: {e}")
                if attempt == 2:
                    raise e
                time.sleep(3)

    # ── Histórico de Observações do regulador (OP11 leitura / OP15 justificativa) ──

    def _localizar_headers(self):
        return {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/LocalizarProcedimentos"
        }

    def get_historico_observacao(self, numero_guia_operadora, numero_guia_prestador):
        """
        OP11 - GET do histórico de observações da guia no regulador.

        O endpoint recebe os números da guia embutidos em Base64 no query param
        `param` (padding '=' é URL-encoded pelo requests) e um cache-buster `_`.
        Retorna a lista crua do portal (parse/normalização em core.historico_observacoes).
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/LocalizarProcedimentos/GetHistoricoObservacao"
        params = {
            "param": build_historico_param(numero_guia_operadora, numero_guia_prestador),
            "_": int(time.time() * 1000),
        }

        for attempt in range(3):
            try:
                resp = self.session.get(
                    url, params=params, headers=self._localizar_headers(), timeout=60
                )
                if 'text/html' in resp.headers.get('Content-Type', ''):
                    raise ValueError(
                        f"Sessão Rejeitada no GetHistoricoObservacao (Retornou HTML). "
                        f"Status: {resp.status_code}. URL: {resp.url}"
                    )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, str):
                    data = json.loads(data)
                return data if isinstance(data, list) else []
            except Exception as e:
                logging.error(
                    f"Erro no GetHistoricoObservacao (guia {numero_guia_operadora}): {e}"
                )
                if attempt == 2:
                    raise e
                time.sleep(3)

    def post_guia_etapa_final_regulacao(self, numero_guia_operadora, numero_guia_prestador):
        """
        OP15 - POST que verifica se a guia está na etapa final do regulamento.
        Chamada prévia ao AddHistoricoObservacao (mesma sequência do portal).
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/LocalizarProcedimentos/GetGuiaEstaNaEtapaFinalDoRegulacao"

        headers = self._localizar_headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        payload = {
            "numeroGuiaOperadora": str(numero_guia_operadora),
            "numeroGuiaPrestador": str(numero_guia_prestador),
        }

        for attempt in range(3):
            try:
                resp = self.session.post(url, headers=headers, data=payload, timeout=60)
                if 'text/html' in resp.headers.get('Content-Type', ''):
                    raise ValueError(
                        f"Sessão Rejeitada no GetGuiaEstaNaEtapaFinalDoRegulacao (Retornou HTML). "
                        f"Status: {resp.status_code}. URL: {resp.url}"
                    )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, str):
                    data = json.loads(data)
                if isinstance(data, dict) and data.get("HasError", False):
                    raise ValueError(f"API Error GetGuiaEstaNaEtapaFinalDoRegulacao: {data.get('ErrorMessage')}")
                return data
            except Exception as e:
                logging.error(f"Erro no GetGuiaEstaNaEtapaFinalDoRegulacao (guia {numero_guia_operadora}): {e}")
                if attempt == 2:
                    raise e
                time.sleep(3)

    def post_add_historico_observacao(
        self, numero_guia_operadora, numero_guia_prestador, observacao,
        libera_pendente_doc=True, libera_auditoria_operadora=False,
        libera_aguardando_beneficiario=False,
    ):
        """
        OP15 - POST que inclui uma observação/justificativa na guia no regulador.
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/LocalizarProcedimentos/AddHistoricoObservacao"

        headers = self._localizar_headers()
        headers["Content-Type"] = "application/json;charset=UTF-8"

        payload = {
            "NumeroGuiaOperadora": str(numero_guia_operadora),
            "NumeroGuiaPrestador": str(numero_guia_prestador),
            "Observacao": str(observacao),
            "LiberaPendenteDoc": bool(libera_pendente_doc),
            "LiberaAuditoriaOperadora": bool(libera_auditoria_operadora),
            "LiberaAguardandoBeneficiario": bool(libera_aguardando_beneficiario),
        }

        for attempt in range(3):
            try:
                resp = self.session.post(url, headers=headers, json=payload, timeout=60)
                if 'text/html' in resp.headers.get('Content-Type', ''):
                    raise ValueError(
                        f"Sessão Rejeitada no AddHistoricoObservacao (Retornou HTML). "
                        f"Status: {resp.status_code}. URL: {resp.url}"
                    )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, str):
                    data = json.loads(data)
                if isinstance(data, dict) and data.get("HasError", False):
                    raise ValueError(f"API Error AddHistoricoObservacao: {data.get('ErrorMessage')}")
                return data
            except Exception as e:
                logging.error(f"Erro no AddHistoricoObservacao (guia {numero_guia_operadora}): {e}")
                if attempt == 2:
                    raise e
                time.sleep(3)

    # ── Recurso de Glosa (OP10 importação / OP16 envio de justificativas) ──

    def _recurso_glosa_headers(self):
        return {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/RecursoGlosa"
        }

    def _recurso_glosa_request(self, method, url, **kwargs):
        """
        Executa uma requisição do módulo RecursoGlosa com o padrão da casa:
        retry x3, detecção de sessão expirada (Content-Type HTML) e unwrap
        de JSON duplamente serializado (.NET WebPlan).
        """
        kwargs.setdefault("headers", self._recurso_glosa_headers())
        kwargs.setdefault("timeout", 60)

        for attempt in range(3):
            try:
                resp = self.session.request(method, url, **kwargs)
                if 'text/html' in resp.headers.get('Content-Type', ''):
                    if attempt < 2:
                        logging.warning("RecursoGlosa retornou HTML (sessão expirada?). Refrescando sessão e retentando...")
                        self.refresh_session()
                        time.sleep(2)
                        continue
                    raise ValueError(
                        f"Sessão Rejeitada no RecursoGlosa (Retornou HTML). "
                        f"Status: {resp.status_code}. URL: {resp.url}"
                    )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, str):
                    data = json.loads(data)
                if isinstance(data, dict) and data.get("HasError", False):
                    raise ValueError(f"API Error RecursoGlosa: {data.get('ErrorMessage')}")
                return data
            except Exception as e:
                logging.error(f"Erro no RecursoGlosa ({url}: {e}")
                if attempt == 2:
                    raise e
                time.sleep(3)

    def get_recurso_glosa_capa(self, protocolo):
        """
        OP10 - GET /RecursoGlosa/Carregar?id={protocolo}
        Valida o acesso ao lote (capa) e devolve o JSON inicial, de onde se
        extrai Servicos.NumeroDePaginas (total de páginas de itens do lote).
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/RecursoGlosa/Carregar"
        return self._recurso_glosa_request(
            "GET", url, params={"id": str(protocolo), "_": int(time.time() * 1000)}
        )

    def get_recurso_glosa_servicos(self, protocolo, pagina=1,
                                   apenas_recursando=False, apenas_sem_justificativa=False):
        """
        OP10 - GET /RecursoGlosa/PesquisarServicosLote
        Retorna {QuantidadePorPagina, NumeroDePaginas, Pagina, MensagemDeAte, Servicos[]}.
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/RecursoGlosa/PesquisarServicosLote"
        params = {
            "idCapa": str(protocolo),
            "pagina": int(pagina),
            "apenasRecursando": "true" if apenas_recursando else "false",
            "apenasSemJustificativa": "true" if apenas_sem_justificativa else "false",
            "_": int(time.time() * 1000),
        }
        return self._recurso_glosa_request("GET", url, params=params)

    def post_salvar_digitacao_parcialmente(self, capa, servicos, pesquisar_recursos_salvos=False):
        """
        OP16 - POST /RecursoGlosa/SalvarDigitacaoParcialmente
        Grava as justificativas de recurso dos serviços do lote (capa).

        servicos: lista de dicts com Chave, ChaveUtServ, QuantidadeGlosada,
        ValorRecurso e Justificativa (mesma forma do payload do portal).
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/RecursoGlosa/SalvarDigitacaoParcialmente"

        headers = self._recurso_glosa_headers()
        headers["Content-Type"] = "application/json;charset=UTF-8"

        payload = {
            "Capa": int(capa),
            "Servicos": servicos,
            "PesquisarRecursosSalvos": bool(pesquisar_recursos_salvos),
        }
        return self._recurso_glosa_request("POST", url, headers=headers, json=payload)

    # ── Conferência de Faturamento (OP17 importação / OP18 confirmação) ──

    def _conferencia_headers(self, form=False):
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://novowebplanipasgo.facilinformatica.com.br/ConferenciaFaturamento/Index",
        }
        if form:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        return headers

    def get_conferencia_procedimentos(self, protocolo):
        """
        OP17 - GET /ConferenciaFaturamento/ObterProcedimentos?protocolo={p}&_={ms}

        Cache-buster `_` = timestamp no momento da requisição (mesma forma do
        portal). Retorna o JSON completo: {LimiteDiasFaturamento, Capa:{...
        Guias:[{... Itens:[...]}]}, HasError, Message}.
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/ConferenciaFaturamento/ObterProcedimentos"
        params = {
            "protocolo": str(protocolo),
            "_": int(time.time() * 1000),
        }
        for attempt in range(3):
            try:
                resp = self.session.get(
                    url, params=params, headers=self._conferencia_headers(), timeout=120
                )
                if 'text/html' in resp.headers.get('Content-Type', ''):
                    if attempt < 2:
                        logging.warning("ObterProcedimentos retornou HTML (sessão expirada?). Refrescando...")
                        self.refresh_session()
                        time.sleep(2)
                        continue
                    raise ValueError(
                        f"Sessão Rejeitada no ObterProcedimentos (Retornou HTML). "
                        f"Status: {resp.status_code}. URL: {resp.url}"
                    )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, str):
                    data = json.loads(data)
                if isinstance(data, dict) and data.get("HasError", False):
                    raise ValueError(f"API Error ObterProcedimentos: {data.get('Message')}")
                return data
            except Exception as e:
                logging.error(f"Erro no ObterProcedimentos (protocolo {protocolo}): {e}")
                if attempt == 2:
                    raise e
                time.sleep(3)

    def post_conferir_item(self, id_servico, status, id_detalhe=None):
        """
        OP18 - POST /ConferenciaFaturamento/ConferirItem (form-urlencoded)

        status: 'Aceito' | 'Recusado' | 'Pendente' (domínio do novo portal).
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/ConferenciaFaturamento/ConferirItem"
        payload = {
            "idServico": id_servico,
            "idDetalhe": id_detalhe if id_detalhe is not None else "",
            "status": status,
        }
        for attempt in range(3):
            try:
                resp = self.session.post(
                    url, data=payload, headers=self._conferencia_headers(form=True), timeout=60
                )
                if 'text/html' in resp.headers.get('Content-Type', ''):
                    if attempt < 2:
                        self.refresh_session()
                        time.sleep(2)
                        continue
                    raise ValueError(
                        f"Sessão Rejeitada no ConferirItem (Retornou HTML). "
                        f"Status: {resp.status_code}. URL: {resp.url}"
                    )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, str):
                    data = json.loads(data)
                if isinstance(data, dict) and data.get("HasError", False):
                    raise ValueError(f"API Error ConferirItem: {data.get('Message')}")
                return data
            except Exception as e:
                logging.error(f"Erro no ConferirItem (idServico {id_servico}): {e}")
                if attempt == 2:
                    raise e
                time.sleep(3)

    def post_editar_data_realizacao(self, codigo_prestador, id_servico, data_realizacao_br, id_detalhe=None):
        """
        OP18 - POST /ConferenciaFaturamento/EditarDataRealizacao (form-urlencoded)

        codigo_prestador: código SEM dígito verificador (ex.: '01889' de '01889-2').
        data_realizacao_br: 'dd/MM/yyyy' (URL-encoded pelo requests).
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/ConferenciaFaturamento/EditarDataRealizacao"
        payload = {
            "codigoPrestador": str(codigo_prestador),
            "idServico": id_servico,
            "idDetalhe": id_detalhe if id_detalhe is not None else "",
            "dataRealizacao": data_realizacao_br,
        }
        for attempt in range(3):
            try:
                resp = self.session.post(
                    url, data=payload, headers=self._conferencia_headers(form=True), timeout=60
                )
                if 'text/html' in resp.headers.get('Content-Type', ''):
                    if attempt < 2:
                        self.refresh_session()
                        time.sleep(2)
                        continue
                    raise ValueError(
                        f"Sessão Rejeitada no EditarDataRealizacao (Retornou HTML). "
                        f"Status: {resp.status_code}. URL: {resp.url}"
                    )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, str):
                    data = json.loads(data)
                if isinstance(data, dict) and data.get("HasError", False):
                    raise ValueError(f"API Error EditarDataRealizacao: {data.get('Message')}")
                return data
            except Exception as e:
                logging.error(f"Erro no EditarDataRealizacao (idServico {id_servico}): {e}")
                if attempt == 2:
                    raise e
                time.sleep(3)
