# Shell, Resource & Concurrency Governance (`Gatekeeper S`)

Agents frequently author ad-hoc Python/Node.js ETL, scraping, kriging, figure-generation and RMarkdown compilation tasks in-situ. Unbounded ad-hoc scripts bypass SVEA's engineered limits in [geopng_compute.json5](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/common/defines/geopng_compute.json5) and cause workstation lag, VRAM/RAM exhaustion, orphaned background processes or concurrent Stadestér/Velkscala corruption.

---

## 1. Mandatory Bounded Launcher (`run_bounded.py`)

Every heavy or background shell invocation (scraping, census ETL, kriging, figure batch rendering, `Rscript.exe` compilation, `population_Stadester.js`, `population_Velkscala.js`, `merge_city_metadata.js`, `verify_downstream_ci_cd.js`) MUST be executed through [run_bounded.py](file:///F:/Active%20Projects/Project%201509%20-%20SVEA/.agents/skills/population-regional-study/scripts/run_bounded.py):

```powershell
python .agents/skills/population-regional-study/scripts/run_bounded.py --project <KEY> --lock stadester_velkscala -- node histmap/2.data_cleaning/population_Stadester/population_Stadester.js
```

`run_bounded.py` reads `common/defines/geopng_compute.json5` dynamically and enforces:
1. **Win32 Job Object (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`)**: Guarantees atomic termination of every child and grandchild process (`python.exe`, `node.exe`, `chrome.exe`, `chromedriver.exe`, `Rscript.exe`, `xelatex.exe`) when a command finishes, times out or is killed via `manage_task`.
2. **Below-Normal Scheduling Priority (`BELOW_NORMAL_PRIORITY_CLASS`)**: Keeps desktop/DWM/IDE interactive during heavy compute.
3. **Thread & Heap Ceilings**: Injects `OMP_NUM_THREADS=4`, `OPENBLAS_NUM_THREADS=4`, `MKL_NUM_THREADS=4`, `NUMEXPR_MAX_THREADS=4`, `VECLIB_MAXIMUM_THREADS=4`, `BLIS_NUM_THREADS=4`, `UV_THREADPOOL_SIZE=4` and `NODE_OPTIONS=--max-old-space-size=6144` (explicit `--max-ram-mb` override clamped `<= 8192`).
4. **Working-Set RAM & Wall-Clock Watchdog**: Terminates leaking scripts exceeding `1,15x` the RAM cap or `--timeout` before host OOM occurs.

---

## 2. Single-Source Pipeline Mutex Law (Zero Concurrent Stadestér/Velkscala Races)

All exclusive pipeline locks live in **one single place** — `run_bounded.py` writing atomic `O_EXCL` lockfiles under `histmap/.locks/<name>.lock` (with dead-PID liveness verification so crashed runs never leave permanent stale locks). Never add duplicate lock layers inside downstream scripts.

| Mutex Name (`--lock`) | Protected Global Resource | Max Concurrent Runners |
| :--- | :--- | :---: |
| `stadester_velkscala` | `population_Stadester.js`, `population_Stadester_transform.js`, `population_Velkscala.js`, `ViscountSubstrataMosaic` global raster compositing | `1` |
| `dataview_metadata` | `merge_city_metadata.js`, `verify_downstream_ci_cd.js`, Dataview `stadester_2.0` cache warming & builds | `1` |
| `gpu_compute` | OpenCL / `ViscountKrigingGPU` runs (respects `frame_budget_ms: 6`, `max_vram_mb: 2048`) | `1` |

Use `--wait-seconds=120` when queueing a second regional study behind an active lock rather than bypassing or running simultaneously.

---

## 3. Hard Concurrency & Hygiene Caps for Ad-Hoc Agent Scripts

1. **Worker Pools (`<= 4`)**: Never call `ProcessPoolExecutor()`, `ThreadPoolExecutor()`, `multiprocessing.Pool()` or `os.cpus().length` without clamping explicitly to `<= 4` (`min(4, ...)`).
2. **RMarkdown / XeLaTeX Builds (`<= 2`)**: Never run `> 2` concurrent `Rscript.exe` / `xelatex.exe` compilations, and never render two `.Rmd` files in the same directory concurrently.
3. **Headless Browsers (`<= 2` + Mandatory Teardown)**: Every Puppeteer/Selenium scraping script MUST wrap browser lifecycles inside `try ... finally` calling `browser.close()` / `driver.quit()` and cap parallel browser instances to `<= 2`.
4. **Zero Detached Processes**: Never spawn `detached: true` (Node.js) or `DETACHED_PROCESS` (Python).
5. **Post-Stage Orphan Audit & Static Gatekeeper S**:
   ```powershell
   python .agents/skills/population-regional-study/scripts/audit_shell_and_scripts.py histmap/1.data_raw/population_regional/<PROJECT_KEY>
   python .agents/skills/population-regional-study/scripts/run_bounded.py --audit-orphans
   ```
   Both commands MUST exit `0` before marking any stage complete or after cancelling any background task.
