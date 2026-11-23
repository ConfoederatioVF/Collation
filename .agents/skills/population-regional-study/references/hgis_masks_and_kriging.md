# Stages A & B — Academic HGIS Areal Masks, Dual HYDE 3.5 + KK10 Kriging & Subadmin Disaggregation

All numeric limits (`hgis_policy`, `catchment_density_policy`, `kriging_sharpness_floors`) live in [viscount_skill_profiles.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/config/viscount_skill_profiles.json5).

---

## 1. Stage A — Two-Pass OHM + Academic HGIS Areal Masks (`Gatekeeper A`)

### Three-Regime Partitioning Law
Configure `regime_transitions` (`[pre_admin_end, contemporary_start]`) in `<slug>_areal_masks.json5`. NEVER retrofit modern 2025 `Admin-1`/`Admin-0` borders onto pre-1945 masks or figures:
- **Regime I (`[-10000, pre_admin_end]`)**: HydroBASINS watersheds, elevation contours (`ETOPO1`), ecotones (`forest_wwf_cr.asc`), coastal-complete `atlas_dejure.naissance`, and coherent archipelago groups. Place coastal/oasis/island corridors above continental interiors in `specialist_masks`.
- **Regime II (`[pre_admin_end, contemporary_start]`)**: Period-authentic historical divisions (provinces, *bailliages*, voivodeships, *vármegyék*, *eyalets*/*vilayets*, commanderies, intendancies, counties) strictly bounded inside each chapter's `[start_year, end_year]` bookends.
- **Regime III (`[contemporary_start, 2026]`)**: `10m` vector `Admin-1` subdivided for active conflict/occupation/displacement using real GIS layers (`HDX`, `UNHCR`, `IOM DTM`, `ACLED`, `UCDP`; zero synthetic `box()` cuts).

### Pass-1 — Preliminary HGIS EDA Swarm (Discovery Only)
Before building any mask or subadmin raster, dispatch a preliminary EDA subagent swarm to harvest and catalogue into `<slug>_hgis_inventory.json5`:
1. **OpenHistoricalMap (OHM)** sub-administrative divisions across all overlapping HYDE windows as the baseline substrata.
2. **Period-specific academic HGIS sub-administrative datasets** (DARMC, DARE, Kiepert, Euratlas, Armand Brette, IH PAN, GISta Hungarorum, RoHGIS, Imperiia, CHGIS, KCHGIS, geoBoundaries, national HGIS archives) + their population enumerations to supersede/enrich OHM wherever higher specificity exists.
3. **Coastal-complete `atlas_dejure.naissance`** (re-encoded Cliopatria with intact coasts) and **`atlas_defacto.naissance` strictly at lowest fallback `z = 1`** (de facto dynastic holdings only; never overrides higher-priority HGIS layers).
4. **Hard Source Bans (`[FAIL]` in `audit_areal_masks.js`)**: Zero videogame maps (`EU4`, `Vic2`, `Victoria2`, `CK2`, `CK3`, `HoI4`, Paradox), zero `aourednik/historical-basemaps`, and zero raw coastal-gapped Cliopatria.

### Degenerate Topology Repair (Mandatory During All Areal Merges)
Whenever merging, dissolving, or clipping OHM substrata, specific academic HGIS layers, and HydroBASINS/coastlines:
1. Repair every input geometry (`make_valid` / zero-width buffer healing) and extract strictly `Polygon`/`MultiPolygon` members from any `GeometryCollection` (dropping stray `Point`/`LineString` artefacts).
2. Snap near-coincident vertices (`<= 1e-4°`), enforce consistent ring winding (CCW exterior, CW holes), and absorb micro-sliver gaps/overlaps (`< 25 km²` or `< 4 px`) into the longest-shared-edge valid neighbour.
3. Clip strictly to coastal land masks before rasterising at `4320×2160` (`0` scanlines, `0` self-intersections, `0` collinear axis-aligned interior box cuts).

### Pass-2 — Bounded 2-Subagent Mask Population & Visual QA Loop (`MAX 2 SUBAGENTS`)
To prevent unbounded token burn whilst eliminating degenerate/modern-border masks, Pass-2 uses **at most 2 subagents**:
1. **`mask_builder` (Subagent 1)**: Executes topological merges, emits **dual outputs** (`*_areal_mask.png` + smooth vector `_shared/_gis_cache/chapter_subregions/<stem>_subregions.geojson`) plus all overlapping HYDE `subadmin_id_<year>.png` rasters (`100y` intervals to `1700 AD`, `10y` to `1950 AD`, `1y` `1951–2025`), and renders regional **bbox crop PNGs** (`/tests/mask_crops/`, `/tests/subadmin_crops/`).
2. **`mask_auditor` (Subagent 2 — strictly separate, read-only)**: Inspects every bbox crop PNG via `read_file` against historical reality (flagging modern-border leakage, straight-line/scanline artefacts, degenerate slivers, missing provinces, or coastal gaps), sends defects back to `mask_builder` in a loop until spotless, and signs `_shared/mask_audit_signoff.json` (`verified_by_separate_auditor: true`, unique crop notes).

Run `audit_areal_masks.js <project_dir> --require-auditor-signoff --render-overlays`. Any later edit to `*_areal_mask.png` or `*_subregions.geojson` invalidates downstream Stage D figures and `.pdf` files.

---

## 2. Stage B — Archaeology, Dual HYDE 3.5 + KK10 Catchments & Non-Stationary Kriging (`Gatekeepers B1–B3`)

### Baseline Probe & Multi-Repository Archaeology
- Plot SVEA's `c14_cleaned_dedup.csv` inside the domain mask first; audit scraped heritage APIs for `NULL`/undated leakage, coordinate fuzzing, monument-complex double counting, and overlapping local periodisations.
- Composite primary national/regional registers across **every** jurisdiction in `jurisdiction_source_matrix` (`0` Wikipedia scraping; `>= 2,5x` c14 anti-stub floor; per-jurisdiction AND domain-wide crowd `<= 25%`, regional/monograph `>= 50%`, `>= 2` regional sources). Separate durable non-habitation monuments from settlement records with biome/aridity-conditioned `Q75 + IQR` shrinkage (`forest_wwf_cr.asc`).

### Dual HYDE 3.5 + KK10 Believed-Density Catchments + Minimum Surface Floor
- Compute per-cell believed historical density from **both** HYDE 3.5 (`histmap/2.data_cleaning/landuse_HYDE/rasters/popc_*.png`) and **KK10** (`histmap/1.data_raw/population_KK10LUH2/KK10/KK10_*.png`) over `land_area.png`:
  $$D_{\text{believed}} = \max(D_{\text{HYDE3.5}},\, D_{\text{KK10}})$$
  so HYDE false-zero or distorted pockets are rescued by KK10.
- Subdivide HydroBASINS/ADM2 catchments tightly where $D_{\text{believed}}$ is high (`>= 25 inh/km² -> <= 1.800 km²`, `5–25 -> <= 3.000 km²`, `1–5 -> <= 6.000 km²`, `0,05–1 -> <= 14.000 km²`), whilst enforcing a **global minimum catchment density floor** (`max_catchment_area_km2 <= 25.000 km²`, `>= 5` catchments per `100k km²`) across the entire habitable domain so kriging covers 100% of required surface area. Exclude only true ice sheets/uninhabited polar interiors where **both** HYDE 3.5 and KK10 are zero and site-free.

### Parameter-Free Kriging, Radial Geometry & Per-Project Isolation
- Use Freeman-Tukey square-root density $Z = \sqrt{S / A_{\text{eff}}}$ + 2D Paciorek-Schervish non-stationary Matérn ($\nu = 3/2$) via Projected Gauss-Seidel Non-Negative Dual Kriging (`ViscountMaternKriging`, wrapped via `run_bounded.js --lock gpu_compute`).
- Pass HYDE `popc` through `ViscountUrbanMask` (`uopp_2023AD > 10 km²` union `GHSL_2020 >= 50k`, Moore buffer `>= 1` px, 3-tier IDW inpainting) across all pre-industrial horizons (`urban_core_med_ratio <= 1,60`, `urban_backproj_p95_ratio <= 1,65`).
- Enforce **metric-isotropic radial Euclidean distance** $\sqrt{\Delta r^2 + (\Delta c \cdot \cos\phi)^2}$ (zero Manhattan BFS diamonds; `manhattan_anisotropy_max_ratio <= 1,35`).
- Isolate all regional fluvial/topographic weights inside `histmap/3.data_transform/population_Substrata.viscount/config/<slug>_dasymetric_admixture.json5` — NEVER modify shared `Viscount*` defaults for region-specific fluvial calibration.
- Import `250 km` cross-frontier sites (`is_frontier_buffer: true`) from completed neighbours and blend seams via `ViscountSubstrataMosaic` + `ViscountSubstrataSeamBlend`.

### Mass-Conserving Sub-Administrative Disaggregation & Visual Sign-Off
- Disaggregate scraped historical/modern sub-administrative enumerations (from Pass-1 HGIS) onto kriged 5-arcminute suitability surfaces using strictly mass-conserving Tobler pycnophylactic multiplier relaxation across every enumerated HYDE year (`worst_unit_rel_err <= 1e-4`, audited in `subadmin_mass_conservation_audit.json`), and export rows for inclusion in Stage D literature reviews.
- Run `audit_kriging_sharpness.js <domain_dir>`, `audit_border_cliffs.js <domain_dir> --check-inter-region --project <KEY>`, and `render_and_audit_kriging_visuals.py <domain_dir> --render-only`. Inspect EVERY generated sheet via `read_file` (confirming crisp relief, zero blurry blobs, zero Manhattan diamonds, balanced fluvial alignment, zero modern border cliffs), sign `<domain_dir>/config/visual_verification_manifest.json`, and verify `audit_kriging_sharpness.js <domain_dir> --require-visual-manifest` (`hp15_mean >= 0,20`, `dx_mean >= 0,14`).

---

## 3. Stage E — `Stadestér -> Velkscala` Reconciliation Invariants (`Gatekeeper E`)

Verified by `audit_velkscala_reconciliation.js --project <KEY>`:
- **Float32 Decoding**: Test 4-byte non-zero OR and decode via `DataView.getFloat32(..., false)` (never `png.data[p4 + 3] > 0` which causes `~1/256` Swiss-cheese zero-holes).
- **Zero Circular Reads**: Kriging scripts MUST NOT read downstream `stadester_rural_*.png`.
- **Sub-`5k` & Micro-Island Floor Protection**: Towns with `0 < pop < 5.000` and inhabited micro-islands retain `gridcell_pop >= settlement_pop`.
- **3-Phase Metro & DEGURBA Conservation**: Zero double-counted metropolitan/suburban overlaps, zero negative post-reconciliation populations, and smooth `1974 -> 1975` DEGURBA transition.
- **Temporal Hiatus & Bookend Isolation**: Enforce `max(200, hyde_interval)` hiatus windows and strict `[start_year, end_year]` domain bookends.
