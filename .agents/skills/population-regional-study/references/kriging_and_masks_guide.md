# Non-Stationary Matérn Kriging, Areal Masks & `Velkscala` Reconciliation

## 1. Three-Regime Spatiotemporal Partitioning Law (`Gatekeeper A2`)

Every Operation Viscount project partitions territory across eras using manifest-configured `regime_transitions` (`[pre_admin_end, contemporary_start]`) in `<slug>_areal_masks.json5`, NEVER retrofitting modern `Admin-1` boundaries across pre-modern societies:

1. **Regime I — Pre-Administrative / Archaeological & Ecological (`[-10000, pre_admin_end]`)**:
   - Delineate zones along physical hydrology (`HydroBASINS` / `flow.asc`), elevation contours (`ETOPO1`), ecological ecotones (`forest_wwf_cr.asc`), `.naissance` historical polity boundaries and ecologically coherent island/archipelago groups.
   - Never clip natural basins to modern borders or straight lat-lon boxes (`bbox_fill_ratio > 0,96` fails `audit_areal_masks.py`). Place distinct coastal/oasis/island/steppe corridors above continental interior masks inside `specialist_masks` so interior hinterlands do not starve their rural budgets.
   - Smooth erratic single-site radiocarbon SPDs into log-space PCHIP population trajectories with uncertainty bands.
2. **Regime II — Historical Fiscal, Imperial, Colonial & Pre-Contemporary Census (`[pre_admin_end, contemporary_start]`)**:
   - Partition along period-authentic sub-divisions (dynastic commanderies/prefectures, viceroyal intendancies, colonial provinces/presidencies, Ottoman *vilayets*, historical counties/territories), separating divergent agrarian core vs interior/rail/mining frontiers and isolating historical borderlands cleanly inside each chapter's `[start_year, end_year]` bookends.
3. **Regime III — Contemporary Statistical & Active Conflict/Displacement (`[contemporary_start, 2026]`)**:
   - Use exact `10m` vector `Admin-1` boundaries subdivided wherever armed conflict, occupation, partition or displacement alters effective jurisdiction using real georeferenced GIS layers (`UN OCHA HDX`, `UNHCR`, `IOM DTM`, `ACLED`, `UCDP` or authoritative theatre GeoJSONs — zero synthetic rectangular `box()` cuts).
4. **Coordinator Overlay Send-Back Loop**: Run `python .agents/skills/population-regional-study/scripts/audit_areal_masks.py <project_dir> --render-overlays`, inspect every `verify_<stem>_overlay.png` via `read_file`, verify `0` starved masks, `0` box shortcuts and `0` stranded settlements (enabling `has_micro_islands` coastal pinning where archipelagos occur).

---

## 2. Multi-Repository Archaeology, Adaptive Catchments & Taphonomic Conditioning

- **Baseline Probe & Anti-Stub Floor (`Stage C0`)**: Map SVEA's global `c14_cleaned_dedup.csv` inside the regional mask first, audit scraped heritage endpoints for `NULL`/undated contamination, coordinate fuzzing and complex double counting, and composite multi-repository national/regional registries (`>= 2,5x` `c14_cleaned_dedup.csv`; aim for full institutional density).
- **Scale-Adaptive Catchment Discretisation (`ADM2 x HydroBASINS`)**: Aggregate archaeological points to empirical Bayes `ADM2` districts where compact, and intersect with `HydroBASINS` Level 6–7 sub-basins wherever vast arid, rainforest, boreal or outback `ADM2` polygons exceed `max_adm2_area_km2` (`25.000 km²`), conserving exact coastal/island land area (`A_eff`).
- **Taphonomic & Monument-Class Bias Conditioning**: Separate durable non-habitation monumental or surface-deflation scatters (megalithic tombs, barrows/tumuli/kurgans, cairns, temple inscriptions, *huacas*) from settlement records and apply biome/canopy/aridity-conditioned `Q75 + IQR` shrinkage (`forest_wwf_cr.asc` / Köppen-Geiger aridity) so arid/funerary visibility never starves humid alluvial agricultural cores.

---

## 3. Parameter-Free Geostatistics: `ViscountMaternKriging` + `ViscountResidualCovariates`

Use the canonical SVEA classes under `histmap/3.data_transform/population_Substrata.viscount/`:

1. **Variance-Stabilising & Non-Negative Formulation**:
   - Replace `log(D + eps)` transforms (which induce negative-log sinkholes and exponential centroid spikes) with **Freeman-Tukey square-root density** \(Z = \sqrt{S / A_{\text{eff}}}\).
   - Fit **2D Paciorek-Schervish non-stationary Matérn ($\nu = 3/2$)** prefactors \(2 r_i r_j / (r_i^2 + r_j^2)\) with Matheron empirical zero-lag nugget and solve via **Projected Gauss-Seidel Non-Negative Dual Kriging** (eliminating post-hoc Cholesky clamping inflation).
   - Couple `ViscountResidualCovariates` WLS regressions (`Natural Earth 10m`/`50m` rivers, coastlines, `ETOPO1`/`GEBCO` elevation/slope, `Köppen-Geiger` biomes, urban-masked IDW-inpainted de-cliffed `HYDE` rural surface) using squared fine-ratio weights `(m_cell / m_macro)^2` (`1,0` fallback strictly on zero-hole cells).
2. **Un-Clamped Sharpness & Frontier Conditioning (`Gatekeepers C1–C3`)**:
   - Export true un-clamped `raw_tau1_dimensionless <= 1,8` and `raw_nugget_to_sill_ratio < 0,45` with active WLS betas (`wls_covariates_active: true`).
   - Condition across international and inter-Viscount seams with a `250 km` neighbouring ADM2/hydro-basin belt and blend seams via $C^1$ raised-cosine feathering aligned to `viscount_precedence.json5` (`z_priority: 14 -> 1`), masking external sovereign pixels strictly to `[0,0,0,0]`.
   - Verify with `audit_kriging_sharpness.py` (`C1`), `audit_border_cliffs.py` (`C2`) and `render_and_audit_kriging_visuals.py` (`C3`: `hp15_mean >= 0,08`, `dx_mean >= 0,04`, signed optical `read_file` manifest).

---

## 4. End-to-End `Stadestér -> Velkscala` Reconciliation Invariants (`Gatekeeper E2`)

`population_Velkscala` (`population_rasters/`, `population_rural_rasters/`, `population_urban_rasters/`) is the final demographic surface evaluated by `audit_velkscala_reconciliation.py --project <KEY>`:
- **Float32 Decoding**: NEVER test big-endian IEEE-754 `float32` PNG pixels with `png.data[p4 + 3] > 0` (which zeroes `~1/256` valid rural pixels whose low mantissa byte is `0x00`, creating "Swiss cheese" rural zero-holes). Always test 4-byte non-zero OR and decode via `DataView.getFloat32(..., false)`.
- **Zero Circular Downstream Reads**: Kriging scripts MUST NOT read downstream `stadester_rural_*.png` rasters.
- **Sub-`5k` & Micro-Island Floor Protection**: Since urban allocation isolates larger hubs (`>= 5k`), towns with `0 < pop < 5.000` and inhabited micro-islands MUST retain non-reducible gridcell support (`gridcell_pop >= settlement_pop`) in `rurc`/`popc`.
- **Temporal Proximity & GHSL DEGURBA Subtraction**: Enforce `max(200, hyde_interval)` temporal proximity windows across archaeological hiatuses and subtract non-primary Stadestér suburbs within GHSL DEGURBA metropolitan polygons.
- **Domain Bookend Isolation**: Calibrated regional weights MUST stop strictly at declared `[start_year, end_year]` bookends (`post_domain_blend_years`) without leaking into downstream epochs or external countries.

---

## 5. Shared GIS Cache & Isolation

- Load Natural Earth baselines (`ne_10m_admin_0_countries.geojson`, `ne_50m_admin_0_countries.geojson`, `ne_10m_rivers_lake_centerlines.geojson`, `ne_50m_rivers_lake_centerlines.geojson`, `ne_50m_coastline.geojson`) from `histmap/1.data_raw/population_regional/_shared/_gis_cache/`.
- Author regional configs inside `histmap/3.data_transform/population_Substrata.viscount/config/<slug>.json5`; NEVER modify legacy `population_Substrata.*` prior folders.
