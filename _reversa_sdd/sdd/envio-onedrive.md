# Spec: envio-onedrive

> Selo 🟡 PLANEJADO em todos os itens. Fonte: [`prd.md`](../prd.md).

**Versão:** 1.0
**Status:** Rascunho
**Autor:** reversa-spec-sdd
**Data:** 2026-09-18
**Reviewers:** iago

---

## 1. Resumo

🟡 Componente que recebe os anexos extraídos pelo `coleta-email`, dá a cada um o nome no padrão da pasta, envia-o via Rclone à pasta `<Empresa> Financeiro/CONTAS A PAGAR` do OneDrive for Business, confirma que o arquivo chegou íntegro e atualiza o registro de processados.

---

## 2. Contexto e Motivação

**Problema:**
🟡 A pasta `CONTAS A PAGAR` é a fonte de trabalho da equipe financeira, e hoje depende de alguém salvar os documentos manualmente. O destino é o OneDrive for Business do tenant `<tenant>`, no OneDrive pessoal de `<conta-admin>@<dominio>`.

**Evidências:**
🟡 Correção do usuário em 2026-09-18: o destino não é Google Drive, e sim OneDrive (`newproject-brief.md`, Correções).

**Por que agora:**
🟡 É o elo que entrega o valor ao usuário: o documento só existe para a analista quando está na pasta.

---

## 3. Goals (Objetivos)

- [ ] 🟡 G-01: Todo anexo entregue pelo `coleta-email` chega à pasta de destino com o nome padronizado.
- [ ] 🟡 G-02: Nenhum arquivo existente na pasta é sobrescrito ou apagado.
- [ ] 🟡 G-03: Um anexo só é marcado como `enviado` depois de confirmado no destino com o mesmo tamanho.

**Métricas de sucesso:**
| Métrica | Baseline atual | Target | Prazo |
|---------|---------------|--------|-------|
| 🟡 Anexos entregues ao envio que chegam ao OneDrive | 🟡 processo manual, não medido | = 100% | 🟡 3 meses após entrada em operação |
| 🟡 Arquivos pré-existentes sobrescritos ou apagados | não se aplica | = 0 | 🟡 contínuo |
| 🟡 Contas pagas em atraso por falta de arquivamento | 🟡 não medido | = 0 por mês | 🟡 3 meses após entrada em operação |

---

## 4. Non-Goals (Fora do Escopo)

- 🟡 NG-01: Apagar, mover ou renomear arquivos já existentes na pasta de destino.
- 🟡 NG-02: Sincronização bidirecional: o que a equipe altera no OneDrive não volta para o sistema.
- 🟡 NG-03: Criar a estrutura de pastas do OneDrive além da subpasta exigida pela convenção de nomes (OQ-01).
- 🟡 NG-04: Enviar para Google Drive ou outro destino; só o remote Rclone configurado.
- 🟡 NG-05: Integração com "Meu Dinheiro", banco ou DDA (não-objetivos do PRD).

---

## 5. Usuários e Personas

**Usuário primário:** 🟡 analista-financeira, que abre a pasta `CONTAS A PAGAR` e encontra o documento já salvo e nomeado.
**Usuário secundário:** 🟡 operador-tecnico, que configura o remote do Rclone e trata falhas de envio.

**Jornada atual (sem a feature):**
1. 🟡 A analista baixa o anexo do e-mail.
2. 🟡 Renomeia-o e o salva na pasta, quando lembra.
3. 🟡 Documentos não salvos resultam em contas esquecidas.

**Jornada futura (com a feature):**
1. 🟡 A analista abre a pasta `CONTAS A PAGAR` no OneDrive.
2. 🟡 O documento está lá, com data, remetente e nome original no nome do arquivo.
3. 🟡 Ela lança a conta na linha de pagamento.

---

## 6. Requisitos Funcionais

### 6.1 Requisitos Principais

| ID | Requisito | Prioridade | Critério de Aceite |
|----|-----------|-----------|-------------------|
| RF-01 | 🟡 O sistema deve montar o nome de destino pela convenção vigente; até a resolução da OQ-01, a convenção provisória é `AAAA-MM-DD_<remetente>_<nome-original>.<ext>`, com a data de recebimento da mensagem e o remetente como a parte do endereço antes do `@`. | Must | 🟡 Anexo `Boleto Set.pdf`, de `cobranca@fornecedor.com.br`, recebido em 18/09/2026, vira `2026-09-18_cobranca_Boleto Set.pdf`. |
| RF-02 | 🟡 O sistema deve remover do nome os caracteres inválidos no OneDrive (`" * : < > ? / \ \|`), espaços nas pontas e pontos finais, e limitar o nome a 200 caracteres preservando a extensão. | Must | 🟡 `NF: 123?.pdf` vira `NF 123.pdf`; um nome de 300 caracteres é truncado para 200, terminando em `.pdf`. |
| RF-03 | 🟡 O sistema deve enviar cada arquivo com o Rclone para `<RCLONE_REMOTE>:<destino da caixa>/<nome>`, sem nunca sobrescrever arquivo existente. | Must | 🟡 Com um arquivo de mesmo nome já no destino, o existente permanece com o conteúdo original. |
| RF-04 | 🟡 O sistema deve, quando já existir no destino arquivo de mesmo nome e conteúdo diferente, acrescentar o sufixo `_2`, `_3` e assim por diante antes da extensão. | Must | 🟡 Segundo `boleto.pdf` distinto no mesmo dia e remetente vira `..._boleto_2.pdf`. |
| RF-05 | 🟡 O sistema deve, quando já existir no destino arquivo de mesmo nome e mesmo tamanho e hash, considerar o anexo `enviado` sem novo upload. | Must | 🟡 Reenviar um anexo idêntico não cria cópia e o registro passa a `enviado`. |
| RF-06 | 🟡 O sistema deve confirmar cada envio consultando o destino e comparando o tamanho do arquivo remoto com o local; só então marcar `enviado` e gravar `caminho_destino` no registro. | Must | 🟡 Com o tamanho remoto divergente, o registro fica `falha-envio` e o log indica "tamanho divergente". |
| RF-07 | 🟡 O sistema deve marcar `falha-envio` quando o Rclone retornar erro, mantendo o anexo apto a nova tentativa na próxima execução. | Must | 🟡 Com o OneDrive indisponível, o anexo é reenviado na execução seguinte sem intervenção. |
| RF-08 | 🟡 O sistema deve apagar a cópia local do anexo da pasta de trabalho assim que o envio for confirmado. | Must | 🟡 Após uma execução sem falhas, a pasta de trabalho está vazia. |
| RF-09 | 🟡 O sistema deve oferecer o comando `testar-onedrive`, que envia um arquivo de teste de 1 KB ao destino, confirma-o e apaga só esse arquivo de teste (`rclone deletefile` no caminho exato), reportando sucesso ou a causa da falha. | Should | 🟡 Com o remote bem configurado, o comando imprime "OneDrive: escrita confirmada em <destino>". |
| RF-10 | 🟡 O sistema deve registrar no log, para cada envio, o nome final, o destino e o tempo gasto. | Should | 🟡 O log contém `enviado: 2026-09-18_cobranca_Boleto Set.pdf -> <Empresa> Financeiro/CONTAS A PAGAR (1.2 s)`. |

### 6.2 Fluxo Principal (Happy Path)

1. 🟡 O sistema recebe do [`coleta-email.md`](./coleta-email.md) a lista de anexos com estado `extraido` ou `falha-envio`.
2. 🟡 Para cada anexo, o sistema monta o nome final (RF-01, RF-02).
3. 🟡 O sistema consulta o destino para verificar se há arquivo de mesmo nome (RF-04, RF-05).
4. 🟡 O sistema envia o arquivo via Rclone sem sobrescrita (RF-03).
5. 🟡 O sistema confirma o tamanho remoto (RF-06), marca `enviado` e apaga a cópia local (RF-08).
6. 🟡 Resultado: o documento está na pasta `CONTAS A PAGAR` e o registro reflete o caminho final.

### 6.3 Fluxos Alternativos

**Fluxo Alternativo A — Destino por caixa:**
1. 🟡 A caixa tem `DESTINO_ONEDRIVE<n>` definido.
2. 🟡 O envio usa esse destino em vez do global.

**Fluxo Alternativo B — Simulação:**
1. 🟡 A execução foi iniciada com `--simular`.
2. 🟡 O sistema monta os nomes e registra no log o que enviaria, sem chamar o Rclone nem alterar o registro.

---

## 7. Requisitos Não-Funcionais

| ID | Requisito | Valor alvo | Observação |
|----|-----------|-----------|------------|
| RNF-01 | 🟡 Performance | 🟡 < 10 s por arquivo de até 5 MB | 🟡 Boletos e DANFEs raramente passam de 1 MB. |
| RNF-02 | 🟡 Integridade | 🟡 0 arquivos sobrescritos | 🟡 Garantido por RF-03 a RF-05. |
| RNF-03 | 🟡 Resiliência | 🟡 Timeout de 120 s por chamada ao Rclone | 🟡 Chamada travada vira `falha-envio`. |
| RNF-04 | 🟡 Custo | 🟡 = 0 além da VPS | 🟡 Rclone e OneDrive já contratado. |

---

## 8. Design e Interface

**Componentes afetados:** 🟡 remote Rclone do OneDrive; pasta `<Empresa> Financeiro/CONTAS A PAGAR`; registro de processados; comando `testar-onedrive`.

**Comportamento esperado:**
🟡 A interface da analista é a própria pasta do OneDrive, no navegador ou no aplicativo. O sistema só acrescenta arquivos.

**Estados da UI:**
- 🟡 Estado vazio: sem anexos novos, a pasta não muda e o log registra "nada a enviar".
- 🟡 Estado de carregamento: não se aplica; o arquivo só aparece na pasta quando o upload termina.
- 🟡 Estado de erro: a pasta não recebe o arquivo; log e aviso de falha indicam a causa.
- 🟡 Estado de sucesso: o arquivo aparece na pasta com o nome padronizado.

---

## 9. Modelo de Dados

**Entidades novas ou modificadas:**

```
AnexoProcessado (definido em coleta-email.md) — campos alterados por este componente:
  estado: "extraido" -> "enviado" | "falha-envio"
  caminho_destino: str            // "<destino>/<nome final>"
  tentativas_envio: int           // incrementado a cada falha
  ultimo_erro: str | nulo         // mensagem resumida do Rclone, sem credenciais
```

**Migrações necessárias:** 🟡 Não; os campos nascem com o registro.

---

## 10. Integrações e Dependências

| Dependência | Tipo | Impacto se indisponível |
|-------------|------|------------------------|
| 🟡 Rclone (backend `onedrive`, tipo *business*) instalado na VPS | Obrigatória | 🟡 Todos os anexos ficam `falha-envio`; aviso de falha. |
| 🟡 Token OAuth do remote, obtido com `rclone authorize` numa máquina com navegador e copiado para a VPS | Obrigatória | 🟡 Token expirado ou revogado: aviso de falha com instrução de renovação. |
| 🟡 Permissão de escrita da conta autenticada em `<Empresa> Financeiro/CONTAS A PAGAR`, no OneDrive de `<conta-admin>@<dominio>` | Obrigatória | 🟡 Erro de acesso negado; aviso de falha. |
| 🟡 Microsoft Graph / OneDrive for Business (tenant `<tenant>`) | Obrigatória | 🟡 Indisponibilidade ou limite de requisições: `falha-envio` e nova tentativa em 30 min. |

---

## 11. Edge Cases e Tratamento de Erros

| Cenário | Trigger | Comportamento esperado |
|---------|---------|----------------------|
| 🟡 EC-01: Token expirado | 🟡 Refresh token revogado ou vencido | 🟡 Todos os envios da execução ficam `falha-envio`; aviso de falha "OneDrive: reautorize o remote" com o comando da documentação. |
| 🟡 EC-02: Acesso negado | 🟡 A conta autenticada perdeu permissão na pasta | 🟡 `falha-envio`; aviso de falha com o destino e o erro 403. |
| 🟡 EC-03: Mesmo nome, conteúdo idêntico | 🟡 Arquivo já enviado por outro e-mail | 🟡 Nenhum upload; registro `enviado` apontando o arquivo existente (RF-05). |
| 🟡 EC-04: Mesmo nome, conteúdo diferente | 🟡 Dois `boleto.pdf` distintos do mesmo remetente no mesmo dia | 🟡 Sufixo `_2` (RF-04). |
| 🟡 EC-05: Limite de requisições | 🟡 HTTP 429 do OneDrive | 🟡 Rclone aplica espera e nova tentativa; persistindo, `falha-envio` e retomada na execução seguinte. |
| 🟡 EC-06: Pasta de destino inexistente | 🟡 Pasta renomeada ou movida pela equipe | 🟡 Não cria a pasta; `falha-envio` e aviso "destino não encontrado: <caminho>". |
| 🟡 EC-07: Falhas repetidas | 🟡 Mesmo anexo com 5 tentativas falhas | 🟡 Aviso de falha específico listando o anexo; as tentativas continuam a cada execução. |
| 🟡 EC-08: Disco da VPS cheio | 🟡 Falha ao gravar na pasta de trabalho | 🟡 Execução abortada e aviso de falha; nenhum registro marcado `enviado`. |

---

## 12. Segurança e Privacidade

- **Autenticação:** 🟡 OAuth 2.0 do Rclone no tenant Microsoft; o token fica no `rclone.conf` do usuário de serviço, com permissão 600.
- **Autorização:** 🟡 a conta autenticada precisa só de edição na pasta de destino; o sistema nunca usa comandos de sincronização ou exclusão em massa (`sync`, `delete`, `purge`, `move`); a única exclusão permitida é a do arquivo de teste do RF-09, pelo caminho exato.
- **Dados sensíveis:** 🟡 os documentos saem da VPS diretamente para o OneDrive da empresa; a cópia local é apagada após a confirmação (RF-08).
- **Auditoria:** 🟡 o registro guarda, por anexo, o caminho final no OneDrive e a data do envio.

---

## 13. Plano de Rollout

- **Estratégia:** 🟡 primeiro `testar-onedrive`; depois uma execução com `--simular`; por fim, produção.
- **Como reverter (rollback):** 🟡 desativar o agendamento; os arquivos enviados podem ser identificados pelo registro (`caminho_destino`) e removidos manualmente, se necessário.
- **Monitoramento pós-deploy:** 🟡 nos primeiros 7 dias, conferir diariamente a pasta com a equipe financeira e comparar com o log.

---

## 14. Open Questions

| # | Pergunta | Impacto | Dono | Prazo |
|---|---------|---------|------|-------|
| OQ-01 | 🟡 ⚠️ ABERTO: qual é o padrão de nomes e de subpastas já usado na pasta `CONTAS A PAGAR`? O usuário pediu para seguir o padrão atual; ele será levantado inspecionando a pasta com `rclone lsf` assim que o remote estiver configurado. Até lá vale a convenção provisória do RF-01. | Alto | iago | 🟡 antes da entrada em operação |
| OQ-02 | 🟡 ⚠️ ABERTO: qual conta autoriza o Rclone: `<conta-admin>@<dominio>` ou uma conta com a pasta compartilhada? Com conta compartilhada, o remote precisa apontar para o drive do administrador. | Alto | iago | 🟡 antes do primeiro teste real |
| OQ-03 | 🟡 ⚠️ ABERTO: o tenant `<tenant>` exige consentimento de administrador para o aplicativo do Rclone? | Alto | iago | 🟡 antes do primeiro teste real |

---

## 15. Decisões Tomadas (Decision Log)

| Decisão | Alternativas consideradas | Racional |
|---------|--------------------------|---------|
| 🟡 Rclone como cliente do OneDrive | 🟡 Microsoft Graph direto em Python | 🟡 Escolha do usuário; o Rclone já trata OAuth, retentativas e limites de requisição. |
| 🟡 Nunca sobrescrever; sufixo numérico em conflito | 🟡 Sobrescrever; pular o arquivo | 🟡 A pasta é de trabalho da equipe; perder um arquivo é pior que ter um sufixo. |
| 🟡 Confirmar pelo tamanho remoto | 🟡 Confiar no código de saída do Rclone | 🟡 Barato e detecta envio truncado; o Rclone também verifica hash no upload. |
| 🟡 Apagar a cópia local após confirmação | 🟡 Manter arquivo local | 🟡 Minimiza dados fiscais e pessoais na VPS (LGPD). |

---

## Apêndice

### Referências
- 🟡 [`prd.md`](../prd.md), seções 4, 6, 7 e 8.
- 🟡 Documentação do backend `onedrive` do Rclone: https://rclone.org/onedrive/

### Histórico de Revisões
| Versão | Data | Autor | Mudanças |
|--------|------|-------|---------|
| 1.0 | 2026-09-18 | reversa-spec-sdd | Criação inicial |

---

## Relatório de avaliação

- **Score:** 100.0/100 (spec_scorer.py, rubrica `evaluation_rubric.md`)
- **Iterações:** 1. Aprovada na primeira avaliação.
- **Gaps críticos:** nenhum apontado pelo scorer.
- **Ressalva:** o score mede estrutura e testabilidade, não a correção das premissas. As questões ⚠️ ABERTO da seção 14 continuam bloqueando a entrada em operação.

Gerado por reversa-spec-sdd em 2026-09-18T19:12:18Z
