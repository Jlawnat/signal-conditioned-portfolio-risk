# LaTeX V2 source

`main.tex` is a portable, condensed article rendering of the authoritative `paper/MANUSCRIPT_DRAFT_V2.md`; `references.bib` mirrors `paper/references_v2.bib`. It uses generic `article`, `natbib`, `amsmath` and `booktabs`, with no author affiliation or journal template. The Markdown manuscript contains the full V2 discussion and linked figures/tables; use it for research review.

When a LaTeX distribution is installed, compile from this directory with:

```sh
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

`pdflatex` and `latexmk` were absent in this environment on 2026-11-02, so compilation is **NOT_TESTED**. The source has no external figure dependency and should produce a readable text/table draft if standard packages are present. SVG figure conversion and placement can be completed after a target venue and production toolchain are chosen.
