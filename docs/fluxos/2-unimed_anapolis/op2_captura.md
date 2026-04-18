# Fluxo Passo a Passo: Rotina 2 (Captura) - Unimed Anápolis

**Objetivo:** Consolidar a visualização da central em cima de uma específica guia de autorização de um paciente, marcando o compromisso prévio ou forçando essa captura caso a clínica ainda não esteja apontada em sua tela.

## 1. Navegação de Base
- Fecha janelas aleatórias secundárias que por ventura restarem do loop (como relatórios pendurados em outra OP).
- Confirma e checa a tela de Menu do SGUCard e mergulha em "Autorizador » SADTs em Aberto (#centro_3)".

## 2. Fase de Pré-Filtro (Guia Já Localizada)
1. Antes de se aventurar na extensa tela de preenchimento de Paciente a Captura busca encurtar a ação via caixa de pesquisa global na rota dos SADTs pelo parâmetro `s_nr_guia`.
2. Emite o token da Guia exata que deseja acessar no `<input>` e aciona Buscar.
3. Se o Elemento da tabela aparecer e contiver os links normatizados:
   - A guia já tinha pertencimento natural na tela (já fora preenchida no passado mas não gravada).
   - Capta o horário impresso na Tabela através de Parsing e formata pra Data Python (`timestamp_captura`).
   - Salva esse registro de captura no banco de Dados para pular etapas e retorna como `"Capturado"` junto a tag interna `pre_filter: True`. O job finaliza com Sucesso de antemão.

## 3. Fase de Re-Captura e Inserção Biometrica - "new_exame"
Caso a fase 2 não encontre a guia solta na listagem inicial, inicia o fluxo detalhista.

1. Identifica o botão `'//*[@id="cadastro_biometria"]/div/div[2]/span'` (`New_Exame`) e simula click.
2. Troca-se o Driver local para a PopUp do Formulário que foi carregado no Background.
3. Repete o detalhamento de inserção da rotina de Consulta:
   - Adiciona Prefixo do Cartão, Beneficiário Integral, "Verificar" etc.
   - Monitora janelas modais avisando de "Senha Inválida" ou "Cartão Falsificado". (Com Abort Crítico com PermanentError).
4. O scraper espera de 10 a 20s em Loop pelo reload da tabela interna na nova PopUp, reclassifica as colunas em Data "Decrescente" via multi-clicking na header igual à OP1.
5. Percorre linha a linha visualmente e lê cada guia no código HTML, se batem com o número alvo. Caso sim:
   - Clica sobre ela, entra na tela da Guia autorizada e dá submit nos links de finalização/vínculo que aparecerem, com prioridade para ID `button_confirmar_voltar` ou pelo menos `button_confirmar`. Ambos amarram de verdade essa guia no WebPortal para a instituição logada.
   - Fecha tudo.

## 4. Fase de Pós-Filtro
1. Na janela Principal nativa remanescente (SADTs Abertas). O script varre *DE NOVO* o campo de input de Filtro global digitando o número da referida Guia que se acabara de capturar, garantindo que o Web Portal SGUCard validou as informações inseridas na Biometria. 
2. Retira o exato e acurado Horário emitido visualmente pelo site (`timestamp_captura`) que simbolizará o marco final que a guia ficou atestada online para a operadora.
3. Retorna sucesso e marca status do agendamento para captura finalizada e pre-filtro como `False`.
