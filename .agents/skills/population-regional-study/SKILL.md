---
name: population-regional-study
description: End-to-end Operation Viscount regional demographic study, settlement gazetteer, non-stationary Matérn kriging substrata, Intellte RMarkdown publishing, and Dataview historical toponymy pipeline. Supersedes the legacy /literature-review-population workflow using POLARIS as the holotype across all 14 canonical macro-regions.
---

# Operation Viscount — Regional Population & Settlement Study (`/population-regional-study`)

This skill governs the end-to-end execution of an Operation Viscount regional demographic reconstruction, benchmarked strictly against **`POLARIS`** across all `14` canonical macro-regions defined in [viscount_precedence.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5).

> [!IMPORTANT]
> **Anti-Stub Guardrails vs True Completion Criterion**: All numeric floors enforced by automated gatekeepers (`>= 35` settlements, `>= 2,5x` `c14_cleaned_dedup.csv` archaeological sites, `>= 15` valid `%PDF-` files in `./papers/`, `>= 20` `.bib` keys, `>= 350` lines and `>= 2.500` words per sub-chapter review) are strictly **anti-stub guardrails**. They MUST NEVER be used as target counts or stopping quotas. A region is complete ONLY when exhaustive multi-wave enumeration reaches asymptotic saturation (`marginal_gain <= 2,0%` and `unaccounted == 0`).

---

## Reference Architecture & 14-Region Profiles (Read Before Executing Each Stage)

0. [viscount_skill_profiles.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/config/viscount_skill_profiles.json5) — Declarative 14-region defaults (`projection_class`, `has_micro_islands`, `max_adm2_area_km2`, `default_modern_census_year`, `default_border_splice_years`, `multi_script_countries`, `adm0_canonical_overrides`, `arch_site_qualifiers`, `romanisation_equivalences`). Override per-project inside `<slug>_gazetteers.json5` and `<slug>_areal_masks.json5`.
1. [census_and_archaeology_ingestion.md](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/references/census_and_archaeology_ingestion.md) — 4-Wave Asymptotic Maximum-Saturation Loop, Anti-Circularity Firewall, 14-region multilingual institutional discovery (banning Wikipedia scraping), upstream API forensics, `>= 90%` `.bib` DOI/URL coverage, compound splitting, `foundation_year` enforcement and GeoNames/Wikidata homonym purging.
2. [kriging_and_masks_guide.md](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/references/kriging_and_masks_guide.md) — Manifest-driven Three-Regime Partitioning Law (Regimes I–III + micro-island/high-latitude guards + Gatekeeper `A2`), scale-adaptive `ADM2 x HydroBASINS` catchments, biome/taphonomic conditioning, parameter-free Freeman-Tukey + 2D Paciorek-Schervish Matérn kriging, `250 km` cross-frontier belts and end-to-end `Velkscala` reconciliation (`Gatekeeper E2`).
3. [viscount_rmd_template.md](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/references/viscount_rmd_template.md) — Non-heuristic Read/Edit-Only `/humanise` prose (write in the style of McEvedy & Jones per sub-chapter, write in the style of Klein Goldewijk at root), multi-script romanisation with `0` `\ufffd` glyphs, Intellte `longtable` geometry (`max_x1 <= 540,5 pt`, non-blank Page `1`, `# Sources`, empty `\endhead`, `0` `??`), strict default Matplotlib theme (`plt.rcdefaults()`, `DejaVu Sans`, 4-sided spines, rendered `$...$` MathText, European `FuncFormatter` ticks) and aspect-matched equal-area figure standards.
4. [swarm_and_visual_qa_protocol.md](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/references/swarm_and_visual_qa_protocol.md) — Plan-Gate governance, Coordinator Overlay Send-Back Loop, `Gemini 3.8 Flash` (`Hydrogen` in-place fallback) swarm with mandatory `@verifier` + `monitor` workers, Read/Edit-Only editorial subagents, Puppeteer/Selenium challenge compliance, Stage F toponymy protection and per-panel cropped `read_file` verification.

---

## Canonical 6-Stage Execution Pipeline (All 14 Macro-Regions)

### Stage A — Precedence Registration, Shared GIS Setup & Mask Audit (`Gatekeeper A2`)
- Look up `<PROJECT_KEY>` in [viscount_precedence.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5) and [viscount_skill_profiles.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/config/viscount_skill_profiles.json5). Inverse z-index order (`z_priority: 14 -> 1`) governs inter-Viscount border overlap resolution (`NICETHI (14)`, `AUSTRAL (12)`/`(13)`, ..., `PRETA (3)`, `POLARIS (2)`, `CENTAUR (1)`).
- Organise chapters into shallow `2`-level chronological/sub-regional folders sharing `_shared/{fonts,template,_gis_cache,sites_*}` (with SHA-256 deduplication across repeated `./papers/` PDFs).
- Read shared Natural Earth vector boundaries from `histmap/1.data_raw/population_regional/_shared/_gis_cache/`.
- Declare `regime_transitions`, `annual_continuity_span`, `border_splice_years`, `geography_profile` (`projection_class`, `has_micro_islands`, `max_adm2_area_km2`) and `script_profile` inside `<slug>_gazetteers.json5` and `<slug>_areal_masks.json5` inside `histmap/1.data_raw/population_regional/<PROJECT_KEY>/`.
- **Gatekeeper A2 Check (Coordinator Overlay Send-Back Loop)**:
  ```powershell
  python .agents/skills/population-regional-study/scripts/audit_areal_masks.py histmap/1.data_raw/population_regional/<PROJECT_KEY> --render-overlays
  ```
  Verify `0` starved masks, `0` synthetic rectangular `box()` cuts, strict chronological domain bookends, and `0` stranded settlements (with micro-island pinning when `has_micro_islands: true`). Inspect every `verify_<stem>_overlay.png` via `read_file` and send defective masks back before Stage C or Stage D proceeds.
- **Isolation Rule**: Never overwrite legacy ethnographic `population_Substrata.*` prior directories or sibling Viscount macro-regions.

### Stage B — Exhaustive Multi-Wave Census & Gazetteer Saturation (`Gatekeeper A`)
Execute the **4-Wave Asymptotic Maximum-Saturation Loop** across every spatiotemporal sub-mask:
- **Wave 1**: Full-row programmatic ingestion of official decennial/quinquennial censuses, dynastic/colonial/fiscal cadastres and national gazetteers (`0` `LIMIT`, `head`, `slice`, or Top-100 caps). Never scrape Wikipedia categories for archaeological sites. Register all candidates in `<stem>_source_ledger.json5`.
- **Wave 2**: Download `>= 15` primary monographs, cadastres and statistical compendia into `<chapter_dir>/papers/` (validating `> 10,24 kB` and `%PDF-`; use Puppeteer/Selenium with `25–30s` wait on JS/DDoS-Guard walls). Extract 100% of settlement tables and appendices.
- **Wave 3**: Longitudinal pre-census backfill (`Gemini 3.8 Flash` swarm + `@verifier` + `monitor`; escalate in-place to `Hydrogen` if stalled) until `post_1995_only_ratio <= 0,45`, adjacent decennial jump `<= 3,0x`, `0` pre-`foundation_year` anachronisms and `0` unsplit compound `"A & B"` modern municipalities.
- **Wave 4+**: Sub-mask gap-hunter sweeps per county/district/watershed until `marginal_gain <= 2,0%` and `unaccounted == 0`. Cross-check major collisions against GeoNames/Wikidata to purge homonym hijacks.
- **Gatekeeper A Check**:
  ```powershell
  python .agents/skills/population-regional-study/scripts/verify_gazetteer_exhaustiveness.py <path_to_gazetteer_or_shard> --require-sources
  ```
  *(Pass `--mode=compiled --geonames-audit <dump.txt>` for compiled Stadestér 2.0 shards.)*

### Stage C — Baseline Probe, API Forensics & Non-Stationary Kriging (`Gatekeepers C1–C3`, `E2`)
- **Stage C0**: Plot SVEA's global `c14_cleaned_dedup.csv` baseline inside the macro-region mask first to quantify baseline sparsity, and audit scraped heritage APIs/catalogues for `NULL`/undated record leakage, coordinate fuzzing, monument-complex double counting and overlapping local periodisations.
- Composite all available multilingual national, provincial and academic archaeological registers (`>= 2,5x` `c14_cleaned_dedup.csv` inside mask; aim for full institutional saturation).
- Aggregate to `ADM2` catchments — or intersect with `HydroBASINS` Level 6–7 watersheds wherever `ADM2` polygons exceed `max_adm2_area_km2` (`25.000 km²`) — applying biome/aridity-conditioned `Q75 + IQR` taphonomic outlier shrinkage before parameter-free Freeman-Tukey `ViscountMaternKriging` + `ViscountResidualCovariates` (`250 km` cross-frontier conditioning belt + $C^1$ seam feathering).
- Write config strictly in `histmap/3.data_transform/population_Substrata.viscount/config/<slug>.json5`.
- **Mandatory Gates**:
  1. **Gatekeeper C1 (Sharpness & Covariates)**: `python .agents/skills/population-regional-study/scripts/audit_kriging_sharpness.py <domain_dir>` (`raw_tau1_dimensionless <= 1,8`, `raw_nugget_to_sill_ratio < 0,45`, active WLS betas, `>= 2,5x` c14 multiplier).
  2. **Gatekeeper C2 (Border Discontinuities)**: `python .agents/skills/population-regional-study/scripts/audit_border_cliffs.py <domain_dir>`.
  3. **Gatekeeper C3 (Cartographic Render & Optical `read_file` Sign-off)**: Run `render_and_audit_kriging_visuals.py <domain_dir> --render-only`, inspect every PNG via `read_file`, write signed `<domain_dir>/config/visual_verification_manifest.json`, and re-run without `--render-only` (`hp15_mean >= 0,08`, `dx_mean >= 0,04`).

### Stage D — Non-Heuristic Read/Edit-Only Reporting & Intellte Publishing (`Gatekeepers D1–D2`)
- Spawn at most **`MAX 1 CHAPTER PAIR PER WORKER`** (`Gemini 3.8 Flash` -> `Hydrogen` in-place). Enforce a **read/edit-only** editorial pass (`read_file` + `edit_file` only; zero Python/regex prose scripts): regional sub-chapters follow **McEvedy & Jones** plain historical prose, and root `studies_on_population.Rmd` follows **Klein Goldewijk** synthesis prose.
- Comply strictly with `/humanise`: non-Oxford `EN-GB` (`mediaeval`), European decimals (`58,88`), dot thousands (`110.642`), Unicode `km²`, consistent era formatting (never `10.000BC` or `March 1953AD`), zero leaked JSON/snake_case schema keys, zero redundant `word (n=X)` tics, zero sub-chapter `@McEvedy`/`@KleinGoldewijk`/`Populstat`/`Chandler1987`/`Modelski2003`/`Maddison` or internal SVEA dataset citations, zero `n < 25` Zipf plots, `>= 85%` per-chapter / `>= 90%` project DOI/URL `.bib` coverage, `# Sources` (never `# References`), non-blank Page `1` cover hero (`<= 0,52\textheight`), empty continuation `\endhead`, `0` `\ufffd` glyphs, `0` unescaped Vue `<Tag>` tokens, and staged per-chapter JSON caches.
- Crop multi-panel figures into individual panels (`1A..nD`), inspect every cropped panel via `read_file` and sign `<chapter_dir>/figures/visual_check.json`. Every Matplotlib figure MUST use strict default styling (`plt.rcdefaults(); plt.style.use("default")` with `DejaVu Sans` sans-serif regular weight, intact 4-sided boxed spines and zero `font.family = "serif"` or `seaborn` style overrides), render mathematical symbols and exponents via MathText (`$\nu = 3/2$`, `$\tau_1 = 1{,}41$`, `$R^2$`, `$\log_{10}$`, never raw ASCII `nu = 3/2`, `tau1=`, or `R-squared`), format fractional axes ticks with European decimal commas (`FuncFormatter` via [viscount_plot_utils.py](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/histmap/1.data_raw/population_regional/_shared/viscount_plot_utils.py)), map category keys via explicit display dictionaries rather than `.replace("_", " ").title()` (which corrupts `II`/`III` into `Ii`/`Iii`) and plot substantive empirical diagnostics (e.g. empirical semivariograms rather than flat `0,998` bar charts or technobabble titles).
- Compile PDFs (`xelatex`), synchronise to Intellte (`sync_viscount_region.js --project=<KEY> --build`), and run **Gatekeepers D1 & D2** (plus standalone [audit_figure_scripts.py](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/scripts/audit_figure_scripts.py)):
  ```powershell
  python .agents/skills/population-regional-study/scripts/audit_academic_prose.py <project_or_chapter_dir>
  python .agents/skills/population-regional-study/scripts/audit_figure_scripts.py <project_or_chapter_dir>
  python .agents/skills/population-regional-study/scripts/audit_rmd_and_bib_calibre.py <project_or_chapter_dir> --require-visual-check
  ```

### Stage E — Stadestér 2.0 Shards & `population_Velkscala` Reconciliation (`Gatekeeper E2`)
- Run SVEA Stage 2 (`population_Stadester.js` via `ViscountGazetteerLoader` + `stadester_uud.js` without inserting project-specific string hacks into universal code) and Stage 3 (`population_Stadester_transform.js`) to emit `< 200 MB` macro-region shards into `histmap/3.data_transform/population_Stadester.transform/stadester/`, `histmap/5.data_visualisation/stadester/stadester_2.0/` and `F:/Active Projects/Project 1436 - Dataview/data/stadester/stadester_2.0/` (`version: "2.0"`), preserving `stadester_1.0/` and `stadester_1.1/` isolation and evicting stale `stadester_2.0_*.json` caches.
- Run **Gatekeeper E2 (`audit_velkscala_reconciliation.py --project <KEY>`)** verifying `0` `png.data[p4 + 3] > 0` float32 alpha-byte bugs, `0` circular `stadester_rural_*` reads in kriging, `0` rural Swiss-cheese zero-holes, `0` `< 5k` / micro-island drops in `population_Velkscala`, `max(200, hyde_interval)` hiatus compliance and GHSL DEGURBA suburb subtraction.

### Stage F — `@verifier` Toponymy Swarm & Annual Cross-Repo CI/CD (`Gatekeeper F`)
- Extract candidate missing historical toponyms (`extract_missing_city_metadata.js`), run batched `30`-city `Gemini 3.8 Flash` swarm enrichment paired with an independent `@verifier` + `monitor` (respecting the 14-region script profile and historical romanisation equivalences in [viscount_skill_profiles.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/config/viscount_skill_profiles.json5)), and merge safely into `Dataview/data/stadester/stadester_2.0/city_metadata.json` via `merge_city_metadata.js`.
- Run **Cross-Repo Gatekeeper F**:
  ```powershell
  node .agents/skills/population-regional-study/scripts/verify_downstream_ci_cd.js --project=<KEY>
  ```
  Checks shard parity, Intellte `rmd_dom` LF cache & VitePress build, Dataview per-version isolation + `tsc -b` + `vite build`, annual live `getCitiesAtYear(yr)` continuity across the project's `annual_continuity_span` (`YoY <= 3,0%` outside `border_splice_years`), `city_metadata.json` orphans, and `14`-region script-safe entity integrity (`0` `_viscount_regional` keys, `0` foreign-script spam in Latin-only countries, `0` Signature A/B hijackings).

---

## Hard Stop-Hook Completion & Coordinator Governance

1. **Plan Gates & Remit Isolation**: Draft and confirm plans before major multi-worker waves; never trust worker completion claims without running the gatekeeper scripts and `read_file` inspections directly; replace or escalate stalled workers cleanly (`Gemini 3.8 Flash` -> `Hydrogen` via `swarm{action: "model", ...}`).
2. All 6 Gatekeeper Suites MUST exit `0`: **A** (`verify_gazetteer_exhaustiveness.py`), **A2** (`audit_areal_masks.py`), **C1–C3** (`audit_kriging_sharpness.py`, `audit_border_cliffs.py`, `render_and_audit_kriging_visuals.py`), **D1–D2** (`audit_academic_prose.py`, `audit_rmd_and_bib_calibre.py --require-visual-check`), **E2** (`audit_velkscala_reconciliation.py`), and **F** (`verify_downstream_ci_cd.js --project=<KEY>`).
3. Pre-existing `tests/` helpers preserved; zero temporary test artefacts left in `.agents/` or `tests/`.
