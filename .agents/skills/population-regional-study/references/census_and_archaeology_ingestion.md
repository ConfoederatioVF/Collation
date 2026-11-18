# Census, Gazetteer & Multi-Repository Archaeological Ingestion

## 1. Anti-Stub Guardrails vs Maximum Saturation Mandate

Minimum quantitative thresholds enforced by `verify_gazetteer_exhaustiveness.py`, `audit_kriging_sharpness.py`, and `audit_rmd_and_bib_calibre.py` are **strictly anti-stub guardrails**. They MUST NEVER be treated as stopping quotas, target counts, or completion criteria:

- Minimum `>= 35` deduplicated settlements per spatiotemporal mask, `>= 2,5x` SVEA's global `c14_cleaned_dedup.csv` density in kriging domains, `>= 15` valid `%PDF-` files (`> 10,24 kB`) in `./papers/`, `>= 20` unique `.bib` keys, and `>= 350` lines (`>= 2.500` words) in each literature review reject empty/truncated stubs.
- **True Stop-Hook Condition**: Every known settlement and primary-source archaeological site inside the spatiotemporal region must be **exhaustively enumerated** across primary census schedules, historical cadastres, archaeological registries, and `./papers/` monographs until additional pass sweeps yield diminishing returns.

---

## 2. Iterative 4-Wave Asymptotic Maximum-Saturation Loop

Execute settlement and archaeological discovery as an explicit converging pipeline rather than a single-pass top-N sample:

1. **Wave 1 — 100% Full-Frame Multilingual Portal Ingestion (Zero Wikipedia Site-Scraping)**:
   - Ingest every row (zero `LIMIT`, `head`, or `slice` caps) of official decennial/quinquennial censuses, dynastic/fiscal/colonial cadastres, national gazetteers and multi-repository archaeological databases, matching census polygon centroids to settlement halls up to `55 km` across all statistical tiers.
   - Clean bureaucratic suffixes (`(CDP)`, `(balance)`, consolidated county tags such as `-Clarke County` / `-Richmond County`, numbered Indian Reserves and raw `AFB` abbreviations -> `Air Force Base` / civilian town name) whilst promoting attested Indigenous endonyms as primary display names (`Maaqtusiis`, `Utqiaġvik`, `Alluitsoq`, `Lax Kw'alaams`, `Yuquot`).
   - **Ban Wikipedia Archaeological Scraping**: Never construct archaeological site corpora by scraping Wikipedia categories or lists. Conduct iterative local-language `search_web` discovery across all indigenous, historical-imperial, colonial and modern administrative languages of the macro-region targeting national monument registries, ministries of culture, open-data ArcGIS FeatureServers and regional digital-humanities portals (e.g. `DINAA`/`tDAR`/`CARD`/`p3k14c`/`c14bazAAR`, `IPHAN`/`CNSA`, `INAH`, `SIGDA`, `CHGIS`, `ASI`, `NABUNKEN`, `EFEO`, `ARIADNEplus`/`ADS`/`XRONOS`, `EAMENA`/`MEGA`, `AustArch`, `OSAAR`/`SAHRIS` and state heritage registries). Single-source `p3k14c` extracts are unacceptable wherever national/regional site inventories exist.
   - **Upstream API Forensics**: Audit every scraped API or catalogue for `NULL`/undated record leakage into period-filtered queries (bypass via leaf record inspection), administrative centroid snapping / coordinate fuzzing, monument-complex vs sub-feature double counting, and overlapping local periodisations (folding `< 25`-site transitional slices into adjacent horizons).
   - Register every harvested raw settlement or site in the regional `<stem>_source_ledger.json5` (with source URL, access method, row count and bounding mask) BEFORE inclusion/exclusion filtering.
   - Archaeological domains MUST composite multiple regional/national heritage registries (`>= 2,5x` `c14_cleaned_dedup.csv` sites inside the domain mask — for reference, `POLARIS` achieves `81,8x` and `114,3x` across Eurasia and `CENTAUR-II` achieves `14,12x` across Northern America with `93.358` continental site-periods plus `6.979` Polynesian *ahupua'a* site-epochs).

2. **Wave 2 — 100% Archival PDF & Monograph Extraction (`./papers/`) & DOI/URL Provenance**:
   - Download `>= 15` primary monographs, statistical abstracts, archaeological catalogues and fiscal/colonial cadastres per sub-chapter into `./papers/`. Validate every download (`> 10,24 kB` and leading `%PDF-` magic bytes; Puppeteer/Selenium `25–30s` wait on JS challenges; open-access `PLOS`/Crossref APIs and permitted shadow libraries ensure permanent offline archival).
   - Enrich `.bib` entries with verifiable `doi` or external `https://` `url` fields (`>= 85%` per chapter, `>= 90%` project-wide) and sanitise any harvested HTML tags (`<i>`, `<em>`, `<sup>`) into proper LaTeX (`\textit{}`, `\textsuperscript{}`).
   - Extract all historical population tables, settlement appendices, tax-hearth/household/hut-tax/padrones/revision/parish registers and gazetteer footnotes from `./papers/`. Do not sample only the largest towns.

3. **Wave 3 — Longitudinal Pre-Census Backfill, `foundation_year` & Modern Continuity**:
   - Pair every settlement active into the statistical era with its earlier censuses, dynastic/colonial/fiscal cadastres and documented `foundation_year` (`found.yr`) metadata (`0` `year < foundation_year` anachronisms). Explicitly set `foundation_year` on 20th-century military installations (`Loring Air Force Base`, `Moody Air Force Base`, Cold War bases) and atomic/company towns (`Oak Ridge`, `Los Alamos`) so synthetic `1850` back-projection never invents pre-foundation populations.
   - Separate pre-consolidation independent municipalities with authentic cutoffs and `0` post-annexation ghost counts (e.g. independent `Brooklyn` `<= 1897` anchored separately from Manhattan `New York`; `Allegheny` `<= 1907` separate from `Pittsburgh`).
   - `verify_gazetteer_exhaustiveness.py --mode=compiled` and `Gatekeeper F` enforce:
     - `post_1995_only_ratio <= 0,45` across settlements active since `1950`, plus adjacent decennial jump `<= 3,0x`.
     - Annual `getCitiesAtYear` step `<= 3,0%` across the region's configured `[t_modern_census, 2025]` span outside declared `border_splice_years` (e.g. `1790`/`1850` in `CENTAUR`, `1872` in `PRETA`, `1897` in `POLARIS`/`SARAY`, `1920` in `CASTLE`, `1953` in `JADE`, `1960` in `NICETHI`/`MANDALA`).
     - `0` unsplit compound `"A & B"` modern municipalities (archaeological type-sites matching `arch_site_qualifiers` exempt), `0` `(agglomeration)` twin ghosts and `0` same-country active pairs `<= 1,5 km` in modern census years.
   - Where historical population rows are missing, dispatch `Gemini 3.8 Flash` (`Hydrogen` in-place fallback) swarm batches paired with a read-only `@verifier` and `monitor`.

4. **Wave 4+ — Sub-Mask Gap-Hunter Saturation Loops & GeoNames/Wikidata Homonym Purge**:
   - Partition each region by sub-mask / district / watershed and audit spatial gaps against official municipal lists, historic seats, missions, trading posts and mining settlements; cross-audit high-collision colonial and Classical city names against `GeoNames` + `Wikidata` (`P1566`/`P571`/`P1082`) to purge out-of-domain metropolis homonym hijacks (`--geonames-audit`).
   - Re-run gap-hunter passes until `marginal_gain_pct <= 2,0%` AND `unaccounted_ledger_candidates == 0` in `verify_gazetteer_exhaustiveness.py`.
   - Record convergence telemetry (`wave_1_count`, `wave_2_count`, `wave_3_backfill`, `final_unique_count`, `marginal_gain_pct`) in `<stem>_source_ledger.json5` and summarise inside `# Methodology`.

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
