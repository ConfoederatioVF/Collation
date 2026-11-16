# Operation Viscount RMarkdown & Prose Template

## 1. Frontmatter & Setup Chunk

Every regional chapter `.Rmd` and synthesis `studies_on_population.Rmd` MUST use shared templates and helpers from `_shared/template/`:

```yaml
---
title: "<Concise Regional or Thematic Title>"
subtitle: "<PROJECT_KEY>: <Scope>, <StartYear>-<EndYear>"
date: "16 November 2026"
authors_line: "Aust Kätzchen"
emails:
  - austkaeztchen@confoederatio.org
hero_figure: "figures/<chapter_hero_map>.png"
hero_caption: "<Self-contained cartographic caption with historical borders and key sites.>"
hero_label: "fig:hero"
bibliography: <chapter_stem>.bib
csl: ../../_shared/template/crd-mla-numeric.csl
link-citations: true
output:
  pdf_document:
    latex_engine: xelatex
    template: ../../_shared/template/template.tex
    keep_tex: false
  github_document:
    html_preview: false
    toc: true
    toc_depth: 3
---
```

Setup chunk (no inline `render_table_template` redefinition):

```r
knitr::opts_chunk$set(
  echo = FALSE,
  message = FALSE,
  warning = FALSE,
  fig.align = "center",
  out.width = "100%"
)
source("../../../_shared/template/viscount_rmd_helpers.R")
```

For LaTeX tables and HTML compatibility in VitePress, call `viscount_table(df, caption, col_names)` and `viscount_figure(path, caption, label)`. Intellte `table_templating.R` emits `<table class="crd-wysiwyg-table" v-pre>` automatically so numeric citations and math never trigger Vue template parsing warnings.

---

## 2. Prose, Numeric & Style Discipline (`audit_academic_prose.py`)

1. **Variety of British English**: Non-Oxford EN-GB (`standardise`, `synchronise`, `artefact`, `colour`, `neighbouring`, no Oxford comma in `A, B and C`).
2. **Numerical notation**:
   - Decimal comma: `58,88%`, `1,24M`, `0,005/km²` (never `58.88%` or `1.24M` in prose).
   - Semantic magnitude suffixes: `k`, `M`, `B`, `T` (`165,35M`, `350,4k`) instead of spelled-out words (`165,35 million`).
   - Dot thousands for small un-suffixed counts: `110.642`, `5.099`.
   - Timezones strictly `GMT+0`.
3. **Academic voice**: Write direct, quantitative historical prose citing primary chronicles, census volumes, tax cadastres and archaeological inventories (`[@CitationKey]`). Eliminate AI clichés (`delve`, `tapestry`, `pivotal role`, `serves as a testament`, `complex interplay`, `robust framework`, `holistic`, `burgeoning`, `spearhead`, negative `"Not only X, but also Y"` filler constructions and triadic marketing triplets).
4. **Citations & BibTeX**: Every empirical table cell, regional division count and methodological parameter must map to a verifiable key in `<chapter_stem>.bib`.
