"""Storyteller: glossario.html, deck.html, features/*.html."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from rvlib import *  # noqa: F401,F403
import re

mods = load("modules.json")
metrics = load("metrics.json")
timeline = load("timeline.json")
COLORS = {a["area"]: a["color"] for a in metrics["area_summary"]}


def slug(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


# ================================================================ GLOSSÁRIO
CATS = ["Documentos fiscais", "E-mail", "Acesso às caixas", "OneDrive", "Operação"]
G = [
    # Documentos fiscais
    ("NF-e", "Documentos fiscais", "Nota fiscal eletrônica de venda de mercadorias. Existe oficialmente como um arquivo XML assinado; o PDF que costuma acompanhá-la é o DANFE.", ["XML da NF-e", "DANFE"]),
    ("XML da NF-e", "Documentos fiscais", "O arquivo oficial da nota eletrônica. O sistema o reconhece com segurança pela estrutura, mesmo que o arquivo se chame apenas arquivo.xml, e dele lê o número da nota, o emitente e, quando há, o vencimento das duplicatas.", ["NF-e", "Emitente"]),
    ("DANFE", "Documentos fiscais", "Versão impressa (PDF) da NF-e. Quando chega junto do XML na mesma mensagem, recebe o mesmo fornecedor e o mesmo vencimento, para que os dois fiquem lado a lado na pasta.", ["NF-e"]),
    ("NFS-e", "Documentos fiscais", "Nota fiscal de serviço, emitida pelas prefeituras. Muitas não trazem data de vencimento, por isso formam o maior grupo de documentos que ficam na raiz do destino.", ["Raiz do destino"]),
    ("Boleto", "Documentos fiscais", "Documento de cobrança bancária. O sistema lê o vencimento diretamente da linha digitável, sem depender do texto ao redor.", ["Linha digitável"]),
    ("Linha digitável", "Documentos fiscais", "A sequência de números do boleto. Nela está codificado o fator de vencimento, que o sistema converte em data; os dígitos verificadores confirmam que a leitura está correta.", ["Boleto", "Vencimento"]),
    ("Duplicata", "Documentos fiscais", "Parcela de pagamento prevista na nota. No XML da NF-e, a primeira duplicata indica o vencimento usado para escolher a pasta.", ["Vencimento"]),
    ("Emitente", "Documentos fiscais", "Quem emitiu a nota. É a fonte preferida para o nome do fornecedor no arquivo.", ["Fornecedor"]),
    ("Fornecedor", "Documentos fiscais", "Parte do nome do arquivo. Vem, nesta ordem, do emitente do XML, do remetente original de um encaminhamento ou do remetente externo da mensagem. Sem nenhuma fonte, o arquivo recebe A IDENTIFICAR.", ["Emitente", "A IDENTIFICAR", "Domínio interno"]),
    ("Vencimento", "Documentos fiscais", "Data em que a conta deve ser paga. Define a subpasta do OneDrive. É procurado no XML, na linha digitável, em outro anexo da mesma mensagem e, por fim, no texto do PDF, logo após a palavra vencimento.", ["Grade por vencimento", "Linha digitável"]),
    # E-mail
    ("Caixa", "E-mail", "Uma conta de e-mail acompanhada pelo sistema, como a do financeiro de cada empresa. Cada caixa é declarada na configuração com um número.", ["Configuração (.env)"]),
    ("IMAP", "E-mail", "O protocolo padrão de leitura de e-mails usado para acessar as caixas do Google Workspace, sempre por conexão criptografada.", ["Somente leitura"]),
    ("Somente leitura", "E-mail", "Garantia central do sistema: a pasta de e-mail é aberta de um modo que não altera nada. Nenhuma mensagem é marcada como lida, movida, apagada ou respondida; a equipe vê a caixa exatamente como antes.", ["IMAP"]),
    ("Pasta monitorada", "E-mail", "A pasta de cada caixa que o sistema lê. Por padrão, a caixa de entrada.", ["Caixa"]),
    ("Janela de busca", "E-mail", "O período de mensagens examinado a cada execução: desde a data inicial, na primeira vez; depois, desde dois dias antes da última mensagem registrada, ou desde o documento pendente mais antigo. A sobreposição evita perder e-mails com data atrasada.", ["Registro de processados"]),
    ("Anexo", "E-mail", "Arquivo que acompanha a mensagem. O sistema considera apenas PDF e XML, inclusive os que estão dentro de mensagens encaminhadas.", ["Classificação"]),
    ("Mensagem encaminhada", "E-mail", "Quando um colega repassa à caixa a nota que recebeu. O sistema procura o remetente original no encaminhamento para não usar o nome da própria empresa como fornecedor.", ["Fornecedor", "Domínio interno"]),
    ("Domínio interno", "E-mail", "O endereço de e-mail das próprias empresas do grupo, deduzido das caixas configuradas. Um remetente desses domínios nunca é tratado como fornecedor.", ["Fornecedor"]),
    ("Classificação", "E-mail", "Decisão sobre cada anexo: NF-e em XML, documento com palavra-chave (nota fiscal, boleto, fatura, duplicata e afins) ou sem classificação. Só os dois primeiros seguem para o OneDrive.", ["Palavra-chave", "Documento retido"]),
    ("Palavra-chave", "E-mail", "Termos como nf, nota fiscal, danfe, boleto, fatura, cobrança e duplicata, procurados no assunto e no nome do arquivo, sem diferenciar maiúsculas nem acentos.", ["Classificação"]),
    ("Documento retido", "E-mail", "Anexo que não foi reconhecido como nota ou boleto, como propostas e contratos. Não vai para o OneDrive e fica registrado para revisão humana.", ["Classificação"]),
    ("Documento sem anexo", "E-mail", "Mensagem com cara de nota ou boleto, mas sem PDF ou XML, como os avisos de NFS-e com link para portal. O sistema não segue links; registra a mensagem no log para conferência manual.", ["Log"]),
    # Acesso
    ("Senha de app", "Acesso às caixas", "Senha específica que o Google gera para um aplicativo acessar a caixa. Exige verificação em duas etapas ativa na conta.", ["OAuth 2.0"]),
    ("OAuth 2.0", "Acesso às caixas", "Forma de autorizar o acesso sem guardar a senha da conta: o titular aprova uma vez no navegador, e o sistema recebe uma autorização própria, que pode ser revogada a qualquer momento.", ["Autorização da caixa", "Credencial temporária"]),
    ("Autorização da caixa", "Acesso às caixas", "Arquivo protegido gerado pelo comando autorizar-caixa, um por caixa em modo OAuth. É o único segredo novo que fica guardado no servidor.", ["OAuth 2.0"]),
    ("Credencial temporária", "Acesso às caixas", "Chave de curta duração obtida a partir da autorização a cada execução. Existe só na memória e nunca é gravada.", ["OAuth 2.0"]),
    ("Mascaramento", "Acesso às caixas", "Senhas, tokens e autorizações aparecem como asteriscos no log, nos avisos e na tela. Nenhum segredo é exibido.", ["Log"]),
    # OneDrive
    ("OneDrive for Business", "OneDrive", "O armazenamento de arquivos do Microsoft 365 onde fica a pasta de contas a pagar de cada empresa, e onde a equipe financeira trabalha.", ["CONTAS A PAGAR"]),
    ("CONTAS A PAGAR", "OneDrive", "A pasta de trabalho do financeiro no OneDrive. É o destino dos documentos; o sistema nunca a cria, renomeia ou reorganiza.", ["Destino", "Grade por vencimento"]),
    ("Destino", "OneDrive", "A pasta do OneDrive que recebe os documentos de uma caixa. Cada empresa pode ter o seu destino.", ["CONTAS A PAGAR"]),
    ("Grade por vencimento", "OneDrive", "A organização que o financeiro já usava: uma pasta para cada dia do mês (DIA 1 a DIA 31) e, dentro dela, uma por mês. O documento vai para a combinação do seu vencimento.", ["Vencimento", "Raiz do destino"]),
    ("Raiz do destino", "OneDrive", "O nível principal da pasta de destino. Recebe os documentos cujo vencimento não pôde ser identificado.", ["Planilha LEIAME"]),
    ("Planilha LEIAME", "OneDrive", "Planilha 00 - LEIAME - DOCUMENTOS SEM VENCIMENTO, no topo da raiz. Lista cada documento que ficou ali e explica o motivo em linguagem de financeiro, como nota de serviço, DANFE sem vencimento ou documento já vencido. É refeita automaticamente.", ["Raiz do destino"]),
    ("Convenção de nomes", "OneDrive", "O padrão de nome que a pasta já usava: EMPRESA - FORNECEDOR NF número - BOLETO ou REF. O número da nota só aparece quando é conhecido.", ["Fornecedor"]),
    ("A IDENTIFICAR", "OneDrive", "Texto que ocupa o lugar do fornecedor quando nenhuma fonte o revela. Sinaliza que o documento merece conferência.", ["Fornecedor"]),
    ("Sufixo _2", "OneDrive", "Quando já existe na pasta um arquivo com o mesmo nome e conteúdo diferente, o novo recebe _2, _3 e assim por diante. Nada é substituído.", ["Conferência de integridade"]),
    ("Conferência de integridade", "OneDrive", "Depois de cada envio, o sistema compara o tamanho e a assinatura digital (hash) do arquivo no OneDrive com a do original. Só então o documento conta como entregue.", ["Registro de processados"]),
    ("Rclone", "OneDrive", "Ferramenta gratuita e consolidada que faz a transferência dos arquivos para o OneDrive. O sistema só lhe permite um conjunto fechado de operações, nenhuma delas capaz de apagar documentos.", ["OneDrive for Business"]),
    # Operação
    ("VPS", "Operação", "O servidor na nuvem onde o sistema roda, sem tela nem intervenção humana.", ["Agendamento"]),
    ("Agendamento", "Operação", "O sistema é disparado automaticamente a cada 30 minutos, nos minutos 0 e 30 de cada hora.", ["Execução"]),
    ("Execução", "Operação", "Uma rodada completa: ler a configuração, coletar os e-mails de todas as caixas, enviar os documentos, gravar o resumo e avisar se algo falhou.", ["Resumo da execução", "Trava"]),
    ("Trava", "Operação", "Impede que duas execuções rodem ao mesmo tempo. Se a anterior ainda não terminou, a nova sai imediatamente.", ["Limite de duração"]),
    ("Limite de duração", "Operação", "Nenhuma execução passa de 20 minutos. O que não coube fica para a próxima, sem perda nem duplicação.", ["Trava"]),
    ("Registro de processados", "Operação", "Banco de dados local que lembra cada anexo já tratado e em que estado ele está. É o que impede enviar o mesmo documento duas vezes. Guarda só dados sobre os arquivos, nunca o conteúdo.", ["Conferência de integridade"]),
    ("Envio em paralelo", "Operação", "Até quatro documentos seguem para o OneDrive ao mesmo tempo, com estimativa de reduzir a cerca de um quarto o tempo de envio de um lote grande.", ["Execução"]),
    ("Log", "Operação", "Diário de bordo em arquivo, uma linha por acontecimento, com um arquivo por dia e retenção de 30 dias.", ["Resumo da execução"]),
    ("Resumo da execução", "Operação", "Linha final de cada execução com caixas processadas, documentos extraídos, enviados, retidos, falhas e duração.", ["Log"]),
    ("Aviso no Telegram", "Operação", "Mensagem ao operador quando uma execução falha, com a causa e a ação sugerida. Uma falha que persiste é lembrada no máximo a cada 6 horas, e a volta ao normal também é avisada.", ["Operador"]),
    ("Simulação", "Operação", "Modo de teste que coleta e classifica sem enviar nada, sem alterar o registro e sem avisar. Mostra o que seria feito.", ["Execução"]),
    ("Configuração (.env)", "Operação", "Arquivo do servidor com as caixas, os destinos, o nome de cada empresa e as credenciais. Acrescentar uma caixa é acrescentar linhas nele, sem mexer no programa.", ["Caixa"]),
    ("Operador", "Operação", "A pessoa técnica responsável pela ferramenta: instala, recebe os avisos e renova credenciais. Todo o procedimento está no guia de instalação e operação.", ["Aviso no Telegram"]),
]
concepts = [{"term": t, "slug": slug(t), "category": c, "definition": d, "related": [slug(r) for r in rel]}
            for t, c, d, rel in G]
known = {c["slug"] for c in concepts}
for c in concepts:
    assert all(r in known for r in c["related"]), (c["term"], c["related"])
dump("soul.json", {"schemaVersion": 1, "generatedAt": now_iso(),
                   "source": "_reversa_sdd/prd.md + _reversa_sdd/sdd/*.md + addenda (soul.md ausente)",
                   "sections": {"Propósito": "Arquivar no OneDrive, sem ação manual, as notas fiscais e os boletos que chegam por e-mail às caixas do financeiro."},
                   "categories": CATS, "concepts": concepts})

chips = '<button type="button" data-cat="" aria-pressed="true">Todos</button>' + "".join(
    f'<button type="button" data-cat="{esc(c)}" aria-pressed="false">{esc(c)}</button>' for c in CATS)
payload_g = f"""
<p class="lede">Os termos que aparecem nas conversas sobre o sistema, explicados sem jargão. Use a busca ou filtre por assunto; os termos relacionados levam a outros verbetes.</p>
<div style="display:flex;flex-direction:column;gap:12px">
  <label for="glossary-search" class="sr-only">Buscar conceito</label>
  <input type="search" id="glossary-search" class="search" placeholder="Buscar termo ou explicação..." autocomplete="off">
  <div class="chips" id="glossary-cats">{chips}</div>
  <p class="small muted" id="glossary-count" aria-live="polite"></p>
</div>
<div class="cards" id="glossary-grid"></div>
"""
scripts_g = """<script>
(function () {
  "use strict";
  var G = (window.RV_DATA || {}).glossary;
  var grid = document.getElementById("glossary-grid"), q = document.getElementById("glossary-search"),
      count = document.getElementById("glossary-count"), cat = "";
  if (!G || !G.concepts) { grid.textContent = "Dados indisponíveis."; return; }
  var bySlug = {}; G.concepts.forEach(function (c) { bySlug[c.slug] = c; });
  function norm(s) { return s.normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase(); }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
  grid.innerHTML = G.concepts.map(function (c) {
    return "<article class='card' id='concept-" + c.slug + "' data-cat='" + esc(c.category) + "' data-text='" +
      esc(norm(c.term + " " + c.definition)) + "'><span class='tag'>" + esc(c.category) + "</span><h3>" + esc(c.term) +
      "</h3><p>" + esc(c.definition) + "</p>" + (c.related.length ? "<p class='small' style='margin-top:8px'>Veja também: " +
      c.related.map(function (r) { return "<a href='#concept-" + r + "'>" + esc(bySlug[r].term) + "</a>"; }).join(", ") + "</p>" : "") +
      "</article>";
  }).join("");
  function apply() {
    var t = norm(q.value.trim()), n = 0;
    grid.querySelectorAll(".card").forEach(function (el) {
      var ok = (!cat || el.dataset.cat === cat) && (!t || el.dataset.text.indexOf(t) >= 0);
      el.hidden = !ok; if (ok) n++;
    });
    count.textContent = n + (n === 1 ? " termo" : " termos");
  }
  q.addEventListener("input", apply);
  document.querySelectorAll("#glossary-cats button").forEach(function (b) {
    b.addEventListener("click", function () {
      cat = b.dataset.cat;
      document.querySelectorAll("#glossary-cats button").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      apply();
    });
  });
  window.addEventListener("hashchange", function () { cat = ""; q.value = ""; apply(); });
  apply();
})();
</script>"""
render(rel="glossario.html", page_id="glossario", title="Glossário", payload=payload_g,
       agent="reversa-docs-storyteller", template="glossario", scripts=scripts_g, source_md="_reversa_sdd/prd.md")


# ================================================================ FEATURES
def files_of(area):
    return sorted([m for m in mods["modules"] if m["area"] == area and m["loc"] > 0], key=lambda m: -m["loc"])


def ul(items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def table(head, rows, num=()):
    th = "".join(f'<th{" class=num" if i in num else ""}>{h}</th>' for i, h in enumerate(head))
    trs = "".join("<tr>" + "".join(f'<td{" class=num" if i in num else ""}>{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="table-wrap"><table class="data"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


FEATURES = [
    {
        "id": "configuracao-caixas", "title": "Configuração das caixas", "area": "configuracao", "order": 1,
        "tldr": "Define, num único arquivo, quais caixas de e-mail o sistema acompanha, como entra em cada uma e para qual pasta do OneDrive vão os documentos de cada empresa. Acrescentar uma caixa é editar esse arquivo, sem mexer no programa.",
        "why": "O pedido original falava de uma caixa, mas já anunciava outras empresas do grupo. Sem um contrato de configuração, cada caixa nova exigiria alterar o código.",
        "rules": [
            "<b>Caixas numeradas.</b> Cada caixa é declarada como EMAIL1, EMAIL2 e assim por diante; a numeração não precisa ser contínua.",
            "<b>Uma pasta de destino por empresa.</b> Há um destino geral e, se preciso, um destino e um nome de empresa próprios para cada caixa.",
            "<b>Dois modos de acesso.</b> Cada caixa entra por senha de app ou por OAuth 2.0, à escolha do operador.",
            "<b>Data inicial obrigatória.</b> Uma caixa nova só considera mensagens a partir da data informada, para não despejar anos de anexos na pasta de contas a pagar.",
            "<b>Erros detectados antes de acessar a rede.</b> Um problema geral (destino ausente, data inválida) interrompe a execução; um problema de uma só caixa desativa apenas ela, e as demais seguem.",
            "<b>Segredos protegidos.</b> Senhas e tokens nunca aparecem em log, aviso ou tela, e o sistema alerta se o arquivo de configuração estiver legível por outros usuários.",
            "<b>Conferência sem risco.</b> O comando verificar-config lista as caixas, os destinos e o estado das autorizações com as senhas mascaradas, sem acessar a rede.",
        ],
        "errors": [
            ("Caixa sem senha ou sem autorização", "Só essa caixa é desativada; o aviso ao operador cita qual variável falta."),
            ("Duas caixas iguais", "A de número maior é desativada como duplicada."),
            ("Data inicial em formato errado", "A execução não começa; a mensagem indica o formato esperado (AAAA-MM-DD)."),
            ("Destino do OneDrive ausente", "A execução não começa, para não enviar a lugar errado."),
            ("Telegram configurado pela metade", "A execução segue, mas o log registra que as falhas não serão avisadas."),
        ],
        "evolution": [
            ("2026-09-18", "Primeira versão", "Caixas numeradas, destino geral e por caixa, validação e comando verificar-config.", "_reversa_sdd/addenda/001-mvp-email-nf-onedrive.md"),
            ("2026-09-21", "Acesso por OAuth 2.0", "Cada caixa passa a escolher entre senha de app e OAuth; entram as variáveis do cliente OAuth e da pasta de autorizações.", "_reversa_sdd/addenda/002-oauth-gmail-google-cloud.md"),
            ("2026-09-22", "Domínios internos", "Os domínios das próprias caixas passam a identificar as empresas do grupo, que nunca são tratadas como fornecedor.", "_reversa_sdd/addenda/bug-BUG-20260922-VBJD-v001.md"),
            ("2026-09-24", "Destino e nome por empresa", "Cada empresa passa a ter a sua pasta de destino, e os documentos já enviados são realocados.", ""),
        ],
        "numbers": [("0", "linhas de código alteradas para incluir uma caixa"), ("44", "testes só da leitura da configuração")],
    },
    {
        "id": "coleta-email", "title": "Coleta de e-mail", "area": "coleta", "order": 2,
        "tldr": "Entra em cada caixa somente para ler, encontra as mensagens novas, separa os anexos PDF e XML, inclusive os de encaminhamentos, e decide quais são notas fiscais ou boletos. Nada na caixa muda.",
        "why": "Quatro pessoas liam a mesma caixa e nenhuma assumia salvar o anexo. A coleta substitui esse passo manual sem alterar a rotina de quem continua usando o e-mail.",
        "rules": [
            "<b>Somente leitura.</b> A pasta é aberta de modo que nenhuma mensagem é marcada como lida, movida, apagada ou respondida.",
            "<b>Janela com sobreposição.</b> Cada execução relê os dois últimos dias e tudo o que ainda está pendente, para não perder e-mails com data atrasada. A repetição é eliminada pelo registro.",
            "<b>Só o que importa é baixado.</b> Desde 23/09, mensagens já resolvidas são reconhecidas pelo identificador, sem baixar de novo o conteúdo.",
            "<b>PDF e XML, inclusive encaminhados.</b> Imagens, assinaturas e outros formatos são ignorados; arquivos compactados são registrados no log.",
            "<b>Três classes.</b> XML de NF-e (reconhecido pela estrutura oficial), documento com palavra-chave no assunto ou no nome, e sem classificação.",
            "<b>O que não é reconhecido fica retido.</b> Propostas, contratos e afins não vão para o OneDrive; ficam registrados para revisão humana. A decisão, de 18/09, trocou a ideia inicial de enviar todo PDF.",
            "<b>Nunca duas vezes.</b> Cada anexo é identificado pela caixa, pela mensagem e pela assinatura do conteúdo.",
            "<b>Uma caixa não derruba as outras.</b> Se uma caixa recusa o acesso, as seguintes são processadas normalmente.",
        ],
        "errors": [
            ("Acesso recusado pela caixa", "A caixa é pulada nesta rodada e o operador recebe o aviso com a causa provável."),
            ("Pasta de e-mail inexistente", "A caixa é pulada; o log lista as pastas que existem."),
            ("Servidor lento ou fora do ar", "A caixa é pulada; a próxima execução recupera o período pela janela de busca."),
            ("Mensagem com link, sem anexo", "Registrada no log como possível documento sem anexo, para conferência manual."),
            ("Registro de processados ilegível", "A execução para antes de qualquer envio, para não duplicar documentos."),
        ],
        "evolution": [
            ("2026-09-18", "Primeira versão", "Leitura somente de consulta, extração, classificação e retenção dos não reconhecidos.", "_reversa_sdd/addenda/001-mvp-email-nf-onedrive.md"),
            ("2026-09-21", "Entrada por OAuth", "A conexão aceita a autorização OAuth, mantendo a lista fechada de comandos de leitura.", "_reversa_sdd/addenda/002-oauth-gmail-google-cloud.md"),
            ("2026-09-22", "Remetente original do encaminhamento", "A coleta passa a extrair o remetente original de mensagens encaminhadas, dentro ou no corpo do e-mail.", "_reversa_sdd/addenda/bug-BUG-20260922-VBJD-v001.md"),
            ("2026-09-23", "Sem download repetido", "Antes, cada rodada baixava de novo toda a janela, cerca de 8 minutos; agora lê só os identificadores das mensagens resolvidas.", "_reversa_sdd/addenda/004-desempenho-coleta-envio.md"),
        ],
        "open": "Em aberto: uma nota fiscal cujo nome e assunto não têm palavra-chave pode ser retida por engano (BUG-20260922-2FVK, prioridade média).",
        "numbers": [("0", "mensagens alteradas nas caixas"), ("3", "classes de anexo"), ("53", "testes da coleta")],
    },
    {
        "id": "envio-onedrive", "title": "Envio ao OneDrive", "area": "envio", "order": 3,
        "tldr": "Dá a cada documento o nome que o financeiro já usava, escolhe a subpasta pelo vencimento e o envia ao OneDrive, conferindo tamanho e assinatura do arquivo antes de considerá-lo entregue. Nunca apaga nem substitui o que já está lá.",
        "why": "A pasta CONTAS A PAGAR é a fonte de trabalho do financeiro. O documento só existe para a equipe quando está lá, com o nome certo e no dia certo da grade de pagamentos.",
        "rules": [
            "<b>Nome no padrão da pasta.</b> <code>EMPRESA - FORNECEDOR NF 123 - BOLETO.pdf</code> ou <code>... - REF.pdf</code>; o número da nota só aparece quando é conhecido.",
            "<b>Fornecedor pela melhor fonte.</b> Emitente do XML, depois remetente original de um encaminhamento, depois remetente externo; sem fonte, A IDENTIFICAR.",
            "<b>Pasta pelo vencimento.</b> O documento vai para <code>DIA d/202X-mm</code>, a grade que o financeiro já usava. Nota, DANFE e boleto da mesma mensagem ficam juntos.",
            "<b>Sem vencimento, na raiz, com explicação.</b> A planilha LEIAME, no topo da raiz, diz por que cada documento ficou ali.",
            "<b>Nunca cria pastas.</b> Se a subpasta do vencimento não existe, o documento fica pendente e o operador é avisado.",
            "<b>Nunca sobrescreve.</b> Nome ocupado por outro conteúdo gera sufixo _2, _3; conteúdo idêntico já presente conta como entregue, sem cópia.",
            "<b>Entrega conferida.</b> Tamanho e assinatura digital do arquivo no OneDrive precisam bater com o original.",
            "<b>Até 4 envios simultâneos</b>, com até 300 segundos de tolerância por operação.",
            "<b>Sem sobras no servidor.</b> A cópia local é apagada assim que a entrega é confirmada, o que reduz dados fiscais e pessoais em repouso (LGPD).",
        ],
        "errors": [
            ("Autorização do OneDrive expirada", "Os envios da rodada ficam pendentes e o operador recebe o comando para reautorizar."),
            ("Pasta renomeada ou apagada pela equipe", "Nada é criado; o documento fica pendente com o aviso de destino não encontrado."),
            ("OneDrive lento ou limitando requisições", "Novas tentativas automáticas; persistindo, o documento volta na próxima execução."),
            ("Mesmo documento falhando 5 vezes", "Aviso específico ao operador; as tentativas continuam."),
        ],
        "evolution": [
            ("2026-09-18", "Primeira versão", "Envio sem sobrescrita, conferência de tamanho e hash, e comando testar-onedrive.", "_reversa_sdd/addenda/001-mvp-email-nf-onedrive.md"),
            ("2026-09-21", "Convenção de nomes do financeiro", "Os arquivos passam a seguir o padrão já usado na pasta CONTAS A PAGAR.", "docs/onedrive/estrutura-contas-a-pagar.md"),
            ("2026-09-22", "Fornecedor correto", "Na primeira execução real, cerca de metade dos arquivos saiu com o nome da própria empresa como fornecedor; a ordem de fontes corrigiu isso.", "_reversa_sdd/addenda/bug-BUG-20260922-VBJD-v001.md"),
            ("2026-09-23", "Pasta por vencimento", "Documentos passam a ir para a subpasta do dia e do mês do vencimento.", "_reversa_sdd/addenda/003-destino-por-vencimento.md"),
            ("2026-09-23", "Envio em paralelo", "O envio, que levava cerca de 52 minutos num lote de 528 arquivos, passa a usar 4 envios simultâneos, com estimativa de cerca de 13 minutos.", "_reversa_sdd/addenda/004-desempenho-coleta-envio.md"),
            ("2026-09-23", "Tolerância de 300 s", "Operações lentas do OneDrive passam a ter mais tempo antes de contar como falha.", "_reversa_sdd/addenda/005-timeout-rclone.md"),
            ("2026-09-23", "Leitura de vencimento revisada", "Boletos com dígitos colados, rótulo duplicata e vencimento no próprio dia passam a ser lidos.", "_reversa_sdd/addenda/003-destino-por-vencimento-v002.md"),
            ("2026-09-23", "Planilha LEIAME", "A raiz ganha a planilha que explica os documentos sem vencimento.", "_reversa_sdd/addenda/006-sumario-leiame-da-raiz.md"),
        ],
        "extra": ("Por que documentos ficam na raiz", table(["Motivo", "Documentos"], [
            ("Nota fiscal de serviço", "50"), ("DANFE sem vencimento identificável", "32"), ("Nota sem fatura (XML)", "18"),
            ("Documento sem texto legível", "12"), ("Nota paga à vista", "10"), ("Vencimento não localizado", "2"),
            ("Já chegou vencido", "1")], num=(1,)) +
            '<p class="small muted" style="margin-top:8px">Medição sobre os 125 documentos sem vencimento da janela de 23/09/2026, após a revisão da leitura (adendo 006). No lote de 22/09, 62% dos documentos tiveram o vencimento identificado.</p>'),
        "open": "Fora da regra automática: as subpastas especiais de contratos e serviços e a de fatura de cartão de crédito continuam a ser preenchidas à mão pelo financeiro.",
        "numbers": [("62%", "documentos com vencimento identificado no lote real"), ("4", "envios simultâneos"), ("0", "arquivos existentes substituídos")],
    },
    {
        "id": "execucao-monitoramento", "title": "Execução e monitoramento", "area": "execucao", "order": 4,
        "tldr": "Coloca o processo para rodar sozinho a cada 30 minutos, impede que duas execuções se atropelem, registra tudo em log e avisa o operador pelo Telegram quando algo falha e quando volta a funcionar.",
        "why": "Uma automação que falha em silêncio recria o esquecimento de contas que deveria eliminar. Além disso, a ferramenta precisa ser entregue à empresa com operação documentada.",
        "rules": [
            "<b>A cada 30 minutos</b>, nos minutos 0 e 30 de cada hora, sem intervenção humana.",
            "<b>Uma execução por vez.</b> Se a anterior ainda roda, a nova sai de imediato; uma trava esquecida há mais de 25 minutos é descartada.",
            "<b>No máximo 20 minutos por execução.</b> O que não coube continua na próxima, sem perda nem duplicação.",
            "<b>Resultado em código.</b> 0 quando tudo deu certo, 1 quando algo falhou em parte, 2 quando houve erro de configuração ou falha total.",
            "<b>Avisos que não viram ruído.</b> Só falhas e recuperações geram mensagem; uma falha que persiste é lembrada no máximo a cada 6 horas.",
            "<b>Resumo fiel.</b> Toda execução termina com a contagem do que de fato aconteceu, inclusive quando é interrompida pelo limite de tempo.",
            "<b>Log diário</b> com retenção de 30 dias.",
            "<b>Modo de simulação</b> para testar sem enviar, sem registrar e sem avisar.",
            "<b>Pronto para entrega.</b> Guia de instalação e operação e modelo de configuração acompanham o código.",
        ],
        "errors": [
            ("Execução anterior ainda rodando", "A nova sai imediatamente, sem erro."),
            ("Telegram fora do ar", "O log registra aviso não entregue, e a próxima execução tenta de novo."),
            ("Servidor desligado por horas", "Na volta, a janela de busca recupera os e-mails do período."),
            ("Disco cheio ou erro inesperado", "A execução termina com código 2, a trava é liberada e o operador é avisado com a causa."),
        ],
        "evolution": [
            ("2026-09-18", "Primeira versão", "Linha de comando, trava, log, avisos com supressão e recuperação, guia de instalação.", "_reversa_sdd/addenda/001-mvp-email-nf-onedrive.md"),
            ("2026-09-21", "Novos comandos", "autorizar-caixa e testar-caixa entram para apoiar o acesso por OAuth.", "_reversa_sdd/addenda/002-oauth-gmail-google-cloud.md"),
            ("2026-09-22", "Resumo correto na interrupção", "Na primeira execução real, o resumo disse 0 enviados quando 79 arquivos tinham sido entregues. O limite de 20 minutos passou a constar da especificação e o resumo a contar o que foi confirmado.", "_reversa_sdd/addenda/bug-BUG-20260922-RWDA-v001.md"),
            ("2026-09-24", "Operação contínua", "O agendamento a cada 30 minutos entra em operação no servidor.", ""),
        ],
        "extra": ("Comandos disponíveis", table(["Comando", "Para que serve"], [
            ("<code>executar</code>", "Rodada completa; com <code>--simular</code>, apenas mostra o que faria."),
            ("<code>verificar-config</code>", "Confere a configuração sem acessar a rede."),
            ("<code>testar-caixa</code>", "Confirma o acesso a cada caixa, sem ler mensagens."),
            ("<code>autorizar-caixa</code>", "Conduz a autorização OAuth de uma caixa no navegador."),
            ("<code>testar-onedrive</code>", "Grava, confere e apaga um arquivo de teste em cada destino."),
        ])),
        "numbers": [("30 min", "intervalo entre execuções"), ("20 min", "duração máxima de uma execução"), ("6 h", "intervalo mínimo entre lembretes da mesma falha")],
    },
]
ftests = {a["area"]: a["tests"] for a in metrics["area_summary"]}
index = []
for f in FEATURES:
    src = f"_reversa_sdd/sdd/{f['id']}.md"
    files = files_of(f["area"])
    kp = "".join(f'<div class="kpi"><strong>{esc(n)}</strong><span>{esc(t)}</span></div>' for n, t in f["numbers"])
    evo = '<ol class="tl-list">' + "".join(
        f'<li style="--dot:{COLORS[f["area"]]}"><time datetime="{d}">{int(d[8:])}/{d[5:7]}</time>'
        f'<p><b>{esc(t)}.</b> {esc(desc)}</p>{f"<p class=small><code>{esc(s)}</code></p>" if s else ""}</li>'
        for d, t, desc, s in f["evolution"]) + "</ol>"
    code = table(["Arquivo", "O que faz", "Linhas"],
                 [(f"<code>{esc(m['id'].replace('src/email_nf_onedrive/', ''))}</code>", esc(m["doc"]), m["loc"]) for m in files],
                 num=(2,))
    extra = f'<details class="acc"><summary>{esc(f["extra"][0])}</summary><div>{f["extra"][1]}</div></details>' if f.get("extra") else ""
    open_ = f'<section class="callout"><p>{esc(f["open"])}</p></section>' if f.get("open") else ""
    payload = f"""
<section class="feature-tldr">
  <h2>Em poucas palavras</h2>
  <p>{esc(f["tldr"])}</p>
</section>
<section class="kpis">{kp}</section>
<p class="prose muted"><b>Por que existe.</b> {esc(f["why"])}</p>
<details class="acc" open><summary>Regras que importam</summary><div>{ul(f["rules"])}</div></details>
<details class="acc"><summary>Quando algo dá errado</summary><div>{table(["Situação", "O que acontece"], [(esc(a), esc(b)) for a, b in f["errors"]])}</div></details>
{extra}
<details class="acc"><summary>Como evoluiu</summary><div>{evo}</div></details>
<details class="acc"><summary>Onde está no código ({len(files)} arquivos, {ftests[f["area"]]} testes)</summary><div>{code}</div></details>
{open_}
<p class="small muted">Especificação completa: <code>{src}</code>. Os adendos listados em “Como evoluiu” prevalecem sobre o texto original da especificação.</p>
"""
    rel = f"features/{f['id']}.html"
    render(rel=rel, page_id=f"feature-{f['id']}", title=f["title"], payload=payload,
           agent="reversa-docs-storyteller", template="feature", source_md=src, depth=1)
    index.append({"id": f["id"], "slug": f["id"], "title": f["title"], "tldr": f["tldr"], "path": src,
                  "page": rel, "area": f["area"], "order": f["order"],
                  "addenda": [s for _, _, _, s in f["evolution"] if "addenda" in s],
                  "files": {"requirements": True, "design": False, "tasks": False}})
dump("features-index.json", {"schemaVersion": 1, "generatedAt": now_iso(), "sddRoot": "_reversa_sdd/sdd",
                             "layout": "flat (um .md por spec; adendos em _reversa_sdd/addenda)", "specs": index})

# ================================================================ DECK
T = metrics["totals"]
last = timeline["events"][-5:]
feat_cards = "".join(f'<li><a href="features/{x["id"]}.html">{esc(x["title"])}</a>: {esc(x["tldr"].split(".")[0])}.</li>' for x in index)
slides = [
    ("capa", "", f'<div class="seal-slot" id="deck-seal"></div><p class="eyebrow">afla-nfes</p><h2>Notas e boletos do e-mail direto para o OneDrive</h2><p>Arquivamento automático das contas a pagar, a cada 30 minutos, sem ação manual.</p>'),
    ("problema", "O problema", "<h2>Todos viam o e-mail, ninguém salvava a nota</h2><ul><li>Quatro pessoas leem a mesma caixa do financeiro.</li><li>Cada uma presume que outra já arquivou o documento.</li><li>Contas são esquecidas, com risco de multa e juros por atraso.</li></ul>"),
    ("solucao", "A solução", "<h2>Um processo que roda sozinho</h2><ol><li>Lê as caixas do financeiro sem alterar nada.</li><li>Separa notas fiscais e boletos dos demais anexos.</li><li>Dá o nome que a equipe já usava e escolhe a pasta pelo vencimento.</li><li>Envia ao OneDrive e confere que chegou íntegro.</li><li>Avisa o operador se algo falhar.</li></ol>"),
    ("garantias", "Garantias", "<h2>O que o sistema nunca faz</h2><ul><li>Nunca altera as caixas de e-mail: nada é marcado como lido, movido ou apagado.</li><li>Nunca apaga nem substitui arquivos no OneDrive.</li><li>Nunca expõe senhas em log, avisos ou tela.</li><li>Nunca envia o mesmo documento duas vezes.</li></ul>"),
    ("arquitetura", "Arquitetura", '<h2>Seis etapas, um maestro</h2><p>Configuração, coleta, registro, envio e avisos são partes separadas, coordenadas por um ciclo central.</p><p><a href="arquitetura.html">Ver a arquitetura e a cidade do código</a> · <a href="modulos.html">Ver o mapa de módulos</a></p>'),
    ("numeros", "Em números", f'<h2>Pequeno, focado e testado</h2><div class="kpis"><div class="kpi"><strong>{T["loc"]:,}</strong><span>linhas de programa</span></div><div class="kpi"><strong>{T["tests"]}</strong><span>testes automáticos</span></div><div class="kpi"><strong>62%</strong><span>documentos com vencimento identificado no lote real</span></div><div class="kpi"><strong>4</strong><span>envios simultâneos ao OneDrive</span></div></div><p><a href="metricas.html">Ver as métricas</a></p>'.replace(f'{T["loc"]:,}', f'{T["loc"]:,}'.replace(",", "."))),
    ("timeline", "Linha do tempo", "<h2>Do plano à operação em uma semana</h2><ul>" + "".join(
        f'<li><b>{int(e["date"][8:])}/{e["date"][5:7]}</b> · {esc(e["title"])}</li>' for e in last) + '</ul><p><a href="timeline.html">Ver a linha do tempo completa</a></p>'),
    ("features", "Funcionalidades", f"<h2>Quatro partes, quatro páginas</h2><ul>{feat_cards}</ul>"),
    ("aberto", "Em aberto", '<h2>O que ainda pede atenção</h2><ul><li>Uma nota sem palavra-chave no nome ou no assunto pode ser retida por engano (problema registrado, prioridade média).</li><li>Documentos sem vencimento legível, como notas de serviço, ficam na raiz, explicados na planilha LEIAME.</li><li>Notas disponíveis só por link de portal não são baixadas; aparecem no log para conferência.</li><li>Subpastas especiais, como contratos e fatura de cartão, seguem manuais.</li></ul>'),
    ("fim", "Próximos passos", '<h2>Para saber mais</h2><ul><li><a href="glossario.html">Glossário</a>: os termos explicados sem jargão.</li><li><a href="features/envio-onedrive.html">Envio ao OneDrive</a>: nomes, pastas e vencimentos.</li><li><a href="index.html">Voltar à visão geral</a></li></ul>'),
]
lis = "".join(f'<li class="deck-slide" data-slide="{sid}">{f"<p class=eyebrow>{esc(eb)}</p>" if eb else ""}{body}</li>'
              for sid, eb, body in slides)
payload_d = f"""
<p class="lede">Apresentação curta do sistema para quem não acompanhou o projeto. Use as setas do teclado ou os botões; a tecla F alterna a tela cheia.</p>
<section class="deck" id="deck" tabindex="-1">
  <ol class="deck-slides" id="deck-slides">{lis}</ol>
  <nav class="deck-nav" aria-label="Navegação do deck">
    <button type="button" data-action="prev" aria-label="Slide anterior">&larr;</button>
    <span class="deck-counter" id="deck-counter">1 / {len(slides)}</span>
    <button type="button" data-action="next" aria-label="Próximo slide">&rarr;</button>
    <button type="button" data-action="fullscreen" aria-label="Tela cheia">Tela cheia</button>
  </nav>
</section>
"""
scripts_d = """<script>
(function () {
  "use strict";
  var deck = document.getElementById("deck"), slides = deck.querySelectorAll(".deck-slide"),
      counter = document.getElementById("deck-counter"), i = 0;
  var seal = document.getElementById("deck-seal");
  if (seal && window.RV_DATA && window.RV_DATA.sealSvg) seal.innerHTML = window.RV_DATA.sealSvg;
  var start = parseInt((location.hash.match(/slide-(\\d+)/) || [])[1], 10);
  if (start >= 1 && start <= slides.length) i = start - 1;
  function go(n) {
    i = Math.max(0, Math.min(slides.length - 1, n));
    slides.forEach(function (s, j) { s.classList.toggle("is-active", j === i); });
    counter.textContent = (i + 1) + " / " + slides.length;
    history.replaceState(null, "", "#slide-" + (i + 1));
  }
  function fs() {
    if (document.fullscreenElement) document.exitFullscreen();
    else if (deck.requestFullscreen) deck.requestFullscreen();
  }
  deck.querySelector("[data-action=prev]").addEventListener("click", function () { go(i - 1); });
  deck.querySelector("[data-action=next]").addEventListener("click", function () { go(i + 1); });
  deck.querySelector("[data-action=fullscreen]").addEventListener("click", fs);
  document.addEventListener("keydown", function (e) {
    if (e.target.matches("input, textarea, select")) return;
    if (e.key === "ArrowRight" || e.key === "PageDown" || e.key === " ") { e.preventDefault(); go(i + 1); }
    else if (e.key === "ArrowLeft" || e.key === "PageUp") { e.preventDefault(); go(i - 1); }
    else if (e.key === "f" || e.key === "F") fs();
    else if (e.key === "Home") go(0);
    else if (e.key === "End") go(slides.length - 1);
  });
  window.addEventListener("hashchange", function () {
    var n = parseInt((location.hash.match(/slide-(\\d+)/) || [])[1], 10);
    if (n >= 1 && n <= slides.length && n - 1 !== i) go(n - 1);
  });
  go(i);
})();
</script>"""
render(rel="deck.html", page_id="deck", title="Apresentação", payload=payload_d,
       agent="reversa-docs-storyteller", template="deck", scripts=scripts_d, source_md="")

st = state()
pages = ["glossario.html", "deck.html"] + [f"features/{x['id']}.html" for x in index]
register(st, "storyteller", "reversa-docs-storyteller", pages)
st["storytellerAdaptations"] = [
    "glossario derivado de prd.md + specs + adendos (soul.md ausente)",
    "features a partir de _reversa_sdd/sdd/*.md (layout plano, sem */requirements.md)",
]
save_state(st)
print("OK storyteller", len(concepts), "conceitos,", len(slides), "slides,", len(index), "features")
