# Personas e Jornadas

> Selo 🟡 PLANEJADO em todos os itens.

## Persona 1: analista-financeira
- **Perfil:** 🟡 Integrante da equipe financeira da empresa cliente (e das empresas ligadas a ela) que lança e paga as contas recebidas por e-mail.
- **Contexto:** 🟡 No escritório, em rotina diária, alternando entre a caixa compartilhada do financeiro, o internet banking e o OneDrive; o problema aparece ao montar a lista de pagamentos e na reunião semanal de pagamentos.
- **Nível técnico:** 🟡 intermediário, em rotinas financeiras (e-mail, internet banking, OneDrive, planilhas); iniciante em automação.
- **Dor principal:** 🟡 Quatro pessoas leem a mesma caixa e ninguém assume salvar a NF ou o boleto na pasta `CONTAS A PAGAR`; contas são esquecidas e há erros de lançamento.
- **Objetivo final:** 🟡 Nenhuma conta esquecida: pagar todas em dia, sem multa nem juros, com a documentação de cada pagamento arquivada.

### Jornada principal
1. 🟡 Receber NF ou boleto do fornecedor na caixa do financeiro
2. 🟡 Aguardar a execução automática do script, sem baixar anexo
3. 🟡 Abrir a pasta `CONTAS A PAGAR` no OneDrive
4. 🟡 Encontrar o documento já salvo e nomeado
5. 🟡 Lançar a conta na linha de pagamento
6. 🟡 Conferir a lista na reunião semanal, junto com os boletos DDA
7. 🟡 Pagar ou agendar a conta no banco até o vencimento

---

## Persona 2: operador-tecnico
- **Perfil:** 🟡 Iago, prestador de serviço externo que constrói, configura e entrega a automação.
- **Contexto:** 🟡 Remoto e sob demanda: configura uma vez, agenda a execução e só intervém quando algo falha ou quando um fornecedor foge do padrão.
- **Nível técnico:** 🟡 intermediário, em engenharia de software com foco em IA, em Python e nas ferramentas da Microsoft.
- **Dor principal:** 🟡 Precisa acessar uma caixa de e-mail no Google Workspace, que exige senha de app ou OAuth, e gravar num OneDrive for Business de outra conta, sem saber se o Rclone e o tenant o permitem.
- **Objetivo final:** 🟡 Entregar a ferramenta documentada e passá-la adiante, para que a própria empresa cliente a opere.

### Jornada principal
1. 🟡 Configurar o acesso à caixa de e-mail e o remote do Rclone no OneDrive
2. 🟡 Definir a pasta de e-mail monitorada e as regras de identificação de NF e boleto
3. 🟡 Agendar a execução periódica do script
4. 🟡 Receber o aviso quando uma execução falhar
5. 🟡 Diagnosticar a falha pelo log e corrigi-la
6. 🟡 Documentar a instalação e a operação
7. 🟡 Entregar a ferramenta à equipe da empresa cliente

---
Gerado por reversa-researcher em 2026-09-18T18:59:51Z
Fonte: ideation.md
