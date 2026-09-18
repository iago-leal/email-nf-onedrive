# Investigation: MVP de arquivamento automático de NFs e boletos

> Identificador: `001-mvp-email-nf-onedrive`
> Data: `2026-09-18`
> Complementa: `roadmap.md` (decisões D-01 a D-19)

## 1. Acesso à caixa: IMAP ou Gmail API

| Critério | IMAP com senha de app | Gmail API com OAuth 2.0 |
|----------|------------------------|-------------------------|
| Dependências | Biblioteca padrão (`imaplib`) | Cliente Google e fluxo OAuth |
| Configuração | Senha de app, que exige verificação em duas etapas na conta | Projeto no Google Cloud, tela de consentimento e token renovável |
| Somente leitura | `EXAMINE` e `BODY.PEEK[]` garantem | Escopo `gmail.readonly` garante |
| Risco | O administrador do Workspace pode desativar o IMAP ou as senhas de app | Mais peças para a empresa cliente operar depois da entrega |

**Escolha:** IMAP, como fixado pela spec `configuracao-caixas` (NG-03). A Gmail API continua como plano B se o login com senha de app falhar (P-02).

Particularidades do Gmail a observar:
- Rótulos aparecem como pastas IMAP. `INBOX` é a caixa de entrada; `[Gmail]/Todos os e-mails` (nome localizado conforme o idioma da conta) contém tudo. Nomes com acento chegam em UTF-7 modificado (RFC 3501, §5.1.3), o que justifica `coleta/utf7.py`.
- `SEARCH SINCE` compara só a data, sem hora, no fuso do servidor; daí a sobreposição de 2 dias da janela (CE RF-03).
- `BODY.PEEK[]` não altera a flag `\Seen`; `FETCH BODY[]` a alteraria, e por isso deve ser proibido no código e verificado em teste.
- O Gmail limita a largura de banda IMAP por conta (ordem de GB por dia), muito acima do volume esperado.

Fontes:
- RFC 3501, IMAP4rev1: https://datatracker.ietf.org/doc/html/rfc3501
- `imaplib`: https://docs.python.org/3/library/imaplib.html
- Senhas de app do Google: https://support.google.com/accounts/answer/185833

## 2. Parsing de e-mail e classificação

- `email.message_from_bytes(..., policy=email.policy.default)` devolve `EmailMessage`, cujo `iter_attachments()` e cujo `get_filename()` já decodificam nomes RFC 2047 e RFC 2231 (CE EC-05). Mensagens encaminhadas como `message/rfc822` exigem descer na parte embutida (CE RF-04).
- NF-e: o XML autorizado tem raiz `nfeProc` (NF-e com protocolo) ou `NFe` (sem protocolo), no namespace `http://www.portalfiscal.inf.br/nfe`. Basta o primeiro evento `start` do `xml.etree.ElementTree.iterparse` para decidir.
- XML hostil: o `expat` embutido nas versões atuais do Python não resolve entidades externas e mitiga expansão exponencial; ler só a raiz e limitar o tamanho (10 MB) reduz ainda mais o risco. `defusedxml` fica como alternativa se a auditoria pedir.
- Palavras-chave: `nf` e `nfe` são curtas demais para busca por substring ("info", "conforme"). A comparação usa texto normalizado (NFKD, sem marcas diacríticas, minúsculas) e expressão regular com fronteira `(?<![a-z0-9])termo(?![a-z0-9])`; `nf-e` e `nfs-e` também casam com `nf_e`, `nfe` e `nfse`, variações comuns em nomes de arquivo.

Fontes:
- `email.policy`: https://docs.python.org/3/library/email.policy.html
- Portal Nacional da NF-e (esquemas XSD): https://www.nfe.fazenda.gov.br/portal/

## 3. Rclone e OneDrive for Business

**Por que o Rclone:** decisão do usuário (spec `envio-onedrive`, decision log). Ele já trata OAuth, renovação de token, retentativas e o limite de requisições (HTTP 429).

Comportamentos relevantes:
- `rclone copyto <local> <remote>:<caminho>` copia um arquivo para um nome exato. Com `--immutable`, o Rclone recusa modificar arquivo existente de conteúdo diferente, o que serve de segunda barreira contra sobrescrita (RN-02).
- `rclone lsjson <remote>:<caminho> --stat --hash` devolve tamanho e hashes de um único objeto; no OneDrive for Business o hash disponível é o QuickXorHash.
- `rclone hashsum quickxor <arquivo-local>` calcula o mesmo hash localmente, o que permite comparar sem baixar o remoto (D-11).
- O Rclone traduz caracteres proibidos no OneDrive por equivalentes Unicode (`--onedrive-encoding`). O saneamento próprio (EO RF-02) roda antes, para que o nome no OneDrive seja o que a equipe lê, sem substitutos inesperados.
- Restrições do OneDrive e do SharePoint: caracteres `" * : < > ? / \ |`, espaços no início ou no fim, ponto final, nomes reservados (`.lock`, `CON`, `PRN`, `AUX`, `NUL`, `COM0`–`COM9`, `LPT0`–`LPT9`, `_vti_`, `desktop.ini`) e caminho completo de até 400 caracteres. O limite de 200 caracteres do nome (EO RF-02) deixa folga para o caminho da pasta.

Fontes:
- Backend `onedrive`: https://rclone.org/onedrive/
- Flags globais (`--immutable`, `--retries`): https://rclone.org/docs/
- `rclone authorize`, para máquinas sem navegador: https://rclone.org/remote_setup/
- Restrições de nomes: https://support.microsoft.com/office/restrictions-and-limitations-in-onedrive-and-sharepoint-64883a5d-228e-48f5-b3d2-eb39e07630fa

## 4. Acesso ao OneDrive de outra conta e consentimento do tenant

A pasta `<Empresa> Financeiro/CONTAS A PAGAR` fica no OneDrive **pessoal** de `<conta-admin>@<dominio>`. Há dois caminhos:

1. **Autenticar como `<conta-admin>`:** o remote aponta para o próprio drive dessa conta, e o caminho de destino é o caminho da pasta. É o mais simples, mas o token dá acesso a todo o OneDrive dessa conta.
2. **Autenticar com outra conta que tenha a pasta compartilhada com permissão de edição:** no `rclone config`, escolher o drive pelo identificador (`drive_id`) do OneDrive de `<conta-admin>`, obtido pela busca de sites ou pelos itens compartilhados; o destino passa a ser relativo a esse drive.

Se o tenant `<tenant>` exigir consentimento de administrador para o aplicativo público do Rclone, as saídas são: o administrador conceder o consentimento, ou registrar um aplicativo próprio no Entra ID (permissões delegadas `Files.ReadWrite` e `offline_access`) e informar `client_id` e `client_secret` no `rclone config`. Ambas as saídas são documentadas no guia (RF-20).

Na VPS sem navegador, a autorização é feita com `rclone authorize "onedrive"` numa máquina com navegador; o token resultante é colado no `rclone config` da VPS. O refresh token do Microsoft 365 expira após período de inatividade (tipicamente 90 dias), o que não ocorre com execuções a cada 30 min, mas pode ser revogado pelo administrador ou por troca de senha (EO EC-01).

## 5. Estado persistente: SQLite

- `sqlite3` está na biblioteca padrão, grava de forma atômica e aceita consultas como "data mais antiga com anexo pendente" (CE RF-03).
- A trava de execução (D-14) garante um escritor por vez; não é preciso WAL nem controle de concorrência além disso.
- O arquivo fica em `var/registro.sqlite3` com permissão 600 (EM RNF-05).
- A simulação (D-17) usa uma transação que termina sempre em `ROLLBACK`.

Alternativas descartadas: JSON em disco (reescrita integral a cada mudança e risco de corrupção por queda no meio da gravação), `shelve` (formato opaco e dependente da plataforma).

## 6. Trava e limite de duração

- `fcntl.flock` libera a trava quando o processo morre, mas não resolve o processo travado; `O_CREAT | O_EXCL` com PID e horário permite as duas verificações exigidas: idade maior que 25 min (EM RF-04) e PID inexistente.
- `signal.alarm(1200)` com um tratador que levanta exceção faz a execução encerrar em 20 min, antes da expiração da trava, e passa pelo `finally` que libera a trava e apaga a pasta de trabalho.
- `cron` não impede sobreposição; a trava fica no código para valer também em execuções manuais.

## 7. Aviso pelo Telegram

- `POST https://api.telegram.org/bot<token>/sendMessage` com `chat_id` e `text`; resposta JSON com `ok`. Limite de 4096 caracteres por mensagem: o aviso é truncado com a indicação "(ver log)".
- O token nunca entra em log: a URL com o token não é registrada, e o filtro de segredos (D-04) cobre exceções que a contenham.
- Criação do bot pelo `@BotFather`; o `chat_id` é obtido enviando uma mensagem ao bot e consultando `getUpdates`, passo a documentar no guia.

Fonte: https://core.telegram.org/bots/api#sendmessage

## 8. Agendamento

`cron` foi escolha do usuário (spec `execucao-monitoramento`, decision log). O `systemd timer` teria log integrado e `Persistent=true` para execuções perdidas, mas a janela de busca já cobre a VPS desligada (EM EC-04). Linha prevista:

```
*/30 * * * * cd /opt/email-nf-onedrive && ./.venv/bin/email-nf-onedrive executar >/dev/null 2>&1
```

A saída vai para `/dev/null` porque o log próprio (D-15) é a fonte da verdade; o `cron` não tem destinatário de e-mail na VPS.

## 9. Padrões aplicáveis

- **Fachada com lista branca** (`envio/rclone.py`): concentra a única fronteira com o processo externo e torna RN-02 verificável num só lugar.
- **Estratégia isolada** (`envio/nomeacao.py`): absorve a mudança prevista em L-03.
- **Injeção de dependências simples:** `ciclo.py` recebe fábricas de cliente IMAP, fachada do Rclone e notificador, o que permite os dublês de teste sem *monkeypatching* extenso.
- **Estados explícitos no registro** (`extraido`, `enviado`, `falha-envio`, `retido`): cada transição tem um único dono (`coleta` ou `envio`), descrito em `data-delta.md`.
