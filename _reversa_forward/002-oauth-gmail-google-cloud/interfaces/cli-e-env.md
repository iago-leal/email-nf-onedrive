# Interface: linha de comando e `.env`

> Tipo: CLI e arquivo de configuração · Direção: entrada (operador → ferramenta) · Dono no código: `cli.py`, `configuracao/`, `autorizacao/`
> Delta sobre: `_reversa_forward/001-mvp-email-nf-onedrive/interfaces/cli-e-env.md`. Tudo o que não aparece aqui continua como lá.

## Linha de comando

```
email-nf-onedrive [--home DIR] autorizar-caixa <n>      (novo)
email-nf-onedrive [--home DIR] testar-caixa [<n>]       (novo)
email-nf-onedrive [--home DIR] verificar-config         (saída alterada)
email-nf-onedrive [--home DIR] executar [--simular]     (sem alteração de contrato)
email-nf-onedrive [--home DIR] testar-onedrive          (sem alteração)
```

| Subcomando | Acessa a rede | Usa trava | Envia aviso | Toca no registro | Códigos de saída |
|------------|---------------|-----------|-------------|------------------|------------------|
| `autorizar-caixa <n>` | Google (consentimento, troca, revogação) e `127.0.0.1` | não | não | não | 0 autorização gravada · 2 qualquer recusa |
| `testar-caixa [<n>]` | Google (renovação, só em `oauth`) e IMAP | não | não | não | 0 todas confirmadas · 1 alguma falhou · 2 configuração inválida, `<n>` inexistente ou nenhuma caixa válida |

### `autorizar-caixa <n>`

Pré-condições, verificadas antes de qualquer rede: `.env` válido; caixa `<n>` existente, válida e em modo `oauth`; credenciais do cliente presentes.

Saída em caso de sucesso (nenhuma linha contém segredo):

```
caixa 2: abra o endereço abaixo numa janela anônima e entre com <endereço>
https://accounts.google.com/o/oauth2/v2/auth?...
aguardando o consentimento (até 5 min)...
caixa 2: autorizada · <endereço>
arquivo: <DIR_AUTORIZACOES>/<endereço>.json (permissão 600)
```

Recusas, todas com código 2 e sem gravar nada: "caixa 2 não existe no .env", "caixa 2 não está em modo oauth (defina AUTH_EMAIL2=oauth)", "credenciais do cliente OAuth ausentes", "caixa 2: consentimento negado", "caixa 2: tempo esgotado à espera do consentimento", "conta autorizada difere de EMAIL2", "caixa 2: o Google não devolveu autorização durável", "caixa 2: acesso ao correio não concedido".

### `testar-caixa [<n>]`

Uma linha por caixa, na ordem do índice; caixas inválidas aparecem como falha:

```
caixa 1: acesso confirmado (senha)
caixa 2: falhou (sem autorização)
caixa 3: falhou (autorização recusada; rode autorizar-caixa 3)
caixa 4: falhou (serviço de autorização indisponível)
caixa 5: falhou (autenticação recusada)
```

Uma única tentativa de autenticação por caixa; a sequência é autenticar, `EXAMINE` da pasta e `LOGOUT`. Pasta inexistente também é falha ("pasta 'X' inexistente").

### `verificar-config`

A linha de cada caixa troca o final `senha ****` pelo modo:

```
1 · <endereço> · INBOX · <destino> · empresa <rótulo> · senha ****
2 · <endereço> · INBOX · <destino> · empresa <rótulo> · oauth (autorizada)
3 · <endereço> · INBOX · <destino> · empresa <rótulo> · oauth (sem autorização)
```

A linha das caixas em `senha` fica idêntica à de hoje. "Autorizada" significa só que o arquivo existe e é legível; o comando continua sem acessar a rede (RF-10). Linhas novas ao final, presentes só quando há caixa em `oauth`: `cliente OAuth: configurado` e `diretório de autorizações: <caminho>`.

## Contrato do `.env`

| Variável | Obrigatória | Padrão | Validação |
|----------|-------------|--------|-----------|
| `AUTH_EMAIL<n>` | não | `senha` | `senha` ou `oauth`, sem diferenciar maiúsculas; outro valor: caixa inválida, "caixa n: AUTH_EMAILn inválido (use senha ou oauth)" |
| `SENHA_EMAIL<n>` | só em modo `senha` | | em `oauth`, se presente: ignorada, com alerta "SENHA_EMAILn presente em caixa oauth; retire-a do .env" |
| `OAUTH_CLIENT_ID` | só se houver caixa em `oauth` | | não vazia; senão, caixas em `oauth` inválidas com "credenciais do cliente OAuth ausentes" |
| `OAUTH_CLIENT_SECRET` | só se houver caixa em `oauth` | | idem; nunca exibida |
| `DIR_AUTORIZACOES` | não | `autorizacoes` | caminho absoluto ou relativo ao diretório de instalação |

Alertas não bloqueantes novos: `AUTH_EMAIL<n>` sem `EMAIL<n>` (órfã, como a senha órfã); "permissão da autorização da caixa n mais aberta que 600" (RF-12); "permissão do diretório de autorizações mais aberta que 700"; `OAUTH_CLIENT_ID` ou `OAUTH_CLIENT_SECRET` definidas sem nenhuma caixa em `oauth` **não** geram alerta (RF-03).

Ordem de validação de uma caixa: endereço, modo, senha ou credenciais do cliente, duplicidade. A detecção de caixa duplicada (mesmo endereço e mesma pasta) independe do modo.

## `.env.example`

Ganha um bloco comentado com `AUTH_EMAIL1=senha`, `OAUTH_CLIENT_ID=`, `OAUTH_CLIENT_SECRET=` e `DIR_AUTORIZACOES=autorizacoes`, com remissão à seção do guia sobre o Google Cloud.
