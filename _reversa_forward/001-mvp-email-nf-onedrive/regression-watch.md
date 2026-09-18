# Regression watch: MVP de arquivamento automático de NFs e boletos

> Identificador: `001-mvp-email-nf-onedrive`
> Feature greenfield: não há regras 🟢 extraídas de código anterior, e o watch principal fica vazio. Os itens de "Observações" ganham peso de regressão quando uma futura extração `/reversa` sobre o código novo os confirmar como 🟢.

## Watch principal

| ID | Origem (arquivo, seção) | Regra esperada após mudança | Tipo de verificação | Sinal de violação |
|----|-------------------------|-----------------------------|---------------------|-------------------|

## Observações

W001 a W010: contratos fixados na rodada T001–T014 e implementados na rodada T015–T028. W011 a W013: acrescentados na rodada T015–T028. W014 a W019: acrescentados na rodada T029–T041. W020 e W021: acrescentados na rodada T043–T045. Segue pendente a verificação manual (T042).

| ID | Origem (arquivo, seção) | Regra esperada | Tipo de verificação | Sinal de violação |
|----|-------------------------|----------------|---------------------|-------------------|
| W001 | `_reversa_sdd/sdd/configuracao-caixas.md#6.1` (RF-01 a RF-05) | Caixas descobertas por `EMAIL<n>`, com lacunas, padrões `INBOX` e `imap.gmail.com:993`, destino sobreponível por caixa. | presença | `tests/unidade/test_configuracao.py` falha, ou a extração não encontra a descoberta por índice. |
| W002 | `_reversa_sdd/sdd/configuracao-caixas.md#6.1` (RF-08, EC-05, EC-06, EC-08) | Erro global aborta antes da rede; erro por caixa invalida só a caixa. | presença | Caixa inválida interrompe as demais, ou erro global não aborta. |
| W003 | `requirements.md#5` (RF-03), `configuracao-caixas.md#6.1` (RF-09) | Senhas e token nunca aparecem em log, aviso ou `repr`. | presença | `tests/unidade/test_segredos.py` falha, ou um segredo aparece em saída. |
| W004 | `_reversa_sdd/sdd/coleta-email.md#6.1` (RF-05, RF-06) | Classificação `nfe-xml` pela raiz e namespace; palavras-chave com fronteira de letras. | redação | `info.pdf` classificado como `palavra-chave`, ou NF-e em XML não reconhecida. |
| W005 | `_reversa_sdd/sdd/coleta-email.md#6.1` (RF-04, EC-05, EC-06, EC-08) | Extração de PDF e XML, inclusive em mensagem encaminhada; compactados só sinalizados. | presença | `.zip` extraído, ou anexo de mensagem encaminhada ignorado. |
| W006 | `_reversa_sdd/sdd/coleta-email.md#6.1` (RF-03) | Janela = `DATA_INICIAL` sem histórico; senão `min(última − 2 dias, pendente mais antiga)`, nunca antes de `DATA_INICIAL`. | redação | `tests/unidade/test_janela.py` falha. |
| W007 | `_reversa_sdd/sdd/envio-onedrive.md#6.1` (RF-01, RF-02, RF-04) | Nome `AAAA-MM-DD_<remetente>_<nome>` (data em Brasília), saneado, até 200 caracteres, sufixo `_n`. Provisório até fechar a L-03. | redação | Mudança na convenção sem a decisão da L-03 registrada. |
| W008 | `requirements.md#4` (RN-03, RN-05), `roadmap.md#3` (D-08, D-09) | Registro com chave (endereço, identificador da mensagem, SHA-256), estado terminal `retido`, estados terminais imutáveis. | presença | Anexo reenviado após renumeração de caixa, ou `retido` enviado. |
| W009 | `_reversa_sdd/sdd/execucao-monitoramento.md#6.1` (RF-03, RF-04) | Trava exclusiva, abandonada após 25 min ou com PID morto; execução limitada a 20 min. | presença | Duas execuções simultâneas completas. |
| W010 | `_reversa_sdd/sdd/execucao-monitoramento.md#6.1` (RF-07 a RF-09) | Aviso na primeira falha, supressão de 6 h por causa, recuperação única, reenvio de aviso não entregue. | presença | Mais de um aviso por causa em 6 h, ou falha sem aviso. |
| W011 | `_reversa_sdd/sdd/coleta-email.md#11` (EC-07); `roadmap.md#3` (D-07, alterada na rodada T015–T028) | XML só é `nfe-xml` se estiver bem formado **até o fim** e tiver raiz `nfeProc` ou `NFe` no namespace da NF-e; XML truncado cai nas regras de texto. | redação | XML truncado com raiz de NF-e classificado como `nfe-xml`. |
| W012 | `_reversa_sdd/sdd/execucao-monitoramento.md#6.1` (RF-06); `roadmap.md#3` (D-15) | Log em arquivo com permissão 600, uma linha por evento no formato `ISO 8601 NIVEL [caixa n] mensagem`, rotação à meia-noite com 29 cópias antigas, filtro de segredos em todo *handler*. | presença | Log com mais de 30 arquivos, sem prefixo de caixa, ou com segredo em claro. |
| W013 | `_reversa_sdd/sdd/execucao-monitoramento.md#6.1` (RF-11) | Linha `resumo: N caixa(s), X extraídos, Y enviados, [Z retidos, ]W falhas, T s`, com o intervalo desde a execução anterior quando conhecido. | redação | Resumo ausente no fim da execução. |
| W014 | `requirements.md#4` (RN-01); `_reversa_sdd/sdd/coleta-email.md#6.1` (RF-01, RF-02); `interfaces/imap-gmail.md` | A caixa é aberta com `EXAMINE` e lida só com `BODY.PEEK[]`; nenhum comando de escrita (`STORE`, `COPY`, `MOVE`, `EXPUNGE`, `SELECT`) é emitido. | ausência | `test_coleta.py::test_so_comandos_de_leitura_e_body_peek` falha, ou mensagem marcada como lida após a execução. |
| W015 | `requirements.md#4` (RN-02, RN-04); `roadmap.md#3` (D-10, alterada na rodada T029–T041) | O Rclone só roda `lsjson`, `hashsum`, `copyto --ignore-existing`, `lsf` e `deletefile` do arquivo de teste; o anexo só vira `enviado` depois de conferidos tamanho e QuickXorHash no destino; arquivo existente de outro conteúdo nunca é sobrescrito. | presença | Arquivo da equipe substituído, `enviado` sem confirmação, ou subcomando fora da lista executado. |
| W016 | `_reversa_sdd/sdd/envio-onedrive.md#6.1` (RF-03, RF-06) | A pasta de destino nunca é criada; destino ausente gera `falha-envio` e aviso `onedrive:destino`, e o anexo é reenviado quando a pasta volta. | presença | Pasta criada automaticamente, ou anexo perdido após a pasta voltar. |
| W017 | `_reversa_sdd/sdd/execucao-monitoramento.md#6.1` (RF-05) | Código 0 sem falhas; 1 em falha parcial, inclusive caixa inválida; 2 em erro de configuração, nenhuma caixa válida, todas as caixas com falha, registro ilegível, tempo esgotado, disco cheio ou exceção não prevista. | redação | `test_ciclo_falhas.py` falha, ou cron recebe 0 com caixa falhando. |
| W018 | `_reversa_sdd/sdd/execucao-monitoramento.md#6.1` (RF-10) | `executar --simular` não envia, não grava o registro (nem o cria) e não avisa; o log lista o que seria enviado. | ausência | Registro alterado ou arquivo no destino após simulação. |
| W019 | `_reversa_sdd/sdd/execucao-monitoramento.md#11` (EC-06, EC-07); `configuracao-caixas.md#6.1` (RF-08) | Erro de configuração é avisado mesmo sem configuração válida (par `TELEGRAM_*` lido à parte) e passa pela supressão; exceção não prevista deixa a pilha no log, avisa com o tipo do erro, libera a trava e remove a pasta de trabalho. | presença | Erro de configuração silencioso, ou trava presa após exceção. |
| W020 | `_reversa_sdd/sdd/execucao-monitoramento.md#6.1` (RF-12); `requirements.md#5` (RF-20) | O guia `docs/instalacao-e-operacao.md` cobre requisitos da VPS, usuário de serviço, Python e Rclone, senha de app, `rclone authorize` e alternativas de tenant, `.env` com `chmod 600`, bot do Telegram, `cron`, nova caixa, renovação de credenciais, leitura do log e revisão dos retidos; o README declara as garantias RN-01 e RN-02. | presença | Seção do guia removida, ou comando citado no guia que o `--help` não reconhece. |
| W021 | `tests/RASTREABILIDADE.md` | Cada cenário do §7 e cada RF-01 a RF-20 aponta para ao menos um teste existente ou para um passo manual explícito. | presença | Teste citado no mapa que o `pytest --collect-only` não encontra, ou RF sem linha. |

## Histórico de re-extrações

## Arquivadas
