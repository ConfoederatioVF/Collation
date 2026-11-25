---
name: population-regional-study
description: End-to-end Operation Viscount regional demographic study: Pass-1/Pass-2 OHM + academic HGIS masks, dual HYDE 3.5 + KK10 Matérn kriging substrata, evidence-only settlement gazetteers, 3-Phase metropolitan reconciliation, Intellte RMarkdown publishing, and persistent spatial-overlay Dataview historical toponymy (2-Pass, n <= 24 cap) with incremental CI/CD caching across all 14 canonical macro-regions.
---

# Operation Viscount — Regional Population & Settlement Study (`/population-regional-study`)

Governs all `14` canonical macro-regions defined in [viscount_precedence.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5), benchmarked strictly against **`POLARIS`**. All numeric thresholds, policies, and 14-region defaults live once in [viscount_skill_profiles.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/config/viscount_skill_profiles.json5).

> [!CAUTION]
> **Anti-Stub Guardrails vs Completion**: Gatekeeper numeric floors (`>= 35` settlements, `>= 2,5x` c14 sites, `>= 15` valid PDFs, `>= 20` `.bib` keys, `>= 350` lines / `>= 2.500` words) reject empty stubs ONLY. They are NEVER stopping quotas. Completion requires asymptotic saturation (`marginal_gain <= 2,0%`, `unaccounted == 0`), visual verification by independent auditors, and exit `0` across all Node.js gatekeepers.

---

## 7 Non-Negotiable Functional Laws

1. **Two-Pass OHM + Academic HGIS Masks & Separate Auditor (`<= 2` Pass-2 Subagents)**: Use OpenHistoricalMap (OHM) sub-administrative divisions as baseline substrata enriched by period-specific academic HGIS datasets, with mandatory degenerate-topology repair. NEVER use modern 2025 borders on pre-1945 masks/figures, NEVER use videogame maps (`EU4`/`Vic2`/`CK`/`HoI`), `aourednik/historical-basemaps`, or coastal-gapped raw Cliopatria (use coastal-complete `atlas_dejure.naissance`; restrict `atlas_defacto.naissance` strictly to `z = 1` fallback). Pass-2 mask authoring uses **at most 2 subagents** (`1` `mask_builder` + `1` separate read-only `mask_auditor` iterating over regional bbox crops).
2. **Dual HYDE 3.5 + KK10 Catchments & Per-Project Isolation**: Tighten kriging catchments as a function of combined believed density `max(D_hyde35, D_kk10)` plus a guaranteed global minimum catchment density floor (`<= 25.000 km²`, `>= 5` catchments per `100k km²`) so HYDE false-zero pockets never starve kriging. Use metric-isotropic radial distance (never Manhattan BFS) and keep biophysical/fluvial tuning strictly inside `config/<slug>_dasymetric_admixture.json5` (zero mutations to shared `Viscount*` defaults).
3. **Strictly Evidence & Canonical-Literature Populations (Zero Heuristics)**: Derive every settlement population purely from primary historical evidence and canonical demographic literature. NEVER stamp pseudo-uniform distributions, placeholder tiers, arbitrary clamps, deterministic jitter, or unattested synthetic pre-census back-projections/CDFs. Use read/write-only evidence swarms + `@auditor` when historical tables require case-by-case assessment.
4. **Structural Rule for Merging & 3-Phase Anti-Double-Counting**: Points sharing the same city-proper municipal boundary (accidental splits or intra-municipal *arrondissements*, *boroughs*, *wards*, municipal-core *ilçes*, *shiyakhas*, urban *raions*, *Stadtbezirke*, *ku*, *quận*, *alcaldías*) MUST be merged up to that single top-level municipality (**capital city status overrides largest population**). NEVER merge multiple distinct municipalities belonging to the same metropolitan area together — preserve independent extra-municipal suburbs and reconcile mixed `metro` / `city_proper` / `suburb` estimates via the 3-Phase subtraction & negative-residual redistribution law (compatible with `1975–2025` GHSL DEGURBA).
5. **Persistent Spatial-Overlay `city_metadata/`, Compact 2-Pass Toponymy & Global `n <= 24` Cap**: `Dataview/data/stadester/stadester_2.0/city_metadata/` (`00_capitals.json` Priority Tier 0 first, plus `01_centaur.json..14_nicethi.json` in Dataview-compatible `historical_names: [{ date, name }]` format) operates as a **persistent `[lng, lat]` point overlay** mapping onto the nearest underlying settlement point (locking Tier-0 capitals and preventing name overrides). Run strict **2-Pass Toponymy**:
   - **Pass 1 (`max_pop > 10k` at any point in history OR capital city)**: Extract compact `{ coords: [lng, lat], names: { "yyyy.m.d": "Name" } }` adaptive batches (`40–200` cities, `<= 24` batches/wave) and resolve from knowledge base via `Gemini 3.8 Flash` workers + separate read-only `toponymy_auditor` under a **hard global `n <= 24` concurrent subagent ceiling**.
   - **Pass 2 (Residual settlements `<= 10k`, non-capital)**: **ZERO LLM agents** — resolve deterministically via World Historical Gazetteer (WHG) + GeoHack heuristics (`resolve_residual_toponymy_whg_geohack.js`).
   - All toponyms obey the **3 Structural Rules for Toponyms** (de facto occupying/ruling authority's preferred name in contemporaneous English-language Latin transliteration; period-accurate historical names rather than modern retrofits; capital cities always retain canonical capital names), non-destructive full-history simplification at `[lng, lat]`, and case-insensitive `.other_names` deduplication.
6. **GitHub-Safe Filenames & Source Concentration Caps**: Keep chapter stems `<= 42` chars, all `.Rmd`/`.pdf`/`.md`/`.bib`/figure/`./papers/` filenames `<= 72` chars, and repo-relative paths `<= 180` chars across SVEA and Intellte. Cap single-source in-text citation share `<= 20%`, top-3 sources `<= 45%`, and require `>= 75%` `.bib` utilisation.
7. **Incremental CI/CD Sharded Sync & Node.js Gatekeepers (`n <= 24` Global Swarm Cap)**: Never rebuild unmodified Dataview or Intellte namespaces (e.g. `CENTAUR`) when updating another region. Never launch more than **`n = 24` concurrent subagents** globally (across toponymy, geocoding, or any swarm), keep bulk geocoding and Pass-2 residual toponymy strictly deterministic ETL (`0` LLM agents), run all audits via fast Node.js gatekeepers, and wrap all heavy commands via `run_bounded.js`.

---

## Reference Modules (Read Before Executing Each Stage)

- **Config (Single Source of Truth)**: [viscount_skill_profiles.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/config/viscount_skill_profiles.json5)
- **Stages A–B (Masks, OHM/HGIS, Kriging & Subadmin Disaggregation)**: [hgis_masks_and_kriging.md](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/references/hgis_masks_and_kriging.md)
- **Stages C & F (Gazetteers, Evidence Populations, Metro Reconciliation & Toponymy)**: [gazetteers_and_toponymy.md](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/references/gazetteers_and_toponymy.md)
- **Stage D (Prose, Path Limits, Citation Diversity, Figures & Intellte PDFs)**: [publishing_and_figures.md](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/references/publishing_and_figures.md)
- **Cross-Cutting (Swarms, Incremental CI/CD & `run_bounded.js`)**: [swarm_and_compute_governance.md](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/references/swarm_and_compute_governance.md)

---

## Canonical Sequential Pipeline (`A -> B -> C -> D -> E -> F`)

### Stage A — Precedence Setup, Pass-1 HGIS EDA & Pass-2 Bounded Areal Masks (`Gatekeeper A`)
1. Register `<PROJECT_KEY>` in `viscount_precedence.json5` (`z_priority: 14 -> 1`) and create shallow 2-level chapter folders (`stem <= 42` chars) sharing `_shared/{fonts,template,_gis_cache,sites_*,subadmin_hgis}`. Never touch sibling projects or legacy `population_Substrata.*`.
2. **Pass-1 (HGIS EDA Swarm)**: Dispatch a preliminary EDA swarm (`<= 24` concurrent) to harvest **OHM** sub-administrative divisions + period-specific academic HGIS datasets + enumerations across every overlapping HYDE window (`100y` to `1700 AD`, `10y` to `1950 AD`, `1y` `1951–2025`) into `<slug>_hgis_inventory.json5`.
3. **Pass-2 (Max 2 Subagents: `mask_builder` + separate read-only `mask_auditor`)**:
   - `mask_builder` merges OHM + specific HGIS with full degenerate-topology repair, emits dual outputs (`*_areal_mask.png` + smooth vector `*_subregions.geojson`) and all overlapping HYDE `subadmin_id_<year>.png` rasters (`atlas_defacto.naissance` strictly `z = 1` fallback), and renders regional bbox crops (`/tests/mask_crops/`, `/tests/subadmin_crops/`).
   - `mask_auditor` inspects every crop via `read_file` and iterates defects back to `mask_builder` until every crop matches historical reality, then signs `_shared/mask_audit_signoff.json`.
4. **Gatekeeper A**:
   ```powershell
   node .agents/skills/population-regional-study/scripts/audit_areal_masks.js histmap/1.data_raw/population_regional/<PROJECT_KEY> --require-auditor-signoff --render-overlays
   ```

### Stage B — Archaeological Substrata, HYDE 3.5 + KK10 Kriging & Mass-Conserving Disaggregation (`Gatekeepers B1–B3`)
1. Probe SVEA's `c14_cleaned_dedup.csv` inside the domain mask, audit heritage APIs for `NULL`/undated/fuzzed records, and composite multi-repository primary registers across **every** jurisdiction in `jurisdiction_source_matrix` (`0` Wikipedia scraping; crowd `<= 25%`, regional/monograph `>= 50%` per jurisdiction).
2. Generate catchments driven by **dual HYDE 3.5 + KK10 believed density** (`max(D_hyde35, D_kk10)`) + minimum coverage floor (`<= 25.000 km²`, `>= 5` per `100k km²`), importing `250 km` cross-frontier sites (`is_frontier_buffer: true`) from completed neighbours.
3. Run `ViscountMaternKriging` (`run_bounded.js --lock gpu_compute`) using `ViscountUrbanMask`, metric-isotropic radial covariates, and project-isolated `config/<slug>_dasymetric_admixture.json5`. Apply mass-conserving pycnophylactic sub-administrative disaggregation (`worst_unit_rel_err <= 1e-4`, logged in `subadmin_mass_conservation_audit.json`) and seam blending (`ViscountSubstrataMosaic` + `ViscountSubstrataSeamBlend`).
4. **Gatekeepers B1–B3**:
   ```powershell
   node .agents/skills/population-regional-study/scripts/audit_kriging_sharpness.js <domain_dir>
   node .agents/skills/population-regional-study/scripts/audit_border_cliffs.js <domain_dir> --check-inter-region --project <KEY>
   python .agents/skills/population-regional-study/scripts/render_and_audit_kriging_visuals.py <domain_dir> --render-only
   ```
   Inspect every PNG in `<domain_dir>/diagnostics_visual/` via `read_file`, sign `<domain_dir>/config/visual_verification_manifest.json`, and re-run `audit_kriging_sharpness.js <domain_dir> --require-visual-manifest`.

### Stage C — 4-Wave Exhaustive Settlement Gazetteers & Metro Accounting (`Gatekeeper C`)
1. **Wave 1**: Full-row per-jurisdiction census/cadastre ingestion (`0` `LIMIT`/`head`/Top-N caps; crowd `<= 20%` per jurisdiction). Apply `consolidate_municipal_districts.js` (with `--municipal-boundaries=<geojson>` where available) so accidental split points and intra-municipal districts inside the same city-proper municipal boundary merge up to one municipality (capital overrides largest population), whilst distinct extra-municipal suburbs in the same metro area remain separate; tag `population_scope` (`city_proper` / `suburb` / `metro`).
2. **Wave 2**: Archive `>= 15` SHA-256-unique `%PDF-` primary monographs/cadastres (`> 10,24 kB`, filename `<= 72` chars) per chapter into `./papers/` covering every jurisdiction; extract 100% of settlement and sub-administrative enumeration tables.
3. **Wave 3**: Pre-census longitudinal backfill using strictly primary evidence and canonical literature (read/write-only swarms `<= 24` concurrent + `@auditor` for non-tabular sources; zero pseudo-uniform tiers, clamps, or synthetic back-projection; enforce `foundation_year`, pre-consolidation cutoffs, and Year:Settlement chronology baselines in `<slug>_gazetteers.json5`).
4. **Wave 4+**: Sub-Region × Era gap-hunter sweeps until `marginal_gain <= 2,0%`, `unaccounted == 0`, `0` empty inhabited sub-regions, `0` variant-spelling duplicates `<= 25 km`, and `0` homonym hijacks.
5. **Gatekeeper C**:
   ```powershell
   node .agents/skills/population-regional-study/scripts/verify_gazetteer_exhaustiveness.js --project-dir histmap/1.data_raw/population_regional/<PROJECT_KEY> --require-sources --require-saturation --audit-temporal-density --audit-spatial-bounds
   ```

### Stage D — Non-Heuristic Read/Edit-Only Reporting, Vector Figures & Intellte Publishing (`Gatekeepers D1–D3`)
1. Spawn `MAX 1 CHAPTER PAIR PER WORKER` (`<= 24` concurrent; `Gemini 3.8 Flash` -> `Hydrogen` in-place); read/edit-only prose (`0` prose-generation scripts) following `/humanise` (McEvedy & Jones per chapter; Klein Goldewijk at root `studies_on_population.Rmd`). Include scraped sub-administrative enumeration tables in relevant chapters.
2. Enforce GitHub-safe lengths (`stem <= 42`, filename `<= 72`, repo path `<= 180` chars), citation concentration caps (`single <= 20%`, `top3 <= 45%`, `bib utilisation >= 75%`), `0` non-code monospace, undivided `# Abstract`, `# Sources`, and all 5 `POLARIS` vector figure laws (`save_viscount_figure(..., strict_layout=True)`, independent `@verifier` cropped-panel `read_file` sign-off in `figures/visual_check.json`, strict mask -> figure -> PDF freshness).
3. Compile PDFs (`xelatex` via `run_bounded.js`, `<= 2` concurrent builds) and run **Gatekeepers D1–D3**:
   ```powershell
   node .agents/skills/population-regional-study/scripts/audit_academic_prose.js <project_dir>
   node .agents/skills/population-regional-study/scripts/audit_figure_scripts.js <project_dir>
   node .agents/skills/population-regional-study/scripts/audit_rmd_and_bib_calibre.js <project_dir> --require-visual-check --require-compiled-pdfs
   ```

### Stage E — Serialised Stadestér 2.0 Shards, 3-Phase Metro Reconciliation & `Velkscala` (`Gatekeeper E`)
1. Wrap every Stage E run with `run_bounded.js --lock stadester_velkscala --project <KEY> --wait-seconds 180`.
2. Execute SVEA Stage 2 (`population_Stadester.js` with `ViscountGazetteerLoader` + `StadesterMetroReconciler` 3-Phase reconciliation across `-10000..1974` seamlessly coupled with `stadester_ghsl.js` `1975–2025` DEGURBA, intra-project UUD isolation, capital-name override guard, and CI `.other_names` deduplication) and Stage 3 (`population_Stadester_transform.js`) emitting `< 200 MB` shards to transform, visualisation, and Dataview `stadester_2.0/` (preserving `1.0`/`1.1`).
3. **Gatekeeper E**:
   ```powershell
   node .agents/skills/population-regional-study/scripts/audit_velkscala_reconciliation.js --project <KEY>
   ```
   Render and optically inspect `06_velkscala_<project>_verification.png` via `read_file` and update `visual_verification_manifest.json`.

### Stage F — Persistent Spatial-Overlay `city_metadata/`, 2-Pass Toponymy & Incremental CI/CD (`Gatekeeper F`)
1. **2-Pass Compact Extraction**: Extract settlements into strict Pass-1 (`max_pop > 10k` or capital; compact `{ coords: [lng, lat], names: { "yyyy.m.d": "Name" } }` adaptive batches `40–200` cities, `<= 24` batches/wave in `pass1/`) and Pass-2 residuals (`<= 10k`, non-capital in `pass2/residuals.json`):
   ```powershell
   node .agents/skills/population-regional-study/scripts/extract_missing_city_metadata.js --project=<KEY>
   ```
2. **Pass 1 (`max_pop > 10k` or capital — Knowledge-Base Swarm, Hard `n <= 24` Cap)**: Run `run_historical_names_swarm.py` (`asyncio.Semaphore(24)`) across `pass1/batch_*.json` using `Gemini 3.8 Flash` workers + strictly separate read-only `toponymy_auditor` enforcing the 3 Structural Rules for Toponyms and zero-tolerance single-error send-back into `pass1/auditor_signoff.json`.
3. **Pass 2 (Residual Settlements — Deterministic WHG + GeoHack, `0` LLM Agents)**:
   ```powershell
   node .agents/skills/population-regional-study/scripts/run_bounded.js -- node .agents/skills/population-regional-study/scripts/resolve_residual_toponymy_whg_geohack.js --project=<KEY>
   ```
4. **Non-Destructive Merge, Full-History Simplification & Case-Insensitive Dedup**: Commit Pass-1 + Pass-2 payloads exclusively into Dataview-compatible `00_capitals.json` and the target regional shard without clobbering existing histories or capital identities:
   ```powershell
   node .agents/skills/population-regional-study/scripts/run_bounded.js --lock dataview_metadata --project <KEY> -- node .agents/skills/population-regional-study/scripts/merge_city_metadata.js --project=<KEY> --require-auditor-signoff
   ```
5. **Gatekeeper F & Gatekeeper S**:
   ```powershell
   node .agents/skills/population-regional-study/scripts/run_viscount_gatekeepers.js --project <KEY> --stage F,S
   ```
   Runs incremental per-shard Dataview cache warming (skipping untouched regions like `CENTAUR`), Dataview `tsc -b` + `vite build`, Intellte incremental dirty-file sync & `rmd_dom` LF cache check, `audit_city_metadata.js` (checking spatial bbox capitals, split capitals, CI `.other_names` dedup, Latin canonical script, and 2-pass sign-off), `audit_shell_and_scripts.js` (enforcing `n <= 24` and Pass-2/geocoding LLM bans), and `run_bounded.js --audit-orphans`. Remove temporary `/tests/` artefacts before finishing.
