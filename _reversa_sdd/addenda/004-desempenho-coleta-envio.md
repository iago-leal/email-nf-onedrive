# Adendo: coleta sem download repetido e envio em paralelo

> Identificador: `004-desempenho-coleta-envio`
> Data: `2026-09-23`
> Origem: pedido de iago em 2026-09-23, após a janela de observação da feature 003 medir ~85 min para escoar o lote
> Imutável: uma revisão futura vira `004-desempenho-coleta-envio-v002.md`; a spec original não é editada.

## Diagnóstico (log da janela de 2026-09-22)

- **Envio:** 528 operações, mediana de 5,8 s e p90 de 8,9 s por anexo, em série: 52 min só de envio.
  Cada anexo faz quatro chamadas ao Rclone (hash local, consulta do nome, cópia, conferência).
- **Coleta:** cada ciclo baixava de novo, com anexos, todas as mensagens desde o anexo pendente mais
  antigo (CE RF-03), ~8 min por ciclo, para reencontrar os pendentes; com o limite de 20 min, restavam
  ~12 min para enviar.

## Delta 1: `coleta-email.md`, CE RF-03 (janela) — leitura das mensagens resolvidas

> A janela de busca não muda. Antes de baixar o corpo, a coleta lê em lote só o `Message-ID` das
> mensagens da janela (`FETCH BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)]`, 200 por comando) e descarta as
> **resolvidas**: as que têm anexo registrado e nenhum pendente (`extraido` ou `falha-envio`), ou só
> ocorrência. Mensagem sem `Message-ID` continua sendo baixada, porque o identificador substituto
> depende do corpo.

A RN-07 fica intacta: nenhuma cópia de anexo sobrevive à execução, de modo que o pendente ainda é
baixado de novo até ser enviado. A alternativa de guardar os pendentes entre execuções foi descartada
por contrariar a RN-07. A RN-01 também: a leitura do cabeçalho é `PEEK` e não marca a mensagem como lida.

## Delta 2: `envio-onedrive.md`, protocolo por anexo — até 4 envios simultâneos

> Até `ENVIOS_SIMULTANEOS` (4) anexos são enviados ao mesmo tempo, cada um pelo protocolo de sempre
> (pasta existe, nome livre ou idêntico, cópia sem sobrescrever, conferência de tamanho e hash).
> Anexos com o mesmo caminho de destino, comparado sem distinguir maiúsculas como o OneDrive, seguem
> juntos e em sequência, para que a escolha do sufixo `_n` veja o arquivo recém-enviado.
> Registro, contagens e cópia local ficam na thread principal.

**Interrupção pelo limite de tempo (RF-14, adendo `bug-BUG-20260922-RWDA-v001`):** o SIGALRM chega à
thread principal, que para de registrar e não inicia envio novo. As cópias já em curso podem terminar
sem registro; a execução seguinte as reconhece no destino pelo hash (`já existia idêntico`), sem
duplicar, como no caso de segunda ordem observado em 2026-09-22. O resumo segue contando só o que o
registro confirmou.

## Efeito esperado

Envio de ~52 min para ~13 min no lote de 2026-09-22; coleta dos ciclos seguintes ao primeiro limitada
às mensagens novas e às que ainda têm pendente.
