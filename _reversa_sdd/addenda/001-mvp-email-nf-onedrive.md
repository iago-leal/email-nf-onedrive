# Adendo: MVP de arquivamento automático de NFs e boletos

> Identificador: `001-mvp-email-nf-onedrive`
> Data: `2026-09-18`
> Cenário: `greenfield` (âncora: `prd.md` e as quatro specs em `sdd/`)
> Sincronização **parcial**: 44 de 45 ações concluídas. Falta a T042, verificação manual contra o OneDrive e o Gmail reais, que também fecha a convenção de nomes (L-03). Uma reexecução do `/reversa-sync` depois dela acrescentará uma seção de atualização.

## Vigência

Vigente desde 2026-09-18.

## Resumo da entrega

A feature entrega o produto mínimo do PRD: a ferramenta de linha de comando `email-nf-onedrive`, que a cada 30 minutos lê as caixas financeiras configuradas no `.env` por IMAP em modo somente leitura, extrai os anexos PDF e XML, arquiva no OneDrive for Business, via Rclone e com nome padronizado, os reconhecidos como NF-e ou boleto, e retém os demais para revisão manual. Falhas geram aviso no Telegram, com supressão de 6 h e aviso de recuperação; cada execução deixa log diário e resumo. Acompanham o código o guia de instalação e operação (`docs/instalacao-e-operacao.md`), o `README.md`, o `.env.example` e o mapa de rastreabilidade (`tests/RASTREABILIDADE.md`), com 217 testes automatizados passando.

Ações concluídas: 44 de 45 (T001 a T041 e T043 a T045).

## Impacto por artefato da extração

| Artefato | Seção | Tipo de impacto | Delta |
|----------|-------|-----------------|-------|
| `_reversa_sdd/prd.md` | `#4. Escopo (in)` | componente-novo | Todo o escopo do MVP está implementado no pacote `src/email_nf_onedrive/`; só a validação contra a infraestrutura real (T042) segue pendente. |
| `_reversa_sdd/prd.md` | `#9. Critérios de aceite (alto nível)` | componente-novo | Os critérios estão cobertos por testes de ponta a ponta, exceto a instalação por terceiro, que depende da T042; ver `tests/RASTREABILIDADE.md`. |
| `_reversa_sdd/sdd/configuracao-caixas.md` | `#6. Requisitos Funcionais` | componente-novo | RF-01 a RF-11 implementados em `configuracao/`; o `verificar-config` imprime, além das caixas com senha `****`, as caixas inválidas, o remote, a data inicial, o estado dos avisos e os alertas. |
| `_reversa_sdd/sdd/configuracao-caixas.md` | `#11. Edge Cases e Tratamento de Erros` | componente-novo | Erro global de configuração também é avisado: o ciclo lê à parte o par `TELEGRAM_*` do `.env` e o aviso passa pela supressão de 6 h. |
| `_reversa_sdd/sdd/coleta-email.md` | `#3. Goals (Objetivos)` | componente-novo | Ler a G-01 como "todo PDF ou XML é extraído e classificado"; só os classificados como `nfe-xml` ou `palavra-chave` seguem ao envio (RN-03). |
| `_reversa_sdd/sdd/coleta-email.md` | `#6. Requisitos Funcionais` | componente-novo | RF-01 a RF-11 implementados em `coleta/`; o RF-07 diverge da spec: anexos `sem-classificacao` **não** são enviados, ficam no estado terminal `retido` com a linha única "retido para revisão" (RN-03, D-08). |
| `_reversa_sdd/sdd/coleta-email.md` | `#9. Modelo de Dados` | componente-novo | A chave do registro é (endereço da caixa em minúsculas, identificador da mensagem, SHA-256), e não o índice da caixa; os estados incluem `retido`, e as ocorrências "sem anexo" e "compactado" ficam em tabela própria (D-09). |
| `_reversa_sdd/sdd/coleta-email.md` | `#11. Edge Cases e Tratamento de Erros` | componente-novo | Para o EC-07, o XML só é NF-e se estiver bem formado até o fim, com limite de 10 MB; a leitura só da raiz, prevista na D-07 do roadmap, foi abandonada. |
| `_reversa_sdd/sdd/coleta-email.md` | `#15. Decisões Tomadas (Decision Log)` | componente-novo | Acrescentar à leitura a decisão de 2026-09-18 (sessão de esclarecimentos, resposta 1c): documentos não reconhecidos ficam retidos para revisão, em vez de enviados. |
| `_reversa_sdd/sdd/envio-onedrive.md` | `#3. Goals (Objetivos)` | componente-novo | A G-03 é cumprida com critério mais estrito: o anexo só vira `enviado` depois de conferidos tamanho **e** QuickXorHash no destino. |
| `_reversa_sdd/sdd/envio-onedrive.md` | `#6. Requisitos Funcionais` | componente-novo | RF-01 a RF-10 implementados em `envio/`; a cópia usa `rclone copyto --ignore-existing`, porque `--immutable` se mostrou incapaz de impedir a sobrescrita, e a pasta de destino nunca é criada. |
| `_reversa_sdd/sdd/envio-onedrive.md` | `#10. Integrações e Dependências` | componente-novo | O Rclone só é chamado com `lsjson`, `hashsum`, `copyto`, `lsf` e `deletefile` do arquivo de teste; erro de token ou de remote suspende os demais envios da execução. |
| `_reversa_sdd/sdd/envio-onedrive.md` | `#14. Open Questions` | componente-novo | A OQ-01 (convenção de nomes, L-03) segue aberta; vale a convenção provisória `AAAA-MM-DD_remetente_nome-original`, isolada em `envio/nomeacao.py`. |
| `_reversa_sdd/sdd/execucao-monitoramento.md` | `#6. Requisitos Funcionais` | componente-novo | RF-01 a RF-13 implementados em `execucao/` e `cli.py`; o código 1 inclui caixa inválida no `.env`, e o código 2 inclui todas as caixas com falha, registro ilegível, tempo esgotado, disco cheio e exceção não prevista. |
| `_reversa_sdd/sdd/execucao-monitoramento.md` | `#9. Modelo de Dados` | componente-novo | Estado dos avisos (causa, primeira ocorrência, último aviso, ativa, entrega pendente) e o horário da última execução ficam no mesmo SQLite do registro de processados. |
| `_reversa_sdd/sdd/execucao-monitoramento.md` | `#11. Edge Cases e Tratamento de Erros` | componente-novo | EC-01 a EC-07 implementados; sem registro legível, o aviso sai direto, sem supressão. |

## Regras sob vigilância

W001 a W021, na seção "Observações" de [`_reversa_forward/001-mvp-email-nf-onedrive/regression-watch.md`](../../_reversa_forward/001-mvp-email-nf-onedrive/regression-watch.md). Por ser feature greenfield, nenhum item tem ainda peso de regressão; ganham esse peso quando uma futura extração `/reversa` os confirmar como 🟢.

## Fontes

- `_reversa_forward/001-mvp-email-nf-onedrive/legacy-impact.md`
- `_reversa_forward/001-mvp-email-nf-onedrive/regression-watch.md`
- `_reversa_forward/001-mvp-email-nf-onedrive/requirements.md`
- `_reversa_forward/001-mvp-email-nf-onedrive/progress.jsonl`
- `_reversa_forward/001-mvp-email-nf-onedrive/roadmap.md`
