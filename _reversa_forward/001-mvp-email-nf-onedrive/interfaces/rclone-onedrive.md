# Interface: Rclone e OneDrive for Business

> Tipo: processo externo (CLI `rclone`) · Direção: saída · Dono no código: `envio/rclone.py`
> Spec de origem: `_reversa_sdd/sdd/envio-onedrive.md`

## Invocação

- Executável: `rclone` do `PATH` (ou `RCLONE_BIN`, se definido), via `subprocess.run` com lista de argumentos, sem shell.
- Ambiente: herdado, sem as variáveis do `.env` (D-03); o `rclone.conf` é o do usuário de serviço, ou o apontado por `RCLONE_CONFIG`.
- Timeout: 120 s por chamada (EO RNF-03); estouro vira `falha-envio`.
- Flags comuns: `--retries 3 --low-level-retries 10 --immutable`.

## Subcomandos permitidos (lista branca)

| Subcomando | Uso | Argumentos | Saída esperada |
|------------|-----|------------|----------------|
| `lsjson --stat --hash` | Existência, tamanho e QuickXorHash de um caminho exato | `<remote>:<destino>/<nome>` | JSON de um objeto; código 3 ou mensagem "not found" quando ausente |
| `hashsum quickxor` | Hash local para comparação | `<arquivo local>` | `<hash>  <nome>` |
| `copyto` | Upload para nome exato | `<local> <remote>:<destino>/<nome>` | código 0 |
| `lsf --max-depth 1` | Verificar que a pasta de destino existe (EO EC-06) e o levantamento da L-03 | `<remote>:<destino>` | lista de nomes |
| `deletefile` | **Somente** o arquivo de teste do `testar-onedrive` | caminho que termina em `.email-nf-onedrive-teste-<uuid>.txt` | código 0 |

Qualquer outro subcomando (`sync`, `delete`, `purge`, `move`, `moveto`, `rmdir`, `copy` de diretório etc.) faz a fachada levantar erro antes de executar (RN-02).

## Protocolo de envio de um arquivo

1. `lsf` do destino; se a pasta não existir, `falha-envio` com "destino não encontrado: <caminho>" (não cria a pasta).
2. Para o nome candidato `N`: `lsjson --stat --hash` em `N`.
   - ausente: segue para o passo 3 com `N`;
   - mesmo tamanho e mesmo QuickXorHash: `enviado` sem upload (EO RF-05);
   - diferente: tenta `N_2`, `N_3`, … até 99; acima disso, `falha-envio`.
3. `copyto` para o nome escolhido.
4. `lsjson --stat` e comparação de tamanho; igual → `enviado` com `caminho_destino`; diferente → `falha-envio` "tamanho divergente".

## Mapeamento de erros

| Sinal no `stderr` ou código | Interpretação | Causa de aviso |
|-----------------------------|---------------|----------------|
| `invalid_grant`, `token expired`, `couldn't fetch token` | Token revogado ou vencido (EO EC-01) | `onedrive:token`, com instrução de reautorizar |
| `accessDenied`, HTTP 403 | Sem permissão na pasta (EO EC-02) | `onedrive:acesso` |
| `activityLimitReached`, HTTP 429 persistente | Limite de requisições (EO EC-05) | nenhuma de imediato; `falha-envio` |
| `is immutable` | Arquivo remoto mudou entre a checagem e o upload | nenhuma; `falha-envio`, nova tentativa na próxima execução |
| `didn't find section in config file` | `RCLONE_REMOTE` inexistente | `config:RCLONE_REMOTE`, código 2 |
| timeout do `subprocess` | Chamada travada | `falha-envio` |

`ultimo_erro` guarda até 500 caracteres do `stderr`, após o filtro de segredos.

## Idempotência

O protocolo acima é idempotente: repetir o envio de um anexo já presente leva ao passo 2, ramo "mesmo tamanho e hash", sem novo upload.
