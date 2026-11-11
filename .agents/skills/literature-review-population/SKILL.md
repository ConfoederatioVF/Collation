---
name: literature-review-population
description: >-
  Compiles regional Holocene demographic literature reviews and supplementary population_Stadester settlement gazetteers (_settlements.json) across a user-definable time domain (defaulting to 10000BC - 2000AD if unspecified), with Intellte R Markdown PDF/MD outputs, archived source PDFs, and real GIS/Matplotlib figures. Triggered by /literature-review-population.
disable-model-invocation: true
---

# Regional Demographic Literature Reviews and Settlement Gazetteers (`/literature-review-population`)

This workflow compiles regional demographic and settlement history across a user-definable time domain (defaulting to `10000BC - 2000AD` when the user does not explicitly specify a start or end date) for any target macro-region (e.g. Amazonia, China, India, Sub-Saharan Africa, Russia, Mesoamerica) inside `histmap/1.data_raw/population_regional/<macro_region>/`.

Execution is divided into two sequential phases:
1. **Phase 1: Regional Demographic Literature Reviews (`<region>_literature_review.{Rmd,pdf,md,bib}`)** — Synthesises external scholarly sources on regional population estimates, ecological/hydrological sub-regions or historical polities, settlement hierarchies, and carrying capacities across the target time domain (`10000BC - 2000AD` by default, or the user-specified start/end dates), supported by archived external PDFs (`./papers/`), default Matplotlib charts, and real GIS maps (`./figures/`).
2. **Phase 2: Regional Settlement Gazetteers (`<region>_settlements.{json,Rmd,pdf,md}`)** — Compiles a comprehensive JSON gazetteer (`120–250+` individual settlements per region) in the exact `population_Stadester` structure across the same time domain, accompanied by a concise supplementary tabular report (`<region>_settlements.{Rmd,pdf,md}`).

---

## Core Mandates (Apply to All Phases and Subagents)

### 1. Source Independence & Archiving
- **Forbidden Global Fallbacks**: Never cite or use global macro-demographic datasets or urban fallback compendia (`Chandler`, `Modelski`, `McEvedy & Jones`, `HYDE`, `KK10`, `Buringh`, `Populstat`, `Maddison`). All population history and settlement series must be derived from regional archaeological, epigraphic, cadastral, tax/tribute, colonial/imperial, and early census scholarship.
- **Forbidden Internal Datasets**: Never extract population estimates, growth curves, or site counts from internal Confoederatio/SVEA files (`population_Substrata`, `OANMAP`, `common/histmap/sites_ia_ras.json5`, `saves/atlas_defacto.naissance`). All demographic data must be researched externally. The sole permitted use of `saves/atlas_defacto.naissance` is inspecting historical polity boundary geometries (`areal masks`) when the user requests polity-binned breakdowns.
- **Mandatory PDF Archiving (`./papers/`)**:
  - Regional scholarship is vulnerable to link rot. Download and archive primary/secondary source PDFs into `<region_dir>/papers/<author_year_short_title>.pdf`.
  - Verify every file in `./papers/` begins with a valid `%PDF` header and is `> 10 KB` (never save HTML landing/error pages as `.pdf`).
  - Open-access repositories (CyberLeninka, Zenodo, JSTOR Open, Archive.org, institutional repositories) and shadow libraries (`Sci-Hub`, `LibGen`, `Anna's Archive`) are permitted to obtain obscure regional monographs and journal articles.
  - Reference archived PDFs in `<region>_literature_review.bib` (`note = {Archived PDF: ./papers/<filename>.pdf}`) and link them in prose where appropriate (`[archived PDF](papers/<filename>.pdf)`).
- **User-Definable Time Domain & Realistic Demographic Trajectories (Default `10000BC - 2000AD`)**:
  - The start and end dates of the demographic series are user-definable; if the user does not explicitly specify a start date, default to `10000BC`, and if the user does not explicitly specify an end date, extend the series to `2000AD`.
  - Avoid noisy, stochastic, or erratic oscillations. Population trajectories across the target time domain must reflect realistic ecological carrying capacities, agricultural/metallurgical transitions, documented epidemic or warfare shocks, and pre-industrial/modern growth rates, anchored in later centuries by tax registers and censuses up to the target end year (`2000AD` by default).

### 2. Prose, Style, and Localization Rules
- **British English (`EN-GB`)**: Use non-Oxford British English (`colonisation`, `urbanisation`, `centre`, `programme`, `kilometres`, `archaeological`, no serial/Oxford comma).
- **Plain Academic Prose (Zero Technobabble)**:
  - Write clear, natural human academic prose. Strictly forbid inflated AI jargon or pseudo-scientific phrasing:
    - *Forbidden*: `"Complete Secular Holocene Demographic Trajectory"`, `"Spatiotemporal Paleodemographic Carrying-Capacity Envelope"`, `"Multi-Scalar Techno-Ecological Regime Shift"`, `"Diachronic Nucleation Vector"`.
    - *Required*: `"Population Estimates"`, `"Regional Subdivisions"`, `"Prehistoric Foragers and Early Farmers (10000BC - 1000BC)"`, `"Classical and Medieval Settlements (500BC - 1500AD)"`, `"Early Modern and Modern Census Era (1500 - 2000AD)"`.
- **Compact Dates (`10000BC`, `1897AD`, `2000AD`)**:
  - Never put a space before `BC` or `AD` in prose, figure labels, or table headers/cells: write `10000BC`, `500BC`, `1AD`, `1200AD`, `1897AD`, `1900AD`, `2000AD` (and ranges such as `1000-1200AD` or `4000-2000BC`).
- **European Decimals & Semantic Abbreviations**:
  - Use commas for decimals (`58,88`, `12,5k`, `1,45M`) and full stops for thousands separators (`1.250`, `20.425`).
- **Plain Hyphens Only**:
  - Replace all em-dashes (`—`), en-dashes (`–`), and `---`/`--` with plain hyphens (`-` or ` - `).
- **Minimal Inline Formatting & Script Transliteration**:
  - Do not mix bold, italics, LaTeX math, and inline code backticks (`\texttt{}`) in prose or tables. Reserve `$...$` exclusively for genuine mathematical formulas.
  - Transliterate non-Latin scripts (Cyrillic, Chinese characters, Devanagari, Arabic, Greek) into Latin script inside tables and body text so XeLaTeX (`Karla` 10pt) never renders missing-glyph boxes.

### 3. Visualisations: Default Matplotlib & Real GIS Maps (`./figures/`)
- **Default Matplotlib Charts**:
  - Use the default Python `matplotlib` style (`plt.style.use('default')`, standard Tab10 palette, white background, subtle grid `alpha=0.3`, `dpi=300`).
  - **No Text/Legend Occlusion**: Never place text annotations over bars, lines, or legends. Use standard Matplotlib legends (`ax.legend(loc='best', frameon=True)` or outside the axes via `bbox_to_anchor`), add `15–20%` upper `ylim` headroom when legends sit inside the plot, and call `fig.tight_layout()`.
- **Real GIS Cartography (No Schematic Scribbles)**:
  - Never draw schematic rectangles, circles, or hand-coded polygons to represent regions or rivers.
  - Every regional basemap (`figures/<region>_regional_map.png`) must use real GIS shapefiles/vectors via `geopandas` / `shapely` / `matplotlib`: Natural Earth 10m/50m coastlines, land, lakes, rivers (`ne_10m_rivers_lake_centerlines`), administrative/country boundaries (`ne_10m_admin_0_countries`, `ne_10m_admin_1_states_provinces`), HydroSHEDS basin polygons, or historical polity geometries from `saves/atlas_defacto.naissance`.
  - Plot real river networks, shaded sub-regional masks, and accurately georeferenced settlement coordinates (`[lat, lon]`) with non-overlapping label placement.
- **Mandatory Optical Verification**:
  - Visually inspect every generated `.png` chart and map using `read_file` before compiling the `.Rmd` to verify that borders, rivers, legends, and labels are legible and non-overlapping.

### 4. Intellte R Markdown (`.Rmd`) & PDF/MD Formatting
- **Template & Author Metadata**:
  - Copy `template.tex` and `crd-mla-numeric.csl` from `E:/Active Projects/Project 1746 - Intellte/core/rticles/intellte/` into each regional directory.
  - Use `authors_line: "Aust Kätzchen"` and `emails: [austkaeztchen@confoederatio.org]`.
  - Include the complete `{r setup, include=FALSE}` override block from [`references/intellte_setup_and_audit.md`](./references/intellte_setup_and_audit.md).
- **Table Rules (`10pt` Inline `longtable`, `valign=top` Headers, Zero Clipping)**:
  - All tables must share the exact `10pt` (`10pt/14pt`) body font size and flow inline across pages via `longtable` (never use `\resizebox` or floating `table` environments that isolate tables onto spare pages).
  - **Top-Aligned Headers (`valign=top`)**: In `col_specs`, use `>{\raggedright\arraybackslash\hyphenpenalty=50\exhyphenpenalty=50}p{%.4f\textwidth}` **without** `\hspace{0pt}` so TeX never breaks before the first word of a header cell. Place `\hspace{0pt}` **only** inside body row cells so long body words hyphenate cleanly without affecting header alignment.
  - **Zero Right-Margin Overflow**: Every page in the compiled `.pdf` must satisfy `max_x1 <= 540.1 pt` (72pt margins on 612pt width).
- **Empty Footnotes Suppression & Zero `??`**:
  - Ensure `template.tex` and `emit_crd_footnotes()` do not output an empty `Footnotes` heading when no footnotes are present.
  - Use Pandoc `[@key]` citations matching `<region>_literature_review.bib` and verify `0` occurrences of `??` in the compiled PDF.

---

## Subagent Management & Anti-Stall Protocol

1. **Regional Parallelisation**:
   - Spawn one subagent (`invoke_subagent` with `TypeName: "self"`, `Model: "inherit"`) per region (or pair of small adjacent sub-regions).
2. **Self-Contained Subagent Prompts**:
   - Every subagent prompt must explicitly state: (a) the forbidden internal/global sources rule, (b) the target time domain (`10000BC - 2000AD` by default, or the user-specified start/end dates) and `./papers/` PDF archiving requirement, (c) the British English plain-prose and `10000BC`/`1897AD`/`2000AD` formatting rules, (d) the path to [`references/intellte_setup_and_audit.md`](./references/intellte_setup_and_audit.md) for the mandatory `{r setup, include=FALSE}` block, and (e) the requirement to visually check all PNG figures (`read_file`) and audit compiled PDFs (`pymupdf`).
3. **Incremental File Generation (Preventing Stream Idle Timeouts)**:
   - Instruct subagents never to draft 150–250+ settlements or an entire 800-line `.Rmd` inside a single massive `<thought>` block. Instead, write data in modular Python generator scripts (`build_<region>_part1.py`, `build_<region>_part2.py`) of 80–120 entries at a time.
4. **Directory-Grouped R Markdown Compilation**:
   - Never run `rmarkdown::render()` on two `.Rmd` files in the same folder simultaneously (intermediate `.tex`/`.aux` files collide). Group parallel compilation jobs by directory.
5. **Handoff Protocol for Stalled Subagents**:
   - If a subagent stalls or exceeds a reasonable runtime, terminate it via `manage_subagents(Action="kill")`, inspect the files already written in its target directory, write a concise handoff prompt listing the exact remaining steps, and spawn a fresh replacement subagent (or execute the final generator script directly).

---

## Step-by-Step Workflow

### Phase 1: Regional Demographic Literature Reviews (`_literature_review`)

1. **Set Up Regional Directories & Template Files**:
   - Create `histmap/1.data_raw/population_regional/<macro_region>/<sub_region>/` along with `./papers/` and `./figures/` subdirectories.
   - Copy `template.tex` and `crd-mla-numeric.csl` from `E:/Active Projects/Project 1746 - Intellte/core/rticles/intellte/` into each regional directory (ensuring `template.tex` suppresses empty `Footnotes` sections).
2. **External Literature Search & PDF Archiving**:
   - Search regional archaeological, historical, cadastral, and census literature covering the target time domain (`10000BC - 2000AD` by default, or the user-specified start/end dates).
   - Download and verify at least 15–35+ source PDFs per region into `./papers/` and build `<region>_literature_review.bib`.
3. **Generate Real GIS Maps & Default Matplotlib Figures**:
   - Generate `figures/<region>_regional_map.png` using real Natural Earth / HydroSHEDS / administrative boundaries and settlement coordinates.
   - Generate 2–3 default Matplotlib demographic charts (covering the full time domain `10000BC - 2000AD` by default: regional/sub-basin trajectories, ecological zone distributions, or urban hierarchy charts) with zero text occlusion.
   - Inspect all `.png` files with `read_file` to confirm visual quality.
4. **Draft & Compile `<region>_literature_review.{Rmd,pdf,md}`**:
   - Write `<region>_literature_review.Rmd` using the `{r setup, include=FALSE}` block from [`references/intellte_setup_and_audit.md`](./references/intellte_setup_and_audit.md), plain academic British English headings (`Population Estimates`, `Regional Subdivisions`, chronological period sections up to the target end date, `2000AD` by default), and `render_table_template()` / `render_figure_template()`.
   - Render `.pdf` and `.md` via `Rscript.exe` and run the `pymupdf` check (`max_x1 <= 540.1 pt`, `qmarks == []`).

### Phase 2: Regional Settlement Gazetteers (`_settlements`)

1. **Compile `<region>_settlements.json` in `population_Stadester` Format**:
   - Build `<region>_settlements.json` using incremental Python generator scripts so that each region contains **120–250+ individual settlements** spanning the target time domain (`10000BC - 2000AD` by default: Prehistoric/Ancient, Classical/Medieval, and Early Modern/Modern Census periods).
   - **Split all compound sites**: Every archaeological site, hillfort, town, fort, mission, trading post, and census town must be an individual entry with its own `[lat, lon]` coordinates.
   - **Exact `population_Stadester` JSON Schema**:
     ```json
     {
       "<Settlement Name>-<Country>": {
         "name": "<Settlement Name>",
         "other_names": ["<Historical Name 1>", "<Alternative Name 2>"],
         "coords": [12.3456, 78.9012],
         "country": "<Country>",
         "key": "<Settlement Name>-<Country>",
         "population": {
           "-4000": 80,
           "1000": 4500,
           "1500": 12000,
           "1800": 18500,
           "1900": 42300,
           "2000": 185000
         }
       }
     }
     ```
   - **Positive Integers Only**: Every value in `.population` must be an integer `> 0`. Never include `0` population entries (as `common/mapmodes/stadester.js` computes settlement lifespan bounds from the minimum and maximum keys of `.population`).
2. **Draft & Compile `<region>_settlements.{Rmd,pdf,md}`**:
   - Create `<region>_settlements.Rmd` using the setup block and dynamic JSON loader chunk in [`references/intellte_setup_and_audit.md`](./references/intellte_setup_and_audit.md).
   - Keep prose minimal and factual (two short introductory paragraphs in plain British English without technobabble), followed by chronological/sub-regional `10pt` `longtable` directories and a complete settlement directory read directly from `<region>_settlements.json`.
   - Render `<region>_settlements.pdf` and `<region>_settlements.md` via `Rscript.exe`.
3. **Final Verification & Cleanup**:
   - Run the automated verification script in [`references/intellte_setup_and_audit.md`](./references/intellte_setup_and_audit.md) across all `_literature_review.pdf`, `_settlements.pdf`, and `_settlements.json` files to verify schema compliance, top-aligned headers (`valign=top`), `max_x1 <= 540.1 pt`, and `0` unresolved `??` tokens.
   - Remove any temporary helper scripts from `/tests/` once verification completes.

Once this process completes, ensure you run the `/humanise` skill if it exists to ensure your paper is in compliance.