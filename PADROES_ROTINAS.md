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
