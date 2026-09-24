# Geradores do mini-site

Scripts que produziram `_reversa_docs/` em 2026-09-24 via `/reversa-docs`. Para regenerar, a partir da raiz do projeto:

    python3 _reversa_docs/.generator/extract.py      # modules.json, deps.json (imports reais via AST)
    python3 _reversa_docs/.generator/mapper.py       # arquitetura.html, modulos.html
    python3 _reversa_docs/.generator/analyst.py      # metricas.html, timeline.html
    python3 _reversa_docs/.generator/storyteller.py  # glossario.html, deck.html, features/*.html
    python3 _reversa_docs/.generator/publisher.py    # selo, data.js, nav, index.html, smoke test
    python3 _reversa_docs/.generator/portable.py     # afla-nfes-documentacao.html: o site inteiro num só arquivo

O chassi `viewer.html` é lido do pacote `reversa` no cache do npx (`rvlib.TPL`). Os textos do glossário, das
features e dos marcos da linha do tempo são curados à mão nos scripts; atualize-os quando surgir adendo novo.
