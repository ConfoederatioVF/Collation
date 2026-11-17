---
name: population-regional-study
description: >-
  End-to-end Operation Viscount regional demographic study, settlement gazetteer,
  non-stationary Matérn kriging substrata, Intellte RMarkdown publishing, and Dataview historical toponymy pipeline. Supersedes the legacy /literature-review-population workflow using POLARIS as the holotype across all 14 canonical macro-regions.
---

# Operation Viscount Regional Study (`/population-regional-study`)

This skill governs regional historical demography and urban gazetteer reconstruction across all **14 canonical Operation Viscount macro-regions** (`1: CENTAUR` through `14: NICETHI`). **POLARIS (`order: 2`)** serves as the architectural holotype.

## Canonical Precedence & Macro-Region Sharding

All regional definitions live exclusively under [viscount_precedence.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5) inside `histmap/2.data_cleaning/population_Stadester/config/` (never in root `SVEA/common/`).

- **Inverse (`z-index`) resolution**: `z_priority = order`, resolved descending from `14` down to `1`:
  - `14: NICETHI` -> `13: AUSTRAL` -> `12: JAGUAR` -> `11: QUIPU` -> `10: MAGNETIC` -> `9: HANDBOOK` -> `8: SARAY` -> `7: MANDALA` -> `6: CASTLE` -> `5: INDUS` -> `4: JADE` -> `3: PRETA` -> `2: POLARIS` -> `1: CENTAUR`
- **Shared frontiers**: Higher `z_priority` projects lock frontier pixels and canonical settlement trajectories first; lower `z_priority` projects calibrate residual `B \ A` cells, backfill uncovered historical years on shared settlements without overwriting higher-order trajectories, and absorb one-sided $C^1$ raised-cosine seam feathering (`200 km` / `24 px`).
- **Stadestér sharding**: Final Stadestér 2.0 databases export per macro-region (`01_centaur.json` .. `14_nicethi.json` + `stadester_manifest.json`, sub-sharded at `200 MB`) via `StadesterPartitionIO` directly into the hoisted `histmap/3.data_transform/population_Stadester.transform/stadester/` directory (no nested `stadester/stadester/`, `stadester_areas/` or `stadester_ghsl/` subdirectories).

---

## Subagent & Swarm Model Scaling Policy

To scale Operation Viscount across all 14 macro-regions without exhausting orchestrator quota or stalling parallel workers, **always use Gemini 3.8 Flash first for subagents and swarms, falling back to Gemini 4 Hydrogen when Flash fails or runs out of quota/capacity**:

- **Primary model — Gemini 3.8 Flash**:
  - **Native `swarm` (`action: "add"`)**: Explicitly pin workers to `"gemini-3.8-flash-high"` (`"Gemini 3.8 Flash (High)"`) for sub-chapter literature reviews, `<stem>_source_ledger.json5` / `<stem>_settlements.json` compilation, and `.Rmd` drafting, or `"gemini-3.8-flash-medium"` (`"Gemini 3.8 Flash (Medium)"`) for high-fan-out lightweight tasks such as Stage F historical toponymy shards. This user-standing directive overrides the default `native_swarm` rule of leaving `model` unset.
  - **`invoke_subagent` & `run_workflow`**: Always pass `Model: "flash"` / `model="flash"` (routes to Gemini 3.8 Flash).
- **Fallback model — Gemini 4 Hydrogen**:
  - Whenever Gemini 3.8 Flash hits quota or capacity limits, is unavailable, or fails verification on a delegated slice, switch immediately to **Hydrogen**:
  - **Native `swarm` (`action: "model"` / `"add"`)**: Switch existing waiting workers in place via `swarm{action: "model", name: "<worker>", model: "gemini-4-hydrogen-high"}` (or `"gemini-4-hydrogen-medium"` for batch shards; never `kill` and re-`add` merely to swap models), or spawn replacement/new workers directly with `model: "gemini-4-hydrogen-high"` (`"gemini-4-hydrogen-medium"` for lightweight shards).
  - **`invoke_subagent` & `run_workflow`**: Because these tools only accept tier enums (`"flash"`, `"flash_lite"`, `"pro"`, `"inherit"`), escalate to `swarm` workers pinned to `"gemini-4-hydrogen-high"` / `"gemini-4-hydrogen-medium"` whenever explicit Hydrogen execution is required; `run_historical_names_swarm.py` also catches per-batch `"flash"` errors and retries automatically on `fallback_model` (`"inherit"` or `"pro"`).

---

## Six-Stage Execution Workflow (`A_` – `F_`)

### Stage A: Regional Taxonomy, Source Discovery & Shifting Boundaries

1. Create `histmap/1.data_raw/population_regional/<PROJECT_KEY>/` mirroring `POLARIS/` (`_shared/`, spatiotemporal sub-folders, synthesis root report `studies_on_population.Rmd`).
2. Identify the region's authentic **historical administrative hierarchies and ecological zones** (never force contemporary 2026 borders onto pre-modern epochs). Encode hierarchical priority masks in `<PROJECT_KEY>/<slug>_areal_masks.json5`.
3. Identify region-appropriate **archaeological site registries** (e.g. INRAP, ARCHI/PastScape, ASI, State Cultural Heritage Lists, university survey corpora) and **dasymetric covariates** (soil fertility, palaeoclimate suitability, river navigable buffers, irrigated alluvial plains, mountain masks).

### Stage B: Exhaustive Settlement Gazetteer Compilation (Zero Artificial Caps)

**Never truncate, sample or cap settlements at `120`, `200` or any fixed quota.**

When parallelising sub-chapter compilation across regional workers (`swarm` or `invoke_subagent`), run chapter workers on **Gemini 3.8 Flash** (`model: "gemini-3.8-flash-high"` in `swarm`, `Model: "flash"` in `invoke_subagent`), switching/falling back to **Hydrogen** (`"gemini-4-hydrogen-high"`) if Flash encounters quota/capacity exhaustion or validation failure.

1. For every sub-chapter `<stem>`, maintain both:
   - `<stem>_settlements.json` — full settlement trajectories (`coords` as `[lat, lng]`, `country`, `other_names`, `original_names`, `population: { "<year>": int }`, `sources: ["<PROJECT_KEY>"]`).
     - **`.sources: string[]` schema**: Stadestér 2.0 replaces legacy `.type: string` with `.sources: string[]`. Never emit a `"type"` key on regional `_settlements.json` or compiled Stadestér 2.0 records.
     - **Literature-review citation rule**: For regional literature-review settlements, `.sources` MUST cite **only** the canonical Viscount project name (`"CENTAUR"`, `"POLARIS"`, `"PRETA"`, `"JADE"`, `"INDUS"`, `"CASTLE"`, `"MANDALA"`, `"SARAY"`, `"HANDBOOK"`, `"MAGNETIC"`, `"QUIPU"`, `"JAGUAR"`, `"AUSTRAL"` or `"NICETHI"`, e.g. `["POLARIS"]`) — never `"type"`, `"viscount_regional"`, sub-chapter keys or individual bibliographic sources. Detailed bibliographic sources belong strictly in `<stem>_source_ledger.json5` and `<stem>.bib`.
     - **Multi-source UUD/GHSL/GHS-POP merging**: In compiled Stadestér 2.0 shards, all contributing sources (`"populstat"`, `"chandler_modelski"`, `"devries"`, `"buringh"`, `"manual"`, `"ghsl"`, `"ghs_pop"` plus each Viscount project name) are appended as deduplicated entries in `.sources`.
   - `<stem>_source_ledger.json5` — complete enumeration of every documented town, fortress, port, mining settlement, trade post and quantified archaeological site in the source literature, marking every candidate `"included"` (with `settlement_key`) or `"excluded"` (with valid `reason` and substantive `justification`).
2. Register chapter files in `<PROJECT_KEY>/<slug>_gazetteers.json5`.
3. **Mandatory Gatekeeper Check**:
   ```powershell
   python .agents/skills/population-regional-study/scripts/verify_gazetteer_exhaustiveness.py <path/to/_settlements.json> --ledger <path/to/_source_ledger.json5>
   ```
   To audit compiled Stadestér 2.0 macro-region shards directly, pass `--require-sources --mode=compiled`. Do not proceed until unaccounted candidates = `0` and schema validation errors = `0`.

### Stage C: Matérn Kriging Substrata & Cross-Frontier Mosaic

Avoid blurry ordinary kriging or sharp administrative border discontinuities.

1. Configure domain parameters in `histmap/3.data_transform/population_Substrata.viscount/config/<slug>.json5` following [kriging_and_masks_guide.md](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/references/kriging_and_masks_guide.md).
2. Couple domestic units with a `>= 250 km` cross-frontier conditioning belt during Empirical Matheron variogram estimation and Paciorek-Schervish non-stationary Matérn ($\nu = 3/2$) log-linear residual kriging via `ViscountMaternKriging`.
3. Blend overlapping regional strata via `ViscountSubstrataMosaic` and `ViscountSubstrataPipeline` (descending `z_priority`).
4. **Mandatory Gatekeeper Checks**:
   ```powershell
   python .agents/skills/population-regional-study/scripts/audit_kriging_sharpness.py <path/to/kriging_diagnostics.json>
   python .agents/skills/population-regional-study/scripts/audit_border_cliffs.py <path/to/1.kriged_rasters>
   ```

### Stage D: Academic RMarkdown & Cartographic Publication

Write authentic academic prose in **non-Oxford British English (EN-GB)**.

1. Source shared helpers from `histmap/1.data_raw/population_regional/_shared/template/viscount_rmd_helpers.R` (`viscount_table()`, `viscount_figure()`, `viscount_fmt_pop()`, `viscount_fmt_number()`). **Never** paste inline `render_table_template` redefinitions inside `.Rmd` files.
2. Follow [viscount_rmd_template.md](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/references/viscount_rmd_template.md): European decimal commas (`58,88`), semantic quantities (`k`, `M`, `B`, `T`), dot thousands for small ints (`10.000`), `GMT+0` timestamps, high-DPI Matplotlib figures via `_shared/viscount_plot_utils.py`.
3. **Mandatory Gatekeeper Check**:
   ```powershell
   python .agents/skills/population-regional-study/scripts/audit_academic_prose.py <path/to/chapter.Rmd>
   ```

### Stage E: Intellte Synchronisation & Fast Incremental SSG Build

1. Ensure `E:/Active Projects/Project 1746 - Intellte/common/metadata/viscount/project_<slug>.json5` exists and matches `intellte_concept_id` in `viscount_precedence.json5`.
2. Synchronise chapter papers and compile incrementally in Intellte:
   ```powershell
   Set-Location "E:\Active Projects\Project 1746 - Intellte"
   node core/framework/node/sync_viscount_region.js --project=<PROJECT_KEY>
   node core/framework/node/run_pipeline.js --only=project_<slug>
   ```
3. Run `npm run docs:build` after major milestone updates to refresh the VitePress bundle and static `.html` redirect stubs.

### Stage F: Stadestér 2.0 Export & Historical Toponymy Sync

1. Export updated UUD (`histmap/2.data_cleaning/population_Stadester/uud/`) and partitioned Stadestér 2.0 outputs (`.sources: string[]` schema) directly into the hoisted `histmap/3.data_transform/population_Stadester.transform/stadester/` directory (no nested `stadester/stadester/`, `stadester_areas/` or `stadester_ghsl/` subdirectories), then synchronise shards to `histmap/5.data_visualisation/stadester/stadester_2.0/` and `F:/Active Projects/Project 1436 - Dataview/data/stadester/stadester_2.0/`. `stadester_1.0/` remains the frozen baseline legacy release whilst `stadester_1.1/` carries the in-situ geolocation fixes backported from `2.0` with its legacy `.type: string` schema preserved (both `1.0/` and `1.1/` retain independent `city_metadata.json` files and legacy optional `.type` support alongside `.sources` in Dataview).
2. Extract unmatched or corrupted regional settlement records into `30`-city batches (defaults to `--dataset=stadester_2.0`, resolving `data/stadester/stadester_2.0/city_metadata.json`):
   ```powershell
   node .agents/skills/population-regional-study/scripts/extract_missing_city_metadata.js --project=<PROJECT_KEY>
   ```
3. Run the historical toponymy workflow (`run_workflow`) over `.agents/skills/population-regional-study/scripts/run_historical_names_swarm.py` with `Args: {"project": "<PROJECT_KEY>", "slug": "<slug>", "model": "flash", "fallback_model": "inherit"}` (runs **Gemini 3.8 Flash** first with automatic per-batch retry fallback). If Flash quota/capacity is exhausted globally, dispatch the `batch_*.json` shards via native `swarm` workers pinned to `"gemini-3.8-flash-medium"`, switching/falling back to `"gemini-4-hydrogen-medium"` (`"gemini-4-hydrogen-high"` for complex historical regions).
4. Validate (`isCorruptedCityName`, `/^-?\d+\.\d+\.\d+$/`, `[lat, lng]` -> `[lng, lat]` transpose, non-destructive `capital` preservation) and commit into Dataview `data/stadester/stadester_2.0/city_metadata.json` while evicting `stadester_2.0_lite.json` and `stadester_2.0_indexed.json`:
   ```powershell
   node .agents/skills/population-regional-study/scripts/merge_city_metadata.js --project=<PROJECT_KEY>
   ```
5. Remove temporary `tests/toponymy_batches/<slug>/` files after verifying `merge_city_metadata.js` output (`0` leftover test artefacts).
