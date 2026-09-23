# Adendo: sumário LEIAME dos documentos sem vencimento

> Identificador: `006-sumario-leiame-da-raiz`
> Data: `2026-09-23`
> Origem: diagnóstico dos 130 documentos que a janela de 2026-09-23 deixou na raiz; pedido e decisões de iago
> Imutável: uma revisão futura vira `006-sumario-leiame-da-raiz-v002.md`; a spec original não é editada.

## Delta: `envio-onedrive.md`, novo RF-16

**RF-16 (Must):** a raiz de cada destino tem a planilha `00 - LEIAME - DOCUMENTOS SEM VENCIMENTO.xlsx`,
que o prefixo `00` põe no topo da listagem. Ela explica ao financeiro o que são os documentos da raiz
e por que não foram classificados na grade por vencimento.

- **Conteúdo.** Aba "Documentos", com uma linha por arquivo solto na raiz, ordenada por motivo: arquivo,
  empresa, fornecedor (os dois tirados do padrão do nome), motivo, recebido em (horário de Brasília),
  remetente e assunto. Aba "Resumo por motivo", com a contagem de cada motivo. O cabeçalho diz como
  classificar um documento e que a planilha é refeita automaticamente.
- **Fonte.** Vem da listagem real da raiz cruzada com o registro. Arquivo que a ferramenta não enviou
  aparece como "não enviado por esta ferramenta"; arquivo enviado antes desta feature, sem motivo
  gravado, aparece como "motivo não apurado".
- **Motivo.** O envio o apura na mesma leitura que decide o vencimento, em linguagem de financeiro:
  - nota paga à vista;
  - nota sem fatura, em XML;
  - nota fiscal de serviço;
  - DANFE sem vencimento identificável;
  - documento sem texto legível (digitalizado ou com fonte embutida);
  - imagem ou formato sem texto;
  - documento que já chegou vencido, com a data;
  - vencimento não localizado.

  O motivo fica na tabela nova `sem_vencimento` do registro. Por ser tabela à parte, e não coluna de
  `anexos`, o registro existente não precisa de migração.
- **Quando.** A planilha é refeita ao fim de cada execução em que o conjunto de nomes da raiz mudou desde
  a última versão, inclusive quando alguém move ou apaga um arquivo à mão, ou quando ela sumiu. A
  assinatura do conjunto fica em `meta`. Na simulação, nada é escrito, e no erro de token ou de remote
  a planilha não é tocada. Falha ao publicá-la vira o aviso `onedrive:leiame`, e a execução seguinte
  tenta de novo.

## Delta: `envio-onedrive.md#RF-03` (nunca sobrescrever)

**Trecho anterior:** o sistema envia cada arquivo sem nunca sobrescrever arquivo existente.

**Como deve ser lido agora:** a regra continua valendo para todo documento. A única exceção é a planilha
LEIAME da raiz, que a ferramenta gera e substitui: `Rclone.publicar_leiame` é o único envio sem
`--ignore-existing` e recusa qualquer nome diferente do exato, assim como `deletefile` só aceita o
arquivo de teste. O subcomando continua sendo `copyto`, da lista branca.

## Por quê

Na janela de 2026-09-23, 130 dos 354 documentos ficaram na raiz sem explicação visível ao financeiro.
Medidos com a revisão `003-destino-por-vencimento-v002`, 125 continuam sem vencimento, e 123 deles
recebem motivo específico:

| Motivo | Documentos |
|--------|-----------:|
| nota fiscal de serviço | 50 |
| DANFE sem vencimento identificável | 32 |
| nota sem fatura (XML) | 18 |
| documento sem texto legível | 12 |
| nota paga à vista | 10 |
| já chegou vencido | 1 |
| vencimento não localizado (proposta comercial, relatório de comissões) | 2 |

O formato .xlsx, um único arquivo reescrito e o nome com LEIAME foram escolhas de iago. A planilha se
filtra por motivo ou fornecedor no próprio OneDrive, sem instalar nada.
