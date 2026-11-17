# Viscount Academic RMarkdown & Humanised Prose Style Guide

All Operation Viscount deliverables (`studies_on_population.Rmd` at project root and paired `<stem>_literature_review.Rmd` / `<stem>_areal_masks_and_bins.Rmd` + `<stem>_settlements.Rmd` per sub-chapter) publish directly to LaTeX PDF (`intellte.cls` / `crd-mla-numeric.csl`) AND synchronise to Intellte (`Project 1746`). Every report MUST comply with both `/humanise` prose standards and Gatekeepers `D1` (`audit_academic_prose.py`) & `D2` (`audit_rmd_and_bib_calibre.py`).

---

## 1. Required File Pairing, Folder Layout & Editorial Voice

1. **Paired Sub-Chapter Files & 2-Level Folders**:
   - Organise sub-chapters in shallow `2`-level chronologically/sub-regionally numbered directories sharing `_shared/{fonts,template,_gis_cache,sites_*}` (with SHA-256 deduplication across repeated `./papers/` files).
   - Pair `<stem>_literature_review.Rmd` (or `<stem>_areal_masks_and_bins.Rmd`) + `<stem>_settlements.Rmd`.
   - Supporting bibliographies: `*.bib` with **`>= 20` unique BibTeX keys** and **`>= 85%` (`>= 90%` project-wide) `doi` or external `https://` `url` fields**.
   - Archival library in `<chapter_dir>/papers/`: **`>= 15` valid `%PDF-` files (`> 10,24 kB`)** per sub-chapter (anti-stub floor).
   - Project root: `studies_on_population.Rmd` (**`>= 450` lines**; consolidated comparative synthesis across all macro sub-chapters).
2. **Anti-Stub Depth Floors & Author/Metadata Block**:
   - Sub-chapter review `.Rmd`: **`>= 350` lines** and **`>= 2.500` words** (keep expanding until regional historiography, areal mask boundaries and census methods are thoroughly covered).
   - Standard author metadata: `authors_line: "Aust Kätzchen"`, `emails: [austkaeztchen@confoederatio.org]`. Keep titles `<= 2` lines and `subtitle` strictly content-grounded (`<= 105` characters).
3. **Zero Prose Scripts (McEvedy & Jones / Klein Goldewijk Voice)**:
   - Never run Python or regex scripts to generate or rewrite `.Rmd` prose. Edit prose solely via direct `read_file` + `edit_file` passes followed by reading compiled PDF pages: regional sub-chapters adopt **Colin McEvedy & Richard Jones** plain demographic narrative, and root `studies_on_population.Rmd` adopts **Kees Klein Goldewijk (HYDE)** comparative synthesis.
4. **Canonical Section Hierarchy (`/humanise` Order)**:
   - Unnumbered headings (`\setcounter{secnumdepth}{-2}`): `Abstract`, `Background`, `Methodology`, `Testing and Validation` (or `Validation`), `Results`, `Limitations`, `Conclusion`, `Appendix`, `Sources` (`[FAIL]` on `# References`), `Footnotes` (suppressed automatically when empty).
   - Zero self-congratulatory badge words (`verified`, `validated`, `empirical`, `complete`) in YAML `hero_caption:`/`subtitle:`, captions or `#` headings.

---

## 2. Formatting, Multi-Script Transliteration & Prose Hygiene (`Gatekeeper D1`)

`audit_academic_prose.py` (`Gatekeeper D1`) enforces these universal rules across YAML metadata, headings, figure/table captions and body text:

- **Spelling**: Non-Oxford British English (`mediaeval`, `colour`, `honour`, `centre`, `analyse`, `harmonise`, `organise`, `standardise`, `synthesise`, `recognise`, no Oxford serial commas).
- **Numbers & Units**:
  - European decimals with comma: `58,88`, `2,5x`, `0,45` with no redundant trailing zeroes (`4,2`, never `4,20`).
  - Full-stop thousands separator: `10.290 settlements`, `110.642 observations` (`[WARN]` on space-delimited thousands).
  - Semantic magnitudes in prose: `k`, `M`, `B`, `T`; always promote `>= 1.000k` (`2,04M`, never `2.040k`).
  - Unicode area units: `km²` and `m²` — ASCII `km2`, `m2`, `km^2`, `m^2` outside LaTeX math fail `D1` (or pass with warning under `--legacy-baseline` for older baseline docs).
- **Dates & Eras**:
  - Format era labels consistently within a chapter using either attached compact (`10000BC`, `1897AD`) OR spaced/prefixed (`500 BC`, `AD 1600`). NEVER insert dots in attached years (`10.000BC` -> `[FAIL]`), NEVER write spaced trailing `AD` (`1600 AD` -> `[FAIL]`), and omit `AD` on modern month-year dates (`March 1953`, not `March 1953AD`).
- **Multi-Script Romanisation & Diacritics**:
  - Transliterate non-Latin scripts into scholarly Latin romanisation (Pinyin, Hepburn/Revised Romanization, IAST, ALA-LC, BGN/PCGN) with Latin diacritics preserved (`Stadestér`, macrons, carons) across body text, legends and tables (`0` `.notdef` / `U+FFFD` replacement glyphs in `10pt` `Karla` XeLaTeX PDFs).
- **Anti-AI & Anti-Schema Leakage Discipline (`/humanise`)**:
  - Zero tortured AI clichés, zero prose ` -> ` arrows (`to`), zero space-padded slashes `' / '`, zero leaked JSON schema names (`other_names`, `coords`, `positive integer population series`), zero leaked `snake_case` folder/code tokens (`sites_...`), zero `"the <PROJECT> synthesis/framework/model"` wrappers (write bare `<PROJECT>`), zero redundant `word (n=X)` tics (`45 regions`, not `forty-five regions (n=45)`), zero prose bullet/label lists, zero compound decorator colour adjectives (`warm gold` -> `gold`), zero geopolitical/demographic euphemisms, and zero unescaped `<Tag>` strings breaking Intellte VitePress Vue builds.
  - **Minimum Zipf Sample Floor**: Never plot or compute Zipf / rank-size regressions where `n < 25` (`[FAIL]` in `D2`).

---

## 3. Intellte LaTeX, Aspect-Adaptive Figures & Compiled PDF Geometry (`Gatekeeper D2`)

- **Shared Helpers & Staged JSON Caches**: Source the Intellte helpers (`render_table_template`, `viscount_table`, `viscount_figure`) cleanly, stage pre-computed JSON summary caches inside each chapter so RMarkdown compilation never fails on runtime lookups, and use `rownames(df) <- NULL`.
- **Table Rules (`10pt` Inline `longtable`)**: Captions sit strictly **below** tables (`<= 3` lines adding analytical context rather than echoing headers), header row emits once via `\endfirsthead` with empty `\endhead` (zero `(Continued from previous page)` banners), zero `\parindent` cell indentation, `<= 6` columns recommended (`[WARN]` > 10 cols, `[FAIL]` > 14 cols) and zero narrative chaining (`A to B to C`) inside single cells.
- **Aspect-Adaptive Equal-Area Cartography (`plt.rcdefaults()`)**: Choose equal-area projection per `geography_profile` (`Albers Equal-Area Conic` for mid-latitude E-W extents; `Lambert Azimuthal Equal-Area` for equatorial, continental, polar or archipelagic domains), use default `DejaVu Sans` regular weight, planar graph-colouring of adjacent regions, `zorder=6` leader pointers behind opaque `zorder=10` white text boxes (`0` crossed lines), colorbar titles on **top** with plain European ticks + `vmax` aligned to the top tick (no white clipping splotches), transparent insets, `Stadestér` diacritic, `n=` dot thousands (`n=1.765`), and `0` interpuncts (`·`).
- **Default Matplotlib Theme, Sans-Serif Typography & MathText (`$...$`) Specification (`audit_figure_scripts.py`)**:
  - Always reset Matplotlib explicitly (`plt.rcdefaults(); plt.style.use("default")` or `apply_viscount_style(ax)` from [viscount_plot_utils.py](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/histmap/1.data_raw/population_regional/_shared/viscount_plot_utils.py)). NEVER set `font.family = "serif"` (`Times`, `Georgia`, `Palatino`), NEVER apply `seaborn` or stripped themes (`theme_classic`), and NEVER strip `spines["top"]` or `spines["right"]` on standard Cartesian axes.
  - Render all mathematical parameters, Greek symbols, subscripts, fractions and exponents inside Matplotlib `$...$` MathText rather than raw ASCII (`r"Matérn $\nu = 3/2$ fit ($\tau_1 = 1{,}06$, $R^2 = 0{,}94$)"` and `r"Normalised semivariance $\gamma(u) / \sigma^2$"`, never `"nu = 3/2"`, `"tau1=1,41"`, `"Pseudo R-squared"`, or `"log10(Sites)"`). Wrap European decimal commas inside `$...$` in braces (`{,}`, or call `format_mathtext_euro()`) so TeX renders zero trailing space after the comma.
  - Format fractional numerical axes with European decimal commas (`euro_tick_formatter()` / `FuncFormatter`, e.g. `0,75`, never `0.75`).
  - Map machine `snake_case` horizon or region keys through explicit human display-name dictionaries (`REGION_DISPLAY_NAMES`, `epochs_order`), NEVER `.replace("_", " ").title()` (which corrupts `"pueblo_iii"` into `"Pueblo Iii"`).
  - Plot substantive diagnostic graphics (empirical semivariograms $\gamma(u)/\sigma^2$ vs dimensionless catchment lag $u_{ij}$ with fitted Matérn models, trajectories with empirical uncertainty intervals, rank-size distributions for `n >= 25`) under plain titles, NEVER degenerate flat `0,998` bar charts or technobabble headers such as `"Non-Stationary Matérn Residual Kriging Fit Summary"`.

  ```python
  import matplotlib.pyplot as plt
  from viscount_plot_utils import apply_viscount_style, euro_tick_formatter, format_mathtext_euro

  HORIZON_LABELS = {"03_middle_mississippian_pueblo_iii": "Middle Mississippian (Pueblo III)"}
  apply_viscount_style(ax)
  ax.set_title(rf"Semivariogram Calibration ($\nu = 3/2$, $\tau_1 = {format_mathtext_euro(tau1)}$)")
  ax.set_xlabel(r"Dimensionless Voronoi geodesic lag $u_{ij}$")
  ax.set_ylabel(r"Normalised semivariance $\gamma(u) / \sigma^2$ ($R^2 = " + format_mathtext_euro(r2) + r"$)")
  ax.xaxis.set_major_formatter(euro_tick_formatter(2))
  ```
- **Provenance Discipline**: NEVER cite `@McEvedy`, `@KleinGoldewijk`, `Populstat`, `Chandler 1987`, `Modelski 2003`, `Maddison` or internal SVEA workspace `histmap/` / `population_Substrata` / `population_Velkscala` paths in sub-chapter files. Only root `studies_on_population.{Rmd,bib}` may compare macro totals against global baselines.
- **Compiled PDF Layout (`pymupdf`)**:
  - Page `1` non-blank with scaled hero figure (`height <= 0,52\textheight`), **`max_x1 <= 540,5 pt`**, **`0` unresolved `??`**, **`0` `(Continued from previous page)`**, and **`0` `\ufffd` replacement glyphs**.
- **Chapter Visual Inspection**: Crop every multi-panel PNG into individual panels (`1A..nD`), inspect every panel via `read_file`, sign `<chapter_dir>/figures/visual_check.json` (`mtime >= max(png.mtime)`), and run `audit_academic_prose.py` (`D1`), `audit_figure_scripts.py` plus `audit_rmd_and_bib_calibre.py --require-visual-check` (`D2`).
