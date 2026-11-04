# Required Updates to Velkscala's Extended Demographic System Modelling Report (`256`)

> [!NOTE]
> This specification audits the current modelling report (*Aust Kätzchen, CRD; Cavalier/Dicey, CRD. Mathematical description of Velkscala's Extended Demographic System*) against the active Histmap and UF/Vercengen pipelines in [`NWM.js`](histmap/3.data_transform/NWM/NWM.js), [`age_sex.js`](histmap/3.data_transform/age_sex/age_sex.js), [`tasks_smoothing.js`](UF/js/geospatiale/files/png/tasks/tasks_smoothing.js), [`tasks_composites.js`](UF/js/geospatiale/files/png/tasks/tasks_composites.js), [`migration_OLS.js`](histmap/2.data_cleaning/migration_OLS/migration_OLS.js), [`births_deaths_OLS.js`](histmap/2.data_cleaning/births_deaths_OLS/births_deaths_OLS.js) and [`UF/js/statistics/`](UF/js/statistics/).

---

## Executive Summary of Major Changes

1. **Age–sex graduation & redistribution (Definitions 1.3–1.9)**:
   - The 1500 AD premodern model cutoff is removed; temporal ensemble weights instead clamp the effective evaluation year to $t_{\mathrm{eff}} = \max(t, 1750)$ across the entire domain $[-10000, 2025]$.
   - Graduation splits into two distinct spatial regimes: for $t \le 1750$ ($\gamma(t) = 0$), graduation runs **per pixel** (elderly monotonic ceiling + coupled combined-density PAVA + biological sex-ratio bounds + secondary per-sex PAVA); for $t > 1750$ ($\gamma(t) > 0$), graduation runs in **ISO3 country bins** (coupled combined-density PAVA with sex-ratio bounds blended with coupled Huber–Whittaker graduation) and redistributes to pixels via **3-iteration Iterative Proportional Fitting (IPF)**.
   - Pre-1950 HMD bypass is no longer applied during Step E clamping; it is applied afterwards in Step F compositing.
   - Stock-reconciliation compatibility is inverted relative to the report's prose: UNWPP cohorts (`1950..2020`) **are** dasymetrically clamped to $P_{i,t}$, whereas WorldPop cohorts (`2015..2020`) are copied **unclamped**.

2. **Migration calibration & global centring (Definitions 2.2–2.5)**:
   - Migration training targets $Y^M_{i,t} = A^M_{i,t}/P_{i,t}$ are no longer clipped to $[-1, 1]$.
   - Migration no longer shares $[Q_{0.01}, Q_{0.99}]$ global/local target-bound blending ($\varepsilon^v_t = e^{-n^v_t/15}$) with vital events. Instead, annual migration bounds $[L^M_t, U^M_t]$ are calibrated per year via **log-tail Tukey's fences** on stride-17 residual targets ($t \ge 1950$) or stride-17 per-capita population growth rates $g_{i,t}/P_{i,t}$ ($t < 1950$).
   - Preliminary migration in both empirical and modelled branches is upper-capped at $g_{i,t} + P_{i,t}$ (with UNWPP deaths capped at $P_{i,t}$) and balanced via a **3-iteration one-sided population-weighted waterfill** over unsaturated cells ($|\sum M| < 0.01$).

3. **Birth/death & migration reconciliation (Definitions 3.5–3.11)**:
   - The admissible rectangle $\mathcal V_i = [B^-_i, B^+_i] \times [D^-_i, D^+_i]$, bisection root-finder $F_t(\lambda^*) = 0$ and equal-weight $L_2$ projection $B^*_i = \operatorname{clip}((B^0_i + D^0_i + H_i)/2; L_i, U_i)$ are **completely removed**.
   - They are replaced by a four-stage sequential scheme: (1) pre-1950 HMD residual migration override, (2) 3-iteration non-HMD migration waterfill under $M_{i,t} \le g_{i,t} + P_{i,t}$ ($|\sum M| < 0.1$), (3) ISO3 country-bin **bivariate hyperbolic (minimum-information) natural-change scaling** and (4) pixel-level bivariate hyperbolic natural-change closure with a mortality ceiling $D^*_i \le P_i$ and unbounded non-negative births $B^*_i \ge 0$.
   - UNWPP vital counts (`1950..2020`) are no longer hard-locked during reconciliation; they serve as baseline priors scaled by the hyperbolic reconciler.

4. **Resolved statistical helpers (Definitions 1.2 & 2.3)**:
   - MNL training ([`tasks_ml_models.js`](UF/js/geospatiale/files/png/tasks/tasks_ml_models.js#L460-L573), [`statistics_logit.js`](UF/js/statistics/statistics_logit.js#L289-L475)) is **weighted** by $w_{i,\tau} = \log(1 + \sum_{s,a} T^s_{i,\tau,a})$, anchors reference class $\beta^{f,(\tau)}_0 \equiv \mathbf 0$, scales covariates by weighted RMS and optimises via batch gradient descent with **heavy-ball momentum $\mu_{\mathrm{mom}} = 0.9$**.
   - Ridge OLS ([`statistics_OLS.js`](UF/js/statistics/statistics_OLS.js#L453-L613)) is intercept-free and penalises RMS-scaled covariates ($J^v_\tau = \operatorname{diag}(s_1^2, \dots, s_{35}^2)$). Fallback aggregation ([`geomeanOLSModels`](UF/js/statistics/statistics_OLS.js#L111-L168)) applies `Math.abs` *after* signed geometric aggregation, forcing all fallback coefficients $\overline\theta^v_j \ge 0$.

---

## 0. Preamble, Orchestration & Temporal Domain

### 0.1 High-Level Orchestration Summary ([`NWM.js`](histmap/3.data_transform/NWM/NWM.js#L578-L589))
- **Age–sex reconstruction paragraph**: Replace *"using a logistic transition from sex-specific isotonic graduation over [1750,1850] to coupled Whittaker–Henderson graduation with Huber loss"* with:
  - For $t \le 1750$ ($\gamma(t)=0$), **per-pixel** elderly monotonic ceiling, coupled combined-density PAVA with biological sex-ratio bounds and secondary per-sex decreasing PAVA.
  - Over $(1750, 1850]$, a logistic transition in **ISO3 country bins** from coupled combined-density PAVA (with biological sex-ratio bounds) to coupled Huber–Whittaker graduation, redistributed to cells via **3-iteration Iterative Proportional Fitting (IPF)** ([`clampCohortsGraduation`](UF/js/geospatiale/files/png/tasks/tasks_smoothing.js#L80-L408)).
- **Migration estimation paragraph**: Replace *"produces preliminary migration and removes its global population-weighted mean"* with *"produces preliminary migration subject to the local upper feasibility cap $M_{i,t} \le g_{i,t} + P_{i,t}$ and removes global net migration imbalance via a 3-iteration population-weighted waterfill over unsaturated cells"* ([`migration_OLS.E_deriveFinalRasters`](histmap/2.data_cleaning/migration_OLS/migration_OLS.js#L384-L531)).
- **Birth/death reconciliation paragraph**: Replace *"jointly adjusts migration and vital events within source-aware bounds"* with *"locks pre-1950 HMD vital actuals via residual migration, re-balances global migration across unsaturated non-HMD cells via 3-iteration waterfill, and closes local natural change via bivariate hyperbolic (minimum-information) scaling of births and deaths subject to $D_{i,t} \le P_{i,t}$"* ([`births_deaths_OLS.E_clampToStadester`](histmap/2.data_cleaning/births_deaths_OLS/births_deaths_OLS.js#L844-L1038)).

### 0.2 Temporal Domain Grid Discrepancy (`-10000` to `0`)
- [`population_Velkscala`](histmap/2.data_cleaning/population_Velkscala/population_Velkscala.js#L39-L61) composites [`population_c14bazAAR`](histmap/3.data_transform/NWM/NWM.js#L139-L148) in **100-year steps** from `-10000` to `0` (`101` antiquity steps; `218` total population stock rasters across `[-10000, 2025]`).
- However, [`landuse_HYDE.sorted_hyde_years`](histmap/2.data_cleaning/landuse_HYDE/landuse_HYDE.js#L41-L55) — used as the default iteration schedule by [`population_Stadester_transform`](histmap/3.data_transform/population_Stadester.transform/population_Stadester_transform.js#L32), [`age_sex`](histmap/3.data_transform/age_sex/age_sex.js#L350), [`migration_OLS`](histmap/2.data_cleaning/migration_OLS/migration_OLS.js#L345) and [`births_deaths_OLS`](histmap/2.data_cleaning/births_deaths_OLS/births_deaths_OLS.js#L622) — remains on **1000-year steps** from `-10000` to `0` (`128` steps total) unless `options.years` is explicitly overridden.
- [`GeoPNG.generateDeltaSeries`](UF/js/geospatiale/files/png/png_delta_framework.js#L51) omits the initial timestep $t = -10000$, so annualised change $g_{i,t}$ and reconciled vital/migration flows span `127` intervals (`-9000` to `2025` by default).

### 0.3 Editorial & Citation Fixes
- Correct `Husinger (2022)` to `Hunsinger (2022)` in both the Preamble and Footnotes.
- Correct `Conversation properties follow from normalisation...` to `Conservation properties follow from normalisation...`.

---

## 1. Definition 1 — Age–Sex Reconstruction

### 1.1 Notation & Covariates
- **Fix prose syntax**: Replace `(X_{i,t}) and denote the covariate vector.` with `(X_{i,t} \in \mathbb{R}^{35}) denote the covariate vector.`
- **Specify the 35 covariates ([`age_sex.covariates_obj`](histmap/3.data_transform/age_sex/age_sex.js#L7-L51))**:
  - 14 HYDE land-use rasters (`conv_rangeland`, `cropland`, `grazing`, `irrigated_not_rice`, `irrigated_rice`, `pasture`, `rainfed_not_rice`, `rainfed_rice`, `rangeland`, `rf_norice`, `rf_rice`, `tot_irri`, `tot_rainfed`, `tot_rice`);
  - 4 Velkscala population rasters (`popc_`, `popd_`, `rurc_`, `urbc_`);
  - 9 Eoscala economic rasters (`discretionary_income`, `disposable_income`, `gdp_nominal`, `gdp_pc`, `gdp_ppp`, `gdp_ppp_pc`, `gini`, `net_income`, `net_wealth`);
  - 8 annualised delta rasters (`delta_gdp_nominal`, `delta_gdp_pc`, `delta_gdp_ppp`, `delta_gdp_ppp_pc`, `delta_popd_`, `delta_popc_`, `delta_rurc_`, `delta_urbc_`).
- **Post-2023 population clamping note**: [`population_Velkscala`](histmap/2.data_cleaning/population_Velkscala/population_Velkscala.js#L50) generates `population_2024.png` and `population_2025.png`, which [`migration_OLS`](histmap/2.data_cleaning/migration_OLS/migration_OLS.js#L353) and [`births_deaths_OLS`](histmap/2.data_cleaning/births_deaths_OLS/births_deaths_OLS.js#L644) read directly as $P_{i,t}$. By contrast, [`age_sex`](histmap/3.data_transform/age_sex/age_sex.js#L198) still clamps $\widetilde t = \min(t, 2023)$ for $P^A_{i,t}$, and [`age_sex_UNWPP.unwpp_years`](histmap/2.data_cleaning/age_sex_UNWPP/age_sex_UNWPP.js#L7) ends at `2020` (not `2025`), so `2024..2025` are not replaced by UNWPP unless external rasters are provided.

### 1.2 Training Targets & Multinomial Models (Resolving Unsupplied Helper)
- **Active training years**: Because [`age_sex_UNWPP`](histmap/2.data_cleaning/age_sex_UNWPP/age_sex_UNWPP.js#L7) spans `1950..2020` and WorldPop spans `2015..2020`, [`age_sex.A_trainMultinomialLogitModels`](histmap/3.data_transform/age_sex/age_sex.js#L162-L202) skips `2021..2025` when neither source exists on disk.
- **Deterministic stride subsampling ([`tasks_ml_models.js`](UF/js/geospatiale/files/png/tasks/tasks_ml_models.js#L512-L538))**: Let $\mathcal C_\tau = \{i : P^A_{i,\tau} \ge 1\}$. If $|\mathcal C_\tau| > 15{,}000$, deterministic stride subsampling selects $i_s = \mathcal C_\tau[\lfloor s|\mathcal C_\tau|/15{,}000 \rfloor]$ for $s = 0,\dots,14{,}999$. The training set $\mathcal I_\tau$ retains sampled cells with finite covariates and target total $T_{i,\tau} = \sum_{s,a} T^s_{i,\tau,a} \ge 1$.
- **Reference-class identifiability ([`Statistics.multinomialLogitRegression`](UF/js/statistics/statistics_logit.js#L327-L337))**: Cohort index $0$ (`f_00`, i.e. $(f,0)$) is fixed at $\beta^{f,(\tau)}_0 \equiv \mathbf 0$; only the remaining 35 cohort parameter vectors are free.
- **Log-population weighted cross-entropy (replaces unweighted loss assumption, [`tasks_ml_models.js`](UF/js/geospatiale/files/png/tasks/tasks_ml_models.js#L558), [`statistics_logit.js`](UF/js/statistics/statistics_logit.js#L308-L414))**: Each cell receives weight
  $$w_{i,\tau} = \log\!\left(1 + \sum_{r,c} T^r_{i,\tau,c}\right), \qquad W_\tau = \sum_{i \in \mathcal I_\tau} w_{i,\tau},$$
  and training minimises the weighted normalised cross-entropy:
  $$-\frac{1}{W_\tau}\sum_{i \in \mathcal I_\tau} w_{i,\tau} \sum_{s,a} q^s_{i,\tau,a} \log \max\!\left(p^{s,(\tau)}_a(\widetilde X_{i,\tau}),\, 10^{-15}\right) + \frac{\lambda_{\mathrm{MNL}}}{2}\sum_{(s,a)\neq(f,0)} \|\tilde\beta^s_{\tau,a}\|_2^2.$$
- **Weighted RMS scaling & heavy-ball momentum ([`statistics_logit.js`](UF/js/statistics/statistics_logit.js#L359-L463))**: Features are scaled by $\mathrm{rms}_j = \sqrt{\frac{1}{W_\tau}\sum_{i \in \mathcal I_\tau} w_{i,\tau}\widetilde X_{i,\tau,j}^2}$ (fallback $1$ if $\le 10^{-12}$). Batch gradient descent uses **momentum $\mu_{\mathrm{mom}} = 0.9$**, $v^{(k)} = 0.9\,v^{(k-1)} - \eta_{\mathrm{learning}}\nabla\mathcal L$, stopping when $\max_{c,j}|v^{(k)}_{c,j}| < \varepsilon_{\mathrm{fit}} = 10^{-4}$ in RMS-scaled parameter space (or $K_{\max} = 50$), before unscaling $\beta^s_{\tau,a,j} = \tilde\beta^s_{\tau,a,j}/\mathrm{rms}_j$.

### 1.3 Coverage-Weighted Temporal Ensemble
- **Remove the 1500 AD cutoff and premodern model $p^{s,\mathrm{pre}}_a$**: [`age_sex.D_generateMultinomialLogitRasters`](histmap/3.data_transform/age_sex/age_sex.js#L360-L420) contains no 1500 AD cutoff and loads no premodern model (the 1500 AD switch exists only in the unused experimental [`anchored_multinomial_gam`](UF/js/statistics/learning_framework.js#L680) routine).
- **Replace with clamped effective year $t_{\mathrm{eff}} = \max(t, 1750)$**: Across the full domain $t \in [-10000, 2025]$, temporal kernel weights use:
  $$t_{\mathrm{eff}} = \max(t, 1750), \qquad v_\tau(t) = \frac{\omega_\tau e^{-|t_{\mathrm{eff}}-\tau|/50}}{\sum_\nu \omega_\nu e^{-|t_{\mathrm{eff}}-\nu|/50}}.$$
  For all $t \le 1750$, ensemble weights freeze at their $1750$ values while historical covariates $\widetilde X_{i,t}$ vary normally.
- **Uninhabited density mask**: [`predictRaster`](UF/js/statistics/learning_framework.js#L524-L526) is invoked with `mask_uninhabited: true` ([`age_sex.js`](histmap/3.data_transform/age_sex/age_sex.js#L419)), writing $p^s_{i,t,a} = 0$ across all 36 cohorts whenever `popd_[i] === 0` (if $P^A_{i,t} \ge 0.01$ on such a cell, downstream clamping falls back to $P^A_{i,t}/36$).

### 1.4 Country-Bin Aggregation
- **Active only when $\gamma(t) > 0$ ($t > 1750$)**: Country-bin aggregation is bypassed entirely for $t \le 1750$ ([`tasks_smoothing.js`](UF/js/geospatiale/files/png/tasks/tasks_smoothing.js#L80-L150)).
- **Remove HMD bypass exclusion from $\mathcal E_{b,t}$**: [`clampCohortsGraduation`](UF/js/geospatiale/files/png/tasks/tasks_smoothing.js#L215-L230) includes **every** cell with $P^A_{i,t} \ge 0.01$ in its ISO3 country bin (unmapped RGB keys fall into `"GLOBAL"`). Pre-1950 HMD replacement now happens after clamping in Step F.

### 1.5 PAVA Graduation (Split into Pre-1750 Per-Pixel vs Transition Country-Bin Regimes)
The report's single country-bin sex-specific PAVA formulation (and its boxed per-sex conservation identity $\sum_a G^{s,I}_a = \sum_a R^s_a$) must be replaced by two distinct regimes:

1. **Pre-1750 Per-Pixel Regime ($t \le 1750$, $\gamma(t) = 0$, [`tasks_smoothing.js`](UF/js/geospatiale/files/png/tasks/tasks_smoothing.js#L80-L149))**:
   For each pixel $i$ with $P^A_{i,t} \ge 0.01$ ($0$ otherwise):
   - **Step 1 — Elderly monotonic ceiling**: Initialise $\tilde p^s_{i,a} = \max(0, p^s_{i,a})$. Sequentially for $a = 14, 15, 16, 17$ (ages $65, 70, 75, 80+$), if $\tilde p^s_{i,a-1} > 0$ and $\tilde p^s_{i,a} > 1.05\,\frac{w_a}{w_{a-1}}\tilde p^s_{i,a-1}$, set $\tilde p^s_{i,a} \leftarrow 1.05\,\frac{w_a}{w_{a-1}}\tilde p^s_{i,a-1}$.
   - **Step 2 — Coupled combined-density PAVA + sex-ratio clipping**: Apply [`Statistics.coupleAgeSexCohorts`](UF/js/statistics/statistics_isotonic.js#L61-L152) on $\mathcal A_+ = \{2,\dots,17\}$ to smooth combined density $(\tilde p^f_{i,a}+\tilde p^m_{i,a})/w_a$, then allocate across all $a \in \{0,\dots,17\}$ using empirical male shares clipped to $[\rho^-_a/(1+\rho^-_a),\, \rho^+_a/(1+\rho^+_a)]$.
   - **Step 3 — Secondary sex-specific PAVA**: Apply [`Statistics.pavaDecreasing`](UF/js/statistics/statistics_isotonic.js#L26-L52) with weights $w_a$ separately to the coupled female and male cohort buffers on $\mathcal A_+$ (because $w_a \equiv 5$ on $\mathcal A_+$, smoothing cohort counts is identical to smoothing annualised densities; note this step may slightly perturb the Step 2 sex-ratio bounds while guaranteeing decreasing per-sex density on $\mathcal A_+$).
   - **Step 4 — Per-pixel clamping**: Normalise the 36 cohorts to sum to $P^A_{i,t}$ (fallback $P^A_{i,t}/36$ if sum is $0$). Raw per-sex totals are **not** preserved.

2. **Transition Country-Bin PAVA Endpoint ($1750 < t < 1850$, $0 < \gamma(t) < 1$, [`tasks_smoothing.js`](UF/js/geospatiale/files/png/tasks/tasks_smoothing.js#L254-L280))**:
   Calls [`Statistics.coupleAgeSexCohorts`](UF/js/statistics/statistics_isotonic.js#L61-L152) on country-bin $(R^f_b, R^m_b)$ **without** secondary per-sex PAVA:
   $$\widehat d^I = \underset{z_2 \ge \cdots \ge z_{17} \ge 0}{\operatorname{argmin}} \sum_{a=2}^{17} w_a(z_a - d_a)^2, \qquad G^I_a = \begin{cases} R_a, & a < 2, \\ w_a \widehat d^I_a, & a \ge 2, \end{cases}$$
   $$m^I_a = \operatorname{clip}\!\left(m_a;\, \frac{\rho^-_a}{1+\rho^-_a},\, \frac{\rho^+_a}{1+\rho^+_a}\right), \qquad G^{m,I}_a = G^I_a m^I_a, \qquad G^{f,I}_a = G^I_a(1 - m^I_a).$$
   Replace the boxed conservation theorem in 1.5 with **combined-sex** conservation:
   $$\sum_{s,a} G^{s,I}_a = \sum_{s,a} R^s_a.$$
   Separate female and male sums are **not** conserved, and individual sex densities $G^{s,I}_a/w_a$ need not be non-increasing when $m^I_a$ varies with age.

### 1.6 Coupled Whittaker–Henderson Endpoint
- **Baseline biological sex-ratio prior ([`Statistics.default_biological_sex_ratios`](UF/js/statistics/statistics_isotonic.js#L11-L15))**:
  $$\rho^{\mathrm{base}} = (1.045, 1.042, 1.040, 1.038, 1.030, 1.015, 0.985, 0.975, 0.965, 0.960, 0.950, 0.930, 0.900, 0.860, 0.810, 0.750, 0.680, 0.600),$$
  triggered when $R_a \le 10^{-9}$ ([`statistics_whittaker.js`](UF/js/statistics/statistics_whittaker.js#L490-L499)).
- **Iteration cap & default ratio bounds**: Coordinate descent uses `max_iterations = 200` outer sweeps ([`age_sex.js`](histmap/3.data_transform/age_sex/age_sex.js#L455), [`statistics_whittaker.js`](UF/js/statistics/statistics_whittaker.js#L529)) with 30-step inner coordinate bisection. Biological sex-ratio bounds $[\rho^-_a, \rho^+_a]$ are **enforced by default** (`enforce_bounds = (options.preserve_sex_ratios !== true)` evaluates to `true` in [`age_sex.E_clampToStadester`](histmap/3.data_transform/age_sex/age_sex.js#L473), superseding an outdated JSDoc default on line 445).

### 1.7 Logistic Demographic-Transition Kernel
- **Endpoint & blend properties**:
  - For $t \le 1750$ ($\gamma(t) = 0$), execution follows the per-pixel pipeline in 1.5.1 rather than country-bin PAVA.
  - For $1750 < t < 1850$, *neither* country-bin endpoint guarantees per-sex decreasing density, **but** because *both* $G^{s,I}_{b,a}$ and $G^{s,W}_{b,a}$ clip male shares to $[m^-_a, m^+_a]$, the blended country-bin male share $G^m_{b,a}/(G^f_{b,a}+G^m_{b,a})$ is a convex combination of $m^I_{b,a}$ and $m^W_{b,a}$ and therefore **does** remain inside $[m^-_a, m^+_a]$ whenever $G^I_{b,a}+G^W_{b,a} > 0$ (correcting the report's statement to the contrary).
  - Note the scale-factor formulation ([`tasks_smoothing.js`](UF/js/geospatiale/files/png/tasks/tasks_smoothing.js#L274-L344)): $k^{s,(0)}_{b,a} = [1-\gamma(t)]k^{s,I}_{b,a} + \gamma(t)k^{s,W}_{b,a}$ where $k^{s,\bullet}_{b,a} = G^{s,\bullet}_{b,a}/R^s_{b,a}$ if $R^s_{b,a} > 0$ (else $1$), and $G^s_{b,a} = R^s_{b,a} k^{s,(0)}_{b,a}$ (so if $R^s_{b,a} = 0$, $G^s_{b,a} = 0$).

### 1.8 Cell Redistribution via 3-Iteration IPF & Source Compositing
- **Replace single-pass cell normalisation with 3-iteration IPF ([`tasks_smoothing.js`](UF/js/geospatiale/files/png/tasks/tasks_smoothing.js#L346-L407))**: For $\gamma(t) > 0$ and $\ell \in \{0, 1, 2\}$:
  $$N^{s,(\ell)}_{i,t,a} = P^A_{i,t}\,\frac{p^s_{i,t,a} k^{s,(\ell)}_{b(i),t,a}}{\sum_{r,c} p^r_{i,t,c} k^{r,(\ell)}_{b(i),t,c}} \quad (i \in \mathcal E_{b,t}),$$
  applying the uniform fallback $P^A_{i,t}/36$ on the final pass $\ell = 2$ if the denominator is $0$ (zero-denominator pixels contribute $0$ on passes $\ell < 2$). For $\ell \in \{0, 1\}$, update country factors whenever $S^{s,(\ell)}_{b,t,a} = \sum_{i \in \mathcal E_{b,t}} N^{s,(\ell)}_{i,t,a} > 0$:
  $$k^{s,(\ell+1)}_{b,t,a} = k^{s,(\ell)}_{b,t,a}\,\frac{G^s_{b,t,a}}{S^{s,(\ell)}_{b,t,a}},$$
  setting $N^{s,\mathrm{clamp}}_{i,t,a} = N^{s,(2)}_{i,t,a}$ (and $0$ when $P^A_{i,t} < 0.01$). Update the prose remark: 3-iteration IPF actively rakes cell-normalised country sums towards $G^s_{b,t,a}$.
- **Move HMD bypass into Step F compositing ([`age_sex.F_compositeTimeseries`](histmap/3.data_transform/age_sex/age_sex.js#L649-L725), [`tasks_composites.js`](UF/js/geospatiale/files/png/tasks/tasks_composites.js#L73-L155))**:
  - For $t < 1950$ where HMD rasters exist and $\sum_{r,c} H^r_{i,t,c} > 0$:
    $$N^s_{i,t,a} = \begin{cases} P^A_{i,t}\,\dfrac{H^s_{i,t,a}}{\sum_{r,c} H^r_{i,t,c}}, & P^A_{i,t} > 0, \\[8pt] H^s_{i,t,a}, & P^A_{i,t} \le 0. \end{cases}$$
  - For $t \ge 1950$: select $U^s_{i,t,a}$ ($1950 \le t < 2015$, $U$ available), $W^s_{i,t,a}$ ($t \ge 2015$, $W$ available), $U^s_{i,t,a}$ ($t \ge 2015$, $W$ absent, $U$ available) or $N^{s,\mathrm{clamp}}_{i,t,a}$ otherwise (which governs `2021..2025` when both $W$ and $U$ are absent).

### 1.9 Stock-Reconciliation Theorem
- **Correct the inverted UNWPP vs WorldPop compatibility claim**:
  - [`age_sex_UNWPP.B_clampToStadester`](histmap/2.data_cleaning/age_sex_UNWPP/age_sex_UNWPP.js#L370-L403) **does** dasymetrically clamp every pixel to Stadestér/Velkscala $P_{i,t}$ via [`GeoPNG.dasymetricCohortScale`](UF/js/geospatiale/files/png/png_dasymetric_framework.js#L132-L176) (with an infant SRB sanity clamp replacing national $m_{00}/f_{00} \notin [0.90, 1.20]$ by $1.05$). Because [`population_Velkscala`](histmap/2.data_cleaning/population_Velkscala/population_Velkscala.js#L121-L149) copies Stadestér verbatim for $t \ge 100$ AD, $\sum_{s,a} U^s_{i,t,a} = P_{i,t}$ holds on mapped populated pixels across `1950..2020`.
  - Conversely, [`age_sex_WorldPop.js`](histmap/2.data_cleaning/age_sex_WorldPop/age_sex_WorldPop.js#L1-L34) (`2015..2020`) copies WorldPop rasters **unclamped**, so $\sum_{s,a} W^s_{i,t,a} \neq P_{i,t}$.
- **Document all four stock-closure exceptions**:
  1. Unclamped WorldPop years (`2015..2020`);
  2. Modelled years `2024..2025` where $P^A_{i,t} = P_{i,2023} \neq P_{i,t}$;
  3. Modelled cells with $0 < P^A_{i,t} < 0.01$, which [`clampCohortsGraduation`](UF/js/geospatiale/files/png/tasks/tasks_smoothing.js#L99) zeroes out;
  4. Pre-1950 HMD cells with $P^A_{i,t} = 0$ and $\sum_{s,a} H^s_{i,t,a} > 0$, where raw $H^s_{i,t,a}$ passes through.

---

## 2. Definition 2 — Migration Estimation, Calibration & Global Conservation

### 2.1 Notation
- Clarify that `delta_total_population_${t}.png` generated by [`GeoPNG.generateDeltaSeries`](UF/js/geospatiale/files/png/png_delta_framework.js#L44-L98) **already stores annualised slope** $g_{i,t} = (P_{i,t} - P_{i,t^-})/h_t$ (`op: "slope"`, `scalar: 1 / year_diff`) rather than raw interval difference $\Delta P_{i,t}$ (which is why [`migration_OLS.js`](histmap/2.data_cleaning/migration_OLS/migration_OLS.js#L94) and [`births_deaths_OLS.js`](histmap/2.data_cleaning/births_deaths_OLS/births_deaths_OLS.js#L857) read `g = d_val` directly). No delta raster exists at $t = -10000$.
- Note $Z_{i,\widetilde t} \equiv \widetilde X_{i,t} \in \mathbb{R}^{35}$ ([`migration_OLS.covariates_obj`](histmap/2.data_cleaning/migration_OLS/migration_OLS.js#L3-L6) spreads `age_sex.covariates_obj`).

### 2.2 Migration Targets
- **Remove $\operatorname{clip}(\cdot; -1, 1)$**: [`migration_OLS.A_generateTargetRasters`](histmap/2.data_cleaning/migration_OLS/migration_OLS.js#L71-L99) stores **unclipped** per-capita residual migration for $t \ge 1950$ and $P_{i,t} \ge 1$:
  $$Y^M_{i,t} = \frac{g_{i,t} - A^B_{i,t} + A^D_{i,t}}{P_{i,t}},$$
  with Niva/Kummu preferred where valid (`2000..2019`, [`births_deaths_Kummu.js`](histmap/2.data_cleaning/births_deaths_Kummu/births_deaths_Kummu.js#L26)) and missing `dpop` pixels defaulting to $g_{i,t} = 0$.

### 2.3 Ridge Regression & Fallback Aggregation (Resolving Both Unsupplied Helpers)
- **Intercept-free RMS-scaled Ridge ([`Statistics.trainOLSModel`](UF/js/statistics/statistics_OLS.js#L453-L516), [`Statistics.ridgeRegression`](UF/js/statistics/statistics_OLS.js#L560-L613))**: [`extractImageDataset`](UF/js/statistics/learning_framework.js#L143-L196) retains cells $i \in \mathcal I^v_\tau$ with finite $Y^v_{i,\tau}$, finite covariates and $(Y^v_{i,\tau} \neq 0 \lor Z_{i,\widetilde\tau} \neq \mathbf 0)$. There is **no intercept**. Each feature $j$ is scaled by its unweighted sample RMS $s_j = \sqrt{\frac{1}{|\mathcal I^v_\tau|}\sum_{i \in \mathcal I^v_\tau} Z_{i,\widetilde\tau,j}^2}$ (fallback $1$ if $\le 10^{-12}$) prior to adding $\lambda_v I_{35}$ ($\lambda_v = 1$) to $\tilde Z^\top \tilde Z$. In unscaled coordinates, this minimises the stated objective with penalty matrix:
  $$J^v_\tau = \operatorname{diag}\!\left(s_1^2, \dots, s_{35}^2\right).$$
- **Exact fallback algebra ([`Statistics.geomeanOLSModels`](UF/js/statistics/statistics_OLS.js#L111-L168) + [`Math.weightedGeometricMean`](UF/js/number/number_basic.js#L441-L476))**:
  - Let $K_{\mathrm{clean}}$ be the count of finite $\widehat\theta^v_{\tau,j}$ across anchor models (including exact zeroes, which remain in $K_{\mathrm{clean}}$ while excluded from $\mathcal P_j$ and $\mathcal N_j$).
  - Both [`migration_OLS.js`](histmap/2.data_cleaning/migration_OLS/migration_OLS.js#L141) and [`births_deaths_OLS.js`](histmap/2.data_cleaning/births_deaths_OLS/births_deaths_OLS.js#L395) pass `weighting_function: (value) => Math.abs(value)`, which [`geomeanOLSModels`](UF/js/statistics/statistics_OLS.js#L149-L150) applies **to the scalar output** of `Math.weightedGeometricMean`:
    $$\overline\theta^v_j = \left| \frac{|\mathcal P_j|}{K_{\mathrm{clean}}}\exp\!\left(\frac{1}{|\mathcal P_j|}\sum_{\tau \in \mathcal P_j}\log\widehat\theta^v_{\tau,j}\right) - \frac{|\mathcal N_j|}{K_{\mathrm{clean}}}\exp\!\left(\frac{1}{|\mathcal N_j|}\sum_{\tau \in \mathcal N_j}\log|\widehat\theta^v_{\tau,j}|\right) \right| \ge 0.$$
  - Every fallback coefficient $\overline\theta^v_j$ is therefore forced non-negative.

### 2.4 Split Target-Bound Calibration (Migration Uses Log-Tail Tukey's Fences; Vital Events Keep $[Q_{0.01}, Q_{0.99}]$)
Section 2.4 must be split into distinct target-bound rules for migration versus vital events:

1. **2.4a Migration Target Bounds via Per-Year Log-Tail Tukey's Fences ([`migration_OLS.D_normaliseOLSRasters`](histmap/2.data_cleaning/migration_OLS/migration_OLS.js#L210-L259))**:
   - **Remove** the $P > 10{,}000$ filter, $|Y^M| > 10^{-10}$ filter, $[Q_{0.01}, Q_{0.99}]$ quantiles, cross-year $[\ell^M_*, u^M_*]$ pooling and $\varepsilon^M_t = e^{-n^M_t/15}$ shrinkage.
   - **Per-year stride-17 sample $S_t$ ($i \in \{0, 17, 34, \dots\}$)**:
     - If `migration_target_${t}.png` exists: sample finite $Y^M_{i,t}$ on cells with $P_{i,t} > 0$ (since $Y^M_{i,t}$ requires $P_{i,t} \ge 1$, effective filter is $P_{i,t} \ge 1$).
     - **Historical growth-rate fallback** (when no target raster exists, e.g. $t < 1950$ or $t > 2020$): if `delta_total_population_${t}.png` exists, sample annualised per-capita population growth $g_{i,t}/P_{i,t}$ at stride 17 on cells with $P_{i,t} > 0$ and finite $g_{i,t}$. (At $t = -10000$, $S_t = \varnothing \implies L^M_t = U^M_t = 0$.)
   - **Tukey log-tail bound compression**: Sort $s_{(0)} \le \cdots \le s_{(n-1)}$, set $q_1^s = Q_{0.25}(s)$, $q_3^s = Q_{0.75}(s)$, $I_s = q_3^s - q_1^s$, $F^-_s = q_1^s - 1.5 I_s$ and $F^+_s = q_3^s + 1.5 I_s$, and define:
     $$R_s(x) = \begin{cases} F^+_s + I_s\log\!\left(1 + \dfrac{x - F^+_s}{I_s}\right), & I_s > 0,\ x > F^+_s, \\[8pt] F^-_s - I_s\log\!\left(1 + \dfrac{F^-_s - x}{I_s}\right), & I_s > 0,\ x < F^-_s, \\[6pt] x, & \text{otherwise.} \end{cases}$$
     Set $L^M_t = R_s(s_{(0)})$ and $U^M_t = R_s(s_{(n-1)})$ (fallback $(F^-_s, F^+_s)$ if $U^M_t \le L^M_t$).

2. **2.4b Vital-Event Target Bounds ([`births_deaths_OLS.D_normaliseOLSRasters`](histmap/2.data_cleaning/births_deaths_OLS/births_deaths_OLS.js#L494-L539))**:
   - Retains the report's stride-7 $[Q_{0.01}, Q_{0.99}]$ sampling on positive targets, $n^v_t = 7 \times (\text{retained sample count})$, $\varepsilon^v_t = e^{-n^v_t/15}$, global $[\ell^v_*, u^{v,\mathrm{bound}}_*]$ shrinkage and lower clipping at $0$ for $v \in \{B, D_f, D_m\}$.

3. **2.4c Raw OLS Prediction Normalisation $u^v_{i,t}$**:
   - Both pipelines apply log-tail Tukey regularisation $R(z^v_{i,t})$ over inhabited land ($\mathrm{landarea}_i > 0 \land P_{i,t} > 0$), **except** the third-tier degenerate scale fallback is $a = 1.0$ for migration ([`migration_OLS.js`](histmap/2.data_cleaning/migration_OLS/migration_OLS.js#L281)) versus $a = 0.01$ for births and deaths ([`births_deaths_OLS.js`](histmap/2.data_cleaning/births_deaths_OLS/births_deaths_OLS.js#L561)).

### 2.5 Preliminary Migration, Feasibility Ceiling & 3-Iteration Waterfill Centring
Replace the unconstrained preliminary migration and single-pass centring formula with [`migration_OLS.E_deriveFinalRasters`](histmap/2.data_cleaning/migration_OLS/migration_OLS.js#L358-L531):

- **Preliminary migration $\widetilde M_{i,t}$ on $\Omega_+(t) = \{i : P_{i,t} > 0\}$** ($0$ outside $\Omega_+(t)$):
  - **Empirical UNWPP branch** (all three UNWPP vital rasters and delta raster exist): cap total deaths at population $A^{D,U}_{i,t} = \min\!\big(P_{i,t},\, [A^{D_f,U}_{i,t}]_+ + [A^{D_m,U}_{i,t}]_+\big)$ and cap residual migration at $g_{i,t} + P_{i,t}$:
    $$\widetilde M_{i,t} = \min\!\left(g_{i,t} - [A^{B,U}_{i,t}]_+ + A^{D,U}_{i,t},\; g_{i,t} + P_{i,t}\right).$$
  - **Modelled branch** (with $g_{i,t} = 0$ if no delta raster exists):
    $$\widetilde M_{i,t} = \min\!\left(P_{i,t} f^M_{i,t},\; g_{i,t} + P_{i,t}\right).$$
- **3-iteration one-sided waterfill centring**: Set $M^{(0)}_{i,t} = \widetilde M_{i,t}$. For $k = 0, 1, 2$:
  - Let $S^{(k)}_t = \sum_{i \in \Omega_+(t)} M^{(k)}_{i,t}$ and $\mathcal U^{(k)}_t = \{i \in \Omega_+(t) : M^{(k)}_{i,t} < g_{i,t} + P_{i,t}\}$ with $P_{\mathcal U^{(k)},t} = \sum_{i \in \mathcal U^{(k)}_t} P_{i,t}$.
  - Terminate early if $|S^{(k)}_t| < 0.01$ or $P_{\mathcal U^{(k)},t} = 0$.
  - Otherwise set $\kappa^{(k)}_t = -S^{(k)}_t / P_{\mathcal U^{(k)},t}$ and update:
    $$M^{(k+1)}_{i,t} = \begin{cases} \min\!\left(M^{(k)}_{i,t} + P_{i,t}\kappa^{(k)}_t,\; g_{i,t} + P_{i,t}\right), & i \in \mathcal U^{(k)}_t, \\ M^{(k)}_{i,t}, & i \notin \mathcal U^{(k)}_t. \end{cases}$$
  - Denote the final iterate by $M^0_{i,t}$.
- **Conservation qualification**: Replace exact algebraic zero-sum $\sum_i M^0_{i,t} = 0$ with approximate zero-sum $|\sum_i M^0_{i,t}| < 0.01$ subject to unsaturated capacity across 3 iterations (noting that cells already at the ceiling $M^{(k)}_{i,t} = g_{i,t} + P_{i,t}$ are excluded from $\mathcal U^{(k)}_t$ even when $S^{(k)}_t > 0 \implies \kappa^{(k)}_t < 0$).

### 2.6 & 2.7 Sex Allocation & Relation to Local Accounting
- **2.6**: Rogers–Castro schedule and SRB fallback match [`migration_OLS.js`](histmap/2.data_cleaning/migration_OLS/migration_OLS.js#L464-L496) (with $\max(0, N^s_{i,t,a})$ sanitation on cohort reads).
- **2.7**: Replace $A^B_{i,t} - A^D_{i,t} + M^0_{i,t} - g_{i,t} = P_{i,t}\kappa_t$ with $[A^{B,U}_{i,t}]_+ - A^{D,U}_{i,t} + M^0_{i,t} - g_{i,t} = M^0_{i,t} - \big(g_{i,t} - [A^{B,U}_{i,t}]_+ + A^{D,U}_{i,t}\big)$, reflecting death capping, upper ceiling clipping and multi-pass waterfill shifts.

---

## 3. Definition 3 — Birth/Death Estimation & Bivariate Hyperbolic Reconciliation

Sections **3.2, 3.3 and 3.4** remain valid as written (referencing 2.4b for vital-event calibration). Sections **3.1 and 3.5 through 3.11** must be **completely replaced** to reflect [`births_deaths_OLS.E_clampToStadester`](histmap/2.data_cleaning/births_deaths_OLS/births_deaths_OLS.js#L808-L1073).

### 3.1 Notation Updates
- Remove obsolete box/bisection symbols $B^\pm_i, D^\pm_i, M^\pm_i, \mathcal V_i, \mathcal F_t, \lambda^*$.
- Introduce $h_i \in \{0,1\}$ (pre-1950 HMD cell lock indicator), ISO3 country bin $b(i)$ (unmapped $\mapsto \text{"GLOBAL"}$), country scaling factors $(s^B_b, s^D_b)$ and hyperbolic discriminants $\Delta_b, \Delta_i$.

### 3.5 Effective Locks & Admissible Flow Domain (Replaces Old 3.5)
- Let $\mathrm{emp}_t \in \{0,1\}$ equal $1$ iff all three UNWPP vital rasters exist for year $t$ (`1950..2020`).
- Define the binary HMD lock indicator ([`births_deaths_OLS.js`](histmap/2.data_cleaning/births_deaths_OLS/births_deaths_OLS.js#L853-L856)):
  $$h_i = \mathbf 1\!\left\{\mathrm{emp}_t = 0 \;\land\; \big(\ell_{B,i} = 1 \;\lor\; (\ell_{f,i} = 1 \land \ell_{m,i} = 1)\big)\right\}.$$
- **Key behavioural changes**:
  1. **UNWPP years ($\mathrm{emp}_t = 1$) are never hard-locked**: $h_i = 0$ globally; UNWPP vital counts act as priors $(B^0_i, D^0_{f,i}, D^0_{m,i})$ scaled during reconciliation.
  2. **Pre-1950 partial HMD coverage**: If $\ell_{B,i} = 1$ while deaths are modelled, $h_i = 1$ freezes *both* actual births and modelled deaths on cell $i$. Conversely, if $\ell_{B,i} = 0$ and only *one* sex's death is actual ($\ell_{f,i} \neq \ell_{m,i}$), $h_i = 0$ and neither death component is locked during reconciliation.
  3. **Unbounded reconciled births**: While preliminary modelled births still satisfy $B^0_i \le 1.5\,Q^B_i$ in 3.4, reconciled flows on non-HMD cells ($h_i = 0$) are constrained only by:
     $$B_i \ge 0, \qquad 0 \le D_i \le P_i, \qquad M_i \le g_i + P_i.$$

### 3.6 & 3.7 Local & Global Feasibility Conditions (Replaces Old 3.6–3.7)
- **Local natural-change feasibility ($h_i = 0$)**: Given migration $M_i$, required natural increase $H_i = g_i - M_i$ admits $(B_i, D_i) \in [0,\infty) \times [0, P_i]$ with $B_i - D_i = H_i$ **if and only if**:
  $$H_i \ge -P_i \iff M_i \le g_i + P_i.$$
  Because $B_i$ has no upper cap in reconciliation, there is no lower migration bound $M^-_i$.
- **Global migration feasibility**: On $\mathcal R_t = \{i : P_i > 0,\ g_i \text{ and } M^0_i \text{ finite}\}$, fixing $M^*_i = M^{\mathrm{HMD}}_i = g_i - (B^0_i - D^0_i)$ on $h_i = 1$ admits a zero-sum migration vector $\sum_{i \in \mathcal R_t} M_i = 0$ with $M_i \le g_i + P_i$ on $h_i = 0$ (when $\{i \in \mathcal R_t : h_i = 0\} \neq \varnothing$) **if and only if**:
  $$\sum_{i \in \mathcal R_t : h_i = 1} \big(g_i - B^0_i + D^0_i\big) + \sum_{i \in \mathcal R_t : h_i = 0} \big(g_i + P_i\big) \ge 0.$$

### 3.8 Two-Stage Migration Reconciliation (Replaces Bisection Root-Finding in Old 3.8)
Delete the $[-10,10]$ bisection root-finder and quadratic-programming projection; replace with Stages 1–2 of [`E_clampToStadester`](histmap/2.data_cleaning/births_deaths_OLS/births_deaths_OLS.js#L844-L929):

1. **Stage 1 — HMD residual override ($h_i = 1$)**:
   $$M^{(0)}_i = g_i - (B^0_i - D^0_i), \qquad \Delta M^{(0)}_i = M^{(0)}_i - M^0_i,$$
   updating $(M^{(0)}_{f,i}, M^{(0)}_{m,i})$ via $\eta^0_{f,i} = M^0_{f,i}/(M^0_{f,i}+M^0_{m,i})$ (fallback $0.488$). On $h_i = 0$, $M^{(0)}_i = M^0_i$. (Note: $M^{(0)}_i$ on $h_i = 1$ is not capped at $g_i + P_i$.)

2. **Stage 2 — 3-iteration non-HMD waterfill ($k = 0, 1, 2$)**:
   - Compute planet-wide sum $S^{(k)} = \sum_{i \in \mathcal R_t} M^{(k)}_i$ and unsaturated non-HMD population $P^{(k)}_{\mathrm{elig}} = \sum_{i \in \mathcal U^{(k)}_0} P_i$ over $\mathcal U^{(k)}_0 = \{i \in \mathcal R_t : h_i = 0 \land M^{(k)}_i < g_i + P_i\}$.
   - Terminate early if $|S^{(k)}| < 0.1$ or $P^{(k)}_{\mathrm{elig}} = 0$.
   - Otherwise set $\lambda^{(k)} = -S^{(k)} / P^{(k)}_{\mathrm{elig}}$ and for every $i \in \mathcal U^{(k)}_0$:
     $$M^{(k+1)}_i = \min\!\left(M^{(k)}_i + P_i\lambda^{(k)},\; g_i + P_i\right),$$
     updating $(M^{(k+1)}_{f,i}, M^{(k+1)}_{m,i})$ by $M^{(k+1)}_i - M^{(k)}_i$ using current share $\eta^{(k)}_{f,i} = M^{(k)}_{f,i}/(M^{(k)}_{f,i}+M^{(k)}_{m,i})$ (fallback $0.488$). Denote the final migration state by $M^*_i$.

### 3.9 Bivariate Hyperbolic (Minimum-Information) Vital Reconciliation (Replaces Equal-Weight $L_2$ Projection in Old 3.9)
On $h_i = 1$, $(B^*_i, D^*_{f,i}, D^*_{m,i}) = (B^0_i, D^0_{f,i}, D^0_{m,i})$. On non-HMD cells ($h_i = 0$), define $H_i = g_i - M^*_i$ ([`births_deaths_OLS.js`](histmap/2.data_cleaning/births_deaths_OLS/births_deaths_OLS.js#L931-L1037)):

1. **Stage 3 — Country-level bivariate scaling**: For each ISO3 bin $b$, sum over $\{i \in \mathcal R_t : h_i = 0,\, b(i) = b\}$:
   $$B^{\mathrm{raw}}_b = \sum B^0_i, \qquad D^{\mathrm{raw}}_b = \sum D^0_i, \qquad H_b = \sum H_i.$$
   If $B^{\mathrm{raw}}_b > 0$ and $D^{\mathrm{raw}}_b > 0$, define:
   $$\Delta_b = \sqrt{H_b^2 + 4 B^{\mathrm{raw}}_b D^{\mathrm{raw}}_b}, \qquad B^*_b = \frac{H_b + \Delta_b}{2}, \qquad D^*_b = \frac{\Delta_b - H_b}{2},$$
   $$s^B_b = \frac{B^*_b}{B^{\mathrm{raw}}_b}, \qquad s^D_b = \frac{D^*_b}{D^{\mathrm{raw}}_b}.$$
   Otherwise set $s^B_b = s^D_b = 1$.
   - *Variational characterisation*: $(B^*_b, D^*_b)$ uniquely solves $B - D = H_b$ under reciprocal scaling $s^B_b s^D_b = 1$ ($\iff B^*_b D^*_b = B^{\mathrm{raw}}_b D^{\mathrm{raw}}_b$), minimising the generalized Kullback–Leibler (Poisson minimum-information) divergence
     $$\underset{B>0,\,D>0}{\operatorname{minimise}} \left\{ B\log\frac{B}{B^{\mathrm{raw}}_b} - B + D\log\frac{D}{D^{\mathrm{raw}}_b} - D \right\} \quad \text{subject to } B - D = H_b.$$

2. **Stage 4 — Pixel-level hyperbolic reconciliation & mortality cap**: Set $\bar B_i = s^B_{b(i)} B^0_i$ and $\bar D_i = s^D_{b(i)} D^0_i$ (with JS `|| 1` fallback if a scaling factor underflows to $0$). Compute:
   $$(\widetilde B_i, \widetilde D_i) = \begin{cases} \left(\dfrac{H_i + \sqrt{H_i^2 + 4\bar B_i\bar D_i}}{2},\; \dfrac{\sqrt{H_i^2 + 4\bar B_i\bar D_i} - H_i}{2}\right), & \bar B_i > 0 \text{ and } \bar D_i > 0, \\[10pt] \big(\max(0, H_i),\; \max(0, -H_i)\big), & \text{otherwise,} \end{cases}$$
   and impose the mortality cap $D_i \le P_i$:
   $$(B^*_i, D^*_i) = \begin{cases} \big(\max(0, P_i + H_i),\; P_i\big), & \widetilde D_i > P_i, \\ (\widetilde B_i, \widetilde D_i), & \widetilde D_i \le P_i. \end{cases}$$
   - **Exact product-invariance identity**: In exact real arithmetic, $B^*_b D^*_b = (\Delta_b^2 - H_b^2)/4 = B^{\mathrm{raw}}_b D^{\mathrm{raw}}_b \implies s^B_b s^D_b = 1$, so $\bar B_i \bar D_i = (s^B_{b(i)} s^D_{b(i)}) B^0_i D^0_i = B^0_i D^0_i$. Thus Stage 3 country pre-scaling cancels out identically inside $\Delta_i = \sqrt{H_i^2 + 4\bar B_i\bar D_i}$ on every interior pixel, altering $(\widetilde B_i, \widetilde D_i)$ only if IEEE-754 float64 cancellation rounds $\Delta_b - H_b$ to $0$ when $H_b \gg 2\sqrt{B^{\mathrm{raw}}_b D^{\mathrm{raw}}_b}$ (triggering `country_sd || 1`).
   - **Exact local closure**: Because $M^*_i \le g_i + P_i$ on $h_i = 0$, $P_i + H_i = P_i + g_i - M^*_i \ge 0$, guaranteeing $B^*_i - D^*_i = H_i = g_i - M^*_i$ across all branches.

### 3.10 Sex-Specific Death & Migration Allocation (Update Old 3.10)
- **Remove singly-locked death cases**: Only $h_i = 1$ retains $(D^0_{f,i}, D^0_{m,i})$. Every $h_i = 0$ pixel allocates $D^*_i$ proportionally via $\rho_i = D^0_{m,i}/D^0_i$ for $D^0_i > 0$ (fallback $0.512$):
  $$D^*_{m,i} = \rho_i D^*_i, \qquad D^*_{f,i} = D^*_i - D^*_{m,i}.$$
- **Migration sex shares**: Incremental updates $m_s \leftarrow m_s + \eta_s\Delta m$ with $\eta_f + \eta_m = 1$ preserve $M^*_{f,i} + M^*_{m,i} = M^*_i$ identically.

### 3.11 Closure Theorem & Numerical Implementation (Replaces Old 3.11 Bullet List)
- **Delete** all references to the $[-10,10]$ bracket, 5 endpoint expansions, 45 bisection iterations, $|F_t(\lambda)| < 10^{-5}$ stopping and $10^{-7}$ skipped migration writes.
- **Document actual numerical tolerances and boundary residuals**:
  1. **Waterfill tolerance & iteration cap**: Stage 2 halts at $|\sum_{i \in \mathcal R_t} M_i| < 0.1$ or after 3 iterations (and excludes $M^{(k)}_i = g_i + P_i$ cells when $S^{(k)} > 0$), so global migration conservation holds within $|\sum_i M^*_i| < 0.1$ when unsaturated non-HMD capacity suffices.
  2. **Newly depopulated cells ($P_{i,t} = 0$ with $P_{i,t^-} > 0$)**: Reconciliation skips $P_{i,t} \le 0$ and disk writes output $B^*_{i,t} = D^*_{i,t} = M^*_{i,t} = 0$ ([`births_deaths_OLS.js`](histmap/2.data_cleaning/births_deaths_OLS/births_deaths_OLS.js#L981)), leaving $g_{i,t} = -P_{i,t^-}/h_t < 0$ unclosed on cells that go extinct over $(t^-, t]$.
  3. **Missing `d_val` edge case**: [`births_deaths_OLS.js`](histmap/2.data_cleaning/births_deaths_OLS/births_deaths_OLS.js#L893) includes cells with `pop > 0 && !isNaN(m_val)` in `total_m_sum` even when `isNaN(d_val)`, while excluding them from updates.
  4. **`float32` RGBA serialisation**: Final PNG outputs quantise all flows to IEEE-754 `binary32`.

---

## 4. Definition 4 (Compact Form) & Footnotes

### 4.1–4.3 Compact Form Updates
- **4.1 Notation**: Replace $\mathcal I$, $B^\pm_{i,t}, D^\pm_{i,t}, M^\pm_{i,t}$ and single-pass $\mathcal A_t$ with:
  - $\mathcal I_{\mathrm{pix}}$: per-pixel elderly-ceiling + coupled-PAVA + per-sex-PAVA operator ($t \le 1750$);
  - $\mathcal I_{\mathrm{bin}}$: country-bin coupled combined-density PAVA with sex-ratio bounds ($1750 < t < 1850$);
  - $\mathcal A^{\mathrm{IPF}}_t$: 3-iteration IPF redistribution followed by Step F source compositing;
  - $\mathcal W^M_t$: upper-capped ($M \le g + P$) 3-iteration waterfill operator;
  - $\mathcal H$: bivariate hyperbolic natural-change operator with $D \le P$ mortality cap.
- **4.2.A (Age–sex stocks)**: Separate $t \le 1750$ ($\mathbf N^{\mathrm{clamp}}_t = \mathcal I_{\mathrm{pix}}(\mathbf p_t, \mathbf P^A_t)$) from $t > 1750$ ($G^s_{b,t,a} = [1-\gamma(t)]\,\mathcal I_{\mathrm{bin}}(R)^s_{b,t,a} + \gamma(t)\,\mathcal W(R)^s_{b,t,a}$, redistributed via 3-iteration IPF), followed by Step F HMD/UNWPP/WorldPop compositing.
- **4.2.B (Preliminary migration)**: Include the UNWPP death cap $A^{D,U}_{i,t} \le P_{i,t}$, the upper cap $\widetilde M_{i,t} \le g_{i,t} + P_{i,t}$ in both branches, and replace the single-step mean subtraction with the 3-iteration waterfill $\mathbf M^0_t = \mathcal W^M_t(\widetilde{\mathbf M}_t; \mathbf g_t, \mathbf P_t; 0.01)$.
- **4.2.C & 4.2.D (Vital events & reconciliation)**: Replace $M^\pm_{i,t}$, $\lambda^*_t$ root-finding and $\operatorname{clip}((B^0+D^0+H)/2; L, U)$ with:
  1. $M^{\mathrm{HMD}}_{i,t} = g_{i,t} - B^0_{i,t} + D^0_{i,t}$ on $h_{i,t} = 1$;
  2. 3-iteration non-HMD waterfill $\mathbf M^*_t$ under $M_{i,t} \le g_{i,t} + P_{i,t}$ to tolerance $0.1$;
  3. Hyperbolic natural-change closure $(B^*_{i,t}, D^*_{i,t}) = \mathcal H(\bar B_{i,t}, \bar D_{i,t}, g_{i,t} - M^*_{i,t}, P_{i,t})$ on $h_{i,t} = 0$.
- **4.3 (Simultaneous constraints)**: Qualify global interval stock closure $\sum_i P_{i,t} - \sum_i P_{i,t^-} = h_t(\sum_i B^*_{i,t} - \sum_i D^*_{i,t})$ with (i) absence of newly extinct cells ($P_{i,t^-} > 0 \to P_{i,t} = 0$), (ii) the $|\sum_i M^*_{i,t}| < 0.1$ waterfill stopping tolerance and (iii) the WorldPop (`2015..2020`), post-2023 $P^A_{i,t}$ and sub-$0.01$ stock caveats from 1.9.

### Footnotes
1. **Footnote 1 (*"The 1500 cutoff is due to the Columbian Exchange."*)**: **Delete** (or replace with a note on $t_{\mathrm{eff}} = \max(t, 1750)$, explaining that MNL temporal ensemble weights freeze at the 1750 start of HMD training coverage).
2. **Footnote 6 (*"Magic numbers from implementation by Husinger for Rogers-Castro..."*)**: Correct spelling to **Hunsinger**.
3. **Footnote 7 (*"Tukey's fences used to preserve intra-country spatial variance."*)**: Expand to note that log-tail Tukey's fences ($q_1 - 1.5a$, $q_3 + 1.5a$) govern **both** spatial rate normalisation of raw OLS predictions $z^v_{i,t}$ for $v \in \{M, B, D_f, D_m\}$ **and** per-year migration rate bound calibration $[L^M_t, U^M_t]$ from empirical residual targets ($t \ge 1950$) or population growth rates $g_{i,t}/P_{i,t}$ ($t < 1950$).

