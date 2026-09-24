"""Utilidades comuns aos agentes do Time Reversa Docs para o projeto afla-nfes."""
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "_reversa_docs"
DATA = DOCS / "assets" / "data"
TPL = Path.home() / ".npm/_npx/07b8d2051a3f1121/node_modules/reversa/templates/documentation/viewer.html"
PROJECT = "afla-nfes"
CONFIG = json.loads((DOCS / ".config.json").read_text(encoding="utf-8"))
STATE_PATH = DOCS / ".state.json"

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def label_pt(iso):
    d = datetime.fromisoformat(iso).astimezone()
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}, {d:%H:%M}"


def esc(s):
    return html.escape(str(s), quote=True)


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def dump(name, obj):
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def render(*, rel, page_id, title, payload, agent, template, category="diagram",
           sidebar="", head_extras="", scripts="", source_md="", depth=0):
    """Aplica o chassi viewer.html. NAV_LINKS e MINI_SEAL_SVG ficam para o Publisher."""
    up = "../" * depth
    t = TPL.read_text(encoding="utf-8")
    gen = now_iso()
    rep = {
        "<!-- TITLE -->": esc(title),
        "<!-- PROJECT_NAME -->": PROJECT,
        "<!-- REVERSA_CATEGORY -->": category,
        "<!-- REVERSA_TEMPLATE -->": template,
        "<!-- REVERSA_SOURCE_MD -->": esc(source_md),
        "<!-- REVERSA_PRODUCER_AGENT -->": agent,
        "<!-- GENERATED_AT_LABEL -->": label_pt(gen),
        "<!-- GENERATED_AT -->": gen,
        "<!-- VISUAL_STYLE -->": CONFIG["interview"]["visualStyle"],
        "<!-- PAGE_ID -->": page_id,
        "<!-- HEAD_EXTRAS -->": '<link rel="stylesheet" href="assets/css/site.css">\n    ' + head_extras,
        "<!-- PAYLOAD -->": payload,
        "<!-- SCRIPTS -->": scripts,
    }
    for k, v in rep.items():
        t = t.replace(k, v)
    # Sidebar vazia precisa ficar realmente vazia para :empty funcionar
    if sidebar:
        t = t.replace("<!-- SIDEBAR -->", sidebar)
    else:
        t = t.replace("\n        <!-- SIDEBAR -->\n    ", "")
    if not source_md:
        t = t.replace('        <span class="reversa-doc-footer-sep" aria-hidden="true">·</span>\n'
                      '        <a href="" class="reversa-doc-source-link">Fonte em markdown</a>\n', "")
    else:
        t = t.replace('>Fonte em markdown</a>', '>Fonte: ' + esc(source_md) + '</a>')
        t = t.replace('href="' + esc(source_md) + '"', 'href="' + up + "../" + esc(source_md) + '"')
    if depth:
        for a in ('href="assets/', 'src="assets/', 'href="index.html"'):
            t = t.replace(a, a.replace('"', '"' + up, 1))
    out = DOCS / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(t, encoding="utf-8")
    return out


def sha(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"schemaVersion": 1, "startedAt": now_iso(), "completedAgents": [],
            "pendingAgents": ["mapper", "analyst", "storyteller", "publisher"],
            "pages": {}, "pagesGenerated": [], "pagesOmitted": []}


def save_state(st):
    st["lastCheckpoint"] = now_iso()
    STATE_PATH.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def register(st, agent_short, agent_full, rels, omitted=()):
    for rel in rels:
        st["pages"][rel] = {"status": "created", "agent": agent_full, "hash": sha(DOCS / rel)}
        if rel not in st["pagesGenerated"]:
            st["pagesGenerated"].append(rel)
    for o in omitted:
        if all(x["page"] != o["page"] for x in st["pagesOmitted"]):
            st["pagesOmitted"].append(o)
    if agent_short not in st["completedAgents"]:
        st["completedAgents"].append(agent_short)
    if agent_short in st["pendingAgents"]:
        st["pendingAgents"].remove(agent_short)
    save_state(st)
