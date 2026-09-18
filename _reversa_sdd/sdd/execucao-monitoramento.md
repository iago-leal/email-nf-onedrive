# Spec: execucao-monitoramento

> Selo 🟡 PLANEJADO em todos os itens. Fonte: [`prd.md`](../prd.md).

**Versão:** 1.0
**Status:** Rascunho
**Autor:** reversa-spec-sdd
**Data:** 2026-09-18
**Reviewers:** iago

---

## 1. Resumo

🟡 Componente que oferece o ponto de entrada único da ferramenta, executa o ciclo configuração → coleta → envio a cada 30 minutos numa VPS Linux via cron, impede execuções sobrepostas, grava log, avisa o operador por Telegram quando algo falha e inclui a documentação de instalação e operação para a entrega à empresa cliente.

---

## 2. Contexto e Motivação

**Problema:**
🟡 Uma automação que falha em silêncio recria o esquecimento de contas que ela deveria eliminar. Além disso, o operador quer entregar a ferramenta e passá-la adiante, o que exige operação documentada.

**Evidências:**
🟡 Persona operador-tecnico: objetivo "entregar e passar adiante" (`personas.md`). Respostas do usuário em 2026-09-18: VPS, execução a cada 30 min, aviso por Telegram, sem custo recorrente além da VPS.

**Por que agora:**
🟡 A execução sem supervisão na VPS é a condição para o MVP entrar em operação.

---

## 3. Goals (Objetivos)

- [ ] 🟡 G-01: O ciclo completo roda a cada 30 min sem intervenção humana.
- [ ] 🟡 G-02: Toda falha chega ao operador pelo Telegram em até 5 min após o fim da execução com falha.
- [ ] 🟡 G-03: Uma pessoa da empresa cliente com nível intermediário instala a ferramenta numa VPS nova seguindo só a documentação.

**Métricas de sucesso:**
| Métrica | Baseline atual | Target | Prazo |
|---------|---------------|--------|-------|
| 🟡 Execuções agendadas que de fato rodaram | não se aplica | ≥ 99% por mês | 🟡 3 meses após entrada em operação |
| 🟡 Falhas sem aviso no Telegram | não se aplica | = 0 | 🟡 contínuo |
| 🟡 Tempo de instalação numa VPS nova seguindo o guia | não se aplica | < 60 min | 🟡 na entrega à empresa cliente |

---

## 4. Non-Goals (Fora do Escopo)

- 🟡 NG-01: Painel web de monitoramento; o acompanhamento é pelo log e pelo Telegram.
- 🟡 NG-02: Contêiner Docker ou orquestração; instalação direta com Python e cron.
- 🟡 NG-03: Alta disponibilidade ou mais de uma VPS executando em paralelo.
- 🟡 NG-04: Aviso de sucesso a cada execução; só falhas e recuperações são notificadas.
- 🟡 NG-05: Suporte a Windows ou macOS como servidor de produção.

---

## 5. Usuários e Personas

**Usuário primário:** 🟡 operador-tecnico (iago e, após a entrega, quem a empresa cliente designar), que instala, agenda, recebe avisos e corrige falhas.
**Usuário secundário:** 🟡 analista-financeira, que se beneficia da regularidade das execuções.

**Jornada atual (sem a feature):**
1. 🟡 Não há execução automática; tudo depende de alguém abrir o e-mail.
2. 🟡 Não há como saber se um documento deixou de ser arquivado.

**Jornada futura (com a feature):**
1. 🟡 O operador instala a ferramenta na VPS seguindo o guia e agenda o cron.
2. 🟡 O sistema executa a cada 30 min e registra o resultado no log.
3. 🟡 Quando algo falha, o operador recebe no Telegram a causa e o que fazer.
4. 🟡 Quando a falha é resolvida, recebe o aviso de recuperação.

---

## 6. Requisitos Funcionais

### 6.1 Requisitos Principais

| ID | Requisito | Prioridade | Critério de Aceite |
|----|-----------|-----------|-------------------|
| RF-01 | 🟡 O sistema deve oferecer uma linha de comando com os subcomandos `executar`, `verificar-config` e `testar-onedrive`, e a opção `--simular` em `executar`. | Must | 🟡 `email-nf-onedrive --help` lista os três subcomandos. |
| RF-02 | 🟡 O subcomando `executar` deve rodar, em ordem, a carga da configuração, a coleta de todas as caixas válidas e o envio dos anexos coletados. | Must | 🟡 Com um e-mail de teste com PDF, uma execução termina com o arquivo no OneDrive. |
| RF-03 | 🟡 O sistema deve impedir execuções sobrepostas com um arquivo de trava; se a trava estiver ativa, a nova execução termina em menos de 1 s com código 0 e a linha de log "execução anterior em andamento". | Must | 🟡 Duas chamadas simultâneas resultam em um ciclo completo e uma saída imediata. |
| RF-04 | 🟡 O sistema deve considerar abandonada a trava com mais de 25 min e retomá-la, registrando o fato no log. | Must | 🟡 Com trava de 30 min de idade, a execução prossegue e o log registra "trava abandonada removida". |
| RF-05 | 🟡 O sistema deve sair com código 0 quando tudo der certo, 1 quando houver falha parcial (alguma caixa ou envio falhou) e 2 quando houver erro de configuração ou falha total. | Must | 🟡 Com senha errada só na caixa 2, o código de saída é 1. |
| RF-06 | 🟡 O sistema deve gravar log em arquivo, uma linha por evento, com data e hora ISO 8601, nível, caixa e mensagem, com rotação diária e retenção de 30 dias. | Must | 🟡 Após 31 dias de operação, existem no máximo 30 arquivos de log. |
| RF-07 | 🟡 O sistema deve enviar aviso ao Telegram (API de bots, `sendMessage`) ao fim de toda execução com código 1 ou 2, contendo o código, as caixas afetadas, a causa resumida de cada falha e a ação sugerida. | Must | 🟡 Com a caixa 1 recusando o login, chega ao chat uma mensagem citando "caixa 1", "autenticação recusada" e "verifique a senha de app". |
| RF-08 | 🟡 O sistema deve suprimir avisos repetidos: uma falha de mesma causa é notificada na primeira ocorrência e depois no máximo a cada 6 h enquanto persistir. | Must | 🟡 Com a mesma falha por 3 h (6 execuções), chega 1 aviso. |
| RF-09 | 🟡 O sistema deve enviar aviso de recuperação na primeira execução com código 0 após uma sequência de falhas. | Should | 🟡 Após corrigir a senha, chega "recuperado: caixa 1 voltou a funcionar". |
| RF-10 | 🟡 O sistema deve, com `--simular`, coletar e classificar sem enviar ao OneDrive, sem alterar o registro de processados e sem enviar aviso ao Telegram. | Must | 🟡 Após `executar --simular`, o registro e a pasta do OneDrive estão inalterados e o log lista o que seria enviado. |
| RF-11 | 🟡 O sistema deve registrar no fim de cada execução um resumo com a duração, as caixas processadas e as contagens de anexos extraídos, enviados e com falha. | Must | 🟡 O log termina com `resumo: 1 caixa, 3 extraídos, 3 enviados, 0 falhas, 42 s`. |
| RF-12 | 🟡 O repositório deve conter um guia de instalação e operação cobrindo: requisitos da VPS; instalação do Python e do Rclone; criação da senha de app do Google; `rclone authorize` numa máquina com navegador e cópia do token; preenchimento do `.env`; criação do bot do Telegram; linha do cron; como acrescentar uma caixa; como renovar credenciais; como ler o log. | Must | 🟡 Uma pessoa que não participou do desenvolvimento instala a ferramenta numa VPS nova em < 60 min seguindo só o guia. |
| RF-13 | 🟡 O repositório deve conter um `.env.example` com todas as variáveis, sem valores reais, e a linha do cron pronta para copiar. | Must | 🟡 O arquivo lista `EMAIL1`, `SENHA_EMAIL1`, `PASTA_EMAIL1`, `RCLONE_REMOTE`, `DESTINO_ONEDRIVE`, `DATA_INICIAL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. |

### 6.2 Fluxo Principal (Happy Path)

1. 🟡 O cron dispara `email-nf-onedrive executar` no minuto 0 e no minuto 30 de cada hora.
2. 🟡 O sistema adquire a trava (RF-03).
3. 🟡 O sistema carrega a configuração ([`configuracao-caixas.md`](./configuracao-caixas.md)).
4. 🟡 O sistema executa a coleta ([`coleta-email.md`](./coleta-email.md)) e o envio ([`envio-onedrive.md`](./envio-onedrive.md)).
5. 🟡 O sistema grava o resumo (RF-11), libera a trava e sai com código 0.
6. 🟡 Resultado: documentos novos no OneDrive, log atualizado, nenhum aviso enviado.

### 6.3 Fluxos Alternativos

**Fluxo Alternativo A — Falha parcial:**
1. 🟡 Uma caixa ou um envio falha.
2. 🟡 O sistema conclui as demais etapas, envia o aviso ao Telegram (RF-07, RF-08) e sai com código 1.

**Fluxo Alternativo B — Telegram indisponível:**
1. 🟡 O envio do aviso falha.
2. 🟡 O sistema registra no log "aviso não entregue" e tenta de novo na execução seguinte, sem alterar o código de saída.

---

## 7. Requisitos Não-Funcionais

| ID | Requisito | Valor alvo | Observação |
|----|-----------|-----------|------------|
| RNF-01 | 🟡 Duração | 🟡 Ciclo típico < 5 min | 🟡 Bem abaixo do intervalo de 30 min. |
| RNF-02 | 🟡 Plataforma | 🟡 Linux (Ubuntu 22.04 ou superior), Python 3.11 ou superior | 🟡 VPS do operador, depois da empresa. |
| RNF-03 | 🟡 Recursos | 🟡 < 256 MB de RAM por execução | 🟡 Compatível com a VPS mais barata. |
| RNF-04 | 🟡 Custo | 🟡 = 0 além da VPS | 🟡 Python, Rclone, cron e API de bots do Telegram são gratuitos. |
| RNF-05 | 🟡 Segurança | 🟡 Execução por usuário de serviço sem privilégio de root | 🟡 `.env`, `rclone.conf` e registro com permissão 600. |

---

## 8. Design e Interface

**Componentes afetados:** 🟡 linha de comando `email-nf-onedrive`; crontab do usuário de serviço; arquivo de trava; diretório de logs; bot do Telegram; guia de instalação; `.env.example`.

**Comportamento esperado:**
🟡 A interface do operador é o terminal, o log e o chat do Telegram. Mensagens em português, com a causa e a ação sugerida.

**Estados da UI:**
- 🟡 Estado vazio: execução sem anexos novos; só o resumo no log.
- 🟡 Estado de carregamento: não se aplica (execução em segundo plano pelo cron).
- 🟡 Estado de erro: aviso no Telegram e linhas de nível ERRO no log.
- 🟡 Estado de sucesso: resumo no log e código de saída 0.

---

## 9. Modelo de Dados

**Entidades novas ou modificadas:**

```
EstadoAvisos {                    // persistido junto ao registro de processados
  causa: str                      // chave da falha, ex.: "caixa1:autenticacao"
  primeira_ocorrencia: datetime
  ultimo_aviso: datetime
  ativa: bool                     // false após a recuperação
}

ResumoExecucao {                  // gravado no log, não persistido
  inicio: datetime
  duracao_s: int
  caixas_processadas: int
  extraidos: int
  enviados: int
  falhas: int
  codigo_saida: 0 | 1 | 2
}
```

**Migrações necessárias:** 🟡 Não.

---

## 10. Integrações e Dependências

| Dependência | Tipo | Impacto se indisponível |
|-------------|------|------------------------|
| 🟡 cron da VPS | Obrigatória | 🟡 Sem agendamento, nada roda; a documentação inclui a verificação `crontab -l`. |
| 🟡 API de bots do Telegram (`api.telegram.org`) | Obrigatória para avisos | 🟡 Falhas registradas só no log; nova tentativa de aviso na execução seguinte. |
| 🟡 [`configuracao-caixas.md`](./configuracao-caixas.md), [`coleta-email.md`](./coleta-email.md), [`envio-onedrive.md`](./envio-onedrive.md) | Obrigatória | 🟡 Componentes orquestrados por este. |
| 🟡 VPS Linux (inicialmente do operador, depois contratada pela empresa) | Obrigatória | 🟡 VPS fora do ar: nenhuma execução; a lacuna é coberta pela janela de busca do `coleta-email` quando voltar. |

---

## 11. Edge Cases e Tratamento de Erros

| Cenário | Trigger | Comportamento esperado |
|---------|---------|----------------------|
| 🟡 EC-01: Execução sobreposta | 🟡 Ciclo anterior ainda rodando | 🟡 Saída imediata com código 0 (RF-03). |
| 🟡 EC-02: Trava abandonada | 🟡 Processo morto sem liberar a trava | 🟡 Retomada após 25 min (RF-04). |
| 🟡 EC-03: Telegram fora do ar | 🟡 Timeout ou erro HTTP na API | 🟡 Log "aviso não entregue"; nova tentativa na execução seguinte. |
| 🟡 EC-04: VPS desligada por horas | 🟡 Manutenção ou falta de pagamento | 🟡 Na volta, a janela de busca recupera os e-mails do período; o resumo registra o intervalo desde a última execução. |
| 🟡 EC-05: Falha persistente | 🟡 Mesma causa por mais de 6 h | 🟡 Novo aviso a cada 6 h (RF-08). |
| 🟡 EC-06: Disco cheio | 🟡 Falha ao gravar log ou registro | 🟡 Saída com código 2; tentativa de aviso ao Telegram com a causa "disco cheio". |
| 🟡 EC-07: Exceção não prevista | 🟡 Erro de programação | 🟡 Pilha completa no log, aviso ao Telegram com o tipo do erro, saída com código 2, trava liberada. |

---

## 12. Segurança e Privacidade

- **Autenticação:** 🟡 token do bot do Telegram no `.env`; acesso à VPS por SSH com chave.
- **Autorização:** 🟡 execução por usuário de serviço sem root; arquivos sensíveis com permissão 600.
- **Dados sensíveis:** 🟡 os avisos do Telegram nunca contêm senhas, tokens nem conteúdo de anexos; citam só caixa, causa, nome do arquivo e remetente. O log segue a mesma regra.
- **Auditoria:** 🟡 log com retenção de 30 dias (RF-06) e registro de processados permanente, que guarda só metadados.

---

## 13. Plano de Rollout

- **Estratégia:** 🟡 (1) instalação na VPS do operador; (2) `verificar-config` e `testar-onedrive`; (3) uma semana de `executar --simular` a cada 30 min, comparando o log com a caixa; (4) produção; (5) migração para a VPS da empresa seguindo o guia, como teste da documentação.
- **Como reverter (rollback):** 🟡 comentar a linha do cron; a caixa de e-mail nunca é alterada e os arquivos enviados ficam identificados no registro.
- **Monitoramento pós-deploy:** 🟡 na primeira semana de produção, ler o resumo diário do log e conferir a pasta com a equipe financeira.

---

## 14. Open Questions

| # | Pergunta | Impacto | Dono | Prazo |
|---|---------|---------|------|-------|
| OQ-01 | 🟡 ⚠️ ABERTO: quem recebe os avisos do Telegram depois da entrega à empresa cliente? Até a resposta, só o chat do operador. | Médio | iago | 🟡 na entrega à empresa cliente |
| OQ-02 | 🟡 ⚠️ ABERTO: o cron deve rodar 24 h por dia ou só em horário comercial? Até a resposta, 24 h. | Baixo | iago | 🟡 antes da entrada em operação |
| OQ-03 | 🟡 ⚠️ ABERTO: prazo do MVP não foi fixado pelo usuário. | Baixo | iago | 🟡 a definir |

---

## 15. Decisões Tomadas (Decision Log)

| Decisão | Alternativas consideradas | Racional |
|---------|--------------------------|---------|
| 🟡 cron a cada 30 min | 🟡 De hora em hora; serviço contínuo | 🟡 Escolha do usuário; simples de operar e auditar. |
| 🟡 Aviso por Telegram | 🟡 E-mail via SMTP da própria caixa | 🟡 Escolha do usuário; gratuito e imediato. |
| 🟡 Só falhas e recuperações são notificadas | 🟡 Aviso a cada execução | 🟡 48 mensagens por dia fariam o operador ignorar os avisos. |
| 🟡 Instalação direta, sem Docker | 🟡 Contêiner | 🟡 Menos camadas para quem vai operar depois da entrega. |

---

## Apêndice

### Referências
- 🟡 [`prd.md`](../prd.md), seções 4, 6, 8 e 9.
- 🟡 [`personas.md`](../personas.md), jornada do operador-tecnico.
- 🟡 API de bots do Telegram: https://core.telegram.org/bots/api#sendmessage

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
