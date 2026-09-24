"""Analyst: metrics.json + metricas.html; timeline.json + timeline.html."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from rvlib import *  # noqa: F401,F403
import re
import subprocess
from collections import Counter, defaultdict

mods = load("modules.json")
deps = load("deps.json")
AREAS = mods["areas"]
ORDER = ["configuracao", "autorizacao", "coleta", "registro", "envio", "execucao", "."]
COLORS = {".": "#6b7280", "configuracao": "#c28f2c", "autorizacao": "#8e6c8a", "coleta": "#3f7cac",
          "registro": "#5b5ea6", "envio": "#2f8f6b", "execucao": "#b5543c"}
byid = {m["id"]: m for m in mods["modules"]}
code = [m for m in mods["modules"] if m["loc"] > 0]

# ---------------------------------------------------------------- testes por etapa
TEST_AREA = {
    "configuracao": "configuracao", "cli_caixas": "configuracao",
    "autoriza": "autorizacao", "oauth": "autorizacao",
    "coleta": "coleta", "mime": "coleta", "classificacao": "coleta", "janela": "coleta",
    "registro": "registro",
    "nomeacao": "envio", "vencimento": "envio", "envio": "envio", "rclone": "envio", "leiame": "envio",
    "ciclo": "execucao", "avisos": "execucao", "trava": "execucao", "logs": "execucao",
    "segredos": ".",
}
tests_by_area = Counter()
n_tests = 0
for f in sorted((ROOT / "tests").rglob("test_*.py")):
    n = f.read_text(encoding="utf-8").count("def test_")
    n_tests += n
    stem = f.stem[5:]
    area = next((a for k, a in TEST_AREA.items() if k in stem), ".")
    tests_by_area[area] += n
test_loc = sum(sum(1 for l in f.read_text(encoding="utf-8").splitlines() if l.strip())
               for f in (ROOT / "tests").rglob("*.py"))

# ---------------------------------------------------------------- metrics.json
bins = [0, 25, 50, 100, 150, 200, 300]
counts = [0] * (len(bins) - 1)
for m in code:
    for i in range(len(bins) - 1):
        if bins[i] < m["loc"] <= bins[i + 1]:
            counts[i] += 1
flows = defaultdict(int)
for e in deps["edges"]:
    a, b = byid[e["source"]]["area"], byid[e["target"]]["area"]
    if a != b:
        flows[(a, b)] += e["weight"]
metrics = {
    "schemaVersion": 1, "generatedAt": now_iso(),
    "totals": {"modules": len(code), "loc": sum(m["loc"] for m in code), "edges": len(deps["edges"]),
               "cycles": len(deps["cycles"]), "tests": n_tests, "testLoc": test_loc},
    "treemap_loc_by_folder": [
        {"folder": m["folder"], "area": m["area"], "areaLabel": AREAS[m["area"]], "id": m["id"],
         "name": m["name"], "loc": m["loc"]} for m in code],
    "top_complexity": [{"id": m["id"], "name": m["name"], "area": m["area"], "complexity": m["complexity"], "loc": m["loc"]}
                       for m in sorted(code, key=lambda m: -m["complexity"])[:15]],
    "loc_histogram": {"bins": bins, "counts": counts},
    "dependency_sankey": {
        "nodes": [{"id": k, "name": AREAS[k], "color": COLORS[k]} for k in ORDER],
        "links": [{"source": AREAS[a], "target": AREAS[b], "value": v} for (a, b), v in sorted(flows.items())]},
    "language_distribution": [
        {"language": lang, "modules": sum(1 for m in code if m["language"] == lang),
         "loc": sum(m["loc"] for m in code if m["language"] == lang)} for lang in ("python", "sql")],
    "area_summary": [
        {"area": k, "label": AREAS[k], "color": COLORS[k],
         "loc": sum(m["loc"] for m in code if m["area"] == k),
         "modules": sum(1 for m in code if m["area"] == k),
         "tests": tests_by_area[k]} for k in ORDER],
}
dump("metrics.json", metrics)
T = metrics["totals"]


def br(n):
    return f"{n:,}".replace(",", ".")


payload_met = f"""
<p class="lede">Um retrato do tamanho, da organização e da proteção do programa. Os números ajudam a responder três perguntas: o sistema é grande? Onde está o esforço? Ele é testado?</p>

<section class="kpis">
  <div class="kpi"><strong>{br(T["loc"])}</strong><span>linhas de código do programa</span></div>
  <div class="kpi"><strong>{T["modules"]}</strong><span>arquivos com código</span></div>
  <div class="kpi"><strong>{T["tests"]}</strong><span>testes automáticos</span></div>
  <div class="kpi"><strong>{br(T["testLoc"])}</strong><span>linhas de teste, mais que o próprio programa</span></div>
  <div class="kpi"><strong>{T["cycles"]}</strong><span>dependências circulares</span></div>
</section>

<section class="dashboard">
  <article class="chart-card wide">
    <h2>Onde está o código</h2>
    <p>Cada retângulo é um arquivo; a área é proporcional ao número de linhas. As cores separam as etapas do processo.</p>
    <div class="chart" id="chart-treemap"></div>
  </article>
  <article class="chart-card">
    <h2>Código e testes por etapa</h2>
    <p>Barras de código (linhas) ao lado da quantidade de testes que verificam cada etapa.</p>
    <div class="chart" id="chart-areas"></div>
  </article>
  <article class="chart-card">
    <h2>Arquivos com mais decisões</h2>
    <p>Quanto mais caminhos de decisão (se isto, então aquilo), mais cuidado o arquivo exige ao ser alterado.</p>
    <div class="chart" id="chart-complexity"></div>
  </article>
  <article class="chart-card wide">
    <h2>Tamanho dos arquivos</h2>
    <p>A maioria dos arquivos é pequena, o que facilita a leitura e a manutenção.</p>
    <div class="chart" id="chart-histogram" style="height:260px"></div>
  </article>
  <article class="chart-card wide">
    <h2>Quem depende de quem</h2>
    <p>Cada célula conta quantas vezes a etapa da linha usa a etapa da coluna; quanto mais escura, mais forte a ligação. A linha da execução mostra o maestro que puxa todas as demais.</p>
    <div class="table-wrap" id="dep-matrix"></div>
  </article>
</section>

<section class="callout">
  <h3>Como ler estes números</h3>
  <ul>
    <li><b>Tamanho modesto.</b> Cerca de três mil linhas é um programa pequeno e focado, compatível com uma ferramenta de um único propósito.</li>
    <li><b>Esforço concentrado onde há risco.</b> As regras de vencimento e de nome dos arquivos estão entre as partes com mais decisões, porque lidam com a variedade de formatos de boletos e notas de cada fornecedor.</li>
    <li><b>Bem protegido.</b> Há mais linhas de teste do que de programa. Os testes usam apenas dados fictícios e nenhum acessa a internet.</li>
  </ul>
</section>
"""

hc_common = """
  var css = getComputedStyle(document.body);
  var FG = css.getPropertyValue("--reversa-fg").trim() || "#1e2937";
  var MUTED = css.getPropertyValue("--reversa-fg-muted").trim() || "#4d5a6b";
  var GRID = css.getPropertyValue("--reversa-border").trim() || "#d6d2c8";
  Highcharts.setOptions({
    lang: { decimalPoint: ",", thousandsSep: ".", contextButtonTitle: "Exportar", downloadPNG: "Baixar PNG", downloadSVG: "Baixar SVG", viewFullscreen: "Tela cheia", exitFullscreen: "Sair da tela cheia", printChart: "Imprimir" },
    chart: { backgroundColor: "transparent", style: { fontFamily: "inherit" } },
    title: { text: null }, credits: { enabled: false },
    xAxis: { labels: { style: { color: MUTED } }, lineColor: GRID, tickColor: GRID },
    yAxis: { labels: { style: { color: MUTED } }, gridLineColor: GRID, title: { style: { color: MUTED } } },
    legend: { itemStyle: { color: FG, fontWeight: "normal" } },
    exporting: { buttons: { contextButton: { menuItems: ["viewFullscreen", "downloadPNG", "downloadSVG"] } } }
  });
"""

scripts_met = """<script>
(function () {
  "use strict";
  var M = (window.RV_DATA || {}).metrics;
  if (!window.Highcharts || !M || !M.totals) {
    document.querySelectorAll(".chart").forEach(function (c) { c.textContent = "Highcharts ou dados indisponíveis."; });
    return;
  }
""" + hc_common + """
  var COLOR = {}, LABEL = {};
  M.area_summary.forEach(function (a) { COLOR[a.area] = a.color; LABEL[a.area] = a.label; });

  var tm = M.area_summary.map(function (a) { return { id: a.area, name: a.label, color: a.color }; });
  M.treemap_loc_by_folder.forEach(function (f) {
    tm.push({ parent: f.area, name: f.name === "__init__" ? f.folder.split("/").pop() : f.name, value: f.loc });
  });
  Highcharts.chart("chart-treemap", {
    series: [{ type: "treemap", layoutAlgorithm: "squarified", alternateStartingDirection: true, data: tm,
      levels: [{ level: 1, borderWidth: 3, borderColor: "#ffffff", dataLabels: { enabled: true, align: "left", verticalAlign: "top",
        style: { fontSize: "13px", fontWeight: "600", textOutline: "none", color: "#ffffff" } } },
        { level: 2, borderWidth: 1, borderColor: "#ffffff", colorVariation: { key: "brightness", to: 0.35 },
          dataLabels: { style: { fontSize: "11px", fontWeight: "normal", textOutline: "none", color: "#ffffff" } } }] }],
    tooltip: { pointFormat: "<b>{point.name}</b>: {point.value} linhas" }
  });

  Highcharts.chart("chart-areas", {
    chart: { type: "bar" },
    xAxis: { categories: M.area_summary.map(function (a) { return a.label; }) },
    yAxis: [{ title: { text: "Linhas de código" } }, { title: { text: "Testes" }, opposite: true }],
    series: [
      { name: "Linhas de código", color: "#3d4a5c", data: M.area_summary.map(function (a) { return { y: a.loc, color: a.color }; }), yAxis: 0 },
      { name: "Testes", data: M.area_summary.map(function (a) { return a.tests; }), color: "#9aa3ad", yAxis: 1 }
    ],
    plotOptions: { series: { groupPadding: 0.12 } }
  });

  Highcharts.chart("chart-complexity", {
    chart: { type: "bar" },
    xAxis: { categories: M.top_complexity.map(function (c) { return c.name; }) },
    yAxis: { title: { text: "Caminhos de decisão" } },
    legend: { enabled: false },
    series: [{ name: "Caminhos de decisão", data: M.top_complexity.map(function (c) {
      return { y: c.complexity, color: COLOR[c.area], custom: { area: LABEL[c.area], loc: c.loc } }; }) }],
    tooltip: { pointFormat: "{point.custom.area}<br>{point.y} caminhos em {point.custom.loc} linhas" }
  });

  var b = M.loc_histogram.bins;
  Highcharts.chart("chart-histogram", {
    chart: { type: "column" },
    xAxis: { categories: M.loc_histogram.counts.map(function (_, i) { return (b[i] + 1) + " a " + b[i + 1]; }), title: { text: "Linhas por arquivo" } },
    yAxis: { title: { text: "Arquivos" }, allowDecimals: false },
    legend: { enabled: false },
    series: [{ name: "Arquivos", data: M.loc_histogram.counts, color: "#3d4a5c" }],
    plotOptions: { column: { pointPadding: 0.05, groupPadding: 0.05 } }
  });

  var names = M.dependency_sankey.nodes.map(function (n) { return n.name; }), val = {}, mx = 1;
  M.dependency_sankey.links.forEach(function (l) { val[l.source + "|" + l.target] = l.value; mx = Math.max(mx, l.value); });
  var h = "<table class='data dep-matrix'><thead><tr><th>usa &rarr;</th>" + names.map(function (n) { return "<th class='num'>" + n.split(" ")[0] + "</th>"; }).join("") + "</tr></thead><tbody>";
  M.dependency_sankey.nodes.forEach(function (a) {
    h += "<tr><th><span class='swatch' style='background:" + a.color + "'></span> " + a.name + "</th>";
    names.forEach(function (b) {
      var v = val[a.name + "|" + b] || 0;
      h += a.name === b ? "<td class='num muted'>&middot;</td>" : "<td class='num' title='" + a.name + " usa " + b + ": " + v + "' style='background:rgba(61,74,92," + (v ? 0.12 + 0.75 * v / mx : 0) + ");color:" + (v / mx > 0.5 ? "#fff" : "inherit") + "'>" + (v || "") + "</td>";
    });
    h += "</tr>";
  });
  document.getElementById("dep-matrix").innerHTML = h + "</tbody></table>";
})();
</script>"""

VENDOR_HC = ['<script src="assets/vendor/highcharts.js"></script>',
             '<script src="assets/vendor/highcharts-accessibility.js"></script>',
             '<script src="assets/vendor/highcharts-exporting.js"></script>']
render(rel="metricas.html", page_id="metricas", title="Métricas", payload=payload_met,
       agent="reversa-docs-analyst", template="metricas",
       head_extras="\n    ".join(VENDOR_HC + ['<script src="assets/vendor/highcharts-treemap.js"></script>']),
       scripts=scripts_met, source_md="")

# ---------------------------------------------------------------- timeline.json
log = subprocess.run(["git", "-C", str(ROOT), "log", "--reverse", "--format=%h|%ad|%s", "--date=iso-strict"],
                     capture_output=True, text=True, check=True).stdout.strip().splitlines()
commits = []
for line in log:
    h, d, s = line.split("|", 2)
    kind = re.match(r"(\w+)", s).group(1) if re.match(r"\w+:", s) else "outro"
    commits.append({"hash": h, "date": d[:10], "datetime": d, "kind": kind, "subject": s})

KIND = {
    "planejamento": ("Planejamento", "#6b7280"),
    "entrega": ("Nova capacidade", "#2f8f6b"),
    "correcao": ("Correção", "#b5543c"),
    "melhoria": ("Melhoria", "#3f7cac"),
    "operacao": ("Operação", "#c28f2c"),
    "documento": ("Documentação", "#8e6c8a"),
}
milestones = [
    ("2026-09-18", "planejamento", "Problema e plano definidos",
     "Registro do problema (contas esquecidas porque ninguém assume arquivar NFs e boletos), das personas, do PRD e das especificações das quatro partes do sistema.",
     ["d4c9128", "6258df2"], "_reversa_sdd/prd.md"),
    ("2026-09-18", "entrega", "Primeira versão entregue",
     "Arquivamento automático das notas e boletos do e-mail no OneDrive, com registro do que já foi processado, avisos pelo Telegram, testes automáticos e guia de instalação.",
     ["4c9d941", "cd90f1d", "89a094a"], "_reversa_sdd/addenda/001-mvp-email-nf-onedrive.md"),
    ("2026-09-21", "entrega", "Nomes no padrão da pasta CONTAS A PAGAR",
     "Os arquivos passam a receber o nome que o financeiro já usava: empresa, fornecedor, número da nota e tipo do documento.",
     ["2db51b3", "0511931"], "docs/onedrive/estrutura-contas-a-pagar.md"),
    ("2026-09-21", "entrega", "Acesso às caixas por OAuth 2.0",
     "Alternativa à senha de app: cada caixa é autorizada uma vez no navegador e a senha da conta deixa de ser guardada. O acesso continua somente leitura.",
     ["e118df5", "d146f95", "eeb74b0"], "_reversa_sdd/addenda/002-oauth-gmail-google-cloud.md"),
    ("2026-09-22", "documento", "Política de privacidade",
     "Publicada a política de privacidade que o Google exige para autorizar o acesso por OAuth.",
     ["e251475"], "docs/politica-de-privacidade.md"),
    ("2026-09-22", "operacao", "Primeira execução real",
     "O sistema roda pela primeira vez sobre caixas reais. Três problemas são registrados: fornecedor com o nome da própria empresa, resumo com zero enviados após interrupção e NF sem palavra-chave retida.",
     ["93afccf"], "_reversa_sdd/traceability/bugs.md"),
    ("2026-09-22", "correcao", "Fornecedor correto em encaminhamentos internos",
     "Quando um colega encaminhava a nota, o arquivo recebia o nome da própria empresa como fornecedor. Corrigido (prioridade alta).",
     ["91c1c39", "d1a2875"], "_reversa_sdd/addenda/bug-BUG-20260922-VBJD-v001.md"),
    ("2026-09-22", "correcao", "Resumo correto quando a execução é interrompida",
     "Se o limite de tempo interrompia a execução, o resumo dizia que nada fora enviado. Agora conta os envios confirmados até a interrupção.",
     ["b95a42f"], "_reversa_sdd/addenda/bug-BUG-20260922-RWDA-v001.md"),
    ("2026-09-23", "entrega", "Pasta por vencimento",
     "Cada documento vai para a subpasta do dia e do mês do seu vencimento, na grade que o financeiro já usava, com a data lida do XML, do boleto ou do texto da nota. No lote real, 62% dos documentos tiveram o vencimento identificado; os demais ficam na raiz.",
     ["e4dcad9"], "_reversa_sdd/addenda/003-destino-por-vencimento.md"),
    ("2026-09-23", "melhoria", "Envio em paralelo",
     "Medição mostrou 52 minutos só de envio, um arquivo por vez. Agora até 4 arquivos seguem ao mesmo tempo e mensagens já resolvidas não são baixadas de novo.",
     ["1c24fa7"], "_reversa_sdd/addenda/004-desempenho-coleta-envio.md"),
    ("2026-09-23", "melhoria", "Mais tolerância a lentidão do OneDrive",
     "O tempo máximo de cada operação com o OneDrive sobe de 120 para 300 segundos, reduzindo falhas por lentidão momentânea.",
     ["d6f69aa"], "_reversa_sdd/addenda/005-timeout-rclone.md"),
    ("2026-09-23", "correcao", "Leitura de vencimento revisada",
     "Diagnóstico de 130 documentos que ficaram na raiz levou a ler melhor a linha digitável dos boletos, o rótulo duplicata e o vencimento no próprio dia.",
     ["fd302a4"], "_reversa_sdd/addenda/003-destino-por-vencimento-v002.md"),
    ("2026-09-23", "entrega", "Planilha LEIAME na raiz",
     "Uma planilha no topo de cada pasta explica, em linguagem de financeiro, por que cada documento da raiz ficou sem vencimento.",
     ["7f26606"], "_reversa_sdd/addenda/006-sumario-leiame-da-raiz.md"),
    ("2026-09-24", "operacao", "Pastas por empresa e agendamento contínuo",
     "Os documentos já enviados são realocados para a pasta de destino de cada empresa, e a execução automática a cada 30 minutos entra em operação no servidor.",
     ["b0aaa23"], ""),
]
subj = {c["hash"]: c["subject"] for c in commits}
events = [{"date": d, "kind": k, "kindLabel": KIND[k][0], "color": KIND[k][1], "title": t, "description": desc,
           "commits": [{"hash": h, "subject": subj.get(h, "")} for h in hs], "source": src}
          for d, k, t, desc, hs, src in milestones]
per_day = defaultdict(Counter)
for c in commits:
    per_day[c["date"]][c["kind"]] += 1
bugs = [
    {"id": "BUG-20260922-VBJD", "title": "Fornecedor recebe o nome da própria empresa em encaminhamento interno", "priority": "P1", "status": "resolvido"},
    {"id": "BUG-20260922-RWDA", "title": "Resumo informa 0 enviados quando a execução é interrompida pelo limite de tempo", "priority": "P2", "status": "resolvido"},
    {"id": "BUG-20260922-2FVK", "title": "Anexo de NF sem palavra-chave no nome é retido por engano", "priority": "P2", "status": "aberto"},
]
dump("timeline.json", {
    "schemaVersion": 1, "generatedAt": now_iso(), "source": "git log + _reversa_sdd/addenda + _reversa_bugs",
    "kinds": {k: {"label": v[0], "color": v[1]} for k, v in KIND.items()},
    "events": events, "commits": commits,
    "commitsPerDay": [{"date": d, **dict(c)} for d, c in sorted(per_day.items())],
    "bugs": bugs,
})

legend_tl = "".join(f'<li><span class="swatch" style="background:{c}"></span>{esc(l)}</li>' for l, c in KIND.values())
payload_tl = f"""
<p class="lede">Do problema à operação contínua em uma semana. A linha do tempo reúne os marcos do projeto a partir do histórico de versões, dos adendos às especificações e dos problemas registrados.</p>

<section class="kpis">
  <div class="kpi"><strong>7</strong><span>dias do plano à operação</span></div>
  <div class="kpi"><strong>{len(commits)}</strong><span>registros no histórico</span></div>
  <div class="kpi"><strong>{sum(1 for e in events if e["kind"] == "entrega")}</strong><span>novas capacidades</span></div>
  <div class="kpi"><strong>2 de 3</strong><span>problemas resolvidos</span></div>
</section>

<ul class="legend">{legend_tl}</ul>

<section class="tl-layout">
  <div>
    <ol class="tl-list" id="tl-list"></ol>
  </div>
  <aside class="card tl-details" aria-live="polite">
    <h2 style="font-size:16px">Detalhes do marco</h2>
    <div id="event-details"><p class="muted small">Clique em um marco para ver o que mudou e os registros correspondentes.</p></div>
  </aside>
</section>

<section class="chart-card">
  <h2>Ritmo de trabalho</h2>
  <p>Registros no histórico por dia, separados pela natureza da mudança.</p>
  <div class="chart" id="chart-rhythm" style="height:300px"></div>
</section>

<section>
  <h2>Problemas registrados</h2>
  <div class="table-wrap"><table class="data">
    <thead><tr><th>Identificador</th><th>Descrição</th><th>Prioridade</th><th>Situação</th></tr></thead>
    <tbody>{"".join(f'<tr><td><code>{b["id"]}</code></td><td>{esc(b["title"])}</td><td>{b["priority"]}</td><td><span class="reversa-pill {"is-low" if b["status"] == "resolvido" else "is-medium"}">{b["status"]}</span></td></tr>' for b in bugs)}</tbody>
  </table></div>
</section>
"""

scripts_tl = """<script>
(function () {
  "use strict";
  var T = (window.RV_DATA || {}).timeline;
  var list = document.getElementById("tl-list"), box = document.getElementById("event-details");
  if (!T || !T.events) { list.innerHTML = "<li>Dados indisponíveis.</li>"; return; }
  var MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  function fmt(d) { var p = d.split("-"); return +p[2] + " " + MESES[+p[1] - 1]; }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
  function show(i) {
    var e = T.events[i];
    box.innerHTML = "<p class='small muted'>" + fmt(e.date) + " &middot; " + e.kindLabel + "</p><h3>" + esc(e.title) + "</h3><p>" +
      esc(e.description) + "</p>" + (e.commits.length ? "<p class='small muted' style='margin-bottom:4px'>Registros no histórico</p><ul class='small'>" +
      e.commits.map(function (c) { return "<li><code>" + c.hash + "</code> " + esc(c.subject) + "</li>"; }).join("") + "</ul>" : "") +
      (e.source ? "<p class='small'>Fonte: <code>" + esc(e.source) + "</code></p>" : "");
    list.querySelectorAll("button").forEach(function (b, j) { b.setAttribute("aria-pressed", j === i ? "true" : "false"); });
  }
  T.events.forEach(function (e, i) {
    var li = document.createElement("li");
    li.style.setProperty("--dot", e.color);
    li.innerHTML = "<button type='button'><time datetime='" + e.date + "'>" + fmt(e.date) + "</time><span class='kind' style='color:" + e.color + "'>" +
      e.kindLabel + "</span><p><b>" + esc(e.title) + "</b></p></button>";
    li.querySelector("button").addEventListener("click", function () { show(i); });
    list.appendChild(li);
  });
  show(T.events.length - 1);

  if (!window.Highcharts) return;
""" + hc_common + """
  var KINDS = { feat: ["Funcionalidade", "#2f8f6b"], fix: ["Correção", "#b5543c"], perf: ["Desempenho", "#3f7cac"],
    test: ["Testes", "#5b5ea6"], docs: ["Documentação", "#8e6c8a"], chore: ["Manutenção", "#9aa3ad"] };
  var days = T.commitsPerDay.map(function (d) { return d.date; });
  Highcharts.chart("chart-rhythm", {
    chart: { type: "column" },
    xAxis: { categories: days.map(fmt) },
    yAxis: { title: { text: "Registros" }, allowDecimals: false, stackLabels: { enabled: true, style: { color: MUTED, textOutline: "none" } } },
    plotOptions: { column: { stacking: "normal", borderWidth: 0 } },
    series: Object.keys(KINDS).map(function (k) {
      return { name: KINDS[k][0], color: KINDS[k][1], data: T.commitsPerDay.map(function (d) { return d[k] || 0; }) };
    })
  });
})();
</script>"""

render(rel="timeline.html", page_id="timeline", title="Linha do tempo", payload=payload_tl,
       agent="reversa-docs-analyst", template="timeline", head_extras="\n    ".join(VENDOR_HC),
       scripts=scripts_tl, source_md="")

st = state()
register(st, "analyst", "reversa-docs-analyst", ["metricas.html", "timeline.html"])
st["timelineSource"] = "git log + addenda + _reversa_bugs (chronicle.md ausente)"
save_state(st)
print("OK analyst", T, len(events), "marcos", len(commits), "commits")
