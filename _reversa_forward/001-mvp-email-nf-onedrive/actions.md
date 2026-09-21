# Actions: MVP de arquivamento automático de NFs e boletos do e-mail no OneDrive

> Identificador: `001-mvp-email-nf-onedrive`
> Data: `2026-09-18`
> Roadmap: `_reversa_forward/001-mvp-email-nf-onedrive/roadmap.md`
>
> ⚠️ **Pré-condição do `/reversa-coding`:** todas as ações escrevem fora das pastas do Reversa (`src/`, `tests/`, `docs/`, `pyproject.toml`, `.env.example`, `README.md`). Com `allowLegacyEdits: false` em `.reversa/reversa-config.json`, o coding recusará a escrita até que o usuário libere esses caminhos (roadmap, risco R-01).
>
> ⚠️ **Ação manual:** T042 depende do remote do OneDrive configurado pelo operador e fecha a premissa P-L03 (L-03). As demais ações são executáveis por agente sem credenciais reais.
>
> Convenção dos testes: os dados em `tests/dados/` são sintéticos; nenhum e-mail, NF ou boleto real entra no repositório.

## Resumo

| Métrica | Valor |
|---------|-------|
| Total de ações | 45 |
| Paralelizáveis (`[//]`) | 27 |
| Maior cadeia de dependência | 11 (T001 → T002 → T004 → T012 → T019 → T023 → T032 → T038 → T039 → T040 → T045) |

| Fase | Ações |
|------|-------|
| 1, Preparação | 5 |
| 2, Testes | 9 |
| 3, Núcleo | 14 |
| 4, Integração | 14 |
| 5, Polimento | 3 |

## Fase 1, Preparação

| ID | Descrição | Dependências | Paralelismo | Arquivo alvo | Confidência | Status |
|----|-----------|--------------|-------------|--------------|-------------|--------|
| T001 | Criar `pyproject.toml` com pacote `email_nf_onedrive` em layout `src/`, `requires-python >= 3.11`, dependência `python-dotenv`, extra `dev` com `pytest` e *console script* `email-nf-onedrive = email_nf_onedrive.cli:main` (D-01). | - | - | `pyproject.toml` | 🟢 | [X] |
| T002 | Criar o esqueleto do pacote: `__init__.py` com `__version__`, `__main__.py` delegando a `cli.main`, e `__init__.py` vazios em `configuracao/`, `registro/`, `coleta/`, `envio/` e `execucao/` (D-02). | T001 | - | `src/email_nf_onedrive/__init__.py` | 🟢 | [X] |
| T003 | Criar `.env.example` com todas as variáveis de `interfaces/cli-e-env.md`, valores fictícios, comentários curtos por variável e a linha do `cron` comentada no fim (EM RF-13). | - | `[//]` | `.env.example` | 🟢 | [X] |
| T004 | Criar `tests/conftest.py` com fixtures: diretório de instalação temporário (`home` com `var/`), fábrica que escreve `.env` a partir de um dicionário e relógio injetável para datas. | T002 | - | `tests/conftest.py` | 🟢 | [X] |
| T005 | Criar dados sintéticos em `tests/dados/`: `.eml` com PDF simples, com PDF e PNG, com nome RFC 2047, com parte PDF sem nome, com `message/rfc822` encaminhada, com `.zip`, só com link de NFS-e, sem `Message-ID`; XMLs de NF-e com raiz `nfeProc` e `NFe`, e um XML malformado. | - | `[//]` | `tests/dados/` | 🟢 | [X] |

## Fase 2, Testes

| ID | Descrição | Dependências | Paralelismo | Arquivo alvo | Confidência | Status |
|----|-----------|--------------|-------------|--------------|-------------|--------|
| T006 | Escrever testes da configuração: descoberta com lacunas, padrões de pasta e servidor, destino por caixa, erros globais (código 2) e por caixa, senha órfã, caixa duplicada, Telegram incompleto, `.env` ausente, alerta de permissão (CC RF-01 a RF-11, EC-01 a EC-08). | T004 | `[//]` | `tests/unidade/test_configuracao.py` | 🟢 | [X] |
| T007 | Escrever testes do filtro de segredos: senha e token substituídos por `****` em mensagem, argumentos e texto de exceção formatada (D-04, RF-03). | T004 | `[//]` | `tests/unidade/test_segredos.py` | 🟢 | [X] |
| T008 | Escrever testes de UTF-7 modificado (ida e volta com `[Gmail]/Todos os e-mails`) e de classificação: `nfe-xml` pelas duas raízes, fronteira de palavra (`info.pdf` não casa `nf`; `NF-e_123.pdf` casa), acentos, XML malformado, limite de 10 MB (D-05, D-07, CE RF-05, RF-06, EC-07). | T004, T005 | `[//]` | `tests/unidade/test_classificacao.py` | 🟡 | [X] |
| T009 | Escrever testes de extração MIME sobre os `.eml` de `tests/dados/`: contagem de anexos, nome decodificado, `anexo-<n>.pdf` sem nome, descida em encaminhada, `.zip` sinalizado e não extraído, identificador substituto sem `Message-ID` (CE RF-04, EC-05, EC-06, EC-08, fluxo B). | T004, T005 | `[//]` | `tests/unidade/test_mime.py` | 🟢 | [X] |
| T010 | Escrever testes da janela de busca: caixa sem histórico usa `DATA_INICIAL`; com histórico usa `max − 2 dias`; anexo pendente mais antigo recua a janela; formato `dd-Mon-aaaa` do IMAP (CE RF-03, `data-delta.md` §2). | T004 | `[//]` | `tests/unidade/test_janela.py` | 🟢 | [X] |
| T011 | Escrever testes da nomeação provisória: exemplo do EO RF-01, remoção de caracteres inválidos, espaços e pontos finais, truncamento em 200 caracteres com extensão preservada, nomes reservados do OneDrive, geração de sufixos `_2`, `_3` (EO RF-01, RF-02, RF-04, D-12). | T004 | `[//]` | `tests/unidade/test_nomeacao.py` | 🟡 | [X] |
| T012 | Escrever testes do registro: criação do esquema, chave única por endereço, transições permitidas e proibidas da máquina de estados, `retido` terminal, tabela `ocorrencias`, abertura em simulação sem persistir, falha de `integrity_check` (`data-delta.md` §2 a §6). | T004 | `[//]` | `tests/unidade/test_registro.py` | 🟡 | [X] |
| T013 | Escrever testes da trava: aquisição exclusiva, segunda aquisição recusada, trava de 30 min considerada abandonada, trava com PID inexistente retomada, liberação no `finally` (EM RF-03, RF-04, D-14). | T004 | `[//]` | `tests/unidade/test_trava.py` | 🟡 | [X] |
| T014 | Escrever testes da lógica de avisos: primeira ocorrência notifica, repetição em menos de 6 h suprime, após 6 h renotifica, entrega pendente é reenviada, recuperação única ao voltar a código 0, mensagem sem segredos (EM RF-07 a RF-09, `data-delta.md` §4). | T004 | `[//]` | `tests/unidade/test_avisos.py` | 🟢 | [X] |

## Fase 3, Núcleo

| ID | Descrição | Dependências | Paralelismo | Arquivo alvo | Confidência | Status |
|----|-----------|--------------|-------------|--------------|-------------|--------|
| T015 | Implementar `segredos.py`: registro de valores sensíveis e `logging.Filter` que os mascara em `msg`, `args` e exceções, até T007 passar (D-04). | T007 | `[//]` | `src/email_nf_onedrive/segredos.py` | 🟢 | [X] |
| T016 | Implementar `configuracao/modelo.py` com as *dataclasses* imutáveis `Caixa`, `Configuracao` e `CaixaInvalida`, com `senha` e token fora do `repr` (CC §9). | T002 | `[//]` | `src/email_nf_onedrive/configuracao/modelo.py` | 🟢 | [X] |
| T017 | Implementar `configuracao/carregar.py`: `dotenv_values`, descoberta de `EMAIL<n>`, padrões, validação global e por caixa, alertas, registro dos segredos em `segredos.py`, até T006 passar (CC RF-01 a RF-11, D-03). | T006, T015, T016 | - | `src/email_nf_onedrive/configuracao/carregar.py` | 🟢 | [X] |
| T018 | Escrever `registro/esquema.sql` com as tabelas `anexos`, `ocorrencias`, `avisos` e `meta`, restrições `CHECK`, chave única e índice (`data-delta.md` §2 a §5). | T002 | `[//]` | `src/email_nf_onedrive/registro/esquema.sql` | 🟢 | [X] |
| T019 | Implementar `registro/banco.py`: abertura com permissão 600, `integrity_check`, aplicação do esquema, modo simulação com `ROLLBACK`, funções de transição validadas e consultas da janela, até T012 passar (D-09, D-17). | T012, T018 | - | `src/email_nf_onedrive/registro/banco.py` | 🟡 | [X] |
| T020 | Implementar `coleta/utf7.py` (codificação e decodificação de UTF-7 modificado, RFC 3501 §5.1.3), até a parte correspondente de T008 passar. | T008 | `[//]` | `src/email_nf_onedrive/coleta/utf7.py` | 🟢 | [X] |
| T021 | Implementar `coleta/classificacao.py`: detecção de NF-e pela raiz com `iterparse` e limite de tamanho, normalização de texto e lista de palavras-chave numa constante única com fronteira de palavra, até T008 passar (D-07). | T008 | `[//]` | `src/email_nf_onedrive/coleta/classificacao.py` | 🟡 | [X] |
| T022 | Implementar `coleta/mime.py`: parsing com `policy.default`, percurso recursivo com `message/rfc822`, seleção PDF/XML, sinalização de compactados, nomes gerados e identificador substituto, até T009 passar (D-06). | T009 | `[//]` | `src/email_nf_onedrive/coleta/mime.py` | 🟢 | [X] |
| T023 | Implementar `coleta/janela.py`: cálculo da data de corte a partir do registro e formatação para `SEARCH SINCE`, até T010 passar (CE RF-03). | T010, T019 | - | `src/email_nf_onedrive/coleta/janela.py` | 🟢 | [X] |
| T024 | Implementar `envio/nomeacao.py` com a única função pública `caminho_destino(anexo, destino)` na convenção provisória, saneamento e gerador de sufixos, até T011 passar (D-12, premissa P-L03). | T011 | `[//]` | `src/email_nf_onedrive/envio/nomeacao.py` | 🟡 | [X] |
| T025 | Implementar `execucao/trava.py`: arquivo com `O_EXCL`, PID e horário, detecção de abandono por idade e por PID, gerenciador de contexto e limite de duração de 20 min via `signal.alarm`, até T013 passar (D-14). | T013 | `[//]` | `src/email_nf_onedrive/execucao/trava.py` | 🟡 | [X] |
| T026 | Implementar `execucao/logs.py`: `TimedRotatingFileHandler` à meia-noite com 29 cópias, formato ISO 8601 com nível e caixa, permissão 600, filtro de segredos em todos os *handlers* e saída de terminal opcional (D-15, EM RF-06). | T015 | - | `src/email_nf_onedrive/execucao/logs.py` | 🟢 | [X] |
| T027 | Implementar `execucao/avisos.py`: registro de falhas por causa, decisão de notificar com a janela de 6 h, recuperação, agregação numa mensagem por execução e truncamento em 4096 caracteres, recebendo o transporte por injeção, até T014 passar (D-16). | T014, T019 | - | `src/email_nf_onedrive/execucao/avisos.py` | 🟢 | [X] |
| T028 | Implementar `execucao/resumo.py`: acumulador `ResumoExecucao` com contagens, duração, intervalo desde a execução anterior e linha `resumo: ...` do EM RF-11. | T002 | `[//]` | `src/email_nf_onedrive/execucao/resumo.py` | 🟢 | [X] |

## Fase 4, Integração

| ID | Descrição | Dependências | Paralelismo | Arquivo alvo | Confidência | Status |
|----|-----------|--------------|-------------|--------------|-------------|--------|
| T029 | Implementar `coleta/imap.py`: classe que embrulha `IMAP4_SSL` com timeout de 60 s e expõe só `LOGIN`, `LIST`, `EXAMINE`, `SEARCH SINCE`, `FETCH BODY.PEEK[]` e `LOGOUT`, com erros tipados por causa (`interfaces/imap-gmail.md`, D-05). | T020 | `[//]` | `src/email_nf_onedrive/coleta/imap.py` | 🟢 | [X] |
| T030 | Implementar `envio/rclone.py`: fachada com lista branca de subcomandos, restrição de `deletefile` ao arquivo de teste, flags comuns, timeout de 120 s, ambiente sem variáveis do `.env`, parsing de `lsjson` e `hashsum`, e mapeamento de `stderr` para causas (`interfaces/rclone-onedrive.md`, D-10). | T015 | `[//]` | `src/email_nf_onedrive/envio/rclone.py` | 🟢 | [X] |
| T031 | Implementar `execucao/telegram.py`: transporte `sendMessage` com `urllib.request`, timeout de 15 s, texto puro, sem registrar a URL, devolvendo entregue ou motivo da falha (`interfaces/telegram-sendmessage.md`). | T015 | `[//]` | `src/email_nf_onedrive/execucao/telegram.py` | 🟢 | [X] |
| T032 | Implementar `coleta/coleta.py`: por caixa, conectar, abrir a pasta, calcular a janela, buscar, extrair, classificar, gravar na pasta de trabalho (700), registrar `extraido` ou `retido`, registrar ocorrências únicas, logar progresso a cada 50 mensagens e isolar falhas por caixa (CE RF-01 a RF-11, RN-03, RN-09). | T017, T019, T021, T022, T023, T029 | - | `src/email_nf_onedrive/coleta/coleta.py` | 🟡 | [X] |
| T033 | Escrever teste de integração da coleta com servidor IMAP dublê: nenhum comando fora da lista, uso de `BODY.PEEK[]`, deduplicação entre execuções, `retido` logado uma vez, falha da caixa 1 sem afetar a caixa 2, pasta inexistente listando pastas. | T032 | - | `tests/integracao/test_coleta.py` | 🟢 | [X] |
| T034 | Escrever teste de integração da fachada com o Rclone real contra diretório local: `lsjson` de ausente e presente, `hashsum quickxor`, `copyto --immutable` recusando sobrescrita, recusa de subcomando fora da lista e de `deletefile` fora do arquivo de teste. | T030 | `[//]` | `tests/integracao/test_rclone.py` | 🟢 | [X] |
| T035 | Implementar `envio/envio.py`: protocolo de `interfaces/rclone-onedrive.md` (pasta de destino existe, candidato, idêntico → `enviado`, sufixos até 99, `copyto`, confirmação por tamanho), transições `enviado` e `falha-envio` com tentativas e último erro, remoção da cópia local, aviso na 5ª tentativa e modo simulação só com `lsjson` (EO RF-01 a RF-08, RF-10). | T019, T024, T030 | - | `src/email_nf_onedrive/envio/envio.py` | 🟡 | [X] |
| T036 | Escrever teste de integração do envio com Rclone real contra diretório local: arquivo novo, idêntico sem upload, conteúdo diferente com `_2`, destino inexistente não criado, cópia local removida, simulação sem efeitos. | T035 | - | `tests/integracao/test_envio.py` | 🟢 | [X] |
| T037 | Implementar `envio/teste_onedrive.py`: grava arquivo de 1 KB com nome `.email-nf-onedrive-teste-<uuid>.txt`, confirma por `lsjson`, apaga só ele e devolve mensagem de sucesso ou causa (EO RF-09). | T030 | - | `src/email_nf_onedrive/envio/teste_onedrive.py` | 🟢 | [X] |
| T038 | Implementar `execucao/ciclo.py`: trava e limite de duração, configuração, logs, registro (normal ou simulação), coleta de todas as caixas, envio, remoção da pasta de trabalho no `finally`, cálculo do código 0/1/2, avisos (exceto em simulação), atualização de `meta` e resumo, com dependências injetáveis (EM RF-02 a RF-11, EC-01 a EC-07). | T025, T026, T027, T028, T031, T032, T035 | - | `src/email_nf_onedrive/execucao/ciclo.py` | 🟡 | [X] |
| T039 | Implementar `cli.py`: `argparse` com `--home`, `executar [--simular]`, `verificar-config` (listagem mascarada, sem rede) e `testar-onedrive`, repassando o código de saída (EM RF-01, CC RF-10, `interfaces/cli-e-env.md`). | T017, T037, T038 | - | `src/email_nf_onedrive/cli.py` | 🟢 | [X] |
| T040 | Escrever testes de ponta a ponta dos cenários de arquivamento do `requirements.md` §7 (boleto arquivado, reexecução, nome repetido, retomada após falha, retido para revisão, sem anexo e compactado, simulação) chamando `cli.main` com IMAP dublê, Rclone local e Telegram dublê. | T039 | - | `tests/integracao/test_ciclo_arquivamento.py` | 🟢 | [X] |
| T041 | Escrever testes de ponta a ponta dos cenários de falha do `requirements.md` §7 (caixa incompleta com código 1, erro global com código 2 sem rede, supressão e recuperação de aviso, credenciais ausentes do log e dos avisos, execuções sobrepostas). | T039 | - | `tests/integracao/test_ciclo_falhas.py` | 🟢 | [X] |
| T042 | **Manual, requer operador:** com o remote do OneDrive configurado, rodar `rclone lsf --max-depth 2` na pasta de destino, registrar o padrão de nomes e subpastas encontrado e ajustar `envio/nomeacao.py` e `tests/unidade/test_nomeacao.py` a ele, fechando a L-03 do `requirements.md`. | T024, T037 | - | `src/email_nf_onedrive/envio/nomeacao.py` | 🔴 | [X] |

## Fase 5, Polimento

| ID | Descrição | Dependências | Paralelismo | Arquivo alvo | Confidência | Status |
|----|-----------|--------------|-------------|--------------|-------------|--------|
| T043 | Escrever `docs/instalacao-e-operacao.md` com todos os itens do EM RF-12: requisitos da VPS, usuário de serviço, Python e Rclone, senha de app, `rclone authorize` e alternativas de tenant (`investigation.md` §4), `.env` e `chmod 600`, bot do Telegram e `chat_id`, `cron`, nova caixa, renovação de credenciais, leitura do log e revisão dos retidos. | T039 | `[//]` | `docs/instalacao-e-operacao.md` | 🟢 | [X] |
| T044 | Escrever `README.md` curto: o que a ferramenta faz, o que ela nunca faz (RN-01, RN-02), instalação rápida para desenvolvimento, subcomandos e link para o guia. | T039 | `[//]` | `README.md` | 🟢 | [X] |
| T045 | Escrever `tests/RASTREABILIDADE.md`, que liga cada um dos 14 cenários do `requirements.md` §7 e cada RF-01 a RF-20 ao teste que o cobre, ou ao passo do `onboarding.md` quando depender de infraestrutura real (RF-14, RF-20). | T040, T041 | `[//]` | `tests/RASTREABILIDADE.md` | 🟢 | [X] |

## Notas de execução

## Histórico de alterações

| Data | Alteração | Autor |
|------|-----------|-------|
| 2026-09-18 | Versão inicial gerada por `/reversa-to-do` | reversa |
