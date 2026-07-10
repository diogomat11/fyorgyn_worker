# PADRÕES DE ROTINAS E SCRAPPERS (WORKERS)

Este documento define os padrões arquiteturais estritos que devem ser seguidos ao desenvolver novos Scrapers para o `Local_worker`, garantindo que o `dispatcher.py` e o Frontend (React) consigam listar, rotear e executar as chamadas sem erros de incompatibilidade.

## 1. Nomenclatura das Pastas (Worker)
Todas as pastas de convênios dentro de `Local_worker/Worker/` **obrigatoriamente** devem seguir a nomenclatura:
`{ID_CONVENIO}-{nome_do_convenio_minusculo}`

Exemplos Corretos:
- `2-unimed_anapolis` (Pois no banco o ID é 2)
- `3-unimed_goiania` (Pois no banco o ID é 3)
- `6-ipasgo`
- `8-sulamerica`
- `9-amil`

Isso garante que o `factory.py` localize o script apropriado pelo ID dinâmico que o Backend fornece via Jobs.

## 2. Padrão Universal de Operações (Tabela convenio_operacoes)
Para cada scrapper criado na pasta, você deve castrar no banco de dados (na tabela `convenio_operacoes`) as rotinas abaixo seguindo exatamente estes Valores Numéricos (Coluna `valor` no SQL):

- `OP=0`: **Login Auth** (Script apenas realiza autenticação, salva cookies/cache e finaliza com Sucesso sem capturar guias).
- `OP=1`: **Consulta Base** (Verifica estado de paciente pendente de autorizações ou captura informações passivas).
- `OP=2`: **Captura de Guias** (Baixa os XMLs/PDFs autorizados atrelados às carteirinhas).
- `OP=3`: **Execução** (Emissão de faturamentos/guias de guias em lotes).

*Nota: Todas as descrições em frontend devem ser limpas.* Exemplo: "0 - Login Auth", "1 - Consulta Base".

## 3. Padrão Estrutural do Python Scraper
Ao construir seu `scraper.py` (herdando de `BaseScraper`), seu bloco `process_job(self, rotina, job_data)` deve possuir a segregação de execuções com base nos numerais passados pela plataforma:

```python
def process_job(self, rotina, job_data):
    # Se a rotina vir nula ou defasada, assuma '1' (Consulta Padrão)
    if not rotina: rotina = "1"
    
    # ROTINA 0 - Fluxo Exclusivo de Login
    if rotina == "0":
        if not self.driver: self.start_driver()
        self.login()
        return [] # Finaliza após validar acesso na operadora

    # ROTINA 1 - Fluxo de Consulta de Paciente
    elif rotina == "1":
        # MECÂNICA DE FALLBACK EXIGIDA:
        try:
             # Tenta achar um elemento marcante de LOGADO
             self.driver.find_element(By.ID, "elemento_pesquisa_logado")
        except:
             # Se falhar, o trabalhador deve auto-invocar a rotina 0 
             # antes de dar crash para garantir continuidade
             self.start_driver()
             self.login()
             
        # Segue sua lógica normal de Consulta Omitida...
        return self.process_carteirinha(job_data['carteirinha'])
```

Seguindo este modelo, evitamos os bugs de "Sessão Expirada" com requisições fantasmas pelo Dispatcher, reduzindo interações mortas na fila do banco de dados.

## 4. Multi-Operadoras e Parâmetros Complexos (registro_ans e Anexos)

### 4.1 Sub-operadoras e Registro ANS
Quando um convênio possui variações ou sub-operadoras no mesmo portal (ex: Bradesco Saúde com ANS `005711`, Bradesco Operadora com ANS `421715`, Mediservice com ANS `333689` no portal Orizon):
- **Banco de Dados**: O campo `registro_ans` na tabela `convenios` deve ser populado com o código ANS correspondente.
- **Worker**: O script deve ler o `RegistroAns` dos parâmetros (`params` serializado no payload do Job) enviados pelo frontend, garantindo que o mesmo código de worker (ex: `1-bradesco`) atenda a múltiplos cadastros de convênio de forma dinâmica.

### 4.2 Arquivos Remotos e Uploads (RM / AI / RC)
Quando a rotina exige o envio de arquivos anexados (ex: Pedido Médico / Relatório Médico `caminho_arquivo_RM`):
- **Frontend**: O modal de solicitações envia o arquivo físico para `/jobs/upload-anexo` e recebe uma URL relativa. A URL absoluta (resolvida com o backend host) deve ser repassada nos parâmetros.
- **Worker**: O worker deve validar se o parâmetro do arquivo inicia com `http://` ou `https://` e realizar o download para um arquivo temporário local (`tempfile.NamedTemporaryFile`) antes de injetar o caminho físico no campo do Selenium.

