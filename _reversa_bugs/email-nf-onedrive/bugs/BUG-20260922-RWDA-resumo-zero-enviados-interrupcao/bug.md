---
schema_version: 1
id: BUG-20260922-RWDA
display_number: 2
title: Resumo informa 0 enviados quando a execução é interrompida pelo limite de tempo
status: open
phase: triaging
severity: medium
priority: P2
created: 2026-09-22
updated: 2026-09-22

origin:
  type: inspection
  external_ref: null

area: execucao-monitoramento
module: execucao
feature: resumo
labels: [observabilidade]

visibility: normal
security_suspected: false

reproduction:
  classification: deterministic
  rate: "1/1"
  suspected_triggers: [limite de 1200 s atingido durante enviar_anexos]

blocking: []

relationships: []

traceability:
  specs:
    - "_reversa_sdd/sdd/execucao-monitoramento.md#6. Requisitos Funcionais"
    - "_reversa_sdd/sdd/execucao-monitoramento.md#11. Edge Cases e Tratamento de Erros"
  affected_code:
    - src/email_nf_onedrive/execucao/ciclo.py
  root_cause: null
  reproduction_tests: []
  regression_tests: []

spec_verdict: null

change_set: []

closure:
  policy: production-service
  satisfied: false
resolution_kind: null
---

# Resumo informa 0 enviados quando a execução é interrompida pelo limite de tempo

## Summary

Na primeira execução real, a ferramenta enviou 80 arquivos e foi interrompida pelo limite de 1200 s. A linha final do log disse `0 enviados`. Quem acompanha pelo log, ou por um aviso futuro no Telegram, conclui que nada foi arquivado, quando o registro e o OneDrive mostram o contrário.

## Expected Behavior

`execucao-monitoramento` RF-11: "registrar no fim de cada execução um resumo com a duração, as caixas processadas e as contagens de anexos extraídos, enviados e com falha". A execução interrompida por tempo também termina com resumo (o próprio código o grava), e as contagens devem refletir o que de fato aconteceu até a interrupção.

## Actual Behavior

`resumo: 5 caixas, 644 extraídos, 0 enviados, 220 retidos, 1 falhas, 1200 s` (2026-09-22T14:32:55Z), precedido de `execução interrompida: execução passou de 1200 s`. No mesmo log há 79 linhas `enviado:`; a pasta de teste tem 80 arquivos; o registro, 84 linhas `enviado`.

Em `execucao/ciclo.py:165-167`, a contagem só é somada depois que `enviar_anexos` retorna (`resumo.enviados += envio.enviados`). A `TempoEsgotado` levantada no meio do laço de envio (`limite_duracao`, `ciclo.py:212`) pula essa soma, e o resumo sai com o valor inicial, 0. O mesmo deve valer para `envio.falhas_de_anexo`.

## Steps to Reproduce

1. Registro com anexos pendentes cujo envio ultrapasse o limite (ou `Dependencias.limite_s` reduzido num teste).
2. `email-nf-onedrive executar` até a interrupção por tempo.
3. A linha `resumo:` mostra `0 enviados`, embora haja linhas `enviado:` no log.

## Evidence

- Log da VPS `medicina-leal`, `/opt/email-nf-onedrive/var/log/`, linhas de 2026-09-22T14:22 a 14:32:55Z.
- `rclone size` da pasta de teste: 80 objetos, 9,587 MiB.
- Registro `var/registro.sqlite3`: 84 `enviado`, 340 `extraido`, 220 `retido`.

## Suspected Area

`src/email_nf_onedrive/execucao/ciclo.py`, `_executar`: soma das contagens do envio só no retorno de `enviar_anexos`; `envio/` pode precisar expor a contagem parcial (por exemplo, atualizando um contador compartilhado a cada envio confirmado).

## Acceptance Criteria

1. Com a execução interrompida por tempo durante o envio, o resumo mostra o número de envios confirmados até a interrupção.
2. O código de saída e a causa `execucao:tempo` seguem como hoje.
3. Teste de regressão com limite reduzido e envio lento simulado.
4. Na VPS, um ciclo interrompido com resumo coerente com as linhas `enviado:`, na janela de observação.

## Traceability

- Specs: `_reversa_sdd/sdd/execucao-monitoramento.md#6. Requisitos Funcionais` (RF-11); `#11. Edge Cases e Tratamento de Erros`.
- Código afetado: `src/email_nf_onedrive/execucao/ciclo.py`.
- Testes: nenhum ainda.

## Resolution

(preenchida pelo `/reversa-debugger-fix`)

## Agent Notes

- Não afeta dados: o registro grava cada envio confirmado, e o ciclo seguinte continua de onde parou.
- Os avisos do Telegram estão desativados na VPS; quando forem ativados, o mesmo número incorreto iria ao aviso da causa `execucao:tempo`.
