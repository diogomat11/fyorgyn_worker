# Checklist de Testes QA - Agenda Hub MultiConv

Este documento serve como um guia para o QA tester validar as rotinas de cada convênio no sistema. Após realizar os testes, favor registrar os resultados e falhas encontradas.

## 📋 Instruções de Teste
1. Inicie o sistema e certifique-se de que os workers estão rodando.
2. Crie ou identifique Jobs para as rotinas específicas no painel administrativo.
3. Monitore os logs e a execução do navegador (se visível).
4. Marque os itens abaixo conforme a validação.

---

## 🏛️ 6 - IPASGO

### Op0 - Login
- [v] O scrapper acessa o portal Facplan.
- [v] O login é realizado com sucesso redirecionando para a home.

### Op1 - Autorizar Facplan
- [ ] O fluxo de solicitação de autorização é concluído sem erros de elemento.

### Op3 - Import Guias
- [ ] O sistema localiza as guias no portal.
- [ ] A importação dos dados para o banco de dados ocorre corretamente.

### Op4 - Confirma Guia (Execução)
- [ ] Clicou no link `#linkfacplan` com sucesso.
- [ ] A nova aba "Bem-vindo ao WebPlan" carregou corretamente.
- [ ] Navegou para a URL de Localizar Procedimentos.
- [ ] Realizou a limpeza de carteira residual (botão 'remove').
- [ ] Injetou o número da guia e limpou os filtros de data (`data-bind`).
- [ ] Clicou em Pesquisar e o Spinner desapareceu.
- [ ] O ícone de execução (grayscale check) foi localizado e é clicável.
- [ ] O modal de confirmação abriu e listou as sessões.
- [ ] Clicou em "Confirmar" na sessão, injetou a carteirinha e validou o popup "noty" de sucesso.
- [ ] O modal foi fechado corretamente após a execução.

### Op5 - Impress Guia
- [ ] Geração do PDF/Impressão da guia funciona para guias autorizadas.

### Op10 - Recurso Glosa
- [ ] Fluxo de recurso de glosa processado até o final.

---

## 🏥 2 - Unimed Anápolis

### Op0 - Login
- [ ] Acesso ao portal SGUCard realizado com sucesso.

### Op1 - Consulta
- [ ] Listagem de SADTs em aberto funciona.
- [ ] Filtro por número de guia localiza o registro.

### Op2 - Captura
- [ ] Extração detalhada dos dados da guia (procedimentos, datas, status).

### Op3 - Execução (Faturamento)
- [ ] Navegou até "SADTs em Aberto".
- [ ] Filtrou e abriu a guia correta via `trRow_2`.
- [ ] Selecionou Tipo "03 - Outras Terapias" e Regime "01 - Ambulatorial".
- [ ] Preencheu a data da série e clicou em "Gravar".
- [ ] Clicou no ícone de vínculo e em "Nova Participação".
- [ ] Lupa de prestador abriu nova janela, buscou pelo nome e selecionou o profissional.
- [ ] Cadastrou o vínculo com Grau "12 - Clínico" e Código de Faturamento correto.
- [ ] Navegou para "Dados da Guia SP/SADT".
- [ ] Clicou em "Finalizar Parcial" e **confirmou no botão `btn_confirmar`** (seja em nova aba ou modal).

---

## 🏥 3 - Unimed Goiânia

### Op0 - Login
- [ ] Acesso ao portal Unimed Goiânia (cookies validados).

### Op1 - Consulta
- [ ] Filtro por data (até 270 dias) funcionando.
- [ ] Identificação de guias pendentes.

### Op2 - Captura
- [ ] Abertura do popup de detalhes da guia.
- [ ] Extração de XML/Dados completa.

### Op3 - Execução
- [ ] Fluxo de finalização de guia no portal concluído.

---

## 💎 8 - SulAmérica
- [ ] **Rotinas Gerais**: (Aguardando implementação/detalhamento)

---

## 🟦 9 - Amil
- [ ] **Rotinas Gerais**: (Aguardando implementação/detalhamento)

---

## 📝 Resultado Geral e Falhas Encontradas
> [!NOTE]
> Utilize este espaço para descrever bugs, erros de timeout ou elementos não encontrados durante os testes.

| Convênio | Rotina | Status (OK/Falha) | Descrição do Problema |
| :--- | :--- | :--- | :--- |
| | | | |
| | | | |
| | | | |
