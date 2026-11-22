---
name: draft-report
description: >-
  Acts as a co-researcher and exploratory data researcher to investigate any user-requested topic - combining exploratory data analysis (EDA) of existing on-disk datasets with external scholarly research and archived PDFs when applicable - and compiles Intellte R Markdown working papers (.Rmd, .pdf, .md, .bib) with British English plain academic prose, default Matplotlib visualisations and real GIS cartography. Triggered by /draft-report.
disable-model-invocation: true
---

# Co-Researcher and Exploratory Data Report Workflow (`/draft-report`)

This skill acts as a co-researcher and exploratory data researcher to investigate any topic, hypothesis, dataset or domain requested by the user, producing a publication-ready Intellte R Markdown report (`<report_stem>.{Rmd,pdf,md}`) supported by reproducible data analysis, default Matplotlib visualisations, real GIS cartography (`./figures/`) and archived external literature (`./papers/` and `<report_stem>.bib` when external sources are used).

Unlike `/literature-review-population` (which is restricted to Holocene regional demographic reviews and forbids internal datasets), `/draft-report` treats **existing on-disk data** as a first-class empirical source alongside external scholarly research. It supports three flexible operating modes depending on the user's request:

1. **On-Disk Exploratory Data Analysis (EDA) & Empirical Modelling**: Discovers, profiles, queries and models existing on-disk datasets (e.g. `/common/`, `/histmap/`, `/livemap/`, `/saves/`, `/core/`, CSV/TSV, JSON/JSON5, GeoJSON/Shapefiles/GeoTIFFs, `.naissance` saves, SQLite/Parquet files or codebase metrics) to test hypotheses, uncover patterns, diagnose anomalies and present quantitative findings.
2. **Hybrid Data & Literature Synthesis**: Combines empirical analysis of on-disk data with external scholarly literature, historical records or benchmark datasets, cross-validating internal series against published research (`./papers/` and `<report_stem>.bib`).
3. **General Domain Literature Review & Synthesis**: Conducts an external scholarly investigation on any requested topic, archiving source PDFs into `./papers/`, synthesising empirical findings into structured tables and plotting comparative charts and GIS maps.

---

## Core Mandates (Apply to All Phases and Subagents)

### 1. Co-Research, On-Disk Data Exploration & Source Archiving
- **On-Disk Data First-Class Support**:
  - Actively inspect and analyse existing on-disk project files and datasets relevant to the user's request (including `saves/atlas_defacto.naissance`, `histmap/`, `livemap/`, `common/` and user-specified paths).
  - Never guess, extrapolate by hand or fabricate summary statistics from on-disk files. Write reproducible Python or R exploratory scripts to inspect schemas, row/feature counts, missingness, distributions, quantiles, correlations, regressions and spatial/temporal aggregations before drafting prose or figures.
- **Analytical Rigour & Co-Researcher Initiative**:
  - Act as a genuine co-researcher: formulate clear hypotheses, compare alternative explanations, quantify uncertainty (e.g. interquartile ranges, confidence intervals, error bounds, sensitivity checks), highlight data anomalies or structural breaks and document methodological limitations transparently.
- **External Literature & PDF Archiving (`./papers/`, When Applicable)**:
  - Whenever external academic scholarship, archival monographs or benchmark studies are cited, download and archive the primary/secondary source PDFs into `<report_dir>/papers/<author_year_short_title>.pdf`.
  - Verify every file in `./papers/` begins with a valid `%PDF` header and is `> 10 KB` (never save HTML landing/error pages as `.pdf`).
  - Open-access repositories (CyberLeninka, Zenodo, JSTOR Open, Archive.org, arXiv, SSRN, institutional repositories) and shadow libraries (`Sci-Hub`, `LibGen`, `Anna's Archive`) are permitted to obtain regional monographs and journal articles, but bibliographies MUST remain diverse across primary journals, university presses and official statistical agencies (cap Zenodo at `<= 15%` and Wikidata/OSM/GeoNames at `<= 10%` of `.bib` entries).
  - Run heavy Python/Node/R EDA, scraping or compilation jobs via `python .agents/skills/population-regional-study/scripts/run_bounded.py -- <cmd>` so Win32 Job Objects, `BelowNormal` CPU priority and `geopng_compute.json5` RAM/thread limits prevent workstation lag and orphaned processes.
  - Reference archived PDFs in `<report_stem>.bib` (`note = {Archived PDF: ./papers/<filename>.pdf}`) and link them in prose where appropriate (`[archived PDF](papers/<filename>.pdf)`).

### 2. Prose, Style and Localisation Rules
- **British English (`EN-GB`)**: Use non-Oxford British English (`colonisation`, `urbanisation`, `centre`, `mediaeval`, `programme`, `kilometres`, `analyse`, `modelling`, `catalogue`, `neighbouring`, no serial/Oxford comma).
- **Plain Academic Prose (Zero Technobabble & Zero Prose Scripts)**:
  - Never use Python/R regex scripts to generate or humanise prose; author and refine prose solely via direct reading and editing (`read_file` + `edit_file`).
  - Forbid inflated AI jargon (`"Complete Secular Holocene Demographic Trajectory"`, `"Spatiotemporal Paleodemographic Carrying-Capacity Envelope"`), leaked JSON/schema keys (`other_names`, `coords`), redundant `word (n=X)` tics (`45 regions`, not `forty-five regions (n=45)`), compound decorator colours (`warm gold` -> `gold`), and unescaped `<Tag>` strings outside code blocks that break VitePress Vue builds.
  - Required: Plain, direct, descriptive headings and sentences (`Abstract`, `Background`, `Methodology`, `Testing and Validation`, `Results`, `Limitations`, `Conclusion`, `Appendix`, `Sources`).
- **Compact Dates (`10000BC`, `1897AD`, `AD 1600`)**:
  - Format historical era labels consistently without dot separators inside attached years (`10000BC`, `500BC`, `1897AD` or `500 BC` / `AD 1600`, never `10.000BC` or `1600 AD`). Omit `AD` on modern month-year dates (`March 1953`).
- **European Decimals, Dot Thousands & Semantic Abbreviations**:
  - Use commas for decimals (`58,88`, `0,84`, `12,5k`, `1,45M`) without redundant trailing zeroes (`4,2`, not `4,20`), and full stops (`1.250`, `20.425`) for thousands separators in prose and tables. Promote `>= 1.000k` magnitudes (`2,04M`, never `2.040k`).
- **Plain Hyphens Only**:
  - Replace all em-dashes (`—`), en-dashes (`–`) and `---`/`--` with plain hyphens (`-` or ` - `).
- **Strict Code-Only Monospace & Minimal Inline Formatting & Multi-Script Transliteration**:
  - Reserve monospace fonts (`LMMono`, `\texttt{}`, `\verb`, `<code>` and Markdown backticks outside evaluated knitr `` `r ...` `` calls) **strictly for code blocks**. NEVER use inline backticks or `\texttt{}` in YAML titles/captions, headings, body prose, figure/table captions or tables (write numbers, `km²` units, `10000BC` dates, counts, dataset names and settlement names in plain text or italics for foreign terms).
  - Do not overuse bold or mix italics and LaTeX math in prose or tables. Reserve `$...$` and `$$...$$` exclusively for genuine mathematical formulas and equations.
  - Transliterate non-Latin scripts (Cyrillic, Chinese characters, Devanagari, Arabic, Greek, Devanagari/Indic, Thai, Korean, Japanese) into standard scholarly Latin romanisation with preserved diacritics (`Stadestér`, macrons, carons) inside tables and body text so XeLaTeX (`Karla` 10pt) renders `0` replacement boxes (`\ufffd`).

### 3. Visualisations: Default Matplotlib & Real GIS Maps (`./figures/`)
- **Default Matplotlib Charts (`plt.rcdefaults()` & MathText)**:
  - Always reset explicitly to Matplotlib defaults (`plt.rcdefaults(); plt.style.use('default')`, standard `DejaVu Sans` sans-serif typeface, intact 4-sided boxed spines on Cartesian plots, standard Tab10 palette, white background, subtle grid `alpha=0.3`, `dpi=300`). NEVER apply `font.family = 'serif'`, `seaborn` or stripped themes, or hide `spines['top']` / `spines['right']` on standard charts.
  - Render all mathematical parameters, Greek symbols and exponents via Matplotlib `$...$` MathText (`r"$\nu = 3/2$"`, `r"$\tau_1 = 1{,}41$"`, `r"Pseudo $R^2$"`, `r"$\log_{10}(\mathrm{Sites})$"`), wrapping European decimal commas inside `$...$` in braces (`{,}`) so TeX adds no trailing spacing. Never leave raw ASCII `nu = 3/2`, `tau1=1,41`, `R-squared` or `log10(` in titles, axes or legends.
  - Format fractional axis ticks with European decimal commas via `FuncFormatter` (`0,75`, never `0.75`), map raw `snake_case` category keys via explicit display dictionaries rather than `.replace('_', ' ').title()` (which corrupts `Pueblo III` into `Pueblo Iii`), avoid technobabble plot titles and choose substantive empirical designs (never zero-variance flat `0,998` bar charts). On all `loglog`, `semilog`, `set_xscale('log')`/`set_yscale('log')` and `LogNorm` plots showing empirical counts, sites, inhabitants or densities, NEVER use scientific notation (`10^k`, `1e4`) or raw `log10` exponent ticks: format ticks with plain European/semantic numerals (`0,01`, `1`, `10`, `100`, `1k`, `1,5M`) using `apply_human_log_ticks()` or `euro_log_formatter()` and suppress noisy minor log labels (`NullFormatter()`).
  - Select chart designs that best communicate the exploratory data findings: multi-panel `(A)`/`(B)` comparisons, time-series trajectories with shaded uncertainty/interquartile bands, scatter/regression plots with residual or error diagnostics, distribution plots (histograms, KDEs, box/violin plots, Lorentz/ECDF curves), heatmaps or grouped bar/area breakdowns.
  - **No Text/Legend Occlusion & Strict In-Panel Bounds**: Never place text annotations over bars, lines, scatter points or legends, and never allow bar-end labels, callouts or legends to exceed the bounds of their subplot spines (`ax.get_window_extent`). Disable default `clip_on=False` overflow by giving bars `18-25%` headroom, setting adequate subplot `wspace` for horizontal tick labels, using standard Matplotlib legends (`ax.legend(loc='best', frameon=True)` or figure legends cleanly anchored below plots with sufficient `bottom` margin) and verifying `0` bleeds or overlaps via renderer `Bbox` inspection (`verify_panel_bounds_and_overlaps` in [viscount_plot_utils.py](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/histmap/1.data_raw/population_regional/_shared/viscount_plot_utils.py)).
- **Real GIS Cartography (Vector Polygons, Equal-Area Framing & No Pixelated Masks)**:
  - Whenever the report includes geographic or spatial data, never draw schematic rectangles, circles or hand-coded polygons, NEVER `imshow()` categorical/binary raster masks in place of vector polygons (reserve `imshow()` strictly for continuous density/kriging surfaces and matrix heatmaps) and NEVER warp maps with equirectangular `imshow(..., extent=..., aspect='auto')`.
  - Every spatial map (`figures/<map_name>.png`) MUST use upright equal-area coordinates (`AlbersEqualAreaConic` or `Lambert Azimuthal Equal-Area` with `ax.set_aspect('equal')`), projecting smooth GIS shapefiles/GeoJSONs (`PatchCollection` with muted parchment-blended fills, Natural Earth coastlines, land, lakes, rivers, administrative boundaries, HydroSHEDS basins or `saves/atlas_defacto.naissance` historical borders) and splitting non-contiguous islands/exclaves (`> 1.500 km` ocean gap) into dedicated panels or `inset_axes` so frames never stretch across empty ocean.
- **Mandatory Figure-by-Figure Optical Repair & Mask-to-PDF Freshness**:
  - Go through every generated `.png` figure one by one via `read_file` to verify that vectors, rivers, axes, MathText, legends and labels are crisp, unwarped, inside panel spines and non-overlapping, fixing and regenerating defective figures until clear. Whenever source masks or datasets change, regenerate figures first and recompile the `.Rmd` to `.pdf`/`.md` afterwards so embedded PDFs never lag behind updated figures.

### 4. Intellte R Markdown (`.Rmd`) & PDF/MD Formatting
- **Template & Author Metadata**:
  - Copy `template.tex` from `E:/Active Projects/Project 1746 - Intellte/core/rticles/intellte/resources/template.tex` and `crd-mla-numeric.csl` from `E:/Active Projects/Project 1746 - Intellte/core/rticles/intellte/skeleton/crd-mla-numeric.csl` into the target report directory (sourcing `framework_init.R` also stages `intellte.cls` and `crd_logo.png` automatically via `stage_intellte_resources()`).
  - Use `authors_line: "Aust Kätzchen"` and `emails: [austkaeztchen@confoederatio.org]` unless the user specifies otherwise.
  - Include the complete `{r setup, include=FALSE}` override block from [`references/intellte_setup_and_audit.md`](./references/intellte_setup_and_audit.md).
- **Table Rules (`10pt` Inline `longtable`, `valign=top` Headers, Zero Clipping)**:
  - All tables must share the exact `10pt` (`10pt/14pt`) body font size and flow inline across pages via `longtable` (never use `\resizebox` or floating `table` environments that isolate tables onto spare pages).
  - **Top-Aligned Headers (`valign=top`)**: In `col_specs`, use `>{\raggedright\arraybackslash\hyphenpenalty=50\exhyphenpenalty=50}p{%.4f\textwidth}` **without** `\hspace{0pt}` so TeX never breaks before the first word of a header cell. Place `\hspace{0pt}` **only** inside body row cells so long body words hyphenate cleanly without affecting header alignment.
  - **Zero Right-Margin Overflow**: Every page in the compiled `.pdf` must satisfy `max_x1 <= 540.1 pt` (72pt margins on 612pt width).
- **Zero Orphaned Page-1 `Abstract` / Section Headings**:
  - Keep `# Abstract` as a single undivided prose block (never insert `##` sub-headings directly under `# Abstract`, which forces a premature break before any paragraph text). Include the `\AtBeginDocument` `\crdneedspace{135pt}` + `\abscontent` `\nopagebreak[4]` headroom guard (from [`references/intellte_setup_and_audit.md`](./references/intellte_setup_and_audit.md)) or cap Page 1 `hero_figure` height so `Abstract` either fits at least 3 opening lines on Page 1 or moves cleanly onto Page 2 together with its opening paragraph.
- **Empty Footnotes Suppression & Zero `??`**:
  - Ensure `template.tex` and `emit_crd_footnotes()` do not output an empty `Footnotes` heading when no footnotes are present.
  - Use Pandoc `[@key]` citations matching `<report_stem>.bib` (when external references are cited) and `\ref{tab:...}` / `\ref{fig:...}` cross-references, and verify `0` occurrences of `??` in the compiled PDF.

---

## Subagent Management & Anti-Stall Protocol

1. **Task & Module Parallelisation**:
   - For multi-part investigations, multi-region analyses or large on-disk dataset audits, spawn subagents (`invoke_subagent` with `TypeName: "self"`, `Model: "inherit"`) per independent analytical module or sub-topic.
2. **Self-Contained Subagent Prompts**:
   - Every subagent prompt must explicitly state: (a) the exact on-disk data paths and/or external literature scope to investigate, (b) the `./papers/` PDF archiving requirement when external literature is cited, (c) the British English plain-prose, European decimal (`58,88`), plain hyphen (`-`) and compact `10000BC`/`2000AD` formatting rules, (d) the path to [`references/intellte_setup_and_audit.md`](./references/intellte_setup_and_audit.md) for the mandatory `{r setup, include=FALSE}` block and (e) the requirement to visually check all PNG figures (`read_file`) and audit compiled PDFs (`pymupdf`).
3. **Incremental Data/Figure Scripts Only (Never Prose Scripts)**:
   - Never draft massive datasets or monolithic prose blocks inside a single huge `<thought>` turn, and NEVER use Python/R scripts to generate or regex-rewrite prose. Use modular scripts strictly for ETL, JSON summary caches and figures; refine `.Rmd` prose directly via read/edit-only passes.
4. **Directory-Grouped R Markdown Compilation**:
   - Never run `rmarkdown::render()` on two `.Rmd` files in the same folder simultaneously (intermediate `.tex`/`.aux` files collide). Group parallel compilation jobs by directory.
5. **Handoff Protocol for Stalled Subagents**:
   - If a subagent stalls or exceeds a reasonable runtime, terminate it via `manage_subagents(Action="kill")`, inspect the files already written in its target directory, write a concise handoff prompt listing the exact remaining steps and spawn a fresh replacement subagent (or execute the final build script directly).

---

## Step-by-Step Workflow

### Step 1: Scope Definition & On-Disk Data Discovery
1. Identify the user's research question, target output directory and report filename stem (`<report_stem>`).
2. Create the target report directory along with `./figures/` (and `./papers/` when external sources are being collected).
3. Copy `template.tex` from `E:/Active Projects/Project 1746 - Intellte/core/rticles/intellte/resources/template.tex` and `crd-mla-numeric.csl` from `E:/Active Projects/Project 1746 - Intellte/core/rticles/intellte/skeleton/crd-mla-numeric.csl` into the report directory.
4. Locate and inventory all relevant on-disk datasets, configuration files or codebase modules (`common/`, `histmap/`, `livemap/`, `saves/`, `core/` or user-specified paths).

### Step 2: Exploratory Data Analysis (EDA) & Literature Search
1. **On-Disk Data Profiling & Modelling**:
   - Write and run Python or R EDA scripts (storing temporary scripts in `/tests/` and cleaning them up afterwards, or keeping reusable data-processing scripts in the report folder if requested) to inspect the structure, coverage, summary statistics, distributions, correlations, anomalies and temporal/spatial trends of the on-disk data.
   - Export clean, verified summary datasets (CSV/JSON) if needed to drive the report's figures and R Markdown tables directly from the computed numbers.
2. **External Literature & Archiving (When Applicable)**:
   - Search relevant scholarly literature, technical documentation or historical/empirical benchmarks.
   - Download and verify source PDFs (`%PDF` header, `> 10 KB`) into `./papers/` and assemble `<report_stem>.bib`.

### Step 3: Generate Default Matplotlib Figures & Real GIS Maps (`./figures/`)
1. Generate a hero figure (`figures/<report_stem>_hero.png`, such as a pure vector Equal-Area GIS map or multi-panel executive summary figure) and 2-4 analytical figures (`figures/fig2_*.png`, `figures/fig3_*.png`, etc.) using `plt.rcdefaults(); plt.style.use('default')` (`DejaVu Sans`, intact 4-sided boxed spines, `$...$` MathText with `{,}` European decimal commas, `FuncFormatter` comma ticks, `dpi=300`), smooth equal-area vector GIS polygons (`set_aspect('equal')`, dedicated insets for distant outliers, zero pixelated mask `imshow()` tiles) and renderer-`Bbox` layout checks (`verify_panel_bounds_and_overlaps()`).
2. Inspect every generated `.png` file one by one using `read_file`, iterating on and regenerating any figure with occluded text, out-of-panel labels or warped map bounds until spotless before PDF compilation.

### Step 4: Draft & Compile `<report_stem>.{Rmd,pdf,md}`
1. Write `<report_stem>.Rmd` using the `{r setup, include=FALSE}` block from [`references/intellte_setup_and_audit.md`](./references/intellte_setup_and_audit.md).
2. Structure the report with clear, plain academic British English headings suited to the topic (for example: `Background`, `Data Sources and Methodology`, `Exploratory Data Analysis`, thematic/regional empirical sections, `Model Diagnostics and Limitations`, `Conclusion`, `Appendix` and `Sources`).
3. Render all tables via `render_table_template()` (inline `10pt` `longtable` with `valign=top` headers) and all figures via `render_figure_template()`.
4. If the user also requested supplementary machine-readable outputs (e.g. a cleaned `.json`, `.csv` or `.Rmd` data appendix), generate and validate them alongside the main report.

### Step 5: Automated Verification & Cleanup
1. Audit any Matplotlib/R figure generator script with `python .agents/skills/population-regional-study/scripts/audit_figure_scripts.py <report_dir>` (`exit 0`, verifying default theme, MathText, vector map polygons and `set_aspect('equal')`), recompile `<report_stem>.pdf` and `<report_stem>.md` via `Rscript.exe` after any final figure regeneration (`pdf.mtime >= fig.mtime`) and run the automated `pymupdf` verification script in [`references/intellte_setup_and_audit.md`](./references/intellte_setup_and_audit.md) to verify:
   - `max_x1 <= 540.1 pt` across all pages (zero right-margin overflow).
   - `0` orphaned Page-1 `Abstract` or bottom section headings (`>= 2` prose lines below every Page-1 heading; push to Page 2 with its paragraph if Page 1 lacks space).
   - `0` unintended monospace font pages (`LMMono`, `Courier`, etc.) unless the report explicitly contains visible code blocks.
   - `0` unresolved `??` citation or cross-reference tokens.
   - Valid `%PDF` headers (`> 10 KB`) on all archived files in `./papers/` (if present).
2. Remove any temporary testing or scratch scripts from `/tests/` once verification is complete.
