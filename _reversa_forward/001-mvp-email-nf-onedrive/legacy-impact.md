# Legacy impact: MVP de arquivamento automático de NFs e boletos

> Identificador: `001-mvp-email-nf-onedrive`
> Data: `2026-09-18`
> Feature greenfield, sem legado pré-existente. Âncora: prd.md + specs SDD.
> Política de edição no momento da execução: `allowLegacyEdits: true`, `allowedPaths: []` (projeto inteiro liberado, sem restrição de caminhos).
> Rodadas: T001–T014 (fases 1 e 2), T015–T028 (fase 3), T029–T041 (fase 4 e ciclo completo) e T043–T045 (polimento). Execução parcial: 44 de 45 ações; pendente só T042 (verificação manual contra o OneDrive e o Gmail reais).
> Estado dos testes: 217 testes passando (`pytest`), 156 de unidade e 61 de integração, estes com IMAP dublê, Rclone real sobre o remote `:local` e Telegram dublê.

## Arquivos afetados

| Arquivo afetado | Componente | Tipo | Severidade | Justificativa |
|-----------------|------------|------|------------|---------------|
| `pyproject.toml` | `execucao-monitoramento` (EM RF-01) | componente-novo | LOW | Empacotamento e *console script* `email-nf-onedrive` (T001). |
| `src/email_nf_onedrive/__init__.py`, `__main__.py` e `__init__.py` dos subpacotes | os quatro componentes | componente-novo | LOW | Esqueleto, um subpacote por spec (T002, D-02). `__main__.py` chama `cli.main`. |
| `.env.example` | `configuracao-caixas` §9, EM RF-13 | componente-novo | LOW | Contrato do `.env` com valores fictícios (T003). |
| `.gitignore` | infraestrutura do repositório | componente-novo | LOW | Arquivo pré-existente **acrescido** de `.venv/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/` e `var/`; linhas anteriores preservadas. Fora da lista de ações. |
| `tests/conftest.py`, `tests/dados/*` | transversal, `coleta-email` | componente-novo | LOW | Fixtures e dados sintéticos (T004, T005). |
| `tests/unidade/*.py` (9 arquivos) | os quatro componentes | componente-novo | LOW | Contratos dos módulos da fase 3 (T006–T014). |
| `src/email_nf_onedrive/segredos.py` | transversal (RF-03 do requirements) | componente-novo | MEDIUM | Mascaramento de senhas e token em logs e avisos (T015, D-04). Severidade média: é a barreira contra vazamento de credenciais. |
| `src/email_nf_onedrive/configuracao/modelo.py` | `configuracao-caixas` | componente-novo | LOW | `Caixa`, `CaixaInvalida`, `Configuracao`, `ErroConfiguracao`; segredos fora do `repr` (T016). |
| `src/email_nf_onedrive/configuracao/carregar.py` | `configuracao-caixas` | componente-novo | MEDIUM | Leitura sem `os.environ`, descoberta de `EMAIL<n>`, validação antes da rede (T017, CC RF-01 a RF-11). |
| `src/email_nf_onedrive/registro/esquema.sql` | `coleta-email` §9, `envio-onedrive` §9, `execucao-monitoramento` §9 | componente-novo | MEDIUM | Tabelas `anexos`, `ocorrencias`, `avisos`, `meta` (T018). |
| `src/email_nf_onedrive/registro/banco.py` | idem | componente-novo | HIGH | Registro de processados e máquina de estados (T019, D-09, D-17). Severidade alta: é o que impede reenvio e duplicação (RN-05). `fechar` passou a ser idempotente na rodada T029–T041. |
| `src/email_nf_onedrive/coleta/utf7.py` | `coleta-email` | componente-novo | LOW | Nomes de pasta IMAP em UTF-7 modificado (T020). |
| `src/email_nf_onedrive/coleta/classificacao.py` | `coleta-email` | componente-novo | HIGH | Classificação; decide o que é enviado e o que fica retido (T021, RN-03). Ver desvio da D-07 abaixo. |
| `src/email_nf_onedrive/coleta/mime.py` | `coleta-email` | componente-novo | MEDIUM | Extração de PDF e XML, inclusive encaminhados (T022, D-06). |
| `src/email_nf_onedrive/coleta/janela.py` | `coleta-email` | componente-novo | MEDIUM | Data de corte da busca (T023, CE RF-03). |
| `src/email_nf_onedrive/coleta/imap.py` | `coleta-email`, `interfaces/imap-gmail.md` | componente-novo | HIGH | Cliente IMAP restrito: `EXAMINE` (via `select(readonly=True)`) e `BODY.PEEK[]`, sem nenhum comando de escrita (T029, RN-01). Severidade alta: é a garantia de que as caixas nunca são alteradas. |
| `src/email_nf_onedrive/coleta/coleta.py` | `coleta-email` | componente-novo | HIGH | Orquestração por caixa, commit por mensagem, retidos e ocorrências únicas, falha isolada por caixa (T032, CE RF-01 a RF-11, RN-09). |
| `src/email_nf_onedrive/envio/nomeacao.py` | `envio-onedrive` | componente-novo | MEDIUM | Convenção de nomes **provisória**, isolada para a troca da L-03 (T024, D-12). |
| `src/email_nf_onedrive/envio/rclone.py` | `envio-onedrive`, `interfaces/rclone-onedrive.md` | delta-de-contrato-externo | HIGH | Fachada do Rclone com lista branca de subcomandos e causas de erro mapeadas (T030, D-10, RN-02). Ver desvio da D-10 abaixo. |
| `src/email_nf_onedrive/envio/envio.py` | `envio-onedrive` | componente-novo | HIGH | Protocolo de envio: pasta existente, nome livre ou idêntico, cópia sem sobrescrita, confirmação de tamanho e hash antes de marcar `enviado` (T035, EO RF-01 a RF-10, RN-04). |
| `src/email_nf_onedrive/envio/teste_onedrive.py` | `envio-onedrive` (EO RF-09) | componente-novo | MEDIUM | Prova de escrita com arquivo de nome exclusivo, apagado só pelo caminho exato (T037). |
| `src/email_nf_onedrive/execucao/trava.py` | `execucao-monitoramento` | componente-novo | MEDIUM | Trava exclusiva e limite de 20 min (T025, D-14). |
| `src/email_nf_onedrive/execucao/logs.py` | `execucao-monitoramento` | componente-novo | MEDIUM | Log com rotação e filtro de segredos (T026, D-15). |
| `src/email_nf_onedrive/execucao/avisos.py` | `execucao-monitoramento` | componente-novo | MEDIUM | Supressão, recuperação e reenvio de avisos (T027, D-16). |
| `src/email_nf_onedrive/execucao/resumo.py` | `execucao-monitoramento` | componente-novo | LOW | Linha de resumo da execução (T028, EM RF-11). |
| `src/email_nf_onedrive/execucao/telegram.py` | `execucao-monitoramento`, `interfaces/telegram-sendmessage.md` | componente-novo | MEDIUM | Transporte `sendMessage` via `urllib`, com erro mascarado e URL nunca registrada (T031). |
| `src/email_nf_onedrive/execucao/ciclo.py` | `execucao-monitoramento` | componente-novo | HIGH | Ciclo completo com código de saída 0/1/2, avisos, resumo e remoção da pasta de trabalho no `finally` (T038, EM RF-02 a RF-11, EC-01 a EC-07). |
| `src/email_nf_onedrive/cli.py` | `execucao-monitoramento` (EM RF-01), `configuracao-caixas` (CC RF-10) | componente-novo | MEDIUM | `executar [--simular]`, `verificar-config` e `testar-onedrive`, com `--home` ou `EMAIL_NF_HOME` (T039). |
| `tests/integracao/dubles.py`, `tests/integracao/conftest.py` | transversal | componente-novo | LOW | Servidor IMAP em memória que recusa comandos de escrita, transporte dublê e ambiente de ponta a ponta (T033, T040). |
| `tests/integracao/test_rclone.py`, `test_coleta.py`, `test_envio.py` | `envio-onedrive`, `coleta-email` | componente-novo | LOW | Integração com o Rclone real sobre `:local` e com o IMAP dublê (T033, T034, T036). |
| `tests/integracao/test_ciclo_arquivamento.py`, `test_ciclo_falhas.py` | os quatro componentes | componente-novo | LOW | Os cenários do `requirements.md` §7 de ponta a ponta, via `cli.main` (T040, T041). |
| `tests/unidade/test_logs.py` | `execucao-monitoramento` (EM RF-06) | componente-novo | LOW | Fixa a rotação diária com 29 cópias, o formato da linha, a permissão 600 e o mascaramento no arquivo; lacuna encontrada ao montar a rastreabilidade (T045). |
| `tests/integracao/test_ciclo_falhas.py` (acréscimo) | `configuracao-caixas` (CC RF-08) | componente-novo | LOW | Cenário 6 do §7 com o valor literal do requisito, `DATA_INICIAL=18/09/2026`; acrescentado na T045. |
| `docs/instalacao-e-operacao.md` | `execucao-monitoramento` (EM RF-12), requirements RF-20 | componente-novo | MEDIUM | Guia de instalação e operação, com alternativas de tenant, renovação de credenciais e revisão dos retidos (T043). Severidade média: é o que permite a um terceiro operar a ferramenta. |
| `README.md` | transversal | componente-novo | LOW | O que a ferramenta faz e nunca faz (RN-01, RN-02), subcomandos e desenvolvimento (T044). |
| `tests/RASTREABILIDADE.md` | transversal | componente-novo | LOW | Liga os 14 cenários do §7 e os RF-01 a RF-20 aos testes ou ao passo manual (T045). |

## Diff conceitual por componente

**`configuracao-caixas`:** completo. `carregar_configuracao(home)` devolve `Configuracao` ou levanta `ErroConfiguracao` com todos os erros globais de uma vez; senhas e token, inclusive de caixas inválidas, entram em `segredos` assim que lidos. O `verificar-config` imprime `n · endereço · pasta · destino · senha ****` por caixa válida e, além do que a CC RF-10 pede, as caixas inválidas, o remote do Rclone, a data inicial, o estado dos avisos e os alertas; sai com 2 em erro global ou sem caixa válida, distinguindo "nenhuma caixa configurada" de "nenhuma caixa válida".

**`coleta-email`:** completo. O cliente IMAP só emite `LOGIN`, `LIST`, `EXAMINE`, `SEARCH`, `FETCH (BODY.PEEK[])` e `LOGOUT`, o que os testes verificam com um dublê que falha diante de qualquer outro comando. Cada mensagem é confirmada no registro assim que processada, de modo que uma interrupção não perde o que já foi lido. **Desvio da D-07:** o roadmap previa ler o XML só até a raiz, mas isso classificava como NF-e um XML truncado, contrariando o EC-07 da spec; a leitura passou a ir até o fim do documento, com o limite de 10 MB mantido. A linha `corrected` de T021 no `progress.jsonl` registra esse desvio, e não uma entrega errada.

**`envio-onedrive`:** completo, com a nomeação ainda provisória (L-03). **Desvio da D-10:** a D-10, o `investigation.md` §3 e o `interfaces/rclone-onedrive.md` preveem `copyto --immutable` para impedir a sobrescrita, mas o teste com o Rclone real mostrou que `--immutable` não impede a cópia sobre um arquivo de conteúdo diferente. A fachada passou a usar `copyto --ignore-existing` e a confirmar tamanho e QuickXorHash no destino depois da cópia; divergência vira `falha-envio` com "tamanho divergente", e o arquivo da equipe nunca é substituído (verificado em `test_envio.py` e `test_ciclo_arquivamento.py`). Os dois documentos da feature ficam desatualizados nesse ponto até o `/reversa-sync`. Erros de token ou de remote inexistente suspendem os envios restantes da execução, porque todos falhariam pela mesma causa.

**`execucao-monitoramento`:** completo. Ordem do ciclo: log, trava, limite de duração, registro, configuração, coleta, envio, avisos e resumo. Duas escolhas não explícitas no roadmap: o registro é aberto **antes** da configuração, para que o erro de configuração também passe pela supressão de 6 h; e, com a configuração inválida, o ciclo lê só o par `TELEGRAM_*` do `.env` para ainda assim avisar (transporte de emergência). Código de saída: 0 sem falhas; 1 com falha parcial, inclusive caixa inválida no `.env`; 2 em erro de configuração, nenhuma caixa válida, todas as caixas com falha na coleta, registro ilegível, tempo esgotado, disco cheio ou exceção não prevista. Sem registro legível, o aviso sai direto, sem supressão. O encerramento (avisos, `meta`, fechamento do registro) nunca altera o código já calculado. A contagem de falhas do resumo soma caixas inválidas, caixas com falha, anexos com falha de envio e erros da execução.

**Documentação e rastreabilidade:** o guia cobre todos os itens do EM RF-12 e acrescenta a revisão dos retidos, os envios com falha e as situações especiais (VPS desligada, disco cheio, registro corrompido, trava presa). Ele registra que os anexos retidos não são guardados pela ferramenta, só os metadados, o que obriga a revisão pela própria caixa de e-mail. A montagem da rastreabilidade revelou duas lacunas, fechadas com testes: a rotação do log não tinha teste, e o cenário 6 do §7 era exercitado com outro erro global. Continuam sem teste automatizado a rotação efetiva em 31 dias e os cenários que dependem de infraestrutura real (RF-14 contra o OneDrive, RF-20), remetidos à T042.

**Registro compartilhado:** a simulação sobre banco inexistente usa um banco em memória e não cria arquivo; sobre banco existente, desfaz tudo ao fechar. O banco corrompido nunca é recriado nem alterado.

## Preservadas

Não se aplica: feature greenfield, sem regras 🟢 extraídas de código anterior.

## Modificadas

Não se aplica: feature greenfield. As divergências em relação às specs e ao roadmap (RN-03, chave do registro por endereço, leitura integral do XML na D-07 e `--ignore-existing` com confirmação por hash na D-10) ficam registradas aqui e no `roadmap.md` §5, para convergência pelo `/reversa-sync`.
