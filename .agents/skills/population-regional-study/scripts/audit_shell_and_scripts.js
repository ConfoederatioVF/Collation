//Import modules
let acorn = require("acorn");
let fs = require("fs");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");

//Initialise functions
{
  let shell_and_scripts_auditor = {
    DIRECT_STADESTER_RE: /\b(?:population_Stadester|population_Velkscala)\.js\b/,
    PY_BROWSER_CLOSE_RE: /\.(?:quit|close)\s*\(/,
    PY_BROWSER_LAUNCH_RE: /\bwebdriver\.(?:Chrome|Edge|Firefox)\s*\(|\basync_playwright\s*\(|\bsync_playwright\s*\(/,
    SKIP_DIRS: new Set([".git", ".Rproj.user", "__pycache__", "_gis_cache", "archive", "diagnostics_visual", "figures", "node_modules", "papers"]),
    UNBOUNDED_NODE_HEAP_RE: /--max-old-space-size\s*=\s*(\d+)/g,

    /**
     * Audits an ad-hoc Node.js script via Acorn AST + static rules for detached spawns, unclosed Puppeteer browsers,
     * uncapped `os.cpus().length`, heap bloat and unguarded pipeline invocations.
     * @alias shell_and_scripts_auditor.auditJsScript
     *
     * @param {string} arg0_source
     * @param {string} arg1_label
     *
     * @returns {{ errors: Array<string>, warnings: Array<string> }}
     */
    auditJsScript (arg0_source, arg1_label) {
      //Convert from parameters
      let label = arg1_label;
      let source = String(arg0_source || "");

      //Declare local instance variables
      let errors = [];
      let has_browser_close = false;
      let has_finally = false;
      let has_puppeteer_launch = false;
      let warnings = [];

      //Function body
      // Heap cap check
      let hm = null;
      this.UNBOUNDED_NODE_HEAP_RE.lastIndex = 0;
      for (let iter = 0; (hm = this.UNBOUNDED_NODE_HEAP_RE.exec(source)) !== null && iter < 20; iter++) {
        let mb = Number(hm[1]);
        if (mb > 8192)
          errors.push(`[${label}] Spawns Node with \`--max-old-space-size=${mb}\` (> 8.192 MiB ceiling).`);
      }

      // Acorn AST parse (strip shebang if present)
      let parseable = source.startsWith("#!") ? source.replace(/^#![^\r\n]*/, "") : source;
      let ast = null;
      try {
        ast = acorn.parse(parseable, { allowHashBang: true, allowReturnOutsideFunction: true, ecmaVersion: 2022, locations: true, sourceType: "script" });
      } catch (e1) {
        try {
          ast = acorn.parse(parseable, { allowHashBang: true, ecmaVersion: 2022, locations: true, sourceType: "module" });
        } catch (e2) {
          ast = null;
        }
      }

      if (ast) {
        let stack = [ast];
        for (let step = 0; stack.length > 0 && step < 200000; step++) {
          let node = stack.pop();
          if (!node || typeof node !== "object") continue;

          if (node.type === "TryStatement" && node.finalizer)
            has_finally = true;

          if (node.type === "Property" && node.key) {
            let kname = node.key.name || node.key.value;
            if (kname === "detached" && node.value && node.value.type === "Literal" && node.value.value === true)
              errors.push(`[${label}] line ${node.loc ? node.loc.start.line : 1}: uses \`detached: true\` in child process spawn; risks orphaned background processes.`);
          }

          if (node.type === "CallExpression" && node.callee && node.callee.type === "MemberExpression") {
            let obj_name = (node.callee.object && node.callee.object.name) ? node.callee.object.name : "";
            let prop_name = (node.callee.property && node.callee.property.name) ? node.callee.property.name : "";
            if (obj_name === "puppeteer" && prop_name === "launch") has_puppeteer_launch = true;
            if ((obj_name === "browser" || obj_name === "page") && prop_name === "close") has_browser_close = true;
          }

          let keys = Object.keys(node);
          for (let i = 0; i < keys.length; i++) {
            let k = keys[i];
            if (k === "loc" || k === "start" || k === "end") continue;
            let v = node[k];
            if (Array.isArray(v)) {
              for (let x = 0; x < v.length; x++) {
                if (v[x] && typeof v[x].type === "string") stack.push(v[x]);
              }
            } else if (v && typeof v.type === "string") {
              stack.push(v);
            }
          }
        }
      } else {
        if (/\bdetached\s*:\s*true\b/.test(source))
          errors.push(`[${label}] Uses \`detached: true\` in child process spawn; risks orphaned background processes.`);
        has_puppeteer_launch = /\bpuppeteer\s*\.\s*launch\s*\(/.test(source);
        has_browser_close = /\b(?:browser|page)\s*\.\s*close\s*\(/.test(source);
        has_finally = /\bfinally\s*\{/.test(source);
      }

      if (has_puppeteer_launch && !(has_browser_close && has_finally))
        errors.push(`[${label}] Calls \`puppeteer.launch()\` without a \`finally { ... browser.close() }\` block; risks orphaned Chrome processes.`);

      if (/os\.cpus\(\)\.length/.test(source) && !/Math\.min\s*\([^)]*os\.cpus\(\)\.length/.test(source))
        errors.push(`[${label}] Uses uncapped \`os.cpus().length\` for worker concurrency; clamp via \`Math.min(4, os.cpus().length)\`.`);

      let base = path.basename(label).toLowerCase();
      if (base !== "population_stadester.js" && base !== "population_velkscala.js") {
        if (this.DIRECT_STADESTER_RE.test(source) && source.includes("spawn") &&
            !source.includes("run_bounded.js") && !source.includes("run_bounded.py")) {
          errors.push(`[${label}] Spawns \`population_Stadester.js\`/\`population_Velkscala.js\` without \`run_bounded.js --lock stadester_velkscala\`.`);
        }
      }

      //Return statement
      return { errors: errors, warnings: warnings };
    },

    /**
     * Audits an ad-hoc Python script for uncapped worker pools, detached spawns, heap bloat and unclosed browsers.
     * @alias shell_and_scripts_auditor.auditPythonScript
     *
     * @param {string} arg0_source
     * @param {string} arg1_label
     *
     * @returns {{ errors: Array<string>, warnings: Array<string> }}
     */
    auditPythonScript (arg0_source, arg1_label) {
      //Convert from parameters
      let label = arg1_label;
      let source = String(arg0_source || "");

      //Declare local instance variables
      let errors = [];
      let lines = source.split(/\r?\n/);
      let warnings = [];

      //Function body
      let has_browser_launch = this.PY_BROWSER_LAUNCH_RE.test(source);
      let has_browser_close = this.PY_BROWSER_CLOSE_RE.test(source);
      let has_try_finally = /^\s*finally\s*:/m.test(source);
      let has_with_stmt = /^\s*(?:async\s+)?with\b/m.test(source);

      if (has_browser_launch && !(has_browser_close && (has_try_finally || has_with_stmt)))
        errors.push(`[${label}] Launches Selenium/Playwright browser without \`try...finally\` (or \`with\`) teardown calling \`.quit()\`/\`.close()\`; risks orphaned browser processes.`);

      let hm = null;
      this.UNBOUNDED_NODE_HEAP_RE.lastIndex = 0;
      for (let iter = 0; (hm = this.UNBOUNDED_NODE_HEAP_RE.exec(source)) !== null && iter < 20; iter++) {
        let mb = Number(hm[1]);
        if (mb > 8192)
          errors.push(`[${label}] Spawns Node with \`--max-old-space-size=${mb}\` (> 8.192 MiB cap; align with \`geopng_compute.json5\`).`);
      }

      let has_popen_wait = /\.(?:wait|communicate|terminate|kill)\s*\(/.test(source);
      for (let i = 0; i < lines.length; i++) {
        let line_no = i + 1;
        let ln = lines[i].replace(/#.*$/, "");
        if (!ln.trim()) continue;

        let exec_m = ln.match(/\b(ProcessPoolExecutor|ThreadPoolExecutor)\s*\(([^)]*)\)/);
        if (exec_m) {
          let fn_name = exec_m[1];
          let arg_str = exec_m[2].trim();
          if (!arg_str) {
            errors.push(`[${label}] line ${line_no}: \`${fn_name}()\` without explicit \`max_workers <= 4\` defaults to saturating all CPU threads.`);
          } else {
            let num_m = arg_str.match(/(?:max_workers\s*=\s*|^)(\d+)\b/);
            if (num_m && Number(num_m[1]) > 4)
              errors.push(`[${label}] line ${line_no}: \`${fn_name}(max_workers=${num_m[1]})\` exceeds \`geopng_compute.json5\` cap (<= 4).`);
            else if (arg_str.includes("cpu_count") && !arg_str.includes("min("))
              errors.push(`[${label}] line ${line_no}: \`${fn_name}\` derives workers from uncapped \`cpu_count()\`; wrap with \`min(4, ...)\`.`);
          }
        }

        let pool_m = ln.match(/\bPool\s*\(([^)]*)\)/);
        if (pool_m && !ln.includes("ThreadPool") && !ln.includes("ProcessPool")) {
          let arg_str = pool_m[1].trim();
          if (!arg_str) {
            errors.push(`[${label}] line ${line_no}: \`multiprocessing.Pool()\` without explicit \`processes <= 4\` saturates all CPU cores.`);
          } else {
            let num_m = arg_str.match(/(?:processes\s*=\s*|^)(\d+)\b/);
            if (num_m && Number(num_m[1]) > 4)
              errors.push(`[${label}] line ${line_no}: \`Pool(processes=${num_m[1]})\` exceeds cap (<= 4).`);
          }
        }

        if (/\bPopen\s*\(/.test(ln)) {
          if (ln.includes("DETACHED_PROCESS"))
            errors.push(`[${label}] line ${line_no}: \`subprocess.Popen(..., DETACHED_PROCESS)\` creates unmanageable orphan processes.`);
          if (!has_popen_wait)
            warnings.push(`[${label}] line ${line_no}: \`subprocess.Popen\` called without visible \`.wait()\`/\`.communicate()\`/\`.terminate()\` cleanup.`);
        }
      }

      if (this.DIRECT_STADESTER_RE.test(source) && !source.includes("run_bounded.js") && !source.includes("run_bounded.py"))
        errors.push(`[${label}] Invokes \`population_Stadester.js\`/\`population_Velkscala.js\` directly without \`run_bounded.js --lock stadester_velkscala\` mutex.`);

      //Return statement
      return { errors: errors, warnings: warnings };
    },

    /**
     * Scans a file or directory of regional/test `.py` and `.js` scripts for shell resource anti-patterns.
     * @alias shell_and_scripts_auditor.auditTarget
     *
     * @param {string} arg0_target_path
     *
     * @returns {{ errors: Array<string>, files_checked: number, success: boolean, warnings: Array<string> }}
     */
    auditTarget (arg0_target_path) {
      //Convert from parameters
      let abs_target = path.resolve(arg0_target_path);

      //Guard clauses
      if (!fs.existsSync(abs_target))
        return { errors: [`Target path not found: ${arg0_target_path}`], files_checked: 0, success: false, warnings: [] };

      //Declare local instance variables
      let all_errors = [];
      let all_warnings = [];
      let is_file = fs.statSync(abs_target).isFile();
      let base_root = is_file ? path.dirname(abs_target) : abs_target;
      let files = is_file ? [abs_target] : viscount_audit_utils.walkFiles(abs_target, function (arg0_full, arg1_name) {
        return /\.(?:py|js)$/i.test(arg1_name);
      }, this.SKIP_DIRS);

      //Function body
      for (let i = 0; i < files.length; i++) {
        let fpath = files[i];
        let rel = path.relative(base_root, fpath).replace(/\\/g, "/");
        let src = "";
        try {
          src = fs.readFileSync(fpath, "utf8");
        } catch (e) {
          continue;
        }
        let res = fpath.toLowerCase().endsWith(".py") ?
          this.auditPythonScript(src, rel) : this.auditJsScript(src, rel);
        for (let x = 0; x < res.errors.length; x++) all_errors.push(res.errors[x]);
        for (let x = 0; x < res.warnings.length; x++) all_warnings.push(res.warnings[x]);
      }

      //Return statement
      return {
        errors: all_errors,
        files_checked: files.length,
        success: all_errors.length === 0,
        warnings: all_warnings
      };
    },

    /**
     * Parses CLI arguments.
     * @alias shell_and_scripts_auditor.parseCliArgs
     *
     * @param {Array<string>} arg0_argv
     *
     * @returns {Object}
     */
    parseCliArgs (arg0_argv) {
      //Convert from parameters
      let argv = Array.isArray(arg0_argv) ? arg0_argv : [];

      //Declare local instance variables
      let out = { json: false, target: "" };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        if (argv[i] === "--json") out.json = true;
        else if (!argv[i].startsWith("--") && !out.target) out.target = argv[i];
      }

      //Return statement
      return out;
    }
  };

  if (require.main === module) {
    let cli = shell_and_scripts_auditor.parseCliArgs(process.argv.slice(2));
    if (!cli.target) {
      console.error("Usage: node audit_shell_and_scripts.js <target> [--json]");
      process.exit(2);
    }
    let res = shell_and_scripts_auditor.auditTarget(cli.target);
    if (cli.json) {
      console.log(JSON.stringify(res, null, 2));
    } else {
      for (let i = 0; i < Math.min(30, res.warnings.length); i++)
        console.log(`[WARN] ${res.warnings[i]}`);
      for (let i = 0; i < Math.min(50, res.errors.length); i++)
        console.error(`[FAIL] ${res.errors[i]}`);
      console.log(`[audit_shell_and_scripts] ${cli.target}: ${res.files_checked} file(s), ${res.errors.length} error(s), ${res.warnings.length} warning(s).`);
    }
    process.exit(res.success ? 0 : 1);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { shell_and_scripts_auditor: shell_and_scripts_auditor };
  }
}
