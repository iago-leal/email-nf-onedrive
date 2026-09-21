# Legacy impact: acesso às caixas do Gmail por OAuth 2.0

> Identificador: `002-oauth-gmail-google-cloud`
> Data: `2026-09-21`
> Âncora greenfield: `_reversa_sdd/prd.md` e as specs em `_reversa_sdd/sdd/`, lidas com o adendo `_reversa_sdd/addenda/001-mvp-email-nf-onedrive.md`. Não há extração de legado (`architecture.md`, `domain.md`); por isso não existem regras 🟢 extraídas, e as seções "Preservadas" e "Modificadas" listam regras das specs e itens de vigilância da feature 001, sem peso de regressão formal.
> Diferente da feature 001, esta altera código que já existia. Os tipos de impacto refletem isso (`regra-alterada`, `delta-de-contrato-externo`), em vez do `componente-novo` uniforme do cenário greenfield puro.
> Política de edição no momento da execução: `allowLegacyEdits: true`, `allowedPaths: []` (projeto inteiro liberado, sem restrição de caminhos).
> Rodada: T001 a T038, em 2026-09-21. Execução: 38 de 39 ações; a T039 é manual, do operador.
> Estado dos testes: 361 passando (`pytest`), dos quais 236 anteriores, sem alteração de expectativa além de `COMANDOS_PERMITIDOS`, e 125 novos.

## Arquivos afetados

| Arquivo afetado | Componente | Tipo | Severidade | Justificativa |
|-----------------|------------|------|------------|---------------|
| `src/email_nf_onedrive/autorizacao/__init__.py` | `autorizacao` (novo; sem spec própria, descrito no roadmap §5) | componente-novo | LOW | Subpacote que concentra tudo o que fala com o Google (T003). |
| `src/email_nf_onedrive/autorizacao/arquivo.py` | `autorizacao`; `configuracao-caixas` §9 (entidade `Autorizacao`) | componente-novo, delta-de-dados | HIGH | Leitura validada e gravação atômica do JSON com a autorização durável, 600 em diretório 700 (T019, D-05). Severidade alta: guarda o segredo que dá acesso total à caixa. |
| `src/email_nf_onedrive/autorizacao/servico.py` | `autorizacao`; contrato `interfaces/google-oauth.md` | componente-novo, delta-de-contrato-externo | HIGH | Troca do código, renovação e revogação com `urllib`; classificação das falhas; endereços só por injeção (T020, T021, D-01, D-08, D-09, D-14). Alta: é por onde o segredo do cliente sai da máquina. |
| `src/email_nf_onedrive/autorizacao/fluxo.py` | `autorizacao`; contrato `interfaces/google-oauth.md` §1 e §2 | componente-novo | HIGH | PKCE, `state`, retorno em `127.0.0.1`, conferência da conta pelo `id_token`, revogação na divergência (T022 a T024, D-02 a D-04, RF-06). |
| `src/email_nf_onedrive/autorizacao/credencial.py` | `autorizacao`; `execucao-monitoramento` (causas de aviso) | componente-novo | MEDIUM | Credencial temporária por caixa e por execução, só em memória; três causas de aviso; nunca escreve o arquivo (T025, D-06, D-08, RF-09). |
| `src/email_nf_onedrive/configuracao/modelo.py` | `configuracao-caixas` §9 | regra-alterada, delta-de-dados | LOW | `Caixa.modo`, `ClienteOAuth`, `Configuracao.cliente_oauth` e `dir_autorizacoes`, todos com padrão que preserva as construções existentes (T004). |
| `src/email_nf_onedrive/configuracao/carregar.py` | `configuracao-caixas` §6 (RF-02, RF-08, RF-11) | regra-alterada | MEDIUM | `AUTH_EMAIL<n>`, `OAUTH_*`, `DIR_AUTORIZACOES`; senha exigida só em `senha`; alertas novos por `stat` (T017, T018, D-10). Média: mexe na validação que decide quais caixas rodam. |
| `src/email_nf_onedrive/coleta/imap.py` | `coleta-email` §6 (RF-01, RF-02); contrato `interfaces/imap-gmail-xoauth2.md` | delta-de-contrato-externo | HIGH | `conectar_oauth` com `AUTHENTICATE XOAUTH2`; `conectar` intacto (T026, D-07). Alta: amplia a lista fechada de comandos IMAP vigiada pela W014. |
| `src/email_nf_onedrive/coleta/coleta.py` | `coleta-email` §11 (EC-01) | regra-alterada | MEDIUM | Escolha do modo por caixa, falhas de autorização com causa própria, log "conectada (modo)"; `conectar` exposto para o `testar-caixa` (T028). |
| `src/email_nf_onedrive/execucao/resumo.py` | `execucao-monitoramento` §9 | regra-alterada | LOW | `falhas_autorizacao` e segmento condicional na linha de resumo (T027, D-13). |
| `src/email_nf_onedrive/execucao/ciclo.py` | `execucao-monitoramento` §6 | regra-alterada | MEDIUM | `Dependencias.servico_autorizacao` e `ao_exibir_endereco`; provedor construído só com caixa em `oauth`; contagem das falhas de autorização (T029). |
| `src/email_nf_onedrive/cli.py` | `execucao-monitoramento` §6; contrato `interfaces/cli-e-env.md` | delta-de-contrato-externo | MEDIUM | Subcomandos `autorizar-caixa` e `testar-caixa`; `verificar-config` mostra o modo e o estado da autorização (T030 a T032). |
| `.env.example` | `configuracao-caixas` §9 | regra-alterada | LOW | Bloco das variáveis novas (T002). |
| `.gitignore` | infraestrutura do repositório | regra-nova | MEDIUM | `autorizacoes/` fora do versionamento (T001). Média: é a barreira contra o envio da autorização durável ao remoto. |
| `tests/integracao/dubles.py`, `tests/integracao/conftest.py` | transversal | componente-novo | LOW | `ConexaoFalsa.authenticate`, `ServicoAutorizacaoFalso`, fixtures `servico_oauth` e `cenario_oauth` (T005 a T007). |
| `tests/unidade/test_configuracao.py`, `tests/integracao/test_coleta.py` | `configuracao-caixas`, `coleta-email` | regra-alterada | MEDIUM | Casos novos; `COMANDOS_PERMITIDOS` ganhou `AUTHENTICATE`, única expectativa antiga alterada (T008, T012). |
| `tests/unidade/test_autorizacao_arquivo.py`, `test_autorizacao_fluxo.py`; `tests/integracao/test_autorizacao_servico.py`, `test_ciclo_oauth.py`, `test_ciclo_oauth_falhas.py`, `test_autorizar_caixa.py`, `test_cli_caixas.py` | `autorizacao` e os contratos novos | componente-novo | LOW | 7 arquivos de teste novos (T009 a T011, T013 a T016, T037). |
| `docs/instalacao-e-operacao.md`, `README.md` | `execucao-monitoramento` (RF-12, RF-13 da spec) | regra-alterada | LOW | Seção 16 do guia (RF-13, RF-14) e remissões nas seções 5, 7, 9, 11.1, 12 e 14; README com os dois modos (T034 a T036). |
| `tests/RASTREABILIDADE.md` | transversal | regra-alterada | LOW | Mapa da feature 002, acrescentado sem tocar no da 001 (T037). |

Não foram tocados: `envio/`, `registro/` (inclusive `esquema.sql`: nenhuma migração), `execucao/avisos.py`, `execucao/trava.py`, `execucao/telegram.py`, `execucao/logs.py`, `segredos.py`, `coleta/mime.py`, `classificacao.py`, `janela.py` e `utf7.py`.

## Diff conceitual por componente

**`configuracao-caixas`.** A caixa deixa de ser sinônimo de "endereço e senha". Cada caixa tem um modo, `senha` ou `oauth`, com `senha` como padrão, de modo que o `.env` atual é lido exatamente como antes. A exigência de senha vale só em `senha`; em `oauth`, uma senha presente é ignorada e vira alerta, para que a senha de terceiro não fique guardada (RN-09). As credenciais do cliente OAuth são globais e só são exigidas havendo caixa em `oauth`: sua falta invalida essas caixas, e não a instalação. A validação continua toda anterior à rede; o estado da autorização é conferido por `stat`, sem abrir o arquivo. Caixa em `oauth` sem arquivo de autorização é válida na configuração e falha só na coleta.

**`autorizacao` (novo).** Quatro módulos com uma responsabilidade cada: o arquivo (o que fica em disco), o serviço (o que vai ao Google), o fluxo (o consentimento, só no `autorizar-caixa`) e a credencial (a renovação, a cada execução). O único segredo em repouso é a autorização durável; a credencial temporária vive em memória e é registrada para mascaramento assim que recebida. O ciclo nunca escreve nem apaga o arquivo: só o `autorizar-caixa` grava, de forma atômica. A conta que consentiu é conferida pelo `id_token`, e a divergência revoga a concessão recém-emitida.

**`coleta-email`.** A fachada IMAP ganha um segundo modo de autenticar, `AUTHENTICATE XOAUTH2`, e nada mais: `conectar` não mudou, e os comandos depois da autenticação são os mesmos (`LIST`, `EXAMINE`, `SEARCH SINCE`, `FETCH BODY.PEEK[]`, `LOGOUT`). A recusa do `AUTHENTICATE` tem causa própria, `autorizacao`, distinta de `autenticacao`, e o desafio JSON do servidor vai ao log, mascarado e truncado. A credencial é obtida antes de abrir a conexão; se a obtenção falha, a conexão IMAP nem é aberta.

**`execucao-monitoramento`.** Três causas de aviso novas entram no gerenciador existente, sem mudança nele: `caixa<n>:autorizacao` (permanente), `caixa<n>:autorizacao-servico` (transitória) e `oauth:cliente` (global, um aviso só). A linha de resumo ganha "`k` de autorização" apenas quando `k` > 0, de modo que as instalações sem OAuth veem a mesma linha de sempre, salvo o sufixo do modo em "conectada". O CLI ganha dois subcomandos que não usam trava, registro nem aviso.

**Escopo concedido maior que o uso (RN-03).** O Google só oferece `https://mail.google.com/` para IMAP com OAuth. O acesso efetivo segue restrito à leitura pela lista fechada de comandos, e a credencial só é usada no IMAP, nunca na API do Gmail. É o ponto de maior atenção para extrações futuras: qualquer comando IMAP novo passa a ter consequência maior do que tinha com senha de app.

## Preservadas

Sem extração de legado, não há regras 🟢 formais. Seguem verdadeiros, conferidos pelos 236 testes anteriores: a caixa somente leitura (RN-01 da 001, W014, agora com `AUTHENTICATE` na lista); o `.env` lido sem tocar em `os.environ`; a validação anterior à rede; a falha de uma caixa que não para as demais (RN-09 da 001); a chave do registro por endereço, que garante a RN-07 sem código novo; a supressão de avisos por 6 h e o aviso de recuperação; o mascaramento de segredos em log, aviso e terminal; os códigos de saída 0, 1 e 2; o esquema do SQLite.

## Modificadas

Regras das specs alteradas por esta feature, a convergir em `_reversa_sdd/addenda/` pelo `/reversa-sync`:

| Origem | Antes | Depois |
|--------|-------|--------|
| `configuracao-caixas` RF-02 e RF-08 | toda caixa exige `SENHA_EMAIL<n>` não vazia | só as caixas em modo `senha`; em `oauth` a senha é ignorada, com alerta |
| `configuracao-caixas` §9, entidade `Caixa` | endereço, senha, pasta, servidor, destino, empresa | acrescida de `modo`; `Configuracao` acrescida de `cliente_oauth` e `dir_autorizacoes` |
| `configuracao-caixas` RF-11 (alertas) | permissão do `.env`, senha órfã, Telegram incompleto | acrescidos: senha em caixa `oauth`, `AUTH_EMAIL<n>` órfã, permissão do arquivo e do diretório de autorizações |
| `coleta-email` RF-01 e RF-02; W014 da feature 001 | autenticação só por `LOGIN`; lista fechada de 7 comandos | `LOGIN` ou `AUTHENTICATE XOAUTH2`, nunca os dois na mesma conexão; lista fechada de 8 comandos |
| `coleta-email` EC-01 | falha de autenticação: causa `caixa<n>:autenticacao` | mantida para `senha`; em `oauth`, as causas `caixa<n>:autorizacao`, `caixa<n>:autorizacao-servico` e `oauth:cliente` |
| `coleta-email`, log de conexão | "caixa n: conectada" | "caixa n: conectada (senha)" ou "caixa n: conectada (oauth)" |
| `execucao-monitoramento` §9, `ResumoExecucao` | sem distinção das falhas de autorização | campo `falhas_autorizacao` e segmento condicional na linha de resumo |
| `execucao-monitoramento` §6, subcomandos | `executar`, `verificar-config`, `testar-onedrive` | acrescidos `autorizar-caixa <n>` e `testar-caixa [<n>]`; `verificar-config` mostra o modo e o estado da autorização |
