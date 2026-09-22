---
schema_version: 1
id: BUG-20260922-2FVK
display_number: 3
title: Anexo de NF sem palavra-chave no nome é retido por engano
status: open
phase: triaging
severity: medium
priority: P2
created: 2026-09-22
updated: 2026-09-22

origin:
  type: inspection
  external_ref: null

area: coleta-email
module: coleta
feature: classificacao
labels: [falso-negativo]

visibility: normal
security_suspected: false

reproduction:
  classification: deterministic
  rate: "1/1"
  suspected_triggers: [assunto com "nota" sem "fiscal"; nome do arquivo sem termo da lista]

blocking: []

relationships: []

traceability:
  specs:
    - "_reversa_sdd/sdd/coleta-email.md#6. Requisitos Funcionais"
    - "_reversa_sdd/addenda/001-mvp-email-nf-onedrive.md#Impacto por artefato da extração"
  affected_code:
    - src/email_nf_onedrive/coleta/classificacao.py
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

# Anexo de NF sem palavra-chave no nome é retido por engano

## Summary

Uma nota fiscal enviada como `Afla 414.pdf`, com o assunto "segue a nota das diárias do hotel ...", foi classificada como `sem-classificacao` e ficou retida para revisão. Na pasta oficial, a analista arquivou esse documento (NF 414) duas vezes. O documento não se perde, porque o retido aparece no log para revisão manual, mas deixa de chegar sozinho ao OneDrive.

## Expected Behavior

Pela spec, a classificação acerta: `coleta-email` RF-05 manda classificar como `palavra-chave` quando o nome ou o assunto contém um termo da lista do RF-06 (`nf`, `nfe`, `nf-e`, `nfs-e`, `nota fiscal`, `danfe`, `boleto`, `fatura`, `cobranca`, `duplicata`), e o adendo 001 (RN-03, D-08) manda reter o que não for reconhecido. "nota", sozinha, não está na lista.

O defeito está na lista, que não cobre um caso real e frequente: o assunto informal com "nota" sem "fiscal". O fix decide entre ampliar a lista (com o risco de falsos positivos, como "nota de débito" ou "nota de repúdio"), usar o conteúdo do PDF ou manter a retenção. `spec_verdict` provável: `spec-desatualizada`, a confirmar com decisão humana.

## Actual Behavior

Registro, caixa 1: `nome_original = "Afla 414.pdf"`, `classe = sem-classificacao`, `estado = retido`, mensagem de 2026-09-10. No log de 2026-09-22, a linha `retido para revisão: Afla 414.pdf (...)`.

## Steps to Reproduce

1. Mensagem com assunto "segue a nota das diárias" e anexo PDF de nome sem termo da lista.
2. `email-nf-onedrive executar` (ou `--simular`).
3. O anexo é retido como `sem-classificacao`.

## Evidence

- Registro `var/registro.sqlite3` na VPS `medicina-leal`, tabela `anexos`, linha com `nome_original = 'Afla 414.pdf'`.
- Log da VPS, linha `retido para revisão` de 2026-09-22 (execução real).
- Pasta oficial: dois arquivos com NF 414 do mesmo fornecedor (comparação de 2026-09-22).

## Suspected Area

`src/email_nf_onedrive/coleta/classificacao.py`: `PALAVRAS_CHAVE` e `classificar`.

## Acceptance Criteria

1. O caso do assunto "segue a nota ..." com PDF é tratado conforme a decisão registrada em adendo.
2. Teste de regressão com o caso, e com ao menos um contraexemplo que deve continuar retido.
3. Medição da mudança sobre os 220 retidos da primeira execução: quantos passariam a ser enviados e quantos seriam falsos positivos.

## Traceability

- Specs: `_reversa_sdd/sdd/coleta-email.md#6. Requisitos Funcionais` (RF-05, RF-06); adendo `_reversa_sdd/addenda/001-mvp-email-nf-onedrive.md` (RN-03, retenção).
- Código afetado: `src/email_nf_onedrive/coleta/classificacao.py`.
- Testes: nenhum ainda.

## Resolution

(preenchida pelo `/reversa-debugger-fix`)

## Agent Notes

- É um caso de uma amostra maior: há 220 retidos na primeira execução. Antes de ampliar a lista, vale medir sobre eles, porque a retenção foi uma decisão deliberada (sessão de esclarecimentos de 2026-09-18, resposta 1c).
- Os CT-e retidos são outro assunto (escopo, no kanban), e não este bug.
