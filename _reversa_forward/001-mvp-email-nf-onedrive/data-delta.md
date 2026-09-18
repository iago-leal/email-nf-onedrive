# Data delta: MVP de arquivamento automático de NFs e boletos

> Identificador: `001-mvp-email-nf-onedrive`
> Data: `2026-09-18`
> Modelo de referência: `_reversa_sdd/sdd/coleta-email.md#9. Modelo de Dados`, `_reversa_sdd/sdd/envio-onedrive.md#9. Modelo de Dados`, `_reversa_sdd/sdd/execucao-monitoramento.md#9. Modelo de Dados`, `_reversa_sdd/sdd/configuracao-caixas.md#9. Modelo de Dados`

## 1. Visão geral

Não há banco anterior. O arquivo `var/registro.sqlite3` nasce na primeira execução, com o esquema abaixo, e implementa as entidades `AnexoProcessado` e `EstadoAvisos` das specs. As entidades `Caixa` e `Configuracao` existem só em memória (lidas do `.env` a cada execução) e `ResumoExecucao` vai só para o log, como previsto nas specs.

## 2. Tabela `anexos` (entidade `AnexoProcessado`)

| Campo | Tipo | Origem | Delta sobre a spec |
|-------|------|--------|--------------------|
| `id` | INTEGER PK | novo | Chave técnica. |
| `caixa_endereco` | TEXT NOT NULL | CE §9 | **Passa a integrar a chave única**, em minúsculas (D-09). |
| `caixa_indice` | INTEGER NOT NULL | CE §9 | Mantido só como informação; deixa a chave. |
| `message_id` | TEXT NOT NULL | CE §9 | Sem alteração; hash substituto no fluxo alternativo B. |
| `sha256` | TEXT NOT NULL | CE §9 | Sem alteração. |
| `nome_original` | TEXT NOT NULL | CE §9 | Sem alteração. |
| `remetente` | TEXT NOT NULL | CE §9 | Sem alteração. |
| `assunto` | TEXT NOT NULL | CE §9 | Sem alteração. |
| `data_mensagem` | TEXT NOT NULL (ISO 8601, UTC) | CE §9 | Sem alteração. |
| `classe` | TEXT NOT NULL, `CHECK IN ('nfe-xml','palavra-chave','sem-classificacao')` | CE §9 | Sem alteração. |
| `estado` | TEXT NOT NULL, `CHECK IN ('extraido','enviado','falha-envio','retido')` | CE §9 | **Novo valor `retido`** (RN-03, D-08). |
| `caminho_destino` | TEXT NULL | EO §9 | Sem alteração. |
| `tentativas_envio` | INTEGER NOT NULL DEFAULT 0 | EO §9 | Sem alteração. |
| `ultimo_erro` | TEXT NULL | EO §9 | Sem alteração; nunca contém credenciais (D-04). |
| `criado_em` | TEXT NOT NULL | novo | Auditoria. |
| `atualizado_em` | TEXT NOT NULL | CE §9 | Sem alteração. |

Restrições e índices:
- `UNIQUE (caixa_endereco, message_id, sha256)`
- `INDEX (caixa_endereco, estado, data_mensagem)`, para a janela de busca (CE RF-03)

### Máquina de estados

```
          (coleta)                  (envio)
 novo ──► extraido ──────────────► enviado        [terminal]
   │         │  ▲                      ▲
   │         ▼  │ (coleta reextrai)    │ (envio)
   │      falha-envio ─────────────────┘
   │
   └────► retido                                   [terminal]
          (coleta, classe sem-classificacao)
```

| Transição | Dono | Condição |
|-----------|------|----------|
| novo → `extraido` | `coleta` | Anexo PDF/XML de classe `nfe-xml` ou `palavra-chave`, fora do registro. |
| novo → `retido` | `coleta` | Anexo de classe `sem-classificacao`; gera a linha de log única "retido para revisão". |
| `extraido` → `enviado` | `envio` | Confirmação por tamanho no destino, ou arquivo idêntico já existente (EO RF-05, RF-06). |
| `extraido` → `falha-envio` | `envio` | Erro do Rclone, tempo esgotado ou tamanho divergente; incrementa `tentativas_envio`. |
| `falha-envio` → `enviado` | `envio` | Nova tentativa bem-sucedida numa execução posterior. |
| `falha-envio` → `falha-envio` | `envio` | Nova falha; na 5ª tentativa, gera o aviso `anexo:<sha256>:tentativas` (EO EC-07). |

Estados terminais nunca voltam atrás. Em `--simular`, nenhuma transição persiste (D-17).

### Janela de busca (CE RF-03), sobre esta tabela

Para cada caixa:
- sem nenhuma linha: `DATA_INICIAL`;
- com linhas: `min(max(data_mensagem) − 2 dias, min(data_mensagem) entre as linhas com estado em ('extraido','falha-envio'))`.

## 3. Tabela `ocorrencias` (nova, sem entidade nas specs)

Registra mensagens já anunciadas no log, para que a sobreposição de 2 dias da janela não repita a mesma linha a cada 30 min.

| Campo | Tipo | Observação |
|-------|------|------------|
| `caixa_endereco` | TEXT NOT NULL | |
| `message_id` | TEXT NOT NULL | |
| `tipo` | TEXT NOT NULL, `CHECK IN ('sem-anexo','compactado')` | CE RF-09 e EC-08. |
| `registrado_em` | TEXT NOT NULL | |

`PRIMARY KEY (caixa_endereco, message_id, tipo)`. Guarda só identificadores; remetente e assunto aparecem apenas no log, que expira em 30 dias (RN-07).

## 4. Tabela `avisos` (entidade `EstadoAvisos`)

| Campo | Tipo | Delta sobre a spec |
|-------|------|--------------------|
| `causa` | TEXT PK | Sem alteração. Exemplos: `config:SENHA_EMAIL2`, `caixa1:autenticacao`, `caixa1:pasta`, `caixa1:conexao`, `onedrive:token`, `onedrive:acesso`, `onedrive:destino`, `anexo:<sha256>:tentativas`, `execucao:excecao`, `execucao:disco`. |
| `primeira_ocorrencia` | TEXT NOT NULL | Sem alteração. |
| `ultimo_aviso` | TEXT NULL | Passa a aceitar nulo: falha registrada cujo aviso ainda não foi entregue. |
| `ativa` | INTEGER NOT NULL (0/1) | Sem alteração. |
| `mensagem` | TEXT NOT NULL | **Novo:** último texto de causa e ação sugerida, sem segredos, para reenviar o aviso pendente (EM fluxo B). |
| `entrega_pendente` | INTEGER NOT NULL (0/1) | **Novo:** 1 quando o Telegram falhou; a execução seguinte tenta de novo. |

Regra de envio (EM RF-08): notificar se `ultimo_aviso` é nulo ou tem mais de 6 h. Recuperação (EM RF-09): numa execução com código 0, toda causa `ativa = 1` gera uma única mensagem de recuperação e passa a `ativa = 0`.

## 5. Tabela `meta` (nova)

| Chave | Valor |
|-------|-------|
| `versao_esquema` | `1` |
| `ultima_execucao_em` | ISO 8601 do início da última execução não simulada; permite ao resumo registrar o intervalo desde a execução anterior (EM EC-04). |

## 6. Migrações

- **Criação:** `registro/esquema.sql`, aplicado com `CREATE TABLE IF NOT EXISTS` quando `versao_esquema` estiver ausente.
- **Evolução futura:** migrações numeradas conforme `versao_esquema`; nenhuma nesta feature.
- **Corrupção** (CE EC-09): se o SQLite não abrir ou `PRAGMA integrity_check` falhar, a execução aborta com código 2 antes de qualquer envio e avisa o operador. O banco nunca é recriado automaticamente, pois isso causaria reenvio de tudo desde `DATA_INICIAL`.

## 7. Retenção (RN-07)

- `anexos`, `ocorrencias`, `avisos` e `meta`: permanentes (resposta 3a).
- Log: 30 dias (resposta 2a), fora do banco.
- Conteúdo de anexos: nunca no banco; na pasta de trabalho, só durante a execução (D-13).
