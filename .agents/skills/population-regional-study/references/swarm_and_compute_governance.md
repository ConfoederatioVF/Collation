# Swarm Governance, Incremental Cross-Repo CI/CD & Bounded Compute (`Gatekeeper S`)

---

## 1. Global Hard Subagent Cap (`n <= 24`), Programmatic ETL & Model Escalation

> [!IMPORTANT]
> **Hard Global Concurrency Cap (`n <= 24`)**: NEVER launch more than **`24` concurrent subagents** globally across any Operation Viscount workflow, toponymy swarm, evidence swarm, or geocoding pipeline. Algorithmic batch construction MUST size batches larger (`40–200` items/batch) or execute in sequential waves capped by a global `asyncio.Semaphore(24)` so `<= 24` agents run concurrently at all times.

- **Programmatic Node.js / Python ETL (Zero LLM Tokens, Wrapped via `run_bounded.js`, `max_workers <= 4`)**:
  - Census parsing, projection, **bulk geocoding** (use deterministic local gazetteers, WHG, GeoHack, Nominatim/Pelias with persistent disk caching — NEVER spawn LLM swarms for bulk geocoding), **Pass-2 residual toponymy** (`resolve_residual_toponymy_whg_geohack.js` for `<= 10k` non-capital settlements — **0 LLM agents**), deduplication, municipal-boundary consolidation, topology repair, Matérn kriging, 3-Phase metro reconciliation, Stadestér sharding, incremental Dataview cache warming, and Intellte dirty-file sync.
- **Bounded Swarm Work (Default `Gemini 3.8 Flash` -> Escalate In-Place to `Hydrogen`, Hard Global Cap `n <= 24`)**:
  - **Stage A Pass-1**: Preliminary HGIS EDA swarm (`<= 24` concurrent, fetching OHM + academic HGIS datasets).
  - **Stage A Pass-2 (`HARD CAP: MAX 2 SUBAGENTS`)**: Strictly `1` `mask_builder` + `1` separate read-only `mask_auditor` iterating over regional bbox crops. Never exceed `2` subagents in Pass-2.
  - **Stage C Evidence Assessment**: Read/write-only swarms (`<= 24` concurrent, `25–40` settlements/batch) + separate `@auditor` for non-tabular historical settlement evidence and Wave 2 archival PDF extraction.
  - **Stage D Writing & Visual QA**: `MAX 1 CHAPTER PAIR PER WORKER` (`<= 24` concurrent) read/edit-only prose + independent `@verifier` for cropped figure panels.
  - **Stage F Pass-1 Toponymy ONLY (`max_pop > 10k` or capital)**: Compact `{ coords: [lng, lat], names: { "yyyy.m.d": "Name" } }` adaptive batches (`40–200` cities/batch, `<= 24` batches/wave) across `Gemini 3.8 Flash` workers + strictly separate read-only `toponymy_auditor` sharing one global `asyncio.Semaphore(24)` and enforcing the **zero-tolerance single-error send-back rule** before merge. Never pass Pass-2 `residuals.json` to an LLM worker.
- **Model Escalation & Monitor**: Multi-worker swarms (`>= 3` workers) include a `monitor` (`swarm_monitor`). If a `Gemini 3.8 Flash` worker stalls, hits quota, or fails auditor checks twice, switch it **in place** via `swarm{action: "model", name: "<worker>", model: "Hydrogen"}` — never `kill` and `add` solely to swap models.
- **Browser Challenges**: On JS rendering or DDoS-Guard challenges, switch immediately to Puppeteer/Selenium inside `try ... finally` (`<= 2` concurrent browsers, `25–30s` challenge wait). Refer hard `"Verify you are human"` CAPTCHAs to the human user in non-headless mode; never attempt automated bypasses.

---

## 2. Incremental CI/CD Sync Law (Dataview & Intellte)

Treat both downstream repositories as incremental CI/CD targets — modifying one macro-region MUST NEVER rebuild or dirty unmodified sibling namespaces:
- **Dataview (`stadester_2.0`)**:
  - Regional city data (`<prefix>_*.json`) and regional spatial-overlay metadata (`city_metadata/<region>.json` + `00_capitals.json`) map 1-to-1 to per-shard disk caches under `data/stadester/cache/stadester_2.0/shards/` tracked by `cache_manifest.json` (`{ shard_sig, region_metadata_sig, region_capitals_sig, ghsl_sig }`).
  - Always invoke targeted incremental warming (`--only-project=<KEY>`): unmodified regions (e.g. `CENTAUR` when updating `MAGNETIC`) incur `0` re-parses, `0` re-writes, and `0` git churn. NEVER delete global caches wholesale.
- **Intellte (`Project 1746`)**:
  - `sync_viscount_region.js --project=<KEY> --build` diffs files by SHA-256 strictly inside `papers/viscount/project_<slug>/`, skips `diagnostics_visual/` and Stage B intermediate rasters, enforces repo-relative paths `<= 180` chars, and compiles `rmd_dom` LF caches only for modified chapters (`only_concept_id`).

---

## 3. Bounded Compute & Single-Source Mutex Law (`run_bounded.js` & `Gatekeeper S`)

Execute all heavy/background jobs through [run_bounded.js](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/scripts/run_bounded.js) (reading [geopng_compute.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/common/defines/geopng_compute.json5)):
1. **Win32 Job Object (`koffi` FFI)**: `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` + `BELOW_NORMAL_PRIORITY_CLASS` guarantees atomic teardown of child/grandchild trees (`node.exe`, `python.exe`, `chrome.exe`, `Rscript.exe`, `xelatex.exe`).
2. **Thread & Heap Caps**: Injects `OMP/OPENBLAS/MKL/NUMEXPR/VECLIB/BLIS/UV_THREADPOOL_SIZE = 4` and `NODE_OPTIONS=--max-old-space-size=6144` (`--max-ram-mb <= 8192`), with RAM (`1,15x`) and wall-clock watchdogs.
3. **Single-Source Mutexes (`histmap/.locks/<name>.lock`, atomic `O_EXCL` + dead-PID liveness check)**:
   - `stadester_velkscala` (`1` runner): `population_Stadester.js`, `population_Stadester_transform.js`, `population_Velkscala.js`, `ViscountSubstrataMosaic`.
   - `dataview_metadata` (`1` runner): `merge_city_metadata.js`, `partition_city_metadata.js`, `verify_downstream_ci_cd.js`, Dataview cache warming & builds.
   - `gpu_compute` (`1` runner): OpenCL/CUDA kriging (`frame_budget_ms: 6`, `max_vram_mb: 2048`).
4. **Ad-Hoc Script Hygiene (`Gatekeeper S` — Enforced Statically by `audit_shell_and_scripts.js`)**:
   - Clamp local worker pools `<= 4`, concurrent `Rscript`/`xelatex` builds `<= 2` (never 2 in the same directory), headless browsers `<= 2` inside `try ... finally`, and `0` detached processes.
   - Hard `[FAIL]` on any uncapped `parallel()`/`asyncio.gather()` over `agent()`/LLM calls without a global `Semaphore(<= 24)` or `<= 24` wave cap, any concurrency literal `> 24`, or any script spawning LLM agents on Pass-2 `residuals.json` or bulk geocoding.
   - Verify with:
     ```powershell
     node .agents/skills/population-regional-study/scripts/audit_shell_and_scripts.js histmap/1.data_raw/population_regional/<PROJECT_KEY>
     node .agents/skills/population-regional-study/scripts/run_bounded.js --audit-orphans
     ```
