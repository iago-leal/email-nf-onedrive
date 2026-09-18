# Interface: IMAP do Google Workspace

> Tipo: protocolo IMAP4rev1 sobre TLS · Direção: saída (cliente) · Dono no código: `coleta/imap.py`
> Spec de origem: `_reversa_sdd/sdd/coleta-email.md`

## Conexão

| Item | Valor |
|------|-------|
| Servidor | `IMAP_HOST_EMAIL<n>`, padrão `imap.gmail.com` |
| Porta | 993, TLS implícito; conexão em texto claro proibida (CE RNF-03) |
| Autenticação | `LOGIN <EMAIL<n>> <SENHA_EMAIL<n>>` com senha de app |
| Timeout | 60 s por operação (CE RNF-04) |

## Sequência de comandos (única permitida)

| # | Comando | Finalidade | Proibições |
|---|---------|------------|------------|
| 1 | `LOGIN` | Autenticar | |
| 2 | `LIST "" "*"` | Só em caso de pasta inexistente, para listar as pastas no log (CE EC-02) | |
| 3 | `EXAMINE "<pasta em UTF-7 modificado>"` | Abrir em somente leitura | `SELECT` proibido |
| 4 | `SEARCH SINCE <dd-Mon-aaaa>` | Mensagens da janela (CE RF-03) | |
| 5 | `FETCH <seq> (BODY.PEEK[])` | Mensagem completa sem alterar `\Seen` | `BODY[]`, `RFC822`, `STORE`, `COPY`, `MOVE`, `EXPUNGE` proibidos |
| 6 | `LOGOUT` | Encerrar | |

O cliente é embrulhado numa classe que só expõe esses métodos; um teste verifica que nenhum outro comando é emitido.

## Respostas e erros

| Situação | Sinal do servidor | Tratamento | Causa de aviso |
|----------|-------------------|------------|----------------|
| Senha comum ou revogada | `NO [AUTHENTICATIONFAILED]` | Caixa pulada; "caixa n: autenticação recusada (verifique a senha de app)" | `caixa<n>:autenticacao` |
| IMAP desativado no Workspace | `NO` no `LOGIN` com texto sobre IMAP desativado | Caixa pulada; mensagem cita o console de administração | `caixa<n>:autenticacao` |
| Pasta inexistente | `NO` no `EXAMINE` | Caixa pulada; log lista as pastas | `caixa<n>:pasta` |
| Sem rede ou tempo esgotado | exceção de socket ou timeout | Caixa pulada; retomada pela janela | `caixa<n>:conexao` |
| Janela vazia | `SEARCH` sem resultados | "caixa n: nenhum anexo novo" | nenhuma |

## Idempotência

Leitura pura: repetir a sequência não altera a caixa. A idempotência do processamento vem do registro (`data-delta.md` §2).
