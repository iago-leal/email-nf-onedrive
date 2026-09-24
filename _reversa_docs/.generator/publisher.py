"""Publisher: selo, data.js, nav + mini-selo, auto-discovery, index, placeholder, links, smoke test, telemetria."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from rvlib import *  # noqa: F401,F403
import math
import os
import random
import re
import shutil
import threading
import time
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

t0 = time.time()
st = state()
seed_hex = CONFIG["seed"]["hash"].split(":", 1)[1]
PATTERNS = ["flow-field", "particle-orbit", "crystal-lattice", "wave-interference", "noise-strata"]
pattern = PATTERNS[int(seed_hex[:2], 16) % 5]
PAL = {"bg": "#f5f3ee", "fg": ["#3d4a5c", "#7c8a99", "#a06b4a", "#4f6b5d", "#bdb4a4"], "accent": "#1e2937"}

# Backup se já houver saída do Publisher
targets = [DOCS / "index.html", DOCS / "assets/img/seal.svg", DOCS / "assets/img/seal-mini.svg"]
if any(p.exists() for p in targets):
    bk = DOCS / f".backup-{datetime.now():%Y%m%d-%H%M%S}"
    for p in targets:
        if p.exists():
            (bk / p.relative_to(DOCS)).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, bk / p.relative_to(DOCS))


# ---------------------------------------------------------------- 1-2. selo (particle-orbit, SVG determinístico)
def seal(size, mini=False):
    rnd = random.Random(int(seed_hex[:16], 16))
    c = size / 2
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
           f'class="{"seal-mini" if mini else "seal-hero"}" role="img" aria-label="Selo do projeto afla-nfes">',
           f'<circle cx="{c}" cy="{c}" r="{c}" fill="{PAL["bg"]}"/>']
    n_orb = 3 if mini else 7
    sw = size / (26 if mini else 400)
    for i in range(n_orb):
        rx = c * (0.28 + 0.62 * (i + 1) / n_orb)
        ry = rx * (0.35 + 0.5 * rnd.random())
        ang = rnd.uniform(0, 180)
        col = PAL["fg"][[0, 0, 1, 3, 4, 1, 0][i % 7]]
        out.append(f'<ellipse cx="{c}" cy="{c}" rx="{rx:.1f}" ry="{ry:.1f}" fill="none" stroke="{col}" '
                   f'stroke-opacity="{0.55 if mini else 0.35}" stroke-width="{sw * (1.6 if mini else 1):.2f}" '
                   f'transform="rotate({ang:.1f} {c} {c})"/>')
        n_p = 1 if mini else 6 + rnd.randint(0, 8)
        for _ in range(n_p):
            t = rnd.uniform(0, 2 * math.pi)
            # trilha: arco curto ao longo da órbita
            pts = []
            span = 0.0 if mini else rnd.uniform(0.15, 0.5)
            for k in range(8):
                tt = t - span * k / 7
                x, y = rx * math.cos(tt), ry * math.sin(tt)
                a = math.radians(ang)
                pts.append((c + x * math.cos(a) - y * math.sin(a), c + x * math.sin(a) + y * math.cos(a)))
            pc = PAL["fg"][rnd.choice([0, 0, 2, 3, 1])]
            if span:
                d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                out.append(f'<path d="{d}" fill="none" stroke="{pc}" stroke-width="{sw * 2.2:.2f}" stroke-linecap="round" stroke-opacity="0.7"/>')
            r = size * (0.045 if mini else rnd.uniform(0.006, 0.016))
            out.append(f'<circle cx="{pts[0][0]:.1f}" cy="{pts[0][1]:.1f}" r="{r:.1f}" fill="{pc}"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="{c * (0.16 if mini else 0.11):.1f}" fill="{PAL["accent"]}"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="{c * (0.07 if mini else 0.05):.1f}" fill="{PAL["fg"][2]}"/>')
    out.append(f'<circle cx="{c}" cy="{c}" r="{c - sw}" fill="none" stroke="{PAL["accent"]}" stroke-width="{sw * 1.5:.2f}"/>')
    out.append("</svg>")
    return "".join(out)


IMG = DOCS / "assets/img"
IMG.mkdir(parents=True, exist_ok=True)
seal_svg, seal_mini = seal(800), seal(64, mini=True)
(IMG / "seal.svg").write_text(seal_svg, encoding="utf-8")
(IMG / "seal-mini.svg").write_text(seal_mini, encoding="utf-8")

# ---------------------------------------------------------------- 5. auto-discovery
aux, aborted = [], False
limit = time.time() + 10
for root in (ROOT / "_reversa_sdd", ROOT / ".reversa"):
    for dirpath, dirs, files in os.walk(root):
        rel = Path(dirpath).relative_to(ROOT)
        if len(rel.parts) > 6 or rel.as_posix().startswith((".reversa/_config", ".reversa/context")):
            dirs[:] = []
            continue
        if time.time() > limit:
            aborted = True
            break
        for fn in files:
            if not fn.endswith(".html"):
                continue
            txt = (Path(dirpath) / fn).read_text(encoding="utf-8", errors="ignore")[:6000]
            m = re.search(r'<meta name="reversa-category" content="([^"]+)"', txt)
            if not m:
                continue
            g = lambda k: (re.search(rf'<meta name="{k}" content="([^"]*)"', txt) or [None, ""])[1]
            aux.append({"path": (rel / fn).as_posix(), "category": m.group(1), "producer": g("reversa-producer-agent"),
                        "generated_at": g("reversa-generated-at"),
                        "title": (re.search(r"<title>(.*?)</title>", txt, re.S) or [None, fn])[1].strip()})

# ---------------------------------------------------------------- 3. nav + data.js
LABELS = [("index", "index.html", "Visão geral"), ("arquitetura", "arquitetura.html", "Arquitetura"),
          ("modulos", "modulos.html", "Módulos"), ("topologia", "topologia.html", "Topologia"),
          ("metricas", "metricas.html", "Métricas"), ("timeline", "timeline.html", "Linha do tempo"),
          ("glossario", "glossario.html", "Glossário"), ("deck", "deck.html", "Apresentação")]
if "index.html" not in st["pagesGenerated"]:
    st["pagesGenerated"].insert(0, "index.html")
gen = set(st["pagesGenerated"])
nav = [{"id": i, "href": h, "label": l} for i, h, l in LABELS if h in gen]
if any(p.startswith("features/") for p in gen):
    nav.append({"id": "features", "href": "index.html#funcionalidades", "label": "Funcionalidades"})


def read_json(name, default):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


RV = {
    "modules": read_json("modules.json", {}), "deps": read_json("deps.json", {}),
    "metrics": read_json("metrics.json", {}), "timeline": read_json("timeline.json", {}),
    "glossary": read_json("soul.json", {}), "featuresIndex": read_json("features-index.json", {}),
    "sealSvg": seal_svg, "sealMiniSvg": seal_mini, "seedShort": seed_hex[:8], "nav": nav,
    "config": {k: CONFIG["interview"][k] for k in ("visualStyle", "readerProfile", "depth")},
}
(DOCS / "assets/js/data.js").write_text(
    "/* Gerado pelo reversa-docs-publisher. Fonte única de dados do mini-site (sem fetch local). */\n"
    "window.RV_DATA = " + json.dumps(RV, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")


def nav_html(depth, current=None):
    up = "../" * depth
    return "".join(f'<a href="{up}{n["href"]}" data-page-id="{n["id"]}">{esc(n["label"])}</a>' for n in nav)


def inject(path, depth):
    t = path.read_text(encoding="utf-8")
    if "<!-- MINI_SEAL_SVG -->" in t:
        t = t.replace("<!-- MINI_SEAL_SVG -->", seal_mini)
    else:
        t = re.sub(r'<svg[^>]*class="seal-mini".*?</svg>', lambda _: seal_mini, t, count=1, flags=re.S)
    if "<!-- NAV_LINKS -->" in t:
        t = t.replace("<!-- NAV_LINKS -->", nav_html(depth))
    else:
        t = re.sub(r'(<nav class="reversa-doc-nav"[^>]*>).*?(</nav>)', lambda m: m.group(1) + "\n            " + nav_html(depth) + "\n        " + m.group(2), t, count=1, flags=re.S)
    if 'rel="icon"' not in t:
        t = t.replace("<link rel=\"stylesheet\" href=\"" + "../" * depth + "assets/css/style.css\">",
                      "<link rel=\"icon\" type=\"image/svg+xml\" href=\"" + "../" * depth + "assets/img/seal-mini.svg\">\n    <link rel=\"stylesheet\" href=\"" + "../" * depth + "assets/css/style.css\">", 1)
    assert t.index("assets/js/data.js") < t.index("assets/js/nav.js")
    path.write_text(t, encoding="utf-8")


# ---------------------------------------------------------------- 8. placeholder para omitidas
for o in st["pagesOmitted"]:
    if o["page"] == "topologia.html":
        render(rel="topologia.html", page_id="topologia", title="Topologia", agent="reversa-docs-publisher",
               template="topologia", head_extras='<meta name="reversa-placeholder" content="true">',
               payload="""<div class="placeholder-box"><p>Esta página compararia a topologia atual do sistema com alternativas de arquitetura. Ela depende de <code>_reversa_sdd/architecture.md</code>, que ainda não existe neste projeto.</p>
<p class="muted">Para habilitá-la, rode <code>/reversa-architect</code> e depois <code>/reversa-docs</code>. Enquanto isso, a página <a href="arquitetura.html">Arquitetura</a> mostra o fluxo e a organização do código.</p></div>""")

# ---------------------------------------------------------------- 6. index
fi = RV["featuresIndex"].get("specs", [])
M = RV["metrics"].get("totals", {})
CARDS = [
    ("arquitetura.html", "Estrutura", "Arquitetura", "O caminho de um documento do e-mail ao OneDrive e a cidade 3D do código."),
    ("modulos.html", "Estrutura", "Módulos", "Mapa interativo de como os arquivos do programa se conectam."),
    ("metricas.html", "Números", "Métricas", "Tamanho, concentração de esforço e cobertura de testes."),
    ("timeline.html", "Histórico", "Linha do tempo", "Do problema à operação contínua, marco a marco."),
    ("glossario.html", "Referência", "Glossário", "NF-e, DANFE, linha digitável, LEIAME e outros termos, sem jargão."),
    ("deck.html", "Apresentação", "Apresentação", "Dez slides para explicar o sistema em poucos minutos."),
]
cards = "".join(f'<a class="card" href="{h}"><span class="tag">{esc(tg)}</span><h3>{esc(t)}</h3><p>{esc(d)}</p></a>'
                for h, tg, t, d in CARDS if h in gen)
fcards = "".join(f'<a class="card" href="{esc(f["page"])}"><span class="tag">Parte {f["order"]}</span><h3>{esc(f["title"])}</h3><p>{esc(f["tldr"])}</p></a>'
                 for f in sorted(fi, key=lambda x: x["order"]))
AUXL = {"review": "Code Reviews", "design-system": "Design System", "diagram": "Diagramas adicionais"}
aux_html = ""
for cat, lab in AUXL.items():
    items = [a for a in aux if a["category"] == cat and not a["producer"].startswith("reversa-docs")]
    if items:
        aux_html += f"<section><h2>{lab}</h2><div class='cards'>" + "".join(
            f'<a class="card" href="../{esc(a["path"])}"><span class="tag">{esc(a["producer"])}</span><h3>{esc(a["title"])}</h3><p>{esc(a["path"])}</p></a>' for a in items) + "</div></section>"
br = lambda n: f"{n:,}".replace(",", ".")
payload_i = f"""
<section class="hero">
  <div class="hero-seal" aria-hidden="true">{seal_svg}</div>
  <div>
    <h2>afla-nfes</h2>
    <p class="lede">Arquiva no OneDrive, sem ação manual, as notas fiscais e os boletos que chegam por e-mail às caixas do financeiro, cada documento com o nome certo e na pasta do seu vencimento.</p>
  </div>
</section>

<section class="kpis">
  <div class="kpi"><strong>30 min</strong><span>entre uma verificação e outra</span></div>
  <div class="kpi"><strong>0</strong><span>e-mails alterados e documentos apagados</span></div>
  <div class="kpi"><strong>{M.get("tests", 0)}</strong><span>testes automáticos</span></div>
  <div class="kpi"><strong>7 dias</strong><span>do plano à operação</span></div>
</section>

<section class="callout">
  <h3>Por onde começar</h3>
  <p>Para uma visão rápida, abra a <a href="deck.html">apresentação</a>. Para entender como o documento percorre o sistema, veja a <a href="arquitetura.html">arquitetura</a>. Termos desconhecidos estão no <a href="glossario.html">glossário</a>, e cada parte do sistema tem sua página em <a href="#funcionalidades">funcionalidades</a>.</p>
</section>

<section>
  <h2>Páginas</h2>
  <div class="cards">{cards}</div>
</section>

<section id="funcionalidades">
  <h2>Funcionalidades</h2>
  <p class="muted prose">As quatro partes do sistema, na ordem em que um documento passa por elas.</p>
  <div class="cards">{fcards}</div>
</section>
{aux_html}
<p class="small muted">Mini-site gerado a partir do código em <code>src/</code>, das especificações em <code>_reversa_sdd/</code> e do histórico do repositório. Selo gerado da semente <code>{seed_hex[:8]}</code>.</p>
"""
render(rel="index.html", page_id="index", title="Visão geral", payload=payload_i, category="index",
       agent="reversa-docs-publisher", template="index", source_md="README.md")

# injeção em todas as páginas (inclusive index e placeholder)
all_pages = sorted(p for p in DOCS.rglob("*.html") if not any(part.startswith(".backup") for part in p.parts))
for p in all_pages:
    inject(p, len(p.relative_to(DOCS).parts) - 1)

# ---------------------------------------------------------------- 7. links
broken = []
for p in all_pages:
    t = p.read_text(encoding="utf-8")
    for href in re.findall(r'(?:href|src)="([^"#][^"]*)"', t):
        if re.match(r"^(https?:|mailto:|data:)", href):
            continue
        target = (p.parent / href.split("#")[0]).resolve()
        if not target.exists():
            broken.append({"from": p.relative_to(DOCS).as_posix(), "href": href, "expected_path": str(target)})

# ---------------------------------------------------------------- 9. smoke test
errors = []
srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(DOCS)))
srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}/"
pages_all = [p.relative_to(DOCS).as_posix() for p in all_pages]
for page in pages_all:
    try:
        html_ = urllib.request.urlopen(base + page, timeout=10).read().decode("utf-8")
    except Exception as e:
        errors.append({"page": page, "kind": "http", "detail": str(e)}); continue
    for src in re.findall(r'<script src="([^"]+)"', html_):
        if src.startswith("http"):
            errors.append({"page": page, "kind": "cdn", "detail": src}); continue
        url = urllib.parse.urljoin(base + page, src)
        try:
            urllib.request.urlopen(url, timeout=10).read()
        except Exception as e:
            errors.append({"page": page, "kind": "asset", "detail": f"{src}: {e}"})
    for pat in ("is not defined", "Failed to fetch", "Erro ao carregar", "Access to fetch", "NetworkError", "fetch("):
        if pat in html_:
            errors.append({"page": page, "kind": "pattern", "detail": pat})
    for mk in ("<!-- NAV_LINKS -->", "<!-- MINI_SEAL_SVG -->", "<!-- PAYLOAD -->", "<!-- TITLE -->"):
        if mk in html_:
            errors.append({"page": page, "kind": "marker", "detail": mk})
srv.shutdown()

# ---------------------------------------------------------------- 10. telemetria
for rel in ["index.html"] + (["topologia.html"] if (DOCS / "topologia.html").exists() else []):
    st["pages"][rel] = {"status": "placeholder" if rel == "topologia.html" else "created",
                        "agent": "reversa-docs-publisher", "hash": sha(DOCS / rel)}
for rel in st["pagesGenerated"]:
    st["pages"][rel]["hash"] = sha(DOCS / rel)
if "publisher" not in st["completedAgents"]:
    st["completedAgents"].append("publisher")
st["pendingAgents"] = []
start = int((Path(__file__).parent / "start").read_text() if (Path(__file__).parent / "start").exists() else str(int(time.time())))
st.update({
    "pipelineDurationMs": int((time.time() - start) * 1000),
    "pagesOmitted": st["pagesOmitted"],
    "placeholders": ["topologia.html"] if (DOCS / "topologia.html").exists() else [],
    "auxiliaryHtmls": aux, "auxiliaryHtmlsDiscovered": len(aux), "auxiliaryDiscoveryAborted": aborted,
    "cdnFallbackUsed": True,
    "cdnFallbackDetails": [{"lib": l, "primary": f"https://code.highcharts.com/11.4.8/{p}",
                            "used": f"https://cdn.jsdelivr.net/npm/highcharts@11.4.8/{p}"}
                           for l, p in [("highcharts", "highcharts.js")] + [(f"highcharts_{m}", f"modules/{m}.js") for m in
                                                                          ("accessibility", "exporting", "treemap", "sankey", "timeline")]],
    "vendorMissing": [], "sealPattern": pattern,
    "smokeTestFailed": bool(errors), "smokeTestErrors": errors, "brokenLinks": broken,
})
save_state(st)
print(json.dumps({"pattern": pattern, "pages": pages_all, "aux": len(aux), "broken": broken, "errors": errors,
                  "durMs": st["pipelineDurationMs"]}, ensure_ascii=False, indent=1))
