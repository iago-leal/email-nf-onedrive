# PRD: email-nf-onedrive

> Selo 🟡 PLANEJADO. Documento gerado a partir de ideation + personas.

**Versão:** 1.0
**Data:** 2026-09-18T19:03:34Z
**Autor:** reversa-drafter
**Status:** rascunho

---

## 1. Problema

🟡 Fornecedores enviam notas fiscais e boletos às caixas compartilhadas da equipe financeira (hoje `financeiro@<empresa-1>`; no futuro também `financeiro@<empresa-2>` e `administrativo@<empresa-3>`). Quatro pessoas leem a mesma caixa e nenhuma assume salvar o documento na pasta `<Empresa> Financeiro/CONTAS A PAGAR` do OneDrive. Como a responsabilidade é difusa, contas são esquecidas e há erros de lançamento, com risco de multa e juros por atraso.

### Quem sente
- 🟡 **Equipe financeira**, ao montar a lista de pagamentos no dia a dia e na reunião semanal de pagamentos, quando falta a NF ou o boleto na pasta.
- 🟡 **Gestora financeira**, no vencimento das contas, quando descobre um pagamento esquecido.
- 🟡 **Operador técnico**, que precisa construir a automação sobre dois ecossistemas distintos: e-mail no Google Workspace e arquivos no OneDrive for Business (Microsoft 365).

---

## 2. Personas-alvo

🟡 Referência completa em [`personas.md`](./personas.md). Resumo:

- **analista-financeira**: 🟡 integrante da equipe financeira que lança e paga as contas; intermediária em rotinas financeiras e iniciante em automação. Dor: ninguém assume arquivar NFs e boletos, e contas são esquecidas.
- **operador-tecnico**: 🟡 iago, prestador externo, intermediário em Python e ferramentas Microsoft. Dor: integrar uma caixa Google Workspace (senha de app ou OAuth) a um OneDrive for Business de outra conta. Objetivo: entregar a ferramenta documentada e passá-la à empresa cliente.

---

## 3. Métricas de sucesso

🟡 Métricas herdadas do `ideation.md`, com unidade, alvo e prazo explicitados.

| Métrica | Unidade | Alvo | Prazo |
|---|---|---|---|
| 🟡 Cobertura de arquivamento automático | % de NFs e boletos recebidos por e-mail que chegam ao OneDrive sem ação manual, aferido por amostragem semanal | 🟡 100% | 🟡 3 meses após a entrada em operação |
| 🟡 Contas esquecidas | Nº de contas pagas em atraso por falta de arquivamento | 🟡 0 por mês | 🟡 3 meses após a entrada em operação |

---

## 4. Escopo (in)

🟡 Derivado de ideation, personas e jornadas.

- 🟡 **Leitura de caixas Google Workspace** pelo protocolo IMAP, autenticada com as credenciais do `.env` (`EMAIL1`, `SENHA_EMAIL1`).
- 🟡 **Suporte a várias caixas por configuração:** o MVP opera com uma caixa, mas acrescentar outra (por exemplo `EMAIL2`/`SENHA_EMAIL2`) não exige alterar o código.
- 🟡 **Pasta de e-mail monitorada configurável** por caixa (a pasta concreta ainda será identificada).
- 🟡 **Identificação de NFs e boletos** entre as mensagens recebidas, a partir dos anexos.
- 🟡 **Download dos anexos** relevantes, sem duplicar documentos já processados em execuções anteriores.
- 🟡 **Nomeação padronizada** dos arquivos, para que a analista encontre o documento já salvo e nomeado.
- 🟡 **Envio ao OneDrive for Business via Rclone**, na pasta `<Empresa> Financeiro/CONTAS A PAGAR` do OneDrive de `<conta-admin>@<dominio>` (tenant `<tenant>`).
- 🟡 **Execução agendada e sem interface** numa VPS Linux: inicialmente a do operador, depois uma contratada pela empresa.
- 🟡 **Registro em log** de cada execução e **aviso ao operador** quando uma execução falhar.
- 🟡 **Documentação de instalação e operação**, para a entrega da ferramenta à empresa cliente.

---

## 5. Não-objetivos (out)

- 🟡 Integração com o "Meu Dinheiro" (sistema de gestão financeira, a confirmar). Citada no áudio como desejo futuro.
- 🟡 Agendamento de pagamento ou lançamento de provisão no banco.
- 🟡 Conciliação com boletos DDA vinculados ao CNPJ.
- 🟡 Extração de dados das notas (valor, vencimento, fornecedor) para planilha ou relatório: o usuário escolheu como valor entregue apenas o arquivamento automático, e não a lista a pagar.
- 🟡 Interface gráfica para a equipe financeira: a interação dela se dá pela pasta do OneDrive.
- 🟡 Alteração do estado das mensagens na caixa (mover, apagar, marcar como lida): [INDEFINIDO, validar com usuário]. Até decisão contrária, o script apenas lê.

---

## 6. Restrições

| Tipo | Descrição |
|---|---|
| 🟡 Técnica | 🟡 Python para os scripts; Rclone (backend `onedrive`, tipo *business*) para o envio; execução sem interface numa VPS Linux. Como a VPS não tem navegador, a autorização OAuth do Rclone precisa ser feita em outra máquina (`rclone authorize`) e o token copiado para a VPS. |
| 🟡 Técnica | 🟡 Google Workspace não aceita IMAP com a senha comum da conta: `SENHA_EMAIL1` precisa ser senha de app (com verificação em duas etapas ativa) ou o acesso terá de usar OAuth 2.0. |
| 🟡 Técnica | 🟡 Credenciais apenas no `.env`, fora do versionamento (já listado no `.gitignore`). |
| 🟡 Prazo | 🟡 [INDEFINIDO, validar com usuário]: o usuário não fixou prazo. |
| 🟡 Compliance | 🟡 NFs e boletos contêm dados de fornecedores, inclusive CPF quando o fornecedor é pessoa física, o que sujeita o tratamento à LGPD. Política de retenção de arquivos na VPS e nos logs: [INDEFINIDO, validar com usuário]. |
| 🟡 Orçamento | 🟡 Sem custo recorrente além da VPS: apenas ferramentas e APIs gratuitas. A VPS definitiva será contratada pela empresa. |

---

## 7. Dependências externas

- 🟡 **Google Workspace (Gmail)** da caixa `EMAIL1`, domínio `<dominio>`, com IMAP habilitado pelo administrador do Workspace.
- 🟡 **Microsoft 365 / OneDrive for Business**, tenant `<tenant>`, pasta `<Empresa> Financeiro/CONTAS A PAGAR`.
- 🟡 **Rclone** (v1.74 disponível na máquina do operador) e sua autorização OAuth no tenant Microsoft.
- 🟡 **VPS Linux**, inicialmente a do operador e depois uma contratada pela empresa.
- 🟡 **Canal de aviso de falha** ao operador: [INDEFINIDO, validar com usuário].

---

## 8. Riscos

| Risco | Impacto | Probabilidade | Mitigação proposta |
|---|---|---|---|
| 🟡 O Rclone não consegue gravar na pasta `CONTAS A PAGAR`, porque a conta autenticada não tem acesso ou porque o tenant bloqueia o aplicativo do Rclone sem consentimento de administrador | 🟡 Alto | 🟡 Média | 🟡 Validar antes de qualquer código: autenticar como `<conta-admin>@<dominio>` (ou conta com acesso de edição) e fazer um upload de teste; se o tenant bloquear, pedir consentimento ao administrador ou registrar aplicativo próprio no Entra ID. |
| 🟡 `SENHA_EMAIL1` é a senha comum da conta, e o IMAP a recusa | 🟡 Alto | 🟡 Média | 🟡 Testar o login IMAP logo no início; se falhar, gerar senha de app (exige verificação em duas etapas) ou migrar para OAuth 2.0. |
| 🟡 IMAP desativado pelo administrador do Google Workspace | 🟡 Alto | 🟡 Baixa | 🟡 Confirmar no console de administração; alternativa é a Gmail API com OAuth. |
| 🟡 NFs ou boletos chegam como link para portal, e não como anexo | 🟡 Médio | 🟡 Média | 🟡 Registrar em log as mensagens sem anexo reconhecido, para revisão manual; tratamento de links fica fora do MVP. |
| 🟡 Documento duplicado ou reprocessado a cada execução | 🟡 Médio | 🟡 Média | 🟡 Controle de mensagens já processadas por identificador da mensagem e verificação de existência no destino. |
| 🟡 Falha silenciosa na VPS (token expirado, senha trocada), que recria o esquecimento de contas | 🟡 Alto | 🟡 Média | 🟡 Aviso de falha ao operador e log legível; a documentação de operação cobre a renovação de credenciais. |
| 🟡 Credenciais expostas na VPS | 🟡 Alto | 🟡 Baixa | 🟡 `.env` com permissão restrita ao usuário do serviço e fora do versionamento. |

---

## 9. Critérios de aceite (alto nível)

- 🟡 **Dado** que um fornecedor enviou NF ou boleto em anexo à caixa monitorada, **Quando** o script executa no horário agendado, **Então** o arquivo aparece, com nome padronizado, na pasta `<Empresa> Financeiro/CONTAS A PAGAR` do OneDrive, sem ação manual da analista financeira.
- 🟡 **Dado** que o script já processou uma mensagem, **Quando** executa novamente, **Então** não cria cópia duplicada do documento.
- 🟡 **Dado** que o operador acrescentou o par `EMAIL2`/`SENHA_EMAIL2` ao `.env`, **Quando** o script executa, **Então** a nova caixa passa a ser processada sem alteração de código.
- 🟡 **Dado** que uma execução falhou (credencial inválida, OneDrive inacessível), **Quando** a falha ocorre, **Então** o operador recebe aviso e o log indica a causa.
- 🟡 **Dado** que a ferramenta foi entregue à empresa cliente, **Quando** alguém da empresa segue a documentação, **Então** consegue instalá-la numa VPS nova e renovar as credenciais sem apoio do operador.

---

## Pendências de cobertura

- 🟡 Pasta de e-mail monitorada na caixa `EMAIL1`.
- 🟡 Frequência de execução do agendamento.
- 🟡 Convenção de nomes dos arquivos no OneDrive (e se haverá subpastas por mês ou por empresa).
- 🟡 Canal de aviso de falha ao operador (e-mail, Telegram, WhatsApp etc.).
- 🟡 Se o script deve alterar o estado das mensagens (marcar como lida, aplicar marcador) ou apenas ler.
- 🟡 Política de retenção dos arquivos baixados e dos logs na VPS (LGPD).
- 🟡 Prazo do MVP.
- 🟡 Tipo de `SENHA_EMAIL1` (senha de app ou senha comum) e conta a usar na autorização do Rclone.

---

Gerado por reversa-drafter em 2026-09-18T19:03:34Z
Fontes: ideation.md, personas.md
