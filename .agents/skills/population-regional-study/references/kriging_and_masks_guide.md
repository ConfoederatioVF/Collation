# Kriging, Dasymetric Covariates & Hierarchical Border Mosaic Guide

## 1. Preventing Blurry Surfaces (`tau1` & Nugget Rules)

A frequent failure in first-pass demographic kriging is over-smoothing across sparse rural districts (high dimensionless range `tau1 > 1,8` or high `nugget_to_sill >= 0,45`), wiping out river valleys, alluvial cores and upland ecological corridors.

Every Viscount domain module running `ViscountMaternKriging` (`histmap/3.data_transform/population_Substrata.viscount/`) must satisfy:

- **Kernel**: Non-stationary Paciorek-Schervish differentiable Matérn ($\nu = 3/2$) driven by local Voronoi catchment spacing $\sigma(x)$.
- **Sharpness threshold**: `tau1_dimensionless <= 1,8` (short-scale local correlation) and `nugget_to_sill_ratio < 0,45` on dated horizons.
- **Non-negative dual weights**: Solve $(C + \eta I) w = z_{\text{adj}}$ subject to $w \ge 0$ via Cholesky warm-start + Projected Gauss-Seidel (Steps `D_`–`E_`).
- **De-cliffed dasymetric trend**: Regress residuals via constrained WLS against HYDE urban-masked rural habitation $u_{\text{hab}}(x)$, palaeoclimate/arable suitability and region-specific covariates (rice paddy irrigation, oasis hydrology, steppe chernozem, elevation bands).

---

## 2. Eliminating Modern Border Cliffs (250 km Coupling + Inverse `z-index`)

Never clip input district centroids cleanly at contemporary nation-state boundaries before fitting variograms or interpolating across frontiers.

1. **Cross-Frontier Conditioning (`>= 250 km`)**: Include administrative units and site densities from adjacent states within `250 km` of the target frontier in `A_loadDomainConfigAndSites` so variogram sills and Kriging dual weights reflect ecological continuity rather than artificial census borders.
2. **Pre-Modern Polygon Masking**: In `<slug>_areal_masks.json5`, construct time-varying priority masks separating ecological and historical polities rather than projecting modern borders back into antiquity.
3. **One-Sided $C^1$ Raised-Cosine Feathering & Inverse Precedence (`14 -> 1`)**:
   - `ViscountSubstrataMosaic` iterates from `z_priority = 14` (`NICETHI`) down to `z_priority = 1` (`CENTAUR`).
   - Higher-order frontier pixels remain **locked**; lower-order regions calibrate against `B \ A` residual mass and apply one-sided $C^1$ raised-cosine seam feathering (`200 km` / `24 px`) at overlaps so frontier gradients match interior smoothness (`audit_border_cliffs.py` `p99 <= 2,5`).
