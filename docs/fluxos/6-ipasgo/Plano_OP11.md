# Plano de Implantação: OP11 - Importação de Guias via API (IPASGO)

## 1. Visão Geral
**Objetivo:** Substituir a extração de guias via Selenium (atualmente na `op3`) por uma abordagem via requisições HTTP (API/Requests) utilizando paginação. O novo fluxo será a `op11`, isolado e independente, sem alterar o funcionamento da `op3` existente.
**Estratégia:** Utilizar a sessão autenticada (cookies/headers) gerada pela `op0` (Login), acessando os novos endpoints levantados e validando os dados na mesma estrutura.

---

## 2. Especificações Técnicas (Baseadas no Prompt YAML)

### 2.1. Endpoints Mapeados
*   **Base URL:** `https://novowebplanipasgo.facilinformatica.com.br`
*   **Bootstrap (Inicialização de Contexto):** `GET /GuiasTISS/LocalizarProcedimentos`
*   **Consulta (Busca Paginada):** `POST /LocalizarProcedimentos/Localizar`

### 2.2. Regras de Payload
O envio JSON exigido pela API do Ipasgo possui tipagem rigorosa de campos vazios:
*   Campos ausentes não devem ser omitidos, mas sim enviados como strings vazias `""` ou a string literal `"null"`.
*   A ordenação padrão deve ser `DataLiberacao`.
*   As flags `DestacarOPME` e `PesquisarTotalItens` devem vir pré-configuradas de acordo com as regras de extração total.

### 2.3. Normalização de Dados (Data Transformation)
A API retorna um array chamado `Procedimentos`. A `op11` aplicará a normalização imediatamente para casar com a estrutura de banco de dados e padronização interna.
*   `CodigoBenficiario` -> `codigo_beneficiario`
*   `NomeBeneficiario` -> `nome_beneficiario`
*   `ChavesUtLib[0]` -> `numero_guia`
*   `Situacoes[0]` -> `situacao`
*   **Regra de Negócio (Senha):** A flag `necessita_senha` será gerada (`true`) estritamente se `SituacaoTiss` (ou situação correspondente) estiver entre `["Autorizado", "Liberado", "Parcialmente autorizada"]` **E** a guia não possuir senha (`HasSenha = false`). Caso contrário, será `false`.

### 2.4. Gestão de Sessão (Error Handling)
*   Se ocorrer `HTTP 401` ou `403` (Sessão Expirada), a rotina lançará erro e acionará um retry com chamamento compulsório da `OP0` para refazer o login.
*   Erros de timeout terão retry automático com *backoff*.

---

## 3. Padrões de Clean Code e Modularidade
- **Isolamento de Diretório:** O script `op11_import_guias_api.py` ficará no diretório `Local_worker/Worker/6-ipasgo/op/`.
- **Reaproveitamento de Componentes:** Expandir o `core/webplan_client.py` com o método de POST apontando para `/LocalizarProcedimentos/Localizar`.
- **Injeção de Dependências:** O parseamento ficará por responsabilidade do módulo `core/webplan_parser.py` (ou dentro da classe client de forma limpa).

---

## 4. Checklist de Implantação

### 🧑‍💼 Product Owner (PO)
- [ ] Validar a regra de negócio da flag `necessita_senha` baseada estritamente nas "Situações" retornadas.
- [ ] Aprovar se o escopo de variáveis contidas no array "Procedimentos" contempla todos os dados usados hoje na conciliação pela clínica.

### 💻 Desenvolvedor (Dev)
- [ ] **Expansão do Client HTTP (`webplan_client.py`):**
  - Adicionar novo método: `post_consultar_guias(self, page, parametros...)`.
  - Configurar injeção de JSON obrigatório no POST utilizando `requests.post(json=payload)`.
- [ ] **Construção do Script (`op11_import_guias_api.py`):**
  - Implementar requisição GET inicial (Bootstrap).
  - Implementar o laço `while has_next_page` ou `for` monitorando o array de resposta. A API para de listar quando envia um array vazio (`length == 0`).
  - Formatar os campos normalizados e fazer o *streaming/bulk upsert* banco.
- [ ] **Clean Code e Lixo:** 
  - Limpar arquivos soltos e utilizar unicamente `scraper.log()` mapeando os metadados estabelecidos no YAML.

### 🕵️ Quality Assurance (QA)
- [ ] **Teste de Paginação Stop-Condition:** Validar se o loop realmente para quando a API entrega array vazio (sem estourar *index exception*).
- [ ] **Teste de Payload Quebrado:** Testar a passagem do payload sem alguma chave para garantir que o Ipasgo rejeita, confirmando que nossa validação de "não omitir e mandar vazio/null" é a ideal.
- [ ] **Comparação de Massas:** Rodar `OP3` vs `OP11` e medir o tempo (espera-se ganho de > 90% em velocidade com a nova arquitetura HTTP).
