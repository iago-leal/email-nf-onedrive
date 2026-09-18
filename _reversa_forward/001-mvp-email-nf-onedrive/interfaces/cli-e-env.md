# Interface: linha de comando e `.env`

> Tipo: CLI e arquivo de configuração · Direção: entrada (operador → ferramenta) · Dono no código: `cli.py`, `configuracao/`
> Specs de origem: `_reversa_sdd/sdd/configuracao-caixas.md`, `_reversa_sdd/sdd/execucao-monitoramento.md`

## Linha de comando

```
email-nf-onedrive [--home DIR] executar [--simular]
email-nf-onedrive [--home DIR] verificar-config
email-nf-onedrive [--home DIR] testar-onedrive
email-nf-onedrive --help
```

- `--home` (ou `EMAIL_NF_HOME`): diretório de instalação, onde ficam `.env` e `var/`; padrão, o diretório corrente.
- `python -m email_nf_onedrive` equivale ao binário.

| Subcomando | Acessa a rede | Usa trava | Envia aviso | Códigos de saída |
|------------|---------------|-----------|-------------|------------------|
| `executar` | sim | sim | sim, em código 1 ou 2 | 0 sucesso · 1 falha parcial · 2 configuração inválida ou falha total |
| `executar --simular` | IMAP e `lsjson` apenas | sim | não | igual a `executar` |
| `verificar-config` | não | não | não | 0 configuração válida · 2 erro global ou nenhuma caixa válida |
| `testar-onedrive` | só Rclone | não | não | 0 escrita confirmada · 2 falha |

## Contrato do `.env`

| Variável | Obrigatória | Padrão | Validação |
|----------|-------------|--------|-----------|
| `EMAIL<n>` | ao menos uma | | contém `@`; `<n>` inteiro positivo, lacunas permitidas |
| `SENHA_EMAIL<n>` | sim, para cada `EMAIL<n>` | | não vazia; senão, caixa inválida |
| `PASTA_EMAIL<n>` | não | `INBOX` | |
| `IMAP_HOST_EMAIL<n>` | não | `imap.gmail.com` | |
| `DESTINO_ONEDRIVE<n>` | não | valor de `DESTINO_ONEDRIVE` | |
| `RCLONE_REMOTE` | sim | | não vazia; erro global |
| `DESTINO_ONEDRIVE` | sim | | não vazia; erro global |
| `DATA_INICIAL` | sim | | `AAAA-MM-DD`; erro global |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | par | | só uma definida: alerta, execução sem aviso |

Mensagens de erro no formato `<escopo>: <variável> <problema>` (CC §8). Alertas não bloqueantes: senha órfã (CC EC-03), caixa duplicada (CC EC-04, mesmo endereço e mesma pasta), permissão do `.env` diferente de 600 (CC RF-11).

## Arquivos produzidos em `<home>/var/`

| Caminho | Permissão | Conteúdo |
|---------|-----------|----------|
| `registro.sqlite3` | 600 | Registro de processados e avisos (`data-delta.md`) |
| `log/email-nf-onedrive.log*` | 600 | Log com rotação diária, 30 arquivos |
| `execucao.lock` | 600 | PID e horário da execução em curso |
| `trabalho/<id>/` | 700 | Anexos da execução corrente; removido ao fim |
