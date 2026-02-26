# GUIA DE MODULARIDADE E PADRÕES DE CÓDIGO - AGENDA HUB

Este documento estabelece as diretrizes para garantir que o projeto seja modular, escalável e utilize as melhores práticas de desenvolvimento.

## 1. Modularidade por Convênio

Cada convênio deve ser isolado em sua própria estrutura dentro da pasta `Worker/convenios/`.

- **Isolamento**: XPaths, URLs e lógicas específicas de cada site devem estar em arquivos de configuração locais ao módulo do convênio.
- **Interfaces**: Todos os módulos de convênio devem implementar uma interface base (ex: `BaseScraper`) para que o `Dispatcher` possa chamá-los de forma agnóstica.

## 2. Clean Code & DRY (Don't Repeat Yourself)

- **Extração de Utilitários**: Funções comuns como formatação de data, limpeza de strings e espera de elementos Selenium devem estar em `core/utils/`.
- **Nomes Significativos**: Variáveis e funções devem ter nomes que descrevam sua intenção em português ou inglês (manter consistência).
- **Funções Pequenas**: Cada função deve fazer apenas uma coisa.

## 3. Reuso de Instâncias (Selenium)

- O `SeleniumManager` é o único responsável por criar e destruir instâncias.
- Workers devem solicitar uma instância ao pool e devolvê-la após o uso (ou mantê-la se o próximo Job for compatível).
- Sempre limpar cookies e sessões ao trocar de convênio na mesma instância.

## 4. Segurança

- **Credenciais**: NUNCA utilize credenciais em código ou arquivos `.env` locais. Todas as senhas devem ser buscadas no banco de dados de forma criptografada.
- **Logs**: Certifique-se de que nenhum log registre senhas ou dados sensíveis dos pacientes.

## 5. Orquestração (Dispatcher)

- O Dispatcher não executa o scraping. Ele apenas decide **quem** (servidor), **o que** (job) e **quando** executar.
- A decisão é baseada exclusivamente na tabela de prioridades e status da fila.
