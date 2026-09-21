# Actions: acesso às caixas do Gmail por OAuth 2.0, com projeto próprio no Google Cloud

> Identificador: `002-oauth-gmail-google-cloud`
> Data: `2026-09-21`
> Roadmap: `_reversa_forward/002-oauth-gmail-google-cloud/roadmap.md`
>
> ⚠️ **Escrita fora das pastas do Reversa:** quase todas as ações escrevem em `src/`, `tests/`, `docs/`, `.env.example`, `.gitignore` e `README.md`. Em 2026-09-21, `.reversa/reversa-config.json` está com `allowLegacyEdits: true` e `allowedPaths` vazio (liberação irrestrita); o `/reversa-coding` deve reler o arquivo antes de escrever.
>
> ⚠️ **Ação manual:** T039 depende do projeto criado no Google Cloud e do consentimento numa conta real; é do operador e fecha as premissas P-01 a P-03. As demais ações são executáveis por agente, sem credenciais reais e sem acesso ao Google.
>
> Convenção dos testes: nenhum segredo real entra no repositório; o serviço de autorização e o IMAP são dublês locais (D-15). Os caminhos de código abaixo são relativos a `src/email_nf_onedrive/`, salvo quando começam por `tests/`, `docs/` ou pela raiz.

## Resumo

| Métrica | Valor |
|---------|-------|
| Total de ações | 39 |
| Paralelizáveis (`[//]`) | 24 |
| Maior cadeia de dependência | 9 (T003 → T019 → T025 → T028 → T029 → T031 → T032 → T033 → T037) |

| Fase | Ações |
|------|-------|
| 1, Preparação | 7 |
| 2, Testes | 9 |
| 3, Núcleo | 11 |
| 4, Integração | 6 |
| 5, Polimento | 6 |

## Fase 1, Preparação

| ID | Descrição | Dependências | Paralelismo | Arquivo alvo | Confidência | Status |
|----|-----------|--------------|-------------|--------------|-------------|--------|
| T001 | Acrescentar `autorizacoes/` ao `.gitignore`, com comentário de que o diretório guarda a autorização durável das caixas (`data-delta.md` §8). | - | `[//]` | `.gitignore` | 🟢 | `[X]` |
| T002 | Acrescentar ao `.env.example` o bloco comentado com `AUTH_EMAIL1=senha`, `OAUTH_CLIENT_ID=`, `OAUTH_CLIENT_SECRET=` e `DIR_AUTORIZACOES=autorizacoes`, com remissão à seção do guia sobre o Google Cloud (`interfaces/cli-e-env.md`). | - | `[//]` | `.env.example` | 🟢 | `[X]` |
| T003 | Criar o subpacote `autorizacao/` com `__init__.py` vazio, no padrão dos demais subpacotes. | - | `[//]` | `autorizacao/__init__.py` | 🟢 | `[X]` |
| T004 | Estender o modelo: `Caixa.modo` (`"senha"` ou `"oauth"`, padrão `"senha"`); classe `ClienteOAuth` com `client_id` e `client_secret` fora do `repr`; `Configuracao.cliente_oauth: ClienteOAuth \| None` e `Configuracao.dir_autorizacoes: Path` (`data-delta.md` §2 e §3). Os padrões não podem quebrar nenhuma construção existente. | - | `[//]` | `configuracao/modelo.py` | 🟢 | `[X]` |
| T005 | Estender o dublê IMAP: `ServidorIMAPFalso.adicionar_caixa_oauth(endereco, credencial)` e `ConexaoFalsa.authenticate(mecanismo, funcao)`, que chama `funcao(b"")`, confere `user=` e a credencial, na recusa chama `funcao(<desafio JSON>)` e exige retorno vazio antes de levantar `imaplib.IMAP4.error`; o comando entra em `nomes_de_comandos()` como `AUTHENTICATE` (`interfaces/imap-gmail-xoauth2.md`). | - | `[//]` | `tests/integracao/dubles.py` | 🟢 | `[X]` |
| T006 | Criar o dublê `ServicoAutorizacaoFalso`: servidor HTTP local em linha de execução própria, com rotas de troca, renovação e revogação, respostas programáveis por `refresh_token` e por `code` (sucesso, `invalid_grant`, `invalid_client`, 503, 429, JSON inválido, atraso acima do tempo limite) e contagem de requisições por rota (D-15, `interfaces/google-oauth.md`). | T005 | - | `tests/integracao/dubles.py` | 🟢 | `[X]` |
| T007 | Acrescentar fixtures de integração: serviço de autorização falso iniciado e encerrado por teste, com os endereços prontos para injeção em `ciclo.Dependencias`; fábrica que grava um arquivo de autorização válido (JSON, 600, diretório 700) para um endereço; `.env` de exemplo com caixas em `senha` e em `oauth`. | T006 | - | `tests/integracao/conftest.py` | 🟢 | `[X]` |

## Fase 2, Testes

Escritos antes do núcleo, como na feature 001; ficam vermelhos até a fase correspondente.

| ID | Descrição | Dependências | Paralelismo | Arquivo alvo | Confidência | Status |
|----|-----------|--------------|-------------|--------------|-------------|--------|
| T008 | Testar a configuração (D-10): `AUTH_EMAIL<n>` ausente vale `senha`; `OAUTH` em maiúsculas é aceito; valor inválido invalida só a caixa; caixa em `oauth` dispensa a senha e é válida sem arquivo de autorização; credenciais do cliente ausentes invalidam só as caixas em `oauth` (RF-03); `.env` sem nenhuma variável nova carrega como antes; alertas de senha presente em caixa `oauth`, de `AUTH_EMAIL<n>` órfã e de permissão mais aberta que 600 e 700; ausência de alerta para `OAUTH_*` sem caixa em `oauth`; endereço com separador de caminho invalida a caixa em `oauth`. | T004 | `[//]` | `tests/unidade/test_configuracao.py` | 🟢 | `[X]` |
| T009 | Testar o arquivo de autorização (D-05): nome pelo endereço em minúsculas; gravação com 600 em diretório 700 criado sob demanda; regravação atômica sem resíduo temporário; cada recusa de leitura (`versao`, endereço divergente, `client_id` divergente, `refresh_token` vazio, escopo do correio ausente, JSON ilegível, arquivo ausente) com o motivo próprio; `DIR_AUTORIZACOES` relativo resolvido a partir da instalação; registro do `refresh_token` em `segredos`. | T003, T004 | `[//]` | `tests/unidade/test_autorizacao_arquivo.py` | 🟢 | `[X]` |
| T010 | Testar as peças puras do fluxo (D-02, D-04): verificador e desafio PKCE `S256` em base64 URL sem preenchimento; `state` de 32 bytes; endereço de consentimento com todos os parâmetros da tabela de `interfaces/google-oauth.md` §1; leitura da declaração `email` e de `email_verified` do `id_token` sem validar a assinatura, inclusive com preenchimento base64 faltante e com `id_token` malformado. | T003 | `[//]` | `tests/unidade/test_autorizacao_fluxo.py` | 🟡 | `[X]` |
| T011 | Testar a renovação contra o dublê, linha a linha da tabela de `interfaces/google-oauth.md` §3: 200; `invalid_grant`; `invalid_client` e `unauthorized_client`; outro `error`; 429 e 5xx; tempo esgotado; JSON inválido ou sem `access_token`. Conferir a classe devolvida, a tentativa única (D-09), o registro do `access_token` em `segredos` e o mascaramento de `error_description`. | T006 | `[//]` | `tests/integracao/test_autorizacao_servico.py` | 🟢 | `[X]` |
| T012 | Atualizar o teste da coleta: `COMANDOS_PERMITIDOS` ganha `AUTHENTICATE` e nada mais (W014); caso novo de caixa em `oauth` que conecta por `conectar_oauth` sem emitir `LOGIN`; caso de recusa em que o cliente responde ao desafio com linha vazia e a falha sai com a causa de autorização (D-07). | T005 | `[//]` | `tests/integracao/test_coleta.py` | 🟢 | `[X]` |
| T013 | Testar o ciclo com OAuth no caminho feliz: instalação mista coleta as caixas dos dois modos; log "conectada (senha)" e "conectada (oauth)"; uma requisição de renovação por caixa em `oauth` e zero em instalação sem OAuth; arquivo de autorização intacto após o ciclo; `client_secret`, `refresh_token` e `access_token` ausentes dos logs (D-06); linha de resumo sem o segmento de autorização quando não há falha (D-13). | T007 | `[//]` | `tests/integracao/test_ciclo_oauth.py` | 🟡 | `[X]` |
| T014 | Testar o ciclo com falhas de autorização (D-08, RF-08, RF-09): arquivo ausente e `invalid_grant` geram `caixa<n>:autorizacao`; 503 gera `caixa<n>:autorizacao-servico`; `invalid_client` gera um único `oauth:cliente` e pula as demais caixas em `oauth` sem nova requisição; `AUTHENTICATE` recusado gera `caixa<n>:autorizacao`; em todos os casos o arquivo fica intacto, as caixas em `senha` seguem, e o resumo traz "`k` de autorização". | T007 | `[//]` | `tests/integracao/test_ciclo_oauth_falhas.py` | 🟢 | `[X]` |
| T015 | Testar `autorizar-caixa` com um navegador simulado que lê o endereço impresso e chama o retorno local: sucesso grava o arquivo e sai com 0; recusas com código 2 e nada gravado (caixa inexistente, caixa em `senha`, credenciais ausentes, `access_denied`, `state` divergente, tempo esgotado com limite injetado, `refresh_token` ausente, escopo do correio não concedido); conta divergente revoga no dublê e nada grava (RF-06); nenhuma linha da saída contém segredo (D-03, D-12). | T007 | `[//]` | `tests/integracao/test_autorizar_caixa.py` | 🟡 | `[X]` |
| T016 | Testar `testar-caixa` e `verificar-config`: linhas de `testar-caixa` por desfecho e códigos 0, 1 e 2, com uma tentativa por caixa, sem trava, sem aviso e sem tocar no registro (D-11); `verificar-config` com "oauth (autorizada)" e "oauth (sem autorização)", linha das caixas em `senha` idêntica à atual, linhas finais só quando há caixa em `oauth`, e nenhuma requisição de rede (RF-10). | T007 | `[//]` | `tests/integracao/test_cli_caixas.py` | 🟢 | `[X]` |

## Fase 3, Núcleo

| ID | Descrição | Dependências | Paralelismo | Arquivo alvo | Confidência | Status |
|----|-----------|--------------|-------------|--------------|-------------|--------|
| T017 | Ler `AUTH_EMAIL<n>`, `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` e `DIR_AUTORIZACOES` (D-10): ordem de validação endereço, modo, senha ou credenciais do cliente, duplicidade; senha exigida só em `senha` e esvaziada em `oauth`; `cliente_oauth` é `None` se faltar qualquer das duas variáveis, caso em que as caixas em `oauth` viram `CaixaInvalida`; `DIR_AUTORIZACOES` relativo resolvido a partir de `home`; `client_secret` registrado em `segredos`; endereço com separador de caminho ou byte nulo invalida a caixa em `oauth`. | T004 | - | `configuracao/carregar.py` | 🟢 | `[X]` |
| T018 | Acrescentar os alertas não bloqueantes (D-10, RF-12): "SENHA_EMAILn presente em caixa oauth; retire-a do .env"; `AUTH_EMAIL<n>` órfã; permissão do arquivo de autorização mais aberta que 600 e do diretório mais aberta que 700, verificadas por `stat`, sem abrir o arquivo; nenhum alerta para `OAUTH_*` sem caixa em `oauth`. | T017 | - | `configuracao/carregar.py` | 🟢 | `[X]` |
| T019 | Implementar o arquivo de autorização (D-05, `data-delta.md` §4): `caminho(dir, endereco)`; `ler(...)` com as validações da tabela, erro tipado com o motivo e registro do `refresh_token` em `segredos`; `gravar(...)` com diretório 700, temporário aberto por `os.open(O_CREAT \| O_EXCL \| O_WRONLY, 0o600)` e `os.replace`; `existe_e_legivel(...)` por `stat`, para o `verificar-config`. | T003, T004 | `[//]` | `autorizacao/arquivo.py` | 🟢 | `[X]` |
| T020 | Implementar o cliente do serviço com `urllib` (D-01, D-09, D-14): constantes dos três endereços do Google reunidas num objeto `Enderecos` injetável; `POST` de formulário com tempo limite de 60 s e tentativa única; `renovar(...)` devolvendo a credencial temporária ou um erro classificado em permanente, cliente ou transitório conforme `interfaces/google-oauth.md` §3; `access_token` registrado em `segredos`; log só com o código de estado e o campo `error`, e `error_description` mascarado. | T003 | `[//]` | `autorizacao/servico.py` | 🟢 | `[X]` |
| T021 | Acrescentar ao cliente do serviço `trocar_codigo(...)` (com `code_verifier` e `redirect_uri`) e `revogar(refresh_token)`, cuja falha é devolvida sem exceção para que o chamador só acrescente a orientação de revogar à mão (`interfaces/google-oauth.md` §2 e §4). | T020 | - | `autorizacao/servico.py` | 🟢 | `[X]` |
| T022 | Implementar as peças puras do fluxo (D-02, D-04): geração do verificador e do desafio PKCE, do `state`, montagem do endereço de consentimento com `login_hint` e `prompt=consent`, e decodificação do `id_token` sem validar a assinatura, devolvendo `email` e `email_verified`. | T003 | `[//]` | `autorizacao/fluxo.py` | 🟡 | `[X]` |
| T023 | Implementar o retorno local (D-02, R-08): `http.server` em `127.0.0.1` com porta efêmera, atende uma requisição e encerra, espera máxima de 5 min injetável, página estática que não reflete parâmetro algum, e resultado tipado (código, `access_denied`, `state` inválido, tempo esgotado, porta indisponível). | T022 | - | `autorizacao/fluxo.py` | 🟢 | `[X]` |
| T024 | Implementar a orquestração `autorizar(...)` (D-03, D-04, D-12): imprime o endereço sem abrir navegador, espera o retorno, troca o código, recusa resposta sem `refresh_token`, sem o escopo do correio ou com `id_token` sem `email` verificado, compara a conta com `EMAIL<n>` sem diferenciar maiúsculas, revoga e nada grava na divergência, e grava o arquivo no sucesso; devolve o desfecho com a mensagem exata de `interfaces/cli-e-env.md`. | T019, T021, T023 | - | `autorizacao/fluxo.py` | 🟡 | `[X]` |
| T025 | Implementar o provedor de credencial por execução (D-06, D-08): para uma caixa em `oauth`, lê o arquivo, renova uma única vez e devolve a credencial em memória ou uma falha com a causa (`autorizacao`, com a variante "ausente"; `autorizacao-servico`; `oauth:cliente`); depois de um `oauth:cliente`, responde às demais caixas com a mesma falha sem nova requisição; nunca escreve nem apaga o arquivo (RF-09). | T019, T020 | `[//]` | `autorizacao/credencial.py` | 🟢 | `[X]` |
| T026 | Acrescentar `ClienteIMAP.conectar_oauth(usuario, credencial)` (D-07), sem alterar `conectar`: `authenticate("XOAUTH2", funcao)` com a resposta inicial `user=<endereço>^Aauth=Bearer <credencial>^A^A` na primeira chamada e vazio na segunda; o desafio de recusa é decodificado, mascarado, truncado em 200 caracteres e registrado; a recusa levanta `ErroIMAP` com causa própria de autorização. | - | `[//]` | `coleta/imap.py` | 🟢 | `[X]` |
| T027 | Acrescentar `ResumoExecucao.falhas_autorizacao` (inteiro, padrão 0) e o segmento "`k` de autorização" depois de "`f` falhas" na linha de resumo, presente só quando `k` > 0 (D-13, `data-delta.md` §6). | - | `[//]` | `execucao/resumo.py` | 🟡 | `[X]` |

## Fase 4, Integração

| ID | Descrição | Dependências | Paralelismo | Arquivo alvo | Confidência | Status |
|----|-----------|--------------|-------------|--------------|-------------|--------|
| T028 | Ligar a coleta aos dois modos (D-07, D-08, D-13): em `oauth`, pedir a credencial ao provedor antes de abrir a conexão e pular a caixa com a `Falha` da causa devolvida; conectar por `conectar_oauth` ou por `conectar` conforme `caixa.modo`; mapear a recusa do `AUTHENTICATE` para `caixa<n>:autorizacao` com a mensagem de `interfaces/imap-gmail-xoauth2.md`; log "caixa n: conectada (senha)" ou "(oauth)". O provedor entra por parâmetro, de modo que a instalação sem OAuth não o constrói. | T017, T025, T026 | - | `coleta/coleta.py` | 🟡 | `[X]` |
| T029 | Ligar o ciclo (D-14, D-08): `Dependencias` ganha os endereços do serviço de autorização, com o padrão do Google e nunca lidos do `.env`; o provedor de credencial é construído uma vez por execução e só se houver caixa em `oauth`; as falhas de causa `autorizacao`, `autorizacao-servico` e `oauth:cliente` somam em `falhas_autorizacao` e seguem ao gerenciador de avisos com as mensagens-base de `data-delta.md` §7, sem mudança no gerenciador. | T027, T028 | - | `execucao/ciclo.py` | 🟢 | `[X]` |
| T030 | Alterar `verificar-config` (RF-10): o final da linha de cada caixa passa a `senha ****`, `oauth (autorizada)` ou `oauth (sem autorização)`; linhas finais `cliente OAuth: configurado` e `diretório de autorizações: <caminho>` só quando há caixa em `oauth`; nenhum acesso à rede. | T018, T019 | - | `cli.py` | 🟢 | `[X]` |
| T031 | Acrescentar o subcomando `testar-caixa [<n>]` (D-11, RF-11): reusa a fábrica IMAP e o provedor de credencial do ciclo; autentica, faz `EXAMINE` da pasta e `LOGOUT`, uma tentativa por caixa; uma linha por caixa no formato de `interfaces/cli-e-env.md`, inclusive para caixas inválidas e pasta inexistente; sem trava, sem aviso e sem registro; códigos 0, 1 e 2. | T029, T030 | - | `cli.py` | 🟢 | `[X]` |
| T032 | Acrescentar o subcomando `autorizar-caixa <n>` (D-12, RF-04 a RF-06): verifica antes de qualquer rede a caixa existente, válida e em `oauth` e as credenciais do cliente; delega a `autorizacao.fluxo.autorizar`; imprime a saída de sucesso ou a recusa exata; código 0 quando grava, 2 em qualquer recusa; sem trava, sem aviso e sem registro. | T024, T031 | - | `cli.py` | 🟢 | `[X]` |
| T033 | Rodar a suíte inteira e fechá-la verde: os 236 testes anteriores sem alteração de expectativa, salvo o `COMANDOS_PERMITIDOS` de T012, e todos os novos. Se algum teste antigo depender do texto "conectada", aplicar o recuo do R-07 (sufixo só em `oauth`) e registrar a escolha nas notas de execução. | T008, T009, T010, T011, T012, T013, T014, T015, T016, T032 | - | `tests/` | 🟢 | `[X]` |

## Fase 5, Polimento

| ID | Descrição | Dependências | Paralelismo | Arquivo alvo | Confidência | Status |
|----|-----------|--------------|-------------|--------------|-------------|--------|
| T034 | Escrever no guia a seção do Google Cloud (RF-13, D-16): projeto sem conta de faturamento na conta do operador, tela de consentimento com público externo e estado "em produção" sem pedir verificação, escopo `https://mail.google.com/`, cliente OAuth do tipo aplicativo para computador, onde copiar o identificador e o segredo, a tela "o Google não verificou este app" com o caminho "Avançado", e o passo do console de administração do Workspace para marcar o cliente como confiável (P-02). | - | `[//]` | `docs/instalacao-e-operacao.md` | 🟢 | `[X]` |
| T035 | Escrever no guia a operação por caixa: comunicado ao titular (RF-14), com o aviso de que trocar a senha exige nova autorização (R-01); `AUTH_EMAIL<n>=oauth`, `autorizar-caixa` em janela anônima e `testar-caixa`; alternativa de autorizar em chamada com o titular (P-01); cópia do diretório de autorizações à VPS por canal cifrado, com permissão e backup; os cinco passos do plano de migração e a volta atrás (roadmap §8); revogação pela conta do titular e pela troca do segredo do cliente (R-05); tabela das três causas de aviso com a ação de cada uma; transferência de posse do projeto na entrega (D-17). | T032, T034 | - | `docs/instalacao-e-operacao.md` | 🟡 | `[X]` |
| T036 | Atualizar o `README.md`: os dois modos de autenticação por caixa, os comandos `autorizar-caixa` e `testar-caixa`, as variáveis novas e a remissão à seção do guia. | T032 | `[//]` | `README.md` | 🟢 | `[X]` |
| T037 | Atualizar o mapa de rastreabilidade com os 16 cenários Gherkin do `requirements.md` §7, apontando o teste automatizado de cada um ou, nos que dependem do Google real, o roteiro manual do `onboarding.md`. | T033 | `[//]` | `tests/RASTREABILIDADE.md` | 🟢 | `[X]` |
| T038 | Conferir o `onboarding.md` contra o que foi implementado: os roteiros manuais de autorização real, de renovação após 1 h e de revogação pelo titular devem citar os comandos e as mensagens exatas; completar o que faltar. | T033 | `[//]` | `_reversa_forward/002-oauth-gmail-google-cloud/onboarding.md` | 🟢 | `[X]` |
| T039 | **Ação manual do operador.** Criar o projeto no Google Cloud seguindo só o guia, autorizar ao menos uma caixa real, copiar a autorização à VPS, rodar `testar-caixa` e um ciclo lá, e conferir por `grep` que o segredo do cliente, a autorização durável e a credencial temporária não aparecem nos logs (critério de pronto, roadmap §10). Registrar o desfecho das premissas P-01 a P-03. | T033, T035 | - | `docs/instalacao-e-operacao.md` | 🟡 | `[ ]` |

## Notas de execução

<!--
Reservado para /reversa-coding registrar avisos ou observações que surgiram durante a execução.
-->

Rodada única de 2026-09-21: T001 a T038 concluídas; T039 é manual e fica aberta. `pytest`: 361 testes verdes (236 anteriores e 125 novos).

1. **R-07 não se materializou.** Nenhum dos 236 testes anteriores dependia do texto "conectada"; o sufixo "(senha)" ou "(oauth)" vale nos dois modos, como decidiu a D-13. A única expectativa antiga alterada foi `COMANDOS_PERMITIDOS`, em `tests/integracao/test_coleta.py`, que ganhou `AUTHENTICATE` (previsto em T012).
2. **Conta não identificada vale como conta divergente.** Quando o `id_token` vem sem `email` ou com `email_verified` falso, o `autorizar-caixa` recusa com "caixa n: o Google não informou a conta que consentiu" **e revoga** a autorização recém-emitida, embora `interfaces/google-oauth.md` §2 só peça a recusa. Motivo: nesse ponto já existe uma concessão de acesso total a uma conta que não se sabe qual é, que é a situação que o RF-06 quer evitar. Quando o escopo do correio não foi concedido, não há revogação, porque a concessão não dá acesso à caixa.
3. **Mensagens não previstas no contrato**, acrescentadas por necessidade: "caixa n: retorno inválido (state)" também cobre retorno sem `code`; "caixa n: troca do código recusada (<error>)"; "caixa n: serviço de autorização do Google indisponível; tente de novo" e a de credenciais do cliente recusadas, ambas na troca do código; "caixa n: não foi possível abrir a porta local de retorno" (R-08); e a variante "autorização OAuth inválida: <motivo>" para arquivo ilegível, de outro endereço ou de outro cliente, ao lado de "ausente" e "recusada".
4. **`/favicon.ico` não consome o retorno.** O contrato diz que o servidor local "atende uma requisição e encerra". Na prática o navegador pode pedir o ícone antes ou depois do retorno; pedidos a caminho diferente de `/` recebem 404 e a espera continua até o prazo.
5. **Ponto de injeção a mais em `ciclo.Dependencias`:** `ao_exibir_endereco`, chamado com o endereço de consentimento já impresso. Existe só para o teste simular o navegador; em produção é `None`, e a D-03 (não abrir navegador) segue valendo. O tempo limite das requisições e a espera do consentimento ficam em `autorizacao.servico.Enderecos`, junto com os endereços, e portanto também só mudam por injeção (D-14).
6. **As linhas do `testar-caixa` saem todas na saída padrão**, inclusive as de falha, para preservar a ordem por índice; só os erros de configuração e de índice inexistente vão à saída de erro.
7. **Três testes de cenário foram acrescentados depois da fase 2**, ao montar o mapa de rastreabilidade (T037): troca de modo sem duplicar (RN-07), diretório de autorizações configurável e alerta de permissão aberta no log do ciclo.
8. **Guia, §16.4:** o `onboarding.md` copiava as autorizações por `scp` direto ao usuário de serviço, que não aceita login (guia, seção 3). O guia e o `onboarding.md` passaram a usar o usuário do operador na VPS e `sudo`.

## Histórico de alterações

| Data | Alteração | Autor |
|------|-----------|-------|
| 2026-09-21 | Versão inicial gerada por `/reversa-to-do` | reversa |
| 2026-09-21 | `/reversa-coding`: T001 a T038 concluídas; notas de execução registradas | reversa |
