# Cápsula de reprodução: BUG-20260922-VBJD

- Data: 2026-09-22
- Commit base: `91b01ae` (branch `main`, árvore limpa no código; só `_reversa_bugs/` e `_reversa_sdd/traceability/` não rastreados)
- Ambiente: macOS 27.0, Python 3.14.7 (`.venv` do projeto)
- Dados: somente sintéticos de `tests/dados/` (`nfe_proc.xml`, `encaminhada.eml`) e endereços `.example`
- Comando: `.venv/bin/python evidence/repro.py` (script nesta pasta), a partir da raiz do projeto
- Exit code: 0
- Taxa: 5/5 casos com o resultado errado esperado; classificação `deterministic`

## Saída

```
1 encaminhamento interno, PDF sem XML    -> ACME - EMPRESA - BOLETO.pdf
2a mesma mensagem: XML                   -> ACME - FORNECEDOR FICTICIO LTDA - REF.xml
2b mesma mensagem: PDF irmão             -> ACME - EMPRESA - REF.pdf
3 remetente externo                      -> ACME - FORNECEDOR - BOLETO.pdf
encaminhada.eml (rfc822 anexo): remetente usado = colega@empresa.example -> ACME - EMPRESA - BOLETO.pdf
```

## Leitura

- Caso 1: o domínio da própria empresa (`empresa.example`, o mesmo da caixa) vira o fornecedor `EMPRESA`, equivalente sintético de `AFLAPARTI`.
- Casos 2a e 2b: o XML da mensagem leva o emitente, mas o PDF irmão não o aproveita.
- Caso 3: o remetente externo está correto e não pode mudar.
- `encaminhada.eml`: mesmo quando o encaminhamento traz a mensagem original como anexo `message/rfc822`, com `From: cobranca@fornecedor.example` disponível, o nome usa o remetente do encaminhamento.

A produção (VPS `medicina-leal`, 41/80 arquivos) confirma o padrão; os dados reais ficam fora do repositório (público).
