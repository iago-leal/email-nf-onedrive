# Brief inicial, /reversa-new

> Selo 🟡 PLANEJADO. Documento de entrada do time Code New Project Agents.
> Versão pública anonimizada: nomes de empresas, domínio, tenant e contas foram substituídos por marcadores (`<empresa-1>`, `<dominio>`, `<tenant>`, `<conta-admin>`).

**Data:** 2026-09-18T18:43:05Z
**Usuário:** iago

## Ideia original

Desenvolver um script (ou ferramenta) em Python que extraia as notas fiscais e boletos recebidos no endereço de e-mail cujas credenciais já estão no `.env` (variáveis `EMAIL1` e `SENHA_EMAIL1`) e, após a extração, suba os arquivos ao Google Drive por meio do Rclone. A pasta de e-mail utilizada pela equipe ainda precisa ser identificada.

## Áudio de origem

A demanda chegou num áudio de WhatsApp da responsável pelo financeiro da empresa cliente, transcrito localmente (mlx-whisper, sem revisão humana). A transcrição não é versionada; os pontos relevantes estão resumidos abaixo.

## Pontos extraídos do áudio

- Caixas envolvidas: `financeiro@<empresa-1>`, `financeiro@<empresa-2>` e `administrativo@<empresa-3>`, além dos e-mails individuais da equipe financeira.
- Fornecedores enviam notas fiscais e boletos para essas caixas; quem vê primeiro deveria salvar o documento na pasta de contas a pagar e lançá-lo na linha de pagamento.
- Dor principal: quatro pessoas leem a caixa do financeiro e ninguém assume o arquivamento, o que gera esquecimento de contas e erros.
- Existe conciliação semanal com boletos DDA do banco, vinculados ao CNPJ da empresa.
- Desejo futuro: integração com o "Meu Dinheiro" (sistema de gestão financeira, a confirmar) e com o banco, para agendamento e provisão de pagamento.
- Alternativa descartada pela solicitante: concentrar o acesso à caixa em uma única pessoa.

## Correções do usuário (2026-09-18)

- **Destino não é o Google Drive, e sim o OneDrive for Business** (Microsoft 365, tenant `<tenant>`). Pasta de destino: `<Empresa> Financeiro/CONTAS A PAGAR`, no OneDrive pessoal de `<conta-admin>@<dominio>`. O usuário não sabe se o Rclone acessa o OneDrive.
- ~~Segundo o usuário, a caixa de e-mail não é Gmail.~~ **Corrigido pelo usuário: a caixa de entrada é Google (Google Workspace).** Interpretação: a afirmação anterior provavelmente se referia ao destino dos arquivos, que é o OneDrive.
- **Divergência resolvida:** o domínio de `EMAIL1` é `<dominio>` (lido com autorização, apenas o domínio). O DNS público mostra MX único em `alt3.aspmx.l.google.com` (servidor do Google Workspace), registro `MS=ms<id>` de verificação do domínio na Microsoft 365 e DNS hospedado na Wix. Pelo MX, a correspondência externa chega a servidores do Google, o que o usuário confirmou.
- **Várias caixas:** hoje há apenas um e-mail e uma senha no `.env` (`EMAIL1`, `SENHA_EMAIL1`), mas a aplicação deve estar preparada para receber outras caixas depois.

---
Gerado por /reversa-new em 2026-09-18T18:43:05Z
