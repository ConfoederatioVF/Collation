//Import modules
let child_process = require("child_process");
let fs = require("fs");
let os = require("os");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");

//Initialise functions
{
  let bounded_runner = {
    _win32: null,
    DEFAULT_LIMITS: {
      enforce_job_object: true,
      max_ram_mb: 6144,
      max_threads: 8,
      max_workers: 4,
      priority_below_normal: true
    },
    ORPHAN_CANDIDATE_EXES: new Set([
      "chrome.exe", "chromedriver.exe", "msedgedriver.exe", "geckodriver.exe",
      "node.exe", "python.exe", "rscript.exe", "xelatex.exe", "pdflatex.exe"
    ]),

    /**
     * Acquires an exclusive atomic lockfile under `histmap/.locks/<name>.lock` with stale-PID recovery.
     * @alias bounded_runner.acquireMutexLock
     *
     * @param {string} arg0_svea_root
     * @param {string} arg1_lock_name
     * @param {string} arg2_project
     * @param {Array<string>} arg3_cmd
     * @param {number} [arg4_wait_seconds=0]
     *
     * @returns {string|null}
     */
    acquireMutexLock (arg0_svea_root, arg1_lock_name, arg2_project, arg3_cmd, arg4_wait_seconds) {
      //Convert from parameters
      let safe_name = String(arg1_lock_name || "").trim().replace(/[^A-Za-z0-9_.-]+/g, "_").replace(/^_+|_+$/g, "");
      let svea_root = arg0_svea_root;
      let wait_ms = Math.max(0, Number(arg4_wait_seconds) || 0)*1000;

      //Guard clauses
      if (!safe_name) return null;

      //Declare local instance variables
      let deadline = Date.now() + wait_ms;
      let locks_dir = path.join(svea_root, "histmap", ".locks");
      let lock_path = path.join(locks_dir, `${safe_name}.lock`);
      let payload = {
        command: (Array.isArray(arg3_cmd) ? arg3_cmd.join(" ") : "").slice(0, 400),
        lock_name: safe_name,
        pid: process.pid,
        project: String(arg2_project || "UNSPECIFIED").toUpperCase(),
        started_utc: new Date().toISOString()
      };

      //Function body
      fs.mkdirSync(locks_dir, { recursive: true });
      for (let attempt = 0; attempt < 10000; attempt++) {
        try {
          let fd = fs.openSync(lock_path, "wx");
          try {
            fs.writeSync(fd, JSON.stringify(payload, null, 2));
          } finally {
            fs.closeSync(fd);
          }
          return lock_path;
        } catch (err) {
          if (err.code !== "EEXIST") throw err;
          let owner = {};
          try {
            owner = JSON.parse(fs.readFileSync(lock_path, "utf8"));
          } catch (e) {
            owner = {};
          }
          let owner_pid = Number(owner.pid || 0);
          if (owner_pid <= 0 || !this.isPidAlive(owner_pid)) {
            try {
              fs.unlinkSync(lock_path);
              console.error(`[run_bounded] Reclaimed stale mutex lock \`${safe_name}\` from exited PID ${owner_pid}.`);
              continue;
            } catch (e) {}
          }
          if (Date.now() >= deadline) {
            throw new Error(
              `[LOCK_CONFLICT] Mutex \`${safe_name}\` is currently held by active PID ${owner_pid} ` +
              `(project=${owner.project || "?"}, started=${owner.started_utc || "?"}). ` +
              "Serialize Stadestér/Velkscala/Dataview/GPU stages instead of running concurrently."
            );
          }
          Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 1500);
        }
      }

      //Return statement
      return null;
    },

    /**
     * Assigns a child PID into an active Win32 Job Object and applies `BELOW_NORMAL_PRIORITY_CLASS`.
     * @alias bounded_runner.assignPidToJob
     *
     * @param {*} arg0_job_handle
     * @param {number} arg1_pid
     * @param {boolean} arg2_below_normal
     *
     * @returns {boolean}
     */
    assignPidToJob (arg0_job_handle, arg1_pid, arg2_below_normal) {
      //Convert from parameters
      let below_normal = Boolean(arg2_below_normal);
      let job = arg0_job_handle;
      let pid = Number(arg1_pid);

      //Guard clauses
      if (process.platform !== "win32" || !pid) return false;

      //Function body
      if (below_normal) {
        try {
          os.setPriority(pid, os.constants.priority.PRIORITY_BELOW_NORMAL);
        } catch (e) {}
      }
      if (!job) return false;

      let w32 = this.initWin32();
      if (!w32) return false;
      let PROCESS_SET_QUOTA = 0x0100;
      let PROCESS_TERMINATE = 0x0001;
      let h_proc = w32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, 0, pid);
      if (!h_proc) return false;
      try {
        return Boolean(w32.AssignProcessToJobObject(job, h_proc));
      } finally {
        w32.CloseHandle(h_proc);
      }
    },

    /**
     * Inspects live OS processes referencing this workspace and reports potential orphans.
     * @alias bounded_runner.auditWorkspaceOrphans
     *
     * @param {string} arg0_svea_root
     *
     * @returns {Array<Object>}
     */
    auditWorkspaceOrphans (arg0_svea_root) {
      //Convert from parameters
      let svea_root = arg0_svea_root;

      //Declare local instance variables
      let findings = [];

      //Guard clauses
      if (process.platform !== "win32") return findings;

      //Function body
      let ps_cmd = "Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId, Name, CommandLine, WorkingSetSize | ConvertTo-Json -Compress";
      let res = child_process.spawnSync("powershell", ["-NoProfile", "-Command", ps_cmd], {
        encoding: "utf8",
        timeout: 20000
      });
      if (res.status !== 0 || !res.stdout || !res.stdout.trim()) return findings;

      let rows = [];
      try {
        let parsed = JSON.parse(res.stdout);
        rows = Array.isArray(parsed) ? parsed : [parsed];
      } catch (e) {
        return findings;
      }

      let ws_norm = path.resolve(svea_root).replace(/\\/g, "/").toLowerCase();
      let ws_name = path.basename(ws_norm);
      let live_pids = new Set();
      for (let i = 0; i < rows.length; i++) {
        if (rows[i] && rows[i].ProcessId) live_pids.add(Number(rows[i].ProcessId));
      }

      for (let i = 0; i < rows.length; i++) {
        let row = rows[i];
        if (!row) continue;
        let pid = Number(row.ProcessId || 0);
        let ppid = Number(row.ParentProcessId || 0);
        let name = String(row.Name || "").toLowerCase();
        let cmdline = String(row.CommandLine || "");
        let cmd_norm = cmdline.replace(/\\/g, "/").toLowerCase();
        if (pid === process.pid || pid === process.ppid || !this.ORPHAN_CANDIDATE_EXES.has(name)) continue;

        let is_ws = cmd_norm.includes(ws_norm) || cmd_norm.includes(ws_name) ||
          ((name === "chrome.exe" || name === "chromedriver.exe") && cmd_norm.includes("--headless") &&
            (cmd_norm.includes("puppeteer") || cmd_norm.includes("selenium") || cmd_norm.includes("remote-debugging-port")));
        if (!is_ws) continue;

        if (!live_pids.has(ppid) || name === "chromedriver.exe" || name === "xelatex.exe") {
          findings.push({
            cmdline: cmdline.slice(0, 180),
            name: name,
            parent_alive: live_pids.has(ppid),
            pid: pid,
            ppid: ppid,
            rss_mb: Number((Number(row.WorkingSetSize || 0)/(1024.0*1024.0)).toFixed(1))
          });
        }
      }

      //Return statement
      return findings;
    },

    /**
     * Builds child environment enforcing BLAS, OpenMP, libuv and Node memory caps.
     * @alias bounded_runner.buildBoundedEnv
     *
     * @param {Object} arg0_limits
     * @param {number} arg1_max_ram_mb
     * @param {number} arg2_max_threads
     * @param {string|null} arg3_lock_name
     *
     * @returns {Object}
     */
    buildBoundedEnv (arg0_limits, arg1_max_ram_mb, arg2_max_threads, arg3_lock_name) {
      //Convert from parameters
      let env = Object.assign({}, process.env);
      let ram_mb = Math.max(1024, Math.min(8192, Math.floor(Number(arg1_max_ram_mb) || 6144)));
      let threads_str = String(Math.max(1, Math.floor(Number(arg2_max_threads) || 4)));

      //Function body
      env.OMP_NUM_THREADS = threads_str;
      env.OPENBLAS_NUM_THREADS = threads_str;
      env.MKL_NUM_THREADS = threads_str;
      env.NUMEXPR_MAX_THREADS = threads_str;
      env.VECLIB_MAXIMUM_THREADS = threads_str;
      env.BLIS_NUM_THREADS = threads_str;
      env.UV_THREADPOOL_SIZE = threads_str;
      env.VISCOUNT_MAX_WORKERS = String(arg0_limits.max_workers);
      env.VISCOUNT_MAX_RAM_MB = String(ram_mb);
      if (arg3_lock_name) env.VISCOUNT_ACTIVE_LOCK = String(arg3_lock_name);

      let existing_opts = String(env.NODE_OPTIONS || "").trim();
      if (existing_opts.includes("--max-old-space-size="))
        existing_opts = existing_opts.replace(/--max-old-space-size=\d+/, `--max-old-space-size=${ram_mb}`);
      else
        existing_opts = `${existing_opts} --max-old-space-size=${ram_mb}`.trim();
      env.NODE_OPTIONS = existing_opts;

      //Return statement
      return env;
    },

    /**
     * Creates a Win32 Job Object configured with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.
     * @alias bounded_runner.createWin32KillOnCloseJob
     *
     * @returns {*}
     */
    createWin32KillOnCloseJob () {
      //Guard clauses
      if (process.platform !== "win32") return null;

      //Function body
      let w32 = this.initWin32();
      if (!w32) return null;

      let job = w32.CreateJobObjectW(null, null);
      if (!job) return null;

      let JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9;
      let JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
      let info = {
        BasicLimitInformation: {
          ActiveProcessLimit: 0,
          Affinity: 0,
          LimitFlags: JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
          MaximumWorkingSetSize: 0,
          MinimumWorkingSetSize: 0,
          PerJobUserTimeLimit: 0,
          PerProcessUserTimeLimit: 0,
          PriorityClass: 0,
          SchedulingClass: 0
        },
        IoInfo: {
          OtherOperationCount: 0,
          OtherTransferCount: 0,
          ReadOperationCount: 0,
          ReadTransferCount: 0,
          WriteOperationCount: 0,
          WriteTransferCount: 0
        },
        JobMemoryLimit: 0,
        PeakJobMemoryUsed: 0,
        PeakProcessMemoryUsed: 0,
        ProcessMemoryLimit: 0
      };

      let ok = w32.SetInformationJobObject(job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, info, w32.ext_limit_size);
      if (!ok) {
        w32.CloseHandle(job);
        return null;
      }

      //Return statement
      return job;
    },

    /**
     * Returns current resident working-set memory in MiB for `arg0_pid`, or 0 if unavailable.
     * @alias bounded_runner.getProcessRssMb
     *
     * @param {number} arg0_pid
     *
     * @returns {number}
     */
    getProcessRssMb (arg0_pid) {
      //Convert from parameters
      let pid = Number(arg0_pid || 0);

      //Guard clauses
      if (process.platform !== "win32" || pid <= 0) return 0;

      //Function body
      let w32 = this.initWin32();
      if (!w32) return 0;

      let PROCESS_QUERY_LIMITED_INFORMATION = 0x1000;
      let PROCESS_VM_READ = 0x0010;
      let h = w32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, 0, pid);
      if (!h) return 0;
      try {
        let pmc = {
          PageFaultCount: 0,
          PagefileUsage: 0,
          PeakPagefileUsage: 0,
          PeakWorkingSetSize: 0,
          QuotaNonPagedPoolUsage: 0,
          QuotaPagedPoolUsage: 0,
          QuotaPeakNonPagedPoolUsage: 0,
          QuotaPeakPagedPoolUsage: 0,
          WorkingSetSize: 0,
          cb: w32.pmc_size
        };
        if (w32.K32GetProcessMemoryInfo(h, pmc, w32.pmc_size))
          return Number(pmc.WorkingSetSize)/(1024.0*1024.0);
        return 0;
      } finally {
        w32.CloseHandle(h);
      }
    },

    /**
     * Lazily binds Win32 Job Object and process memory APIs via `koffi`.
     * @alias bounded_runner.initWin32
     *
     * @returns {Object|null}
     */
    initWin32 () {
      //Guard clauses
      if (this._win32 !== null) return this._win32;
      if (process.platform !== "win32") return null;

      //Function body
      try {
        let koffi = require("koffi");
        let kernel32 = koffi.load("kernel32.dll");

        let IO_COUNTERS = koffi.struct("IO_COUNTERS", {
          OtherOperationCount: "uint64",
          OtherTransferCount: "uint64",
          ReadOperationCount: "uint64",
          ReadTransferCount: "uint64",
          WriteOperationCount: "uint64",
          WriteTransferCount: "uint64"
        });
        let JOBOBJECT_BASIC_LIMIT_INFORMATION = koffi.struct("JOBOBJECT_BASIC_LIMIT_INFORMATION", {
          PerProcessUserTimeLimit: "int64",
          PerJobUserTimeLimit: "int64",
          LimitFlags: "uint32",
          MinimumWorkingSetSize: "uintptr",
          MaximumWorkingSetSize: "uintptr",
          ActiveProcessLimit: "uint32",
          Affinity: "uintptr",
          PriorityClass: "uint32",
          SchedulingClass: "uint32"
        });
        let JOBOBJECT_EXTENDED_LIMIT_INFORMATION = koffi.struct("JOBOBJECT_EXTENDED_LIMIT_INFORMATION", {
          BasicLimitInformation: JOBOBJECT_BASIC_LIMIT_INFORMATION,
          IoInfo: IO_COUNTERS,
          ProcessMemoryLimit: "uintptr",
          JobMemoryLimit: "uintptr",
          PeakProcessMemoryUsed: "uintptr",
          PeakJobMemoryUsed: "uintptr"
        });
        let PROCESS_MEMORY_COUNTERS = koffi.struct("PROCESS_MEMORY_COUNTERS", {
          cb: "uint32",
          PageFaultCount: "uint32",
          PeakWorkingSetSize: "uintptr",
          WorkingSetSize: "uintptr",
          QuotaPeakPagedPoolUsage: "uintptr",
          QuotaPagedPoolUsage: "uintptr",
          QuotaPeakNonPagedPoolUsage: "uintptr",
          QuotaNonPagedPoolUsage: "uintptr",
          PagefileUsage: "uintptr",
          PeakPagefileUsage: "uintptr"
        });

        this._win32 = {
          AssignProcessToJobObject: kernel32.func("int __stdcall AssignProcessToJobObject(void *hJob, void *hProcess)"),
          CloseHandle: kernel32.func("int __stdcall CloseHandle(void *hObject)"),
          CreateJobObjectW: kernel32.func("void * __stdcall CreateJobObjectW(void *lpJobAttributes, str16 lpName)"),
          GetExitCodeProcess: kernel32.func("int __stdcall GetExitCodeProcess(void *hProcess, _Out_ uint32 *lpExitCode)"),
          K32GetProcessMemoryInfo: kernel32.func("int __stdcall K32GetProcessMemoryInfo(void *Process, _Inout_ PROCESS_MEMORY_COUNTERS *ppsmemCounters, uint32 cb)"),
          OpenProcess: kernel32.func("void * __stdcall OpenProcess(uint32 dwDesiredAccess, int bInheritHandle, uint32 dwProcessId)"),
          SetInformationJobObject: kernel32.func("int __stdcall SetInformationJobObject(void *hJob, int JobObjectInfoClass, JOBOBJECT_EXTENDED_LIMIT_INFORMATION *lpJobObjectInfo, uint32 cbJobObjectInfoLength)"),
          TerminateJobObject: kernel32.func("int __stdcall TerminateJobObject(void *hJob, uint32 uExitCode)"),
          ext_limit_size: koffi.sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION),
          pmc_size: koffi.sizeof(PROCESS_MEMORY_COUNTERS)
        };
      } catch (e) {
        this._win32 = false;
        return null;
      }

      //Return statement
      return this._win32;
    },

    /**
     * Returns true when `arg0_pid` refers to a currently live OS process.
     * @alias bounded_runner.isPidAlive
     *
     * @param {number} arg0_pid
     *
     * @returns {boolean}
     */
    isPidAlive (arg0_pid) {
      //Convert from parameters
      let pid = Number(arg0_pid || 0);

      //Guard clauses
      if (!Number.isInteger(pid) || pid <= 0) return false;

      //Function body
      if (process.platform === "win32") {
        let w32 = this.initWin32();
        if (w32) {
          let PROCESS_QUERY_LIMITED_INFORMATION = 0x1000;
          let STILL_ACTIVE = 259;
          let h = w32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid);
          if (!h) return false;
          try {
            let code_out = [0];
            if (w32.GetExitCodeProcess(h, code_out))
              return code_out[0] === STILL_ACTIVE;
            return true;
          } finally {
            w32.CloseHandle(h);
          }
        }
      }

      try {
        process.kill(pid, 0);
        return true;
      } catch (e) {
        return false;
      }
    },

    /**
     * Loads workstation CPU/RAM/Job-Object caps from `common/defines/geopng_compute.json5`.
     * @alias bounded_runner.loadComputeLimits
     *
     * @param {string} arg0_svea_root
     *
     * @returns {Object}
     */
    loadComputeLimits (arg0_svea_root) {
      //Convert from parameters
      let limits = Object.assign({}, this.DEFAULT_LIMITS);
      let cfg_path = path.join(arg0_svea_root, "common/defines/geopng_compute.json5");

      //Guard clauses
      if (!fs.existsSync(cfg_path)) return limits;

      //Function body
      try {
        let data = viscount_audit_utils.loadJsonOrJson5(cfg_path);
        let cpu_cfg = (data && data.cpu) ? data.cpu : {};
        let native_cfg = (data && data.native) ? data.native : {};
        let ram_cfg = (data && data.ram) ? data.ram : {};
        limits.max_workers = Math.max(1, Math.min(8, Number(cpu_cfg.max_workers) || limits.max_workers));
        limits.max_threads = Math.max(1, Math.min(12, Number(native_cfg.max_threads) || limits.max_threads));
        limits.max_ram_mb = Math.max(1024, Math.min(8192, Number(ram_cfg.max_ram_mb) || limits.max_ram_mb));
        limits.priority_below_normal = (cpu_cfg.priority_below_normal !== undefined) ? Boolean(cpu_cfg.priority_below_normal) : true;
        limits.enforce_job_object = (native_cfg.enforce_job_object !== undefined) ? Boolean(native_cfg.enforce_job_object) : true;
      } catch (e) {}

      //Return statement
      return limits;
    },

    /**
     * Parses CLI arguments for `run_bounded.js`.
     * @alias bounded_runner.parseCliArgs
     *
     * @param {Array<string>} arg0_argv
     *
     * @returns {Object}
     */
    parseCliArgs (arg0_argv) {
      //Convert from parameters
      let argv = Array.isArray(arg0_argv) ? arg0_argv : [];

      //Declare local instance variables
      let out = {
        audit_orphans: false,
        cmd: [],
        cwd: null,
        lock: null,
        max_ram_mb: 0,
        max_threads: 0,
        project: "UNSPECIFIED",
        timeout: 0,
        wait_seconds: 0
      };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok === "--") {
          out.cmd = argv.slice(i + 1);
          break;
        }
        if (tok === "--lock" && i + 1 < argv.length) out.lock = argv[++i];
        else if (tok.startsWith("--lock=")) out.lock = tok.slice(7);
        else if (tok === "--wait-seconds" && i + 1 < argv.length) out.wait_seconds = Number(argv[++i]) || 0;
        else if (tok.startsWith("--wait-seconds=")) out.wait_seconds = Number(tok.slice(15)) || 0;
        else if (tok === "--project" && i + 1 < argv.length) out.project = argv[++i];
        else if (tok.startsWith("--project=")) out.project = tok.slice(10);
        else if (tok === "--timeout" && i + 1 < argv.length) out.timeout = Number(argv[++i]) || 0;
        else if (tok.startsWith("--timeout=")) out.timeout = Number(tok.slice(10)) || 0;
        else if (tok === "--max-ram-mb" && i + 1 < argv.length) out.max_ram_mb = Number(argv[++i]) || 0;
        else if (tok.startsWith("--max-ram-mb=")) out.max_ram_mb = Number(tok.slice(13)) || 0;
        else if (tok === "--max-threads" && i + 1 < argv.length) out.max_threads = Number(argv[++i]) || 0;
        else if (tok.startsWith("--max-threads=")) out.max_threads = Number(tok.slice(14)) || 0;
        else if (tok === "--cwd" && i + 1 < argv.length) out.cwd = argv[++i];
        else if (tok.startsWith("--cwd=")) out.cwd = tok.slice(6);
        else if (tok === "--audit-orphans") out.audit_orphans = true;
        else {
          out.cmd = argv.slice(i);
          break;
        }
      }

      //Return statement
      return out;
    },

    /**
     * Releases a mutex lockfile if owned by the current process.
     * @alias bounded_runner.releaseMutexLock
     *
     * @param {string|null} arg0_lock_path
     */
    releaseMutexLock (arg0_lock_path) {
      //Guard clauses
      if (!arg0_lock_path || !fs.existsSync(arg0_lock_path)) return;

      //Function body
      try {
        let owner = JSON.parse(fs.readFileSync(arg0_lock_path, "utf8"));
        if (Number(owner.pid || 0) === process.pid)
          fs.unlinkSync(arg0_lock_path);
      } catch (e) {}
    },

    /**
     * Executes a child command bounded by Win32 Job Object, priority cap, env thread caps, mutex lock and watchdogs.
     * @alias bounded_runner.runCommand
     *
     * @param {Object} arg0_cli
     */
    runCommand (arg0_cli) {
      //Convert from parameters
      let cli = arg0_cli;
      let svea_root = viscount_audit_utils.findSveaRoot(cli.cwd || process.cwd()) || path.resolve(__dirname, "../../../..");

      //Function body
      if (cli.audit_orphans) {
        let orphans = this.auditWorkspaceOrphans(svea_root);
        if (orphans.length > 0) {
          for (let i = 0; i < orphans.length; i++) {
            let it = orphans[i];
            console.error(`[FAIL] Orphaned/stale process PID=${it.pid} (${it.name}, ${it.rss_mb} MiB, parent_alive=${it.parent_alive}): ${it.cmdline}`);
          }
          process.exit(1);
        }
        console.log("[run_bounded] PASS: 0 orphaned workspace background processes detected.");
        process.exit(0);
      }

      if (!Array.isArray(cli.cmd) || cli.cmd.length === 0) {
        console.error("[FAIL] No command provided to run_bounded.js (pass `-- <command> <args>`).");
        process.exit(2);
      }

      let limits = this.loadComputeLimits(svea_root);
      let eff_ram = Math.max(1024, Math.min(8192, cli.max_ram_mb > 0 ? cli.max_ram_mb : limits.max_ram_mb));
      let eff_threads = Math.max(1, Math.min(8, cli.max_threads > 0 ? cli.max_threads : limits.max_workers));
      let lock_path = null;
      let job_handle = null;
      let child = null;
      let watchdog = null;
      let cleaned = false;

      let that = this;
      let cleanup = function (arg0_kill_job) {
        if (cleaned) return;
        cleaned = true;
        if (watchdog) clearInterval(watchdog);
        let w32 = that.initWin32();
        if (job_handle && w32) {
          if (arg0_kill_job) {
            try { w32.TerminateJobObject(job_handle, 1); } catch (e) {}
          }
          try { w32.CloseHandle(job_handle); } catch (e) {}
          job_handle = null;
        }
        that.releaseMutexLock(lock_path);
      };

      try {
        if (cli.lock)
          lock_path = this.acquireMutexLock(svea_root, cli.lock, cli.project, cli.cmd, cli.wait_seconds);

        let env = this.buildBoundedEnv(limits, eff_ram, eff_threads, cli.lock);
        if (process.platform === "win32" && limits.enforce_job_object)
          job_handle = this.createWin32KillOnCloseJob();

        let start_ms = Date.now();
        child = child_process.spawn(cli.cmd[0], cli.cmd.slice(1), {
          cwd: cli.cwd || process.cwd(),
          detached: false,
          env: env,
          stdio: "inherit",
          windowsHide: true
        });

        if (child.pid)
          this.assignPidToJob(job_handle, child.pid, limits.priority_below_normal);

        watchdog = setInterval(() => {
          if (!child || child.exitCode !== null) return;
          if (cli.timeout > 0 && (Date.now() - start_ms) > cli.timeout*1000) {
            console.error(`[FAIL] [run_bounded] Timeout exceeded (${cli.timeout}s); terminating job tree.`);
            try { child.kill(); } catch (e) {}
            cleanup(true);
            process.exit(124);
          }
          if (child.pid) {
            let rss_mb = that.getProcessRssMb(child.pid);
            if (rss_mb > eff_ram*1.15) {
              console.error(`[FAIL] [run_bounded] Child PID ${child.pid} exceeded RAM cap (${rss_mb.toFixed(1)} MiB > ${Math.round(eff_ram*1.15)} MiB); terminating job tree.`);
              try { child.kill(); } catch (e) {}
              cleanup(true);
              process.exit(137);
            }
          }
        }, 500);

        process.on("SIGINT", function () {
          try { if (child) child.kill(); } catch (e) {}
          cleanup(true);
          process.exit(130);
        });
        process.on("SIGTERM", function () {
          try { if (child) child.kill(); } catch (e) {}
          cleanup(true);
          process.exit(143);
        });

        child.on("error", function (arg0_err) {
          console.error(`[FAIL] [run_bounded] Failed to spawn command: ${arg0_err.message}`);
          cleanup(true);
          process.exit(1);
        });

        child.on("exit", function (arg0_code) {
          cleanup(true);
          process.exit(arg0_code === null ? 1 : arg0_code);
        });
      } catch (err) {
        console.error(`[FAIL] ${err.message}`);
        cleanup(true);
        process.exit(1);
      }
    }
  };

  if (require.main === module) {
    let cli = bounded_runner.parseCliArgs(process.argv.slice(2));
    bounded_runner.runCommand(cli);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { bounded_runner: bounded_runner };
  }
}
