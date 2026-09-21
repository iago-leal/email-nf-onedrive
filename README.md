# email-nf-onedrive

Arquiva no OneDrive for Business, sem ação manual, as notas fiscais e os boletos que chegam por e-mail.

A cada execução, agendada no `cron` a cada 30 minutos, a ferramenta:

1. lê as caixas do Google Workspace configuradas no `.env`, por IMAP, autenticando em cada uma com senha de app ou com OAuth 2.0;
2. extrai os anexos PDF e XML, inclusive de mensagens encaminhadas;
3. classifica cada anexo: NF-e em XML e documentos com palavra-chave (nota fiscal, boleto, fatura etc.) seguem para o OneDrive, e os demais ficam retidos para revisão manual;
4. envia os arquivos à pasta de destino via [Rclone](https://rclone.org), com o nome no padrão da pasta, `<EMPRESA> - <FORNECEDOR> [NF <n>] - <REF|BOLETO>.<ext>` (por exemplo, `ACME - FORNECEDOR NF 123 - REF.pdf`);
5. registra o que foi processado, grava log diário e avisa o operador pelo Telegram quando algo falha.

## O que ela nunca faz

- **Nunca altera as caixas de e-mail.** A pasta é aberta em modo somente leitura (`EXAMINE`) e as mensagens são lidas com `BODY.PEEK[]`: nada é marcado como lido, movido, apagado ou respondido.
- **Nunca apaga nem sobrescreve arquivos no OneDrive.** Um nome já ocupado por outro conteúdo recebe sufixo `_2`, `_3`...; a pasta de destino nunca é criada; o único arquivo que a ferramenta apaga é o de teste do comando `testar-onedrive`, pelo nome exato.
- **Nunca expõe credenciais.** Senhas, tokens, o segredo do cliente OAuth e as autorizações das caixas são mascarados no log, nos avisos e no terminal.

## Uso

```
email-nf-onedrive [--home DIR] executar [--simular]   # ciclo completo; --simular não envia, não registra, não avisa
email-nf-onedrive [--home DIR] verificar-config       # valida o .env e lista as caixas, sem acessar a rede
email-nf-onedrive [--home DIR] testar-onedrive        # grava, confere e apaga um arquivo de teste em cada destino
email-nf-onedrive [--home DIR] testar-caixa [<n>]     # autentica e abre a pasta de cada caixa, sem ler mensagens
email-nf-onedrive [--home DIR] autorizar-caixa <n>    # consentimento OAuth de uma caixa; grava a autorização
```

`--home` (ou a variável `EMAIL_NF_HOME`) indica o diretório com o `.env` e a pasta `var/`; o padrão é o diretório corrente. Códigos de saída: `0` sucesso, `1` falha parcial, `2` erro de configuração ou falha total.

## Autenticação nas caixas

Cada caixa usa um de dois modos, escolhido por `AUTH_EMAIL<n>` no `.env`:

- `senha` (padrão): senha de app do Google em `SENHA_EMAIL<n>`. Um `.env` sem `AUTH_EMAIL<n>` funciona como sempre funcionou.
- `oauth`: autorização OAuth 2.0 concedida a um cliente próprio no Google Cloud (`OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`), sem custo. O comando `autorizar-caixa <n>` conduz o consentimento no navegador e grava a autorização em `autorizacoes/<endereço>.json` (ou em `DIR_AUTORIZACOES`), com permissão 600; a cada execução ela é trocada por uma credencial temporária, que fica só em memória, e a conexão usa `AUTHENTICATE XOAUTH2`. A senha da conta deixa de ser guardada.

O escopo que o Google exige para IMAP com OAuth é amplo, mas o acesso efetivo continua somente leitura. O roteiro completo (projeto no Google Cloud, comunicado ao titular, cópia para a VPS, avisos, revogação e entrega) está na seção 16 do guia.

## Instalação em produção

Siga o [guia de instalação e operação](docs/instalacao-e-operacao.md): VPS, usuário de serviço, senha de app do Google ou OAuth 2.0, autorização do Rclone, `.env`, bot do Telegram, `cron` e rotina de operação. O modelo do `.env` está em [`.env.example`](.env.example).

## Desenvolvimento

Requer Python 3.11 ou superior e, para os testes de integração, o Rclone 1.60 ou superior no `PATH`.

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest                    # todos os testes
.venv/bin/pytest -m "not integracao"  # só os de unidade
```

Os testes usam apenas dados sintéticos (`tests/dados/`), um servidor IMAP simulado, um serviço de autorização OAuth simulado em `127.0.0.1`, um Telegram simulado e o Rclone real gravando num diretório temporário: nenhum acessa a rede. O mapa entre requisitos e testes está em [`tests/RASTREABILIDADE.md`](tests/RASTREABILIDADE.md).

Organização do código em `src/email_nf_onedrive/`: `configuracao/` (leitura do `.env`), `autorizacao/` (OAuth: arquivo de autorização, serviço do Google, fluxo de consentimento e credencial por execução), `coleta/` (IMAP, MIME e classificação), `envio/` (nomeação e Rclone), `execucao/` (ciclo, trava, log, avisos) e `registro/` (SQLite).
