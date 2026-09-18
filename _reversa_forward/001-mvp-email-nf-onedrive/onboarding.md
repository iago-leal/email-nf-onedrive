# Onboarding: testar a feature pela primeira vez

> Identificador: `001-mvp-email-nf-onedrive`
> Data: `2026-09-18`
> Público: quem vai testar a ferramenta depois do `/reversa-coding`, na máquina de desenvolvimento e depois na VPS.
> Tempo estimado: 20 min na etapa local; 60 min na etapa com OneDrive e Gmail reais.

## 0. Pré-requisitos

- Python 3.11 ou superior (`python3 --version`).
- Rclone 1.60 ou superior (`rclone version`); a máquina do operador tem a 1.74.
- Acesso à caixa `EMAIL1`, com verificação em duas etapas ativa e uma **senha de app** gerada.
- Acesso de edição à pasta `<Empresa> Financeiro/CONTAS A PAGAR` no OneDrive de `<conta-admin>@<dominio>`.
- Um bot do Telegram (criado pelo `@BotFather`) e o `chat_id` do operador.

## 1. Instalação local e testes automatizados

```bash
cd <diretório do repositório>
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

Esperado: todos os testes verdes, inclusive os de `tests/integracao/`, que usam o Rclone real contra um diretório temporário.

## 2. Configuração

```bash
cp .env.example .env.novo   # compare com o .env existente e acrescente as variáveis que faltam
chmod 600 .env
email-nf-onedrive verificar-config
```

Preencha no `.env`, além de `EMAIL1` e `SENHA_EMAIL1`: `RCLONE_REMOTE`, `DESTINO_ONEDRIVE`, `DATA_INICIAL`, `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`.

Esperado: `1 · <endereço> · INBOX · <destino>` e a senha como `****`. Se o `.env` estiver com permissão 644, o log registra "permissão do .env mais aberta que 600"; hoje ele está assim na máquina do operador.

Teste negativo: apague temporariamente `RCLONE_REMOTE`, rode `email-nf-onedrive executar` e confira `echo $?` igual a `2`, sem nenhuma conexão aberta.

## 3. Remote do OneDrive e levantamento da convenção de nomes (fecha a L-03)

```bash
rclone config          # novo remote, tipo onedrive, "business"
                       # na VPS sem navegador: rclone authorize "onedrive" noutra máquina e colar o token
rclone lsf "<remote>:<Empresa> Financeiro/CONTAS A PAGAR" --max-depth 2 | head -50
```

Anote o padrão de nomes e de subpastas que a equipe já usa e leve-o ao `/reversa-add` ou ao próprio `/reversa-coding`, para ajustar `envio/nomeacao.py`. Se o `rclone config` falhar por consentimento do tenant, siga `investigation.md` §4.

```bash
email-nf-onedrive testar-onedrive
```

Esperado: `OneDrive: escrita confirmada em <destino>`, e nenhum arquivo de teste restante na pasta.

## 4. Simulação contra a caixa real

```bash
email-nf-onedrive executar --simular
tail -50 var/log/email-nf-onedrive.log
```

Esperado:
- conexão "caixa 1: conectada";
- lista do que seria enviado e do que ficaria "retido para revisão";
- nenhuma mensagem marcada como lida no Gmail;
- `var/registro.sqlite3` sem linhas novas (`sqlite3 var/registro.sqlite3 'select count(*) from anexos'`);
- nenhuma mensagem no Telegram.

Confira na lista de retidos se alguma NF ou boleto legítimo ficou de fora (risco R-04). Se ficou, amplie a lista de palavras-chave antes da produção.

## 5. Ciclo real com e-mail de teste

1. De outra conta, envie à caixa 1 um e-mail com assunto "Boleto teste" e um PDF anexo `Boleto Teste.pdf`, e outro com assunto "Proposta" e `contrato.pdf`.
2. Rode `email-nf-onedrive executar` e confira `echo $?` igual a `0`.
3. No OneDrive, confirme `AAAA-MM-DD_<remetente>_Boleto Teste.pdf` (ou o nome pela convenção real, se a L-03 já estiver fechada).
4. Confirme que `contrato.pdf` **não** está na pasta e aparece no log como "retido para revisão".
5. Rode `executar` de novo: nenhum arquivo novo, e o log diz "caixa 1: nenhum anexo novo".
6. Confirme que `var/trabalho/` está vazio.

## 6. Falha e aviso

1. Troque `SENHA_EMAIL1` por um valor errado e rode `executar`: código `2` (única caixa inválida), aviso no Telegram citando "caixa 1", "autenticação recusada" e "verifique a senha de app".
2. Rode de novo: nenhum aviso novo (supressão de 6 h).
3. Restaure a senha e rode: aviso "recuperado: caixa 1 voltou a funcionar".
4. `grep -F "<senha real>" var/log/*` não deve retornar nada; faça o mesmo com o token do Telegram.

## 7. Sobreposição

Em dois terminais, rode `executar` ao mesmo tempo. Esperado: um conclui o ciclo e o outro sai em menos de 1 s com código `0` e a linha "execução anterior em andamento".

## 8. Agendamento

```bash
crontab -e
# */30 * * * * cd /opt/email-nf-onedrive && ./.venv/bin/email-nf-onedrive executar >/dev/null 2>&1
crontab -l
```

Depois de 1 h, o log deve mostrar dois resumos, e `var/log/` deve ter um único arquivo do dia.

## 9. Critério de sucesso do onboarding

Todos os passos de 1 a 8 com o resultado esperado. Qualquer divergência vira registro em `/reversa-debugger`.
