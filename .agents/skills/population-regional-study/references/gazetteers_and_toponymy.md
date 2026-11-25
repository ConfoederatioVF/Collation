# Stages C & F — Evidence-Based Settlement Gazetteers, 3-Phase Metro Reconciliation & Partitioned Toponymy

All numeric thresholds (`provenance_caps`, `population_distribution_guards`, `municipal_decomposition_rules`, `metro_reconciliation_policy`, `toponymy_pipeline_policy`, `toponymy_naming_policy`, `overlay_binding_policy`, `suspicious_toponym_patterns`, `jurisdiction_source_matrix`) live in [viscount_skill_profiles.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/config/viscount_skill_profiles.json5).

---

## 1. Stage C — 4-Wave Asymptotic Maximum-Saturation Loop (`Gatekeeper C`)

1. **Wave 1 (Per-Jurisdiction Full-Row Ingestion)**: Iterate over **every** jurisdiction in `jurisdiction_source_matrix` (`0` `LIMIT`/`head`/Top-N caps; never stop at global `Wikidata`/`OSM`/`GeoNames`; crowd share `<= 20%` per jurisdiction). Register raw candidates and `jurisdiction_coverage` in `<stem>_source_ledger.json5` before filtering.
2. **Wave 2 (Archival PDFs & Tables)**: Archive `>= 15` SHA-256-unique `%PDF-` primary monographs/cadastres (`> 10,24 kB`, filename `<= 72` chars) per chapter into `./papers/` covering every jurisdiction; extract 100% of settlement and subadmin tables.
3. **Wave 3 (Evidence-Only Longitudinal Backfill & Chronology Targets)**:
   - **Strictly Evidence & Canonical-Literature Population Law**: Every population estimate MUST come directly from historical evidence (excavated hectares × peer-reviewed period urban densities, walled areas, hearth/tax/parish registers, *tahrir defters*, *salnames*, imperial/colonial/national censuses) or canonical demographic monographs.
   - **Hard Anti-Heuristic Bans (`[FAIL]` in `verify_gazetteer_exhaustiveness.js`)**:
     - Zero pseudo-uniform population distributions, hardcoded tier stamping, ceiling clamps (`380`-person plateaus), deterministic sine/hash jitter, or narrow synthetic bands (`top1_peak_share <= 3,5%`, `top3_peak_share <= 12%`, `unique_peak_ratio >= 55%` for `n >= 50`, `interquartile_log_spread >= 0,40`).
     - Zero blind exponential pre-census back-projections or unattested synthetic village-formation CDFs. Where archival sources are non-tabular, dispatch **read/write-only evidence-assessment swarms** (`<= 24` concurrent) paired with a separate `@auditor` sending unacceptable distributions back.
   - Declare scholarly regional `chronology_targets` (benchmark-year settlement floors + `foundation_year` guards for planned/industrial/colonial new towns) in `<slug>_gazetteers.json5` (`early_modern_step_ratio <= 1,35`, `post_1995_only_ratio <= 0,45`, adjacent decennial jump `<= 3,0x`).
4. **Wave 4+ (Sub-Region × Era Gap-Hunter)**: Close every empty/sparse inhabited RGB sub-region across historical (`<= 1900`) and modern eras until `marginal_gain <= 2,0%`, `unaccounted == 0`, `0` variant-spelling duplicates `<= 25 km`, `0` suspicious temple/monument/admin-suffix names, `0` compound `"A & B"` modern municipalities, and `0` homonym hijacks.
5. **Anti-Circularity Firewall**: Sub-chapters MUST NOT read or cite SVEA on-disk demographic tables (`population_Substrata*`, `population_Velkscala`, `population_Stadester`, `atlas_defacto.naissance` pop figures) or global fallback compendia (`@McEvedy`, `@KleinGoldewijk`, `Populstat`, `Chandler1987`, `Modelski2003`, `Maddison`).

---

## 2. Structural Rule for Merging & Municipal-Limits Non-Decomposition (`consolidate_municipal_districts.js`)

Distinguish sharply between **same-municipality splits/subdivisions** and **distinct extra-municipal settlements in the same metro area**:
- **Same Municipal Boundary (MUST MERGE TO ONE CITY PROPER)**:
  - If two or more settlement points accidentally fall inside the **same city-proper municipal boundary** (whether duplicate geocoded pins `<= 2,5 km` or intra-municipal *arrondissements*, *boroughs*, *wards*, municipal-core *ilçes*, *shiyakhas*/*qisms*, urban *raions*, *Stadtbezirke*, *ku*, *quận*, *alcaldías*, `mod_uk`), they MUST be merged up into **one unified city-proper municipality** via `consolidate_municipal_districts.js` (passing `--municipal-boundaries=<geojson>` whenever official city-proper polygons are available; metro polygons are explicitly rejected).
  - Where a census supplies the unified municipality total, exclude overlapping intra-municipal rows (`reason: "intra_municipal_subdivision"`).
  - Where a feed lists only intra-municipal districts or split municipal points, aggregate them onto one top-level municipal entity whose canonical name and coordinates follow **capital city status overrides largest population; otherwise the largest-population constituent inherits the municipal name**.
- **Distinct Municipalities in the Same Metro Area (NEVER MERGE TOGETHER)**:
  - Independent suburbs, commuter towns, and neighbouring municipalities outside the central city's municipal boundary MUST NEVER be collapsed into the central city or merged with one another, even when they belong to the same continuous metropolitan area (e.g. `Paris` vs `Boulogne-Billancourt`/`Saint-Denis`; `Tokyo` vs `Yokohama`; `Aulla` vs `Podenzana`/`Tresana`). They remain separate settlement records and are reconciled strictly through the 3-Phase metro accounting law below.

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

## 4. Stage F — Persistent Spatial Point Overlay `city_metadata/` & 2-Pass Toponymy (`Gatekeeper F`)

### Persistent Spatial Point Overlay & Compatible On-Disk Shards
`Dataview/data/stadester/stadester_2.0/city_metadata/` (`city_metadata_manifest.json`, `version: "2.0"`) retains the **exact current Dataview on-disk JSON layout** (`name`, `coords: [lng, lat]`, `historical_names: [{ date, name }]`, `other_names`, `capital`, `key`, `country`) for full backwards compatibility whilst operating at runtime (`bindCityMetadataOverlay()` in `stadester_metadata.ts` and `stadester_compiler.ts`) as a **persistent spatial point overlay**:
- **`00_capitals.json` (Priority Tier 0 — Loaded, Bound & Capital-Locked First)**: Drops capital overlay points onto the nearest underlying settlement point (preferring `city_proper` over `metro` shells; `<= 2,5 km` unconditional snap, `<= 10 km` nearest underlying settlement, `<= 15 km` Tier-0 capital fallback with stem/country validation). Once bound, `is_capital_locked = true` prevents any regional shard or sub-district record from ever overriding that capital city's canonical name or timeline.
- **`01_centaur.json` .. `14_nicethi.json`** (auto-sub-sharded at `<= 12 MB` / `20k` records): Persistent regional spatial overlays ensuring shard rebuilds never wipe curated metadata and cross-continent homonyms (`50 km` name-first matching is retired) can never hijack unrelated cities.
- `stadester_1.0/` and `stadester_1.1/` remain completely untouched.

### Compact Batch Schema & Adaptive `n <= 24` Chunking (`extract_missing_city_metadata.js`)
To eliminate token bloat and subagent exhaustion (`thousands` of tiny 25-city batches), `extract_missing_city_metadata.js --project=<KEY>` emits **minimal compact batch JSON** containing ONLY `[lng, lat]` coordinates and the existing `date: string` map (`yyyy.m.d`):
```json
[
  { "coords": [28.9784, 41.0082], "cap": true, "names": { "-667.1.1": "Byzantium", "330.5.11": "Constantinople", "1930.3.28": "Istanbul" } }
]
```
- Verbose operational metadata (`key`, `country`, `max_pop`, `earliest_year`) is stripped from LLM batch files and kept strictly in a local deterministic sidecar (`pass1/batch_index.json`) consumed by `merge_city_metadata.js`.
- **Adaptive Batch Sizing**: `batch_size = clamp(ceil(pass1_count / 24), 40, 200)` (`40–200` cities per batch, `<= 24` batches per wave). If a macro-region exceeds `4.800` Pass-1 settlements, chunks execute in sequential waves of at most `24` concurrent agents (`global Semaphore(24)`).

### Strict 2-Pass Toponymy System
1. **Pass 1 (`max_pop > 10k` at any point in history OR capital city — Knowledge-Base Agent Swarm, `n <= 24`)**:
   - Written to `tests/toponymy_batches/<slug>/pass1/batch_NNN.json`.
   - Resolved by `run_historical_names_swarm.py` (`Gemini 3.8 Flash` workers + strictly separate read-only `toponymy_auditor` sharing one global `asyncio.Semaphore(24)`).
   - Zero-tolerance auditor: after a zero-cost programmatic pre-audit (date syntax, Latin script, intra-municipal district filter, capital protection), the read-only auditor reviews the compact batch; **even a single historical error** triggers surgical error-only re-prompting (escalating in-place to `Hydrogen` after 2 failures) until `pass1/auditor_signoff.json` logs `approved: true, errors_remaining: 0`.
2. **Pass 2 (Residual Settlements `<= 10k`, Non-Capital — Deterministic WHG + GeoHack, `0` LLM Agents)**:
   - Written to `tests/toponymy_batches/<slug>/pass2/residuals.json`.
   - Resolved exclusively by `resolve_residual_toponymy_whg_geohack.js` (`max_workers <= 4`, persistent disk cache at `_shared/_gis_cache/whg_geohack_cache.json`, **0 LLM agents**) querying World Historical Gazetteer (WHG) + Wikipedia GeoSearch / GeoHack + Wikidata (`P1448`/`P580`) cross-referenced against Dataview `states.json` to infer the de facto ruling authority's preferred English-language Latin transliteration.
   - Emits `pass2/pass2_whg_geohack_report.json` (`llm_agents_used: 0`) verified by `audit_city_metadata.js`.

### 3 Structural Rules for Toponyms (Mandatory for Pass 1 & Pass 2)
1. **De Facto Occupying / Ruling Authority Rule (Latin Script)**: Always use the name preferred by the de facto ruling or occupying authority of the settlement at that date, rendered in the Latin script using the contemporaneous English-language transliteration for that time (e.g. `Keijo` under Japanese rule `1910–1945` -> `Seoul` `1945.8.15`; `Kiev` under Russian/Soviet rule -> `Kyiv` `1991.8.24`; `Constantinople` -> `Istanbul` `1930.3.28`; `Danzig` -> `Gdansk` `1945.3.30`; `Bombay` -> `Mumbai` `1995.11.4`; `Batavia` -> `Jakarta` `1942.12.8`; `Godthaab` -> `Nuuk` `1979.5.1`; `Edo` -> `Tokyo` `1868.9.3`; `Tenochtitlan` -> `Mexico City` `1521.8.13`). Canonical `.name` and `.historical_names` MUST be pure Latin script (zero Cyrillic/Arabic/Greek/CJK/Indic glyphs, zero backtick haceks `` ` ``, zero comma-inverted articles `Mans, Le`, zero parentheticals).
2. **Historical Period Accuracy Rule**: Use period-accurate historical names rather than retrofitting modern names into earlier centuries. Pre-colonial settlements carry their attested pre-colonial ruling-authority name prior to colonial founding or occupation.
3. **Capital City Precedence Rule**: Any settlement identified as a capital city (`00_capitals.json` / `"cap": true`) MUST ALWAYS carry the canonical contemporaneous name of that capital city across its entire timeline, even if an underlying census row, GHSL cluster, or sub-district feed reads a ward, quarter, or district label (e.g. `Paris 05 Panthéon`, `Al-Dawâwîn`, `Kepos`, `City of London`).

### Non-Destructive Full-History Simplification & Case-Insensitive Deduplication (`merge_city_metadata.js`, `partition_city_metadata.js`)
- **Full-History Simplification at `[lng, lat]`**: New merges NEVER blindly overwrite existing capital or major-city histories (`simplifyHistoryAtCoord()` merges ALL existing and incoming entries at `[lng, lat]`, strips intra-municipal sub-district labels, collapses same-date or consecutive case-insensitive/orthographic variant duplicates, preserves genuine historical renames, and locks Tier-0 capitals against Pass-2/sub-district overrides).
- **Case-Insensitive `.other_names` Deduplication**: `deduplicateOtherNamesCI()` (enforced in `merge_city_metadata.js`, `partition_city_metadata.js`, `ViscountGazetteerLoader.js`, `stadester_uud.js`, Dataview `city_metadata_framework.ts`/`stadester_types.ts`, and audited as `[FAIL]` in `audit_city_metadata.js`) drops every duplicate alias and any alias matching `.name` or `.historical_names` case-insensitively (preferring mixed-case / diacritic-rich spellings when collapsing duplicates).
- **Live Remediation**: `partition_city_metadata.js --clean-existing --all` (wrapped in `run_bounded.js --lock dataview_metadata`) validates `00_capitals.json` against `states.json` spatial bboxes + `state_capitals.json`, demotes cross-continent misbound homonyms, consolidates same-municipality split capitals `<= 3,0 km` (without merging distinct neighbouring municipalities), restores sub-district-overridden capitals, and removes all case-insensitive `.other_names` duplicates across every shard.
