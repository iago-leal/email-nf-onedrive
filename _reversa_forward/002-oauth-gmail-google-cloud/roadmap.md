# Roadmap: acesso às caixas do Gmail por OAuth 2.0, com projeto próprio no Google Cloud

> Identificador: `002-oauth-gmail-google-cloud`
> Data: `2026-09-21`
> Requirements: `_reversa_forward/002-oauth-gmail-google-cloud/requirements.md`
> Confidência: 🟢 CONFIRMADO, 🟡 INFERIDO, 🔴 LACUNA
>
> O `requirements.md` chegou a este plano sem marcador `[DÚVIDA]`. As premissas da seção 4 vêm dos pontos 🟡 da seção 10 dos requisitos que a documentação do Google não resolve sozinha: dependem do estado real das contas e dos domínios dos clientes.

## 1. Resumo da abordagem

A feature acrescenta um segundo modo de autenticação por caixa, sem tocar no primeiro. A configuração ganha `AUTH_EMAIL<n>`, as credenciais do cliente OAuth e o diretório de autorizações; a coleta passa a escolher, por caixa, entre o `LOGIN` atual e o mecanismo `XOAUTH2` do IMAP. Um subpacote novo, `autorizacao`, concentra tudo o que fala com o Google: o fluxo de consentimento do comando `autorizar-caixa` (código de autorização com PKCE e retorno por endereço de laço local, o único ainda aceito pelo Google para aplicativo de computador), a troca da autorização durável pela credencial temporária a cada execução e a leitura e gravação do arquivo de autorização. Tudo usa a biblioteca padrão (`urllib`, `http.server`, `secrets`, `hashlib`, `json`), de modo que a única dependência de execução continua sendo `python-dotenv`. A conta que consentiu é conferida pelo `id_token` devolvido na troca do código, o que dispensa chamada extra e atende ao RF-06. Falhas de autorização entram no sistema de avisos existente com causas próprias, separando o que é permanente (refazer a autorização) do que é transitório (serviço do Google fora do ar). Os testes seguem o padrão da feature 001: dublês locais para o serviço de autorização e para o `AUTHENTICATE` do servidor IMAP falso, sem depender do Google.

## 2. Princípios aplicados

Não existe `.reversa/principles.md` neste projeto; não há princípio formal a verificar. Valem como invariantes as regras RN-01 a RN-09 do `requirements.md` e as regras sob vigilância W001 a W021 da feature 001, em especial a W014 (caixa somente leitura).

| Princípio | Como a feature se relaciona | Status |
|-----------|------------------------------|--------|
| n/a | Nenhum princípio registrado. A recomendação do roadmap da feature 001 permanece: rodar `/reversa-principles` e promover a caixa intocada e a pasta só de acréscimos a princípios. Esta feature reforça o caso, porque o escopo concedido passa a ser maior do que o uso (RN-03). | n/a |

## 3. Decisões técnicas

| ID | Decisão | Justificativa | Alternativas descartadas | Confidência |
|----|---------|----------------|--------------------------|-------------|
| D-01 | OAuth implementado com a biblioteca padrão: `urllib.request` para o serviço de autorização, `http.server` para o retorno local, `secrets` e `hashlib` para PKCE e `state`. Nenhuma dependência nova. | Mantém a decisão D-01 e o resumo da feature 001 (só `python-dotenv`); são três chamadas HTTP de formulário, o que não justifica `google-auth` e `google-auth-oauthlib`, com suas dependências transitivas. | `google-auth-oauthlib` (três pacotes a mais para instalar na VPS); `requests-oauthlib`. | 🟢 |
| D-02 | Cliente OAuth do tipo "aplicativo para computador" no Google Cloud. Fluxo de código de autorização com PKCE (`S256`), `redirect_uri` em `http://127.0.0.1:<porta efêmera>`, `access_type=offline`, `prompt=consent`, `login_hint=<EMAIL<n>>` e `state` aleatório conferido no retorno. | É o fluxo que o Google documenta para aplicativos instalados; o fluxo de copiar e colar o código (OOB) foi descontinuado. `prompt=consent` garante a emissão de autorização durável mesmo numa reautorização. | Fluxo de dispositivo (não aceita o escopo do Gmail); OOB (descontinuado); cliente do tipo "aplicativo da Web" (exigiria endereço público de retorno). | 🟢 |
| D-03 | `autorizar-caixa` **imprime** o endereço de autorização e espera o retorno por até 5 min; não abre o navegador por conta própria. O guia manda colar o endereço numa janela anônima. | Pela RN-09, o operador entra na conta do cliente. O navegador padrão do operador está com a conta dele, e abrir ali induziria o consentimento com a conta errada. O endereço não contém segredo (só o identificador do cliente, o desafio PKCE e o `state`). | `webbrowser.open` automático; opção `--abrir` (superfície a mais sem ganho). | 🟢 |
| D-04 | Escopos pedidos: `https://mail.google.com/`, `openid` e `email`. A conta que consentiu é lida da declaração `email` do `id_token` devolvido na troca do código e comparada, sem diferenciar maiúsculas, com `EMAIL<n>`. Em divergência, a autorização recém-emitida é revogada no serviço do Google, nada é gravado e a saída diz "conta autorizada difere de EMAIL<n>". | Atende ao RF-06 sem chamada extra. O `id_token` chega direto do serviço de autorização por TLS, caso em que o Google dispensa a validação da assinatura. `openid` e `email` são escopos não sensíveis e não mudam a tela de consentimento de forma relevante. Revogar evita deixar uma concessão órfã na conta errada. | Tentar o `XOAUTH2` com `EMAIL<n>` e inferir a divergência pela recusa (não distingue conta errada de IMAP desativado); chamar a API de perfil do Gmail (mais uma requisição e mais um ponto de falha). | 🟡 |
| D-05 | Arquivo de autorização em JSON, um por caixa, em `<DIR_AUTORIZACOES>/<endereço em minúsculas>.json`, com `versao`, `endereco`, `client_id`, `refresh_token`, `escopos` e `autorizada_em`. Diretório com permissão 700, arquivo criado já com 600 (`os.open` com modo explícito) e trocado de forma atômica (`os.replace`). `DIR_AUTORIZACOES` relativo é resolvido a partir do diretório de instalação. | Nome pelo endereço, coerente com a RN-07 e com a chave do registro; renumerar o `.env` não desvincula a autorização. `client_id` no arquivo permite dizer "autorização emitida para outro cliente OAuth" em vez de um erro opaco do Google. Nada no arquivo depende da máquina, o que atende ao RF-05. | Guardar no SQLite (dificulta a cópia para a VPS e mistura segredo com registro); guardar no `.env` (arquivo editado à mão; regravá-lo por programa é arriscado). | 🟢 |
| D-06 | A credencial temporária é obtida uma vez por caixa e por execução, no momento de conectar, vive só em memória e é registrada em `segredos` para mascaramento, assim como `OAUTH_CLIENT_SECRET` e a autorização durável lida do arquivo. | RNF de segurança (segredo em repouso só o durável) e RN-04. Com ciclos de 30 min e validade de cerca de 1 h, guardar a credencial entre execuções pouparia uma requisição a cada dois ciclos, ao custo de mais um segredo em disco. | Cache da credencial temporária em `var/`. | 🟢 |
| D-07 | `ClienteIMAP` ganha o método `conectar_oauth(usuario, credencial)`, ao lado do `conectar(usuario, senha)` atual, que não muda. O método novo emite `AUTHENTICATE XOAUTH2` por `imaplib.IMAP4.authenticate`, com a resposta inicial `user=<endereço>^Aauth=Bearer <credencial>^A^A`. Na recusa, o servidor devolve um desafio com o erro em JSON; o cliente responde com linha vazia, como o protocolo exige, e registra o motivo no log. | Mantém a fachada restrita da D-05 da feature 001: o conjunto de comandos permitidos ganha só `AUTHENTICATE`. `imaplib` faz a codificação em base64; a função de resposta devolve a cadeia na primeira chamada e vazio na segunda. | Trocar a assinatura de `conectar` por um objeto de credencial (mexe num contrato que hoje funciona, sem ganho); subclasse de `ClienteIMAP` por modo (duplica a fachada); biblioteca IMAP de terceiros. | 🟢 |
| D-08 | Classificação das falhas de autorização em três causas de aviso. `caixa<n>:autorizacao` (permanente): arquivo ausente, ilegível, de outro endereço ou de outro cliente, resposta `invalid_grant` do serviço, ou `AUTHENTICATE` recusado. `caixa<n>:autorizacao-servico` (transitória): sem resposta em 60 s, erro de rede, HTTP 5xx ou 429. `oauth:cliente` (global às caixas em `oauth`): resposta `invalid_client` ou `unauthorized_client`, que indica credenciais do cliente erradas no `.env`. O arquivo de autorização nunca é apagado nem alterado pelo ciclo. | RF-08 pede causa distinta da senha recusada; RF-09 pede que a falha transitória não descarte a autorização. Separar `oauth:cliente` evita cinco avisos iguais quando o erro é um só. As chaves entram na supressão de 6 h e no aviso de recuperação existentes, sem mudança no gerenciador. | Reusar `caixa<n>:autenticacao` com outra mensagem (o operador não saberia se refaz a autorização ou corrige a senha); apagar o arquivo em `invalid_grant` (perde a evidência e contraria o espírito do RF-09). | 🟢 |
| D-09 | Uma única tentativa de obter a credencial temporária por caixa e por execução, com tempo limite de 60 s; sem repetição dentro do ciclo. | A execução seguinte, 30 min depois, é a repetição. Cinco caixas no pior caso somam 5 min, dentro do limite de 20 min da D-14 da feature 001. | Repetição com espera exponencial (arrisca estourar o limite da execução). | 🟢 |
| D-10 | Validação da configuração continua toda anterior à rede. `AUTH_EMAIL<n>` aceita `senha` e `oauth` sem diferenciar maiúsculas; ausente vale `senha`. Em `oauth`, `SENHA_EMAIL<n>` é opcional e, se presente, é ignorada com o alerta "SENHA_EMAIL<n> presente em caixa oauth; retire-a do .env" (RN-09). A existência e a permissão do arquivo de autorização são verificadas por `stat`, sem abrir a rede, e alimentam o `verificar-config` (RF-10) e o alerta de permissão (RF-12). | Preserva o RF-08 da spec `configuracao-caixas`. O alerta transforma a orientação da RN-09 em algo que a ferramenta cobra. Caixa em `oauth` sem arquivo é **válida** na configuração e falha só na coleta, como pede o cenário "caixa em oauth dispensa a senha". | Tornar inválida a caixa sem autorização (contraria o cenário e impediria o `autorizar-caixa` de carregar a configuração). | 🟢 |
| D-11 | Comando `testar-caixa [<n>]`: conecta, abre a pasta com `EXAMINE` e encerra, uma tentativa por caixa, sem trava, sem aviso e sem tocar no registro. Código 0 se todas passarem, 1 se alguma falhar, 2 em erro de configuração, índice inexistente ou nenhuma caixa válida. | RF-11. Reusa a fábrica IMAP e o provedor de credencial do ciclo, de modo que o teste exercita o mesmo caminho da produção. | Reusar `executar --simular` (lê mensagens e demora; não serve a um teste rápido de acesso). | 🟢 |
| D-12 | Comando `autorizar-caixa <n>`: exige a caixa válida e em modo `oauth`; código 0 quando grava, 2 em qualquer recusa (caixa inexistente ou em modo `senha`, credenciais do cliente ausentes, consentimento negado, tempo esgotado, conta divergente, resposta sem autorização durável). Não usa trava nem registro e não envia aviso. | RF-04 a RF-06. Rodar na máquina do operador com o mesmo `.env` da VPS mantém um só contrato de configuração. | Arquivo de configuração separado para a máquina do operador. | 🟢 |
| D-13 | Observabilidade: a linha de conexão passa a ser "caixa n: conectada (senha)" ou "caixa n: conectada (oauth)"; o resumo da execução ganha o segmento "`k` de autorização" depois de "`f` falhas", presente só quando `k` > 0. | RNF de observabilidade. O segmento condicional mantém inalterada a linha de resumo das instalações sem OAuth. Conferido em 2026-09-21: nenhum teste depende do texto emitido pela coleta (`tests/unidade/test_logs.py` escreve a própria linha), de modo que o sufixo em ambos os modos não altera expectativa; ver R-07. | Contador separado sempre presente (mudaria a linha de todos os ciclos). | 🟡 |
| D-14 | Os endereços do serviço de autorização do Google são constantes do código, substituíveis só por injeção em `ciclo.Dependencias`, nunca pelo `.env`. | Os testes precisam apontar para o dublê local; uma variável de ambiente que redirecionasse o envio do segredo do cliente seria um vetor de vazamento. | Variável `OAUTH_TOKEN_URL` no `.env`. | 🟢 |
| D-15 | Testes: unidade para a leitura de `AUTH_EMAIL<n>`, o arquivo de autorização, PKCE, a montagem do endereço, a leitura do `id_token` e a classificação de erros; integração com um servidor HTTP local em linha de execução própria, que faz o papel do serviço de autorização, e com o `ServidorIMAPFalso` estendido com `authenticate`. O consentimento real é roteiro manual no `onboarding.md`. | RNF de testabilidade e padrão de `tests/RASTREABILIDADE.md`. | Gravar respostas reais do Google (levaria segredo para o repositório). | 🟢 |
| D-16 | Projeto no Google Cloud sem conta de faturamento, na conta pessoal do operador, com público externo e estado "em produção", sem pedir a verificação do aplicativo. O guia documenta a tela "o Google não verificou este app" e o caminho "Avançado". | RN-05, RN-08 e sessão de esclarecimentos (2a). A documentação do Google confirma: em modo de teste a autorização caduca em 7 dias; em produção sem verificação há o aviso e o teto de 100 usuários novos, folgado para cinco contas. | Modo de teste (vedado pela RN-05); verificação do aplicativo (auditoria paga para escopo restrito, fere a RN-08). | 🟢 |
| D-17 | Transferência de posse na entrega: o guia manda acrescentar a conta do cliente como proprietária do projeto no IAM e, depois do aceite, retirar a do operador; o identificador e o segredo do cliente OAuth não mudam, e as autorizações seguem válidas. | Sessão de esclarecimentos (2a). Evita reautorizar as cinco caixas na entrega. | Criar projeto novo na conta do cliente (obriga a reautorizar tudo). | 🟡 |

## 4. Premissas

Nenhuma premissa deriva de `[DÚVIDA]` aberta. As abaixo são fatos do ambiente dos clientes que só o roteiro manual revela.

| Premissa | Origem (`requirements.md` seção) | Risco se errada |
|----------|----------------------------------|-----------------|
| P-01: o Google não exige desafio de identidade (SMS, aparelho confiável) quando o operador entra nas contas a partir da sua máquina. | §10, pontos 🟡; RN-09 | Médio: a caixa afetada precisa da presença do titular no momento da autorização. O código não muda; o guia traz a alternativa (autorizar em chamada com o titular). |
| P-02: nos três domínios do Workspace, o acesso de aplicativos de terceiros não está restrito, ou o administrador aceita marcar o cliente OAuth como confiável. | §10, pontos 🟡 | Alto para aquele domínio: o consentimento é bloqueado com "acesso bloqueado pelo administrador". Mitigação fora do código: o guia traz o passo do console de administração; em último caso, a caixa fica em `senha` com senha de app. |
| P-03: o IMAP está habilitado nas cinco contas. | §10, pontos 🟡 | Médio: `AUTHENTICATE` recusado mesmo com autorização válida. O `testar-caixa` revela antes do agendamento. |
| P-04: nenhum dos `EMAIL<n>` é apelido; todos são o endereço principal da conta. | RF-06 | Baixo: o `id_token` traz o endereço principal, e a comparação recusaria um apelido. Correção no `.env`. |
| P-05: um projeto sem organização aceita a troca de proprietário por convite no IAM. | §10, pontos 🟡; D-17 | Baixo: na pior hipótese, a entrega exige projeto novo e nova autorização das cinco caixas, procedimento já coberto pelo guia. |

## 5. Delta arquitetural

Não existe `_reversa_sdd/architecture.md`; a referência são as specs em `_reversa_sdd/sdd/`, lidas com o adendo `_reversa_sdd/addenda/001-mvp-email-nf-onedrive.md`.

| Componente | Arquivo de origem no legado | Tipo de mudança | Resumo |
|------------|------------------------------|-----------------|--------|
| `configuracao/modelo.py` | `_reversa_sdd/sdd/configuracao-caixas.md#9. Modelo de Dados` | regra-alterada | `Caixa` ganha `modo`; `Configuracao` ganha o cliente OAuth e o diretório de autorizações. |
| `configuracao/carregar.py` | `_reversa_sdd/sdd/configuracao-caixas.md#6. Requisitos Funcionais` (RF-02, RF-08, RF-11) | regra-alterada | Lê `AUTH_EMAIL<n>`, `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` e `DIR_AUTORIZACOES`; senha exigida só em modo `senha`; novos alertas (D-10). |
| `autorizacao/` (subpacote novo: `arquivo.py`, `servico.py`, `fluxo.py`, `credencial.py`) | n/a | componente-novo | Arquivo de autorização, chamadas ao serviço do Google, fluxo de consentimento e provedor de credencial por caixa. |
| `coleta/imap.py` | `_reversa_sdd/sdd/coleta-email.md#6. Requisitos Funcionais` (RF-01, RF-02) | contrato-alterado | Método novo `conectar_oauth`; `AUTHENTICATE XOAUTH2` entra na lista de comandos permitidos (D-07). |
| `coleta/coleta.py` | `_reversa_sdd/sdd/coleta-email.md#11. Edge Cases e Tratamento de Erros` (EC-01) | regra-alterada | Obtém a credencial antes de conectar; mensagens e causas de falha por modo (D-08); log "conectada (modo)". |
| `execucao/ciclo.py` | `_reversa_sdd/sdd/execucao-monitoramento.md#6. Requisitos Funcionais` | regra-alterada | `Dependencias` ganha o serviço de autorização injetável (D-14); conta as falhas de autorização para o resumo. |
| `execucao/resumo.py` | `_reversa_sdd/sdd/execucao-monitoramento.md#9. Modelo de Dados` | regra-alterada | Campo `falhas_autorizacao` e segmento condicional na linha de resumo (D-13). |
| `cli.py` | `_reversa_sdd/sdd/execucao-monitoramento.md#6. Requisitos Funcionais` | contrato-alterado | Subcomandos `autorizar-caixa <n>` e `testar-caixa [<n>]`; `verificar-config` mostra o modo e o estado da autorização (RF-10). |
| `tests/integracao/dubles.py` | n/a | componente-novo | `ConexaoFalsa.authenticate` e `ServicoAutorizacaoFalso` (servidor HTTP local). |
| `docs/instalacao-e-operacao.md`, `README.md`, `.env.example`, `.gitignore`, `tests/RASTREABILIDADE.md` | `_reversa_sdd/sdd/execucao-monitoramento.md#6. Requisitos Funcionais` (RF-12, RF-13) | regra-alterada | Seção nova do guia (RF-13, RF-14), variáveis novas, `autorizacoes/` fora do versionamento, mapa de rastreabilidade. |

Os módulos `envio/`, `registro/`, `execucao/avisos.py`, `execucao/trava.py` e `execucao/telegram.py` não mudam.

## 6. Delta no modelo de dados

- Resumo das mudanças: nenhuma alteração no SQLite. `Caixa` ganha o campo `modo`; surgem a entidade em memória `ClienteOAuth` e a entidade em arquivo `Autorizacao` (um JSON por caixa). Não há migração: instalações existentes seguem válidas sem edição (RN-01, RN-07).
- Detalhe completo em: `_reversa_forward/002-oauth-gmail-google-cloud/data-delta.md`

## 7. Delta de contratos externos

| Contrato | Tipo | Arquivo de detalhe |
|----------|------|--------------------|
| Serviço de autorização do Google (consentimento, troca de código, renovação, revogação) | HTTP | `_reversa_forward/002-oauth-gmail-google-cloud/interfaces/google-oauth.md` |
| IMAP do Gmail: autenticação `XOAUTH2` (delta sobre `001/interfaces/imap-gmail.md`) | protocolo IMAP | `_reversa_forward/002-oauth-gmail-google-cloud/interfaces/imap-gmail-xoauth2.md` |
| Linha de comando e `.env` (delta sobre `001/interfaces/cli-e-env.md`) | CLI e arquivo | `_reversa_forward/002-oauth-gmail-google-cloud/interfaces/cli-e-env.md` |

## 8. Plano de migração

Não há dado a migrar. A passagem de uma instalação para OAuth é operacional e reversível, caixa a caixa:

1. Atualizar o pacote na máquina do operador e na VPS; rodar `verificar-config` e confirmar que nada mudou (todas as caixas em `senha`).
2. Criar o projeto no Google Cloud e preencher `OAUTH_CLIENT_ID` e `OAUTH_CLIENT_SECRET` nos dois `.env`.
3. Para cada caixa: enviar o comunicado ao titular (RF-14), definir `AUTH_EMAIL<n>=oauth`, rodar `autorizar-caixa <n>` na máquina do operador e `testar-caixa <n>`.
4. Copiar o diretório de autorizações para a VPS, conferir a permissão e rodar `testar-caixa` lá.
5. Retirar `SENHA_EMAIL<n>` das caixas autorizadas, nos dois `.env` (RN-09), e rodar `executar --simular` antes de religar o `cron`.

Para voltar atrás, basta remover `AUTH_EMAIL<n>` e repor a senha; o registro de processados não é afetado (RN-07).

## 9. Riscos e mitigações

| ID | Risco | Impacto | Probabilidade | Mitigação |
|----|-------|---------|---------------|-----------|
| R-01 | O titular troca a senha da conta: o Google invalida autorizações que contêm escopo do Gmail. | médio | médio | Aviso `caixa<n>:autorizacao` com a ação "rode autorizar-caixa n"; o comunicado ao titular (RF-14) avisa que a troca de senha exige nova autorização. Pela RN-09, a nova senha teria de chegar ao operador, ou o titular participa da reautorização. |
| R-02 | Administrador do Workspace restringe aplicativos de terceiros (P-02). | alto | médio | Passo do console de administração no guia; senha de app como alternativa por caixa, já que os modos convivem (RN-01). |
| R-03 | Desafio de identidade no login pelo operador (P-01). | médio | médio | Alternativa no guia: autorização em chamada com o titular. |
| R-04 | O escopo concedido permite mais do que ler (RN-03): um defeito futuro poderia alterar a caixa. | alto | baixo | Fachada IMAP com lista fechada de comandos e o teste que a vigia (W014); `AUTHENTICATE` é o único acréscimo. A credencial só é usada no IMAP, nunca na API do Gmail. |
| R-05 | Vazamento do diretório de autorizações ou do `.env` da VPS dá acesso total às cinco caixas até a revogação. | alto | baixo | Permissão 600 e 700, alerta do RF-12, mascaramento em log, procedimento de revogação no guia (conta do titular e, para o cliente inteiro, troca do segredo no Google Cloud). |
| R-06 | O Google passa a exigir verificação para aplicativos em produção com escopo restrito, ou reduz o teto de usuários. | alto | baixo | Fora do controle do projeto; o modo `senha` permanece (Won't "remoção do modo senha"), e a leitura pela API com escopo de leitura está registrada como evolução. |
| R-07 | A linha "conectada" vira "conectada (senha)" e quebra expectativa de algum dos 236 testes, contrariando o RNF de compatibilidade ("sem alteração de expectativa"). | baixo | baixo | Verificado no planejamento: só `coleta/coleta.py` emite a linha e nenhum teste a confere. Se a implementação encontrar dependência não vista, o recuo é manter "conectada" no modo `senha` e usar o sufixo só em `oauth`, o que ainda satisfaz o RF-07. |
| R-08 | Porta local ocupada ou bloqueada por firewall durante o `autorizar-caixa`. | baixo | baixo | Porta efêmera escolhida pelo sistema; mensagem clara e código 2. |

## 10. Critério de pronto

- [ ] Todas as ações do `actions.md` marcadas `[X]`
- [ ] `cross-check.md` (se executado) sem CRITICAL nem HIGH
- [x] `regression-watch.md` gerado (W022 a W037, 2026-09-21)
- [ ] Re-extração reversa executada e sem regressão vermelha (recomendado, não obrigatório)
- [x] `pytest` verde: os 236 testes atuais sem alteração de expectativa e os novos (361 no total em 2026-09-21; a única expectativa antiga alterada foi `COMANDOS_PERMITIDOS`, prevista na T012)
- [x] Os 16 cenários Gherkin do `requirements.md` §7 com teste automatizado ou, quando dependem do Google real (autorização, renovação após 1 h, revogação pelo titular), com roteiro manual no `onboarding.md`
- [x] O teste que vigia os comandos IMAP aceita `AUTHENTICATE` e nenhum outro comando novo
- [ ] Ao menos uma caixa real autorizada e lida pela VPS, com `grep` do segredo do cliente, da autorização durável e da credencial temporária nos logs sem ocorrência
- [ ] Guia lido por terceiro, que cria o projeto e autoriza uma caixa só com ele (RF-13)

## 11. Histórico de alterações

| Data | Alteração | Autor |
|------|-----------|-------|
| 2026-09-21 | Versão inicial gerada por `/reversa-plan` | reversa |
| 2026-09-21 | Critério de pronto (seção 10): quatro de nove itens marcados após o `/reversa-coding`; os demais dependem da T039, do `/reversa-audit` e da re-extração | reversa |
