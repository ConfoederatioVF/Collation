# Stages C & F — Evidence-Based Settlement Gazetteers, 3-Phase Metro Reconciliation & Partitioned Toponymy

All numeric thresholds (`provenance_caps`, `population_distribution_guards`, `municipal_decomposition_rules`, `metro_reconciliation_policy`, `suspicious_toponym_patterns`, `jurisdiction_source_matrix`) live in [viscount_skill_profiles.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/config/viscount_skill_profiles.json5).

---

## 1. Stage C — 4-Wave Asymptotic Maximum-Saturation Loop (`Gatekeeper C`)

1. **Wave 1 (Per-Jurisdiction Full-Row Ingestion)**: Iterate over **every** jurisdiction in `jurisdiction_source_matrix` (`0` `LIMIT`/`head`/Top-N caps; never stop at global `Wikidata`/`OSM`/`GeoNames`; crowd share `<= 20%` per jurisdiction). Register raw candidates and `jurisdiction_coverage` in `<stem>_source_ledger.json5` before filtering.
2. **Wave 2 (Archival PDFs & Tables)**: Archive `>= 15` SHA-256-unique `%PDF-` primary monographs/cadastres (`> 10,24 kB`, filename `<= 72` chars) per chapter into `./papers/` covering every jurisdiction; extract 100% of settlement and subadmin tables.
3. **Wave 3 (Evidence-Only Longitudinal Backfill & Chronology Targets)**:
   - **Strictly Evidence & Canonical-Literature Population Law**: Every population estimate MUST come directly from historical evidence (excavated hectares × peer-reviewed period urban densities, walled areas, hearth/tax/parish registers, *tahrir defters*, *salnames*, imperial/colonial/national censuses) or canonical demographic monographs.
   - **Hard Anti-Heuristic Bans (`[FAIL]` in `verify_gazetteer_exhaustiveness.js`)**:
     - Zero pseudo-uniform population distributions, hardcoded tier stamping, ceiling clamps (`380`-person plateaus), deterministic sine/hash jitter, or narrow synthetic bands (`top1_peak_share <= 3,5%`, `top3_peak_share <= 12%`, `unique_peak_ratio >= 55%` for `n >= 50`, `interquartile_log_spread >= 0,40`).
     - Zero blind exponential pre-census back-projections or unattested synthetic village-formation CDFs. Where archival sources are non-tabular, dispatch **read/write-only evidence-assessment swarms** paired with a separate `@auditor` sending unacceptable distributions back.
   - Declare scholarly regional `chronology_targets` (benchmark-year settlement floors + `foundation_year` guards for planned/industrial/colonial new towns) in `<slug>_gazetteers.json5` (`early_modern_step_ratio <= 1,35`, `post_1995_only_ratio <= 0,45`, adjacent decennial jump `<= 3,0x`).
4. **Wave 4+ (Sub-Region × Era Gap-Hunter)**: Close every empty/sparse inhabited RGB sub-region across historical (`<= 1900`) and modern eras until `marginal_gain <= 2,0%`, `unaccounted == 0`, `0` variant-spelling duplicates `<= 25 km`, `0` suspicious temple/monument/admin-suffix names, `0` compound `"A & B"` modern municipalities, and `0` homonym hijacks.
5. **Anti-Circularity Firewall**: Sub-chapters MUST NOT read or cite SVEA on-disk demographic tables (`population_Substrata*`, `population_Velkscala`, `population_Stadester`, `atlas_defacto.naissance` pop figures) or global fallback compendia (`@McEvedy`, `@KleinGoldewijk`, `Populstat`, `Chandler1987`, `Modelski2003`, `Maddison`).

---

## 2. Municipal-Limits Non-Decomposition Rule (`consolidate_municipal_districts.js`)

Distinguish sharply between **intra-municipal subdivisions** and **extra-municipal suburbs**:
- **Inside Municipal Limits (NEVER DECOMPOSE)**: Subdivisions within a large city's municipal limits (*arrondissements*, *boroughs*, *wards*, municipal-core *ilçes*, *shiyakhas*/*qisms*, urban *raions*, *Stadtbezirke*, *ku*, *quận*, *alcaldías*, `mod_uk`) MUST retain the **single top-level municipal city structure**.
  - Where a census supplies the unified municipality total, exclude overlapping intra-municipal rows (`reason: "intra_municipal_subdivision"`).
  - Where a census omits the unified row and lists only intra-municipal districts, aggregate them onto one top-level city entity whose canonical name and coordinates follow **capital city status overrides largest population; otherwise the largest-population constituent district inherits the city name**.
- **Outside Municipal Limits (PRESERVE DISTINCT SETTLEMENTS)**: Independent suburbs, commuter towns, and satellite municipalities sitting outside municipal limits remain separate settlement records (never collapsed into the central city, and blocked from hijacking the central city's metadata).

---

## 3. Spatiotemporally Agnostic 3-Phase Metropolitan Reconciliation (`StadesterMetroReconciler.js`)

Whenever scholarly datasets provide mixed **metropolitan**, **city proper**, and **suburban** populations across any era (`-10000..2025`), avoid double counting and protect major cities (`London`, `Paris`, `New York`, `Tokyo`) from stochastic-like raster shocks using explicit `population_scope` (`"city_proper"`, `"suburb"`, `"metro"`):

1. **Separate Datapoints**: Major cities may carry BOTH a separate `"metro"` datapoint ($P_{\text{metro}}(t)$) AND a persistent municipal `"city_proper"` datapoint ($P_0(t)$), alongside independent `"suburb"` datapoints ($P_1(t), \dots, P_k(t)$).
2. **Membership Weights $u_{i,m}(t) \in [0, 1]$** ($\sum_m u_{i,m}(t) \le 1$ across multi-metro corridors):
   - **`1975–2025`**: Exact 5-year-interpolated GHSL DEGURBA urban-centre polygon membership (`stadester_ghsl.js`).
   - **`-10000..1974`**: Explicit `metro_parent_key` / `metro_members` links plus transport-era allometric radial envelope (`t < 1830`: `<= 12 km`; `1830..1944`: `<= 28 km`; `1945..1974`: smooth `1965–1975` taper into `1975` DEGURBA).
3. **3-Phase Reconciliation**:
   - **Phase 1 (Subtract Constituents)**: $S_{\text{sys}}(t) = \sum_{i \in \mathcal{S}} u_{i,m}(t) P_i(t)$, $R_{\text{metro}}(t) = P_{\text{metro}}(t) - S_{\text{sys}}(t)$. If $R_{\text{metro}}(t) > 0$, the separate `Metro` datapoint stays active holding **only** the positive unenumerated remainder $R_{\text{metro}}(t)$, whilst `City proper` and `Suburbs` keep their exact $P_i(t)$.
   - **Phase 2 (System Shares)**: $w_i(t) = u_{i,m}(t) P_i(t) / S_{\text{sys}}(t)$ ($\sum w_i = 1$).
   - **Phase 3 (Overflow Removal & Redistribution when $R_{\text{metro}}(t) \le 0$)**: Redistribute negative overflow $R_{\text{metro}}(t)$ proportionally across `City proper` and `Suburbs` ($P_i^{\text{in}}(t) = u_{i,m} P_i + R_{\text{metro}} w_i = P_{\text{metro}} w_i \ge 0$) and **remove the separate `Metro` datapoint for year $t$** ($R_{\text{metro}}'(t) = 0$), whilst the **municipal `City proper` datapoint continues existing uninterrupted**.
   - **Guarantees**: $C^0$-continuous total raster urban mass ($= P_{\text{metro}}(t)$) across $R_{\text{metro}} = 0$, strict non-negativity, preserved intra-metro shares, and exact algebraic compatibility with `stadester_ghsl.js`.

---

## 4. Stage F — Partitioned Dataview `city_metadata/` & Zero-Tolerance Flash Auditor (`Gatekeeper F`)

### Partitioned Storage & Unified Capital Grouping
`Dataview/data/stadester/stadester_2.0/city_metadata/` (`city_metadata_manifest.json`, `version: "2.0"`) replaces the monolithic file (`stadester_1.0/` and `stadester_1.1/` stay isolated):
- **`00_capitals.json` (Priority Tier 0 — Loaded & Bound First)**: Groups `capital` / `capital_records` (reconciled with `state_capitals.json`) directly inside the same record as `name`, `historical_names`, `other_names`, `coords`, and `key`, guaranteeing every capital city receives its verified historical names and preventing lower-tier shards from clobbering it.
- **`01_centaur.json` .. `14_nicethi.json`** (auto-sub-sharded at `<= 12 MB` / `20k` records): Keyed regional maps so updating one region never touches or wipes sibling regions.

### Chunked `Gemini 3.8 Flash` Swarm, Encoding Rulebook & Zero-Tolerance Auditor
1. **Chunking (`extract_missing_city_metadata.js --project=<KEY>`)**: Extracts missing, single-entry stub (`>= 10k` or indigenous/colonial heritage), capital, duplicate, inverted-article, or corrupt entries into `25–30`-city geographic chunks (`tests/toponymy_batches/<slug>/chunk_NNN.json`). Deterministic single-entry staging is banned for capitals, pre-1950 settlements, cities `>= 5k`, and indigenous-heritage regions.
2. **Structural Encoding Rulebook (Injected into Every Flash Worker)**:
   - **Endonymic Latin Transliteration**: Use official/scholarly endonyms in clean Latin Unicode (Hepburn, Pinyin, Revised Romanization, BGN/PCGN, ALA-LC; zero foreign exonyms like `Baranawitschy`/`Kiev`, zero ASCII backtick/apostrophe haceks `Ker`c`/`Pe'c`, zero comma-inverted articles `Mans, Le`, zero parentheticals, zero street/admin paths, zero temple/shrine/monument names, zero foreign-script `other_names` spam in Latin-only countries).
   - **Pre-Colonial & Indigenous Endonyms**: Mandatory pre-colonial indigenous endonym before colonial founding + documented restoration date where applicable (`Nuuk`, `Auckland`, `Sydney`, `Utqiaġvik`, `Iqaluit`, `Cahokia`, `Cusco`, `Tenochtitlan`, Hokkaido/Ryukyu, Sápmi, Siberia).
   - **Strict Chronology**: `YYYY.M.D` (`-10000 <= Y <= 2026`, `Y != 0`, valid month/day), earliest entry `<= earliest_year`, zero fabricated `1950.1.1` dates, zero consecutive variant-spelling renames (variants belong in `other_names`).
   - **Capital-Era Alignment**: Every `00_capitals.json` polity interval must align with the city's contemporaneous historical name.
3. **Zero-Tolerance Final Auditor (`toponymy_auditor` — Strictly Separate Read-Only Agent)**:
   - Reviews every resolved chunk alongside `audit_city_metadata.js`. **If even a single historical error is detected**, rejects that chunk with line-item diagnostics and sends the Flash worker back to fix it (escalating in-place to `Hydrogen` after 2 failures).
   - `merge_city_metadata.js --project=<KEY> --require-auditor-signoff` commits atomically ONLY into `00_capitals.json` and the target regional shard, then triggers incremental Dataview cache refresh (`--only-project=<KEY>`).
