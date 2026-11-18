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
5. **Dual Mask Output Law (`*_areal_mask.png` + `*_subregions.geojson`) & Regeneration Trigger**: Always persist clean vector sub-region polygons (`_shared/_gis_cache/chapter_subregions/<stem>_subregions.geojson` and epoch GeoJSONs) alongside every `4320x2160` `*_areal_mask.png` pipeline raster. Chapter and root figures MUST plot these smooth vector polygons via `PatchCollection` rather than `imshow()`-ing pixelated categorical mask PNGs. Any modification to `*_areal_mask.png`, `*_subregions.geojson`, settlement JSONs or Stage C rasters invalidates downstream `figures/*.png` and compiled `*.pdf` files: regenerate affected figures first and recompile PDFs afterwards (`Gatekeeper D2` fails on stale PDFs or stale spatial PNGs).

---

## 2. Multi-Repository Archaeology, Adaptive Catchments & Taphonomic Conditioning

- **Baseline Probe & Anti-Stub Floor (`Stage C0`)**: Map SVEA's global `c14_cleaned_dedup.csv` inside the regional mask first, audit scraped heritage endpoints for `NULL`/undated contamination, coordinate fuzzing and complex double counting, and composite multi-repository national/regional registries (single-source `p3k14c` pulls are insufficient; `>= 2,5x` anti-stub floor vs `c14_cleaned_dedup.csv`, targeting `>= 10x` full institutional density where continental registries exist — e.g. **`CENTAUR-II`** combines `DINAA`, `CARD`, `p3k14c`, `c14bazAAR` and regional monument/*ahupua'a* registries to reach `93.358` continental site-periods at `14,12x` baseline plus `6.979` *ahupua'a* site-epochs).
- **Scale-Adaptive Catchment Discretisation (`ADM2 x HydroBASINS`)**: Aggregate archaeological points to empirical Bayes `ADM2` districts where compact, and intersect with `HydroBASINS` Level 6–7 sub-basins wherever vast arid, rainforest, boreal or outback `ADM2` polygons exceed `max_adm2_area_km2` (`25.000 km²`), conserving exact coastal/island land area (`A_eff`) while calibrating high-variance catch-all / *ahupua'a* catchments (`raw_tau1 >= 0,25`).
- **Taphonomic & Monument-Class Bias Conditioning**: Separate durable non-habitation monumental or surface-deflation scatters (megalithic tombs, barrows/tumuli/kurgans, cairns, temple inscriptions, *huacas*) from settlement records and apply biome/canopy/aridity-conditioned `Q75 + IQR` shrinkage (`forest_wwf_cr.asc` / Köppen-Geiger aridity) so arid/funerary visibility never starves humid alluvial agricultural cores.

---

## 3. Parameter-Free Geostatistics: `ViscountMaternKriging` + `ViscountResidualCovariates`

Use the canonical SVEA classes under `histmap/3.data_transform/population_Substrata.viscount/`:

1. **Variance-Stabilising & Non-Negative Formulation**:
   - Replace `log(D + eps)` transforms (which induce negative-log sinkholes and exponential centroid spikes) with **Freeman-Tukey square-root density** \(Z = \sqrt{S / A_{\text{eff}}}\).
   - Fit **2D Paciorek-Schervish non-stationary Matérn ($\nu = 3/2$)** prefactors \(2 r_i r_j / (r_i^2 + r_j^2)\) with Matheron empirical zero-lag nugget and solve via **Projected Gauss-Seidel Non-Negative Dual Kriging** (eliminating post-hoc Cholesky clamping inflation).
   - **Extended HYDE Urban Buffer Mask (`ViscountUrbanMask`)**: Across EVERY benchmark year (`-10000..1900`), pass `HYDE popc` through `ViscountUrbanMask.getModernUrbanMask()` + `ViscountUrbanMask.loadUrbanMaskedHYDEPopcRaster()` (`ViscountBiophysicalCovariates` / `ViscountRuralSuitability` / `ViscountResidualCovariates`): mask modern cities (`uopp_2023AD.png > 10,0 km²`) unified with `GHSL_2020.png >= 50k`, dilate by Moore `buffer_radius >= 1` (default `2` px, `~45 km`), absorb contiguous suburban-sprawl fringe pixels (`uopp > 2,0 km²`), union historical `urbc_<year> > 0`, flag `> 8x` Moore rural spikes and universal `9x9` settled-basin reservoir zero-holes, and reconstruct underlying rural carrying capacity via 3-tier (`r`, `2r`, `4r`, `KK10LUH2`) boundary IDW (`inpaintUrbanMaskGrid`). Pre-industrial surfaces MUST never backproject modern metropolitan cores or suburbs (pre-industrial median `urban_core_med_ratio <= 1,60`, prehistoric/earliest-horizon `urban_backproj_p95_ratio <= 1,65`).
   - **Dasymetric Habitability & Macro Carrying-Capacity Weighting**: NEVER allow `preserve_period_dynamics` bypasses to fill `u_hab = 1,0` or pin `beta_0_hab = 0`, NEVER add a blanket `1e-5` raster floor to uninhabited pixels, and NEVER project `1900` HYDE mass onto site-free catchments. Suppress genuinely uninhabitable cells (`HYDE < 0,002 inhabitants/km²` and `dist_site > 6 px` / `~50 km`) cleanly (`unhab_leak_ratio <= 0,03`, `unhab_mass_share <= 0,015`, `beta_0_hab > 0`), preserve macro-scale carrying capacity (`0,65 * m_macro + 0,35 * global_m_mean` so fertile river basins stand out over semi-arid margins, `log_corr_hyde >= 0,25`), weight documented settlement hierarchy (towns, mounds, tells and pueblos above isolated lithic scatters) and impute missing-registry ADM2 zero-holes inside settled belts (`adm2_coverage_ratio >= 0,65`).
2. **Un-Clamped Sharpness & Frontier Conditioning (`Gatekeepers C1–C3`)**:
   - Export true un-clamped `raw_tau1_dimensionless` (`0,25 <= raw_tau1 <= 1,8`), `raw_nugget_to_sill_ratio < 0,45`, `beta_0_hab > 0`, `urban_mask_applied: true` and `wls_covariates_active: true`.
   - Condition across international, maritime-channel and inter-Viscount seams (e.g. Nares Strait, Bering Strait and `250 km` neighbouring ADM2/hydro-basin belts) using smooth geodesic covariates and blend seams via $C^1$ raised-cosine feathering aligned to `viscount_precedence.json5` (`z_priority: 14 to 1`), masking external sovereign pixels strictly to `[0,0,0,0]`.
   - Verify with `audit_kriging_sharpness.py` (`C1`: variogram sharpness, `unhab_leak_ratio <= 0,03`, `unhab_mass_share <= 0,015`, `log_corr_hyde >= 0,25`, `urban_core_med_ratio <= 1,60`, prehistoric `urban_backproj_p95_ratio <= 1,65`), `audit_border_cliffs.py` (`C2`) and `render_and_audit_kriging_visuals.py` (`C3`: `hp15_mean >= 0,08`, `dx_mean >= 0,04`, plus mandatory `read_file` optical verification of raw diagnostic sheets `01..05` and compiled `06_velkscala_<project>_verification.png` in `visual_verification_manifest.json`).

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
