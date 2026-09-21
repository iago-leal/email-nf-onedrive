# Investigation: acesso às caixas do Gmail por OAuth 2.0

> Identificador: `002-oauth-gmail-google-cloud`
> Data: `2026-09-21`
> Complementa: `roadmap.md` (decisões D-01 a D-17)
> Fontes consultadas em 2026-09-21; cada afirmação abaixo indica se foi conferida na documentação oficial (🟢) ou se vem de conhecimento geral (🟡).

## 1. Pontos 🟡 dos requisitos, conferidos

| Ponto (`requirements.md` §10) | Resultado | Confidência |
|-------------------------------|-----------|-------------|
| Escopo exigido para IMAP com OAuth | "The scope for IMAP, POP, and SMTP access is `https://mail.google.com/`." Não existe escopo de leitura para IMAP; o escopo `gmail.readonly` vale só para a API do Gmail. Confirma a RN-03. | 🟢 |
| Validade de 7 dias em modo de teste | "Authorizations by a test user will expire seven days from the time of consent." Confirma a RN-05: o estado tem de ser "em produção". | 🟢 |
| Teto de 100 contas para aplicativo não verificado | "100 new users in total, after the app presents the unverified app screen." Cinco contas cabem com folga. O modo de teste tem teto próprio, também de 100 usuários de teste, irrelevante aqui. | 🟢 |
| Aviso de aplicativo não verificado | Aparece sempre que o cliente pede escopo sensível ou restrito sem verificação; o escopo do Gmail é restrito. O consentimento segue pelo caminho "Avançado". | 🟢 |
| Restrição de aplicativos de terceiros pelo administrador do Workspace | O console de administração (Segurança › Controles de API › Acesso de apps) permite bloquear aplicativos não configurados e marcar um identificador de cliente como confiável. Se estiver restrito, o consentimento é bloqueado antes da tela de aceite. Depende do estado real de cada domínio: premissa P-02. | 🟡 |
| IMAP habilitado nos três domínios | O administrador do Workspace pode desativar o IMAP para a organização. Só o `testar-caixa` responde: premissa P-03. | 🟡 |
| Desafio de identidade no login pelo operador | O Google decide por risco (aparelho, local, histórico) e não documenta a regra. Premissa P-01. | 🟡 |
| Transferência de posse de projeto sem organização | O IAM aceita acrescentar outro proprietário por convite; migrar o projeto para dentro de uma organização é operação distinta e não é necessária. Premissa P-05. | 🟡 |

## 2. Por que a autorização pode deixar de valer

A documentação do Google lista os motivos pelos quais a autorização durável (`refresh_token`) para de funcionar. Cada um se traduz, na ferramenta, na causa `caixa<n>:autorizacao` (D-08):

| Motivo documentado | Relevância para o projeto |
|--------------------|---------------------------|
| O usuário revogou o acesso | Cenário Gherkin "autorização revogada pelo titular". |
| Seis meses sem uso | Irrelevante: a ferramenta usa a autorização a cada 30 min. |
| **O usuário trocou a senha e a autorização contém escopo do Gmail** | Relevante e pouco intuitivo: risco R-01. Entra no comunicado ao titular (RF-14). |
| Excesso de autorizações vivas: 100 por conta e por cliente OAuth | Cada `autorizar-caixa` emite uma nova; a mais antiga é descartada ao passar de 100. Inalcançável no uso previsto. |
| Acesso por tempo limitado concedido pelo usuário | Não se aplica ao fluxo escolhido. |
| Administrador restringiu o serviço pedido nos escopos | Variante tardia da premissa P-02. |
| Controle de duração de sessão do Google Cloud | Aplica-se a escopos do Google Cloud, não ao do Gmail. |
| Projeto em modo de teste | Vedado pela RN-05 e pela D-16. |

Todos chegam como HTTP 400 com `error=invalid_grant` na renovação, sem distinção do motivo. Por isso a mensagem de aviso enumera as causas prováveis (revogação ou troca de senha) e dá uma única ação: refazer `autorizar-caixa <n>`.

## 3. Fluxo de autorização: alternativas

| Critério | Código com PKCE e retorno local (escolhido) | Copiar e colar (OOB) | Fluxo de dispositivo | Conta de serviço com delegação |
|----------|---------------------------------------------|----------------------|----------------------|--------------------------------|
| Estado no Google | Recomendado para aplicativo de computador | Descontinuado | Ativo | Ativo |
| Aceita `https://mail.google.com/` | Sim | n/a | Não: a lista de escopos do fluxo de dispositivo é restrita | Sim |
| Alcança a conta `@gmail.com` | Sim | n/a | n/a | Não |
| Exige administrador do domínio | Só se houver restrição (P-02) | n/a | n/a | Sempre, nos três domínios |
| Funciona sem navegador na VPS | Sim: roda na máquina do operador e o arquivo é copiado (RF-05) | n/a | Sim | Sim |

A delegação em todo o domínio ficou como Won't na sessão de esclarecimentos. O retorno local usa `http://127.0.0.1:<porta>`; o Google aceita qualquer porta para clientes do tipo "aplicativo para computador", sem cadastro prévio do endereço.

Parâmetros relevantes do pedido de autorização: `access_type=offline` (sem ele não vem autorização durável), `prompt=consent` (sem ele, uma segunda autorização da mesma conta pode vir sem `refresh_token`), `login_hint` (preenche a conta esperada e reduz o erro do RF-06), `code_challenge` com `code_challenge_method=S256` e `state`.

O segredo do cliente, em aplicativo de computador, não é tratado pelo Google como confidencial no sentido estrito, mas o serviço o exige na troca e na renovação. A ferramenta o trata como segredo de qualquer modo (RN-04).

## 4. Biblioteca padrão ou biblioteca do Google

| Critério | Biblioteca padrão (escolhida) | `google-auth` + `google-auth-oauthlib` |
|----------|-------------------------------|-----------------------------------------|
| Dependências novas | nenhuma | `google-auth`, `google-auth-oauthlib`, `requests-oauthlib`, `requests`, `oauthlib`, `cachetools`, `pyasn1-modules`, `rsa` |
| Código próprio | cerca de 200 linhas: três requisições de formulário, um servidor de retorno, PKCE | cerca de 40 linhas |
| Controle sobre log e mascaramento | total | as bibliotecas registram em `logging` próprio; exigiria conferir que nada ecoa credencial |
| Testabilidade com dublê local | endereços injetáveis (D-14) | exige *monkeypatch* de endereços internos |

O critério decisivo é a instalação por terceiro numa VPS pequena, objetivo da persona operador-tecnico, e a regra de não registrar segredo, mais fácil de garantir em código próprio e curto.

## 5. `XOAUTH2` com `imaplib`

`imaplib.IMAP4.authenticate(mecanismo, funcao)` chama `funcao(desafio)` e codifica o retorno em base64. Para `XOAUTH2`:

- primeira chamada, desafio vazio: devolver `user=<endereço>\x01auth=Bearer <credencial>\x01\x01` em bytes;
- se o servidor recusar, ele envia um segundo desafio com um JSON (`status`, `schemes`, `scope`), e o cliente tem de responder com linha vazia para receber o `NO` final. A função devolve `b""` na segunda chamada; devolver `None` enviaria `*`, que cancela a autenticação e também encerra de forma correta, mas perde o JSON de diagnóstico.

O JSON do desafio não contém segredo e vai para o log, truncado, depois de passar pelo mascaramento. Falha de `authenticate` levanta `imaplib.IMAP4.error`, já convertido em `ErroIMAP` por `ClienteIMAP._chamar`; basta uma causa nova.

Capacidade anunciada: o Gmail lista `AUTH=XOAUTH2` no `CAPABILITY`. A ferramenta não consulta a capacidade antes: a recusa do `AUTHENTICATE` já é tratada, e o `IMAP_HOST_EMAIL<n>` de outro provedor em modo `oauth` não é caso de uso desta feature.

## 6. Conferência da conta pelo `id_token`

Com `openid email` entre os escopos, a resposta da troca do código traz `id_token`, um JWT cujo corpo contém `email` e `email_verified`. A orientação do Google é validar a assinatura quando o token chega por um intermediário; quando vem direto do serviço de autorização, por TLS, a validação é dispensável. A ferramenta decodifica só o corpo (base64 URL, JSON), sem biblioteca de JWT. Se `email` faltar, a autorização é recusada do mesmo modo que na divergência, com mensagem própria.

## 7. Privacidade e LGPD

O escopo concedido (acesso total ao correio) excede o uso (leitura de anexos), e o consentimento é dado pelo operador em nome do titular (RN-09). As salvaguardas do plano, à luz dos princípios da necessidade e da transparência (LGPD, art. 6º, III e VI):

- uso efetivo restrito por construção: lista fechada de comandos IMAP, vigiada por teste (W014);
- a credencial só é apresentada ao servidor IMAP, nunca à API do Gmail;
- comunicado prévio ao titular com o alcance real da concessão e o caminho de revogação (RF-14);
- retirada da senha de terceiro do `.env` depois da autorização, cobrada por alerta (D-10);
- segredo em repouso limitado à autorização durável, em arquivo 600 (D-05, D-06).

A evolução registrada como Won't (leitura pela API do Gmail com `gmail.readonly`) é o caminho para alinhar o escopo concedido ao uso.

## 8. Fontes

- OAuth 2.0 no Google, validade das autorizações: https://developers.google.com/identity/protocols/oauth2
- OAuth 2.0 para aplicativos instalados (retorno local, PKCE, endereços dos serviços, revogação): https://developers.google.com/identity/protocols/oauth2/native-app
- Mecanismo `XOAUTH2` do Gmail: https://developers.google.com/workspace/gmail/imap/xoauth2-protocol
- Público do aplicativo, estados de publicação e tetos: https://support.google.com/cloud/answer/15549945
- OpenID Connect no Google (`id_token`, quando validar): https://developers.google.com/identity/openid-connect/openid-connect
- Controle de acesso de aplicativos no Workspace: https://support.google.com/a/answer/7281227
- `imaplib.IMAP4.authenticate`: https://docs.python.org/3/library/imaplib.html#imaplib.IMAP4.authenticate
- RFC 7636, PKCE: https://datatracker.ietf.org/doc/html/rfc7636
- RFC 8252, OAuth 2.0 para aplicativos nativos: https://datatracker.ietf.org/doc/html/rfc8252
