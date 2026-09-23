# Adendo: destino por vencimento

> Identificador: `003-destino-por-vencimento`
> Data: `2026-09-23`
> Origem: cartão 2 do kanban ("Destino por vencimento"), decisões de iago em 2026-09-23
> Imutável: uma revisão futura vira `003-destino-por-vencimento-v002.md`; a spec original não é editada.

## Vigência

Vigente desde 2026-09-23. Complementa `_reversa_sdd/sdd/envio-onedrive.md` e os adendos
`001-mvp-email-nf-onedrive` e `bug-BUG-20260922-VBJD-v001`; a convenção de nomes não muda.

## Delta 1: `envio-onedrive.md#6. Requisitos Funcionais`, regra nova (RF-15)

> RF-15: O sistema deve gravar cada documento em
> `<DESTINO_ONEDRIVE>/NOTAS E BOLETOS POR VENCIMENTO/DIA <d>/202X-<mm>/`, com `d` (sem zero à esquerda)
> e `mm` (com zero) do vencimento, e o ano literalmente `202X`, como a grade do financeiro
> (`docs/onedrive/estrutura-contas-a-pagar.md`, seção 1). O vencimento é a primeira fonte que responder:
> 1. o primeiro `cobr/dup/dVenc` do XML de NF-e do próprio anexo;
> 2. o fator de vencimento da linha digitável do próprio boleto, reconhecida pelos dígitos verificadores
>    dos três primeiros campos; entre o ciclo antigo (base 1997-10-07) e o recomeçado em 2025-02-22, vale
>    a data mais próxima do recebimento;
> 3. o vencimento da mensagem: o do XML de NF-e de outro anexo e, sem ele, o da linha digitável de um
>    boleto irmão, de modo que nota, DANFE e boleto da mesma mensagem fiquem juntos;
> 4. a primeira data, posterior ao recebimento, até 80 caracteres depois de "vencimento", "venc." ou
>    "vencto" no texto das três primeiras páginas do PDF.
>
> Sem vencimento, o documento fica na raiz de `DESTINO_ONEDRIVE`, como antes. As fontes do próprio anexo
> vêm antes das da mensagem para que o boleto de uma parcela não herde o vencimento da primeira.

**Decisões (2026-09-23):** nota parcelada vai uma só vez, para o primeiro vencimento; as subpastas
especiais `DIA 9/202X-<mm>/Contratos-Serviços/` e `DIA 7/<EMPRESA> - FATURA CARTÃO DE CRÉDITO/` ficam
fora da regra, e o financeiro move à mão o que couber nelas.

## Delta 2: `envio-onedrive.md`, RF de pasta inexistente

> A proibição de criar pastas vale também para a subpasta de vencimento: se `DIA <d>/202X-<mm>/` não
> existir no destino, o anexo falha com `onedrive:destino` e fica pendente, sem que nada seja criado.

## Medição no lote real (2026-09-23)

Sobre os 346 arquivos da janela de 2026-09-22, agrupados pela mensagem de origem, 216 (62%) acham o
vencimento: 88 de 98 boletos, 45 de 73 XML e 83 de 175 notas em PDF. Todas as datas caem entre
setembro e novembro de 2026. Nos 65 PDFs com linha digitável e data no texto, as duas concordam;
antes da exigência de data posterior ao recebimento, a data de emissão ao lado do rótulo produzia
divergências. Os 130 restantes (notas de serviço sem data, XML sem cobrança, mensagem sem boleto)
ficam na raiz.

## Limitação conhecida

Tabela cujo texto extraído põe a data antes do rótulo "VENCIMENTO" não é lida; PDF só com imagem
também não. Ambos ficam na raiz.
