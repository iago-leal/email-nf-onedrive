# Roadmap: MVP de arquivamento automático de NFs e boletos do e-mail no OneDrive

> Identificador: `001-mvp-email-nf-onedrive`
> Data: `2026-09-18`
> Requirements: `_reversa_forward/001-mvp-email-nf-onedrive/requirements.md`
> Confidência: 🟢 CONFIRMADO, 🟡 INFERIDO, 🔴 LACUNA
>
> ⚠️ **Plano com premissa aberta.** A convenção de nomes e subpastas (L-03) ainda não foi decidida. Este plano adota a convenção provisória do RF-10 e a isola num único módulo, para que a troca não afete o restante do envio. Ver seção 4.

## 1. Resumo da abordagem

Projeto greenfield: o "legado" é o conjunto de specs do `/reversa-new` em `_reversa_sdd/sdd/`, e este roadmap é o delta que as materializa em código. A ferramenta será um pacote Python (3.11 ou superior), instalado num ambiente virtual na VPS, com o ponto de entrada `email-nf-onedrive` e três subcomandos. Cada spec vira um subpacote com fronteira explícita: `configuracao` (spec `configuracao-caixas`), `coleta` (spec `coleta-email`), `envio` (spec `envio-onedrive`) e `execucao` (spec `execucao-monitoramento`). O código usa a biblioteca padrão para o que ela cobre bem: IMAP, MIME, SQLite, XML, hash, log com rotação e HTTP para o Telegram. A única dependência de execução é `python-dotenv`, e o Rclone é chamado como processo externo, por uma fachada que só admite os subcomandos necessários. O estado persistente (registro de processados e estado dos avisos) fica num arquivo SQLite local. O agendamento é uma linha de `cron` a cada 30 minutos, e o sistema ganha duas travas de segurança: uma trava de execução com expiração de 25 minutos e um limite de duração da própria execução. Os testes usam dublês para o IMAP e o Telegram, e o Rclone real apontado para um diretório local, o que exercita a fachada sem depender do OneDrive.

## 2. Princípios aplicados

Não existe `.reversa/principles.md` neste projeto; não há princípio formal a verificar. As regras de negócio RN-01 a RN-09 do `requirements.md` funcionam, na prática, como invariantes deste plano e estão cobertas pelas decisões abaixo.

| Princípio | Como a feature se relaciona | Status |
|-----------|------------------------------|--------|
| n/a | Nenhum princípio registrado. Recomenda-se rodar `/reversa-principles` antes da segunda feature, promovendo RN-01 (caixa intocada) e RN-02 (pasta só recebe acréscimos) a princípios. | n/a |

## 3. Decisões técnicas

| ID | Decisão | Justificativa | Alternativas descartadas | Confidência |
|----|---------|----------------|--------------------------|-------------|
| D-01 | Pacote `email_nf_onedrive` em layout `src/`, com `pyproject.toml` e *console script* `email-nf-onedrive`; subcomandos via `argparse`. | Python é restrição do PRD; `argparse` evita dependência e basta para três subcomandos. | Click ou Typer (dependência extra); script solto sem empacotamento (dificulta a instalação pelo guia). | 🟢 |
| D-02 | Um subpacote por spec: `configuracao`, `coleta`, `envio`, `execucao`, mais `registro` (SQLite) compartilhado entre `coleta` e `envio`. | Espelha a organização das specs escolhida (`granularity = module`) e facilita a rastreabilidade RF → código. | Módulo único; organização por camada técnica. | 🟢 |
| D-03 | Leitura do `.env` com `dotenv_values` (sem injetar em `os.environ`), do diretório de instalação (`EMAIL_NF_HOME` ou diretório corrente). | Evita vazar segredos para subprocessos, como o Rclone. `python-dotenv` é sugerido pela spec `configuracao-caixas` (seção 10). | Leitor próprio (reimplementar aspas e escapes); `os.environ` puro (exigiria exportar variáveis no cron). | 🟢 |
| D-04 | Filtro de log que substitui por `****` todo valor de segredo carregado (senhas e token do Telegram), aplicado a todos os *handlers*, além da regra de nunca interpolar segredos. | Defesa em profundidade para RF-03: um erro de biblioteca que ecoe a senha não chega ao log nem ao aviso. | Confiar só na disciplina do código. | 🟢 |
| D-05 | IMAP com `imaplib.IMAP4_SSL` (porta 993, `timeout=60`), `select(pasta, readonly=True)` (equivale a `EXAMINE`), `SEARCH SINCE <data>` e `FETCH BODY.PEEK[]`. Nomes de pasta codificados em UTF-7 modificado (RFC 3501, seção 5.1.3) e entre aspas. | Garante RN-01 por construção; rótulos do Gmail com acento (ex.: `[Gmail]/Todos os e-mails`) exigem essa codificação. | Gmail API com OAuth (fora do MVP, spec `configuracao-caixas` NG-03); busca por UID (a spec `coleta-email` preferiu janela por data). | 🟢 |
| D-06 | Extração MIME com `email` (política `default`), percorrendo recursivamente as partes, inclusive `message/rfc822`; reconhecimento por extensão (`.pdf`, `.xml`) ou tipo (`application/pdf`, `application/xml`, `text/xml`). | Cobre CE RF-04 e EC-05 (a política `default` decodifica nomes `=?UTF-8?B?...?=`). | Biblioteca de terceiros para e-mail. | 🟢 |
| D-07 | Classificação: `nfe-xml` pela raiz `nfeProc` ou `NFe` no namespace `http://www.portalfiscal.inf.br/nfe`, lida com `iterparse` só até o primeiro elemento e com limite de 10 MB; `palavra-chave` pela lista do CE RF-06, comparada sobre texto sem acento e em minúsculas, **por fronteira de palavra**. | A fronteira evita falso positivo de `nf` em "info" ou "conforme". Ler só a raiz limita o custo e o risco de XML hostil. | Busca por substring (falsos positivos); `defusedxml` (dependência extra, desnecessária para ler só a raiz com o expat atual). | 🟡 |
| D-08 | Anexos `sem-classificacao` recebem o estado terminal `retido` no registro e uma linha de log única "retido para revisão"; não são enviados. | Resposta 1c da sessão de esclarecimentos (RN-03, RF-07). O estado terminal impede novo registro a cada execução. | Enviar para subpasta; não registrar (repetiria o log a cada execução). | 🟢 |
| D-09 | Registro de processados em SQLite (`var/registro.sqlite3`, permissão 600), com chave única (endereço da caixa em minúsculas, identificador da mensagem, SHA-256). | Transações atômicas e consulta da janela de busca (CE RF-03) sem carregar tudo em memória. Chave pelo **endereço**, e não pelo índice `<n>`: renumerar o `.env` não gera reenvio. | JSON em disco (sem atomicidade nem consulta); chave pelo índice da caixa, como na spec `coleta-email` seção 9 (frágil a renumeração). | 🟡 |
| D-10 | Fachada `envio/rclone.py` que executa `rclone` via `subprocess` com lista branca de subcomandos (`lsjson`, `copyto`, `hashsum`, `deletefile`, `lsf`) e recusa qualquer outro; `deletefile` só aceita o caminho do arquivo de teste do `testar-onedrive`. Toda chamada leva `timeout=120` e as flags `--immutable`, `--retries 3` e `--low-level-retries 10`. | Garante RN-02 por construção (spec `envio-onedrive` seção 12). `--immutable` é uma segunda barreira: o Rclone falha em vez de sobrescrever. | Microsoft Graph direto em Python (decision log da spec: Rclone é escolha do usuário); `rclone copy` de diretório (sem controle por arquivo). | 🟢 |
| D-11 | Antes de cada upload, `lsjson` do caminho final; se existir arquivo com mesmo tamanho e mesmo QuickXorHash (calculado localmente com `rclone hashsum quickxor`), o anexo é dado por `enviado`; se o conteúdo diferir, tenta os sufixos `_2`, `_3` etc. Após o `copyto`, novo `lsjson` confirma o tamanho. | Cobre EO RF-04 a RF-06 sem baixar arquivos; o OneDrive for Business expõe QuickXorHash, e o Rclone o calcula para arquivos locais. | Baixar o remoto para comparar (lento e desnecessário); confiar só no código de saída (EO decision log). | 🟡 |
| D-12 | Convenção de nomes isolada em `envio/nomeacao.py`, com uma única função pública `caminho_destino(anexo, destino) -> str`, que devolve subpasta e nome; a implementação inicial é a provisória do RF-10 (`AAAA-MM-DD_<remetente>_<nome-original>`, sem subpasta), seguida do saneamento de EO RF-02. | Premissa de L-03: a convenção definitiva só será conhecida após `rclone lsf` na pasta real. Isolar reduz a troca a um arquivo e seus testes. | Espalhar a formatação pelo envio. | 🟡 |
| D-13 | Pasta de trabalho por execução em `var/trabalho/<id-execucao>/`, permissão 700, **sempre** removida no fim da execução (`finally`), com ou sem falha. | Anexos com `falha-envio` são extraídos de novo da caixa na execução seguinte (CE fluxo A), então não é preciso guardá-los; minimiza dados fiscais na VPS (RN-07). | Manter os pendentes em disco até o envio (mais dados pessoais em repouso). | 🟡 |
| D-14 | Trava por arquivo `var/execucao.lock` criado com `O_CREAT \| O_EXCL`, contendo PID e horário; é considerada abandonada se tiver mais de 25 min **ou** se o PID não existir mais. A execução impõe a si própria um limite de 20 min (`signal.alarm`), abortando com código 2 e liberando a trava. | Cobre EM RF-03 e RF-04. O limite de 20 min garante que uma execução travada termine antes de a trava expirar, evitando dois ciclos simultâneos. | `fcntl.flock` puro (libera com a morte do processo, mas não trata processo travado); `flock(1)` na linha do cron (tira a regra do código). | 🟡 |
| D-15 | Log com `logging.handlers.TimedRotatingFileHandler` (`when="midnight"`, `backupCount=29`, portanto 30 arquivos no total), formato `AAAA-MM-DDTHH:MM:SS±HH:MM NIVEL [caixa n] mensagem`, em `var/log/`. Saída de terminal só para os subcomandos interativos. | EM RF-06 com retenção de 30 dias (resposta 2a). | `logrotate` do sistema (depende de configuração fora do projeto). | 🟢 |
| D-16 | Avisos pelo Telegram com `urllib.request` (POST em `sendMessage`, timeout de 15 s). O estado de supressão fica na tabela `avisos` do mesmo SQLite, por chave de causa (ex.: `caixa1:autenticacao`, `onedrive:token`, `anexo:<sha>:tentativas`). Aviso não entregue fica pendente e é reenviado na execução seguinte. | EM RF-07 a RF-09 e fluxo B, sem dependência HTTP extra. | Biblioteca de bot do Telegram (desnecessária para um único endpoint). | 🟢 |
| D-17 | Em `--simular`, o registro é aberto numa transação sempre desfeita (`ROLLBACK`), a fachada do Rclone só executa `lsjson` e nenhum aviso é enviado; o log diz o que seria enviado ou retido. | EM RF-10: nada persiste, mas o caminho de código é o mesmo da produção. | Ramo de código separado para a simulação (divergiria da produção). | 🟢 |
| D-18 | Testes com `pytest`: unidade para configuração, classificação, MIME, nomeação, janela de busca, trava e supressão de avisos; integração com IMAP simulado (classe dublê injetada) e **Rclone real contra um diretório local temporário**, que exercita `--immutable`, sufixos e confirmação de tamanho. | Testa a fachada do Rclone de verdade sem credenciais do OneDrive. | Mockar todo o Rclone (não pegaria erro de flag ou de parsing do `lsjson`). | 🟢 |
| D-19 | Instalação por `python -m venv` e `pip install .` em `/opt/email-nf-onedrive` (ou `~/email-nf-onedrive`), com usuário de serviço sem root; `cron` com `*/30 * * * *` chamando o binário do venv; guia em `docs/instalacao-e-operacao.md` e `.env.example` na raiz. | EM RF-12, RF-13 e NG-02 (sem contêiner). | Docker; `systemd timer` (válido, mas o usuário escolheu `cron`). | 🟢 |

## 4. Premissas

| Premissa | Origem (`requirements.md` seção) | Risco se errada |
|----------|----------------------------------|-----------------|
| ⚠️ **P-L03:** a convenção provisória `AAAA-MM-DD_<remetente>_<nome-original>`, sem subpastas, vale até o levantamento da pasta real com `rclone lsf`. O levantamento é a **primeira ação da fase de envio**, logo após configurar o remote, e fecha a L-03 antes de o código de nomeação ser congelado. | §10 Lacunas, L-03; §5 RF-10 | Médio: arquivos com nome fora do padrão da equipe. Contido por D-12 (troca restrita a `envio/nomeacao.py`); arquivos já enviados não são renomeados (RN-02). |
| A caixa 1 aceita IMAP com senha de app e a pasta monitorada é `INBOX`. | §10 P-01, P-02 | Alto para a operação, nulo para o código: `verificar-config` e a primeira execução revelam o problema; a correção é só no `.env`. |
| A conta que autorizar o Rclone tem edição na pasta de destino e o tenant permite o aplicativo do Rclone, ou um aplicativo próprio no Entra ID. | §10 P-04 | Alto: sem isso nada chega ao OneDrive. Validado pelo `testar-onedrive` antes da produção; ver `investigation.md` §4. |
| A lista de palavras-chave do CE RF-06 reconhece todas as NFs e todos os boletos reais. | §10 P-05; RN-03 | Alto após a resposta 1c: documento legítimo classificado como `sem-classificacao` não é enviado. Mitigado pela semana de `--simular`, que lista os retidos, e pelo log "retido para revisão". |

## 5. Delta arquitetural

Não existe `_reversa_sdd/architecture.md`; a referência são as specs do `/reversa-new`. Todos os componentes são novos.

| Componente | Arquivo de origem no legado | Tipo de mudança | Resumo |
|------------|------------------------------|-----------------|--------|
| `configuracao` | `_reversa_sdd/sdd/configuracao-caixas.md` | componente-novo | Lê `.env`, descobre `EMAIL<n>`, valida antes da rede e expõe `Configuracao` e `Caixa`; subcomando `verificar-config`. |
| `coleta` | `_reversa_sdd/sdd/coleta-email.md` | componente-novo | IMAP somente leitura, janela de busca, extração MIME, classificação; grava anexos na pasta de trabalho e no registro. |
| `envio` | `_reversa_sdd/sdd/envio-onedrive.md` | componente-novo | Nomeação isolada, fachada do Rclone com lista branca, envio sem sobrescrita, confirmação; subcomando `testar-onedrive`. |
| `execucao` | `_reversa_sdd/sdd/execucao-monitoramento.md` | componente-novo | CLI, trava, limite de duração, log com rotação, resumo, códigos de saída, avisos pelo Telegram. |
| `registro` | `_reversa_sdd/sdd/coleta-email.md#9. Modelo de Dados` | componente-novo | SQLite compartilhado: anexos, ocorrências já registradas e estado dos avisos. |
| Regra RN-03 (retenção de `sem-classificacao`) | `_reversa_sdd/sdd/coleta-email.md#6. Requisitos Funcionais` (RF-07) | regra-alterada | Spec previa enviar tudo; a feature retém os não reconhecidos. Convergir no `/reversa-sync`. |
| Chave do registro | `_reversa_sdd/sdd/coleta-email.md#9. Modelo de Dados` | regra-alterada | Chave pelo endereço da caixa, e não pelo índice (D-09). Convergir no `/reversa-sync`. |

Árvore de código prevista (fora das pastas do Reversa):

```
pyproject.toml
.env.example
README.md
docs/instalacao-e-operacao.md
src/email_nf_onedrive/
  __init__.py  __main__.py  cli.py  segredos.py
  configuracao/  (carregar.py, modelo.py)
  registro/      (banco.py, esquema.sql)
  coleta/        (imap.py, utf7.py, mime.py, classificacao.py, janela.py, coleta.py)
  envio/         (nomeacao.py, rclone.py, envio.py, teste_onedrive.py)
  execucao/      (ciclo.py, trava.py, logs.py, avisos.py, resumo.py)
tests/
  unidade/  integracao/  dados/ (e-mails .eml e XMLs de NF-e sintéticos, sem dados reais)
```

## 6. Delta no modelo de dados

- Resumo das mudanças: banco SQLite novo com as tabelas `anexos` (entidade `AnexoProcessado` das specs, mais o estado `retido`, contagem de tentativas e último erro), `ocorrencias` (mensagens já registradas como "possível documento sem anexo" ou "anexo compactado ignorado", para não repetir a linha a cada execução), `avisos` (entidade `EstadoAvisos` da spec `execucao-monitoramento`) e `meta` (versão do esquema e horário da última execução, para EM EC-04).
- Detalhe completo em: `_reversa_forward/001-mvp-email-nf-onedrive/data-delta.md`

## 7. Delta de contratos externos

| Contrato | Tipo | Arquivo de detalhe |
|----------|------|--------------------|
| IMAP do Google Workspace | protocolo IMAP4rev1 sobre TLS | `_reversa_forward/001-mvp-email-nf-onedrive/interfaces/imap-gmail.md` |
| Rclone e OneDrive for Business | processo externo (CLI) | `_reversa_forward/001-mvp-email-nf-onedrive/interfaces/rclone-onedrive.md` |
| API de bots do Telegram | HTTP | `_reversa_forward/001-mvp-email-nf-onedrive/interfaces/telegram-sendmessage.md` |
| Linha de comando e `.env` da ferramenta | CLI e arquivo | `_reversa_forward/001-mvp-email-nf-onedrive/interfaces/cli-e-env.md` |

## 8. Plano de migração

Não há dados legados a migrar; o banco nasce vazio e `DATA_INICIAL` limita a primeira coleta (RN-06). A entrada em operação segue o rollout das specs:

1. Liberar a escrita fora das pastas do Reversa em `.reversa/reversa-config.json` (ato do usuário; ver risco R-01).
2. Implementar e testar localmente (ações do `actions.md`).
3. Configurar o remote do OneDrive, rodar `rclone lsf` na pasta de destino e fechar a L-03 (premissa P-L03).
4. `verificar-config` e `testar-onedrive` na VPS do operador.
5. Uma semana de `executar --simular` a cada 30 min, comparando o log com a caixa e revisando os `sem-classificacao`.
6. Produção na VPS do operador.
7. Migração para a VPS da empresa seguindo só o guia, como teste da documentação (RF-20).

## 9. Riscos e mitigações

| Risco | Impacto | Probabilidade | Mitigação |
|-------|---------|---------------|-----------|
| R-01: `.reversa/reversa-config.json` está com `allowLegacyEdits: false`, o que bloqueia o `/reversa-coding` de escrever `src/`, `tests/`, `docs/`, `pyproject.toml`, `.env.example` e `README.md`. | alto | alto | Antes do coding, o usuário libera `allowLegacyEdits: true` com `allowedPaths` restritos a esses caminhos. |
| R-02: o tenant bloqueia o aplicativo público do Rclone sem consentimento de administrador. | alto | médio | `testar-onedrive` cedo; alternativa documentada em `investigation.md` §4 (aplicativo próprio no Entra ID com `client_id`). |
| R-03: a pasta de destino está no OneDrive de outra conta, e o remote aponta para o drive errado. | alto | médio | Configurar o remote com o `drive_id` do OneDrive de `<conta-admin>` (`investigation.md` §4); `testar-onedrive` confirma o caminho. |
| R-04: palavra-chave deixa NF ou boleto legítimo como `sem-classificacao`, e o documento não é enviado. | alto | médio | Semana de `--simular`; log "retido para revisão" com remetente e assunto; a lista de palavras-chave fica numa constante única, fácil de ampliar. |
| R-05: execução travada (IMAP pendurado apesar do timeout) mantém a trava e sobrepõe o ciclo seguinte. | médio | baixo | Limite de 20 min por execução (D-14), menor que a expiração de 25 min da trava. |
| R-06: `.env` com permissão 644 (estado atual na máquina do operador). | médio | alto | RF-03 alerta no log; o guia e o `onboarding.md` mandam aplicar `chmod 600`. |
| R-07: janela de busca grande na primeira execução ou após longa parada da VPS. | baixo | médio | CE EC-10: log de progresso a cada 50 mensagens; limite de 20 min por execução; o que não couber é retomado na execução seguinte pela janela, pois só `enviado` e `retido` saem da fila. |
| R-08: o Gmail devolve datas de mensagem em fusos variados, e a janela por dia (`SINCE`) tem granularidade diária. | baixo | médio | Datas normalizadas para UTC no registro; a sobreposição de 2 dias absorve a diferença, e a deduplicação elimina o excesso. |

## 10. Critério de pronto

- [X] Todas as ações do `actions.md` marcadas `[X]`
- [ ] `cross-check.md` (se executado) sem CRITICAL nem HIGH
- [X] `regression-watch.md` gerado
- [ ] Re-extração reversa executada e sem regressão vermelha (recomendado, não obrigatório)
- [X] `pytest` verde, incluindo a integração com o Rclone contra um diretório local
- [X] Os 14 cenários Gherkin do `requirements.md` §7 têm teste automatizado correspondente ou, quando dependem da infraestrutura real (RF-14, RF-20), roteiro manual no `onboarding.md`
- [X] L-03 fechada com a convenção real aplicada em `envio/nomeacao.py`
- [ ] `grep` pelo valor de `SENHA_EMAIL1` e do token do Telegram nos logs de um ciclo real sem ocorrências

## 11. Histórico de alterações

| Data | Alteração | Autor |
|------|-----------|-------|
| 2026-09-18 | Versão inicial gerada por `/reversa-plan`, com L-03 adotada como premissa | reversa |
| 2026-09-21 | Critério de pronto conferido: cinco itens verificados e marcados; seguem abertos o ciclo real (grep de segredos), a re-extração reversa e o `cross-check.md`, não executado | reversa |
