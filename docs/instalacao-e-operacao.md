# Guia de instalação e operação

Este guia leva uma VPS Linux nova até a ferramenta rodando a cada 30 minutos, e depois orienta a operação do dia a dia. Quem o segue não precisa conhecer o código. Tempo estimado: 60 minutos, dos quais boa parte é espera por consentimentos no Google e na Microsoft.

Nos exemplos, `<Empresa> Financeiro/CONTAS A PAGAR` é a pasta de destino, `<conta-admin>@<dominio>` é a conta Microsoft 365 dona dessa pasta e `/opt/email-nf-onedrive` é o diretório de instalação. Substitua pelos valores reais.

## 1. O que a ferramenta faz e o que ela nunca faz

A cada execução, ela lê as caixas de e-mail configuradas, extrai os anexos PDF e XML que parecem nota fiscal ou boleto e os grava na pasta do OneDrive, com nome padronizado. Os anexos que ela não reconhece ficam **retidos para revisão**: aparecem no log, mas não vão para o OneDrive.

Ela **nunca** altera as caixas de e-mail: não marca como lida, não move, não apaga, não responde. Também **nunca** apaga nem sobrescreve arquivos no OneDrive: se já existir arquivo com o mesmo nome e outro conteúdo, o novo recebe o sufixo `_2`, `_3` e assim por diante.

## 2. Requisitos da VPS

- Linux com `systemd` e `cron` (Debian 12 ou Ubuntu 22.04 em diante foram os alvos do projeto).
- 1 vCPU, 512 MB de RAM e 1 GB livre em disco bastam; os anexos só passam pelo disco durante a execução.
- Saída para a internet nas portas 993 (IMAP do Gmail) e 443 (OneDrive e Telegram). Nenhuma porta de entrada precisa ser aberta.
- Relógio sincronizado (`timedatectl` deve mostrar `System clock synchronized: yes`).

## 3. Usuário de serviço

A ferramenta roda sob um usuário próprio, sem senha e sem `sudo`. O `.env`, o registro e a configuração do Rclone ficam acessíveis só a ele.

```bash
sudo adduser --system --group --home /opt/email-nf-onedrive --shell /bin/bash email-nf
sudo -iu email-nf        # a partir daqui, todos os comandos rodam como email-nf
```

## 4. Python, Rclone e a ferramenta

Como administrador (fora do usuário de serviço):

```bash
sudo apt update
sudo apt install -y python3 python3-venv sqlite3 git curl unzip
python3 --version        # precisa ser 3.11 ou superior
curl https://rclone.org/install.sh | sudo bash
rclone version           # precisa ser 1.60 ou superior
```

O Rclone dos repositórios da distribuição costuma ser antigo; o script oficial instala a versão atual.

Como `email-nf`:

```bash
cd /opt/email-nf-onedrive
git clone <url do repositório> app
python3 -m venv .venv
.venv/bin/pip install ./app
.venv/bin/email-nf-onedrive --help
```

Para atualizar depois: `cd app && git pull && cd .. && .venv/bin/pip install ./app`. O agendamento não precisa mudar.

## 5. Senha de app do Google (uma por caixa)

A ferramenta entra no Gmail com uma **senha de app**, não com a senha da conta.

1. Na conta da caixa, ative a verificação em duas etapas (Conta Google > Segurança).
2. Em Conta Google > Segurança > Senhas de app, crie uma senha com o nome `email-nf-onedrive`. O Google mostra 16 letras uma única vez; copie-as sem espaços.
3. No Google Workspace, confirme com o administrador que o acesso IMAP está permitido para a conta (Admin > Apps > Google Workspace > Gmail > Acesso do usuário final).

Se a opção "Senhas de app" não aparecer, o administrador do Workspace precisa permitir a verificação em duas etapas para a organização.

## 6. Acesso ao OneDrive com o Rclone

### 6.1 Autorização

A VPS não tem navegador, então a autorização é feita em duas máquinas.

Num computador com navegador e o Rclone instalado:

```bash
rclone authorize "onedrive"
```

O navegador abre; entre com a conta que tem permissão de edição na pasta de destino. O terminal imprime um bloco JSON com o token: copie-o inteiro.

Na VPS, como `email-nf`:

```bash
rclone config
```

- `n` para novo remote; nome, por exemplo, `onedrive-financeiro` (é o valor de `RCLONE_REMOTE`);
- tipo `onedrive`; `client_id` e `client_secret` em branco (ver 6.3 se o tenant exigir);
- região `global`; não editar a configuração avançada;
- à pergunta sobre usar o navegador para autenticar, responda `n` e cole o token copiado;
- na escolha do drive, siga 6.2;
- confirme e saia.

### 6.2 Qual drive escolher

A pasta `<Empresa> Financeiro/CONTAS A PAGAR` está no OneDrive de `<conta-admin>@<dominio>`. Há dois caminhos:

1. **Autorizar com a própria `<conta-admin>`:** escolha "OneDrive Personal or Business". O destino é o caminho da pasta a partir da raiz desse OneDrive. É o caminho mais simples, mas o token dá acesso a todo o OneDrive da conta.
2. **Autorizar com outra conta, que recebeu a pasta compartilhada com permissão de edição:** escolha informar o identificador do drive (`drive_id`) do OneDrive de `<conta-admin>`, que o próprio `rclone config` ajuda a encontrar pela busca de sites ou pelos itens compartilhados. O destino passa a ser relativo a esse drive. O acesso fica restrito ao que foi compartilhado com a conta usada.

Confira o acesso listando a pasta:

```bash
rclone lsf "onedrive-financeiro:<Empresa> Financeiro/CONTAS A PAGAR" | head
```

### 6.3 Tenant que exige consentimento do administrador

Se, ao autorizar, a Microsoft pedir aprovação do administrador, há duas saídas:

- o administrador do tenant concede o consentimento ao aplicativo do Rclone no Entra ID; ou
- o administrador registra um aplicativo próprio no Entra ID, com as permissões delegadas `Files.ReadWrite` e `offline_access` e a URI de redirecionamento `http://localhost:53682/`, e informa o `client_id` e o `client_secret` gerados. Nesse caso, use `rclone authorize "onedrive" <client_id> <client_secret>` na máquina com navegador e informe os mesmos valores no `rclone config` da VPS.

## 7. Arquivo `.env`

```bash
cd /opt/email-nf-onedrive
cp app/.env.example .env
chmod 600 .env
nano .env
```

Preencha, no mínimo:

| Variável | Conteúdo |
|----------|----------|
| `EMAIL1` | endereço da primeira caixa |
| `SENHA_EMAIL1` | a senha de app da seção 5, sem espaços |
| `PASTA_EMAIL1` | pasta ou marcador monitorado; `INBOX` se omitida |
| `RCLONE_REMOTE` | o nome do remote da seção 6, sem os dois-pontos |
| `DESTINO_ONEDRIVE` | a pasta de destino, relativa ao remote |
| `DATA_INICIAL` | primeira data considerada, `AAAA-MM-DD`; uma data antiga envia todo o histórico |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | seção 8; sem elas, as falhas ficam só no log |

Cada caixa pode ter destino próprio (`DESTINO_ONEDRIVE1`) e servidor próprio (`IMAP_HOST_EMAIL1`; padrão `imap.gmail.com`).

Valide sem acessar a rede:

```bash
.venv/bin/email-nf-onedrive --home /opt/email-nf-onedrive verificar-config
```

Esperado: uma linha `1 · <endereço> · INBOX · <destino> · senha ****` por caixa e código de saída 0. Erros aparecem um por linha, no formato `<escopo>: <variável> <problema>`. O `.env` nunca deve ser versionado nem copiado para fora da VPS.

## 8. Bot do Telegram

1. No Telegram, converse com `@BotFather`, envie `/newbot` e escolha nome e usuário. O BotFather devolve o token (`123456789:AA...`).
2. Envie qualquer mensagem ao bot recém-criado, a partir da conta que vai receber os avisos (ou adicione o bot a um grupo e escreva no grupo).
3. Descubra o `chat_id`, com um espaço no início da linha para o comando não ficar no histórico do shell:

   ```bash
    curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates"
   ```

   O número em `"chat":{"id":...}` é o `TELEGRAM_CHAT_ID` (negativo, no caso de grupo).
4. Grave as duas variáveis no `.env` e rode `verificar-config`: a linha "avisos pelo Telegram: ativos" confirma.

## 9. Testes antes do agendamento

```bash
cd /opt/email-nf-onedrive
.venv/bin/email-nf-onedrive testar-onedrive
.venv/bin/email-nf-onedrive executar --simular
tail -30 var/log/email-nf-onedrive.log
```

- `testar-onedrive` grava, confere e apaga um arquivo de teste em cada destino. Esperado: `OneDrive: escrita confirmada em <destino>`.
- `executar --simular` lê as caixas e mostra no log o que seria enviado ("simulação: enviaria ...") e o que ficaria retido, sem enviar, sem gravar o registro e sem avisar. Confira se algum documento legítimo ficaria retido; se ficar, ver seção 13.

Depois, uma execução real: `.venv/bin/email-nf-onedrive executar; echo $?`. O código esperado é `0`, e os arquivos devem aparecer no OneDrive.

## 10. Agendamento com `cron`

Como `email-nf`, `crontab -e` e acrescente:

```
*/30 * * * * cd /opt/email-nf-onedrive && ./.venv/bin/email-nf-onedrive executar >/dev/null 2>&1
```

A saída é descartada porque tudo vai para o log. Execuções sobrepostas são impedidas pela própria ferramenta: se uma execução ainda estiver em andamento, a seguinte termina em menos de 1 segundo. Depois de uma hora, o log deve ter duas linhas `resumo:`.

## 11. Operação do dia a dia

### 11.1 Onde fica cada coisa

| Caminho | Conteúdo |
|---------|----------|
| `.env` | configuração e credenciais (permissão 600) |
| `var/log/email-nf-onedrive.log` | log do dia; os 29 dias anteriores ficam em arquivos com a data no nome |
| `var/registro.sqlite3` | registro dos anexos já processados; **faça backup**, ele impede reenvios |
| `var/execucao.lock` | existe só durante uma execução |
| `var/trabalho/` | anexos em trânsito; vazio fora das execuções |

### 11.2 Como ler o log

Cada linha tem data e hora, nível (`INFO`, `WARNING`, `ERROR`), a caixa quando se aplica e a mensagem:

```
2026-09-18T12:00:04-03:00 INFO [caixa 1] enviado: ACME - FORNECEDOR - BOLETO.pdf -> <Empresa> Financeiro/CONTAS A PAGAR (1.2 s)
2026-09-18T12:00:05-03:00 INFO resumo: 1 caixa, 1 extraídos, 1 enviados, 0 falhas, 5 s (desde a execução anterior: 30 min)
```

Consultas úteis:

```bash
grep ' resumo: ' var/log/email-nf-onedrive.log | tail          # uma linha por execução
grep -E ' (ERROR|WARNING) ' var/log/email-nf-onedrive.log         # problemas
grep 'retido para revisão' var/log/email-nf-onedrive.log         # documentos a revisar
grep -E 'possível documento sem anexo|anexo compactado' var/log/email-nf-onedrive.log
```

O código de saída da execução segue a regra: `0` tudo certo; `1` falha parcial (uma caixa ou um envio falhou, as demais seguiram); `2` erro de configuração ou falha total. Toda execução com código 1 ou 2 gera aviso no Telegram, repetido no máximo a cada 6 horas enquanto a mesma causa persistir; quando o problema some, chega uma mensagem "recuperado".

### 11.3 Revisão dos retidos

Anexos retidos **não** são guardados pela ferramenta: ela registra só remetente, assunto, data e nome do arquivo. Para listar os pendentes de revisão:

```bash
sqlite3 -header -column var/registro.sqlite3 \
  "select data_mensagem, caixa_indice, remetente, assunto, nome_original from anexos where estado = 'retido' order by data_mensagem"
```

Abra a mensagem no Gmail e, se for documento a pagar, salve o anexo manualmente na pasta. Se o mesmo tipo de documento ficar retido com frequência, ver seção 13.

Mensagens com palavra-chave no assunto e sem anexo (por exemplo, NFS-e disponível só por link) e anexos `.zip` ou `.rar` aparecem no log e também exigem tratamento manual.

### 11.4 Envios que falharam

```bash
sqlite3 -header -column var/registro.sqlite3 \
  "select id, nome_original, tentativas_envio, ultimo_erro from anexos where estado = 'falha-envio'"
```

Esses anexos são retentados automaticamente a cada execução; depois de 5 tentativas, o aviso no Telegram cita o anexo.

## 12. Acrescentar uma caixa

1. Gere a senha de app da nova conta (seção 5).
2. No `.env`, acrescente o próximo índice livre: `EMAIL2`, `SENHA_EMAIL2` e, se preciso, `PASTA_EMAIL2`, `DESTINO_ONEDRIVE2` e `IMAP_HOST_EMAIL2`. Lacunas na numeração são aceitas.
3. Rode `verificar-config`. Uma caixa incompleta é ignorada com aviso, sem derrubar as demais.
4. Rode `executar --simular`. A nova caixa começa pela `DATA_INICIAL`; se ela for antiga, todo o histórico dessa caixa será enviado na primeira execução.

Para desativar uma caixa, apague ou comente as linhas dela. O histórico no registro é mantido.

## 13. Ajustes que exigem alteração de código

- **Palavras-chave** que identificam documentos: `PALAVRAS_CHAVE` em `app/src/email_nf_onedrive/coleta/classificacao.py`.
- **Convenção de nomes** dos arquivos (`<EMPRESA> - <FORNECEDOR> [NF <n>] - <REF|BOLETO>.<ext>`, o padrão apurado na pasta em `docs/onedrive/estrutura-contas-a-pagar.md`): `app/src/email_nf_onedrive/envio/nomeacao.py`. O rótulo da empresa vem de `EMPRESA_EMAIL<n>` no `.env`.

Depois de alterar, reinstale (`.venv/bin/pip install ./app`) e rode `executar --simular`.

## 14. Renovação de credenciais

| Sintoma no aviso ou no log | Causa provável | O que fazer |
|----------------------------|----------------|-------------|
| `caixa N: autenticação recusada` | senha de app revogada, troca de senha da conta ou IMAP desativado | gere nova senha de app (seção 5), atualize `SENHA_EMAILN` e rode `verificar-config` |
| `OneDrive: reautorize o remote` | token da Microsoft expirado ou revogado (troca de senha, ação do administrador, longa inatividade) | refaça 6.1: `rclone authorize "onedrive"` na máquina com navegador e, na VPS, `rclone config`, edite o remote e cole o novo token; confirme com `testar-onedrive` |
| `acesso negado ... (403)` | a pasta deixou de estar compartilhada com permissão de edição | peça à `<conta-admin>` que restaure o compartilhamento |
| `destino não encontrado` | a pasta foi renomeada ou movida | corrija `DESTINO_ONEDRIVE`; a ferramenta nunca cria a pasta |
| aviso no Telegram deixou de chegar | token do bot revogado no BotFather ou bot removido do grupo | gere novo token com `/revoke` no BotFather e atualize `TELEGRAM_BOT_TOKEN` |

Depois de trocar qualquer credencial, a próxima execução com sucesso envia a mensagem de recuperação.

## 15. Situações especiais

- **VPS desligada por horas:** na volta, a busca recua até a última mensagem processada, e o resumo informa o intervalo desde a execução anterior. Nada precisa ser feito.
- **Disco cheio:** a execução termina com código 2 e aviso "disco cheio". Libere espaço; os anexos pendentes são retomados.
- **Registro corrompido:** a execução para com código 2 e aviso sobre `var/registro.sqlite3`. Restaure o backup. Sem backup, mova o arquivo para outro nome: a ferramenta cria um registro novo e reconhece os arquivos que já estão no OneDrive com o mesmo conteúdo, sem duplicá-los, mas os retidos voltam a aparecer no log uma vez.
- **Trava presa:** uma trava com mais de 25 minutos, ou de processo que não existe mais, é removida automaticamente, com a linha "trava abandonada removida" no log.
