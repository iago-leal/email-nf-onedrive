# Regression watch: acesso às caixas do Gmail por OAuth 2.0

> Identificador: `002-oauth-gmail-google-cloud`
> Âncora greenfield: não há regras 🟢 extraídas de código anterior, e o watch principal fica vazio. Os itens de "Observações" ganham peso de regressão quando uma futura extração `/reversa` sobre o código os confirmar como 🟢.
> A numeração continua a da feature 001 (W001 a W021, em `_reversa_forward/001-mvp-email-nf-onedrive/regression-watch.md`), para que um ID nunca designe duas regras no projeto. O W022 revisa o W014 da 001, que passa a ser lido com esta redação.

## Watch principal

| ID | Origem (arquivo, seção) | Regra esperada após mudança | Tipo de verificação | Sinal de violação |
|----|-------------------------|-----------------------------|---------------------|-------------------|

## Observações

W022 a W037: acrescentados na rodada T001–T038, de 2026-09-21. Pendente a verificação manual com o Google real (T039).

| ID | Origem (arquivo, seção) | Regra esperada | Tipo de verificação | Sinal de violação |
|----|-------------------------|----------------|---------------------|-------------------|
| W022 | `interfaces/imap-gmail-xoauth2.md`; `roadmap.md` D-07, R-04; revisa o W014 da feature 001 | A lista fechada de comandos IMAP é `CONNECT`, `LOGIN` ou `AUTHENTICATE`, `LIST`, `EXAMINE`, `SEARCH`, `FETCH` com `BODY.PEEK[]`, `LOGOUT`. `AUTHENTICATE` é o único acréscimo; `LOGIN` e `AUTHENTICATE` nunca ocorrem na mesma conexão. | redação | `COMANDOS_PERMITIDOS` em `tests/integracao/test_coleta.py` com outro comando novo; `test_caixa_oauth_conecta_por_xoauth2_sem_login` falha. |
| W023 | `requirements.md#4` (RN-03) | A credencial temporária só é usada no `AUTHENTICATE` do IMAP; o código não chama a API do Gmail nem nenhum outro serviço do Google com ela. | ausência | Qualquer requisição com cabeçalho `Authorization: Bearer` ou endereço `gmail.googleapis.com` no pacote. |
| W024 | `requirements.md#4` (RN-01); `roadmap.md` D-10 | Sem `AUTH_EMAIL<n>`, a caixa é `senha`; o `.env` da feature 001 carrega sem alerta novo e sem nenhuma requisição ao serviço de autorização. | presença | `uni/configuracao::test_auth_ausente_vale_senha_e_nada_muda` ou `e2e/oauth::test_instalacao_sem_oauth_nao_fala_com_o_servico_de_autorizacao` falha. |
| W025 | `requirements.md#4` (RN-02, RN-09); `interfaces/cli-e-env.md` | Em `oauth`, `SENHA_EMAIL<n>` é dispensada; se presente, é ignorada (a `Caixa` fica com senha vazia), mascarada e vira o alerta "SENHA_EMAILn presente em caixa oauth; retire-a do .env". | presença | Caixa em `oauth` com `senha` não vazia em memória, ou alerta ausente. |
| W026 | `requirements.md#5` (RF-03) | Credenciais do cliente ausentes invalidam só as caixas em `oauth`; presentes sem caixa em `oauth`, não geram alerta. | presença | Instalação em `senha` abortada ou alertada por causa de `OAUTH_*`. |
| W027 | `roadmap.md` D-14 | Os endereços do serviço de autorização são constantes do código e só mudam por injeção de `Enderecos` em `ciclo.Dependencias`; nenhuma variável do `.env` ou do ambiente os altera. | ausência | Leitura de variável como `OAUTH_TOKEN_URL` em `configuracao/` ou `autorizacao/`. |
| W028 | `roadmap.md` D-06; `data-delta.md` §5 | A credencial temporária não tem representação em disco; é obtida uma vez por caixa e por execução e registrada em `segredos`. | ausência | Escrita de `access_token` em `var/` ou no arquivo de autorização; `e2e/oauth::test_credencial_temporaria_e_renovada_a_cada_execucao` falha. |
| W029 | `requirements.md#5` (RF-09); `data-delta.md` §4 | O ciclo (`executar`, `testar-caixa`) nunca escreve nem apaga arquivo de autorização, qualquer que seja a falha; só o `autorizar-caixa` grava. | ausência | Bytes do arquivo diferentes depois de um ciclo com falha (`e2e/oauth-fal`). |
| W030 | `roadmap.md` D-05; `data-delta.md` §4 | O arquivo de autorização é nomeado pelo endereço em minúsculas, gravado com 600 em diretório 700, por temporário exclusivo e `os.replace`; endereço com separador de caminho invalida a caixa em `oauth`. | presença | `uni/arquivo::test_grava_com_600_em_diretorio_700_criado_sob_demanda` ou `test_regravacao_substitui_sem_deixar_residuo` falha. |
| W031 | `requirements.md#5` (RF-06); `roadmap.md` D-04 | Conta do `id_token` diferente de `EMAIL<n>` (sem diferenciar maiúsculas), ou não identificada, revoga a autorização recém-emitida e nada grava; a autorização anterior da caixa fica intacta. | presença | `e2e/autorizar::test_conta_divergente_revoga_e_nada_grava` falha. |
| W032 | `roadmap.md` D-02, D-03 | O consentimento usa código de autorização com PKCE `S256`, `state` conferido, retorno só em `127.0.0.1` com porta efêmera, `access_type=offline` e `prompt=consent`; o endereço é impresso, e o navegador nunca é aberto pelo programa. | presença | Uso de `webbrowser` no pacote; `uni/fluxo::test_endereco_de_consentimento_traz_todos_os_parametros` falha. |
| W033 | `roadmap.md` D-08; `data-delta.md` §7 | Três causas de aviso: `caixa<n>:autorizacao` (permanente), `caixa<n>:autorizacao-servico` (transitória) e `oauth:cliente` (global, um aviso por execução); nenhuma reusa `caixa<n>:autenticacao`. | redação | Aviso de autorização com o texto "autenticação recusada"; mais de um aviso `oauth:cliente` na mesma execução. |
| W034 | `roadmap.md` D-09 | Uma tentativa de renovação por caixa e por execução, com tempo limite de 60 s; depois de `oauth:cliente`, nenhuma requisição nova na execução. | presença | Contagem de requisições maior que 1 por caixa em `int/servico` ou `e2e/oauth-fal`. |
| W035 | `roadmap.md` D-13 | A linha de resumo só ganha "`k` de autorização" quando `k` > 0; o log de conexão é "caixa n: conectada (senha)" ou "(oauth)". | redação | Resumo de instalação sem falha de autorização com o segmento; linha "conectada" sem o modo. |
| W036 | `roadmap.md` D-11, D-12; `interfaces/cli-e-env.md` | `autorizar-caixa` e `testar-caixa` não usam trava, não tocam no registro e não enviam aviso; códigos 0 e 2, e 0, 1 e 2, respectivamente. `verificar-config` segue sem rede. | ausência | `var/registro.sqlite3` ou `var/execucao.lock` criados por esses comandos; requisição de rede no `verificar-config`. |
| W037 | `requirements.md#4` (RN-04); `interfaces/google-oauth.md`, "Segredos em trânsito e em log" | `client_secret`, `code`, `code_verifier`, `refresh_token`, `access_token` e `id_token` nunca aparecem em log, aviso ou terminal; do erro HTTP só vão ao log o estado e o campo `error`. | ausência | `e2e/oauth::test_nenhum_segredo_chega_ao_log` ou `int/servico::test_log_traz_o_estado_e_o_erro_sem_nenhum_segredo` falha; em produção, o `grep` do `onboarding.md` §9 responde "VAZOU". |

Implementados nesta rodada, sem peso de regressão até uma extração os confirmar: RF-01 a RF-12 (código e testes), RF-13 e RF-14 (guia, §16). Premissas ainda abertas, a fechar na T039: P-01 (desafio de identidade no login do operador), P-02 (restrição a aplicativos de terceiros no Workspace), P-03 (IMAP habilitado nas cinco contas), P-04 (nenhum `EMAIL<n>` é apelido) e P-05 (troca de proprietário do projeto por convite).

## Histórico de re-extrações

## Arquivadas
