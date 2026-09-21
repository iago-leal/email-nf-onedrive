# Interface: IMAP do Gmail, autenticação `XOAUTH2`

> Tipo: protocolo IMAP4rev1 sobre TLS · Direção: saída (cliente) · Dono no código: `coleta/imap.py`
> Delta sobre: `_reversa_forward/001-mvp-email-nf-onedrive/interfaces/imap-gmail.md`. Tudo o que não aparece aqui continua como lá.

## Conexão

| Item | Modo `senha` (sem alteração) | Modo `oauth` (novo) |
|------|------------------------------|----------------------|
| Servidor, porta, TLS, tempo limite | como hoje | iguais |
| Autenticação | `LOGIN <EMAIL<n>> <SENHA_EMAIL<n>>` | `AUTHENTICATE XOAUTH2 <resposta inicial>` |

Resposta inicial, antes da codificação em base64 feita pelo `imaplib` (`^A` é o byte `0x01`):

```
user=<EMAIL<n>>^Aauth=Bearer <credencial temporária>^A^A
```

## Sequência de comandos

A lista fechada da feature 001 ganha uma alternativa no primeiro passo e nada mais:

| # | Comando | Observação |
|---|---------|------------|
| 1 | `LOGIN` **ou** `AUTHENTICATE XOAUTH2` | conforme o modo da caixa; nunca os dois na mesma conexão |
| 2 a 6 | `LIST`, `EXAMINE`, `SEARCH SINCE`, `FETCH (BODY.PEEK[])`, `LOGOUT` | sem alteração; as proibições permanecem (`SELECT`, `STORE`, `COPY`, `MOVE`, `EXPUNGE`, `BODY[]`, `RFC822`) |

O teste que verifica os comandos emitidos passa a aceitar `AUTHENTICATE` e continua reprovando qualquer outro comando novo (regra W014).

## Respostas e erros

| Situação | Sinal do servidor | Tratamento | Causa de aviso |
|----------|-------------------|------------|----------------|
| Credencial aceita | `OK` | log "caixa n: conectada (oauth)" | nenhuma |
| Credencial recusada | desafio `+ <base64 de JSON com status, schemes, scope>`; o cliente responde com linha vazia e recebe `NO` | caixa pulada; o JSON decodificado vai ao log, mascarado e truncado em 200 caracteres | `caixa<n>:autorizacao` |
| IMAP desativado na conta ou no domínio | `NO` no `AUTHENTICATE`, com texto sobre IMAP | caixa pulada; a mensagem cita o console de administração, como no modo `senha` | `caixa<n>:autorizacao` |
| Sem rede ou tempo esgotado | exceção de socket | como hoje | `caixa<n>:conexao` |

Mensagem de aviso para `caixa<n>:autorizacao` vinda do IMAP: "caixa n: autorização OAuth recusada pelo servidor de e-mail. Ação: rode autorizar-caixa n e confira se o IMAP está ativo na conta."

Uma credencial temporária recém-emitida e recusada pelo IMAP quase sempre indica IMAP desativado ou endereço divergente, e não autorização caducada (essa falha antes, na renovação). Por isso a ação sugerida traz as duas hipóteses.

## Idempotência

Sem alteração: leitura pura.

## Dublê de teste

`ConexaoFalsa` ganha `authenticate(mecanismo, funcao)`: chama `funcao(b"")`, confere `user=` e a credencial contra as cadastradas em `ServidorIMAPFalso.adicionar_caixa_oauth(endereco, credencial)`; na recusa, chama `funcao(<desafio>)` de novo e exige retorno vazio antes de levantar `imaplib.IMAP4.error`. O comando é registrado em `nomes_de_comandos()` como `AUTHENTICATE`.
