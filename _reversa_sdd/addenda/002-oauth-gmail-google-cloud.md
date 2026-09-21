# Adendo: acesso às caixas do Gmail por OAuth 2.0

> Identificador: `002-oauth-gmail-google-cloud`
> Data: `2026-09-21`
> Cenário: `greenfield` (âncora: `prd.md` e as quatro specs em `sdd/`, lidas com o adendo `001-mvp-email-nf-onedrive.md`)
> Diferente da feature 001, esta altera código que já existia; por isso os tipos de impacto seguem os do `legacy-impact.md` (`regra-alterada`, `regra-nova`, `delta-de-dados`, `delta-de-contrato-externo`), e não o `componente-novo` uniforme do greenfield puro.
> Sincronização **parcial**: 38 de 39 ações concluídas. Falta a T039, verificação manual do operador contra o Google real, que também fecha as premissas P-01 a P-03. Uma reexecução do `/reversa-sync` depois dela acrescentará uma seção de atualização.

## Vigência

Vigente desde 2026-09-21.

## Resumo da entrega

A feature permite que a ferramenta entre nas caixas do Gmail por OAuth 2.0, com projeto próprio no Google Cloud, como alternativa à senha de app. O motivo foi o teste de 2026-09-21: as cinco caixas recusaram o login com as senhas comuns, e a senha de app obrigaria cada titular a ativar a verificação em duas etapas. Cada caixa passa a ter um modo, `senha` (padrão, de modo que o `.env` atual é lido como antes) ou `oauth`; o operador autoriza cada caixa na própria máquina com `autorizar-caixa <n>`, copia a autorização à VPS e confere o acesso com `testar-caixa`. A cada execução, a credencial temporária é renovada em memória, e as falhas de autorização têm causas de aviso próprias. Acompanham o código a seção 16 do guia de instalação e operação, o `README.md`, o `.env.example` e o mapa de rastreabilidade, com 361 testes automatizados passando (236 anteriores e 125 novos). O envio ao OneDrive e o registro de processados não foram tocados.

Ações concluídas: 38 de 39 (T001 a T038).

## Impacto por artefato da extração

| Artefato | Seção | Tipo de impacto | Delta |
|----------|-------|-----------------|-------|
| `_reversa_sdd/prd.md` | `#4. Escopo (in)` | componente-novo | O escopo ganha o subpacote `autorizacao/` (arquivo, serviço, fluxo e credencial), sem spec própria e descrito no roadmap §5 da feature 002, que concentra tudo o que fala com o Google. |
| `_reversa_sdd/prd.md` | `#6. Restrições` | regra-alterada | A restrição do IMAP no Google Workspace passa a ser atendida por OAuth 2.0 com projeto sem faturamento na conta do operador; a senha de app vira a alternativa, e o consentimento se faz fora da VPS, como no Rclone. |
| `_reversa_sdd/prd.md` | `#7. Dependências externas` | delta-de-contrato-externo | Entram o serviço de autorização do Google, com endereços constantes do código e alteráveis só por injeção (D-14), e o projeto no Google Cloud com cliente do tipo aplicativo para computador; nenhuma API do Google é ativada. |
| `_reversa_sdd/sdd/configuracao-caixas.md` | `#6. Requisitos Funcionais` | regra-alterada | RF-02 e RF-08 passam a exigir `SENHA_EMAIL<n>` só em modo `senha`; entram `AUTH_EMAIL<n>`, `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` (exigidas só havendo caixa em `oauth`) e `DIR_AUTORIZACOES`; o RF-11 ganha os alertas de senha em caixa `oauth`, `AUTH_EMAIL<n>` órfã e permissão das autorizações. |
| `_reversa_sdd/sdd/configuracao-caixas.md` | `#9. Modelo de Dados` | delta-de-dados | `Caixa` ganha `modo`, e `Configuracao` ganha `cliente_oauth` e `dir_autorizacoes`; a entidade `Autorizacao` é um JSON por caixa, nomeado pelo endereço em minúsculas, com permissão 600 em diretório 700 (D-05, `data-delta.md` da feature). |
| `_reversa_sdd/sdd/configuracao-caixas.md` | `#12. Segurança e Privacidade` | regra-nova | A autorização durável é o único segredo novo em repouso, fora do versionamento pelo `.gitignore`; em `oauth`, a senha presente no `.env` é ignorada, mascarada e alertada (RN-09), e o estado da autorização é conferido por `stat`, sem abrir o arquivo. |
| `_reversa_sdd/sdd/coleta-email.md` | `#6. Requisitos Funcionais` | delta-de-contrato-externo | O RF-01 autentica por `LOGIN` ou por `AUTHENTICATE XOAUTH2`, nunca os dois na mesma conexão; a lista fechada do RF-02 passa de 7 para 8 comandos, e o W014 da feature 001 deve ser lido com a redação do W022. |
| `_reversa_sdd/sdd/coleta-email.md` | `#10. Integrações e Dependências` | delta-de-contrato-externo | Em `oauth`, a credencial temporária é obtida antes de abrir a conexão IMAP, que nem é aberta se a obtenção falha; contrato em `interfaces/imap-gmail-xoauth2.md` da feature. |
| `_reversa_sdd/sdd/coleta-email.md` | `#11. Edge Cases e Tratamento de Erros` | regra-alterada | O EC-01 vale só para `senha`; em `oauth`, a recusa tem as causas `caixa<n>:autorizacao`, `caixa<n>:autorizacao-servico` e `oauth:cliente`, e o log de conexão passa a "caixa n: conectada (senha)" ou "(oauth)". |
| `_reversa_sdd/sdd/coleta-email.md` | `#12. Segurança e Privacidade` | regra-alterada | O escopo concedido, `https://mail.google.com/`, é maior que o uso: a leitura só é garantida pela lista fechada de comandos, e a credencial nunca é usada fora do IMAP (RN-03, W023). |
| `_reversa_sdd/sdd/execucao-monitoramento.md` | `#6. Requisitos Funcionais` | delta-de-contrato-externo | O CLI ganha `autorizar-caixa <n>` (códigos 0 e 2) e `testar-caixa [<n>]` (0, 1 e 2), sem trava, registro nem aviso; o `verificar-config` mostra o modo e o estado da autorização, ainda sem rede; o guia ganha a seção 16 (RF-13 e RF-14 da feature). |
| `_reversa_sdd/sdd/execucao-monitoramento.md` | `#9. Modelo de Dados` | delta-de-dados | `ResumoExecucao` ganha `falhas_autorizacao`, e a linha de resumo, o segmento "`k` de autorização" só quando `k` > 0; o esquema do SQLite não mudou. |
| `_reversa_sdd/sdd/execucao-monitoramento.md` | `#11. Edge Cases e Tratamento de Erros` | regra-nova | Três causas de aviso entram no gerenciador existente, sem mudança nele: autorização recusada (permanente), serviço indisponível após uma tentativa de 60 s (transitória) e cliente OAuth recusado (global, um aviso por execução e nenhuma requisição depois dele). |
| `_reversa_sdd/sdd/execucao-monitoramento.md` | `#12. Segurança e Privacidade` | regra-nova | O ciclo nunca escreve nem apaga arquivo de autorização, e só o `autorizar-caixa` grava, de forma atômica; `client_secret`, código, verificador, credencial durável, credencial temporária e `id_token` são mascarados em log, aviso e terminal. |

## Regras sob vigilância

W022 a W037, na seção "Observações" de [`_reversa_forward/002-oauth-gmail-google-cloud/regression-watch.md`](../../_reversa_forward/002-oauth-gmail-google-cloud/regression-watch.md). O W022 revisa o W014 da feature 001. Por ser feature greenfield, nenhum item tem ainda peso de regressão; ganham esse peso quando uma futura extração `/reversa` os confirmar como 🟢.

## Fontes

- `_reversa_forward/002-oauth-gmail-google-cloud/legacy-impact.md`
- `_reversa_forward/002-oauth-gmail-google-cloud/regression-watch.md`
- `_reversa_forward/002-oauth-gmail-google-cloud/requirements.md`
- `_reversa_forward/002-oauth-gmail-google-cloud/progress.jsonl`
- `_reversa_forward/002-oauth-gmail-google-cloud/actions.md`
