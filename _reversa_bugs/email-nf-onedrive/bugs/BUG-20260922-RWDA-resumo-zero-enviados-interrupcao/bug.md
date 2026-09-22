---
schema_version: 1
id: BUG-20260922-RWDA
display_number: 2
title: Resumo informa 0 enviados quando a execução é interrompida pelo limite de tempo
status: resolved
phase: observing
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
  rate: "1/1 (produção); 5/5 (sintético)"
  suspected_triggers: [limite de 1200 s atingido durante enviar_anexos]

blocking: []

relationships: []

traceability:
  specs:
    - "_reversa_sdd/sdd/execucao-monitoramento.md#6. Requisitos Funcionais"
    - "_reversa_sdd/sdd/execucao-monitoramento.md#11. Edge Cases e Tratamento de Erros"
  affected_code:
    - src/email_nf_onedrive/execucao/ciclo.py
  root_cause:
    state: confirmed
    location: src/email_nf_onedrive/execucao/ciclo.py:165-168 (_Ciclo._executar)
    summary: >
      O ciclo transporta as contagens do envio para o resumo só depois que `enviar_anexos` retorna.
      O Enviador conta certo a cada envio confirmado (envio/envio.py:147), mas a referência ao
      ResultadoEnvio existe apenas dentro da chamada: a TempoEsgotado levantada pelo SIGALRM de
      `limite_duracao` (execucao/trava.py:100) no meio do laço de Enviador.enviar sobe pelo
      _executar e leva o acumulador consigo. O resumo sai com o valor inicial, zero. O mesmo vale
      para falhas_de_anexo.
    evidence:
      - evidence/reproduction.md (5/5 determinístico, dados sintéticos)
      - evidence/repro.py
      - leitura de ciclo.py:165-168, envio.py:144-149, trava.py:94-106
      - VPS medicina-leal, 2026-09-22T14:32:55Z: resumo com 0 enviados, 79 linhas `enviado:` no log
  reproduction_tests:
    - tests/integracao/test_ciclo_falhas.py::test_interrupcao_por_tempo_conta_os_envios_ja_confirmados
  regression_tests:
    - tests/integracao/test_ciclo_falhas.py::test_interrupcao_por_tempo_preserva_o_codigo_e_o_aviso
    - tests/integracao/test_ciclo_falhas.py::test_falha_de_anexo_antes_da_interrupcao_entra_no_resumo
    - tests/integracao/test_envio.py::test_resultado_de_quem_chama_e_preenchido_a_cada_envio
    - tests/integracao/test_ciclo_arquivamento.py::test_simulacao_diz_no_resumo_quantos_anexos_avaliou
    - "suíte existente (389 testes verdes antes da correção)"

spec_verdict:
  verdict: spec-gap
  decided_by: iago
  decided_at: 2026-09-22
  addendum: _reversa_sdd/addenda/bug-BUG-20260922-RWDA-v001.md

change_set:
  - {id: CHG-001, kind: code, artifact: src/email_nf_onedrive/envio/envio.py, diff: fix/CHG-001.diff, applied: 2026-09-22}
  - {id: CHG-002, kind: code, artifact: src/email_nf_onedrive/execucao/ciclo.py, diff: fix/CHG-002.diff, applied: 2026-09-22}
  - {id: CHG-003, kind: code, artifact: src/email_nf_onedrive/execucao/resumo.py, diff: fix/CHG-003.diff, applied: 2026-09-22}
  - {id: CHG-004, kind: specification, artifact: _reversa_sdd/addenda/bug-BUG-20260922-RWDA-v001.md, applied: 2026-09-22}

change_risk:
  level: baixa
  reasons: [só a linha de resumo e um parâmetro opcional, nenhum dado histórico tocado, nenhum contrato externo, sem concorrência, reversível por git revert]

delivery:
  merged: "main b95a42f (fix) + 260d830 (registro), push em 2026-09-22"
  deployed: "VPS medicina-leal, /opt/email-nf-onedrive, commit 260d830, 2026-09-22; pip install . no venv, verificar-config com código 0"

post_fix_observation:
  window: "4 ciclos reais na VPS, 2026-09-22 19:23 a 20:30 UTC; três interrompidos pelo limite"
  started: 2026-09-22T19:23:03Z
  result: sem-recorrencia
  evidence: >
    Resumos dos quatro ciclos: 116, 111, 149 e 68 enviados, somando 444. O registro fechou com
    exatamente 444 anexos em estado enviado, e o log da janela traz 344 linhas `enviado:` mais 100
    `já existia idêntico:`, também 444. Os três primeiros ciclos foram interrompidos pelo limite de
    1200 s e mostraram a contagem correta; antes da correção diriam 0. O quarto terminou sozinho em
    473 s com código 0, o que prova que o caminho normal não mudou.

closure:
  policy: production-service
  satisfied: true
resolution_kind: fixed
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

**Causa raiz (`confirmed`).** O ciclo só transportava as contagens do envio para o resumo depois que
`enviar_anexos` retornava (`execucao/ciclo.py:165-168`). O `Enviador` sempre contou certo, a cada
envio confirmado (`envio/envio.py:147`); o que se perdia era a referência ao `ResultadoEnvio`, que
morria com o quadro de pilha quando a `TempoEsgotado` do SIGALRM subia do meio do laço de envio.

**Veredito de spec: `spec-gap`**, aprovado por iago em 2026-09-22. A RF-11 já exigia as contagens,
mas a spec nunca especificou o limite de duração de 20 min, que existe no código desde o MVP, nem
disse que a execução interrompida também grava resumo. Adendo aditivo em
`_reversa_sdd/addenda/bug-BUG-20260922-RWDA-v001.md`, com três deltas: RF-14 (limite e
interrupção), releitura da RF-11 (contagens do que aconteceu até o encerramento, mais a contagem de
simulados) e o caso EC-RWDA-1.

**`resolution_kind`: `fixed`** (pendente da closure policy).

### Change set

| CHG | tipo | artefato | o que mudou |
|-----|------|----------|-------------|
| CHG-001 | code | `envio/envio.py` | `Enviador` e `enviar_anexos` aceitam `resultado: ResultadoEnvio \| None`; sem o parâmetro, o comportamento é o de antes. |
| CHG-002 | code | `execucao/ciclo.py` | O ciclo cria o acumulador, chama o envio em `try` e contabiliza em `finally`, por `_contabilizar_envio`. |
| CHG-003 | code | `execucao/resumo.py` | Campo `simulados` e o segmento `N simulados` na linha, só quando houver. |
| CHG-004 | specification | `_reversa_sdd/addenda/bug-BUG-20260922-RWDA-v001.md` | Adendo do veredito `spec-gap`. |

Diffs em `fix/CHG-001.diff`, `fix/CHG-002.diff` e `fix/CHG-003.diff`; os testes em `fix/testes.diff`.

### Prova vermelho → verde

Gate 1, com os testes aplicados e a correção ainda ausente:

```
FAILED test_ciclo_falhas.py::test_interrupcao_por_tempo_conta_os_envios_ja_confirmados
        assert '2 enviados' in '... resumo: 1 caixa, 4 extraídos, 0 enviados, 1 falhas, 0 s'
FAILED test_ciclo_falhas.py::test_falha_de_anexo_antes_da_interrupcao_entra_no_resumo
FAILED test_envio.py::test_resultado_de_quem_chama_e_preenchido_a_cada_envio
        TypeError: enviar_anexos() got an unexpected keyword argument 'resultado'
FAILED test_ciclo_arquivamento.py::test_simulacao_diz_no_resumo_quantos_anexos_avaliou
4 failed, 389 passed
```

Gate 2, com o change set aplicado: `393 passed`. A cápsula de reprodução, que exigia `0 enviados`,
passou a falhar nesse assert, e o resumo do mesmo cenário virou
`1 caixa, 4 extraídos, 2 enviados, 1 falhas, 0 s`.

O teste `test_interrupcao_por_tempo_preserva_o_codigo_e_o_aviso` passou desde o gate 1, como se
esperava de regressão pura: ele guarda o código de saída 2 e o aviso `execucao:tempo`, que a
correção não podia mudar.

## Agent Notes

- **Fora do escopo, a registrar como bug novo:** a mesma perda de contagem na **coleta**. `coletar`
  devolve a lista das caixas só no fim (`coleta/coleta.py:234`); interrompida durante a coleta, a
  execução perderia caixas, extraídos e retidos do mesmo modo. Não houve ocorrência real — as duas
  interrupções da VPS caíram no envio — e cobrir isso exigiria transformar `coletar` em gerador.
- Não afeta dados: o registro grava cada envio confirmado, e o ciclo seguinte continua de onde parou.
- Os avisos do Telegram estão desativados na VPS; quando forem ativados, o mesmo número incorreto iria ao aviso da causa `execucao:tempo`.
