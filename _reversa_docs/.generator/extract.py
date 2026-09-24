#!/usr/bin/env python3
"""Extrai modules.json e deps.json de src/email_nf_onedrive com imports reais (AST)."""
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

import ast
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = "email_nf_onedrive"
SRC = ROOT / "src" / PKG
OUT = ROOT / "_reversa_docs" / "assets" / "data"
NOW = datetime.now(timezone.utc).isoformat()

# Rótulos legíveis para leitor não técnico
AREA = {
    ".": "Núcleo",
    "autorizacao": "Autorização (OAuth)",
    "coleta": "Coleta de e-mail",
    "configuracao": "Configuração",
    "envio": "Envio ao OneDrive",
    "execucao": "Execução e avisos",
    "registro": "Registro (banco)",
}


def complexity(tree):
    n = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.IfExp, ast.ExceptHandler,
                             ast.With, ast.Assert, ast.comprehension, ast.Match)):
            n += 1
        elif isinstance(node, ast.BoolOp):
            n += len(node.values) - 1
    return n


def modname(path: Path) -> str:
    rel = path.relative_to(SRC.parent).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


files = sorted(SRC.rglob("*.py"))
by_mod = {}
modules = []
for f in files:
    text = f.read_text(encoding="utf-8")
    tree = ast.parse(text)
    loc = sum(1 for l in text.splitlines() if l.strip())
    folder_rel = f.parent.relative_to(SRC).as_posix()
    area_key = folder_rel.split("/")[0] if folder_rel != "." else "."
    funcs = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree))
    classes = sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
    doc = (ast.get_docstring(tree) or "").strip().split("\n")[0][:160]
    mid = f.relative_to(ROOT).as_posix()
    m = {
        "id": mid,
        "name": f.stem,
        "module": modname(f),
        "folder": f.parent.relative_to(ROOT).as_posix(),
        "area": area_key,
        "areaLabel": AREA.get(area_key, area_key),
        "loc": loc,
        "language": "python",
        "complexity": complexity(tree),
        "functions": funcs,
        "classes": classes,
        "type": "package" if f.name == "__init__.py" else "module",
        "doc": doc,
    }
    modules.append(m)
    by_mod[m["module"]] = (m, f, tree)

# SQL do esquema também conta como artefato do pacote
sql = SRC / "registro" / "esquema.sql"
if sql.exists():
    t = sql.read_text(encoding="utf-8")
    modules.append({
        "id": sql.relative_to(ROOT).as_posix(), "name": "esquema", "module": f"{PKG}.registro.esquema.sql",
        "folder": sql.parent.relative_to(ROOT).as_posix(), "area": "registro", "areaLabel": AREA["registro"],
        "loc": sum(1 for l in t.splitlines() if l.strip()), "language": "sql", "complexity": 1,
        "functions": 0, "classes": 0, "type": "schema", "doc": "Esquema SQLite do registro de documentos",
    })


def resolve(base_mod, is_pkg, node):
    """Devolve lista de módulos internos importados por um nó Import/ImportFrom."""
    out = []
    if isinstance(node, ast.Import):
        for a in node.names:
            if a.name.startswith(PKG):
                out.append(a.name)
        return out
    if node.level:
        parts = base_mod.split(".")
        if not is_pkg:
            parts = parts[:-1]
        parts = parts[: len(parts) - (node.level - 1)]
        prefix = ".".join(parts)
        target = f"{prefix}.{node.module}" if node.module else prefix
    else:
        target = node.module or ""
    if not target.startswith(PKG):
        return out
    for a in node.names:
        cand = f"{target}.{a.name}"
        out.append(cand if cand in by_mod else target)
    return out


edges = defaultdict(int)
for mname, (m, f, tree) in by_mod.items():
    is_pkg = f.name == "__init__.py"
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for t in resolve(mname, is_pkg, node):
                while t not in by_mod and "." in t:
                    t = t.rsplit(".", 1)[0]
                if t in by_mod and t != mname:
                    edges[(m["id"], by_mod[t][0]["id"])] += 1

# Ciclos (Tarjan, SCC > 1)
graph = defaultdict(list)
for (a, b) in edges:
    graph[a].append(b)
idx, low, st, on, sccs, counter = {}, {}, [], set(), [], [0]


def strong(v):
    idx[v] = low[v] = counter[0]; counter[0] += 1
    st.append(v); on.add(v)
    for w in graph[v]:
        if w not in idx:
            strong(w); low[v] = min(low[v], low[w])
        elif w in on:
            low[v] = min(low[v], idx[w])
    if low[v] == idx[v]:
        comp = []
        while True:
            w = st.pop(); on.discard(w); comp.append(w)
            if w == v:
                break
        if len(comp) > 1:
            sccs.append(sorted(comp))


sys.setrecursionlimit(10000)
for m in modules:
    if m["id"] not in idx:
        strong(m["id"])

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "modules.json").write_text(json.dumps({
    "schemaVersion": 1, "generatedAt": NOW, "rootPath": ".", "areas": AREA, "modules": modules,
}, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "deps.json").write_text(json.dumps({
    "schemaVersion": 1, "generatedAt": NOW,
    "nodes": [{"id": m["id"]} for m in modules],
    "edges": [{"source": a, "target": b, "weight": w} for (a, b), w in sorted(edges.items())],
    "cycles": sccs,
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"OK: {len(modules)} modulos, {len(edges)} arestas, {len(sccs)} ciclos, LOC={sum(m['loc'] for m in modules)}")
