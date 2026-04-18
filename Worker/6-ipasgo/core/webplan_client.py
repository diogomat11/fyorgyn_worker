import requests
import time
import json
import logging

class WebPlanClient:
    def __init__(self, driver):
        """
        Inicia o client HTTP baseado em requisições a partir de um driver Selenium logado na OP0.
        """
        self.driver = driver
        self.session = self.get_authenticated_session()

    def get_authenticated_session(self):
        """
        Captura os cookies do Selenium e converte num objeto requests.Session().
        """
        # Extrai User-Agent e cookies da sessão ativa atual (OP6 já navegou para a correta)
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
            "Referer": "https://novowebplanipasgo.facilinformatica.com.br/GuiasTISS/FaturamentoAtendimentos"
        })
        
        for cookie in selenium_cookies:
            # We explicitly set the domain parameter to prevent requests from ignoring it
            domain = cookie.get('domain', 'novowebplanipasgo.facilinformatica.com.br')
            # remove starting dot if present for standard requests behavior although requests handles it
            session.cookies.set(cookie['name'], cookie['value'], domain=domain)
            
        return session

    def post_consultar_guias(self, page=1, codigo_prestador="", guia="", data_ini="", data_fim="", carteira="", codigo_beneficiario="", situacao=""):
        """
        OP11 - POST para busca de guias no endpoint LocalizarProcedimentos/Localizar
        """
        url = "https://novowebplanipasgo.facilinformatica.com.br/LocalizarProcedimentos/Localizar"
        
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01"
        }
        
        payload = {
            "CodigoPrestador": str(codigo_prestador) if codigo_prestador else "",
            "NumeroGuia": str(guia) if guia else "null",
            "NumeroGuiaPrestador": "",
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
                resp = self.session.post(url, headers=headers, json=payload, timeout=20)
                
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
                resp = self.session.post(url, headers=headers, json=payload, timeout=20)
                
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
                resp = self.session.post(url, headers=headers, data=payload, timeout=20)
                
                if 'text/html' in resp.headers.get('Content-Type', ''):
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
