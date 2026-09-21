# Data delta: acesso às caixas do Gmail por OAuth 2.0

> Identificador: `002-oauth-gmail-google-cloud`
> Data: `2026-09-21`
> Modelo de referência: `_reversa_sdd/sdd/configuracao-caixas.md#9. Modelo de Dados`, `_reversa_sdd/sdd/execucao-monitoramento.md#9. Modelo de Dados` e `_reversa_forward/001-mvp-email-nf-onedrive/data-delta.md`

## 1. Visão geral

O banco `var/registro.sqlite3` não muda: nenhuma tabela, coluna ou índice novo, e nenhuma migração. A chave do registro continua (endereço da caixa em minúsculas, identificador da mensagem, SHA-256), o que garante a RN-07 sem código novo. O delta está em duas entidades em memória e numa entidade em arquivo.

## 2. Entidade `Caixa` (em memória, `configuracao/modelo.py`)

| Campo | Tipo | Delta |
|-------|------|-------|
| `modo` | `"senha"` ou `"oauth"` | **Novo**, padrão `"senha"`. Lido de `AUTH_EMAIL<n>`, sem diferenciar maiúsculas. |
| `senha` | texto, fora do `repr` | **Regra alterada**: obrigatória só quando `modo == "senha"`; vazia em `oauth`, mesmo que `SENHA_EMAIL<n>` exista no `.env` (D-10). |
| demais campos | | Sem alteração. |

## 3. Entidade `ClienteOAuth` (em memória, nova)

| Campo | Tipo | Origem | Observação |
|-------|------|--------|------------|
| `client_id` | texto | `OAUTH_CLIENT_ID` | Não é segredo; aparece no endereço de autorização. |
| `client_secret` | texto, fora do `repr` | `OAUTH_CLIENT_SECRET` | Registrado em `segredos`. |

`Configuracao` ganha `cliente_oauth: ClienteOAuth | None` e `dir_autorizacoes: Path`. `cliente_oauth` é `None` quando qualquer das duas variáveis falta; nesse caso, toda caixa em `oauth` vira `CaixaInvalida` com o motivo "caixa n: credenciais do cliente OAuth ausentes", e as caixas em `senha` seguem (RF-03).

## 4. Entidade `Autorizacao` (em arquivo, nova)

Caminho: `<DIR_AUTORIZACOES>/<endereço em minúsculas>.json`. `DIR_AUTORIZACOES` tem o padrão `autorizacoes`, relativo ao diretório de instalação (o mesmo do `.env`). Diretório com permissão 700; arquivo com 600, UTF-8.

```json
{
  "versao": 1,
  "endereco": "financeiro@<dominio-1>",
  "client_id": "<identificador do cliente OAuth>",
  "refresh_token": "<autorização durável>",
  "escopos": ["https://mail.google.com/", "openid", "email"],
  "autorizada_em": "2026-09-21T18:40:11+00:00"
}
```

| Campo | Validação na leitura | Falha |
|-------|----------------------|-------|
| `versao` | igual a `1` | autorização ilegível |
| `endereco` | igual a `EMAIL<n>`, sem diferenciar maiúsculas | "autorização de outro endereço" |
| `client_id` | igual a `OAUTH_CLIENT_ID` | "autorização emitida para outro cliente OAuth" |
| `refresh_token` | texto não vazio; registrado em `segredos` | autorização ilegível |
| `escopos` | contém `https://mail.google.com/` | autorização ilegível |
| `autorizada_em` | informativo | nenhuma |

Toda falha de leitura gera a causa `caixa<n>:autorizacao` (D-08) e a mesma ação: rodar `autorizar-caixa <n>`.

Regras de escrita (só o `autorizar-caixa` escreve):

1. cria o diretório com 700 se não existir;
2. grava em arquivo temporário no mesmo diretório, aberto com `os.open(..., O_CREAT | O_EXCL | O_WRONLY, 0o600)`;
3. `os.replace` sobre o destino, de modo que uma reautorização substitui a anterior de forma atômica e um consentimento recusado (RF-06) não deixa resíduo.

Nome do arquivo: o endereço em minúsculas seguido de `.json`. Endereço que contenha separador de caminho ou byte nulo invalida a caixa em modo `oauth` na configuração; na prática não ocorre, mas impede a travessia de diretório.

O ciclo nunca escreve nem apaga o arquivo (RF-09). A renovação do Google não troca a autorização durável, de modo que não há o que regravar.

## 5. Credencial temporária (em memória, nova)

`access_token` e o prazo informado por `expires_in`. Não tem representação em disco (D-06). É obtida no início do tratamento de cada caixa e descartada ao fim; registrada em `segredos` assim que recebida.

## 6. Entidade `ResumoExecucao` (em memória)

| Campo | Tipo | Delta |
|-------|------|-------|
| `falhas_autorizacao` | inteiro, padrão 0 | **Novo.** Conta as caixas puladas por causa `autorizacao`, `autorizacao-servico` ou `oauth:cliente`. Já estão incluídas em `falhas`; o campo só as distingue na linha de resumo (D-13). |

## 7. Tabela `avisos` (SQLite)

Sem mudança de esquema. Passam a existir três chaves de causa novas, tratadas pelo gerenciador atual sem alteração:

| Chave | Natureza | Mensagem-base |
|-------|----------|----------------|
| `caixa<n>:autorizacao` | permanente | "caixa n: autorização OAuth recusada (rode autorizar-caixa n)", com a variante "ausente" quando não há arquivo |
| `caixa<n>:autorizacao-servico` | transitória | "caixa n: serviço de autorização do Google indisponível. Nova tentativa na próxima execução." |
| `oauth:cliente` | permanente, global | "credenciais do cliente OAuth recusadas pelo Google. Ação: confira OAUTH_CLIENT_ID e OAUTH_CLIENT_SECRET no .env." |

## 8. Versionamento e cópias

- `.gitignore` ganha `autorizacoes/`. Quem usar `DIR_AUTORIZACOES` fora do padrão responde por mantê-lo fora do versionamento; o guia avisa.
- O diretório de autorizações entra na lista do que o guia manda copiar para a VPS e incluir no cuidado de backup, com a mesma ressalva do `.env`: cópia só por canal cifrado e com permissão restrita.

## 9. Migrações

Nenhuma. Instalação sem `AUTH_EMAIL<n>` lê a configuração exatamente como antes.
