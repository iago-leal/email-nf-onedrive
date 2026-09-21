# Onboarding: testar a feature pela primeira vez

> Identificador: `002-oauth-gmail-google-cloud`
> Data: `2026-09-21`
> Público: quem vai testar a feature depois do `/reversa-coding`, na máquina do operador e depois na VPS.
> Tempo estimado: 10 min na etapa automatizada; 30 min para criar o projeto no Google Cloud; 10 min por caixa autorizada.

## 0. Pré-requisitos

- A feature 001 instalada e com `pytest` verde (ver `_reversa_forward/001-mvp-email-nf-onedrive/onboarding.md`).
- Uma conta do Google para ser dona do projeto no Google Cloud: a conta pessoal do operador (sessão de esclarecimentos, 2a). Não é preciso cartão nem conta de faturamento.
- Para a etapa real: o endereço e a senha de ao menos uma das caixas, e o comunicado ao titular já enviado (RN-09, RF-14).
- Um navegador com janela anônima na máquina do operador. A VPS não precisa de navegador.

## 1. Testes automatizados

```bash
cd <diretório do repositório>
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

Esperado: 361 testes verdes (os 236 anteriores e 125 novos), sem acesso à internet: o serviço de autorização e o IMAP são dublês locais. Os de integração exigem o `rclone` no `PATH`; sem ele, são pulados.

## 2. Compatibilidade: nada muda sem `AUTH_EMAIL<n>`

```bash
email-nf-onedrive verificar-config
```

Esperado: a mesma saída de antes da atualização, com todas as caixas terminando em `senha ****`, sem linha sobre cliente OAuth.

## 3. Validação da configuração, sem rede

No `.env` de teste:

```
AUTH_EMAIL2=oauth
```

1. Sem `OAUTH_CLIENT_ID` e `OAUTH_CLIENT_SECRET`: `verificar-config` mostra `inválida: caixa 2: credenciais do cliente OAuth ausentes`, e a caixa 1 segue listada.
2. Com as duas variáveis preenchidas com qualquer texto e sem `SENHA_EMAIL2`: a caixa 2 aparece como `oauth (sem autorização)`.
3. Com `AUTH_EMAIL3=token`: `inválida: caixa 3: AUTH_EMAIL3 inválido (use senha ou oauth)`.
4. Com `SENHA_EMAIL2` presente: `alerta: SENHA_EMAIL2 presente em caixa oauth; retire-a do .env`.

## 4. Projeto no Google Cloud (uma vez)

Os nomes dos menus podem variar. O roteiro completo, com o caso do Workspace que restringe aplicativos de terceiros, está em `docs/instalacao-e-operacao.md` §16.1; o ideal é seguir o guia, e não este resumo, para validar o RF-13.

1. Em https://console.cloud.google.com, com a conta pessoal do operador, criar um projeto (por exemplo `email-nf-onedrive`). Recusar qualquer oferta de teste gratuito com faturamento.
2. Em "Google Auth Platform" › "Branding": nome do aplicativo e e-mail de suporte.
3. Em "Público": tipo **Externo**; depois, **Publicar aplicativo**, de modo que o estado fique "Em produção". Não pedir a verificação. Em modo de teste a autorização caduca em 7 dias (RN-05).
4. Em "Acesso a dados": acrescentar o escopo `https://mail.google.com/`.
5. Em "Clientes": criar cliente OAuth do tipo **App para computador**. Copiar o identificador e o segredo para `OAUTH_CLIENT_ID` e `OAUTH_CLIENT_SECRET` do `.env`, na máquina do operador e na VPS.
6. Não ativar nenhuma API: o IMAP não depende da API do Gmail.

Conferência: `verificar-config` mostra `cliente OAuth: configurado`.

## 5. Autorizar uma caixa (máquina do operador)

```bash
email-nf-onedrive autorizar-caixa 2
```

1. Copiar o endereço impresso e abri-lo numa **janela anônima**.
2. Entrar com o endereço e a senha da caixa 2. Se o Google pedir confirmação em outro aparelho ou código por SMS, parar: essa caixa precisa do titular presente (premissa P-01).
3. Na tela "O Google não verificou este app", escolher "Avançado" e "Acessar email-nf-onedrive (não seguro)".
4. Manter marcada a permissão de acesso ao Gmail e continuar.
5. A janela mostra "Retorno recebido. Você pode fechar esta janela e voltar ao terminal."; o terminal mostra `caixa 2: autorizada · <endereço>` e `arquivo: <caminho>.json (permissão 600)`.

Conferências:

```bash
ls -l autorizacoes/          # arquivo <endereço>.json com -rw-------
email-nf-onedrive verificar-config   # caixa 2: oauth (autorizada)
email-nf-onedrive testar-caixa 2     # caixa 2: acesso confirmado (oauth)
```

Se o consentimento for bloqueado com "acesso bloqueado pelo administrador", o domínio restringe aplicativos de terceiros (premissa P-02): o administrador do Workspace precisa marcar o identificador do cliente como confiável em Segurança › Controles de API.

Testes negativos:

1. **Conta errada:** rodar `autorizar-caixa 2` e entrar com a conta de outra caixa. Esperado: `conta autorizada difere de EMAIL2`, código 2, e o arquivo anterior da caixa 2 intacto (mesma data de modificação).
2. **Consentimento negado:** clicar em "Cancelar" na tela do Google. Esperado: `caixa 2: consentimento negado`, código 2.
3. **Tempo esgotado:** rodar e não abrir o endereço. Esperado: `erro: caixa 2: tempo esgotado à espera do consentimento` após 5 min, código 2.
4. **Permissão desmarcada:** na tela de consentimento, desmarcar o acesso ao Gmail. Esperado: `erro: caixa 2: acesso ao correio não concedido`, código 2, nada gravado.

As recusas saem na saída de erro, com o prefixo `erro:`. A tabela completa está no guia, §16.3.

## 6. Levar a autorização para a VPS

O usuário de serviço não aceita login; a cópia passa pelo seu usuário na VPS (guia, §16.4):

```bash
scp -rp autorizacoes/ <seu-usuario>@<vps>:autorizacoes-novas
ssh <seu-usuario>@<vps>
sudo mkdir -p -m 700 /opt/email-nf-onedrive/autorizacoes
sudo cp ~/autorizacoes-novas/*.json /opt/email-nf-onedrive/autorizacoes/ && rm -r ~/autorizacoes-novas
sudo chown -R email-nf: /opt/email-nf-onedrive/autorizacoes
sudo chmod 700 /opt/email-nf-onedrive/autorizacoes && sudo chmod 600 /opt/email-nf-onedrive/autorizacoes/*.json
sudo -iu email-nf
.venv/bin/email-nf-onedrive testar-caixa
```

Esperado na VPS: `acesso confirmado (oauth)` para cada caixa autorizada, sem nenhum passo de navegador (RF-05).

Depois de confirmada a caixa, retirar `SENHA_EMAIL2` dos dois `.env` (RN-09) e conferir que o alerta do item 3.4 some.

## 7. Ciclo completo

```bash
email-nf-onedrive executar --simular
grep "conectada" var/log/*.log | tail
```

Esperado: `caixa 2: conectada (oauth)`, anexos listados como seriam enviados, mensagens não lidas ainda não lidas na caixa.

Renovação sem intervenção: repetir `testar-caixa 2` mais de 1 h depois, sem reautorizar. Esperado: acesso confirmado.

Troca de modo sem duplicar (RN-07): numa caixa que já enviou documentos em modo `senha`, mudar para `oauth`, autorizar e rodar `executar --simular`. Esperado: nenhum documento já enviado aparece como "seria enviado".

## 8. Falhas e avisos

1. **Revogação:** na conta da caixa 2, em https://myaccount.google.com/permissions, remover o acesso do aplicativo. Rodar `executar`. Esperado: log `caixa 2: autorização OAuth recusada (rode autorizar-caixa 2)`, as demais caixas processadas, código 1, um aviso no Telegram; na execução seguinte, dentro de 6 h, nenhum aviso repetido.
2. **Recuperação:** refazer `autorizar-caixa 2`, copiar o arquivo e rodar `executar`. Esperado: código 0 e um único aviso de recuperação.
3. **Serviço indisponível:** na VPS, bloquear por alguns minutos a saída para `oauth2.googleapis.com` (por exemplo, com uma linha em `/etc/hosts` apontando para `127.0.0.1`) e rodar `executar`. Esperado: `caixa N: serviço de autorização do Google indisponível. Nova tentativa na próxima execução.` para cada caixa em `oauth`, resumo com `k de autorização`, arquivos de autorização com a mesma data de modificação; ao desfazer o bloqueio, a execução seguinte entra normalmente.
4. **Credenciais do cliente erradas:** trocar um caractere de `OAUTH_CLIENT_SECRET` e rodar `testar-caixa`. Esperado: cada caixa em `oauth` aparece como `falhou (credenciais do cliente OAuth recusadas pelo Google)`, mas só a primeira consulta o Google. Com `executar`, o aviso no Telegram traz uma única linha `credenciais do cliente OAuth recusadas pelo Google. Ação: confira OAUTH_CLIENT_ID e OAUTH_CLIENT_SECRET no .env.`, e não uma por caixa.
5. **Permissão aberta:** `chmod 644 autorizacoes/<endereço>.json` e rodar `executar --simular`. Esperado: `configuração: permissão da autorização da caixa 2 mais aberta que 600` no log, e a mesma frase como `alerta:` no `verificar-config`. Restaurar com `chmod 600`.

## 9. Segredos fora dos logs

Depois de um ciclo real:

```bash
grep -rF -f <(python3 - <<'PY'
import json, glob
from dotenv import dotenv_values
print(dotenv_values(".env")["OAUTH_CLIENT_SECRET"])
for f in glob.glob("autorizacoes/*.json"):
    print(json.load(open(f))["refresh_token"])
PY
) var/log/ && echo "VAZOU" || echo "limpo"
```

Esperado: `limpo`. O comando não imprime os segredos no terminal; usa-os só como padrão de busca.

## 10. Entrega ao cliente (quando chegar a hora)

No Google Cloud, em IAM, acrescentar a conta do cliente como **Proprietário** do projeto; depois do aceite do convite, remover a conta do operador. O identificador e o segredo do cliente OAuth não mudam, e as autorizações seguem válidas (D-17, premissa P-05). Conferir com `testar-caixa` na VPS.
