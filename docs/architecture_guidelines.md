# Relatório de Arquitetura e Padronização MultiConv
## Papel: Product Owner / Senior Dev / QA

Esta documentação define os padrões arquiteturais estritos (Frontend, Backend, Local Worker) e os planos de refatoração para garantir a aderência aos padrões SOLID, Clean Code e DRY, garantindo estabilidade e modularidade escalar.

---

## 1. Local Worker (Web Scrapers)

### 1.1 Estado Atual (Problemas Encontrados pelo QA)
- **Quebra de Modularidade:** Scripts não padronizados. O convênio `2-unimed_anapolis` segue um padrão de scaffolding (`core`, `config`, `op`), mas o convênio `3-unimed_goiania` é monolítico (tudo no arquivo `ImportBaseGuias.py`).
- **Sujeira no Root:** Dezenas de scripts soltos no diretório raiz (ex: `test_login.py`, `diag.py`, `check_output.txt`, `op1_output_v10.txt`, `reset_jobs.py`). Isso polui a branch principal e causa confusão no entry-level do desenvolvedor.
- **Acoplamento:** Alguns scripts dependem fortemente de caminhos absolutos locais não previstos em `.env`.

### 1.2 Regras de Negócio e Padrão Exigido (PO + Dev Senior)
- **Estrutura de Pastas Obrigatória (Padrão: `{ID}-{NOME_CONVENIO}`):**
  - `config/`: Constantes e seletores CSS/XPath.
  - `core/`: Arquivo central `scraper.py` implementando a interface `BaseScraper`. O scraper não deve conter nenhuma regra de negócio visual; apenas o controle do SeleniumManager.
  - `infra/`: Helpers de Selenium genéricos (Waiters genéricos).
  - `op/`: Rotinas isoladas. (Ex: `op0_login.py`, `op1_consulta.py`, `op2_captura.py`). O `op0_login` TEM que existir independentemente.
- **Limpeza do Root:** Todos os scripts utilitários e de debug criados (ex: `reset_jobs.py` e `.txt`s de log) deverão ser movidos estritamente para a pasta `/scripts_testes_locais` dentro do Root.

---

## ⚠️ MÓDULOS ESTÁVEIS — ALTERAÇÃO SOMENTE POR PEDIDO EXPRESSO

> Os módulos abaixo estão **100% funcionais e validados em produção**. Qualquer alteração — mesmo refatoração interna — exige **pedido explícito e aprovação do Product Owner**. Nenhum desenvolvedor deve modificá-los por iniciativa própria. Para as implantações da Unimed Goiania, NÃO deve ser feito alterações nas rotinas da Unimed Anápolis, nem mesmo na rotina 0 e 1 da Unimed Goiania que já estão estáveis, exceto se solicitado explicitamente pelo usuário.

| Módulo | Path | Rotinas Estáveis |
|---|---|---|
| Unimed Goiânia | `Local_worker/Worker/3-unimed_goiania/` | `op0_login.py` (login), `op1_consulta.py` (consulta de guias) |
| Unimed Anápolis | `Local_worker/Worker/2-unimed_anapolis/` | `op0_login.py` (login), `op1_consulta.py` (consulta de guias) |

**Regras:**
- Credenciais de acesso exclusivamente via tabela `convenios` no banco remoto (campo `senha_criptografada` + `FERNET_SECRET` no `.env`).
- Nenhuma senha, login ou chave deve ser hardcoded em arquivo de código.
- Não mover, renomear ou refatorar sem pedido expresso.

---

## Fluxo Detalhado — Unimed Anápolis: Rotina 1 (Consulta de Guias)

### Visão Geral
A Rotina 1 da Unimed Anápolis é executada para **cada carteirinha** via o sistema de jobs. O objetivo é capturar todas as guias autorizadas nos últimos 180 dias e registrá-las no banco de dados.

### Atores do Fluxo
- **Dispatcher** (`dispatcher.py`): Busca jobs pendentes no banco, seleciona um Worker livre e envia via HTTP POST.
- **Server** (`server.py`): Recebe o job, instancia o scraper, injeta driver Selenium e delega à rotina.
- **SeleniumManager** (`selenium_manager.py`): Gerencia o pool de instâncias Chrome (máx. 1 por Worker). Reutiliza sessões abertas para evitar re-login.
- **UnimedAnopolisScraper** (`core/scraper.py`): Carrega credenciais do banco, faz login, roteia para `op1_consulta.py`.
- **op0_login.py**: Navega para `https://sgucard.unimedanapolis.com.br/cmagnet/Login.do`, preenche usuário/senha e valida sessão.
- **op1_consulta.py**: Executa toda a navegação e extração de dados da guia.

### Passo a Passo — Rotina 1

```
[Dispatcher]
  ↓ POST /process_job  {job_id, id_convenio=2, rotina='1', carteirinha, ...}
[server.py]
  ↓ SeleniumManager.get_driver(id_convenio=2) → reutiliza ou cria Chrome
  ↓ ScraperFactory.get_scraper(2) → UnimedAnopolisScraper.__init__()
       ↓ _load_credentials() → DB: SELECT usuario, senha_criptografada WHERE id_convenio=2
       ↓ decrypt_password(senha_criptografada) via FERNET_SECRET
  ↓ scraper.driver = driver  (Chrome injetado)
  ↓ scraper.process_job('1', job_data)

[process_job]
  ↓ Tenta find_element(By.ID, 'mainMenuItem2')
      → se FALHA (sem sessão): chama login()
      → se OK: session reuse, pula login
  ↓ login() → op0_login.execute()
       ↓ driver.get(LOGIN_URL)
       ↓ Preenche campo 'login' com username
       ↓ Preenche campo 'passwordTemp' com password
       ↓ Clica 'Button_DoLogin'
       ↓ Valida sessão: busca 'mainMenuItem2' ou URL != Login.do

[op1_consulta.execute()]

  FASE 1 — Navegação até Consulta:
  ↓ close_popup_window() — fecha eventuais janelas secundárias abertas
  ↓ Clica ícone principal 'centro_61' (menu home, se presente)
  ↓ Clica 'mainMenuItem2' (Autorizador / SADTs)
  ↓ Fecha popups abertos automaticamente pelo portal
  ↓ Clica '#centro_3 .MagnetoSubMenuTittle' → SADTs em Aberto
  ↓ Aguarda 3s para carregamento da seção

  FASE 2 — Abertura do formulário de busca por carteirinha:
  ↓ Verifica presença de 'nr_via' (form já disponível) ou 'cadastro_biometria' (botão Nova Consulta)
  ↓ Clica botão 'new_exame' (#cadastro_biometria > div > div[2] > span)
  ↓ Aguarda popup de busca abrir (nova janela/tab)
  ↓ switch_to.window(handles[-1]) — foca na janela do formulário

  FASE 3 — Preenchimento da Carteirinha:
  ↓ funccarteira(carteirinha) → split em x1(4), x2(4), x3(6), x4(2), x5(1)
  ↓ Clica 'ignora-cartao' (bypass de leitura física)
  ↓ Clica 'cad_Benef' (opção de busca por código)
  ↓ Preenche input x1 (prefixo da operadora)
  ↓ Preenche 's_CD_BNF_PADRAO_PTU' com x2+x3+x4+x5 (número do beneficiário)
  ↓ Clica 'botao_verificar'

  FASE 4 — Validação da Carteirinha:
  ↓ Smart loop (até 5s) verificando:
      → JavaScript alert com "inválido" ou "dígito" → lança PermanentError (não tenta novamente)
      → Elemento DOM com mensagem de erro → PermanentError
      → Botão Button_Update / Button_Insert / tabela 'tb_sadt_aberto' → carteira VÁLIDA, continua
  ↓ Se prefixo x1 != '0178' (não é Unimed local):
      → Clica 'Button_Update' (Atualizar Beneficiário) ou 'Button_Insert' (Cadastrar)

  FASE 5 — Aguarda tabela de guias (conteudo-submenu):
  ↓ Loop de até 20s esperando formulário '//*[@id="conteudo-submenu"]/form/...' estar visível
  ↓ Busca tabela principal de guias: '//*[@id="conteudo-submenu"]/table[2]'
  ↓ Se tabela vazia (≤1 linha) → retorna [] (paciente sem guias)

  FASE 6 — Ordenação da tabela por data (decrescente):
  ↓ Localiza cabeçalho 'SOLICITA' ou 'DATA' na tabela
  ↓ 1º clique no cabeçalho → ordena crescente (POSTBACK/reload parcial)
  ↓ Re-fetch dos elementos (anti-StaleElement)
  ↓ 2º clique no cabeçalho → ordena decrescente (mais recentes primeiro)

  FASE 7 — Loop de extração de guias (paginado):
  ↓ Para cada linha da tabela:
      → td[6] = status (AUTORIZADO / EM ESTUDO / NEGADO / CANCELADO / outros)
      → td[1] = data de solicitação
      → Se data < hoje - 180 dias → PARA (todas as guias mais antigas são irrelevantes)
      → Clica link em td[4] para acessar detalhes da guia
      → Verifica 'label_error_redeAtendPrestEspec' (acesso negado) → pula linha
      → Extrai: numero_guia, data_autorizacao, senha, validade_senha, codigo_terapia, qtde_solicitada, qtde_autorizada
      → Clica 'Button_Voltar' para voltar à lista
  ↓ Se link 'Próxima' presente → pagina e repete o loop
  ↓ Se não → fim da tabela

  FASE 8 — Limpeza e retorno:
  ↓ Fecha janela popup (close)
  ↓ switch_to.window(handles[0]) → volta à janela principal
  ↓ Retorna lista de dicts com todas as guias coletadas

[server.py / dispatcher]
  ↓ Recebe lista de guias
  ↓ Dispatcher processa e salva cada guia no banco (tabela base_guias)
  ↓ Job marcado como 'success'
```

### Tratamento de Erros e Retentativas
- **PermanentError** (ex: carteira inválida, sem credenciais): **sem retentativas** — job marcado como `error` imediatamente.
- **TimeoutException**: até 3 tentativas com re-login.
- **Exception geral**: até 3 tentativas com re-login e reinício do driver.
- **StaleElementException**: prevenido por re-fetch dos elementos após cada POSTBACK.

---

## 2. Backend (FastAPI + SQLAlchemy)

### 2.1 Estado Atual (Problemas)
- A lógica de `deps` (dependências) e a passagem explícita de `db` está acoplada a várias rotas onde poderia haver Middleware ou Unit of Work Pattern.
- Existem scripts de migração soltos (ex: `apply_migration_35.py`) jogados aleatoriamente, em vez de ficarem dentro do Alembic ou da pasta de `migrations/scripts`.
- A lógica de rate-limiting ou failover do Dispatcher conflitou em si mesma algumas vezes misturando "estado local" de variáveis não inicializadas (visto na rotina recente do `env_port_conv_map`).

### 2.2 Padrão Exigido
- **DRY em Consultas SQLAlchemy:** Repositórios genéricos isolados (`services/` ou `repositories/`) ao invés de codificar filtros brutos (`db.query(...).filter(...)`) dentro da camada visual do Endpoint (`routes/`). 
- **DB Migrations Clean:** Todos os `.sql` de manutenção local ou `apply_migration_XX.py` que já foram rodados devem ir para uma pasta "archive" ou `/migrations/past_fixes/`.
- **Triggers e Functions SQL:** Estão dispersos nos changelogs. Mapear e arquivar estáticos em `/docs/database_schema.md`.

---

## 3. Frontend (React + Vite + Next.js Patterns)

### 3.1 Padrão Exigido
- Componentização Estrita: Um componente JSX = Uma responsabilidade visual. Arquivos maiores que 200 linhas deverão ser quebrados em `hooks/` se possuírem lógicas complexas de data-fetching, e em `components/ui/` se possuírem HTML pesado.
- Redundância Visual: Reutilização compulsória de componentes de Tabela (`BaseTable`, `StatusBadge`).

---

## 4. Plano de Ação (Refactor Step-by-Step)

1. **Refactor Local_Worker Lixo**:
   - Mover os `.txt`, `.log`, e `.py` isolados da raiz do projeto para o diretório `/test_scripts/`.
2. **Refactor Unimed Goiânia (3)**:
   - Dividir `ImportBaseGuias.py` em `/config`, `/core/scraper.py`, `/op/op0_login.py` (autenticação crua), `/op/op1_consulta.py`.
3. **Mover Backend Migrations Soltos**:
   - Organizar a pasta raiz do backend isolando os `apply_migration.py` extintos.
4. **Criação do `/docs` Mestre**:
   - Materializar o schema consolidado dos workflows na raiz sob a nova documentação PO.
- Regra: responder no chat apenas em português - brasileiro