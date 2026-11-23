# Stage D — Humanised RMarkdown Publishing, GitHub-Safe Paths, Citation Diversity & `POLARIS` Figures

All numeric caps (`path_and_title_limits`, `citation_diversity_limits`, `provenance_caps`) live in [viscount_skill_profiles.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/config/viscount_skill_profiles.json5).

---

## 1. File Pairing, GitHub-Safe Path Limits & Editorial Voice (`Gatekeeper D1`)

1. **GitHub & Windows `MAX_PATH` Hygiene (Hard `[FAIL]` in `D1`, `D3`, `F`)**:
   - Chapter stem: **`<= 42` chars** (concise `snake_case`, e.g. `early_modern_se_europe`).
   - Any `.Rmd`, `.pdf`, `.md`, `.bib`, `_settlements.json`, figure PNG, or `./papers/*.pdf` filename: **`<= 72` chars**.
   - Any repo-relative file path across SVEA AND Intellte (`papers/viscount/project_<slug>/...`): **`<= 180` chars** so every PDF commits cleanly to GitHub without `MAX_PATH` or `subst` workarounds.
   - Root `studies_on_population.Rmd`: exact `title: "Studies on Population"`, `subtitle <= 90` chars (`>= 450` lines). Chapter `.Rmd`: canonical itinerary title (`<= 72` chars / `<= 10` words, `subtitle <= 90` chars, zero bloated wrappers), `>= 350` lines and `>= 2.500` words. Author metadata: `authors_line: "Aust Kätzchen"`, `emails: [austkaeztchen@confoederatio.org]`.
2. **Read/Edit-Only Prose (`0` Prose Scripts)**: Edit `.Rmd` prose solely via `read_file` + `edit_file` (`MAX 1 CHAPTER PAIR PER WORKER`). Voice: **McEvedy & Jones** plain historical narrative per sub-chapter; **Klein Goldewijk** synthesis at root. Include scraped sub-administrative enumeration tables in relevant chapters.
3. **Canonical Section Order (`/humanise`, `\setcounter{secnumdepth}{-2}`)**:
   - `Abstract` (single undivided prose block, `0` `##` sub-headings, pushed cleanly onto Page 2 with its paragraph if Page 1 hero leaves `< 3` lines), `Background`, `Methodology`, `Testing and Validation`, `Results`, `Limitations`, `Conclusion`, `Appendix`, `Sources` (`[FAIL]` on `# References`), `Footnotes`.
   - Zero self-congratulatory badge words (`verified`, `validated`, `empirical`, `complete`) in titles, headings, or captions.
4. **Formatting & Anti-AI Hygiene**:
   - Non-Oxford `EN-GB` (`mediaeval`, `colour`, `harmonise`), European decimals (`58,88`, no trailing zeroes), dot thousands (`110.642`), semantic magnitudes (`k`, `M`, `B`, `T`; promote `>= 1.000k`), Unicode `km²`/`m²`.
   - Consistent era labels (`10000BC`/`1897AD` OR `500 BC`/`AD 1600`; never `10.000BC`, `1600 AD`, or `March 1953AD`).
   - Scholarly Latin romanisation (`0` `\ufffd`/`.notdef` glyphs in `10pt` `Karla`).
   - **Zero non-code monospace** (`0` inline backticks outside `` `r ...` ``, `\texttt{}`, `\verb`, `<code>` in YAML, headings, prose, captions, or tables), zero leaked JSON/snake_case keys, zero ` -> ` arrows, zero `' / '`, zero redundant `word (n=X)`, zero prose bullet lists, zero unescaped Vue `<Tag>` tokens.

---

## 2. Bibliography & Source Concentration Caps (`Gatekeeper D3`)

Every chapter `.bib` and `./papers/` archive MUST satisfy:
- **Archival Floor**: `>= 15` SHA-256-unique valid `%PDF-` files (`> 10,24 kB`, filename `<= 72` chars) covering every constituent jurisdiction, and `>= 20` unique `.bib` keys (`>= 85%` chapter / `>= 90%` project DOI or `https://` URL coverage; sanitise HTML tags `<i>`/`<sup>` to LaTeX).
- **Source Diversity & Anti-Concentration Law (No Disproportionate Reliance on Few Sources)**:
  - **Single-source in-text cap**: No single BibTeX key may account for **`> 20%`** of all in-text `@cite` occurrences in a chapter review.
  - **Top-3 sources cap**: The top `3` most-cited keys combined MUST NOT exceed **`45%`** of in-text citations.
  - **Active bibliography utilisation**: **`>= 75%`** of declared `.bib` keys (minimum `>= 15` distinct cited works) must be cited in the chapter text.
  - **Author/publisher cap**: No single first-author or publisher/domain may exceed **`30%`** of a chapter's bibliography; `>= 5` distinct scholarly publishers/domains; Zenodo `<= 15%` chapter / `<= 10%` project; crowd `<= 10%`.
- **Sub-Chapter Fallback Ban**: Never cite `@McEvedy`, `@KleinGoldewijk`, `Populstat`, `Chandler1987`, `Modelski2003`, `Maddison`, or internal SVEA paths in sub-chapters (allowed only in root `studies_on_population.Rmd`).

---

## 3. Intellte LaTeX/PDF Geometry (`pymupdf` Batched Probe) & 5 `POLARIS` Figure Laws (`Gatekeepers D2–D3`)

- **LaTeX & Tables**: Include float-fraction tuning (`\topfraction=0.88`, `\bottomfraction=0.82`, `\textfraction=0.08`, `\floatpagefraction=0.75`, `\raggedbottom`), cap interior figures `<= 0,42\textheight` (`<= 0,52\textheight` Page-1 hero only), forbid ad-hoc `\newpage`/`\clearpage` padding, emit inline `10pt` `longtable` captions **below** tables with empty `\endhead` (`<= 10` cols recommended, `[FAIL]` > 14), stage per-chapter JSON caches, and enforce `n >= 25` Zipf floor.
- **Batched `pymupdf` PDF Audit (`pdf_geometry_probe.py` via `audit_rmd_and_bib_calibre.js`)**: Verifies non-blank Page 1, `0` orphaned Page-1 `Abstract` headings, `0` interior deadspace pages (`occupancy >= 35%`, `max_gap <= 55%`), `0` unintended monospace font pages, `max_x1 <= 540,5 pt`, `0` `??`, `0` `(Continued from previous page)`, and `0` `\ufffd` glyphs.
- **5 `POLARIS` Figure Laws (`audit_figure_scripts.js` + `save_viscount_figure(..., strict_layout=True)`)**:
  1. **Vector Cartography Only**: Plot smooth projected GeoJSON `PatchCollection` polygons (`mute_rgb_hex`), Natural Earth land/rivers and `.naissance` borders — NEVER `imshow()` categorical `*_areal_mask.png` rasters (reserve `imshow()` strictly for continuous kriged/`Velkscala` surfaces and non-spatial heatmaps).
  2. **Upright Equal-Area Projections (`set_aspect("equal")`)**: `Albers Equal-Area Conic` or `Lambert Azimuthal Equal-Area`; split distant exclaves/archipelagos (`> 1.500 km` or `> 90°` lon span) into dedicated `GridSpec`/`inset_axes` panels with `±360°` antimeridian wrapping.
  3. **In-Panel Bbox Containment & Zero Occlusion**: `place_inbounds_callouts()` + `verify_panel_bounds_and_overlaps(fig, ..., {"strict": True})`, `1,18x–1,25x` axis headroom, `0` spine bleeds or overlaps.
  4. **Default Matplotlib Theme, MathText & Plain Human Numerals**: `plt.rcdefaults(); plt.style.use("default")` (`DejaVu Sans`, 4 boxed spines, `0` serif/`seaborn`), rendered `$...$` MathText with `{,}` European decimals, `euro_tick_formatter()`, `apply_human_log_ticks()` / `euro_log_formatter()` (`0,01..1k..1,5M`, `0` `$10^k$`/`1e4` on counts/densities), explicit display dictionaries (`0` `.replace("_", " ").title()`).
  5. **Mask -> Figure -> PDF Freshness & Independent `@verifier` QA**: Regenerate figures FIRST and PDFs AFTER any mask/data edit (`pdf.mtime >= fig.mtime >= mask.mtime`). Crop multi-panel PNGs (`1A..nD`), have an **independent `@verifier`** inspect every panel via `read_file`, fix any defect in a loop, and sign `<dir>/figures/visual_check.json` (`>= 50`-char unique notes per PNG, `manifest.mtime >= max(png.mtime)`).
