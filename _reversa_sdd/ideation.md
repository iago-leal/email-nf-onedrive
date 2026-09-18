# Ideation, email-nf-onedrive

> Selo 🟡 PLANEJADO em todos os itens, sujeito a validação.

## Brief original
Desenvolver um script (ou ferramenta) em Python que extraia as notas fiscais e boletos recebidos no endereço de e-mail cujas credenciais já estão no `.env` (variáveis `EMAIL1` e `SENHA_EMAIL1`) e, após a extração, suba os arquivos ao Google Drive por meio do Rclone. A pasta de e-mail utilizada pela equipe ainda precisa ser identificada.

## Problema
🟡 Fornecedores enviam notas fiscais e boletos às caixas compartilhadas financeiro@<empresa-1>, financeiro@<empresa-2> e administrativo@<empresa-3> (domínios exatos a confirmar). Quatro pessoas leem a mesma caixa e nenhuma assume salvar o documento na pasta de contas a pagar no OneDrive; em consequência, contas são esquecidas e há erros de lançamento. Quem sente é a gestora financeira, na reunião de pagamentos e no vencimento das contas.

## Valor entregue
🟡 Toda NF e todo boleto recebidos por e-mail aparecem sozinhos na pasta `<Empresa> Financeiro/CONTAS A PAGAR` do OneDrive, sem depender de alguém lembrar de salvá-los.

## Alternativas existentes
- 🟡 **Processo manual atual:** quem vê o e-mail primeiro salva o documento no OneDrive. Não basta porque a responsabilidade é difusa: ninguém assume e há esquecimento.
- 🟡 **Concentrar a caixa em uma só pessoa:** sugestão mencionada no áudio de origem. A solicitante a reconhece como alternativa, mas prefere automatizar, porque a automação reduz também erros e esquecimentos, e não apenas a difusão de responsabilidade.

## Público-alvo (bruto)
🟡 A equipe financeira da empresa cliente e das empresas ligadas a ela, que consulta o OneDrive para lançar e pagar contas. O script é operado por iago, não pela equipe.

## Métricas de sucesso
- 🟡 **Cobertura:** percentual de NFs e boletos recebidos por e-mail que chegam ao OneDrive sem ação manual. Alvo: 100%, aferido por amostragem semanal.
- 🟡 **Contas esquecidas:** número de contas pagas em atraso por falta de arquivamento. Alvo: 0 por mês.

## Premissas a validar
- 🟡 **Rclone no OneDrive certo:** é possível configurar o Rclone (backend `onedrive`, tipo *business*) com permissão de escrita na pasta `<Empresa> Financeiro/CONTAS A PAGAR`, que fica no OneDrive pessoal de `<conta-admin>@<dominio>` no tenant `<tenant>`. Riscos: a conta autenticada precisa ter acesso a essa pasta, e o tenant pode exigir consentimento de administrador para o aplicativo do Rclone.
- 🟡 **Acesso à caixa Google Workspace:** o usuário confirmou que a caixa é Google, coerente com o MX de `<dominio>`. O Google Workspace não aceita mais IMAP com a senha comum da conta: `SENHA_EMAIL1` precisa ser uma senha de app (que exige verificação em duas etapas) ou o acesso terá de usar OAuth 2.0. O administrador do Workspace também pode ter desativado o IMAP.

## Notas
- 🟡 Credenciais disponíveis no `.env`: apenas `EMAIL1` e `SENHA_EMAIL1` (uma caixa). As demais caixas citadas no áudio não têm credenciais registradas.
- 🟡 **Requisito confirmado pelo usuário:** o MVP opera com uma única caixa, mas a aplicação deve suportar várias caixas desde o início, de modo que acrescentar uma nova seja questão de configuração (por exemplo, o par `EMAIL2`/`SENHA_EMAIL2` no `.env`), sem alterar o código.
- 🟡 Destino corrigido pelo usuário em 2026-09-18: OneDrive for Business, e não Google Drive, como dizia o brief original. A pasta de e-mail monitorada ainda não foi identificada.
- 🟡 DNS de `<dominio>` (consulta pública, 2026-09-18): MX único `alt3.aspmx.l.google.com`, TXT `MS=ms<id>` (domínio verificado na Microsoft 365), nameservers da Wix. Um único MX secundário do Google é configuração incomum e pode indicar migração incompleta. Arquitetura resultante, confirmada pelo usuário: e-mail no Google Workspace, arquivos no OneDrive for Business (Microsoft 365).
- 🟡 Fora do escopo inicial, mas citado no áudio como desejo futuro: integração com o "Meu Dinheiro" (sistema de gestão financeira, a confirmar), agendamento e provisão de pagamento no banco, e conciliação com boletos DDA vinculados ao CNPJ.
- 🟡 Premissas levantadas e não marcadas como perigosas pelo usuário: NFs e boletos identificáveis como anexos. Segue como hipótese de trabalho.
- 🟡 Fonte primária: transcrição automática (mlx-whisper, sem revisão humana) do áudio de WhatsApp da solicitante (não versionado).

---
Gerado por reversa-ideator em 2026-09-18T18:51:40Z
Fonte: newproject-brief.md
