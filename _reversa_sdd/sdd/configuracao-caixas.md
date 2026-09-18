# Spec: configuracao-caixas

> Selo 🟡 PLANEJADO em todos os itens. Fonte: [`prd.md`](../prd.md).

**Versão:** 1.0
**Status:** Rascunho
**Autor:** reversa-spec-sdd
**Data:** 2026-09-18
**Reviewers:** iago

---

## 1. Resumo

🟡 Componente que lê o arquivo `.env` e monta a lista de caixas de e-mail a processar, com a pasta monitorada de cada uma, o remote do Rclone, a pasta de destino no OneDrive e o canal de aviso de falha. Existe para que acrescentar uma caixa nova seja questão de configuração, sem alteração de código.

---

## 2. Contexto e Motivação

**Problema:**
🟡 Hoje o `.env` contém apenas `EMAIL1` e `SENHA_EMAIL1`, e o áudio de origem cita outras caixas (`financeiro@<empresa-2>`, `administrativo@<empresa-3>`) que entrarão depois. Sem um contrato de configuração, cada caixa nova exigiria mexer no código.

**Evidências:**
🟡 Requisito confirmado pelo usuário em 2026-09-18: "precisamos preparar a aplicação para que coloquemos mais e-mails" (`ideation.md`, Notas).

**Por que agora:**
🟡 A convenção de nomes precisa ser fixada antes do primeiro código, porque o `.env` já existe com o padrão numerado `EMAIL1`/`SENHA_EMAIL1`.

---

## 3. Goals (Objetivos)

- [ ] 🟡 G-01: Acrescentar uma caixa exige apenas novas linhas no `.env`, sem alteração de código.
- [ ] 🟡 G-02: Erros de configuração são detectados antes de qualquer acesso à rede e descritos numa mensagem que cita a variável problemática.
- [ ] 🟡 G-03: O `.env` atual (`EMAIL1`, `SENHA_EMAIL1`) funciona sem nenhuma variável adicional obrigatória para a parte de e-mail.

**Métricas de sucesso:**
| Métrica | Baseline atual | Target | Prazo |
|---------|---------------|--------|-------|
| 🟡 Linhas de código alteradas para incluir uma caixa | não se aplica | = 0 linhas | 🟡 na entrega do MVP |
| 🟡 Erros de configuração detectados antes da conexão IMAP | 0% | = 100% dos casos da seção 11 | 🟡 na entrega do MVP |

---

## 4. Non-Goals (Fora do Escopo)

- 🟡 NG-01: Interface gráfica ou web para cadastrar caixas; a configuração é feita editando o `.env`.
- 🟡 NG-02: Cofre de segredos (Vault, gerenciadores de senha): as credenciais ficam no `.env`, protegido por permissão de arquivo.
- 🟡 NG-03: Autenticação OAuth 2.0 no Gmail: o MVP usa senha de app; OAuth só entra se o teste de login com senha de app falhar (ver OQ-02).
- 🟡 NG-04: Recarregar a configuração durante uma execução: o `.env` é lido uma vez por execução.

---

## 5. Usuários e Personas

**Usuário primário:** 🟡 operador-tecnico (iago e, depois da entrega, quem a empresa cliente designar), que edita o `.env` na VPS.
**Usuário secundário:** 🟡 nenhum; a analista-financeira não interage com a configuração.

**Jornada atual (sem a feature):**
1. 🟡 Existe um único par de credenciais no `.env`.
2. 🟡 Não há forma definida de declarar outra caixa, a pasta monitorada ou o destino.

**Jornada futura (com a feature):**
1. 🟡 O operador acrescenta `EMAIL2` e `SENHA_EMAIL2` (e, se quiser, `PASTA_EMAIL2`) ao `.env`.
2. 🟡 Na execução seguinte, o sistema passa a processar a nova caixa.
3. 🟡 Se faltar uma variável, o sistema registra no log e avisa qual caixa e qual variável estão incompletas, e segue com as demais caixas.

---

## 6. Requisitos Funcionais

### 6.1 Requisitos Principais

| ID | Requisito | Prioridade | Critério de Aceite |
|----|-----------|-----------|-------------------|
| RF-01 | 🟡 O sistema deve descobrir as caixas procurando no `.env` todas as variáveis `EMAIL<n>`, com `<n>` inteiro positivo, sem exigir numeração contínua. | Must | 🟡 Com `EMAIL1` e `EMAIL3` definidos, o sistema monta 2 caixas, de índices 1 e 3. |
| RF-02 | 🟡 O sistema deve exigir, para cada `EMAIL<n>`, a variável `SENHA_EMAIL<n>` não vazia. | Must | 🟡 Com `EMAIL2` sem `SENHA_EMAIL2`, a caixa 2 é marcada inválida com a mensagem "caixa 2: SENHA_EMAIL2 ausente". |
| RF-03 | 🟡 O sistema deve ler a pasta monitorada de `PASTA_EMAIL<n>`, usando `INBOX` quando a variável estiver ausente. | Must | 🟡 Sem `PASTA_EMAIL1`, a caixa 1 é configurada com a pasta `INBOX`. |
| RF-04 | 🟡 O sistema deve ler o servidor IMAP de `IMAP_HOST_EMAIL<n>`, usando `imap.gmail.com` na porta 993 quando ausente. | Must | 🟡 Sem a variável, a caixa usa `imap.gmail.com:993`. |
| RF-05 | 🟡 O sistema deve ler o nome do remote do Rclone de `RCLONE_REMOTE` e a pasta de destino de `DESTINO_ONEDRIVE` (obrigatória, sem valor padrão, pois o caminho real contém o nome da empresa e fica só no `.env`); `DESTINO_ONEDRIVE<n>` sobrepõe o destino da caixa `<n>`. | Must | 🟡 Com `DESTINO_ONEDRIVE2` definido, só a caixa 2 usa esse destino; as demais usam o global. |
| RF-06 | 🟡 O sistema deve ler a data inicial de coleta de `DATA_INICIAL` (formato `AAAA-MM-DD`, obrigatória), aplicada às caixas ainda sem histórico. | Must | 🟡 Com `DATA_INICIAL=2026-09-01`, a primeira execução de uma caixa nova considera só mensagens a partir dessa data; sem a variável, a execução é abortada com código 2. |
| RF-07 | 🟡 O sistema deve ler `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` para o aviso de falha. | Must | 🟡 Com as duas variáveis definidas, a configuração expõe o canal de aviso como ativo. |
| RF-08 | 🟡 O sistema deve validar toda a configuração antes de qualquer acesso à rede e separar erros globais (abortam a execução) de erros por caixa (invalidam só aquela caixa). | Must | 🟡 `RCLONE_REMOTE` ausente aborta a execução com código de saída 2; `SENHA_EMAIL2` ausente invalida só a caixa 2. |
| RF-09 | 🟡 O sistema nunca deve gravar senhas nem o token do Telegram em log, mensagem de aviso ou saída de terminal. | Must | 🟡 Busca pelo valor de `SENHA_EMAIL1` nos logs de um ciclo completo não retorna ocorrência. |
| RF-10 | 🟡 O sistema deve oferecer o comando `verificar-config`, que imprime as caixas encontradas (índice, endereço, pasta, destino) com as senhas mascaradas e sai sem acessar a rede. | Should | 🟡 O comando lista a caixa 1 como `1 · <endereço> · INBOX · <Empresa> Financeiro/CONTAS A PAGAR` e a senha como `****`. |
| RF-11 | 🟡 O sistema deve emitir alerta no log quando o arquivo `.env` tiver permissão de leitura para grupo ou outros usuários. | Should | 🟡 Com `chmod 644 .env`, o log registra "permissão do .env mais aberta que 600". |

### 6.2 Fluxo Principal (Happy Path)

1. 🟡 O ponto de entrada (ver [`execucao-monitoramento.md`](./execucao-monitoramento.md)) solicita a configuração.
2. 🟡 O sistema lê o `.env` do diretório de instalação.
3. 🟡 O sistema valida as variáveis globais (`RCLONE_REMOTE`, `DESTINO_ONEDRIVE`, `DATA_INICIAL`, Telegram).
4. 🟡 O sistema descobre os índices `<n>` de `EMAIL<n>` e monta uma caixa por índice, com os padrões dos RF-03 a RF-05.
5. 🟡 Resultado: uma lista ordenada por índice de caixas válidas, mais a lista de caixas inválidas com o motivo.

### 6.3 Fluxos Alternativos

**Fluxo Alternativo A — Caixa incompleta:**
1. 🟡 O sistema encontra `EMAIL2` sem `SENHA_EMAIL2`.
2. 🟡 A caixa 2 entra na lista de inválidas; a execução segue com as válidas e o aviso de falha cita a caixa 2.

**Fluxo Alternativo B — Nenhuma caixa válida:**
1. 🟡 O sistema não encontra nenhuma caixa válida.
2. 🟡 A execução termina com código de saída 2 e aviso de falha.

---

## 7. Requisitos Não-Funcionais

| ID | Requisito | Valor alvo | Observação |
|----|-----------|-----------|------------|
| RNF-01 | 🟡 Performance | 🟡 Leitura e validação em < 1 s | 🟡 Sem acesso à rede nesta etapa. |
| RNF-02 | 🟡 Compatibilidade | 🟡 Aceita o `.env` atual sem alteração | 🟡 Só `EMAIL1`/`SENHA_EMAIL1` para a parte de e-mail. |
| RNF-03 | 🟡 Segurança | 🟡 `.env` com permissão 600 recomendada | 🟡 Arquivo já listado no `.gitignore`. |
| RNF-04 | 🟡 Portabilidade | 🟡 Python 3.11 ou superior, Linux | 🟡 VPS do operador e, depois, da empresa. |

---

## 8. Design e Interface

**Componentes afetados:** 🟡 arquivo `.env`; comando `verificar-config`; consumidores: `coleta-email`, `envio-onedrive`, `execucao-monitoramento`.

**Comportamento esperado:**
🟡 Não há interface gráfica. A interação é o `.env` e a saída de terminal do `verificar-config`.

**Estados da UI:**
- 🟡 Estado vazio: nenhuma `EMAIL<n>` encontrada; mensagem "nenhuma caixa configurada no .env".
- 🟡 Estado de carregamento: não se aplica (operação local em < 1 s).
- 🟡 Estado de erro: cada erro numa linha, no formato `<escopo>: <variável> <problema>`.
- 🟡 Estado de sucesso: lista das caixas válidas com senha mascarada.

---

## 9. Modelo de Dados

**Entidades novas ou modificadas:**

```
Caixa {
  indice: int               // <n> de EMAIL<n>
  endereco: str             // valor de EMAIL<n>
  senha: str                // valor de SENHA_EMAIL<n>; nunca serializado
  pasta: str                // PASTA_EMAIL<n> ou "INBOX"
  imap_host: str            // IMAP_HOST_EMAIL<n> ou "imap.gmail.com"
  imap_porta: int           // 993
  destino: str              // DESTINO_ONEDRIVE<n> ou DESTINO_ONEDRIVE
}

Configuracao {
  caixas: lista<Caixa>
  caixas_invalidas: lista<(indice, motivo)>
  rclone_remote: str
  data_inicial: date
  telegram_bot_token: str   // nunca serializado
  telegram_chat_id: str
}
```

**Migrações necessárias:** 🟡 Não. O `.env` atual continua válido; as variáveis novas são acréscimos.

---

## 10. Integrações e Dependências

| Dependência | Tipo | Impacto se indisponível |
|-------------|------|------------------------|
| 🟡 Arquivo `.env` no diretório de instalação | Obrigatória | 🟡 Execução abortada com código 2 e mensagem "arquivo .env não encontrado". |
| 🟡 Biblioteca de leitura de `.env` (ex.: `python-dotenv`) ou leitor próprio | Obrigatória | 🟡 Sem ela, a instalação falha; documentada no guia de instalação. |

---

## 11. Edge Cases e Tratamento de Erros

| Cenário | Trigger | Comportamento esperado |
|---------|---------|----------------------|
| 🟡 EC-01: Numeração com lacuna | 🟡 `EMAIL1` e `EMAIL3`, sem `EMAIL2` | 🟡 Monta as caixas 1 e 3, sem erro. |
| 🟡 EC-02: Senha ausente | 🟡 `EMAIL2` sem `SENHA_EMAIL2` | 🟡 Caixa 2 inválida; demais seguem; aviso de falha cita a caixa 2. |
| 🟡 EC-03: Senha órfã | 🟡 `SENHA_EMAIL4` sem `EMAIL4` | 🟡 Alerta no log "SENHA_EMAIL4 sem EMAIL4"; nenhuma caixa criada. |
| 🟡 EC-04: Endereço duplicado | 🟡 `EMAIL1` e `EMAIL2` com o mesmo endereço e a mesma pasta | 🟡 Caixa de maior índice inválida com o motivo "duplicada da caixa 1". |
| 🟡 EC-05: Data inválida | 🟡 `DATA_INICIAL=18/09/2026` | 🟡 Erro global: "DATA_INICIAL fora do formato AAAA-MM-DD"; execução abortada com código 2. |
| 🟡 EC-06: Remote ou destino ausente | 🟡 `RCLONE_REMOTE` ou `DESTINO_ONEDRIVE` vazio | 🟡 Erro global; execução abortada com código 2. |
| 🟡 EC-07: Telegram incompleto | 🟡 Só uma das duas variáveis do Telegram definida | 🟡 Alerta no log; a execução segue sem canal de aviso e registra que falhas não serão notificadas. |
| 🟡 EC-08: Arquivo `.env` ausente ou ilegível (falha de leitura) | 🟡 Arquivo removido ou sem permissão | 🟡 Execução abortada com código 2 e mensagem clara. |

---

## 12. Segurança e Privacidade

- **Autenticação:** 🟡 não se aplica; o componente só lê um arquivo local.
- **Autorização:** 🟡 o `.env` deve pertencer ao usuário de serviço da VPS, com permissão 600 (RF-11 alerta se estiver mais aberta).
- **Dados sensíveis:** 🟡 senhas de app do Gmail e token do Telegram; nunca registrados (RF-09), mascarados no `verificar-config` (RF-10).
- **Auditoria:** 🟡 o log registra quais caixas foram carregadas e quais foram invalidadas, sem valores sensíveis.

---

## 13. Plano de Rollout

- **Estratégia:** 🟡 big bang: entra junto com o MVP.
- **Como reverter (rollback):** 🟡 remover as linhas da caixa nova do `.env`; a execução seguinte a ignora.
- **Monitoramento pós-deploy:** 🟡 rodar `verificar-config` após cada edição do `.env` e conferir o log da primeira execução.

---

## 14. Open Questions

| # | Pergunta | Impacto | Dono | Prazo |
|---|---------|---------|------|-------|
| OQ-01 | 🟡 ⚠️ ABERTO: qual pasta da caixa `EMAIL1` a equipe usa? O padrão `INBOX` vale até a resposta. | Alto | iago | 🟡 antes do primeiro teste real |
| OQ-02 | 🟡 ⚠️ ABERTO: `SENHA_EMAIL1` é senha de app do Google? Se for a senha comum, o login IMAP será recusado. | Alto | iago | 🟡 antes do primeiro teste real |
| OQ-03 | 🟡 ⚠️ ABERTO: qual `DATA_INICIAL` usar na primeira execução? Um valor antigo sobe todo o histórico para o OneDrive. | Médio | iago | 🟡 antes da entrada em operação |

---

## 15. Decisões Tomadas (Decision Log)

| Decisão | Alternativas consideradas | Racional |
|---------|--------------------------|---------|
| 🟡 Variáveis numeradas `EMAIL<n>`/`SENHA_EMAIL<n>` | 🟡 Arquivo YAML ou JSON de caixas | 🟡 Mantém compatível o `.env` atual e é o formato que o usuário já adotou. |
| 🟡 Caixa inválida não aborta as demais | 🟡 Abortar toda a execução | 🟡 Uma credencial errada não deve interromper o arquivamento das outras caixas. |
| 🟡 `DATA_INICIAL` obrigatória | 🟡 Processar todo o histórico | 🟡 Evita subir anos de anexos para a pasta de contas a pagar na primeira execução. |

---

## Apêndice

### Referências
- 🟡 [`prd.md`](../prd.md), seções 4, 6 e 9.
- 🟡 [`ideation.md`](../ideation.md), Notas (requisito de várias caixas).

### Histórico de Revisões
| Versão | Data | Autor | Mudanças |
|--------|------|-------|---------|
| 1.0 | 2026-09-18 | reversa-spec-sdd | Criação inicial |

---

## Relatório de avaliação

- **Score:** 100.0/100 (spec_scorer.py, rubrica `evaluation_rubric.md`)
- **Iterações:** 2. Iteração 1 corrigiu falso positivo do scorer (placeholder ou termo vago em identificador técnico); sem alteração de conteúdo.
- **Gaps críticos:** nenhum apontado pelo scorer.
- **Ressalva:** o score mede estrutura e testabilidade, não a correção das premissas. As questões ⚠️ ABERTO da seção 14 continuam bloqueando a entrada em operação.

Gerado por reversa-spec-sdd em 2026-09-18T19:12:18Z
