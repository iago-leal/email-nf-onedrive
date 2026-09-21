# Requirements: acesso às caixas do Gmail por OAuth 2.0, com projeto próprio no Google Cloud

> Identificador: `002-oauth-gmail-google-cloud`
> Data: `2026-09-21`
> Pasta da extração reversa: `_reversa_sdd/` (modo greenfield: artefatos do ciclo `/reversa-new`, lidos com o adendo vigente `addenda/001-mvp-email-nf-onedrive.md`)
> Confidência: 🟢 CONFIRMADO, 🟡 INFERIDO, 🔴 LACUNA / DÚVIDA
>
> Nota de confidência: os artefatos de origem levam o selo 🟡 PLANEJADO. Recebem 🟢 os pontos que o usuário confirmou na conversa de 2026-09-21 e os fatos apurados no teste de login do mesmo dia, registrado no cartão "Senhas de app do Google" do quadro do projeto. As afirmações sobre regras do Google (escopo, validade de autorização, tipos de público) vêm de conhecimento geral e levam 🟡 até serem conferidas na documentação oficial durante o `/reversa-plan`.
>
> Anonimização: este documento é versionado e segue os marcadores dos artefatos públicos (`<empresa-1>`, `<dominio-1>`). Os endereços reais ficam só em `_reversa_sdd/contexto-cliente.local.md` e no `.env`.

## 1. Resumo executivo

A feature permite que a ferramenta entre nas caixas do Gmail por OAuth 2.0 (protocolo de autorização delegada, em que o titular concede acesso sem entregar senha), usando um projeto próprio no Google Cloud, como alternativa à senha de app. Serve ao operador técnico, que hoje não consegue pôr o MVP em operação: as cinco caixas recusaram o login, porque as senhas recebidas são as comuns e a senha de app obrigaria cada titular a ativar a verificação em duas etapas. Entrega também o roteiro de criação do projeto no Google Cloud e o procedimento de autorização de cada caixa, de modo que nenhuma conta dos clientes precise mudar a forma de entrar.

## 2. Contexto a partir do legado

Projeto greenfield, com o MVP (feature 001) implementado e todas as 45 ações concluídas. A autenticação atual é endereço e senha, por caixa.

| Fonte | Trecho relevante | Confidência |
|-------|------------------|-------------|
| `_reversa_sdd/prd.md#6. Restrições` | O Google Workspace não aceita IMAP (protocolo de leitura de caixa de e-mail) com a senha comum: ou senha de app, com verificação em duas etapas, ou OAuth 2.0. A VPS não tem navegador, e a autorização OAuth do Rclone já é feita em outra máquina, com o token copiado depois. Sem custo recorrente além da VPS. | 🟡 |
| `_reversa_sdd/personas.md#Persona 2: operador-tecnico` | A dor principal do operador já previa "senha de app ou OAuth" para a caixa do Google Workspace. | 🟡 |
| `_reversa_sdd/sdd/configuracao-caixas.md#6. Requisitos Funcionais` | RF-02 exige `SENHA_EMAIL<n>` não vazia para toda caixa; RF-08 valida tudo antes da rede; RF-09 proíbe segredos em log; RF-10 define o `verificar-config`; RF-11 alerta sobre a permissão do `.env`. | 🟡 |
| `_reversa_sdd/sdd/configuracao-caixas.md#9. Modelo de Dados` | A entidade `Caixa` tem `senha` como único segredo de acesso. | 🟡 |
| `_reversa_sdd/sdd/configuracao-caixas.md#14. Open Questions` | OQ-02 perguntava se `SENHA_EMAIL1` era senha de app; o teste de 2026-09-21 respondeu que não. | 🟢 |
| `_reversa_sdd/sdd/coleta-email.md#6. Requisitos Funcionais` | RF-01 manda autenticar "com endereço e senha de app"; RF-02 fixa o acesso somente leitura; RF-10 impede que a falha de uma caixa interrompa as demais. | 🟡 |
| `_reversa_sdd/sdd/coleta-email.md#11. Edge Cases e Tratamento de Erros` | EC-01: login recusado pula a caixa, registra "autenticação recusada (verifique a senha de app)" e gera aviso de falha. | 🟡 |
| `_reversa_sdd/sdd/coleta-email.md#12. Segurança e Privacidade` | Autenticação por senha de app lida do `.env`, nunca registrada; autorização só de leitura. | 🟡 |
| `_reversa_sdd/sdd/execucao-monitoramento.md#6. Requisitos Funcionais` | Avisos de falha com supressão de 6 h por causa e aviso de recuperação; códigos de saída 0, 1 e 2. | 🟡 |
| `_reversa_sdd/addenda/001-mvp-email-nf-onedrive.md#Impacto por artefato da extração` | RF-01 a RF-11 da configuração e da coleta estão implementados em `configuracao/` e `coleta/`; a chave do registro usa o endereço da caixa, não o índice. | 🟢 |

Fatos de 2026-09-21 que motivam a feature: 🟢 as cinco caixas do `.env` devolveram `AUTHENTICATIONFAILED`; 🟢 quatro caixas são de três domínios do Google Workspace (`<dominio-1>`, `<dominio-2>`, `<dominio-3>`) e uma é conta pessoal `@gmail.com`; 🟢 o usuário decidiu criar o projeto no Google Cloud em vez de pedir a verificação em duas etapas aos titulares.

## 3. Personas e cenários de uso

| Persona | Objetivo | Cenário-chave |
|---------|----------|---------------|
| operador-tecnico | Pôr as cinco caixas em operação sem exigir mudança nas contas dos clientes. | Cria o projeto no Google Cloud uma vez, na própria conta pessoal, seguindo o guia; comunica cada titular; autoriza cada caixa pela linha de comando, no próprio computador, entrando na conta com a senha recebida e aceitando o pedido de acesso; leva as autorizações para a VPS e confere o acesso antes de agendar. |
| operador-tecnico | Ser avisado quando uma autorização deixar de valer. | Recebe o aviso no Telegram com a caixa e a causa, refaz a autorização só daquela caixa e vê o aviso de recuperação na execução seguinte. |
| titular da caixa (integrante da equipe financeira ou administrativa do cliente) | Saber que acesso foi concedido em seu nome, sem alterar a forma como entra na conta. | Recebe o comunicado do operador antes da autorização, não precisa executar nenhum passo e sabe onde revogar o acesso na própria conta. |
| analista-financeira | Continuar encontrando os documentos arquivados. | Nenhuma mudança percebida: a caixa segue intocada e os documentos aparecem na pasta de contas a pagar. |

## 4. Regras de negócio novas ou alteradas

1. **RN-01:** cada caixa tem exatamente um modo de autenticação, `senha` ou `oauth`. Caixa sem modo declarado usa `senha`, de forma que o `.env` atual continua válido sem edição. 🟢
   - Origem no legado: `_reversa_sdd/sdd/configuracao-caixas.md#6. Requisitos Funcionais` (RF-02) e `_reversa_sdd/sdd/coleta-email.md#6. Requisitos Funcionais` (RF-01)
   - Tipo: alterada
2. **RN-02:** a exigência de `SENHA_EMAIL<n>` não vazia passa a valer só para as caixas em modo `senha`. 🟢
   - Origem no legado: `_reversa_sdd/sdd/configuracao-caixas.md#6. Requisitos Funcionais` (RF-02)
   - Tipo: alterada
3. **RN-03:** o acesso à caixa continua somente leitura, qualquer que seja o modo. O escopo que o Google exige para IMAP com OAuth concede acesso total ao correio; a ferramenta não pode usar nada além da leitura já fixada, e o guia deve dizer isso ao titular com clareza. 🟡
   - Origem no legado: `_reversa_sdd/sdd/coleta-email.md#6. Requisitos Funcionais` (RF-02); regra W014 de `_reversa_forward/001-mvp-email-nf-onedrive/regression-watch.md`
   - Tipo: alterada (o contrato de leitura permanece; muda o alcance do que o titular concede)
4. **RN-04:** o segredo do cliente OAuth e as autorizações das caixas recebem o mesmo tratamento das senhas: nunca aparecem em log, aviso ou saída de terminal, ficam fora do versionamento e em arquivo com permissão restrita ao usuário de serviço. 🟢
   - Origem no legado: `_reversa_sdd/sdd/configuracao-caixas.md#6. Requisitos Funcionais` (RF-09, RF-11)
   - Tipo: alterada (amplia o conjunto de segredos)
5. **RN-05:** a autorização de uma caixa é ato único e durável. Configuração do projeto no Google Cloud que faça a autorização caducar em prazo fixo (caso do público externo em modo de teste, em que ela vale 7 dias) não é aceita para operação: o projeto usa público externo publicado (decisão da sessão de 2026-09-21). 🟡
   - Tipo: nova
6. **RN-06:** autorização recusada, revogada ou caducada é falha daquela caixa apenas: a caixa é pulada, as demais seguem, e o aviso de falha nomeia a caixa e manda refazer a autorização. 🟢
   - Origem no legado: `_reversa_sdd/sdd/coleta-email.md#6. Requisitos Funcionais` (RF-10) e `#11. Edge Cases e Tratamento de Erros` (EC-01)
   - Tipo: alterada
7. **RN-07:** a identidade da caixa não muda com o modo de autenticação. O registro de processados continua usando o endereço, e trocar `senha` por `oauth` não reenvia documento já arquivado. 🟢
   - Origem no legado: `_reversa_sdd/addenda/001-mvp-email-nf-onedrive.md#Impacto por artefato da extração` (chave do registro)
   - Tipo: nova
8. **RN-08:** a feature não pode criar custo recorrente: o projeto no Google Cloud é usado sem conta de faturamento. 🟡
   - Origem no legado: `_reversa_sdd/prd.md#6. Restrições` (orçamento)
   - Tipo: nova
9. **RN-09:** o consentimento de cada caixa é dado pelo operador, que entra na conta com a senha recebida do cliente. Por ser ato praticado em nome do titular dos dados, vale como exceção justificada pela indisponibilidade dos cinco titulares, e não como padrão: o titular é comunicado antes da autorização (RF-14), e o guia orienta a retirar `SENHA_EMAIL<n>` do `.env` depois que a caixa estiver autorizada, para que a senha de terceiro não permaneça guardada. 🟢
   - Tipo: nova

## 5. Requisitos Funcionais

| ID | Requisito | Prioridade | Critério de aceite | Confidência |
|----|-----------|------------|--------------------|-------------|
| RF-01 | O sistema deve ler o modo de autenticação de cada caixa em `AUTH_EMAIL<n>`, com os valores `senha` e `oauth`, sem diferenciar maiúsculas, usando `senha` quando a variável estiver ausente. | Must | Com `AUTH_EMAIL2=oauth` e nenhuma outra variável `AUTH_EMAIL<n>`, só a caixa 2 usa OAuth; `AUTH_EMAIL3=token` invalida a caixa 3 com o motivo "caixa 3: AUTH_EMAIL3 inválido (use senha ou oauth)". | 🟢 |
| RF-02 | O sistema deve dispensar `SENHA_EMAIL<n>` nas caixas em modo `oauth` e continuar exigindo-a nas caixas em modo `senha`. | Must | Caixa 2 em `oauth` sem `SENHA_EMAIL2` é válida; caixa 1 em `senha` sem `SENHA_EMAIL1` é inválida com a mensagem atual. | 🟢 |
| RF-03 | O sistema deve ler as credenciais do cliente OAuth das variáveis `OAUTH_CLIENT_ID` e `OAUTH_CLIENT_SECRET` do `.env`, exigidas só quando houver ao menos uma caixa em modo `oauth`. | Must | Com uma caixa em `oauth` e qualquer das duas variáveis ausente ou vazia, essa caixa é inválida com o motivo "credenciais do cliente OAuth ausentes", e as caixas em `senha` seguem; sem caixa em `oauth`, a ausência não gera erro nem alerta. | 🟢 |
| RF-04 | O sistema deve oferecer o comando `autorizar-caixa <n>`, que conduz a autorização da caixa `<n>` e grava o resultado em arquivo próprio daquela caixa, nomeado pelo endereço, no diretório indicado por `DIR_AUTORIZACOES` (padrão: `autorizacoes/`, ao lado do `.env`), com permissão 600, sem imprimir segredo. O consentimento acontece no navegador da mesma máquina que roda o comando (RN-09). | Must | Após a autorização, o arquivo `<endereço da caixa>` existe no diretório de autorizações com permissão 600; com `DIR_AUTORIZACOES` definido, é gravado nesse diretório; a saída informa "caixa 2: autorizada" e o endereço autorizado, e nenhum segredo aparece no terminal nem no log. | 🟡 |
| RF-05 | O comando `autorizar-caixa` deve funcionar numa máquina diferente da VPS, e o arquivo gerado deve poder ser copiado para a VPS sem edição. | Must | Autorização feita no computador do operador e copiada para a VPS permite à VPS entrar na caixa na execução seguinte. | 🟡 |
| RF-06 | O comando `autorizar-caixa` deve recusar a autorização quando a conta que consentiu for diferente do endereço configurado em `EMAIL<n>`. | Must | Ao consentir com a conta da caixa 3 durante `autorizar-caixa 2`, nada é gravado e a saída diz "conta autorizada difere de EMAIL2". | 🟡 |
| RF-07 | O sistema deve autenticar no servidor IMAP, nas caixas em modo `oauth`, com credencial de acesso temporária obtida a partir da autorização gravada, renovando-a sem intervenção humana a cada execução. | Must | Dois ciclos separados por mais de 1 h (validade usual da credencial temporária) entram na caixa sem nova autorização; o log registra "caixa 2: conectada (oauth)". | 🟡 |
| RF-08 | O sistema deve tratar autorização ausente, ilegível, revogada ou caducada como falha só daquela caixa, com causa de aviso própria, distinta da senha recusada. | Must | Com a autorização da caixa 2 revogada, a caixa 2 é pulada com o log "caixa 2: autorização OAuth recusada (rode autorizar-caixa 2)", a caixa 1 é processada, o código de saída é 1 e o aviso segue a supressão de 6 h. | 🟢 |
| RF-09 | O sistema deve tratar indisponibilidade do serviço de autorização do Google (sem resposta em 60 s ou erro de servidor) como falha transitória da caixa, sem descartar a autorização gravada. | Must | Com o serviço inacessível, a caixa é pulada, o arquivo de autorização permanece intacto e a execução seguinte entra normalmente. | 🟡 |
| RF-10 | O comando `verificar-config` deve mostrar, por caixa, o modo de autenticação e, nas caixas em `oauth`, se existe autorização gravada, sem acessar a rede e sem exibir segredo. | Should | A caixa 2 aparece como `2 · <endereço> · INBOX · <destino> · oauth (autorizada)`; sem o arquivo, `oauth (sem autorização)`. | 🟢 |
| RF-11 | O sistema deve oferecer o comando `testar-caixa [<n>]`, que entra em cada caixa (ou só na `<n>`), abre a pasta em modo somente leitura e sai, informando o resultado por caixa, com uma única tentativa por caixa. | Should | Com a caixa 1 autorizada e a caixa 2 sem autorização, a saída traz "caixa 1: acesso confirmado" e "caixa 2: falhou (sem autorização)", e o código de saída é 1. | 🟡 |
| RF-12 | O sistema deve alertar no log quando um arquivo de autorização tiver permissão de leitura para grupo ou outros usuários; as credenciais do cliente ficam no `.env`, já coberto pelo alerta vigente (RF-11 da configuração). | Should | Com `chmod 644` no arquivo de autorização da caixa 2, o log registra "permissão da autorização da caixa 2 mais aberta que 600". | 🟢 |
| RF-13 | O guia de instalação e operação deve ganhar o roteiro de criação do projeto no Google Cloud (projeto sem faturamento na conta pessoal do operador, tela de consentimento, público externo publicado, cliente OAuth), o procedimento de autorização de cada caixa pelo operador, com o aviso de aplicativo não verificado que a tela exibe, a retirada de `SENHA_EMAIL<n>` após a autorização, a cópia para a VPS, a revogação, a resposta aos avisos de autorização e a transferência da posse do projeto ao cliente na entrega. O `.env.example` deve trazer as variáveis novas. | Must | Uma pessoa que nunca usou o Google Cloud cria o projeto e autoriza uma caixa seguindo só o guia; o `.env.example` lista `AUTH_EMAIL<n>`, `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` e `DIR_AUTORIZACOES`. | 🟢 |
| RF-14 | O guia deve trazer o comunicado ao titular, em linguagem não técnica: que o operador autorizará a ferramenta em nome dele, que a concessão do Google menciona acesso total ao correio, que a ferramenta só lê, e como conferir e revogar o acesso na própria conta. | Should | O guia contém um texto de até 10 linhas, pronto para ser enviado ao titular antes da autorização da caixa. | 🟢 |

## 6. Requisitos Não Funcionais

| Tipo | Requisito | Evidência ou justificativa | Confidência |
|------|-----------|----------------------------|-------------|
| Segurança | Segredo do cliente, autorizações e credenciais temporárias nunca são gravados em log, aviso ou saída; a busca pelos seus valores nos logs de um ciclo real não retorna ocorrência. | `_reversa_sdd/sdd/configuracao-caixas.md#6. Requisitos Funcionais` (RF-09) | 🟢 |
| Segurança | Arquivos de autorização ficam fora do versionamento (o diretório de autorizações entra no `.gitignore`) e com permissão 600; as credenciais do cliente ficam no `.env`, sob as regras que já valem para ele. | `_reversa_sdd/sdd/configuracao-caixas.md#12. Segurança e Privacidade` | 🟢 |
| Segurança | A credencial temporária vive só em memória, pelo tempo da execução; em disco fica apenas a autorização durável. | Minimiza segredo em repouso na VPS. | 🟡 |
| Privacidade | O consentimento concede mais do que a ferramenta usa (RN-03); o acesso efetivo continua restrito à leitura, coberto pelo teste que proíbe comandos de escrita. | Regra W014 do `regression-watch.md` da feature 001; LGPD, princípio da necessidade. | 🟡 |
| Confiabilidade | A obtenção da credencial temporária tem tempo limite de 60 s e cabe no limite de 20 min por execução. | `_reversa_sdd/sdd/coleta-email.md#11. Edge Cases e Tratamento de Erros` (EC-03); decisão D-14 do roadmap da feature 001. | 🟡 |
| Compatibilidade | Instalação que não declare nenhuma caixa em `oauth` se comporta exatamente como hoje; os 236 testes atuais seguem passando sem alteração de expectativa. | RN-01. | 🟢 |
| Custo | Nenhum custo recorrente novo; projeto no Google Cloud sem conta de faturamento. | `_reversa_sdd/prd.md#6. Restrições` | 🟡 |
| Observabilidade | O log de cada execução registra, por caixa, o modo de autenticação usado e o resultado; o resumo da execução distingue falha de senha de falha de autorização. | `_reversa_sdd/sdd/execucao-monitoramento.md#6. Requisitos Funcionais` | 🟡 |
| Testabilidade | Os testes automatizados não dependem do Google: o serviço de autorização e o servidor IMAP são substituídos por dublês locais; a validação contra as contas reais é roteiro manual. | Padrão da feature 001 (`tests/RASTREABILIDADE.md`). | 🟢 |

## 7. Critérios de Aceitação

```gherkin
Cenário: instalação atual segue funcionando sem edição
  Dado um .env com EMAIL1 e SENHA_EMAIL1 e nenhuma variável AUTH_EMAIL<n>
  Quando o operador roda verificar-config
  Então a caixa 1 aparece em modo senha
  E nenhuma credencial de cliente OAuth é exigida

Cenário: caixa em oauth dispensa a senha
  Dado AUTH_EMAIL2=oauth, as credenciais do cliente definidas e SENHA_EMAIL2 ausente
  Quando o operador roda verificar-config
  Então a caixa 2 é válida e aparece como "oauth (sem autorização)"

Cenário: modo de autenticação inválido
  Dado AUTH_EMAIL3=token
  Quando a configuração é carregada
  Então a caixa 3 é inválida com o motivo "caixa 3: AUTH_EMAIL3 inválido (use senha ou oauth)"
  E as demais caixas seguem válidas

Cenário: credenciais do cliente ausentes
  Dado AUTH_EMAIL2=oauth e nenhuma credencial de cliente OAuth
  Quando a configuração é carregada
  Então a caixa 2 é inválida com o motivo "credenciais do cliente OAuth ausentes"
  E a caixa 1, em modo senha, é processada normalmente

Cenário: autorização de uma caixa no computador do operador
  Dado a caixa 2 em modo oauth, sem autorização gravada
  Quando o operador roda autorizar-caixa 2 e o titular consente com a conta de EMAIL2
  Então o arquivo de autorização da caixa 2 é gravado com permissão 600
  E a saída informa "caixa 2: autorizada"
  E nenhum segredo aparece no terminal nem no log

Cenário: diretório de autorizações configurável
  Dado DIR_AUTORIZACOES apontando para outro diretório
  Quando o operador roda autorizar-caixa 2 e consente com a conta de EMAIL2
  Então o arquivo de autorização é gravado nesse diretório, nomeado pelo endereço da caixa 2
  E verificar-config mostra a caixa 2 como "oauth (autorizada)"

Cenário: consentimento dado com a conta errada
  Dado a caixa 2 em modo oauth
  Quando o operador roda autorizar-caixa 2 e o consentimento vem da conta de EMAIL3
  Então nenhum arquivo é gravado
  E a saída diz "conta autorizada difere de EMAIL2"

Cenário: ciclo completo com caixa em oauth
  Dado a caixa 2 autorizada, com a autorização copiada para a VPS
  Quando o ciclo executa
  Então o log registra "caixa 2: conectada (oauth)"
  E os anexos da caixa 2 são coletados e enviados como os de uma caixa em modo senha
  E as mensagens não lidas continuam não lidas

Cenário: renovação sem intervenção
  Dado a caixa 2 autorizada há mais de 1 hora
  Quando um novo ciclo executa
  Então a caixa 2 é acessada sem nova autorização

Cenário: autorização revogada pelo titular
  Dado a autorização da caixa 2 revogada na conta do titular
  Quando o ciclo executa
  Então a caixa 2 é pulada com o log "caixa 2: autorização OAuth recusada (rode autorizar-caixa 2)"
  E a caixa 1 é processada
  E o código de saída é 1
  E o aviso de falha é enviado uma vez e suprimido por 6 horas

Cenário: recuperação após nova autorização
  Dado a caixa 2 com aviso de autorização recusada ativo
  Quando o operador refaz autorizar-caixa 2 e o ciclo seguinte termina com código 0
  Então o aviso de recuperação é enviado uma única vez

Cenário: serviço de autorização do Google fora do ar
  Dado a caixa 2 autorizada e o serviço de autorização sem resposta em 60 s
  Quando o ciclo executa
  Então a caixa 2 é pulada como falha transitória
  E o arquivo de autorização permanece intacto

Cenário: troca de modo não duplica documentos
  Dado a caixa 1 com documentos já enviados em modo senha
  Quando o operador muda AUTH_EMAIL1 para oauth, autoriza a caixa e o ciclo executa
  Então nenhum documento já enviado é enviado de novo

Cenário: teste de acesso por caixa
  Dado a caixa 1 autorizada e a caixa 2 sem autorização
  Quando o operador roda testar-caixa
  Então a saída traz "caixa 1: acesso confirmado" e "caixa 2: falhou (sem autorização)"
  E o código de saída é 1
  E cada caixa recebeu uma única tentativa de login

Cenário: arquivo de autorização com permissão aberta
  Dado o arquivo de autorização da caixa 2 com permissão 644
  Quando o ciclo executa
  Então o log registra "permissão da autorização da caixa 2 mais aberta que 600"

Cenário: segredos fora dos logs
  Dado um ciclo real com ao menos uma caixa em oauth
  Quando o operador busca nos logs o segredo do cliente e o conteúdo da autorização
  Então nenhuma ocorrência é encontrada
```

## 8. Prioridade MoSCoW

| Item | MoSCoW | Justificativa |
|------|--------|---------------|
| RF-01, RF-02, RF-03 | Must | Sem o modo por caixa e as credenciais do cliente, não há como declarar uma caixa em OAuth mantendo o `.env` atual válido. |
| RF-04, RF-05, RF-06 | Must | A autorização é o ato que destrava a operação; a VPS não tem navegador, e autorizar a conta errada arquivaria documentos de uma empresa na pasta de outra. |
| RF-07 | Must | É o acesso propriamente dito. |
| RF-08, RF-09 | Must | Revogação e indisponibilidade são os modos de falha novos; sem tratamento próprio, o operador não sabe o que refazer, ou perde uma autorização válida. |
| RF-13 | Must | O pedido do usuário começa pela criação do projeto no Google Cloud; sem roteiro, a entrega a terceiros (objetivo da persona operador-tecnico) fica comprometida. |
| RF-10, RF-12 | Should | Diagnóstico e higiene de segredos; a operação funciona sem eles. |
| RF-11 | Should | Hoje o teste de login é feito à mão; o comando evita tentativas repetidas nas contas dos clientes, mas não bloqueia a entrada em operação. |
| RF-14 | Should | O consentimento é dado pelo operador em nome do titular (RN-09); o comunicado mantém o titular informado e ciente de como revogar. |
| Delegação em todo o domínio por conta de serviço | Won't | Dispensaria o consentimento por caixa, mas depende do administrador de cada um dos três domínios e não alcança a conta `@gmail.com`; fica registrada como evolução possível. |
| Consentimento remoto pelo titular, em computador diferente do que roda o comando | Won't | A decisão desta sessão põe o consentimento nas mãos do operador; o fluxo remoto volta à pauta se algum titular preferir consentir por conta própria. |
| Leitura pela API do Gmail com escopo somente leitura, em vez de IMAP | Won't | Atenderia melhor ao princípio da necessidade (RN-03), mas exige reescrever a coleta; fica registrado como evolução possível. |
| Remoção do modo senha | Won't | A senha de app continua sendo o caminho mais simples para quem já usa verificação em duas etapas. |
| Verificação pública do aplicativo junto ao Google | Won't | O uso é privado, com cinco contas conhecidas; a verificação pública de escopo restrito exige auditoria de segurança paga, o que fere a RN-08. |

## 9. Esclarecimentos

### Sessão 2026-09-21

- **Q:** (L-01) Qual mecanismo de autorização a feature adota? **R:** consentimento por conta nas cinco caixas agora, com a delegação em todo o domínio registrada como evolução possível (Won't).
- **Q:** (L-02) Em qual conta o projeto do Google Cloud é criado, e com que tipo de público? **R:** na conta pessoal do operador, com público externo publicado; a posse é transferida ao cliente na entrega.
- **Q:** (L-03) Quem dá o consentimento em cada caixa? **R:** o operador, entrando em cada conta com as senhas recebidas; registrado como exceção justificada na RN-09, com comunicado prévio ao titular (RF-14). O RF-04 não precisa suportar consentimento em outra máquina.
- **Q:** Onde ficam o identificador e o segredo do cliente OAuth? **R:** em duas variáveis do `.env`, `OAUTH_CLIENT_ID` e `OAUTH_CLIENT_SECRET`; o RF-12 passa a cobrir só os arquivos de autorização.
- **Q:** Onde ficam os arquivos de autorização das caixas, e como são nomeados? **R:** em diretório configurável por `DIR_AUTORIZACOES`, com o padrão `autorizacoes/` ao lado do `.env`, um arquivo por caixa nomeado pelo endereço, coerente com a RN-07.

## 10. Lacunas

Nenhuma dúvida bloqueante em aberto: L-01, L-02 e L-03 foram resolvidas na sessão de 2026-09-21 (seção 9).

Pontos 🟡 a conferir na documentação oficial durante o planejamento, sem bloquear os requisitos: o escopo exigido para IMAP com OAuth; a validade de 7 dias da autorização em modo de teste; o limite de 100 contas para aplicativo não verificado; a necessidade de o administrador de cada domínio do Workspace marcar o aplicativo como confiável quando o acesso de aplicativos de terceiros estiver restrito; se o IMAP está habilitado nos três domínios (`_reversa_sdd/sdd/coleta-email.md#10. Integrações e Dependências`); se o Google impõe desafio de identidade (código por SMS ou confirmação em outro aparelho) quando o operador entra nas contas a partir de máquina desconhecida, o que obrigaria a envolver o titular naquela caixa; e as condições para transferir a posse de um projeto criado em conta pessoal, sem organização, para a conta do cliente.

## Pendências de Qualidade

- Q-010: RF-13 e RF-14 são requisitos de documentação e não têm cenário Gherkin; a verificação é a leitura do guia por terceiro, em roteiro manual, como o RF-20 da feature 001.
- Q-018: o documento nomeia Google, Gmail, Google Cloud e Telegram porque a feature trata justamente da integração com esses serviços; nenhuma biblioteca ou estrutura de código é prescrita.

## 11. Histórico de alterações

| Data | Alteração | Autor |
|------|-----------|-------|
| 2026-09-21 | Versão inicial gerada por `/reversa-requirements` | reversa |
| 2026-09-21 | Sessão de `/reversa-clarify`: L-01 a L-03 resolvidas; RN-09 criada; RF-03, RF-04, RF-12, RF-13 e RF-14 reescritos; local das credenciais do cliente e das autorizações definido | reversa |
