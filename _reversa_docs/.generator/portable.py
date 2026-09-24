"""Portable: empacota o mini-site num único HTML que abre por duplo clique, sem servidor nem rede.

Cada página vira um documento guardado em JSON dentro do próprio arquivo. A casca exibe a página pedida
num iframe srcdoc, montado na hora com o CSS, o JS e as bibliotecas embutidos (cada recurso guardado uma
só vez). Links entre páginas viram rotas na âncora (#/arquitetura.html), então voltar e avançar funcionam
e cada página tem endereço próprio. Links para fora do mini-site apontam para o repositório no GitHub.
"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from rvlib import *  # noqa: F401,F403
import base64
import posixpath
import re

OUT = DOCS / f"{PROJECT}-documentacao.html"
REPO = "https://github.com/iago-leal/email-nf-onedrive/blob/main/"

LINK_CSS = re.compile(r'<link rel="stylesheet" href="([^"]+)">')
LINK_ICON = re.compile(r'\s*<link rel="icon"[^>]*>')
SCRIPT_SRC = re.compile(r'<script src="([^"]+)"></script>')
HREF = re.compile(r'href="([^"#:]+\.md)"')


def rel_of(page, ref):
    """Resolve ref relativo à página; devolve o caminho a partir da raiz do mini-site."""
    return posixpath.normpath(posixpath.join(posixpath.dirname(page), ref))


def to_json(obj):
    # "</" e "<!--" não podem aparecer dentro de <script>, nem mesmo em JSON
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s.replace("</", "<\\/").replace("<!--", "<\\u0021--")


pages = sorted(p.relative_to(DOCS).as_posix() for p in DOCS.rglob("*.html")
               if not any(part.startswith(".") for part in p.relative_to(DOCS).parts) and p != OUT)
assets, bundle = {}, {}


def asset(page, ref, kind):
    key = rel_of(page, ref)
    text = (DOCS / key).read_text(encoding="utf-8")
    if re.search(r"</(script|style)|<!--", text, re.I):
        sys.exit(f"ERRO: {key} contém sequência que quebraria o HTML embutido")
    assets[key] = text
    return f"@@RV:{kind}:{key}@@"


def outside(page, ref):
    key = rel_of(page, ref)
    if not key.startswith("../"):
        return f'href="{ref}"'
    return f'href="{REPO}{key[3:]}" target="_blank" rel="noopener"'


for page in pages:
    t = (DOCS / page).read_text(encoding="utf-8")
    t = LINK_ICON.sub("", t)
    t = LINK_CSS.sub(lambda m: asset(page, m.group(1), "css"), t)
    t = SCRIPT_SRC.sub(lambda m: asset(page, m.group(1), "js"), t)
    t = HREF.sub(lambda m: outside(page, m.group(1)), t)
    t = t.replace("<head>", "<head>\n    @@RV:boot@@", 1)
    left = re.findall(r'(?:src|href)="((?!https?:|#|data:)[^"]*\.(?:css|js|svg|png|jpg))"', t)
    if left:
        sys.exit(f"ERRO: {page} ainda referencia arquivos externos: {left}")
    bundle[page] = t

# Script injetado no início de cada página, antes de qualquer outro. Um srcdoc resolve URLs relativas
# contra o endereço da casca, então âncoras e history.replaceState precisam ser redirecionados para
# about:srcdoc, e os links entre páginas passam para a casca.
BOOT = r"""
(function () {
  "use strict";
  var P = window.parent, H = window.history;
  function sync() { try { P.RV_SYNC(RV_CUR, location.hash.slice(1)); } catch (e) {} }
  ["replaceState", "pushState"].forEach(function (m) {
    var orig = H[m];
    H[m] = function (s, t, u) {
      if (typeof u === "string" && u.charAt(0) === "#") u = "about:srcdoc" + u;
      var r = orig.call(H, s, t, u);
      sync();
      return r;
    };
  });
  if (RV_FRAG) H.replaceState(null, "", "#" + RV_FRAG);
  window.addEventListener("hashchange", sync);
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a[href]");
    if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
    var href = a.getAttribute("href");
    if (!href || a.hasAttribute("download")) return;
    if (/^[a-z][a-z0-9+.-]*:/i.test(href)) {
      if (/^https?:/i.test(href) && !a.target) { a.target = "_blank"; a.rel = "noopener"; }
      return;
    }
    e.preventDefault();
    if (href.charAt(0) === "#") location.hash = href.slice(1);
    else P.RV_GO(href, RV_CUR);
  });
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".reversa-doc-nav a[href]").forEach(function (a) {
      var r = P.RV_RESOLVE(a.getAttribute("href"), RV_CUR);
      if (r.path === RV_CUR && !r.frag) { a.classList.add("is-active"); a.setAttribute("aria-current", "page"); }
    });
  });
})();
"""

SHELL = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="reversa-portable" content="__GENERATED__">
<title>__PROJECT__ | Documentação</title>
<link rel="icon" type="image/svg+xml" href="__ICON__">
<style>
  html, body { margin: 0; height: 100%; background: #f5f3ee; overflow: hidden; }
  #rv-frame { display: block; width: 100%; height: 100%; border: 0; }
  .rv-msg { font: 15px/1.5 system-ui, sans-serif; color: #1e2937; max-width: 36rem; margin: 15vh auto; padding: 0 16px; }
</style>
</head>
<body>
<noscript><p class="rv-msg">Esta documentação precisa de JavaScript habilitado para ser exibida.</p></noscript>
<script type="application/json" id="rv-pages">__PAGES__</script>
<script type="application/json" id="rv-assets">__ASSETS__</script>
<script>
(function () {
  "use strict";
  var PAGES = JSON.parse(document.getElementById("rv-pages").textContent);
  var ASSETS = JSON.parse(document.getElementById("rv-assets").textContent);
  var BOOT = __BOOT__;
  var ENTRY = "index.html", current = null;

  function resolve(href, from) {
    var u = new URL(href, "http://rv.local/" + (from || ENTRY));
    var path = decodeURIComponent(u.pathname.slice(1)) || ENTRY;
    if (path.slice(-1) === "/") path += ENTRY;
    return { path: path, frag: decodeURIComponent(u.hash.slice(1)) };
  }

  function route() {
    var h = location.hash.replace(/^#\/?/, ""), i = h.indexOf("#");
    var path = (i < 0 ? h : h.slice(0, i)) || ENTRY;
    return { path: PAGES[path] ? path : ENTRY, frag: i < 0 ? "" : h.slice(i + 1) };
  }

  function build(path, frag) {
    var boot = "<script>var RV_CUR = " + JSON.stringify(path) + ", RV_FRAG = " + JSON.stringify(frag) +
               ";" + BOOT + "<\/script>";
    return PAGES[path].replace(/@@RV:(css|js|boot):?([^@]*)@@/g, function (m, kind, key) {
      if (kind === "boot") return boot;
      if (kind === "css") return "<style>\n" + ASSETS[key] + "\n</style>";
      return "<script>\n" + ASSETS[key] + "\n<\/script>";
    });
  }

  function frame() { return document.getElementById("rv-frame"); }

  function scrollTo(frag) {
    var f = frame(), doc = f && f.contentDocument, el = doc && frag && doc.getElementById(frag);
    if (el) el.scrollIntoView({ block: "start" });
  }

  function render(path, frag) {
    current = path;
    var f = document.createElement("iframe");
    f.id = "rv-frame";
    f.title = "Documentação";
    f.setAttribute("allow", "fullscreen");
    f.srcdoc = build(path, frag);
    f.addEventListener("load", function () {
      try { document.title = f.contentDocument.title || document.title; } catch (e) {}
      if (frag) scrollTo(frag);
      f.contentWindow.focus();
    });
    var old = frame();
    if (old) old.replaceWith(f); else document.body.appendChild(f);
  }

  function url(path, frag) { return "#/" + path + (frag ? "#" + frag : ""); }

  window.RV_RESOLVE = resolve;
  window.RV_GO = function (href, from) {
    var r = resolve(href, from);
    if (!PAGES[r.path]) return;
    if (r.path === current) {
      history.pushState(null, "", url(r.path, r.frag));
      if (r.frag) scrollTo(r.frag); else frame().contentWindow.scrollTo(0, 0);
    } else {
      location.hash = url(r.path, r.frag);
    }
  };
  window.RV_SYNC = function (path, frag) {
    if (path === current) history.replaceState(null, "", url(path, frag));
  };

  window.addEventListener("hashchange", function () {
    var r = route();
    if (r.path !== current) render(r.path, r.frag);
    else if (r.frag) scrollTo(r.frag);
  });
  var r = route();
  render(r.path, r.frag);
})();
</script>
</body>
</html>
"""

icon = "data:image/svg+xml;base64," + base64.b64encode((DOCS / "assets/img/seal-mini.svg").read_bytes()).decode()
vals = {"GENERATED": now_iso(), "PROJECT": PROJECT, "ICON": icon,
        "BOOT": to_json(BOOT), "ASSETS": to_json(assets), "PAGES": to_json(bundle)}
out = re.sub(r"__([A-Z]+)__", lambda m: vals[m.group(1)], SHELL)
OUT.write_text(out, encoding="utf-8")
kb = OUT.stat().st_size / 1024
print(f"OK: {OUT.relative_to(ROOT)} ({kb:,.0f} KB, {len(bundle)} páginas, {len(assets)} recursos)")
