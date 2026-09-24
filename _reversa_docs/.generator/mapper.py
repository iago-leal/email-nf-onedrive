"""Mapper: arquitetura.html (Code City 3D) e modulos.html (mapa 2D)."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from rvlib import *  # noqa: F401,F403

mods = load("modules.json")
deps = load("deps.json")
n_mod = sum(1 for m in mods["modules"] if m["loc"] > 0)
loc = sum(m["loc"] for m in mods["modules"])

AREA_COLORS = {
    ".": "#6b7280", "configuracao": "#c28f2c", "autorizacao": "#8e6c8a", "coleta": "#3f7cac",
    "registro": "#5b5ea6", "envio": "#2f8f6b", "execucao": "#b5543c",
}
AREA_ORDER = ["configuracao", "autorizacao", "coleta", "registro", "envio", "execucao", "."]
areas_js = json.dumps([{"key": k, "label": mods["areas"][k], "color": AREA_COLORS[k]} for k in AREA_ORDER],
                      ensure_ascii=False)
legend = "".join(f'<li><span class="swatch" style="background:{AREA_COLORS[k]}"></span>{esc(mods["areas"][k])}</li>'
                 for k in AREA_ORDER)

# ---------------------------------------------------------------- arquitetura
flow = [
    ("configuracao", "Ler a configuração", "Descobre quais caixas de e-mail acompanhar e para qual pasta do OneDrive vai o documento de cada empresa."),
    ("coleta", "Ler os e-mails", "Abre cada caixa em modo somente leitura e separa os anexos PDF e XML, inclusive de mensagens encaminhadas."),
    ("coleta", "Classificar", "Decide se o anexo é nota fiscal ou boleto. O que não for reconhecido fica retido para revisão humana."),
    ("registro", "Evitar repetição", "Consulta o registro local: o que já foi arquivado não é enviado de novo."),
    ("envio", "Arquivar no OneDrive", "Dá ao arquivo o nome padrão da pasta, escolhe a subpasta pelo vencimento e envia, sem nunca apagar nem sobrescrever."),
    ("execucao", "Avisar e registrar", "Grava o log do dia, atualiza o sumário LEIAME e avisa o operador pelo Telegram quando algo falha."),
]
flow_html = "".join(f'<li style="--area-color:{AREA_COLORS[a]}"><b>{esc(t)}</b>{esc(d)}</li>' for a, t, d in flow)

payload_arq = f"""
<p class="lede">O <b>afla-nfes</b> é um programa que roda sozinho a cada 30 minutos num servidor. Ele lê as caixas de e-mail do financeiro, encontra notas fiscais e boletos e os guarda na pasta de contas a pagar do OneDrive de cada empresa, com o nome certo e sem intervenção manual.</p>

<section>
  <h2>O caminho de um documento</h2>
  <ol class="flow">{flow_html}</ol>
</section>

<section class="callout">
  <h3>Três garantias de projeto</h3>
  <ul>
    <li><b>Os e-mails ficam intactos.</b> Nada é marcado como lido, movido, apagado ou respondido.</li>
    <li><b>O OneDrive só recebe, nunca perde.</b> Um nome já ocupado ganha sufixo <code>_2</code>, <code>_3</code>; nenhum arquivo existente é apagado ou substituído.</li>
    <li><b>Senhas não aparecem.</b> Credenciais são mascaradas no log, nos avisos e no terminal.</li>
  </ul>
</section>

<section>
  <h2>A cidade do código</h2>
  <p class="muted prose">Cada prédio é um arquivo do programa. Os bairros agrupam os arquivos pela etapa de que cuidam; a altura mostra o tamanho do arquivo (linhas de código) e o tom, do claro ao escuro, indica quantos caminhos de decisão ele contém. Arraste para girar, use a roda do mouse para aproximar e passe o cursor sobre um prédio para ver o que ele faz.</p>
  <div class="stage" id="city-stage">
    <div class="loader" id="city-loader">Montando a cidade do código...</div>
    <div class="tooltip" id="city-tip"></div>
  </div>
  <ul class="legend" style="margin-top:12px">{legend}</ul>
</section>

<section class="kpis">
  <div class="kpi"><strong>{n_mod}</strong><span>arquivos com código</span></div>
  <div class="kpi"><strong>{loc:,}</strong><span>linhas de código</span></div>
  <div class="kpi"><strong>7</strong><span>bairros (etapas e núcleo)</span></div>
  <div class="kpi"><strong>{len(deps["edges"])}</strong><span>ligações internas</span></div>
</section>
"""
payload_arq = payload_arq.replace(f"{loc:,}", f"{loc:,}".replace(",", "."))

sidebar_arq = """
<div class="sidebar-group">
  <h3>Ajustes da cidade</h3>
  <label>Altura dos prédios
    <input type="range" min="0.3" max="3" step="0.1" value="1" data-param="heightScale" data-default="1">
  </label>
  <label>Intensidade da luz
    <input type="range" min="0.2" max="2" step="0.1" value="1" data-param="light" data-default="1">
  </label>
  <label class="check"><input type="checkbox" data-param="rotate" data-default="true" checked> Girar sozinha</label>
</div>
<p class="small muted">Os ajustes ficam guardados neste navegador.</p>
"""

scripts_arq = """<script>
(function () {
  "use strict";
  var AREAS = %AREAS%;
  var stage = document.getElementById("city-stage");
  var loader = document.getElementById("city-loader");
  var tip = document.getElementById("city-tip");
  if (!window.THREE || !window.RV_DATA || !window.RV_DATA.modules || !window.RV_DATA.modules.modules) {
    loader.textContent = "Biblioteca 3D ou dados indisponíveis. Abra novamente após o Publisher gerar assets/js/data.js.";
    return;
  }
  var mods = window.RV_DATA.modules.modules.filter(function (m) { return m.loc > 0; });
  var colorOf = {}; AREAS.forEach(function (a) { colorOf[a.key] = a.color; });
  var maxC = Math.max.apply(null, mods.map(function (m) { return m.complexity; }));

  var W = stage.clientWidth, H = stage.clientHeight;
  var renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(W, H);
  stage.appendChild(renderer.domElement);
  var scene = new THREE.Scene();
  scene.background = new THREE.Color(getComputedStyle(document.body).getPropertyValue("--reversa-surface").trim() || "#ffffff");
  var camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 2000);
  camera.position.set(60, 70, 90);
  var controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.6;
  var hemi = new THREE.HemisphereLight(0xffffff, 0x8a8577, 0.7);
  var dir = new THREE.DirectionalLight(0xffffff, 0.8);
  dir.position.set(40, 80, 30);
  scene.add(hemi, dir);

  // Bairros em grade 4 x 2, prédios em grade dentro de cada bairro
  var GAP = 4, CELL = 5, buildings = [];
  var cols = 4, district = 0, offsets = [];
  var groups = AREAS.map(function (a) {
    return { area: a, items: mods.filter(function (m) { return m.area === a.key; }).sort(function (x, y) { return y.loc - x.loc; }) };
  }).filter(function (g) { return g.items.length; });
  var sizes = groups.map(function (g) { return Math.ceil(Math.sqrt(g.items.length)); });
  var dSize = Math.max.apply(null, sizes) * CELL + 2;
  groups.forEach(function (g, gi) {
    var gx = (gi % cols) * (dSize + GAP), gz = Math.floor(gi / cols) * (dSize + GAP);
    var ground = new THREE.Mesh(new THREE.BoxGeometry(dSize, 0.4, dSize),
      new THREE.MeshLambertMaterial({ color: new THREE.Color(g.area.color).lerp(new THREE.Color(0xffffff), 0.72) }));
    ground.position.set(gx + dSize / 2, -0.2, gz + dSize / 2);
    scene.add(ground);
    var side = sizes[gi];
    g.items.forEach(function (m, i) {
      var h = Math.max(0.6, m.loc / 6);
      var t = 0.25 + 0.75 * (m.complexity / maxC);
      var col = new THREE.Color(0xf2f0ea).lerp(new THREE.Color(g.area.color), t);
      var foot = 2.4 + Math.min(1.4, m.functions / 10);
      var mesh = new THREE.Mesh(new THREE.BoxGeometry(foot, 1, foot), new THREE.MeshLambertMaterial({ color: col }));
      mesh.userData = { m: m, h: h, base: col.clone() };
      mesh.scale.y = h;
      mesh.position.set(gx + 1 + CELL / 2 + (i % side) * CELL, h / 2, gz + 1 + CELL / 2 + Math.floor(i / side) * CELL);
      scene.add(mesh);
      buildings.push(mesh);
    });
  });
  var cx = (Math.min(cols, groups.length) * (dSize + GAP) - GAP) / 2;
  var cz = (Math.ceil(groups.length / cols) * (dSize + GAP) - GAP) / 2;
  controls.target.set(cx, 6, cz);
  camera.position.set(cx + 55, 60, cz + 70);
  loader.remove();

  function setHeight(k) {
    buildings.forEach(function (b) { b.scale.y = b.userData.h * k; b.position.y = b.userData.h * k / 2; });
  }
  document.addEventListener("reversa:param-change", function (e) {
    var d = e.detail || {};
    if (d.param === "heightScale") setHeight(+d.value);
    if (d.param === "light") { dir.intensity = 0.8 * d.value; hemi.intensity = 0.7 * d.value; }
    if (d.param === "rotate") controls.autoRotate = !!d.value;
  });
  document.querySelectorAll(".reversa-doc-sidebar [data-param]").forEach(function (c) {
    var v = c.type === "checkbox" ? c.checked : +c.value;
    document.dispatchEvent(new CustomEvent("reversa:param-change", { detail: { param: c.dataset.param, value: v } }));
  });

  var ray = new THREE.Raycaster(), mouse = new THREE.Vector2(), hovered = null;
  renderer.domElement.addEventListener("mousemove", function (ev) {
    var r = renderer.domElement.getBoundingClientRect();
    mouse.x = ((ev.clientX - r.left) / r.width) * 2 - 1;
    mouse.y = -((ev.clientY - r.top) / r.height) * 2 + 1;
    ray.setFromCamera(mouse, camera);
    var hit = ray.intersectObjects(buildings)[0];
    if (hovered && (!hit || hit.object !== hovered)) { hovered.material.color.copy(hovered.userData.base); hovered = null; }
    if (hit) {
      hovered = hit.object;
      hovered.material.color.set(0x1e2937);
      var m = hovered.userData.m;
      var area = AREAS.filter(function (a) { return a.key === m.area; })[0];
      tip.innerHTML = "<b>" + m.name + ".py</b>" + (area ? area.label : "") + " &middot; " + m.loc + " linhas" +
        (m.doc ? "<br>" + m.doc.replace(/</g, "&lt;") : "");
      tip.style.left = Math.min(ev.clientX - r.left + 14, r.width - 330) + "px";
      tip.style.top = (ev.clientY - r.top + 14) + "px";
      tip.style.opacity = 1;
    } else tip.style.opacity = 0;
  });
  renderer.domElement.addEventListener("mouseleave", function () { tip.style.opacity = 0; });
  window.addEventListener("resize", function () {
    W = stage.clientWidth; H = stage.clientHeight;
    renderer.setSize(W, H); camera.aspect = W / H; camera.updateProjectionMatrix();
  });
  (function loop() { requestAnimationFrame(loop); controls.update(); renderer.render(scene, camera); })();
})();
</script>""".replace("%AREAS%", areas_js)

render(rel="arquitetura.html", page_id="arquitetura", title="Arquitetura", payload=payload_arq,
       agent="reversa-docs-mapper", template="arquitetura", sidebar=sidebar_arq,
       head_extras='<script src="assets/vendor/three.min.js"></script>\n    <script src="assets/vendor/OrbitControls.js"></script>',
       scripts=scripts_arq, source_md="README.md")

# ---------------------------------------------------------------- modulos
checks = "".join(f'<label class="check"><input type="checkbox" class="area-filter" value="{k}" checked>'
                 f'<span class="swatch" style="background:{AREA_COLORS[k]}"></span>{esc(mods["areas"][k])}</label>'
                 for k in AREA_ORDER)
payload_mod = f"""
<p class="lede">Os arquivos do programa conversam entre si. Neste mapa, cada círculo é um arquivo e cada linha indica que um deles usa o outro. Círculos maiores têm mais código; a cor mostra a etapa a que o arquivo pertence.</p>

<section>
  <div class="stage" id="graph-stage">
    <svg id="d3-canvas" aria-label="Mapa de módulos"></svg>
    <div class="tooltip" id="graph-tip"></div>
  </div>
  <ul class="legend" style="margin-top:12px">{legend}</ul>
</section>

<section class="callout">
  <h3>O que o mapa revela</h3>
  <ul>
    <li><b>Um centro de comando.</b> O arquivo <code>ciclo.py</code>, na etapa de execução, chama as demais etapas na ordem certa; é o maestro do processo.</li>
    <li><b>Regras compartilhadas.</b> A coleta já calcula o nome e o vencimento de cada documento com as regras que moram na etapa de envio; o envio, por sua vez, recebe os anexos no formato que a coleta define. As duas etapas andam juntas por desenho.</li>
    <li><b>Nenhuma dependência circular.</b> Não há arquivos que dependam uns dos outros em círculo, sinal de organização saudável.</li>
  </ul>
</section>

<section>
  <h2>Arquivos por etapa</h2>
  <div class="table-wrap"><table class="data" id="mod-table">
    <thead><tr><th>Arquivo</th><th>Etapa</th><th>O que faz</th><th class="num">Linhas</th><th class="num">Usa</th><th class="num">É usado por</th></tr></thead>
    <tbody></tbody>
  </table></div>
</section>
"""
sidebar_mod = f"""
<div class="sidebar-group">
  <h3>Etapas visíveis</h3>
  {checks}
</div>
<div class="sidebar-group">
  <h3>Disposição</h3>
  <label>Força de afastamento
    <input type="range" min="-600" max="-40" step="20" value="-260" data-param="charge" data-default="-260">
  </label>
  <label>Distância entre ligados
    <input type="range" min="30" max="200" step="10" value="80" data-param="distance" data-default="80">
  </label>
  <label class="check"><input type="checkbox" data-param="hideInit" data-default="true" checked> Ocultar arquivos vazios</label>
</div>
"""
scripts_mod = """<script>
(function () {
  "use strict";
  var AREAS = %AREAS%;
  var colorOf = {}, labelOf = {};
  AREAS.forEach(function (a) { colorOf[a.key] = a.color; labelOf[a.key] = a.label; });
  var D = window.RV_DATA || {};
  if (!window.d3 || !D.modules || !D.modules.modules) {
    document.getElementById("graph-stage").insertAdjacentHTML("beforeend", "<div class='loader'>Biblioteca D3 ou dados indisponíveis.</div>");
    return;
  }
  var all = D.modules.modules, edgesAll = D.deps.edges || [];
  var cyc = {}; (D.deps.cycles || []).forEach(function (c) { c.forEach(function (id) { cyc[id] = 1; }); });
  var outDeg = {}, inDeg = {};
  edgesAll.forEach(function (e) { outDeg[e.source] = (outDeg[e.source] || 0) + 1; inDeg[e.target] = (inDeg[e.target] || 0) + 1; });
  function label(m) { return m.name === "__init__" ? m.folder.split("/").pop() + "/__init__" : m.name; }

  // Tabela
  var tb = document.querySelector("#mod-table tbody");
  var order = AREAS.map(function (a) { return a.key; });
  all.filter(function (m) { return m.loc > 0; }).sort(function (a, b) {
    return order.indexOf(a.area) - order.indexOf(b.area) || b.loc - a.loc;
  }).forEach(function (m) {
    var tr = document.createElement("tr");
    tr.innerHTML = "<td><code>" + m.id.replace("src/email_nf_onedrive/", "") + "</code></td><td><span class='swatch' style='background:" +
      colorOf[m.area] + "'></span> " + labelOf[m.area] + "</td><td>" + (m.doc || "").replace(/</g, "&lt;") +
      "</td><td class='num'>" + m.loc + "</td><td class='num'>" + (outDeg[m.id] || 0) + "</td><td class='num'>" + (inDeg[m.id] || 0) + "</td>";
    tb.appendChild(tr);
  });

  var svg = d3.select("#d3-canvas"), stage = document.getElementById("graph-stage"), tip = document.getElementById("graph-tip");
  var W = stage.clientWidth, H = stage.clientHeight;
  svg.attr("viewBox", [0, 0, W, H]);
  var root = svg.append("g");
  svg.call(d3.zoom().scaleExtent([0.3, 4]).on("zoom", function (ev) { root.attr("transform", ev.transform); }));
  svg.append("defs").append("marker").attr("id", "arrow").attr("viewBox", "0 -4 8 8").attr("refX", 8).attr("markerUnits", "userSpaceOnUse").attr("markerWidth", 9)
    .attr("markerHeight", 9).attr("orient", "auto").append("path").attr("d", "M0,-4L8,0L0,4").attr("fill", "#9aa3ad");
  var gLinks = root.append("g"), gNodes = root.append("g");
  var sim = d3.forceSimulation().force("charge", d3.forceManyBody().strength(-260))
    .force("link", d3.forceLink().id(function (d) { return d.id; }).distance(80))
    .force("center", d3.forceCenter(W / 2, H / 2)).force("collide", d3.forceCollide().radius(function (d) { return d.r + 6; }));
  var state = { areas: {}, hideInit: true };
  AREAS.forEach(function (a) { state.areas[a.key] = true; });

  function draw() {
    var nodes = all.filter(function (m) { return state.areas[m.area] && !(state.hideInit && m.loc === 0); })
      .map(function (m) { return Object.assign({}, m, { r: 5 + Math.sqrt(m.loc) * 0.9 }); });
    var ids = {}; nodes.forEach(function (n) { ids[n.id] = 1; });
    var links = edgesAll.filter(function (e) { return ids[e.source] && ids[e.target]; }).map(function (e) { return Object.assign({}, e); });
    var l = gLinks.selectAll("line").data(links).join("line").attr("stroke", "#9aa3ad").attr("stroke-opacity", 0.55)
      .attr("stroke-width", function (d) { return 0.8 + d.weight * 0.5; }).attr("marker-end", "url(#arrow)");
    var n = gNodes.selectAll("g.node").data(nodes, function (d) { return d.id; }).join(function (enter) {
      var g = enter.append("g").attr("class", "node").style("cursor", "grab");
      g.append("circle"); g.append("text").attr("font-size", 11).attr("fill", "currentColor").attr("dy", "0.32em");
      return g;
    });
    n.select("circle").attr("r", function (d) { return d.r; }).attr("fill", function (d) { return cyc[d.id] ? "#d62728" : colorOf[d.area]; })
      .attr("stroke", "#fff").attr("stroke-width", 1.5);
    n.select("text").text(label).attr("x", function (d) { return d.r + 3; });
    n.on("mouseenter", function (ev, d) {
      var near = {}; links.forEach(function (x) { if (x.source.id === d.id) near[x.target.id] = 1; if (x.target.id === d.id) near[x.source.id] = 1; });
      n.style("opacity", function (o) { return o.id === d.id || near[o.id] ? 1 : 0.2; });
      l.style("opacity", function (x) { return x.source.id === d.id || x.target.id === d.id ? 1 : 0.08; });
      var r = stage.getBoundingClientRect();
      tip.innerHTML = "<b>" + d.id.replace("src/email_nf_onedrive/", "") + "</b>" + labelOf[d.area] + " &middot; " + d.loc +
        " linhas &middot; usa " + (outDeg[d.id] || 0) + ", usado por " + (inDeg[d.id] || 0) + (d.doc ? "<br>" + d.doc.replace(/</g, "&lt;") : "");
      tip.style.left = Math.min(ev.clientX - r.left + 14, r.width - 330) + "px"; tip.style.top = (ev.clientY - r.top + 14) + "px"; tip.style.opacity = 1;
    }).on("mouseleave", function () { n.style("opacity", 1); l.style("opacity", 1); tip.style.opacity = 0; })
      .call(d3.drag().on("start", function (ev, d) { if (!ev.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on("drag", function (ev, d) { d.fx = ev.x; d.fy = ev.y; })
        .on("end", function (ev, d) { if (!ev.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));
    sim.nodes(nodes).on("tick", function () {
      l.each(function (d) {
        var dx = d.target.x - d.source.x, dy = d.target.y - d.source.y, len = Math.sqrt(dx * dx + dy * dy) || 1;
        d3.select(this).attr("x1", d.source.x).attr("y1", d.source.y)
          .attr("x2", d.target.x - dx / len * (d.target.r + 3)).attr("y2", d.target.y - dy / len * (d.target.r + 3));
      });
      n.attr("transform", function (d) { return "translate(" + d.x + "," + d.y + ")"; });
    });
    sim.force("link").links(links);
    sim.alpha(1).restart();
  }
  document.querySelectorAll(".area-filter").forEach(function (c) {
    c.addEventListener("change", function () { state.areas[c.value] = c.checked; draw(); });
  });
  document.addEventListener("reversa:param-change", function (e) {
    var d = e.detail || {};
    if (d.param === "charge") { sim.force("charge").strength(+d.value); sim.alpha(0.6).restart(); }
    if (d.param === "distance") { sim.force("link").distance(+d.value); sim.alpha(0.6).restart(); }
    if (d.param === "hideInit") { state.hideInit = !!d.value; draw(); }
  });
  draw();
})();
</script>""".replace("%AREAS%", areas_js)

render(rel="modulos.html", page_id="modulos", title="Módulos", payload=payload_mod,
       agent="reversa-docs-mapper", template="modulos", sidebar=sidebar_mod,
       head_extras='<script src="assets/vendor/d3.v7.min.js"></script>', scripts=scripts_mod,
       source_md="README.md")

st = state()
register(st, "mapper", "reversa-docs-mapper", ["arquitetura.html", "modulos.html"],
         omitted=[{"page": "topologia.html", "reason": "topology not detected: _reversa_sdd/architecture.md ausente"}])
print("OK mapper", n_mod, loc, len(deps["edges"]))
