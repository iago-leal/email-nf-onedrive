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

Há uma alternativa que dispensa a senha de app: o acesso por **OAuth 2.0**, com um projeto próprio no Google Cloud (seção 16). Os dois modos convivem na mesma instalação, caixa a caixa.

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
| `SENHA_EMAIL1` | a senha de app da seção 5, sem espaços; dispensada se a caixa usar OAuth (seção 16) |
| `PASTA_EMAIL1` | pasta ou marcador monitorado; `INBOX` se omitida |
| `RCLONE_REMOTE` | o nome do remote da seção 6, sem os dois-pontos |
| `DESTINO_ONEDRIVE` | a pasta de destino, relativa ao remote; cada documento vai para `NOTAS E BOLETOS POR VENCIMENTO/DIA <d>/202X-<mm>/` dentro dela, pelo vencimento, ou fica na raiz quando o vencimento não é identificado |
| `DATA_INICIAL` | primeira data considerada, `AAAA-MM-DD`; uma data antiga envia todo o histórico |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | seção 8; sem elas, as falhas ficam só no log |

Cada caixa pode ter destino próprio (`DESTINO_ONEDRIVE1`) e servidor próprio (`IMAP_HOST_EMAIL1`; padrão `imap.gmail.com`).

Valide sem acessar a rede:

```bash
.venv/bin/email-nf-onedrive --home /opt/email-nf-onedrive verificar-config
```

Esperado: uma linha `1 · <endereço> · INBOX · <destino> · senha ****` por caixa (nas caixas em OAuth, o final é `oauth (autorizada)` ou `oauth (sem autorização)`) e código de saída 0. Erros aparecem um por linha, no formato `<escopo>: <variável> <problema>`. O `.env` nunca deve ser versionado nem copiado para fora da VPS.

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
.venv/bin/email-nf-onedrive testar-caixa
.venv/bin/email-nf-onedrive testar-onedrive
.venv/bin/email-nf-onedrive executar --simular
tail -30 var/log/email-nf-onedrive.log
```

- `testar-caixa` autentica em cada caixa, abre a pasta em somente leitura e encerra, sem ler mensagens. Esperado: `caixa N: acesso confirmado (senha)` ou `(oauth)`. Com um índice (`testar-caixa 2`), testa só aquela caixa.
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
| `autorizacoes/` | autorização OAuth de cada caixa, um `.json` por endereço (diretório 700, arquivos 600); **faça backup** por canal cifrado e nunca versione (seção 16) |
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

1. Gere a senha de app da nova conta (seção 5) ou, para OAuth, siga a seção 16.3 com `AUTH_EMAIL2=oauth`.
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
| `caixa N: autorização OAuth ...`, `serviço de autorização do Google indisponível` ou `credenciais do cliente OAuth recusadas` | falha do acesso por OAuth | ver a tabela da seção 16.6 |
| `OneDrive: reautorize o remote` | token da Microsoft expirado ou revogado (troca de senha, ação do administrador, longa inatividade) | refaça 6.1: `rclone authorize "onedrive"` na máquina com navegador e, na VPS, `rclone config`, edite o remote e cole o novo token; confirme com `testar-onedrive` |
| `acesso negado ... (403)` | a pasta deixou de estar compartilhada com permissão de edição | peça à `<conta-admin>` que restaure o compartilhamento |
| `destino não encontrado` | a pasta, ou uma subpasta `DIA <d>/202X-<mm>` da grade por vencimento, foi renomeada, movida ou não existe | corrija `DESTINO_ONEDRIVE` ou recrie a subpasta; a ferramenta nunca cria pastas |
| aviso no Telegram deixou de chegar | token do bot revogado no BotFather ou bot removido do grupo | gere novo token com `/revoke` no BotFather e atualize `TELEGRAM_BOT_TOKEN` |

Depois de trocar qualquer credencial, a próxima execução com sucesso envia a mensagem de recuperação.

## 15. Situações especiais

- **VPS desligada por horas:** na volta, a busca recua até a última mensagem processada, e o resumo informa o intervalo desde a execução anterior. Nada precisa ser feito.
- **Disco cheio:** a execução termina com código 2 e aviso "disco cheio". Libere espaço; os anexos pendentes são retomados.
- **Registro corrompido:** a execução para com código 2 e aviso sobre `var/registro.sqlite3`. Restaure o backup. Sem backup, mova o arquivo para outro nome: a ferramenta cria um registro novo e reconhece os arquivos que já estão no OneDrive com o mesmo conteúdo, sem duplicá-los, mas os retidos voltam a aparecer no log uma vez.
- **Trava presa:** uma trava com mais de 25 minutos, ou de processo que não existe mais, é removida automaticamente, com a linha "trava abandonada removida" no log.

## 16. Acesso por OAuth 2.0 (alternativa à senha de app)

Em vez da senha de app, uma caixa pode ser lida com uma **autorização OAuth** concedida a um aplicativo seu, registrado no Google Cloud. A autorização é dada uma vez, no navegador, e fica gravada num arquivo; a cada execução a ferramenta a troca por uma credencial temporária, que vive só em memória. O modo é escolhido por caixa, com `AUTH_EMAIL<n>=oauth`; sem essa variável, a caixa continua em `senha`, e nada muda.

Dois pontos para ter claros antes de começar:

- **O Google só oferece um escopo para IMAP, e ele é amplo.** A tela de consentimento fala em "ler, escrever, enviar e excluir permanentemente" os e-mails. A ferramenta continua usando apenas a leitura descrita na seção 1: a lista de comandos IMAP que ela emite é fechada e vigiada por teste. O titular da caixa deve saber disso antes (seção 16.2).
- **Não há custo.** O projeto no Google Cloud é criado sem conta de faturamento; recuse qualquer oferta de avaliação gratuita que peça cartão.

### 16.1 Projeto no Google Cloud (uma vez)

Os nomes dos menus mudam com alguma frequência; procure pelo sentido. Use uma conta Google do operador, pessoal ou do Google Workspace. Com conta do Workspace, o projeto nasce dentro da organização do domínio e fica sujeito às políticas dela, o que pesa na entrega ao cliente (seção 16.8).

1. Crie o projeto sem conta de faturamento. O identificador é único entre todos os projetos do Google Cloud, e não só entre os seus; use um sufixo, como `email-nf-onedrive-<cliente>`. Pelo terminal, com o [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) autenticado na conta do operador (`gcloud auth list` mostra qual):

   ```bash
   gcloud projects create email-nf-onedrive-<cliente> --name=email-nf-onedrive
   ```

   Ou pelo console, em <https://console.cloud.google.com>, no seletor de projetos › **Novo projeto**. Os passos seguintes só existem no console: o Google não oferece linha de comando nem API pública para a tela de consentimento e para clientes do tipo computador.
2. Abra a **Google Auth Platform** já no projeto: `https://console.cloud.google.com/auth/overview?project=<identificador>&authuser=<conta do operador>`. O `authuser` importa quando o navegador tem mais de uma conta Google: sem ele, o console abre na conta padrão, que não enxerga o projeto. Se a página disser que "não pode ser visualizada para organizações", o console está no nível da organização, e não do projeto: no seletor do topo, abra a aba **Todos** (o projeto criado pelo terminal não aparece entre os recentes) e selecione-o. O topo deve mostrar o nome do projeto. Em consoles antigos, o caminho é "APIs e serviços" › "Tela de permissão OAuth".
3. Clique em **Vamos começar**. O assistente tem quatro etapas:
   - **Informações do app:** nome `email-nf-onedrive` e o e-mail de suporte do operador. Não é preciso logotipo nem domínio.
   - **Público:** marque **Externo**. Em projeto de organização, o console oferece também **Interno**, que restringe o consentimento às contas do domínio da organização; as caixas dos clientes estão em outros domínios e não conseguiriam autorizar. O texto do Externo avisa que o app começa em modo de testes, o que o passo 4 resolve.
   - **Dados de contato:** o e-mail do operador.
   - **Concluir:** aceite a política de dados de usuário e clique em **Criar**. Esperado: "Configuração do OAuth criada".
4. Em **Branding**, preencha também a **página inicial do aplicativo**, a **política de privacidade** e os **domínios autorizados**: sem os dois endereços, o botão **Publicar app** do passo seguinte fica inativo. Servem o repositório e a política que acompanha a ferramenta:

   - página inicial: `https://github.com/iago-leal/email-nf-onedrive`
   - política de privacidade: `https://github.com/iago-leal/email-nf-onedrive/blob/main/docs/politica-de-privacidade.md`
   - domínio autorizado: `github.com`

   A política (`docs/politica-de-privacidade.md`) indica o contato do operador; numa instalação de outro operador, publique uma cópia com o contato dele e use o endereço dessa cópia.
5. Em **Público-alvo**, no bloco **Status de publicação**, clique em **Publicar app** e confirme, para que o estado fique **Em produção**. Não peça a verificação do aplicativo, e não use usuários de teste como atalho. Este passo é obrigatório: em modo de teste, só os usuários de teste listados conseguem consentir, e toda autorização caduca em 7 dias. Sem ele, o consentimento para em "Erro 403: access_denied", com a mensagem de que o app "está em fase de testes".
6. Em **Acesso a dados** › **Adicionar ou remover escopos**, cole `https://mail.google.com/` no campo de escopo manual, adicione e clique em **Salvar**. O console o classifica como escopo restrito; é esperado.
7. Em **Clientes** › **Criar cliente**, escolha o tipo **App para computador**, com o nome `email-nf-onedrive`. Não use **Aplicativo da Web**: ele exige endereço de retorno fixo, e o `autorizar-caixa` recebe a resposta em `127.0.0.1` com porta variável. Na janela que se abre, copie o **ID do cliente** e a **chave secreta**, ou baixe o JSON: o console só mostra a chave nesse momento, e perdê-la obriga a gerar outra. Grave os dois no `.env`, tanto na máquina do operador quanto na VPS:

   ```
   OAUTH_CLIENT_ID=<ID do cliente>
   OAUTH_CLIENT_SECRET=<chave secreta>
   ```

   O JSON baixado traz a chave em claro; apague-o depois de copiar os valores, e nunca o deixe dentro do repositório.
8. Não ative nenhuma API: o acesso é por IMAP, que não depende da API do Gmail.

Sem verificação, o Google limita o aplicativo a 100 contas e mostra um aviso na tela de consentimento (seção 16.3, passo 4). Para cinco caixas conhecidas, é o arranjo adequado: a verificação de escopo restrito exige auditoria paga.

**Google Workspace com restrição a aplicativos de terceiros.** Se o consentimento parar em "acesso bloqueado pelo administrador", o administrador do domínio precisa marcar o aplicativo como confiável: Admin › Segurança › Acesso e controle de dados › Controles de API › Gerenciar acesso de apps de terceiros › Adicionar app › ID do cliente OAuth, com acesso **Confiável**. Se isso não for possível, mantenha a caixa em `senha`, com senha de app (seção 5).

### 16.2 Comunicado ao titular da caixa

O consentimento é dado pelo operador, que entra na conta com a senha recebida do cliente. Por ser ato praticado em nome do titular, avise-o **antes**. Texto pronto para enviar:

> Olá. Para arquivar automaticamente as notas fiscais e os boletos que chegam ao seu e-mail, vou autorizar a nossa ferramenta a ler a sua caixa. Farei isso entrando na sua conta uma única vez, com a senha que você me passou, e depois a senha deixa de ficar guardada conosco.
> Na autorização, o Google descreve o acesso como "ler, escrever, enviar e excluir e-mails", porque é a única permissão que ele oferece para esse tipo de leitura. A ferramenta só lê: não marca mensagens como lidas, não move, não apaga e não envia nada.
> Você pode conferir e cancelar esse acesso quando quiser, em <https://myaccount.google.com/permissions>, no item "email-nf-onedrive".
> Se você trocar a senha da conta, o Google cancela a autorização, e eu precisarei refazê-la; me avise quando isso acontecer.

### 16.3 Autorizar uma caixa (na máquina do operador)

O consentimento exige navegador; por isso é feito na máquina do operador, com uma instalação da ferramenta e o mesmo `.env` da VPS.

1. No `.env`, defina `AUTH_EMAIL<n>=oauth` para a caixa e rode `verificar-config`. Esperado: a caixa termina em `oauth (sem autorização)` e aparece a linha `cliente OAuth: configurado`.
2. Num terminal em primeiro plano, rode:

   ```bash
   email-nf-onedrive autorizar-caixa 2
   ```

   O comando imprime o endereço de consentimento e fica aguardando a volta do navegador. Não o mande para segundo plano: o endereço deixa de aparecer na tela, e o comando parece travado.

3. Copie o endereço impresso e abra-o numa **janela anônima** do navegador, nova a cada caixa. Não use a janela normal: ela está com a sua conta, e o consentimento sairia para a conta errada; nem reaproveite a anônima da caixa anterior, que ainda está conectada àquela conta. Entre com o endereço e a senha da caixa.
4. Na tela **"O Google não verificou este app"**, clique em **Avançado** e em **Acessar email-nf-onedrive (não seguro)**. O aviso é esperado: o aplicativo é seu e não passou pela verificação pública.
5. Na tela "email-nf-onedrive quer acessar sua Conta do Google", **marque a caixa do Gmail** ("Ler, escrever, enviar e excluir permanentemente…") ou clique em **Selecionar tudo**: o Google apresenta as permissões desmarcadas. Só então clique em **Continuar**. A janela mostra "Você pode fechar esta janela", e o terminal, `caixa 2: autorizada · <endereço>` e o caminho do arquivo gravado.
6. Confirme o acesso: `email-nf-onedrive testar-caixa 2`. Esperado: `caixa 2: acesso confirmado (oauth)`.

O comando espera o consentimento por até 5 minutos e sai com código 0 quando grava a autorização, ou 2 em qualquer recusa, sem gravar nada:

| Mensagem | O que aconteceu | O que fazer |
|----------|-----------------|-------------|
| `conta autorizada difere de EMAIL2` | o consentimento foi dado com outra conta; a ferramenta já o revogou | repita na janela anônima, com a conta certa |
| `caixa 2: consentimento negado` | alguém clicou em "Cancelar" | repita |
| `caixa 2: tempo esgotado à espera do consentimento` | o endereço não foi aberto em 5 min | repita |
| `caixa 2: acesso ao correio não concedido` | a caixa do Gmail ficou desmarcada na tela de permissões | repita, marcando-a antes de continuar |
| `caixa 2: o Google não devolveu autorização durável` | resposta incompleta do Google | repita; se persistir, remova o acesso em <https://myaccount.google.com/permissions> e repita |
| `caixa 2 não está em modo oauth` | falta `AUTH_EMAIL2=oauth` no `.env` | corrija o `.env` |
| `credenciais do cliente OAuth ausentes` | falta `OAUTH_CLIENT_ID` ou `OAUTH_CLIENT_SECRET` | seção 16.1, passo 7 |
| `não foi possível revogar; revogue em myaccount.google.com/permissions` | a revogação automática falhou | remova o acesso à mão, na conta em que o consentimento foi dado |

**Se o Google pedir confirmação em outro aparelho ou código por SMS**, pare: essa caixa precisa do titular presente. É o caso de toda conta com verificação em duas etapas. Faça os passos 2 a 5 com o titular ao lado, ou numa chamada, com ele confirmando o desafio no próprio celular. Convém descobrir antes quais caixas têm a verificação ativa e agendar todas numa única visita.

Se o `AUTHENTICATE` for recusado logo depois de uma autorização bem-sucedida (`caixa N: falhou (autorização recusada...)` no `testar-caixa`), o mais provável é o **IMAP desativado** na conta ou no domínio (seção 5, passo 3).

### 16.4 Levar as autorizações para a VPS

As autorizações não dependem da máquina em que foram dadas. Copie o diretório por canal cifrado e confira as permissões:

```bash
# na máquina do operador; o usuário de serviço não aceita login, então a cópia passa pelo seu usuário
scp -rp autorizacoes/ <seu-usuario>@<vps>:autorizacoes-novas

# na VPS
sudo mkdir -p -m 700 /opt/email-nf-onedrive/autorizacoes
sudo cp ~/autorizacoes-novas/*.json /opt/email-nf-onedrive/autorizacoes/
rm -r ~/autorizacoes-novas
sudo chown -R email-nf: /opt/email-nf-onedrive/autorizacoes
sudo chmod 700 /opt/email-nf-onedrive/autorizacoes
sudo chmod 600 /opt/email-nf-onedrive/autorizacoes/*.json
sudo -iu email-nf
.venv/bin/email-nf-onedrive testar-caixa
```

Esperado: `acesso confirmado (oauth)` em cada caixa autorizada, sem nenhum passo de navegador. O diretório padrão é `autorizacoes/`, ao lado do `.env`; `DIR_AUTORIZACOES` aponta outro, absoluto ou relativo à instalação. Quem usa um diretório próprio responde por mantê-lo fora do versionamento. Permissão mais aberta que 700 no diretório ou 600 nos arquivos gera alerta no `verificar-config` e no log.

Esses arquivos dão acesso às caixas: trate-os como o `.env`. Inclua-os no backup, sempre cifrado, e nunca os envie por e-mail ou mensageiro.

### 16.5 Passar uma instalação existente para OAuth

A troca é por caixa e reversível. O registro de processados usa o endereço, de modo que mudar o modo **não** reenvia documento já arquivado.

1. Atualize a ferramenta na máquina do operador e na VPS e rode `verificar-config`: nada deve mudar, com todas as caixas em `senha ****`.
2. Crie o projeto (16.1) e preencha `OAUTH_CLIENT_ID` e `OAUTH_CLIENT_SECRET` nos dois `.env`.
3. Para cada caixa: envie o comunicado (16.2), defina `AUTH_EMAIL<n>=oauth`, rode `autorizar-caixa <n>` e `testar-caixa <n>` (16.3).
4. Copie as autorizações para a VPS e rode `testar-caixa` lá (16.4).
5. **Retire `SENHA_EMAIL<n>` das caixas autorizadas**, nos dois `.env`: a senha de terceiro não deve continuar guardada. Enquanto ela estiver lá, o `verificar-config` e o log mostram `alerta: SENHA_EMAILn presente em caixa oauth; retire-a do .env`. Por fim, rode `executar --simular` antes de religar o `cron`.

Para voltar atrás numa caixa, remova `AUTH_EMAIL<n>` e reponha a senha de app.

### 16.6 Avisos de autorização

A linha de resumo do log ganha o trecho `k de autorização` quando alguma caixa falha por estes motivos. As demais caixas seguem normalmente.

| Aviso | Natureza | O que fazer |
|-------|----------|-------------|
| `caixa N: autorização OAuth ausente (rode autorizar-caixa N)` | permanente | o arquivo da caixa não está no diretório de autorizações: autorize (16.3) ou copie-o (16.4) |
| `caixa N: autorização OAuth recusada (rode autorizar-caixa N)` | permanente | o titular revogou o acesso, trocou a senha da conta, ou a autorização ficou 6 meses sem uso: refaça 16.3 e 16.4 |
| `caixa N: autorização OAuth inválida: ... (rode autorizar-caixa N)` | permanente | arquivo ilegível, de outro endereço ou emitido para outro cliente OAuth: refaça 16.3 e 16.4 |
| `caixa N: autorização OAuth recusada pelo servidor de e-mail` | permanente | confira se o IMAP está ativo na conta (seção 5, passo 3); se estiver, refaça 16.3 |
| `caixa N: serviço de autorização do Google indisponível` | transitória | nada: a próxima execução tenta de novo, e a autorização gravada não é tocada |
| `credenciais do cliente OAuth recusadas pelo Google` | permanente, vale para todas as caixas em OAuth | confira `OAUTH_CLIENT_ID` e `OAUTH_CLIENT_SECRET` no `.env` contra o cliente do Google Cloud (16.1, passo 7) |

A ferramenta nunca apaga nem altera um arquivo de autorização durante a execução; só o `autorizar-caixa` grava.

### 16.7 Revogar o acesso

- **Uma caixa:** na conta do titular, em <https://myaccount.google.com/permissions>, remova "email-nf-onedrive". Depois apague o arquivo `autorizacoes/<endereço>.json` na VPS e na máquina do operador e retire a caixa do `.env` (ou volte-a para `senha`).
- **Todas de uma vez**, por exemplo se a VPS ou o `.env` vazarem: no Google Cloud, em **Clientes**, gere nova chave secreta para o cliente OAuth e exclua a antiga. As autorizações gravadas deixam de servir a quem só tiver a chave antiga. Atualize `OAUTH_CLIENT_SECRET` nos dois `.env` e rode `testar-caixa`. Em caso de vazamento, peça também a cada titular que remova o acesso na própria conta e refaça as autorizações (16.3).

### 16.8 Entrega do projeto ao cliente

O projeto nasce na conta do operador e pode mudar de dono sem reautorizar nenhuma caixa:

1. No Google Cloud, em **IAM e administrador** › **IAM**, conceda à conta do cliente o papel **Proprietário**.
2. O cliente aceita o convite que chega por e-mail.
3. Confirmado o aceite, o cliente (ou você) remove a conta do operador da lista.
4. Em **Google Auth Platform** › **Branding**, troque o e-mail de suporte pelo do cliente.

**Projeto dentro de uma organização.** Se o projeto nasceu numa conta do Google Workspace (seção 16.1), ele pertence à organização do domínio do operador, e a troca de proprietário não o tira de lá. Há duas saídas. Na primeira, o cliente recebe o papel de proprietário e o projeto continua na organização do operador; a política de compartilhamento restrito ao domínio, se estiver ativa, impede o convite a uma conta de fora, e o administrador precisa abrir exceção. Na segunda, o projeto é movido para a organização do cliente, o que exige permissão de administrador de projetos nas duas organizações. Se nenhuma das duas for viável, resta a alternativa do fim desta seção.

O ID e a chave secreta do cliente OAuth não mudam, e as autorizações seguem válidas. Confira com `testar-caixa` na VPS. Se a transferência por convite não estiver disponível para o projeto, a alternativa é o cliente criar um projeto novo (16.1) e as caixas serem autorizadas de novo (16.3 e 16.4).
