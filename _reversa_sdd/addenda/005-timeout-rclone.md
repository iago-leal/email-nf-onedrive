# Adendo: limite de 300 s por chamada ao Rclone

> Identificador: `005-timeout-rclone`
> Data: `2026-09-23`
> Origem: janela de observação de 2026-09-23 com o envio em paralelo (adendo `004-desempenho-coleta-envio`); decisão de iago
> Imutável: uma revisão futura vira `005-timeout-rclone-v002.md`; a spec original não é editada.

## Delta: `envio-onedrive.md#RNF-03`

**Trecho anterior:** Timeout de 120 s por chamada ao Rclone; chamada travada vira `falha-envio`.

**Como deve ser lido agora:** Timeout de **300 s** por chamada ao Rclone; chamada travada vira `falha-envio`.

## Por quê

No ciclo 3 da janela, o primeiro com 4 envios simultâneos, o OneDrive fez o envio pausar duas vezes,
por cerca de 2 min cada, e as chamadas em curso estouraram os 120 s: 12 `falha-envio`, contra nenhuma
nos ciclos em série. O Rclone cumpre a espera pedida pelo OneDrive dentro da própria chamada, de modo
que o limite a cortava no meio. Nada se perdeu: o ciclo seguinte reenviou os 12 e reconheceu pelo
hash as 8 cópias que haviam chegado ao destino apesar do corte (conciliação de 354 arquivos, exata).

Reduzir o paralelismo foi descartado: mesmo com as pausas, 4 threads renderam ~20 envios/min, contra
~17 esperados com 2 sem pausa e ~7 em série. O limite de 20 min por execução (RF-14) não muda.
