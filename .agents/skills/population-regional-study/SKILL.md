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
- **Stadestér sharding**: Final Stadestér databases export per macro-region (`01_centaur.json` .. `14_nicethi.json` + `stadester_manifest.json`, sub-sharded at `200 MB`) via `StadesterPartitionIO` into `histmap/3.data_transform/population_Stadester.transform/stadester/`.

---

## Six-Stage Execution Workflow (`A_` – `F_`)

### Stage A: Regional Taxonomy, Source Discovery & Shifting Boundaries

1. Create `histmap/1.data_raw/population_regional/<PROJECT_KEY>/` mirroring `POLARIS/` (`_shared/`, spatiotemporal sub-folders, synthesis root report `studies_on_population.Rmd`).
2. Identify the region's authentic **historical administrative hierarchies and ecological zones** (never force contemporary 2026 borders onto pre-modern epochs). Encode hierarchical priority masks in `<PROJECT_KEY>/<slug>_areal_masks.json5`.
3. Identify region-appropriate **archaeological site registries** (e.g. INRAP, ARCHI/PastScape, ASI, State Cultural Heritage Lists, university survey corpora) and **dasymetric covariates** (soil fertility, palaeoclimate suitability, river navigable buffers, irrigated alluvial plains, mountain masks).

### Stage B: Exhaustive Settlement Gazetteer Compilation (Zero Artificial Caps)

**Never truncate, sample, or cap settlements at `120`, `200`, or any fixed quota.**

1. For every sub-chapter `<stem>`, maintain both:
   - `<stem>_settlements.json` — full settlement trajectories (`coords` as `[lat, lng]`, `country`, `other_names`, `original_names`, `population: { "<year>": int }`).
   - `<stem>_source_ledger.json5` — complete enumeration of every documented town, fortress, port, mining settlement, trade post, and quantified archaeological site in the source literature, marking every candidate `"included"` (with `settlement_key`) or `"excluded"` (with valid `reason` and substantive `justification`).
2. Register chapter files in `<PROJECT_KEY>/<slug>_gazetteers.json5`.
3. **Mandatory Gatekeeper Check**:
   ```powershell
   python .agents/skills/population-regional-study/scripts/verify_gazetteer_exhaustiveness.py <path/to/_settlements.json> --ledger <path/to/_source_ledger.json5>
   ```
   Do not proceed until unaccounted candidates = `0`.

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

### Stage F: Stadestér 2.0 Export & Gemini Flash Historical Toponymy Sync

1. Export updated UUD (`histmap/2.data_cleaning/population_Stadester/uud/`) and partitioned Stadestér 2.0 outputs (`histmap/3.data_transform/population_Stadester.transform/stadester/`) and synchronise shards to `F:/Active Projects/Project 1436 - Dataview/data/stadester/stadester_2.0/` (`stadester_1.1/` and `stadester_1.0/` remain frozen legacy versions with independent `city_metadata.json` files).
2. Extract unmatched or corrupted regional settlement records into `30`-city batches (defaults to `--dataset=stadester_2.0`, resolving `data/stadester/stadester_2.0/city_metadata.json`):
   ```powershell
   node .agents/skills/population-regional-study/scripts/extract_missing_city_metadata.js --project=<PROJECT_KEY>
   ```
3. Run the Gemini Flash toponymy workflow (`run_workflow`) over `.agents/skills/population-regional-study/scripts/run_historical_names_swarm.py` with `Args: {"project": "<PROJECT_KEY>", "slug": "<slug>", "model": "flash"}`.
4. Validate (`isCorruptedCityName`, `/^-?\d+\.\d+\.\d+$/`, `[lat, lng]` -> `[lng, lat]` transpose, non-destructive `capital` preservation) and commit into Dataview `data/stadester/stadester_2.0/city_metadata.json` while evicting `stadester_2.0_lite.json` and `stadester_2.0_indexed.json`:
   ```powershell
   node .agents/skills/population-regional-study/scripts/merge_city_metadata.js --project=<PROJECT_KEY>
   ```
5. Remove temporary `tests/toponymy_batches/<slug>/` files after verifying `merge_city_metadata.js` output (`0` leftover test artefacts).
