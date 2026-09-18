# Interface: API de bots do Telegram, `sendMessage`

> Tipo: HTTP · Direção: saída · Dono no código: `execucao/avisos.py`
> Spec de origem: `_reversa_sdd/sdd/execucao-monitoramento.md` (RF-07 a RF-09)

## Request

```
POST https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/sendMessage
Content-Type: application/x-www-form-urlencoded

chat_id=<TELEGRAM_CHAT_ID>&text=<mensagem>&disable_web_page_preview=true
```

- Sem `parse_mode`: texto puro, para que nomes de arquivo com `_` ou `*` não quebrem a formatação.
- `text` limitado a 4096 caracteres; acima disso, truncado com "… (ver log)".
- A URL, que contém o token, nunca é registrada em log.

## Response

| Resposta | Interpretação |
|----------|---------------|
| HTTP 200 e `{"ok": true, ...}` | Entregue; `ultimo_aviso` atualizado e `entrega_pendente = 0`. |
| HTTP 4xx com `{"ok": false, "description": ...}` | Não entregue; log "aviso não entregue: <description>"; `entrega_pendente = 1`. Um HTTP 401 indica token inválido. |
| HTTP 429 | Não entregue; nova tentativa na execução seguinte. |
| Timeout (15 s) ou erro de rede | Não entregue; nova tentativa na execução seguinte (EM EC-03). |

A falha do aviso nunca altera o código de saída da execução (EM fluxo B).

## Formato das mensagens

Falha:
```
email-nf-onedrive: execução com falha (código 1)
• caixa 1: autenticação recusada. Ação: verifique a senha de app no .env.
• anexo 2026-09-18_cobranca_Boleto Set.pdf: 5 tentativas de envio falharam. Ação: ver log.
```

Recuperação:
```
email-nf-onedrive: recuperado
• caixa 1 voltou a funcionar.
```

Conteúdo permitido: caixa, causa, ação, nome de arquivo e remetente. Proibido: senhas, tokens, conteúdo de anexos e assunto completo (RN-07).

## Idempotência e supressão

Uma mensagem por execução, agregando as causas que devem ser notificadas naquela execução. A supressão de 6 h e o reenvio de pendentes seguem a tabela `avisos` (`data-delta.md` §4).
