# Adendo: destino por vencimento, revisão 2 da leitura

> Identificador: `003-destino-por-vencimento-v002`
> Data: `2026-09-23`
> Origem: diagnóstico dos 130 documentos que a janela de 2026-09-23 deixou na raiz; decisão de iago
> Revisa: `003-destino-por-vencimento` (fontes 2 e 4 da ordem do vencimento). O adendo 003 não é editado.

## Delta: fonte 2, linha digitável

**Trecho anterior:** a linha digitável terminava no último dígito do valor, sem dígito colado depois dela.

**Como deve ser lido agora:** a linha digitável vale ainda que o extrator de texto cole dígitos ao fim
do valor. Os três dígitos verificadores dos campos continuam sendo a proteção contra falso positivo.

## Delta: fonte 4, data no texto

**Trecho anterior:** a primeira data, posterior ao recebimento, até 80 caracteres depois de
"vencimento", "venc." ou "vencto".

**Como deve ser lido agora:**

- o rótulo aceita também "duplicata" e "duplicatas", comum no quadro de fatura do DANFE;
- a data **colada ao rótulo**, separada dele só por espaço, quebra de linha, dois-pontos ou ponto,
  vale a partir do próprio dia do recebimento ("VENCIMENTO: 19/09/2026" recebido em 19/09);
- a data solta no trecho, como a de uma tabela com emissão e vencimento lado a lado, continua exigindo
  ser posterior ao recebimento.

## Por quê

Dos 130 documentos na raiz, 5 tinham vencimento legível que a regra anterior não lia: 3 boletos com
dígitos colados à linha digitável, 1 DANFE com o quadro "DUPLICATAS" e 1 boleto que venceu no dia em
que chegou. Com a revisão, os 5 passam à grade; os documentos já na grade não foram remedidos, pois a
revisão só amplia o que é lido e a fonte 2 segue protegida pelos dígitos verificadores. Os 125 restantes
não têm vencimento no texto (notas de serviço, notas pagas à vista, documentos digitalizados, boletos
já vencidos); a leitura por OCR fica registrada como feature futura.
