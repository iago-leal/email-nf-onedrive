# Requirements: MVP de arquivamento automático de NFs e boletos do e-mail no OneDrive

> Identificador: `001-mvp-email-nf-onedrive`
> Data: `2026-09-18`
> Pasta da extração reversa: `_reversa_sdd/` (modo greenfield: artefatos do ciclo `/reversa-new`)
> Confidência: 🟢 CONFIRMADO, 🟡 INFERIDO, 🔴 LACUNA / DÚVIDA
>
> Nota de confidência: todos os artefatos de origem levam o selo 🟡 PLANEJADO. Recebem 🟢 apenas os pontos que o usuário confirmou expressamente em 2026-09-18, conforme o registro em `_reversa_sdd/newproject-brief.md#Correções do usuário (2026-09-18)` e nos *decision logs* das specs.
>
> Anonimização: este documento é versionado e segue os marcadores dos artefatos públicos (`<empresa-1>`, `<dominio>`, `<tenant>`, `<conta-admin>`). Os valores reais ficam só em `_reversa_sdd/contexto-cliente.local.md` e no `.env`.

## 1. Resumo executivo

A feature entrega o produto mínimo descrito no PRD: uma ferramenta de linha de comando que, a cada 30 minutos, lê as caixas de e-mail financeiras configuradas, extrai os anexos PDF e XML e arquiva os reconhecidos como nota fiscal ou boleto, com nome padronizado, na pasta `<Empresa> Financeiro/CONTAS A PAGAR` do OneDrive for Business. Os beneficiários são a equipe financeira, que passa a encontrar os documentos já salvos, e o operador técnico, que é avisado quando algo falha. O problema resolvido é o esquecimento de contas: hoje quatro pessoas leem a mesma caixa e ninguém assume o arquivamento.

## 2. Contexto a partir do legado

Projeto greenfield: não há código legado. O contexto vem do PRD e das quatro specs SDD produzidas pelo `/reversa-new`, que esta feature implementa de uma só vez.

| Fonte | Trecho relevante | Confidência |
|-------|------------------|-------------|
| `_reversa_sdd/prd.md#1. Problema` | Responsabilidade difusa pelo arquivamento causa contas esquecidas e erros de lançamento. | 🟡 |
| `_reversa_sdd/prd.md#4. Escopo (in)` | Leitura de caixas Google Workspace, várias caixas por configuração, identificação e download de anexos sem duplicar, nomeação padronizada, envio ao OneDrive, execução agendada, log, aviso de falha e documentação. | 🟡 |
| `_reversa_sdd/prd.md#5. Não-objetivos (out)` | Fora do escopo: "Meu Dinheiro", banco, DDA, extração de valores, interface gráfica. | 🟡 |
| `_reversa_sdd/prd.md#6. Restrições` | Python, Rclone e VPS Linux sem interface; senha de app no Google Workspace; custo zero além da VPS; LGPD. | 🟡 |
| `_reversa_sdd/newproject-brief.md#Correções do usuário (2026-09-18)` | Destino é o OneDrive for Business, caixa é Google Workspace, aplicação deve aceitar várias caixas. | 🟢 |
| `_reversa_sdd/sdd/configuracao-caixas.md#6. Requisitos Funcionais` | Convenção `EMAIL<n>`/`SENHA_EMAIL<n>`, validação antes da rede, comando `verificar-config`. | 🟡 |
| `_reversa_sdd/sdd/coleta-email.md#6. Requisitos Funcionais` | Acesso somente leitura, janela de busca com sobreposição, extração PDF/XML, classificação, deduplicação. | 🟡 |
| `_reversa_sdd/sdd/coleta-email.md#15. Decisões Tomadas (Decision Log)` | Enviar todo PDF/XML; não alterar a caixa; deduplicar por caixa, identificador da mensagem e hash. | 🟢 |
| `_reversa_sdd/sdd/envio-onedrive.md#6. Requisitos Funcionais` | Nome padronizado, envio sem sobrescrita, sufixo em conflito, confirmação por tamanho, comando `testar-onedrive`. | 🟡 |
| `_reversa_sdd/sdd/execucao-monitoramento.md#6. Requisitos Funcionais` | Subcomandos, trava, códigos de saída, log com rotação, aviso por Telegram, guia de instalação e `.env.example`. | 🟡 |
| `_reversa_sdd/sdd/execucao-monitoramento.md#15. Decisões Tomadas (Decision Log)` | Execução a cada 30 min, aviso por Telegram, só falhas e recuperações notificadas, sem contêiner. | 🟢 |
| `_reversa_sdd/personas.md#Persona 2: operador-tecnico` | O operador quer entregar a ferramenta documentada para que a empresa cliente a opere. | 🟡 |

## 3. Personas e cenários de uso

| Persona | Objetivo | Cenário-chave |
|---------|----------|---------------|
| analista-financeira | Pagar todas as contas em dia, com o documento de cada uma arquivado. | Abre a pasta `CONTAS A PAGAR` antes da reunião semanal de pagamentos e encontra cada NF ou boleto recebido por e-mail já salvo e nomeado, sem ter baixado nenhum anexo. |
| operador-tecnico | Operar a automação sem supervisão e entregá-la à empresa cliente. | Recebe no Telegram o aviso de que a caixa 1 recusou o login, renova a senha de app seguindo o guia e recebe o aviso de recuperação na execução seguinte. |
| operador-tecnico | Acrescentar uma caixa nova sem programar. | Inclui `EMAIL2` e `SENHA_EMAIL2` no `.env`, confere com `verificar-config` e vê a caixa ser processada na execução seguinte. |

A analista acompanha o resultado diariamente, na rotina de lançamentos. O operador intervém apenas quando recebe um aviso de falha ou quando alguém acrescenta uma caixa.

## 4. Regras de negócio novas ou alteradas

Todas as regras são novas, pois não existe sistema anterior; o processo substituído é manual.

1. **RN-01, caixa intocada:** o sistema nunca move, apaga, marca como lida nem rotula mensagem alguma; a equipe continua vendo a caixa exatamente como hoje. 🟢
   - Origem: `_reversa_sdd/sdd/coleta-email.md#4. Non-Goals (Fora do Escopo)` (NG-01, "decisão do usuário, só ler")
   - Tipo: nova
2. **RN-02, pasta só recebe acréscimos:** nenhum arquivo existente na pasta de destino é sobrescrito, renomeado, movido ou apagado. A única exclusão permitida é a do arquivo de teste criado pelo próprio comando de teste, pelo caminho exato. 🟡
   - Origem: `_reversa_sdd/sdd/envio-onedrive.md#12. Segurança e Privacidade`
   - Tipo: nova
3. **RN-03, só documentos reconhecidos são arquivados:** seguem para o destino os anexos PDF e XML classificados como `nfe-xml` ou `palavra-chave`. Os anexos `sem-classificacao` não são enviados: ficam registrados no log e no registro de processados para revisão manual do operador. 🟢
   - Origem: `_reversa_sdd/sdd/coleta-email.md#15. Decisões Tomadas (Decision Log)` e `#14. Open Questions` (OQ-03), resolvida na sessão de esclarecimentos de 2026-09-18
   - Tipo: nova; **diverge da spec**, que previa enviar todo PDF e XML. A spec `coleta-email` (RF-07, decision log e métrica G-01) precisa ser alinhada pelo `/reversa-sync` ao fim da feature
4. **RN-04, arquivado significa confirmado:** um anexo só conta como arquivado depois que o destino confirma a presença do arquivo com o mesmo tamanho do original; até lá, ele permanece pendente e é retentado a cada execução. 🟡
   - Origem: `_reversa_sdd/sdd/envio-onedrive.md#3. Goals (Objetivos)` (G-03)
   - Tipo: nova
5. **RN-05, nenhum documento duas vezes:** um anexo, identificado pela caixa, pelo identificador da mensagem e pelo resumo criptográfico do conteúdo, é arquivado no máximo uma vez. 🟢
   - Origem: `_reversa_sdd/sdd/coleta-email.md#6. Requisitos Funcionais` (RF-08)
   - Tipo: nova
6. **RN-06, marco inicial obrigatório:** a primeira coleta de cada caixa considera só mensagens a partir de uma data inicial declarada na configuração, para não despejar anos de histórico na pasta de contas a pagar. 🟡
   - Origem: `_reversa_sdd/sdd/configuracao-caixas.md#15. Decisões Tomadas (Decision Log)`
   - Tipo: nova
7. **RN-07, minimização de dados pessoais:** documentos fiscais só permanecem no servidor de execução até a confirmação do envio; o registro persistente guarda apenas metadados, e nem log nem aviso contêm senha, token ou conteúdo de anexo. O log, que registra remetente e assunto, é retido por 30 dias; o registro de processados guarda seus metadados de forma permanente, pois é ele que garante a não duplicação. 🟢
   - Origem: `_reversa_sdd/sdd/coleta-email.md#12. Segurança e Privacidade`, `_reversa_sdd/prd.md#6. Restrições` (Compliance, LGPD)
   - Tipo: nova
8. **RN-08, aviso só quando importa:** o operador é avisado de falhas e de recuperações, nunca de execuções bem-sucedidas; uma falha de mesma causa é repetida no máximo a cada 6 horas. 🟢
   - Origem: `_reversa_sdd/sdd/execucao-monitoramento.md#15. Decisões Tomadas (Decision Log)`
   - Tipo: nova
9. **RN-09, falha isolada:** a falha de uma caixa ou de um envio não interrompe o processamento das demais caixas e anexos. 🟡
   - Origem: `_reversa_sdd/sdd/configuracao-caixas.md#15. Decisões Tomadas (Decision Log)`, `_reversa_sdd/sdd/coleta-email.md#6. Requisitos Funcionais` (RF-10)
   - Tipo: nova

## 5. Requisitos Funcionais

A coluna "Spec" aponta o requisito de origem, que detalha limites e mensagens. Abreviações: CC = `configuracao-caixas`, CE = `coleta-email`, EO = `envio-onedrive`, EM = `execucao-monitoramento`.

| ID | Requisito | Prioridade | Critério de aceite | Confidência | Spec |
|----|-----------|------------|--------------------|-------------|------|
| RF-01 | O sistema descobre as caixas pelas variáveis numeradas `EMAIL<n>` do `.env`, aceita lacunas na numeração e aplica os valores padrão de pasta (`INBOX`) e servidor (`imap.gmail.com:993`). | Must | Com `EMAIL1` e `EMAIL3` definidos, a configuração contém as caixas 1 e 3; sem `PASTA_EMAIL1`, a caixa 1 usa `INBOX`. | 🟢 | CC RF-01, RF-03, RF-04 |
| RF-02 | O sistema lê o remote, o destino global (com sobreposição por caixa), a data inicial e o canal de aviso, e valida toda a configuração antes de acessar a rede: erro global aborta com código 2, erro de caixa invalida só aquela caixa. | Must | `RCLONE_REMOTE` ausente encerra com código 2; `EMAIL2` sem `SENHA_EMAIL2` invalida só a caixa 2, com a mensagem "caixa 2: SENHA_EMAIL2 ausente". | 🟡 | CC RF-02, RF-05 a RF-08, EC-01 a EC-08 |
| RF-03 | O sistema nunca exibe senhas nem o token do Telegram em log, aviso ou terminal, e oferece o comando `verificar-config`, que lista as caixas com a senha mascarada sem acessar a rede. | Must | A busca pelo valor de `SENHA_EMAIL1` nos logs de um ciclo completo retorna zero ocorrências; `verificar-config` mostra `****` no lugar da senha. | 🟡 | CC RF-09, RF-10, RF-11 |
| RF-04 | O sistema acessa cada caixa válida por conexão cifrada e em modo somente leitura. | Must | Após uma execução, as mensagens não lidas continuam não lidas e nenhuma mudou de pasta ou de marcador. | 🟢 | CE RF-01, RF-02 |
| RF-05 | O sistema busca as mensagens a partir da data de corte: a data inicial para caixa sem histórico; para caixa com histórico, a menor entre a data da mensagem mais recente registrada menos 2 dias e a da mensagem mais antiga com anexo pendente. | Must | Com última mensagem registrada em 10/09 e nada pendente, a busca começa em 08/09; com anexo pendente de 01/09, começa em 01/09. | 🟡 | CE RF-03 |
| RF-06 | O sistema extrai os anexos PDF e XML, reconhecidos por extensão ou tipo de conteúdo, inclusive dentro de mensagens encaminhadas, e registra no log os anexos compactados, sem extraí-los. | Must | Um e-mail com `NF123.PDF` e `assinatura.png` gera um anexo extraído; um `.zip` gera a linha "anexo compactado ignorado". | 🟡 | CE RF-04, RF-11, EC-05, EC-06, EC-08 |
| RF-07 | O sistema classifica cada anexo como `nfe-xml`, `palavra-chave` ou `sem-classificacao`; entrega ao envio só os das duas primeiras classes e registra os `sem-classificacao` no log e no registro de processados como retidos para revisão manual, sem enviá-los e sem voltar a registrá-los nas execuções seguintes. | Must | Um XML de NF-e chamado `arquivo.xml` recebe `nfe-xml` e é enviado; um PDF `contrato.pdf` sem palavra-chave recebe `sem-classificacao`, aparece uma única vez no log como "retido para revisão" e não chega ao destino. | 🟢 | CE RF-05, RF-06, RF-07 (alterado), EC-07 |
| RF-08 | O sistema mantém um registro persistente dos anexos, com os estados `extraido`, `enviado` e `falha-envio`, e ignora os já enviados. | Must | Duas execuções seguidas sem e-mails novos entregam zero anexos na segunda. | 🟢 | CE RF-08, fluxos A e B; EO seção 9 |
| RF-09 | O sistema registra no log as mensagens com palavra-chave no assunto e sem anexo PDF ou XML, como "possível documento sem anexo". | Should | Um e-mail "Sua NFS-e está disponível" só com link aparece no log com remetente, assunto e data. | 🟡 | CE RF-09 |
| RF-10 | O sistema dá a cada arquivo o nome no padrão da pasta, `<EMPRESA> - <FORNECEDOR> [NF <n>] - <REF\|BOLETO>.<ext>`, sem caracteres inválidos no OneDrive e com no máximo 200 caracteres, preservada a extensão. | Must | `Boleto Set.pdf`, de `cobranca@fornecedor.com.br`, na caixa da empresa ACME, vira `ACME - FORNECEDOR - BOLETO.pdf`; o XML de NF-e vira `ACME - <emitente> NF <n> - REF.xml`. | 🟢 | EO RF-01, RF-02; L-03 |
| RF-11 | O sistema envia cada arquivo ao destino da caixa sem sobrescrever: diante de arquivo de mesmo nome e conteúdo diferente, acrescenta sufixo numérico; diante de arquivo idêntico, dá o anexo por enviado sem novo upload. | Must | Um segundo `boleto.pdf` distinto, do mesmo remetente e dia, vira `..._boleto_2.pdf`, e o primeiro permanece intacto. | 🟡 | EO RF-03, RF-04, RF-05 |
| RF-12 | O sistema confirma cada envio comparando o tamanho remoto com o local antes de marcar `enviado`; em erro ou divergência, marca `falha-envio` e retenta na execução seguinte. | Must | Com o OneDrive indisponível, o anexo fica `falha-envio` e chega ao destino na execução seguinte, sem intervenção. | 🟡 | EO RF-06, RF-07, EC-01 a EC-08 |
| RF-13 | O sistema apaga a cópia local de cada anexo assim que o envio é confirmado. | Must | Após uma execução sem falhas, a pasta de trabalho está vazia. | 🟡 | EO RF-08 |
| RF-14 | O sistema oferece o comando `testar-onedrive`, que grava, confirma e apaga um arquivo de teste de 1 KB no destino. | Should | Com o remote bem configurado, o comando imprime "OneDrive: escrita confirmada em <destino>". | 🟡 | EO RF-09 |
| RF-15 | O sistema oferece o ponto de entrada `email-nf-onedrive` com os subcomandos `executar`, `verificar-config` e `testar-onedrive`; `executar` roda configuração, coleta e envio, e aceita `--simular`, que coleta e classifica sem enviar, sem alterar o registro e sem avisar. | Must | `email-nf-onedrive --help` lista os três subcomandos; após `executar --simular`, registro e pasta do OneDrive estão inalterados. | 🟡 | EM RF-01, RF-02, RF-10; EO fluxo B |
| RF-16 | O sistema roda a cada 30 minutos sem sobreposição: uma nova execução com outra em andamento sai em menos de 1 s com código 0, e uma trava com mais de 25 min é considerada abandonada. | Must | Duas chamadas simultâneas resultam em um ciclo completo e uma saída imediata. | 🟢 | EM RF-03, RF-04 |
| RF-17 | O sistema sai com código 0 em sucesso, 1 em falha parcial e 2 em erro de configuração ou falha total. | Must | Com senha errada só na caixa 2, o código de saída é 1. | 🟡 | EM RF-05 |
| RF-18 | O sistema grava log em arquivo, uma linha por evento, com rotação diária e retenção de 30 dias, e termina cada execução com um resumo de duração e contagens. | Must | O log termina com `resumo: 1 caixa, 3 extraídos, 3 enviados, 0 falhas, 42 s`. | 🟡 | EM RF-06, RF-11 |
| RF-19 | O sistema avisa o operador pelo Telegram ao fim de toda execução com código 1 ou 2, com causa e ação sugerida, suprime repetições da mesma causa por 6 h e avisa a recuperação. | Must | Com a caixa 1 recusando o login por 3 h, chega um único aviso citando "caixa 1", "autenticação recusada" e "verifique a senha de app". | 🟢 | EM RF-07, RF-08, RF-09 |
| RF-20 | O repositório contém guia de instalação e operação e um `.env.example` com todas as variáveis, sem valores reais, e a linha de agendamento pronta. | Must | Uma pessoa alheia ao desenvolvimento instala a ferramenta numa VPS nova em menos de 60 min seguindo só o guia. | 🟡 | EM RF-12, RF-13 |

## 6. Requisitos Não Funcionais

| Tipo | Requisito | Evidência ou justificativa | Confidência |
|------|-----------|----------------------------|-------------|
| Desempenho | Ciclo típico em menos de 5 min; coleta em menos de 5 min por caixa com até 200 mensagens na janela; envio em menos de 10 s por arquivo de até 5 MB; validação da configuração em menos de 1 s. | `_reversa_sdd/sdd/execucao-monitoramento.md#7. Requisitos Não-Funcionais`, `_reversa_sdd/sdd/coleta-email.md#7. Requisitos Não-Funcionais`, `_reversa_sdd/sdd/envio-onedrive.md#7. Requisitos Não-Funcionais` | 🟡 |
| Resiliência | Tempo-limite de 60 s por operação no servidor de e-mail e de 120 s por envio; operação que estoura o limite vira falha retentável. | `_reversa_sdd/sdd/coleta-email.md#7. Requisitos Não-Funcionais` (RNF-04), `_reversa_sdd/sdd/envio-onedrive.md#7. Requisitos Não-Funcionais` (RNF-03) | 🟡 |
| Integridade | Zero mensagens alteradas na caixa e zero arquivos sobrescritos ou apagados no destino. | RN-01, RN-02 | 🟢 |
| Segurança | Conexões cifradas; execução por usuário de serviço sem privilégio de administrador; `.env`, configuração do Rclone e registro com permissão 600; alerta quando o `.env` estiver mais aberto. | `_reversa_sdd/sdd/execucao-monitoramento.md#12. Segurança e Privacidade`, `_reversa_sdd/sdd/configuracao-caixas.md#12. Segurança e Privacidade` | 🟡 |
| Privacidade | Minimização conforme a LGPD (Lei nº 13.709/2018): cópias locais apagadas após confirmação; registro só com metadados e retido permanentemente; log retido por 30 dias (RN-07). | `_reversa_sdd/prd.md#6. Restrições` (Compliance); Esclarecimentos, sessão 2026-09-18 | 🟢 |
| Observabilidade | Log por evento com data e hora ISO 8601, nível, caixa e mensagem; resumo por execução; aviso de falha em até 5 min após o fim da execução com falha; zero falhas sem aviso. | `_reversa_sdd/sdd/execucao-monitoramento.md#3. Goals (Objetivos)` | 🟡 |
| Plataforma | Linux (Ubuntu 22.04 ou superior), Python 3.11 ou superior, menos de 256 MB de RAM por execução. | `_reversa_sdd/sdd/execucao-monitoramento.md#7. Requisitos Não-Funcionais` | 🟢 |
| Custo | Nenhum custo recorrente além da VPS. | `_reversa_sdd/prd.md#6. Restrições` (Orçamento) | 🟢 |
| Operabilidade | Acrescentar uma caixa exige zero linhas de código; instalação numa VPS nova em menos de 60 min pelo guia. | `_reversa_sdd/sdd/configuracao-caixas.md#3. Goals (Objetivos)`, `_reversa_sdd/sdd/execucao-monitoramento.md#3. Goals (Objetivos)` | 🟢 |

## 7. Critérios de Aceitação

```gherkin
# Cobre RF-04, RF-06, RF-07, RF-10, RF-11, RF-12, RF-13, RF-15, RF-17, RF-18
Cenário: Boleto recebido é arquivado sem ação manual
  Dado que um fornecedor enviou à caixa 1 um e-mail com "Boleto Set.pdf" e "assinatura.png"
  E que a mensagem ainda não foi lida por ninguém
  Quando a execução agendada roda
  Então "2026-09-18_cobranca_Boleto Set.pdf" aparece na pasta de destino
  E a mensagem continua não lida e na mesma pasta da caixa
  E a pasta de trabalho local está vazia
  E o log termina com o resumo da execução
  E o código de saída é 0

# Cobre RF-08
Cenário: Reexecução não duplica documentos
  Dado que todos os anexos da janela de busca já constam como enviados
  Quando a execução roda de novo
  Então nenhum arquivo novo aparece na pasta de destino
  E o log registra "caixa 1: nenhum anexo novo"

# Cobre RF-11
Cenário: Nome repetido com conteúdo diferente
  Dado que a pasta de destino já contém "2026-09-18_cobranca_boleto.pdf"
  Quando chega do mesmo remetente, no mesmo dia, outro "boleto.pdf" de conteúdo distinto
  Então o novo arquivo é gravado como "2026-09-18_cobranca_boleto_2.pdf"
  E o arquivo original permanece com o conteúdo intacto

# Cobre RF-05, RF-12
Cenário: OneDrive indisponível e retomada automática
  Dado que o OneDrive recusou o envio de um anexo na execução anterior
  E que o anexo ficou registrado como "falha-envio"
  Quando a execução seguinte roda com o OneDrive disponível
  Então o anexo é reenviado e confirmado no destino
  E o registro passa a "enviado"

# Cobre RF-01, RF-02, RF-17, RF-19
Cenário: Caixa nova incompleta não derruba as demais
  Dado que o operador acrescentou "EMAIL2" ao .env sem "SENHA_EMAIL2"
  Quando a execução roda
  Então a caixa 1 é processada normalmente
  E a caixa 2 é invalidada com a mensagem "caixa 2: SENHA_EMAIL2 ausente"
  E o código de saída é 1
  E o operador recebe aviso no Telegram citando a caixa 2

# Cobre RF-02, RF-17
Cenário: Erro global de configuração aborta antes da rede
  Dado que "DATA_INICIAL" vale "18/09/2026"
  Quando a execução roda
  Então nenhuma conexão de rede é aberta
  E o log registra "DATA_INICIAL fora do formato AAAA-MM-DD"
  E o código de saída é 2

# Cobre RF-19
Cenário: Falha persistente não inunda o operador
  Dado que a caixa 1 recusa o login por 3 horas seguidas
  Quando seis execuções falham pela mesma causa
  Então o operador recebe um único aviso
  E, após a correção da senha, recebe "recuperado: caixa 1 voltou a funcionar"

# Cobre RF-03
Cenário: Credenciais nunca vazam
  Dado um ciclo completo com uma falha de autenticação
  Quando o operador procura o valor de "SENHA_EMAIL1" no log, no aviso e na saída de "verificar-config"
  Então não encontra nenhuma ocorrência
  E "verificar-config" exibe "****" no lugar da senha

# Cobre RF-16
Cenário: Execuções sobrepostas
  Dado que uma execução está em andamento há 10 minutos
  Quando o agendador dispara outra
  Então a nova sai em menos de 1 segundo com código 0
  E o log registra "execução anterior em andamento"

# Cobre RF-15
Cenário: Simulação não produz efeitos
  Dado uma caixa com dois anexos novos
  Quando o operador roda "executar --simular"
  Então o log lista os dois nomes que seriam enviados
  E a pasta de destino, o registro e o chat do Telegram ficam inalterados

# Cobre RF-07
Cenário: Anexo não reconhecido fica retido para revisão
  Dado um e-mail com assunto "Proposta comercial" e o anexo "contrato.pdf"
  Quando a execução roda duas vezes seguidas
  Então "contrato.pdf" não aparece na pasta de destino
  E o log registra uma única vez "retido para revisão", com remetente, assunto e nome do arquivo

# Cobre RF-09, RF-06
Cenário: Documento sem anexo e anexo compactado
  Dado um e-mail "Sua NFS-e está disponível" apenas com link
  E outro e-mail com "notas.zip" anexado
  Quando a execução roda
  Então o log registra o primeiro como "possível documento sem anexo"
  E o segundo como "anexo compactado ignorado"
  E nenhum dos dois gera arquivo no destino

# Cobre RF-14
Cenário: Teste de escrita no OneDrive
  Dado um remote configurado com permissão de edição no destino
  Quando o operador roda "testar-onedrive"
  Então o comando imprime "OneDrive: escrita confirmada em <destino>"
  E o arquivo de teste não permanece na pasta

# Cobre RF-20
Cenário: Instalação por terceiro
  Dado uma VPS Linux nova e uma pessoa que não participou do desenvolvimento
  Quando ela segue apenas o guia de instalação e o ".env.example"
  Então conclui a instalação, os testes e o agendamento em menos de 60 minutos
```

## 8. Prioridade MoSCoW

| Item | MoSCoW | Justificativa |
|------|--------|---------------|
| RF-01, RF-02, RF-03 | Must | Sem configuração validada e segura, nada roda; o requisito de várias caixas foi confirmado pelo usuário. |
| RF-04 a RF-08 | Must | Formam a coleta; RF-04 materializa a decisão de só ler, e RF-08 impede duplicação. |
| RF-10 a RF-13 | Must | Entregam o valor à analista e garantem a integridade da pasta. |
| RF-15 a RF-19 | Must | Sem execução agendada e aviso de falha, a automação falha em silêncio e recria o esquecimento. |
| RF-20 | Must | Condição para a entrega à empresa cliente. |
| RF-09 | Should | Cobre o risco de documentos por link, mas o tratamento deles está fora do MVP. |
| RF-14 | Should | Encurta o diagnóstico do Rclone, sem ser indispensável ao ciclo. |
| RNF de desempenho | Should | Os limites têm folga larga em relação ao intervalo de 30 min. |
| RNF de privacidade | Must | Exigência legal (LGPD). |
| Descompactação de `.zip`, leitura de links, OCR | Won't (nesta feature) | Não-objetivos da spec `coleta-email`; reavaliar após a semana de simulação. |

## 9. Esclarecimentos

### Sessão 2026-09-18

- **Q:** Os anexos PDF ou XML que o sistema não reconhece como NF ou boleto (contratos, propostas, relatórios) devem ter qual destino?
  **R:** Não são enviados; ficam só registrados no log para revisão manual. Aplicado em RN-03, RF-07 e no cenário "Anexo não reconhecido fica retido para revisão". Diverge da spec `coleta-email`, que previa enviar todo PDF e XML.
- **Q:** Por quanto tempo o log deve guardar remetente e assunto dos e-mails processados?
  **R:** 30 dias, conforme a proposta da spec. Aplicado em RN-07 e no RNF de privacidade.
- **Q:** Por quanto tempo o registro de processados deve guardar os metadados de cada anexo?
  **R:** Permanentemente, pois é o que garante a não duplicação. Aplicado em RN-07 e no RNF de privacidade.
- **Q:** Como os arquivos devem ser nomeados e organizados em `CONTAS A PAGAR`?
  **R:** Levantar o padrão atual com `rclone lsf` antes de decidir; a questão permanece aberta até lá (L-03).

## 10. Lacunas

Ponto que altera o comportamento especificado e depende de decisão do usuário:

- 🟢 **L-03** (resolvida em 2026-09-21) Convenção de nomes e de subpastas de `CONTAS A PAGAR`, levantada com `rclone lsf -R` sobre 2.304 arquivos e 738 pastas (`docs/onedrive/estrutura-contas-a-pagar.md`). **Nomes:** `<EMPRESA> - <FORNECEDOR> [NF <n>] - <REF|BOLETO>.<ext>`; adotado no RF-10 e implementado em `envio/nomeacao.py` (T042), com a EMPRESA em `EMPRESA_EMAIL<n>` no `.env`. **Subpastas:** a equipe usa a grade `NOTAS E BOLETOS POR VENCIMENTO/DIA <1..31>/202X-<01..12>/`, por dia e mês de **vencimento**; essa parte fica fora desta feature e vira exigência nova (cartão 2 do kanban), pois exige ler o vencimento do documento. Até lá a ferramenta grava na raiz do destino.

Premissas operacionais, que não mudam o requisito e são validadas na instalação e na semana de simulação:

- 🟡 **P-01** Pasta ou marcador monitorado da caixa 1; padrão `INBOX` (`_reversa_sdd/sdd/configuracao-caixas.md#14. Open Questions`, OQ-01).
- 🟡 **P-02** `SENHA_EMAIL1` precisa ser senha de app do Google; se for a senha comum, o login é recusado (idem, OQ-02).
- 🟡 **P-03** Valor de `DATA_INICIAL` na primeira execução (idem, OQ-03).
- 🟡 **P-04** Conta que autoriza o Rclone e eventual consentimento de administrador no tenant `<tenant>` (`_reversa_sdd/sdd/envio-onedrive.md#14. Open Questions`, OQ-02 e OQ-03).
- 🟡 **P-05** Ocorrência de NFs em `.zip`, a observar na semana de simulação (`_reversa_sdd/sdd/coleta-email.md#14. Open Questions`, OQ-02). A mesma semana serve para conferir se a lista de palavras-chave deixa NFs ou boletos legítimos na classe `sem-classificacao`, que agora não é enviada (RN-03).
- 🟡 **P-06** Destinatário dos avisos após a entrega, execução 24 h ou só em horário comercial, e prazo do MVP (`_reversa_sdd/sdd/execucao-monitoramento.md#14. Open Questions`, OQ-01 a OQ-03). Até decisão contrária, avisos só ao operador e execução 24 h.

## 11. Histórico de alterações

| Data | Alteração | Autor |
|------|-----------|-------|
| 2026-09-18 | Versão inicial gerada por `/reversa-requirements`, consolidando PRD e as quatro specs do ciclo `/reversa-new` | reversa |
| 2026-09-18 | Sessão de esclarecimentos: anexos `sem-classificacao` retidos (RN-03, RF-07), retenção de log e registro definida (RN-07); L-01 e L-02 resolvidas, L-03 mantida | reversa-clarify |
| 2026-09-21 | L-03 resolvida pelo levantamento da pasta real (T042): RF-10 passa à convenção `EMPRESA - FORNECEDOR - TIPO`; a organização por vencimento vira exigência nova | reversa-coding |

## Pendências de Qualidade

Resultado da auto-validação pela checklist de `.reversa/templates/quality-template.md`, após duas iterações:

- **Q-018 (nomes de produto):** o documento cita Rclone, OneDrive, Telegram, Google Workspace e Python. A menção é deliberada, pois são restrições fixadas pelo usuário no PRD (`_reversa_sdd/prd.md#6. Restrições`), e não escolhas de solução deste documento.
- **Q-017 (o quê, não o como):** alguns critérios de aceite herdam das specs detalhes de mecanismo (sufixo `_2`, trava de 25 min, formato do resumo). Foram mantidos por serem comportamento observável pelo usuário, e não decisão interna de implementação.
- **Q-019 e Q-020 (princípios):** não há `.reversa/principles.md` neste projeto; a verificação de princípios ficou sem objeto.
