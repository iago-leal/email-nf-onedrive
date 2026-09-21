# Interface: serviço de autorização do Google (OAuth 2.0)

> Tipo: HTTP sobre TLS · Direção: saída (cliente) e, só no `autorizar-caixa`, entrada local em `127.0.0.1` · Dono no código: `autorizacao/servico.py`, `autorizacao/fluxo.py`
> Requisitos de origem: RF-04 a RF-09; decisões D-02, D-04, D-08, D-09 e D-14 do `roadmap.md`

## Endereços

| Operação | Método e endereço | Quem chama |
|----------|-------------------|------------|
| Consentimento | `GET https://accounts.google.com/o/oauth2/v2/auth` (aberto no navegador pelo operador) | `autorizar-caixa` |
| Troca do código | `POST https://oauth2.googleapis.com/token` | `autorizar-caixa` |
| Renovação | `POST https://oauth2.googleapis.com/token` | `executar`, `testar-caixa` |
| Revogação | `POST https://oauth2.googleapis.com/revoke` | `autorizar-caixa`, só na divergência de conta (RF-06) |

Os endereços são constantes do código, substituíveis apenas por injeção nos testes (D-14). Corpo dos `POST` em `application/x-www-form-urlencoded`; respostas em JSON. Tempo limite de 60 s por requisição; uma tentativa, sem repetição (D-09).

## 1. Consentimento

Parâmetros do endereço impresso pelo `autorizar-caixa`:

| Parâmetro | Valor |
|-----------|-------|
| `client_id` | `OAUTH_CLIENT_ID` |
| `redirect_uri` | `http://127.0.0.1:<porta efêmera>` |
| `response_type` | `code` |
| `scope` | `https://mail.google.com/ openid email` |
| `access_type` | `offline` |
| `prompt` | `consent` |
| `login_hint` | `EMAIL<n>` |
| `state` | 32 bytes aleatórios, base64 URL |
| `code_challenge` | SHA-256 do verificador, base64 URL sem preenchimento |
| `code_challenge_method` | `S256` |

Retorno local: o servidor escuta só em `127.0.0.1`, atende uma requisição e encerra. Espera máxima de 5 min.

| Retorno | Tratamento | Saída |
|---------|------------|-------|
| `?code=...&state=<igual>` | segue para a troca | página "pode fechar esta janela" |
| `?error=access_denied` | nada gravado, código 2 | "caixa n: consentimento negado" |
| `state` divergente ou ausente | nada gravado, código 2 | "caixa n: retorno inválido (state)" |
| nenhum retorno em 5 min | nada gravado, código 2 | "caixa n: tempo esgotado à espera do consentimento" |

A página devolvida ao navegador é estática e não reflete nenhum parâmetro recebido.

## 2. Troca do código

Requisição: `grant_type=authorization_code`, `code`, `client_id`, `client_secret`, `redirect_uri` (o mesmo do consentimento) e `code_verifier`.

Resposta 200: `access_token`, `expires_in`, `refresh_token`, `scope`, `token_type=Bearer`, `id_token`.

| Situação | Tratamento |
|----------|------------|
| `refresh_token` ausente | recusa: "caixa n: o Google não devolveu autorização durável"; código 2 |
| `scope` sem `https://mail.google.com/` (o usuário desmarcou a permissão) | recusa: "caixa n: acesso ao correio não concedido"; código 2 |
| `id_token` sem `email`, ou `email_verified` falso | recusa; código 2 |
| `email` diferente de `EMAIL<n>` | revoga o `refresh_token`, nada grava: "conta autorizada difere de EMAIL<n>"; código 2 (RF-06) |
| tudo certo | grava o arquivo (`data-delta.md` §4): "caixa n: autorizada · <endereço>"; código 0 |

O `id_token` é decodificado sem validar a assinatura, porque chega direto do serviço por TLS (`investigation.md` §6).

## 3. Renovação

Requisição: `grant_type=refresh_token`, `refresh_token`, `client_id`, `client_secret`.

Resposta 200: `access_token`, `expires_in` (cerca de 3600), `scope`, `token_type`. O Google não devolve novo `refresh_token`; o arquivo não é regravado.

| Resposta | Classe | Causa de aviso | Arquivo de autorização |
|----------|--------|----------------|-------------------------|
| 200 | sucesso | nenhuma | intacto |
| 400 `invalid_grant` | permanente: revogada, caducada, senha trocada | `caixa<n>:autorizacao` | intacto |
| 400 ou 401 `invalid_client`, `unauthorized_client` | permanente, global | `oauth:cliente` | intacto |
| 400 com outro `error` | permanente | `caixa<n>:autorizacao`, com o `error` no log | intacto |
| 429, 5xx | transitória | `caixa<n>:autorizacao-servico` | intacto |
| sem resposta em 60 s, falha de DNS, TLS ou conexão | transitória | `caixa<n>:autorizacao-servico` | intacto |
| 200 com JSON inválido ou sem `access_token` | transitória | `caixa<n>:autorizacao-servico` | intacto |

Depois de um `oauth:cliente`, as demais caixas em `oauth` da mesma execução são puladas sem nova requisição, e cada uma conta como falha no resumo.

## 4. Revogação

Requisição: `token=<refresh_token>`. Resposta 200 em caso de sucesso. Falha na revogação não muda o desfecho do `autorizar-caixa` (nada é gravado de qualquer modo); a saída acrescenta "não foi possível revogar; revogue em myaccount.google.com/permissions".

## Idempotência

- Renovação: repetir é seguro; cada resposta traz uma credencial temporária nova e as anteriores seguem válidas até expirar.
- Troca do código: o código vale uma vez; repetir devolve `invalid_grant`. O comando não repete.
- `autorizar-caixa` repetido para a mesma caixa emite nova autorização durável e substitui o arquivo; a anterior segue válida no Google até a revogação ou até o teto de 100 por conta e cliente.

## Segredos em trânsito e em log

`client_secret`, `code`, `code_verifier`, `refresh_token`, `access_token` e `id_token` nunca são registrados. Os três primeiros segredos duráveis e o `access_token` entram em `segredos` assim que conhecidos. Mensagens de erro HTTP registram só o código de estado e o campo `error`; `error_description` passa pelo mascaramento antes de ir ao log.

## Dublê de teste

`ServicoAutorizacaoFalso`: servidor HTTP local em linha de execução própria, com respostas programáveis por `refresh_token` (sucesso, `invalid_grant`, `invalid_client`, 503, atraso acima do tempo limite) e contagem de requisições, para verificar a tentativa única e a ausência de chamadas em instalação sem OAuth.
