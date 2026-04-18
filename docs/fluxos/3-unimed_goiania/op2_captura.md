# Fluxo Passo a Passo: Rotina 2 (Captura) - Unimed Goiânia

**Objetivo:** Mesma finalização prévia que Anápolis para apontamento de Execução de Guias. Destaca-se nesta rotina exclusivas validações lógicas e travas na checagem de Expiradas.

## 1. Navegação de Base
- Identifica Janelas Flutuantes presas e derruba, focando na principal `0`. 
- Repete o percurso Anapolis usando Seletores e cliques para acessar sub-menu da Listagem List: `"#centro_3"`.

## 2. Fase de Pré-Filtro (Timeouts Rígidos)
1. Busca-se unicamente pelo campo textual `#s_nr_guia`. O Bot cola a Guia enviada do Servidor ali e avança para Filtra.
2. Identificando a presença dela listada em Aberto (pela tag âncora `"/td[3]/a"` no HTML): 
3. **Gestão do Tempo de Fuga (Mecanismo "Goiano"):** 
   - Raspa na própria tabela a Concatenação da String Data mais a String Horário para estipular a emissão oficial na Unimed (`/td[1]` + `/td[2]`).
   - Avalia a regra vitalícia limitante de **59 minutos**. Se a vida contábil online transcorrida deste horário extraído for maior ou igual ao Limite e somada uma folga paralela (2 minutos de segurança para travas de comunicação Web HTTP).
   - O Sistema determina a Guia como `"Expirada localmente!"`. 
   - Clica sobre imagem Vector do "Excluir" (lixeira vermelha) disposta ao final daquela linha HTML e destrói o registro da tabela SGUCard na nuvem.
   - Força falha parcial do retorno da Função (sinalizando para recapturar/regravar na fase seguinte).

## 3. Fase de Re-Captura Biométrica (Recomeço / Start Up)
Caso o Pré-Filtro tenha resultado estéril ou tenha sido abortado pelo Expirador Temporal acima citado:
1. O Robô invoca a Tela do `New_Exame` (Popup com Botões Formato Cartão Físico).
2. O envio da carteirinha usa a mesma base da Rotina 1 (Consulta) de Goiânia: sub-divide a string inteligente via RegEx, injeta Javascript convertendo `nr_via`, `DS_CARTAO` e `CD_DEPENDENCIA` para literais textuais, e preenche a guia. Caso prefixo fora do padrão clica `Button_Consulta`.
3. Espera o "Reload" da tabela listada da Sub-View para os resultados de GUIAS do paciente em questão.
4. **Extração do Vínculo**: 
   - Efetua dupla formatação Clicável Sort por Coluna `'SOLICITA / DATA'`.
   - Procura linha a linha o número da respectiva guia cruzando contra status "AUTORIZADO / LIBERADO".
   - Acerta o Mouse virtual no painel interno. Clica formalmente no botão `button_confirmar_voltar` ou `button_confirmar`.
5. **Espera da Biometria Facial**: 
   - Imediatamente após confirmação, varre a tela pelo elemento de Verificação Biométrica (XPath: `//*[@id="root"]/section/div/div/div/div[2]/div/div[3]/button[1]/span[1]`).
   - Se apareceu o QR/Scan, o robô entra num estado de Timeout Limite de até **3 minutos** aguardando a realização do reconhecimento fácil. A tela desaparecerá sozinha do SGUCard.
   - Se estourar 3 minutos com a tela de biometria engasgada na frente, ele encerra a popup e segue pra checar falha.

## 4. Fase de Pós-Filtro de Reingresso
1. Com a popup fechada, o Scraper foca na listagem Global de Aberto original e submete a guia isoladamente no Input Search.
2. **Verdade de Captura Final:**
   - Se o portal retornar a aba de registro: Capta o Timestamp Server-Side de posse da guida. Transmite sucesso pro DB Hub. Encerrando rotina.
   - **Caso Inválido:** Se a listagem retornar vazia (o pós-filtro não achar), atesta-se matematicamente falha na fase 3: Seja via recusa de Biometria vencida nos 3 Minutos, ou problemas no próprio `Confirmar`. O Workflow registra via log restrito `"guia não capturada ou biometria não realizada"` e lança exception de barramento para parar fila.
