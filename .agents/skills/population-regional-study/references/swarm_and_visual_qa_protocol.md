# Swarm Orchestration, Historical Toponymy & Mandatory Visual QA Protocol

## 1. Programmatic ETL vs Swarm Delegation Boundary

Never waste LLM tokens on bulk deterministic parsing, and never skip human-knowledge disambiguation where historical toponymy requires scholarly judgement:

- **Programmatic Node.js / Python ETL (No LLM Swarm)**:
  - Census CSV/DBF/Parquet parsing, coordinate projection, Gazetteer deduplication, Matérn kriging (`ViscountMaternKriging.js` + `ViscountResidualCovariates.js`), Stadestér shard partitioning, Dataview cache warming and VitePress/Intellte incremental syncing.
- **Swarm Work (Default `Gemini 3.8 Flash` -> Escalate to `Hydrogen`)**:
  - Literature PDF discovery & archival table extraction (`./papers/`).
  - Pre-census historical census backfill (`Wave 3`) & `foundation_year` recovery in manageable `25–40` settlement batches, always accompanied by a read-only `@verifier` worker + `monitor`.
  - Authoring paired `<stem>_settlements.Rmd` and `<stem>_literature_review.Rmd` (or `*_areal_masks_and_bins.Rmd`) files (strictly `MAX 1 CHAPTER PAIR PER WORKER`).
  - Dedicated **Read/Edit-Only Editorial Pass** (`read_file` + `edit_file` only; zero regex prose-rewriting scripts) enforcing McEvedy & Jones (sub-chapters) and Klein Goldewijk (root synthesis).
  - Stage F historical toponym & `city_metadata.json` enrichment via batched knowledge-base workers (`30` cities per batch) + `@verifier`.

---

## 2. Model Selection, `@verifier` + `monitor` Topology & In-Place Escalation

1. **Default Worker Model**: Spawn all swarm workers (`swarm{action: "add", model: "Gemini 3.8 Flash", ...}`) on **`Gemini 3.8 Flash`**.
2. **Mandatory `@verifier` + `monitor` on Multi-Worker Swarms**: Every multi-slice data/toponymy swarm (`>= 3` workers) MUST include an independent read-only `@verifier` auditing primary source/year bounds prior to merge and a `monitor` (`swarm_monitor` skill) to detect and unstick stalls automatically.
3. **In-Place Fallback (`Hydrogen`) & Stalled-Worker Handoff**: If a `Gemini 3.8 Flash` worker hits quota/capacity limits, emits repeated syntax/citation defects or stalls, **switch it in place** via `swarm{action: "model", name: "<worker>", model: "Hydrogen"}` — never `kill` and `add` simply to change models. If a subagent remains unrecoverable, kill, inspect partial outputs on disk, and dispatch a focused handoff prompt.
4. **Scope Cap per Worker**:
   - Assign **at most 1 chapter pair** per writing worker.
   - Assign **`25–40` settlements per batch** for pre-census historical backfill workers.
   - Assign **`30` cities per batch** for Stage F historical metadata enrichment (`run_historical_names_swarm.py`).
5. **Coordinator Overlay Send-Back Loop (`Gatekeeper A2`)**: Render `verify_<stem>_overlay.png` via `audit_areal_masks.py --render-overlays`, inspect every overlay PNG with `read_file`, and send back any mask showing rectangular cuts, modern border clips, starved sub-regions or stranded sites *before* running Stage C kriging or writing regional text.

---

## 3. Archival PDF Retrieval & Browser Anti-Bot Compliance

- Download full-text scholarly papers, archaeological monographs and official census publications into each sub-chapter's `./papers/` directory (`>= 15` valid `%PDF-` files exceeding `10,24 kB`; zero stub HTML redirects).
- **Mandatory JS / DDoS-Guard Rule**: Whenever a scholarly archive or statistical portal requires JavaScript rendering or encounters a DDoS-Guard / browser challenge, switch immediately to **Puppeteer/Selenium** (`25–30s` wait for challenge resolution).
- If a hard `"Verify you are human"` / CAPTCHA gate blocks all alternative open mirrors, pause and refer it to the human user in non-headless mode; NEVER attempt automated CAPTCHA bypasses.

---

## 4. Stage F: Historical Names Enrichment & Entity Identity Protection

Before mutating `Dataview/data/stadester/stadester_2.0/city_metadata.json` (remember `stadester_1.0` and `stadester_1.1` keep their own isolated `city_metadata.json`!):

1. **Foreign-Script Spam Guard (`merge_city_metadata.js` & `viscount_skill_profiles.json5`)**:
   - Exclude non-local Cyrillic, Arabic, Indic, Thai or CJK `other_names` spam on cities in purely Latin-script jurisdictions across all `14` macro-regions (configured in [viscount_skill_profiles.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/config/viscount_skill_profiles.json5)), whilst preserving authentic indigenous, multi-script and colonial exonyms where jurisdictions are multi-script.
2. **Entity Identity Protection against Suburb & Annex Hijacks**:
   - Never rename an active modern primary city after a smaller merged/subordinate suburb or annexed municipality (`Pittsburgh -> Allegheny`, `Watsonville -> Pajaro`):
     - Primary `.name` overwrites when stems differ require `<= 1,0 km` tolerance AND an explicitly corrupted source name.
     - Cross-language historical romanisation equivalences (`Peking <-> Beijing`, `Bombay <-> Mumbai`, `Constantinople <-> Istanbul`, `Oskemen <-> Ust-Kamenogorsk`) are whitelisted in `viscount_skill_profiles.json5` so legitimate historical re-romanisations never trigger false hijack failures.
     - Terminal Modern Name Anchor (`>= 1950` / `>= 1995`): preserve the canonical base primary `.name` rather than retrofitting a merged locality name or appending `_viscount_regional`.
3. **Post-Index Integrity & Annual Continuity Check (`Gatekeeper F`)**:
   - `verify_downstream_ci_cd.js --project=<KEY>` inspects both `stadester_2.0_indexed.json` AND annual `getCitiesAtYear(yr)` coverage across the region's `annual_continuity_span` (`<= 3,0%` YoY step outside `border_splice_years`), verifying:
     - `0` `_viscount_regional` keys and `0` orphaned explicitly-tagged `city_metadata.json` records.
     - `0` foreign-script `other_names` spam entries in Latin-script-only countries across all `14` macro-regions.
     - `0` Signature A (`>= 1995` suburb hijack) or Signature B (`< 1920` defunct annex hijack on `>= 1950` active cities) regressions.

---

## 5. Mandatory Optical Inspection (`read_file`) & Signed Manifests

Quantitative CSV/JSON metrics alone cannot confirm cartographic quality or PDF layout hygiene. Agents MUST inspect rendered visual outputs directly via `read_file`:

1. **Kriging & Population Surface Verification (`Gatekeeper C3`)**:
   - Run `python .agents/skills/population-regional-study/scripts/render_and_audit_kriging_visuals.py <domain_dir> --render-only`.
   - Call `read_file` on EVERY generated PNG inside `<domain_dir>/diagnostics_visual/`.
   - Confirm visually:
     - Sharp fluvial corridors, valleys, coasts and elevation ridges (zero blurry Voronoi blobs).
     - Seamless cross-border continuity (zero hard modern border cliffs or rectangular mosaic tiles).
   - Write `<domain_dir>/config/visual_verification_manifest.json` after reading the PNGs:
     ```json
     {
       "verified_by": "population-regional-study",
       "verified_at_utc": "2026-11-17T20:00:00Z",
       "inspected_sheets": [
         {
           "file": "kriged_periods_overview.png",
           "inspected_via_read_file": true,
           "river_coastal_alignment_verified": true,
           "zero_isotropic_voronoi_blobs": true,
           "zero_modern_border_cliffs": true,
           "cartographic_notes": ">= 80 chars describing concrete fluvial ridges, catchment density and border continuity observed in panels A-D."
         }
       ]
     }
     ```
   - Re-run `render_and_audit_kriging_visuals.py <domain_dir>` (without `--render-only`) to pass Gatekeeper C3.
2. **Chapter Figure & Panel-by-Panel Inspection (`figures/visual_check.json`)**:
   - Crop multi-panel figures into individual panels (`1A..nD`), inspect **every panel** and single PNG in `<chapter_dir>/figures/` via `read_file`, and inspect compiled `.pdf` Page `1` and multi-page tables.
   - Verify optically on every panel:
     - Default Matplotlib theme: `DejaVu Sans` sans-serif typography (`0` serif or custom theme overrides) and intact 4-sided boxed spines on Cartesian plots.
     - Properly typeset MathText (`$\nu$`, `$\tau_1$`, `$R^2$`, `$\log_{10}$`, never raw ASCII `nu = 3/2`, `tau1=1,41`, or `Pseudo R-squared`) with European `{,}` decimals.
     - European decimal comma axis ticks (`0,75`, never `0.75`), intact Roman numerals and acronyms (`Pueblo III`, `SSR`, never `Pueblo Iii` or `Ssr`), plain titles (zero technobabble) and informative data series (never degenerate flat `0,998` bar charts).
     - Uncrossed `zorder=6/10` callouts, top colorbar titles, `vmax` ceiling match and `Stadestér` diacritic.
   - Save `<chapter_dir>/figures/visual_check.json` recording all inspected filenames/panels AFTER final PNG generation (`visual_check.json` `mtime >= max(png.mtime)`).
3. **Note on Intellte Sync**:
   - `sync_viscount_region.js` skips `diagnostics_visual/` and Stage C intermediate grids during web sync so high-DPI inspection sheets remain local QA artefacts rather than bloating VitePress static assets.
