# Estrutura da pasta `<Empresa> Financeiro/CONTAS A PAGAR`

Levantamento feito em 2026-09-21 com `rclone lsf -R` no OneDrive da `<conta-admin>`
(remote `onedrive-financeiro`). As listagens brutas ficam ao lado, **fora do git** (`.gitignore`), por trazerem
fornecedores, números de nota e nomes de pessoas do cliente:

- `contas-a-pagar-pastas.txt`: as 738 pastas, uma por linha, caminho relativo à raiz de CONTAS A PAGAR;
- `contas-a-pagar-arquivos.tsv`: os 2.304 arquivos, com caminho, tamanho em bytes e data de modificação.

Totais no dia do levantamento: 2.304 arquivos, 843 MiB. Nada foi baixado, alterado nem apagado.

Para refazer o levantamento:

```bash
rclone lsf -R --dirs-only  "onedrive-financeiro:<Empresa> Financeiro/CONTAS A PAGAR" > docs/onedrive/contas-a-pagar-pastas.txt
rclone lsf -R --files-only --format pst "onedrive-financeiro:<Empresa> Financeiro/CONTAS A PAGAR" | sed 's/;/\t/g' > docs/onedrive/contas-a-pagar-arquivos.tsv
```

## Visão geral

A raiz tem só duas pastas, com finalidades distintas:

| Pasta | Arquivos | Papel |
|---|---|---|
| `NOTAS E BOLETOS POR VENCIMENTO` | 105 | Fila do que **ainda vai vencer**, organizada por dia e mês de vencimento |
| `RELATÓRIO DE PAGAMENTOS SEMANAIS` | 2.199 | Histórico do que **foi pago**, organizado por mês e semana de pagamento |

O fluxo aparente é: o documento entra em `NOTAS E BOLETOS POR VENCIMENTO/DIA n/202X-mm/`; na semana do
pagamento, é levado (com sufixo ` - OK` no nome) para a semana correspondente do `RELATÓRIO`. A caixa de
saída da ferramenta é, portanto, a primeira pasta; a segunda é trabalho manual do financeiro e não deve ser
tocada pela automação.

## 1. `NOTAS E BOLETOS POR VENCIMENTO`

Esqueleto canônico, três níveis:

```
NOTAS E BOLETOS POR VENCIMENTO/
└── DIA <d>/                 d = 1 … 31, sem zero à esquerda ("DIA 1", "DIA 10")
    └── 202X-<mm>/           mm = 01 … 12, com zero; o ano é literalmente "202X"
        └── <arquivo>.pdf
```

São 31 pastas `DIA` × 12 pastas de mês = 372 pastas-folha, todas presentes, a maioria vazia. O `202X`
mostra que a grade é reutilizada de ano em ano: o mês é o do vencimento; o ano não entra no caminho.

Além do esqueleto, existem:

- `DIA <d>/202X-<mm>/Contratos-Serviços/`: uma subpasta por mês, só em `DIA 9`, para notas de contratos
  de serviço (3 arquivos em `DIA 9/202X-10/Contratos-Serviços/`).
- `DIA 7/<EMPRESA> - FATURA CARTÃO DE CRÉDITO/202X-<mm>/`: a fatura do cartão, que vence todo dia 7, tem grade
  própria de 12 meses dentro do `DIA 7`, no lugar da pasta de mês.

Anomalias que **não** devem ser reproduzidas (parecem cópias acidentais da grade):

- em todos os `DIA`, `202X-04/` contém `202X-01/`, `202X-02/` e `202X-03/` vazias;
- em 23 `DIA`, `202X-10/` contém o mesmo trio; idem em `DIA 7/<EMPRESA> - FATURA CARTÃO DE CRÉDITO/202X-04/`;
- um mesmo boleto está copiado em `202X-10` de 29 dos 31 `DIA`, e uma mesma imagem em três meses do `DIA 5`;
- um PDF está solto em `DIA 22`, fora de qualquer mês;
- um boleto em `DIA 28/202X-09/` está sem extensão.

## 2. `RELATÓRIO DE PAGAMENTOS SEMANAIS`

```
RELATÓRIO DE PAGAMENTOS SEMANAIS/
└── <AAAA-MM>/                          2025-9 (sem zero, único caso), 2025-10 … 2026-09
    └── [n. ]SEMANA DE <dd-mm> A <dd-mm>/  a numeração "1. ", "2. " … só aparece a partir de 2026-09
        ├── <arquivo>.pdf               notas, boletos e comprovantes já pagos
        ├── RELATÓRIOS/                 a partir de 2026, o relatório semanal por caixa/empresa
        ├── CARTÃO DE CRÉDITO/ …        subpastas variáveis: cartão, comprovantes, reembolsos,
        └── COMPROVANTES/ …             prestação de contas, dias específicos ("DIA 28-10-25")
```

- 13 meses, de setembro de 2025 a setembro de 2026, entre 61 e 254 arquivos por mês.
- As semanas começam no sábado e terminam na sexta (ex.: `SEMANA DE 19-09 A 25-09`), com exceção da
  primeira e da última de cada mês, cortadas na virada (`1. SEMANA DE 01-09 A 04-09`, `5. SEMANA DE 26-09 A 30-09`).
- Semana que atravessa o ano leva o ano no fim: `SEMANA DE 27-12 A 02-01-2026`.
- As subpastas dentro da semana não seguem padrão fixo; a mais estável é `RELATÓRIOS/` (12 ocorrências),
  com o `RELATÓRIO CONTAS A PAGAR <dd> A <dd> <MÊS> - <caixa>.pdf` de cada empresa ou conta do grupo.

## 3. Convenção de nomes dos arquivos

Padrão dominante, com ` - ` como separador:

```
<EMPRESA> - <FORNECEDOR> [NF <n>] - <TIPO> [<n>][ - OK].pdf
```

| Campo | Valores observados |
|---|---|
| EMPRESA | a empresa principal do grupo em 1.104 arquivos; outras nove entidades do grupo (minas, fazendas, sócios) entre 5 e 141 arquivos cada; grafia inconsistente em duas delas (com e sem acento). As demais empresas atendidas pela ferramenta **não aparecem** nesta pasta |
| TIPO | `REF <n>` (775; a nota fiscal, com o número de referência do sistema), `BOLETO` (383), `REG <n>` (337; guias, impostos, recibos), `NF <n>` |
| ` - OK` | sufixo acrescentado quando o pagamento foi feito (48 no levantamento, concentrados nas semanas recentes) |

Exemplos (nomes fictícios): `ACME - FORNECEDOR NF 109652 - REF.pdf` (nota) e `ACME - FORNECEDOR - BOLETO.pdf`
(boleto da mesma nota); `FILIAL - OUTRO FORNECEDOR NF 2666 - REF 18291 - OK.pdf`.

Formatos: 2.151 PDF, 59 PNG, 41 JPEG, 21 HEIC, 16 XLSX, 8 ZIP, 4 DOCX, 3 arquivos sem extensão.

## 4. Consequências para a ferramenta

1. O destino canônico de um documento novo é
   `NOTAS E BOLETOS POR VENCIMENTO/DIA <d>/202X-<mm>/`, com `d` e `mm` do **vencimento**, não do
   recebimento. Isso confirma a exigência registrada em 2026-09-21 (pastas por mês e dia de vencimento).
2. Toda pasta-folha já existe; a ferramenta pode continuar sem criar pastas, desde que a grade esteja
   completa no destino (é o caso da oficial e, após a reprodução, da de teste).
3. O nome provisório da ferramenta (`AAAA-MM-DD_remetente_nome-original`) não seguia a convenção da pasta;
   em 2026-09-21 (T042) ela passou a `<EMPRESA> - <FORNECEDOR> [NF <n>] - <REF|BOLETO>.<ext>`, com a EMPRESA
   em `EMPRESA_EMAIL<n>` e o FORNECEDOR do XML ou do remetente (`src/email_nf_onedrive/envio/nomeacao.py`).
4. `RELATÓRIO DE PAGAMENTOS SEMANAIS` é operado à mão e fica fora do alcance da automação.

## 5. Pasta de teste

`<Empresa> Financeiro/CONTAS A PAGAR - TESTE` recebeu, em 2026-09-21, o esqueleto canônico da seção 1
(31 × 12 pastas de mês, mais `DIA 9/202X-<mm>/Contratos-Serviços/` e
`DIA 7/<EMPRESA> - FATURA CARTÃO DE CRÉDITO/202X-<mm>/`), sem arquivos e sem as anomalias. O `RELATÓRIO` não foi
reproduzido, por estar fora do escopo da ferramenta.
