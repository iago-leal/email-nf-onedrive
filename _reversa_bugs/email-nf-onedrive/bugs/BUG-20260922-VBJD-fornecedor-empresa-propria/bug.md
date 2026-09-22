---
schema_version: 1
id: BUG-20260922-VBJD
display_number: 1
title: Fornecedor recebe o nome da própria empresa em encaminhamento interno
status: resolved
phase: observing
severity: high
priority: P1
created: 2026-09-22
updated: 2026-09-22

origin:
  type: inspection
  external_ref: null

area: envio-onedrive
module: envio
feature: nomeacao
labels: [spec-gap, nomes-de-arquivo]

visibility: normal
security_suspected: false

reproduction:
  classification: deterministic
  rate: "41/41 (produção); 5/5 (sintético)"
  suspected_triggers: []

blocking: []

relationships: []

traceability:
  specs:
    - "_reversa_sdd/sdd/envio-onedrive.md#6. Requisitos Funcionais"
    - "_reversa_sdd/addenda/001-mvp-email-nf-onedrive.md#Impacto por artefato da extração"
    - "_reversa_sdd/addenda/bug-BUG-20260922-VBJD-v001.md"
  affected_code:
    - src/email_nf_onedrive/envio/nomeacao.py
    - src/email_nf_onedrive/coleta/mime.py
    - src/email_nf_onedrive/coleta/coleta.py
  root_cause:
    state: confirmed
    location: src/email_nf_onedrive/envio/nomeacao.py:146 (nome_destino), com origem de dados em coleta/mime.py:77 e coleta/coleta.py:158
    summary: >
      O fornecedor sai de uma única fonte por anexo: o emitente do próprio XML ou, na falta dele,
      o domínio do From de topo da mensagem. Três lacunas se combinam: (1) não há noção de domínio
      interno, então o domínio da própria empresa vira fornecedor; (2) cada anexo é nomeado isolado,
      e o PDF não herda o emitente do XML da mesma mensagem; (3) mime.analisar_mensagem guarda só o
      From de topo e descarta o remetente original do encaminhamento (message/rfc822 ou encaminhamento
      em linha no corpo).
    evidence:
      - evidence/reproduction.md (5/5 determinístico, dados sintéticos)
      - leitura de nomeacao.py:139-150, mime.py:75-109, coleta.py:153-162
      - produção: 41/80 enviados com AFLAPARTI, 7 deles com XML na mesma mensagem
  reproduction_tests:
    - tests/unidade/test_nomeacao.py::test_remetente_interno_sem_outra_fonte_fica_a_identificar
    - tests/unidade/test_nomeacao.py::test_pdf_herda_o_emitente_do_xml_da_mesma_mensagem
    - tests/unidade/test_nomeacao.py::test_encaminhamento_interno_usa_o_remetente_original
    - tests/unidade/test_mime.py::test_encaminhada_como_anexo_expoe_o_remetente_original
    - tests/unidade/test_mime.py::test_encaminhada_em_linha_expoe_o_remetente_original
    - tests/integracao/test_coleta.py::test_coleta_entrega_ao_envio_as_fontes_do_fornecedor
    - tests/integracao/test_ciclo_arquivamento.py::test_encaminhamento_interno_leva_o_fornecedor_real
  regression_tests:
    - tests/unidade/test_nomeacao.py::test_remetente_externo_sem_outra_fonte_nao_muda
    - tests/unidade/test_nomeacao.py::test_remetente_de_provedor_generico_nao_e_interno
    - tests/unidade/test_nomeacao.py::test_remetente_original_interno_e_pulado
    - tests/unidade/test_nomeacao.py::test_dominio_interno_comparado_sem_diferenca_de_caixa
    - tests/unidade/test_nomeacao.py::test_emitente_do_proprio_xml_vence_o_da_mensagem
    - tests/unidade/test_nomeacao.py::test_emitente_da_mensagem_vence_o_remetente_original
    - tests/unidade/test_nomeacao.py::test_pdf_de_remetente_externo_tambem_herda_o_emitente_do_xml
    - tests/unidade/test_nomeacao.py::test_encaminhamento_por_externo_usa_o_remetente_original
    - tests/unidade/test_mime.py::test_mensagem_direta_nao_tem_remetente_encaminhado
    - tests/unidade/test_mime.py::test_remetentes_citados_no_corpo
    - tests/unidade/test_configuracao.py::test_dominios_internos_sao_os_das_caixas_sem_os_genericos
    - "suíte existente (321 testes verdes antes da correção)"

spec_verdict:
  verdict: spec-desatualizada
  decided_by: iago
  decided_at: 2026-09-22
  addendum: _reversa_sdd/addenda/bug-BUG-20260922-VBJD-v001.md

change_set:
  - {id: CHG-001, kind: code, artifact: src/email_nf_onedrive/coleta/mime.py, diff: fix/CHG-001.diff, applied: 2026-09-22}
  - {id: CHG-002, kind: code, artifact: src/email_nf_onedrive/coleta/coleta.py, diff: fix/CHG-002.diff, applied: 2026-09-22}
  - {id: CHG-003, kind: code, artifact: "src/email_nf_onedrive/configuracao/{modelo,carregar}.py", diff: fix/CHG-003.diff, applied: 2026-09-22}
  - {id: CHG-004, kind: code, artifact: src/email_nf_onedrive/envio/nomeacao.py, diff: fix/CHG-004.diff, applied: 2026-09-22}
  - {id: CHG-005, kind: code, artifact: "src/email_nf_onedrive/envio/envio.py, execucao/ciclo.py", diff: fix/CHG-005.diff, applied: 2026-09-22}
  - {id: CHG-006, kind: specification, artifact: _reversa_sdd/addenda/bug-BUG-20260922-VBJD-v001.md, applied: 2026-09-22}
  - {id: CHG-007, kind: data-repair, artifact: "VPS var/registro.sqlite3 + pasta CONTAS A PAGAR - TESTE", script: fix/CHG-007-reparo.py, applied: 2026-09-22, detalhe: "pasta esvaziada (80 arquivos, grade de 429 subpastas preservada); 84 linhas voltaram a extraido; backup var/registro.sqlite3.bak-20260922T171041Z"}

change_risk:
  level: media
  reasons: [nomes no destino são contrato visível ao financeiro, toca mime/coleta/configuração/nomeação/ciclo, leitura do corpo é heurística, sem mudança de esquema, reversível por git revert]

delivery:
  merged: "main 91c1c39 (fix) + 93afccf (registro), push em 2026-09-22"
  deployed: "VPS medicina-leal, /opt/email-nf-onedrive, commit 93afccf, 2026-09-22 (sem crontab ativo para email-nf)"

post_fix_observation:
  window: "4 ciclos reais na VPS, 2026-09-22 19:23 a 20:30 UTC, lote inteiro escoado"
  started: 2026-09-22T19:23:03Z
  result: sem-recorrencia
  evidence: >
    444 anexos enviados e 346 arquivos na pasta CONTAS A PAGAR - TESTE, que partiu de zero.
    Nenhum arquivo com AFLAPARTI, RIOMARMINERACAO ou CALMAISMINERACAO como fornecedor (0 de 346).
    33 arquivos com A IDENTIFICAR, o sinal previsto de origem não apurada, a investigar à parte.

closure:
  policy: production-service
  satisfied: true
resolution_kind: fixed
---

# Fornecedor recebe o nome da própria empresa em encaminhamento interno

## Summary

Quando o documento chega à caixa por encaminhamento de alguém da própria empresa (remetente `@<dominio-da-empresa>`), o nome gerado usa como fornecedor o domínio desse remetente, e o arquivo vai para o OneDrive como `AFLA - AFLAPARTI ... - BOLETO.pdf`. Na primeira execução real, 41 dos 80 arquivos enviados saíram assim. Como vários documentos passam a ter o mesmo nome, surgem os sufixos `_2` a `_10`, e a analista não distingue os fornecedores pela pasta.

## Expected Behavior

O nome segue a convenção da pasta oficial, `<EMPRESA> - <FORNECEDOR> [NF <n>] - <REF|BOLETO>.<ext>`, adotada no commit `0511931` e registrada no adendo `001-mvp-email-nf-onedrive.md`: o fornecedor vem do emitente da NF-e ou do domínio do remetente. Na pasta oficial, o fornecedor é quem emitiu o documento (por exemplo, a NF 29058 aparece como `NEW LINE`, e não com o nome da empresa).

**spec-gap:** a regra do "domínio do remetente" nunca previu o encaminhamento interno, em que o remetente é a própria empresa, nem os domínios das empresas do grupo. A decisão sobre o comportamento esperado (remetente original do encaminhamento, emitente de um XML da mesma mensagem, marcador neutro) fica para o fix.

## Actual Behavior

`nome_destino` (`envio/nomeacao.py:139`) usa `_rotulo(emitente)` só quando o próprio anexo é o XML da NF-e; nos demais casos, `rotulo_do_endereco(dados.remetente)`, que converte `fulano@<dominio-da-empresa>` em `AFLAPARTI`. Consequências observadas:

- 41 dos 80 arquivos enviados vêm de remetentes `@<dominio-da-empresa>` e levam `AFLAPARTI` como fornecedor.
- Em 7 desses 41, a mensagem tinha também o XML da NF-e, mas o PDF irmão não aproveitou o emitente do XML.
- Colisões de nome: `AFLA - AFLAPARTI - BOLETO.pdf` e `_2` a `_10`; `AFLA - AFLAPARTI - REF.pdf` e `_2`, `_3`.
- Outros 12 enviados vêm de um segundo domínio (`<dominio-do-grupo>`, `MINERION` no nome), possivelmente também interno; a confirmar.

## Steps to Reproduce

1. Caixa configurada com `EMPRESA_EMAIL1`; uma mensagem encaminhada por `alguem@<dominio-da-empresa>` com um PDF de boleto de um fornecedor externo, sem XML.
2. `email-nf-onedrive executar`.
3. O arquivo chega como `<EMPRESA> - AFLAPARTI - BOLETO.pdf`.

## Evidence

- Log da VPS `medicina-leal`, `/opt/email-nf-onedrive/var/log/`, linhas `enviado:` de 2026-09-22T14:22 a 14:32Z (caixa 1).
- Registro `var/registro.sqlite3`, tabela `anexos`: 84 linhas `enviado`, das quais 41 com remetente `@<dominio-da-empresa>`.
- Comparação por número de NF com a pasta oficial (conversa de 2026-09-22): NF 29058 e NF 789 aparecem como `NEW LINE` na oficial e como `AFLAPARTI` no teste.
- Não copiados para cá por conterem nomes de fornecedores e endereços reais, e o repositório ser público.

## Suspected Area

`src/email_nf_onedrive/envio/nomeacao.py`: `nome_destino` e `rotulo_do_endereco`. Possivelmente também o ponto em que os anexos de uma mesma mensagem são nomeados um a um, sem compartilhar o emitente do XML.

## Acceptance Criteria

1. Documento encaminhado por um domínio da própria empresa nunca recebe como fornecedor o rótulo desse domínio.
2. PDF que acompanha o XML de NF-e na mesma mensagem recebe o emitente do XML.
3. A regra escolhida para o encaminhamento interno está registrada na spec efetiva (adendo), com decisão humana.
4. Teste de regressão cobrindo os três casos: encaminhamento interno sem XML, com XML, e remetente externo (que não pode mudar).
5. Na VPS, um ciclo real sem novos arquivos com `AFLAPARTI` como fornecedor, observado pela janela da closure policy.

## Traceability

- Specs: `_reversa_sdd/sdd/envio-onedrive.md#6. Requisitos Funcionais`; adendo `_reversa_sdd/addenda/001-mvp-email-nf-onedrive.md#Impacto por artefato da extração` (convenção de nomes).
- Código afetado: `src/email_nf_onedrive/envio/nomeacao.py`.
- Testes de reprodução e de regressão: nenhum ainda.

## Resolution

**Estado:** `active` / `delivering`. Correção aplicada e verde localmente; falta a entrega, o reparo CHG-007 e a observação da closure policy `production-service`. `resolution_kind` será `fixed` ao fechar.

**Causa raiz (confirmed):** o fornecedor saía de uma única fonte por anexo (`nomeacao.py:146`): o emitente do próprio XML ou o domínio do `From` de topo. Faltavam a noção de domínio interno, o emitente do XML irmão e o remetente original do encaminhamento, que `mime.py` descartava. Evidência: `evidence/reproduction.md` (5/5) e registro da VPS (178 anexos com remetente do domínio da caixa, 109 `Fwd:`).

**Estratégia:** correção direta (sem debate), com ordem de fontes do fornecedor: XML do anexo, XML da mensagem, remetente original externo, remetente externo, `A IDENTIFICAR`. Domínios internos são os das caixas menos os genéricos (a caixa 5 é `@gmail.com`). `<dominio-MINERION>` foi verificado na VPS: é fornecedor, não do grupo.

**Veredito de spec:** `spec-desatualizada` (decisão de iago, 2026-09-22). A RF-01 ainda prescrevia a convenção provisória e a OQ-01 constava aberta; a regra do fornecedor não existia. Adendo `_reversa_sdd/addenda/bug-BUG-20260922-VBJD-v001.md` (deltas 1 a 3).

| CHG | tipo | artefato | diff |
|-----|------|----------|------|
| CHG-001 | code | `coleta/mime.py`: `remetentes_encaminhados` (rfc822 e linhas `De:`/`From:`) | [fix/CHG-001.diff](fix/CHG-001.diff) |
| CHG-002 | code | `coleta/coleta.py`: `emitente_mensagem` e `remetentes_encaminhados` no `AnexoParaEnvio`, também no reenvio | [fix/CHG-002.diff](fix/CHG-002.diff) |
| CHG-003 | code | `configuracao/`: `Configuracao.dominios_internos` | [fix/CHG-003.diff](fix/CHG-003.diff) |
| CHG-004 | code | `envio/nomeacao.py`: `_fornecedor`, `dominios_internos`, `FORNECEDOR_A_IDENTIFICAR` | [fix/CHG-004.diff](fix/CHG-004.diff) |
| CHG-005 | code | `envio/envio.py`, `execucao/ciclo.py`: repasse de `internos` | [fix/CHG-005.diff](fix/CHG-005.diff) |
| CHG-006 | specification | adendo `bug-BUG-20260922-VBJD-v001.md` | (arquivo novo) |
| CHG-007 | data-repair | VPS: 84 linhas `enviado` da pasta de teste voltaram a `extraido` em 2026-09-22, depois de esvaziada a pasta (80 arquivos; a grade de 429 subpastas ficou) | [fix/CHG-007-reparo.py](fix/CHG-007-reparo.py), backup `var/registro.sqlite3.bak-20260922T171041Z` |

**Testes (vermelho → verde):** diff em [fix/testes.diff](fix/testes.diff).

- Vermelho (2026-09-22, antes da correção): `13 failed, 321 passed, 1 error` — `ImportError: FORNECEDOR_A_IDENTIFICAR`; `AttributeError` em `MensagemAnalisada.remetentes_encaminhados`, `AnexoParaEnvio.emitente_mensagem`, `Configuracao.dominios_internos`; ponta a ponta com `'ACME - EMPRESA - BOLETO.pdf' != 'ACME - FORNECEDOR - BOLETO.pdf'`.
- Verde (2026-09-22, depois): `388 passed` na suíte inteira; `27 passed` nos testes de reprodução e regressão listados em `traceability`.

**Simulação de verificação (VPS, 2026-09-22 17:12–17:32, `executar --simular`):** 269 nomes gerados, **0 com `AFLAPARTI`** (eram 41 de 80 antes) e 27 com `A IDENTIFICAR`. A execução parou nos 1200 s em plena caixa 3; ~155 pendentes não foram nomeados. Os 27 são encaminhamentos internos sem XML cujo remetente original não foi achado, entre eles a NF 29058 (`NEW LINE` na pasta oficial); hipótese a investigar: cabeçalho de encaminhamento só na parte `text/html`. Ver `handoff.md`.

**Ponto de atenção registrado:** pela ordem aprovada, o remetente original precede o remetente de topo também quando este é externo (`test_encaminhamento_por_externo_usa_o_remetente_original`). Uma resposta de fornecedor que cite um terceiro externo no corpo passaria a levar o terceiro. Se isso aparecer na observação, a fonte 3 pode ser restrita a remetente de topo interno.

## Agent Notes

- Os 80 arquivos já enviados à pasta de teste têm nomes errados; o fix precisa dizer se eles são renomeados (a ferramenta nunca renomeia no destino, NG-01) ou se a pasta de teste é esvaziada e o envio refeito. Decisão humana.
- Os domínios da própria empresa e do grupo não estão no `.env`; o fix pode precisar de configuração nova (por exemplo, uma lista de domínios internos) ou derivá-los de `EMAIL<n>`.
- Fora deste bug, a registrar à parte: `<outro-emitente>@<dominio-MINERION>` envia notas de `<outro emitente>` (emitente no assunto, sem XML) e o fornecedor sai `MINERION`.
- Na VPS, `/opt/email-nf-onedrive/._autorizacoes` (AppleDouble do `tar`) ainda existe; não foi apagado por esta sessão.
- `tests/RASTREABILIDADE.md` não recebeu as linhas dos testes novos.
- Relação a observar com o cartão 2 do kanban (gravação por vencimento), que também mexe em `envio/`.
