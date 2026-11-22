# Census, Gazetteer & Multi-Repository Archaeological Ingestion

## 1. Anti-Stub Guardrails vs Maximum Saturation Mandate

Minimum quantitative thresholds enforced by `verify_gazetteer_exhaustiveness.py`, `audit_kriging_sharpness.py`, and `audit_rmd_and_bib_calibre.py` are **strictly anti-stub guardrails**. They MUST NEVER be treated as stopping quotas, target counts, or completion criteria:

- Minimum `>= 35` deduplicated settlements per spatiotemporal mask, `>= 2,5x` SVEA's global `c14_cleaned_dedup.csv` density in kriging domains, `>= 15` valid `%PDF-` files (`> 10,24 kB`) in `./papers/`, `>= 20` unique `.bib` keys, and `>= 350` lines (`>= 2.500` words) in each literature review reject empty/truncated stubs.
- **True Stop-Hook Condition**: Every known settlement and primary-source archaeological site inside the spatiotemporal region must be **exhaustively enumerated** across primary census schedules, historical cadastres, archaeological registries, and `./papers/` monographs until additional pass sweeps yield diminishing returns.

---

## 2. Iterative 4-Wave Asymptotic Maximum-Saturation Loop

Execute settlement and archaeological discovery as an explicit converging pipeline rather than a single-pass top-N sample:

1. **Wave 1 — Per-Jurisdiction Full-Frame Multilingual Portal Ingestion (Zero Global-Only Scraping)**:
   - **Per-Jurisdiction Scraping Mandate**: Iterate explicitly over **every sovereign country and distinct historical/island jurisdiction** listed for the macro-region in `jurisdiction_source_matrix` ([viscount_skill_profiles.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/config/viscount_skill_profiles.json5)) — e.g. Japan mainland, Hokkaido (Ezo), Ryukyu, South Korea AND North Korea (incl. Eastern provinces) in `CASTLE`; every sovereign state in `MANDALA` (incl. Laos, Cambodia, Myanmar, Timor-Leste, Brunei); all five republics in `SARAY`. Stopping at global databases (`Wikidata`, `OSM`, `Overpass`, `GeoNames`, `p3k14c`, `c14bazAAR`, `Zenodo`) or allowing a well-scraped country to mask an unscraped neighbour is an unconditional `[FAIL]` in Gatekeepers `A` and `C1`.
   - Ingest every row (zero `LIMIT`, `head`, or `slice` caps) of official decennial/quinquennial censuses, dynastic/fiscal/colonial cadastres, national gazetteers and multi-repository archaeological databases, matching census polygon centroids to settlement halls up to `55 km` across all statistical tiers.
   - Clean bureaucratic suffixes (`(CDP)`, `(balance)`, consolidated county tags, raw `-shi`/`-gun`/`-ken`/`Prefecture`/`District`/`Kabupaten`/`Amphoe` administrative suffixes and raw `AFB` abbreviations) and exclude non-settlement religious/monumental entries (`Wat ...`, `Candi ...`, `Prasat ...`, temples, shrines, pagodas, tombs, monasteries) from urban settlement gazetteers whilst promoting attested Indigenous endonyms as primary display names.
   - **Ban Wikipedia Archaeological Scraping**: Never construct archaeological site corpora by scraping Wikipedia categories or lists. Conduct iterative local-language `search_web` discovery across all indigenous, historical-imperial, colonial and modern administrative languages of every constituent jurisdiction targeting national monument registries, ministries of culture, academies of sciences and open-data GIS portals (`DINAA`/`tDAR`/`CARD`, `IPHAN`/`CNSA`, `INAH`, `SIGDA`, `CHGIS`, `ASI`, `NABUNKEN`, `bunkacho`, `cha.go.kr`, `KCHGIS`, `EFEO`, `FAD`, `Kemendikbud`, `CAAL`, `ARIADNEplus`/`ADS`, `EAMENA`/`MEGA`, `AustArch`, `OSAAR`/`SAHRIS`).
   - **Upstream API Forensics**: Audit every scraped API or catalogue for `NULL`/undated record leakage into period-filtered queries (bypass via leaf record inspection), administrative centroid snapping / coordinate fuzzing, monument-complex vs sub-feature double counting, and overlapping local periodisations (folding `< 25`-site transitional slices into adjacent horizons).
   - Register every harvested raw settlement or site AND a complete `jurisdiction_coverage` map in `<stem>_source_ledger.json5` (with primary census/cadastre sources, archived demographic literature, row counts and `crowd_fallback_share <= 0,20` per jurisdiction) BEFORE inclusion/exclusion filtering.
   - Archaeological domains MUST composite multiple regional/national heritage registries per jurisdiction (`>= 2,5x` `c14_cleaned_dedup.csv` baseline floor, `>= 50%` primary national/regional registers + monograph tables, `<= 25%` `Wikidata`/`OSM`/`Overpass` crowd share both domain-wide and per jurisdiction).

2. **Wave 2 — 100% Per-Jurisdiction Archival PDF & Monograph Extraction (`./papers/`) & Bibliography Diversity**:
   - Download `>= 15` SHA-256-unique primary monographs, statistical abstracts, archaeological catalogues and fiscal/colonial cadastres per sub-chapter into `./papers/`, ensuring **every constituent country/jurisdiction** in the macro-region has dedicated historical population/demography literature archived and cited (validating `> 10,24 kB` and leading `%PDF-` magic bytes; Puppeteer/Selenium inside `try...finally` via `run_bounded.py` with `25–30s` wait on JS challenges).
   - **Source Diversity Caps (`Gatekeeper D2`)**: Zenodo (`zenodo.org` / `10.5281/zenodo`) is capped at **`<= 15%` per chapter `.bib`** and **`<= 10%` project-wide**; Wikidata/OSM/GeoNames at **`<= 10%`**; every chapter `.bib` MUST cite **`>= 5` distinct scholarly publishers/journals/domains** with **`>= 85%` per-chapter / `>= 90%` project-wide** verifiable `doi` or `https://` `url` fields. Sanitise harvested HTML tags (`<i>`, `<em>`, `<sup>`) into LaTeX (`\textit{}`, `\textsuperscript{}`).
   - Extract all historical population tables, settlement appendices, tax-hearth/household/hut-tax/padrones/revision/parish registers and gazetteer footnotes from `./papers/`. Do not sample only the largest towns.

3. **Wave 3 — Longitudinal Pre-Census Backfill, `foundation_year` & Modern Continuity**:
   - Pair every settlement active into the statistical era with its earlier censuses, dynastic/colonial/fiscal cadastres and documented `foundation_year` (`found.yr`) metadata (`0` `year < foundation_year` anachronisms). Explicitly set `foundation_year` on 20th-century military installations (`Loring Air Force Base`, `Moody Air Force Base`, Cold War bases) and atomic/company towns (`Oak Ridge`, `Los Alamos`) so synthetic `1850` back-projection never invents pre-foundation populations.
   - Separate pre-consolidation independent municipalities with authentic cutoffs and `0` post-annexation ghost counts (e.g. independent `Brooklyn` `<= 1897` anchored separately from Manhattan `New York`; `Allegheny` `<= 1907` separate from `Pittsburgh`).
   - `verify_gazetteer_exhaustiveness.py --mode=compiled` and `Gatekeeper F` enforce:
     - `post_1995_only_ratio <= 0,45` across settlements active since `1950`, plus adjacent decennial jump `<= 3,0x`.
     - Annual `getCitiesAtYear` step `<= 3,0%` across the region's configured `[t_modern_census, 2025]` span outside declared `border_splice_years` (e.g. `1790`/`1850` in `CENTAUR`, `1872` in `PRETA`, `1897` in `POLARIS`/`SARAY`, `1920` in `CASTLE`, `1953` in `JADE`, `1960` in `NICETHI`/`MANDALA`).
     - `0` unsplit compound `"A & B"` modern municipalities (archaeological type-sites matching `arch_site_qualifiers` exempt), `0` `(agglomeration)` twin ghosts and `0` same-country active pairs `<= 1,5 km` in modern census years.
   - Where historical population rows are missing, dispatch `Gemini 3.8 Flash` (`Hydrogen` in-place fallback) swarm batches paired with a read-only `@verifier` and `monitor`.

4. **Wave 4+ — Sub-Region × Era Gap-Hunter Loops, Variant-Duplicate Scrubbing & Homonym Purge**:
   - Cross-tabulate active settlements against every RGB sub-region in `*_areal_mask.png` and every constituent jurisdiction across historical (`<= 1900`) and modern eras; work until **zero** inhabited sub-regions sit empty or chronically sparse (`[SUBREGION_GAP]` / `[SUBREGION_ERA_GAP]`) and `0` all-era variant-spelling duplicates (`<= 25 km`, e.g. `Samarqand` vs `Samarkand`) or suspicious temple/monument/admin names remain.
   - Cross-audit high-collision colonial and Classical city names against `GeoNames` + `Wikidata` (`P1566`/`P571`/`P1082`) to purge out-of-domain metropolis homonym hijacks (`--geonames-audit`).
   - Re-run gap-hunter passes until `marginal_gain_pct <= 2,0%` AND `unaccounted_ledger_candidates == 0` in `verify_gazetteer_exhaustiveness.py --require-sources --require-saturation --audit-temporal-density --audit-spatial-bounds --ledger <ledger>`.
   - Record convergence telemetry (`wave_1_count`, `wave_2_count`, `wave_3_backfill`, `final_unique_count`, `marginal_gain_pct`, `jurisdiction_coverage`) in `<stem>_source_ledger.json5` and summarise inside `# Methodology`.

---

## 3. Explicit Data Shortcuts, Circularity & Provenance Bans

The following shortcuts trigger an unconditional `[FAIL]` in Gatekeepers `A` (`verify_gazetteer_exhaustiveness.py`), `C1` (`audit_kriging_sharpness.py`), `D1` (`audit_academic_prose.py`) and `D2` (`audit_rmd_and_bib_calibre.py`):

- **Anti-Circularity Firewall**: Sub-chapter researchers MUST NOT read, import or cite SVEA's own on-disk demographic tables (`population_Substrata*`, `population_Velkscala`, `population_Stadester`, internal workspace `histmap/` paths or `saves/atlas_defacto.naissance` population figures; `.naissance` files may only inform historical polity boundary polygons).
- **Top-N city compendia**: Using Census Gibson `twps0027`, `top_100_cities`, SQL `LIMIT <= 250` or hard `max_settlements <= 250` caps.
- **Global fallback disaggregation in sub-chapters**: Using or citing `@McEvedy`, `@KleinGoldewijk` (HYDE), `Populstat`, `Chandler 1987`, `Modelski 2003` or `Maddison` to backfill or disaggregate sub-chapter settlements or populations.
- **Placeholder exclusion padding**: Excluding settlements with generic dummy reasons; every excluded candidate must carry a valid taxonomic reason.
- **Overwriting legacy ethnographic substrata**: NEVER modify legacy `population_Substrata.*` priors under `histmap/3.data_transform/`.

---

## 4. Sovereign Polygon Bounds, Island/Archipelago Buffers & Precedence Hygiene

- Verify every settlement's `[lat, lon]` coordinates lie inside its sovereign country/state/territory polygon resolved dynamically across all `14` regions via [viscount_skill_profiles.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/config/viscount_skill_profiles.json5) + `ne_10m_admin_0_countries.geojson` (`0,28 deg` continental buffer; `0,65 deg` when `has_micro_islands: true` covers Oceania, Caribbean, Insular SE Asia, Maldives, Indian/South Atlantic or Arctic islands) plus regional domain masks.
- Respect canonical inverse z-index precedence in [viscount_precedence.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5) (`NICETHI = 14` down to `CENTAUR = 1`) and preserve clean primary canonical `.name` / `.coords` with `0` `_viscount_regional` key suffixes.
