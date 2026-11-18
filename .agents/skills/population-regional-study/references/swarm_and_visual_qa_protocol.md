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
   - Exclude non-local Cyrillic, Arabic, Indic, Thai or CJK `other_names` spam on cities in purely Latin-script jurisdictions across all `14` macro-regions (configured in [viscount_skill_profiles.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/config/viscount_skill_profiles.json5)), including US border towns below `32,4°N`, whilst preserving authentic Russian Chukotka Cyrillic records (`lng < -168,98, lat > 64,0`) as well as indigenous, multi-script and colonial exonyms in multi-script jurisdictions.
2. **Entity Identity Protection against Suburb, Annex & Intra-Project Self-Merges**:
   - Never rename an active modern primary city after a smaller merged/subordinate suburb or annexed municipality (`Pittsburgh -> Allegheny`, `Watsonville -> Pajaro`):
     - In `stadester_uud.js` (`initialiseUUD`), NEVER merge two distinct settlements already belonging to the same `viscount_project` (`ViscountGazetteerLoader` handles intra-project deduplication; cross-radius UUD merges would otherwise collapse neighbouring towns like `Provincetown -> Truro` across township aliases).
     - Harmonise `*-United States` `populstat` duplicates onto canonical `<Name>-<State>` keys (except `Washington-United States`).
     - Primary `.name` overwrites when stems differ require `<= 1,0 km` tolerance AND an explicitly corrupted source name.
     - Cross-language historical romanisation equivalences (`Peking <-> Beijing`, `Bombay <-> Mumbai`, `Constantinople <-> Istanbul`, `Oskemen <-> Ust-Kamenogorsk`, `Alluitsoq <-> Lichtenau`) are whitelisted in `viscount_skill_profiles.json5` so legitimate historical re-romanisations never trigger false hijack failures.
     - Terminal Modern Name Anchor (`>= 1950` / `>= 1995`): whenever an Indigenous settlement temporarily carried a colonial name (`Port Simpson` -> `Lax Kw'alaams`, `Friendly Cove` -> `Yuquot`, `Godthåb` -> `Nuuk`, `Barrow` -> `Utqiaġvik`), record the modern Indigenous restoration entry (`>= 1950` date) at the end of `historical_names` so Dataview's `stadester_metadata.ts` resolves the modern endonym cleanly without Signature B reversion. Preserve canonical base primary `.name` without `_viscount_regional`.
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
   - Call `read_file` on EVERY generated PNG inside `<domain_dir>/diagnostics_visual/` (both raw kriging sheets `01..05` and the compiled `06_velkscala_<project>_verification.png` composite once Stage E Velkscala completes).
   - Confirm visually:
     - Sharp fluvial corridors, valleys, coasts and elevation ridges matching `POLARIS` (`0` blurry Voronoi blobs or uniform "samey" carrying-capacity washout).
     - Genuine dasymetric suppression of uninhabitable deserts, high-alpine ridges, tundra and ice caps (`0` flat non-zero background floors).
     - Zero backprojection of modern `uopp_2023AD` / `GHSL_2020` metropolitan footprints or suburban rings in pre-industrial sheets, and zero unweighted county-centroid polka-dots or rectangular mosaic tiles.
     - Plain European human numerals (`0,01`, `1`, `10`, `100`, `1k`, `10k`) on all axes and colorbars (`0` `$10^k$` / `1e4` scientific notation on counts or densities).
     - Seamless cross-border continuity (`0` hard modern border cliffs).
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
2. **Figure-by-Figure Visual Confirmation, Repair Loop & Auditor Sign-Off (`figures/visual_check.json`)**:
   - Never treat `visual_check.json` as a script-generated formality or copy boilerplate notes across figures (`Gatekeeper D2` fails on duplicate or `< 50`-char notes).
   - Crop multi-panel figures into individual panels (`1A..nD`), inspect **every figure and cropped panel one by one** via `read_file`, and inspect compiled `.pdf` Page `1` (`abstract` continuity with Page 2 if pushed by the cover hero) and multi-page tables. If ANY defect is found (pixelated mask tiles, warped/overextended ocean frame, stale pre-revision boundaries, occluded callout/legend, label crossing outside a panel spine, serif override, raw ASCII math, an orphaned Page-1 `Abstract` heading stranded without prose, or `LMMono`/monospace typography outside code), **fix the script or `.Rmd` / LaTeX headroom, regenerate that figure/PDF and re-open it via `read_file` in a loop until spotless** before proceeding.
   - Verify optically on every panel:
     - **Mask & Vector Fidelity**: Smooth projected vector sub-region polygons (`0` pixelated `*_areal_mask.png` `imshow()` blocks except continuous kriging/`Velkscala` surfaces) matching current masks and `.naissance` borders.
     - **Unwarped Equal-Area Framing**: Crisp `set_aspect("equal")` shapes with dedicated side-panels or insets for distant islands/exclaves (`0` stretched coastlines or empty-ocean frames).
     - **Strict In-Panel Bounds & Zero Occlusion**: All callouts, bar-end values, axis labels and interior legends stay completely inside panel spines and canvas bounds (`0` overlapping text boxes or clipped labels).
     - **Default Matplotlib Theme & Typography**: `DejaVu Sans` sans-serif typography (`0` serif or `seaborn` overrides), intact 4-sided boxed spines, rendered MathText (`$\nu$`, `$\tau_1$`, `$R^2$`, `$\log_{10}$`, never raw `nu = 3/2`, `tau1=1,41`, or `Pseudo R-squared`) with European `{,}` decimals, comma axis ticks (`0,75`), plain human log ticks (`0,01..1k..1,5M`, never `$10^k$` or `1e4` scientific notation on counts, sites, inhabitants or densities), intact Roman numerals (`Pueblo III`, never `Pueblo Iii`), plain titles and informative non-degenerate plots.
     - **Geographic & Demographic Sense**: Sub-regions, rivers, cities, uninhabitable wasteland voids, suppressed modern urban footprints and trajectories make clear historical and cartographic sense to independent `@verifier` / auditor agents.
     - **PDF Page-1 Typesetting & Font Purity**: Confirm visually on compiled PDF pages that `# Abstract` is never orphaned at the bottom of Page `1` (move `Abstract` onto Page `2` together with its opening paragraph whenever Page `1` hero spacing is tight) and that `0` monospace (`LMMono`/typewriter) spans appear in captions, headings, prose or tables.
   - Recompile affected `.pdf` and Intellte `.md` outputs **after** final PNG fixes (`pdf.mtime >= fig.mtime >= mask.mtime`), then save `<chapter_dir>/figures/visual_check.json` and `<project_dir>/figures/visual_check.json` containing one dict per PNG with unique figure-specific `notes` (`>= 50` chars) and explicit `zero_occlusion_and_in_panel_bounds: true` plus `polaris_visual_parity: true` attestations (`manifest.mtime >= max(png.mtime)`):
     ```json
     {
       "approved": true,
       "verified_at_gmt0": "2026-11-18T07:30:00Z",
       "zero_occlusion_and_in_panel_bounds": true,
       "polaris_visual_parity": true,
       "figures": [
         {
           "file": "fig1_example_spatial.png",
           "zero_occlusion_and_in_panel_bounds": true,
           "polaris_visual_parity": true,
           "notes": "Inspected full panel and cropped inset: smooth vector sub-regions in Equal-Area Albers with mainland/island insets, 7 in-bounds callouts clear of river lines and legend."
         }
       ]
     }
     ```
3. **Note on Intellte Sync**:
   - `sync_viscount_region.js` skips `diagnostics_visual/` and Stage C intermediate grids during web sync so high-DPI inspection sheets remain local QA artefacts rather than bloating VitePress static assets.
