# OP1 - Consulta Guias no portal Faturamento (Faturi / Orizon)

## Objetivo
Verificar o status de uma guia de faturamento específica no portal da Orizon, identificando se ela está pendente ou faturada/em lote.

## Portal
- **URL de Trabalho:** `https://portal.orizon.com.br/fature/prestador.html#/guias`

## Parâmetros (via `params` do Job)
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `guia` | str | Sim | Número da guia a ser consultada |
| `dataInicio` | str | Sim | Data inicial do período de emissão (formato `DD/MM/YYYY` ou `YYYY-MM-DD`) |
| `dataFim` | str | Sim | Data final do período de emissão (formato `DD/MM/YYYY` ou `YYYY-MM-DD`) |
| `prestador_id` | str | Não* | ID do prestador executante (Fallback: `cod_prestador` do scraper) |
| `reg_ans` | str | Não | Registro ANS da operadora (limpa zeros à esquerda, ex: `5711`) |

## Fluxo Detalhado
1. **Navegação Inicial:** Acessar a URL base de guias de faturamento.
2. **Aguardar Componentes:** Aguarda o carregamento do botão de busca (`id="buscarGuias"`), timeout de 20s.
3. **Limpeza de Tela:** Executa rotina para fechar quaisquer modais ou popovers intrusivos:
   * Popovers com classe `btn btn-sm btn-default`.
   * Modal de envio de imagens (`id="modal_enviar_imagens"`).
4. **Fase 1 - Consulta de Pendentes (Status 199):**
   * Dispara uma chamada assíncrona (`fetch`) via injeção de JavaScript contra o endpoint REST do Fature:
     `https://rest-guia-fature-apicast-production.api.ocppr.orizon.com.br/api/Status_Guia/Get` filtrando por `StatusGuia=199` e `carteirinhaOuGuiaPrestador={guia}`.
   * Se a guia for localizada, retorna imediatamente seu status.
5. **Fase 2 - Consulta de Faturadas em Lote (Status 5):**
   * Se a fase 1 não retornar registros, dispara uma chamada JavaScript adicional buscando guias já associadas a lotes:
     `https://rest-guia-fature-apicast-production.api.ocppr.orizon.com.br/api/Status_Guia/GetGuiasLote` com `Status_Guia_Id=5` e `numeroGuiaPrestador={guia}`.
   * Se localizada, retorna as informações do lote/guia.
6. **Fase 3 - Guia Não Localizada:**
   * Retorna um status indicando que o documento não foi encontrado nas buscas do período informado.

> **Nota de Implementação (Fetch via JS):** O bot não faz scrap visual da tabela do portal. Ele executa uma chamada `fetch` assíncrona injetada pelo driver do Selenium. Isso permite que a requisição herde automaticamente os cookies de sessão ativos e o cabeçalho `Authorization: Bearer <token>` extraído do `localStorage`/`sessionStorage` do navegador.

## Retorno
Formato de sucesso ou não localização:
```json
[{
    "guia": "987654321",
    "status_guia": "5",
    "descricao": "Faturada"
}]
```

## Erros Tratados
| Cenário | Comportamento |
|---------|---------------|
| Parâmetros nulos | `ValueError` indicando campos ausentes. |
| Erro de parse no JSON retornado | O scraper loga o erro de comunicação com a API REST, mas tenta a próxima chamada (ou falha com retry). |
| Cookies inválidos | A chamada fetch retorna erro HTTP 401/403, disparando o retry automático com login prévio. |

## Nota sobre Persistência no Banco
Diferente das rotinas de autorização, as consultas de guias do Bradesco OP1 Fature **não** são gravadas na tabela `base_guias`. Os resultados obtidos são devolvidos diretamente no payload de resposta do job e registrados em formato JSON na tabela de `logs` do banco de dados, servindo exclusivamente como verificação em tempo real.
