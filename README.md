# email-nf-onedrive

Arquiva no OneDrive for Business, sem ação manual, as notas fiscais e os boletos que chegam por e-mail.

A cada execução, agendada no `cron` a cada 30 minutos, a ferramenta:

1. lê as caixas do Google Workspace configuradas no `.env`, por IMAP;
2. extrai os anexos PDF e XML, inclusive de mensagens encaminhadas;
3. classifica cada anexo: NF-e em XML e documentos com palavra-chave (nota fiscal, boleto, fatura etc.) seguem para o OneDrive, e os demais ficam retidos para revisão manual;
4. envia os arquivos à pasta de destino via [Rclone](https://rclone.org), com o nome `AAAA-MM-DD_remetente_nome-original`;
5. registra o que foi processado, grava log diário e avisa o operador pelo Telegram quando algo falha.

## O que ela nunca faz

- **Nunca altera as caixas de e-mail.** A pasta é aberta em modo somente leitura (`EXAMINE`) e as mensagens são lidas com `BODY.PEEK[]`: nada é marcado como lido, movido, apagado ou respondido.
- **Nunca apaga nem sobrescreve arquivos no OneDrive.** Um nome já ocupado por outro conteúdo recebe sufixo `_2`, `_3`...; a pasta de destino nunca é criada; o único arquivo que a ferramenta apaga é o de teste do comando `testar-onedrive`, pelo nome exato.
- **Nunca expõe credenciais.** Senhas e tokens são mascarados no log, nos avisos e no terminal.

## Uso

```
email-nf-onedrive [--home DIR] executar [--simular]   # ciclo completo; --simular não envia, não registra, não avisa
email-nf-onedrive [--home DIR] verificar-config       # valida o .env e lista as caixas, sem acessar a rede
email-nf-onedrive [--home DIR] testar-onedrive        # grava, confere e apaga um arquivo de teste em cada destino
```

`--home` (ou a variável `EMAIL_NF_HOME`) indica o diretório com o `.env` e a pasta `var/`; o padrão é o diretório corrente. Códigos de saída: `0` sucesso, `1` falha parcial, `2` erro de configuração ou falha total.

## Instalação em produção

Siga o [guia de instalação e operação](docs/instalacao-e-operacao.md): VPS, usuário de serviço, senha de app do Google, autorização do Rclone, `.env`, bot do Telegram, `cron` e rotina de operação. O modelo do `.env` está em [`.env.example`](.env.example).

## Desenvolvimento

Requer Python 3.11 ou superior e, para os testes de integração, o Rclone 1.60 ou superior no `PATH`.

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest                    # todos os testes
.venv/bin/pytest -m "not integracao"  # só os de unidade
```

Os testes usam apenas dados sintéticos (`tests/dados/`), um servidor IMAP simulado, um Telegram simulado e o Rclone real gravando num diretório temporário: nenhum acessa a rede. O mapa entre requisitos e testes está em [`tests/RASTREABILIDADE.md`](tests/RASTREABILIDADE.md).

Organização do código em `src/email_nf_onedrive/`: `configuracao/` (leitura do `.env`), `coleta/` (IMAP, MIME e classificação), `envio/` (nomeação e Rclone), `execucao/` (ciclo, trava, log, avisos) e `registro/` (SQLite).
