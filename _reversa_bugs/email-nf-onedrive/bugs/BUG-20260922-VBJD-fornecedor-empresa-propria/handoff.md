# Handoff · BUG-20260922-VBJD · sessão de 2026-09-22

> Para retomar: leia este arquivo e o `bug.md` da mesma pasta. O bug está `active` / `delivering`;
> falta **um item** da closure policy `production-service`: um ciclo real observado sem `AFLAPARTI`.

## Onde o trabalho parou

A correção está escrita, testada, commitada, publicada e instalada na VPS. Os arquivos errados da
pasta de teste foram apagados e o registro foi reparado. A última ação foi uma **simulação** na VPS,
que confirmou o efeito da correção. Falta a execução real e a observação.

## O que foi feito (em ordem)

1. **Reprodução** determinística, 5/5, com dados sintéticos: `evidence/reproduction.md` e `evidence/repro.py`.
2. **Causa raiz `confirmed`**: o fornecedor saía de uma única fonte por anexo (XML do próprio anexo ou
   domínio do `From` de topo). Faltavam a noção de domínio interno, o emitente do XML irmão e o
   remetente original do encaminhamento, que `mime.py` descartava.
3. **Plano aprovado**: `fix/plan.html`.
4. **Gate 1** (testes vermelhos): `fix/testes.diff`. Antes da correção, `13 failed, 321 passed, 1 error`.
5. **Gate 2** (correção): `fix/CHG-001.diff` a `fix/CHG-005.diff`. Depois, `388 passed` na suíte inteira.
6. **Veredito de spec `spec-desatualizada`** (decisão de iago): adendo
   `_reversa_sdd/addenda/bug-BUG-20260922-VBJD-v001.md`.
7. **Commits e push** em `main`: `91c1c39` (fix) e `93afccf` (registro de bugs).
8. **Instalação na VPS** `medicina-leal`, `/opt/email-nf-onedrive`, commit `93afccf`. Não há crontab
   para o usuário `email-nf`: nada roda sozinho.
9. **Pasta esvaziada**: 80 arquivos apagados de `AFLA Financeiro/CONTAS A PAGAR - TESTE`; as 429
   subpastas da grade por vencimento foram preservadas de propósito.
10. **CHG-007 (data-repair) aplicado**: 84 linhas `enviado` voltaram a `extraido`. Backup em
    `var/registro.sqlite3.bak-20260922T171041Z`. Registro hoje: 424 `extraido`, 220 `retido`, 0 `enviado`.
11. **Simulação** (`executar --simular`, 2026-09-22 17:12 a 17:32): 269 nomes, **0 `AFLAPARTI`**,
    27 `A IDENTIFICAR`. Parou nos 1200 s em plena caixa 3; ~155 pendentes não chegaram a ser nomeados.

## Regra do fornecedor, como ficou

Primeira fonte que responder: (1) XML de NF-e do próprio anexo; (2) XML de outro anexo da mesma
mensagem; (3) remetente original do encaminhamento (anexo `message/rfc822` ou bloco `De:`/`From:` no
corpo `text/plain`), se não for interno; (4) remetente de topo, se não for interno; (5) `A IDENTIFICAR`.
Domínios internos = domínios das caixas menos os provedores genéricos; na VPS resolvem para
aflaparti.com, calmaismineracao.com e riomarmineracao.com.br (a caixa 5 é `@gmail.com` e fica de fora).

## O que falta, na ordem recomendada

1. **Investigar os 27 `A IDENTIFICAR`** (precisa de aval: lê corpo de mensagens reais por IMAP).
   Hipótese: são encaminhamentos cujo cabeçalho só existe na parte `text/html`, que a leitura não cobre.
   Caso emblemático: a NF 29058, que na pasta oficial é `NEW LINE`. Confirmada a hipótese, registrar
   bug novo (estender a leitura ao HTML), em vez de reabrir este.
2. **Corrigir o BUG-20260922-RWDA** (resumo com "0 enviados" após interrupção). A simulação reforçou o
   defeito: o resumo saiu `5 caixas, 8 extraídos, 0 enviados, 3 retidos, 1 falhas, 1200 s` e não
   menciona os 269 nomes simulados.
3. **Execução real e observação** (fecha este bug):
   ```
   ssh medicina-leal
   cd /opt/email-nf-onedrive && sudo -u email-nf .venv/bin/email-nf-onedrive executar
   ```
   Serão precisos dois ou três ciclos para escoar os 424 pendentes, porque cada um para nos 1200 s.
   Critério: nenhum arquivo novo com `AFLAPARTI` como fornecedor. Conferência rápida:
   ```
   sudo -u email-nf rclone lsf --files-only --max-depth 1 \
     "onedrive-financeiro:AFLA Financeiro/CONTAS A PAGAR - TESTE" | grep -c " - AFLAPARTI"
   ```
4. **Fechar o bug**: `post_fix_observation.result`, `status: resolved`, `resolution_kind: fixed`,
   `closure.satisfied: true` e a trava `DONE.md`. Depois, `/reversa-debugger-graph` para as views.

## Pendências fora do ciclo deste bug

- **Não commitado:** as anotações de entrega, instalação e reparo no `bug.md`, mais este handoff.
- **Bug a registrar:** fornecedor que envia por domínio de terceiro (o emitente vem no assunto, sem XML);
  hoje o nome leva o dono do domínio.
- **Ponto de atenção da regra:** a fonte 3 vale também quando o remetente de topo é externo. Uma resposta
  de fornecedor que cite terceiro no corpo levaria o terceiro. Se aparecer na observação, restringir a
  fonte 3 a remetente de topo interno (teste `test_encaminhamento_por_externo_usa_o_remetente_original`).
- **VPS:** `/opt/email-nf-onedrive/._autorizacoes`, sobra do `tar`; não foi apagado.
- **`tests/RASTREABILIDADE.md`** ainda não lista os testes novos.
- **`.claude`** tem alteração não commitada, herdada do início da sessão.
- **Tarefas fantasma:** chegaram duas notificações de tarefas em segundo plano que esta sessão não
  iniciou ("rodar a simulação", "rodar a execução real"), ambas mortas por queda de SSH (código 255).
  Nenhuma execução real ocorreu; o registro comprova. Se houver outra sessão aberta neste projeto,
  convém fechá-la antes da execução real, para não gastar a janela de observação.

## Anonimização (repositório público)

Nomes de fornecedores, endereços e domínios reais **não entram** nos arquivos deste registro. Use os
marcadores já adotados: `<dominio-da-empresa>`, `<dominio-MINERION>`, `<outro emitente>`. Os fatos
brutos ficam no log e no `registro.sqlite3` da VPS.
