# Spec: coleta-email

> Selo 🟡 PLANEJADO em todos os itens. Fonte: [`prd.md`](../prd.md).

**Versão:** 1.0
**Status:** Rascunho
**Autor:** reversa-spec-sdd
**Data:** 2026-09-18
**Reviewers:** iago

---

## 1. Resumo

🟡 Componente que conecta a cada caixa configurada no Google Workspace via IMAP, somente leitura, encontra as mensagens novas da pasta monitorada, extrai os anexos PDF e XML, classifica cada um (NF-e em XML, NF ou boleto por palavra-chave, sem classificação) e os entrega ao `envio-onedrive`, registrando o que já foi processado para nunca duplicar.

---

## 2. Contexto e Motivação

**Problema:**
🟡 NFs e boletos chegam por e-mail à caixa do financeiro, quatro pessoas a leem e ninguém assume salvar os anexos. O componente substitui esse passo manual.

**Evidências:**
🟡 Áudio de origem, resumido em `newproject-brief.md`: a solicitante relata que, quando todos veem o e-mail e ninguém salva a nota na pasta, a conta é esquecida.

**Por que agora:**
🟡 É o primeiro elo da cadeia: sem coleta, não há o que enviar ao OneDrive.

---

## 3. Goals (Objetivos)

- [ ] 🟡 G-01: Todo anexo PDF ou XML recebido na pasta monitorada, a partir de `DATA_INICIAL`, é extraído e entregue ao envio.
- [ ] 🟡 G-02: Nenhum anexo é entregue duas vezes em execuções sucessivas.
- [ ] 🟡 G-03: A caixa de e-mail permanece exatamente como estava: nenhuma mensagem é movida, apagada, marcada como lida ou rotulada.

**Métricas de sucesso:**
| Métrica | Baseline atual | Target | Prazo |
|---------|---------------|--------|-------|
| 🟡 Anexos PDF/XML extraídos sobre anexos PDF/XML recebidos (amostragem semanal) | 🟡 processo manual, não medido | = 100% | 🟡 3 meses após entrada em operação |
| 🟡 Anexos duplicados entregues ao envio | não se aplica | = 0 por mês | 🟡 3 meses após entrada em operação |
| 🟡 Mensagens com estado alterado na caixa | não se aplica | = 0 | 🟡 contínuo |

---

## 4. Non-Goals (Fora do Escopo)

- 🟡 NG-01: Alterar mensagens na caixa (mover, apagar, marcar como lida, aplicar marcador): decisão do usuário, "só ler".
- 🟡 NG-02: Baixar documentos a partir de links para portais de fornecedores ou prefeituras; mensagens nessa situação só são registradas no log.
- 🟡 NG-03: Extrair dados das notas (valor, vencimento, CNPJ) para planilha ou relatório.
- 🟡 NG-04: Descompactar anexos `.zip` ou `.rar`: registrados no log como "anexo compactado ignorado" (ver OQ-02).
- 🟡 NG-05: Ler imagens (JPG, PNG) ou fazer OCR.
- 🟡 NG-06: Autenticação OAuth 2.0 (ver NG-03 de [`configuracao-caixas.md`](./configuracao-caixas.md)).

---

## 5. Usuários e Personas

**Usuário primário:** 🟡 analista-financeira, beneficiária indireta: encontra os documentos no OneDrive sem baixar anexos.
**Usuário secundário:** 🟡 operador-tecnico, que acompanha o log e trata mensagens sem anexo reconhecido.

**Jornada atual (sem a feature):**
1. 🟡 A analista abre a caixa do financeiro e vê o e-mail do fornecedor.
2. 🟡 Presume que outra pessoa já salvou o anexo, ou baixa e salva manualmente.
3. 🟡 Parte dos documentos nunca chega à pasta, e a conta é esquecida.

**Jornada futura (com a feature):**
1. 🟡 O fornecedor envia o e-mail com NF ou boleto.
2. 🟡 Em até 30 min, o sistema extrai o anexo e o entrega ao envio.
3. 🟡 A analista encontra o documento no OneDrive, e o e-mail continua intacto na caixa.

---

## 6. Requisitos Funcionais

### 6.1 Requisitos Principais

| ID | Requisito | Prioridade | Critério de Aceite |
|----|-----------|-----------|-------------------|
| RF-01 | 🟡 O sistema deve conectar a cada caixa válida por IMAP sobre TLS (porta 993), autenticando com endereço e senha de app. | Must | 🟡 Com credenciais válidas, a conexão é aberta e registrada no log como "caixa 1: conectada". |
| RF-02 | 🟡 O sistema deve abrir a pasta monitorada em modo somente leitura (comando IMAP `EXAMINE`) e buscar o corpo das mensagens sem alterar a flag `\Seen` (`BODY.PEEK`). | Must | 🟡 Após uma execução, as mensagens não lidas continuam não lidas no Gmail. |
| RF-03 | 🟡 O sistema deve selecionar as mensagens recebidas a partir da data de corte: `DATA_INICIAL` para caixa sem histórico; para caixa com histórico, a menor entre (a) a data da mensagem mais recente já registrada menos 2 dias e (b) a data da mensagem mais antiga com anexo em estado `extraido` ou `falha-envio`. | Must | 🟡 Numa caixa com última mensagem registrada em 10/09 e nenhum anexo pendente, a busca usa `SINCE 08-Sep-2026`; havendo anexo `falha-envio` de 01/09, usa `SINCE 01-Sep-2026`. |
| RF-04 | 🟡 O sistema deve extrair de cada mensagem os anexos com extensão `.pdf` ou `.xml`, sem diferenciar maiúsculas, ou com tipo MIME `application/pdf`, `application/xml` ou `text/xml`, inclusive dentro de mensagens encaminhadas (`message/rfc822`). | Must | 🟡 Um e-mail com `NF123.PDF` e `assinatura.png` gera 1 anexo extraído. |
| RF-05 | 🟡 O sistema deve classificar cada anexo em uma de três classes: `nfe-xml`, quando o XML tem raiz `nfeProc` ou `NFe` no namespace `http://www.portalfiscal.inf.br/nfe`; `palavra-chave`, quando o assunto ou o nome do arquivo contém um dos termos da lista do RF-06; `sem-classificacao`, nos demais casos. | Must | 🟡 Um XML de NF-e autorizada recebe `nfe-xml` mesmo com nome `arquivo.xml`; um PDF `boleto_set.pdf` recebe `palavra-chave`. |
| RF-06 | 🟡 O sistema deve usar como lista padrão de palavras-chave, sem diferenciar maiúsculas nem acentos: `nf`, `nfe`, `nf-e`, `nfs-e`, `nota fiscal`, `danfe`, `boleto`, `fatura`, `cobranca`, `duplicata`. | Must | 🟡 Assunto "Cobrança referente a setembro" classifica o PDF anexo como `palavra-chave`. |
| RF-07 | 🟡 O sistema deve entregar ao envio todos os anexos extraídos, qualquer que seja a classe, junto com os metadados do modelo de dados (seção 9). | Must | 🟡 Um PDF `sem-classificacao` também é entregue ao `envio-onedrive`, com a classe registrada. |
| RF-08 | 🟡 O sistema deve identificar cada anexo pela chave (caixa, `Message-ID`, SHA-256 do conteúdo) e ignorar os que já constam no registro de processados com estado `enviado`. | Must | 🟡 Duas execuções seguidas sobre a mesma caixa, sem e-mails novos, entregam 0 anexos na segunda. |
| RF-09 | 🟡 O sistema deve registrar no log as mensagens da janela de busca sem anexo PDF/XML cujo assunto contenha palavra-chave do RF-06, como "possível documento sem anexo". | Should | 🟡 Um e-mail "Sua NFS-e está disponível" com link e sem anexo aparece no log com remetente, assunto e data. |
| RF-10 | 🟡 O sistema deve processar as caixas em sequência, na ordem dos índices, e a falha de uma caixa não deve interromper as seguintes. | Must | 🟡 Com a caixa 1 recusando o login, a caixa 2 é processada na mesma execução. |
| RF-11 | 🟡 O sistema deve gravar cada anexo extraído numa pasta de trabalho local da execução, de onde o `envio-onedrive` o lê. | Must | 🟡 Após a extração, o arquivo existe na pasta de trabalho com o conteúdo idêntico ao anexo (mesmo SHA-256). |

### 6.2 Fluxo Principal (Happy Path)

1. 🟡 O sistema recebe a lista de caixas válidas de [`configuracao-caixas.md`](./configuracao-caixas.md).
2. 🟡 Para cada caixa, o sistema conecta via IMAP e abre a pasta monitorada em modo somente leitura.
3. 🟡 O sistema calcula a data de corte (RF-03) e busca as mensagens a partir dela.
4. 🟡 Para cada mensagem, o sistema extrai os anexos PDF/XML, calcula o SHA-256 e descarta os já enviados.
5. 🟡 O sistema classifica cada anexo novo, grava-o na pasta de trabalho e o registra com estado `extraido`.
6. 🟡 O sistema encerra a conexão IMAP da caixa.
7. 🟡 Resultado: lista de anexos novos entregue ao [`envio-onedrive.md`](./envio-onedrive.md), com a caixa intacta.

### 6.3 Fluxos Alternativos

**Fluxo Alternativo A — Anexo extraído e não enviado numa execução anterior:**
1. 🟡 O anexo consta no registro com estado `extraido` ou `falha-envio`.
2. 🟡 O sistema o extrai de novo e o entrega ao envio, sem criar registro duplicado.

**Fluxo Alternativo B — Mensagem sem `Message-ID`:**
1. 🟡 O cabeçalho `Message-ID` está ausente.
2. 🟡 O sistema usa como identificador o SHA-256 de remetente + data + assunto.

---

## 7. Requisitos Não-Funcionais

| ID | Requisito | Valor alvo | Observação |
|----|-----------|-----------|------------|
| RNF-01 | 🟡 Performance | 🟡 < 5 min por caixa para até 200 mensagens na janela | 🟡 Cabe folgado no intervalo de 30 min do agendamento. |
| RNF-02 | 🟡 Não interferência | 🟡 0 alterações de estado na caixa | 🟡 Garantido por `EXAMINE` + `BODY.PEEK`. |
| RNF-03 | 🟡 Segurança | 🟡 TLS obrigatório; nenhuma conexão IMAP em texto claro | 🟡 Porta 993. |
| RNF-04 | 🟡 Resiliência | 🟡 Timeout de 60 s por operação IMAP | 🟡 Evita execução travada. |

---

## 8. Design e Interface

**Componentes afetados:** 🟡 conexão IMAP; pasta de trabalho local; registro de processados (compartilhado com o `envio-onedrive`).

**Comportamento esperado:**
🟡 Não há interface gráfica. O resultado aparece no log e, indiretamente, na pasta do OneDrive.

**Estados da UI:**
- 🟡 Estado vazio: "caixa 1: nenhum anexo novo" no log.
- 🟡 Estado de carregamento: não se aplica (execução em segundo plano).
- 🟡 Estado de erro: linha de log com caixa, etapa e causa, mais aviso de falha (ver [`execucao-monitoramento.md`](./execucao-monitoramento.md)).
- 🟡 Estado de sucesso: "caixa 1: N anexos novos (x nfe-xml, y palavra-chave, z sem-classificacao)".

---

## 9. Modelo de Dados

**Entidades novas ou modificadas:**

```
AnexoProcessado {                 // registro persistente, compartilhado com envio-onedrive
  caixa_indice: int
  caixa_endereco: str
  message_id: str                 // Message-ID ou hash substituto (fluxo alternativo B)
  sha256: str                     // hash do conteúdo do anexo
  nome_original: str
  remetente: str                  // endereço do From
  assunto: str
  data_mensagem: datetime         // cabeçalho Date, em UTC
  classe: "nfe-xml" | "palavra-chave" | "sem-classificacao"
  estado: "extraido" | "enviado" | "falha-envio"
  caminho_destino: str | nulo     // preenchido pelo envio-onedrive
  atualizado_em: datetime
}
chave única: (caixa_indice, message_id, sha256)
```

**Migrações necessárias:** 🟡 Não; o registro é criado na primeira execução (armazenamento local, por exemplo SQLite, definido no plano).

---

## 10. Integrações e Dependências

| Dependência | Tipo | Impacto se indisponível |
|-------------|------|------------------------|
| 🟡 Servidor IMAP do Google Workspace (`imap.gmail.com:993`) | Obrigatória | 🟡 A caixa é pulada nesta execução; aviso de falha; nova tentativa em 30 min. |
| 🟡 IMAP habilitado pelo administrador do Workspace | Obrigatória | 🟡 Login recusado; aviso de falha com a causa. |
| 🟡 [`configuracao-caixas.md`](./configuracao-caixas.md) | Obrigatória | 🟡 Sem caixas válidas, nada é coletado. |
| 🟡 Registro de processados em disco local | Obrigatória | 🟡 Sem ele, a execução aborta para não duplicar envios. |

---

## 11. Edge Cases e Tratamento de Erros

| Cenário | Trigger | Comportamento esperado |
|---------|---------|----------------------|
| 🟡 EC-01: Login recusado | 🟡 Senha comum em vez de senha de app, ou senha trocada | 🟡 Caixa pulada; log "caixa 1: autenticação recusada (verifique a senha de app)"; aviso de falha. |
| 🟡 EC-02: Pasta inexistente | 🟡 `PASTA_EMAIL1` com nome errado | 🟡 Caixa pulada; log lista as pastas existentes na caixa; aviso de falha. |
| 🟡 EC-03: Servidor fora do ar ou timeout | 🟡 Sem resposta em 60 s | 🟡 Caixa pulada nesta execução; aviso de falha; retomada automática na próxima execução pela janela do RF-03. |
| 🟡 EC-04: Mesmo anexo em dois e-mails | 🟡 Fornecedor reenvia o mesmo PDF | 🟡 Tratados como anexos distintos (Message-ID diferente); o `envio-onedrive` detecta conteúdo idêntico no destino (ver EC-03 dele). |
| 🟡 EC-05: Nome de anexo com codificação MIME | 🟡 Nome em `=?UTF-8?B?...?=` | 🟡 Nome decodificado para UTF-8 antes do registro. |
| 🟡 EC-06: Anexo sem nome | 🟡 Parte PDF sem `filename` | 🟡 Nome gerado `anexo-<n>.pdf`, com `<n>` a posição na mensagem. |
| 🟡 EC-07: XML malformado | 🟡 XML que não faz parse | 🟡 Classe `palavra-chave` ou `sem-classificacao` pelas regras de texto; o anexo segue para o envio. |
| 🟡 EC-08: Anexo compactado | 🟡 `.zip` ou `.rar` | 🟡 Não extraído; log "anexo compactado ignorado" com remetente e assunto. |
| 🟡 EC-09: Registro de processados corrompido | 🟡 Arquivo ilegível | 🟡 Execução abortada antes de qualquer envio; aviso de falha pedindo intervenção. |
| 🟡 EC-10: Grande volume na primeira execução | 🟡 `DATA_INICIAL` antiga, mais de 500 mensagens | 🟡 Processa todas, registrando progresso a cada 50 mensagens no log. |

---

## 12. Segurança e Privacidade

- **Autenticação:** 🟡 senha de app por caixa, lida do `.env`; nunca registrada.
- **Autorização:** 🟡 só leitura na caixa (`EXAMINE`); o sistema não envia, move nem apaga mensagens.
- **Dados sensíveis:** 🟡 NFs e boletos contêm CNPJ, e às vezes CPF de fornecedor pessoa física (LGPD). A pasta de trabalho é apagada ao fim de cada execução bem-sucedida; o registro guarda só metadados, nunca o conteúdo dos anexos.
- **Auditoria:** 🟡 o log registra caixa, remetente, assunto, nome do anexo, classe e SHA-256 de cada anexo extraído.

---

## 13. Plano de Rollout

- **Estratégia:** 🟡 primeiro em modo `--simular` (ver [`execucao-monitoramento.md`](./execucao-monitoramento.md)), que coleta e classifica sem enviar; depois em produção.
- **Como reverter (rollback):** 🟡 desativar o agendamento; como a caixa não é alterada, não há o que desfazer nela.
- **Monitoramento pós-deploy:** 🟡 na primeira semana, comparar diariamente o log com a caixa e contar anexos não extraídos.

---

## 14. Open Questions

| # | Pergunta | Impacto | Dono | Prazo |
|---|---------|---------|------|-------|
| OQ-01 | 🟡 ⚠️ ABERTO: qual pasta ou marcador do Gmail a equipe usa? Até a resposta, `INBOX`. | Alto | iago | 🟡 antes do primeiro teste real |
| OQ-02 | 🟡 ⚠️ ABERTO: fornecedores enviam NFs em `.zip`? Se sim, a descompactação entra no escopo. | Médio | iago | 🟡 após 1 semana de `--simular` |
| OQ-03 | 🟡 ⚠️ ABERTO: anexos `sem-classificacao` (ex.: propostas, contratos em PDF) devem ir para a mesma pasta ou para uma subpasta separada? Até a resposta, mesma pasta, conforme a escolha "todo PDF e XML anexo". | Médio | iago | 🟡 após 1 semana de `--simular` |

---

## 15. Decisões Tomadas (Decision Log)

| Decisão | Alternativas consideradas | Racional |
|---------|--------------------------|---------|
| 🟡 Enviar todo PDF/XML e usar a classificação só como metadado | 🟡 Enviar só anexos com palavra-chave | 🟡 O usuário marcou as três regras; enviar tudo garante a métrica de cobertura de 100%, e a classe permite filtrar depois. |
| 🟡 Somente leitura na caixa | 🟡 Marcador "Processado" ou marcar como lida | 🟡 Decisão do usuário; a equipe continua vendo a caixa como hoje. |
| 🟡 Janela de busca com 2 dias de sobreposição | 🟡 Busca por UID desde a última execução | 🟡 Resiste a e-mails com data atrasada e a mudança de UIDVALIDITY; a deduplicação elimina o excesso. |
| 🟡 Deduplicação por (caixa, Message-ID, SHA-256) | 🟡 Só por nome de arquivo | 🟡 Nomes se repetem entre fornecedores (`boleto.pdf`); o hash identifica o conteúdo. |

---

## Apêndice

### Referências
- 🟡 [`prd.md`](../prd.md), seções 4, 5, 8 e 9.
- 🟡 [`configuracao-caixas.md`](./configuracao-caixas.md), [`envio-onedrive.md`](./envio-onedrive.md), [`execucao-monitoramento.md`](./execucao-monitoramento.md).

### Histórico de Revisões
| Versão | Data | Autor | Mudanças |
|--------|------|-------|---------|
| 1.0 | 2026-09-18 | reversa-spec-sdd | Criação inicial |

---

## Relatório de avaliação

- **Score:** 100.0/100 (spec_scorer.py, rubrica `evaluation_rubric.md`)
- **Iterações:** 2. Iteração 1 corrigiu falso positivo do scorer (termo vago em nome de arquivo de exemplo). Na revisão de consistência, o RF-03 passou a incluir na janela de busca os anexos pendentes, para que um `falha-envio` antigo não saia da janela e deixe de ser retentado.
- **Gaps críticos:** nenhum apontado pelo scorer.
- **Ressalva:** o score mede estrutura e testabilidade, não a correção das premissas. As questões ⚠️ ABERTO da seção 14 continuam bloqueando a entrada em operação.

Gerado por reversa-spec-sdd em 2026-09-18T19:12:18Z
