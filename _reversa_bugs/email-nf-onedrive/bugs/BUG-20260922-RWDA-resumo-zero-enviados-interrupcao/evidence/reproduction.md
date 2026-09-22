# Cápsula de reprodução: BUG-20260922-RWDA

- Data: 2026-09-22
- Commit base: `93afccf` (branch `main`; só `_reversa_bugs/` fora do índice)
- Ambiente: macOS 27.0 (arm64), Python 3.14.7 (`.venv` do projeto), rclone v1.74.0 no remote `:local`
- Dados: somente sintéticos de `tests/dados/` (`encaminhada.eml`, `encaminhada_em_linha.eml`, `interna_nfe_e_danfe.eml`)
- Comando: `.venv/bin/python evidence/repro.py`, a partir da raiz do projeto
- Exit code: 0 (o script; o ciclo sob teste sai com 2, como manda a interrupção por tempo)
- Taxa: 5/5; classificação `deterministic`

## Saída

```
código de saída          : 2
arquivos no destino      : 2
linhas 'enviado:' no log : 2
estados no registro      : ['enviado', 'enviado', 'extraido', 'extraido']
resumo                   : 1 caixa, 4 extraídos, 0 enviados, 1 falhas, 0 s
```

## Leitura

Dois anexos chegaram ao destino, o registro gravou os dois como `enviado` e o log traz as duas
linhas `enviado:`. Mesmo assim o resumo final anuncia `0 enviados`. É o mesmo desencontro observado
na VPS `medicina-leal` em 2026-09-22 (79 linhas `enviado:` no log, 80 arquivos na pasta, 84 linhas
`enviado` no registro, resumo com `0 enviados`), reproduzido aqui sem dado real.

Os demais campos do resumo sobrevivem porque são somados antes do envio: `4 extraídos` e `1 caixa`
saem do laço da coleta, e `1 falhas` é a falha `execucao:tempo` contada em `_Ciclo.rodar`. O código
de saída 2 e a causa `execucao:tempo` são o comportamento esperado da interrupção, e não mudam.

## Como a interrupção é imposta

`signal.alarm` só aceita segundos inteiros, de modo que reproduzir pelo relógio exigiria um ciclo de
mais de um segundo com envios lentos — instável e lento na suíte. O script injeta um `Rclone` que
levanta `TempoEsgotado` a partir da terceira cópia: a mesma exceção que `limite_duracao` levanta a
partir do SIGALRM (`execucao/trava.py:100`), levantada no mesmo ponto, dentro do laço de
`Enviador.enviar`. O caminho de código exercitado é idêntico; só a origem do disparo muda.
