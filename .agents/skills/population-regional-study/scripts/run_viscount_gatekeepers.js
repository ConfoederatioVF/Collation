//Import modules
let child_process = require("child_process");
let fs = require("fs");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");

//Initialise functions
{
  let viscount_gatekeeper_runner = {
    /**
     * Parses CLI flags for the unified Operation Viscount gatekeeper runner.
     * @alias viscount_gatekeeper_runner.parseCliArgs
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
        project: "",
        require_compiled_pdfs: false,
        require_visual_check: false,
        stage: "ALL",
        svea_root: ""
      };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok === "--project" && i + 1 < argv.length) out.project = argv[++i].toUpperCase();
        else if (tok.startsWith("--project=")) out.project = tok.slice(10).toUpperCase();
        else if (tok === "--stage" && i + 1 < argv.length) out.stage = argv[++i].toUpperCase();
        else if (tok.startsWith("--stage=")) out.stage = tok.slice(8).toUpperCase();
        else if (tok === "--svea-root" && i + 1 < argv.length) out.svea_root = argv[++i];
        else if (tok.startsWith("--svea-root=")) out.svea_root = tok.slice(12);
        else if (tok === "--require-visual-check") out.require_visual_check = true;
        else if (tok === "--require-compiled-pdfs") out.require_compiled_pdfs = true;
      }

      //Return statement
      return out;
    },

    /**
     * Executes one Node.js gatekeeper script synchronously and captures timing + exit status.
     * @alias viscount_gatekeeper_runner.runStep
     *
     * @param {string} arg0_label
     * @param {string} arg1_script
     * @param {Array<string>} arg2_args
     * @param {string} arg3_cwd
     *
     * @returns {{ elapsed_ms: number, label: string, ok: boolean }}
     */
    runStep (arg0_label, arg1_script, arg2_args, arg3_cwd) {
      //Convert from parameters
      let args = Array.isArray(arg2_args) ? arg2_args : [];
      let cwd = arg3_cwd;
      let label = arg0_label;
      let script = path.join(__dirname, arg1_script);

      //Function body
      let t0 = Date.now();
      console.log(`\n=== [${label}] node ${arg1_script} ${args.join(" ")} ===`);
      let res = child_process.spawnSync(process.execPath, [script].concat(args), {
        cwd: cwd,
        stdio: "inherit"
      });
      let elapsed = Date.now() - t0;
      let ok = res.status === 0;
      console.log(`=== [${label}] ${ok ? "PASS" : "FAIL"} (${elapsed} ms) ===`);

      //Return statement
      return { elapsed_ms: elapsed, label: label, ok: ok };
    },

    /**
     * Runs the requested Operation Viscount stage(s) (`A`, `B`, `C`, `D`, `E`, `F`, `S`, or `ALL`) for a macro-region.
     * @alias viscount_gatekeeper_runner.runStages
     *
     * @param {Object} arg0_cli
     *
     * @returns {{ results: Array<Object>, success: boolean }}
     */
    runStages (arg0_cli) {
      //Convert from parameters
      let cli = arg0_cli;
      let project = String(cli.project || "").toUpperCase();
      let stage = String(cli.stage || "ALL").toUpperCase();
      let svea_root = cli.svea_root ? path.resolve(cli.svea_root) : (viscount_audit_utils.findSveaRoot(__dirname) || path.resolve(__dirname, "../../../.."));

      //Declare local instance variables
      let proj_dir = path.join(svea_root, "histmap/1.data_raw/population_regional", project);
      let results = [];
      let stage_set = new Set(stage.split(",").map(function (arg0_t) { return arg0_t.trim(); }).filter(Boolean));
      let wants = function (arg0_s) { return stage === "ALL" || stage_set.has(arg0_s); };

      //Guard clauses
      if (!project || !fs.existsSync(proj_dir)) {
        console.error(`[run_viscount_gatekeepers] Project directory not found for key \`${project}\`: ${proj_dir}`);
        return { results: [], success: false };
      }

      //Function body
      if (wants("S")) {
        results.push(this.runStep("S: Shell & Script Resources", "audit_shell_and_scripts.js", [proj_dir], svea_root));
        results.push(this.runStep("S: Orphan Process Check", "run_bounded.js", ["--audit-orphans"], svea_root));
      }

      if (wants("A"))
        results.push(this.runStep("A: Areal Masks", "audit_areal_masks.js", [proj_dir, "--require-auditor-signoff"], svea_root));

      if (wants("B")) {
        let shared_dir = path.join(proj_dir, "_shared");
        if (fs.existsSync(shared_dir)) {
          let domains = fs.readdirSync(shared_dir).filter(function (arg0_d) {
            return arg0_d.startsWith("sites_") && fs.statSync(path.join(shared_dir, arg0_d)).isDirectory();
          });
          for (let i = 0; i < domains.length; i++) {
            let d_path = path.join(shared_dir, domains[i]);
            results.push(this.runStep(`B1/B3: Kriging Sharpness (${domains[i]})`, "audit_kriging_sharpness.js", [d_path], svea_root));
            let k_dir = path.join(d_path, "1.kriged_rasters");
            if (fs.existsSync(k_dir))
              results.push(this.runStep(`B2: Border Cliffs (${domains[i]})`, "audit_border_cliffs.js", [k_dir], svea_root));
          }
        }
      }

      if (wants("C"))
        results.push(this.runStep("C: Gazetteer Exhaustiveness", "verify_gazetteer_exhaustiveness.js", ["--project-dir", proj_dir, "--require-sources"], svea_root));

      if (wants("D")) {
        results.push(this.runStep("D1: Academic Prose", "audit_academic_prose.js", [proj_dir], svea_root));
        let d3_args = [proj_dir, "--mode", "project"];
        if (cli.require_visual_check) d3_args.push("--require-visual-check");
        if (cli.require_compiled_pdfs) d3_args.push("--require-compiled-pdfs");
        results.push(this.runStep("D2/D3: Rmd, Bib, Figures & PDFs", "audit_rmd_and_bib_calibre.js", d3_args, svea_root));
      }

      if (wants("E"))
        results.push(this.runStep("E: Velkscala Reconciliation", "audit_velkscala_reconciliation.js", ["--project", project], svea_root));

      if (wants("F")) {
        results.push(this.runStep("F: City Metadata Audit", "audit_city_metadata.js", [`--project=${project}`], svea_root));
        results.push(this.runStep("F: Downstream CI/CD", "verify_downstream_ci_cd.js", [`--project=${project}`], svea_root));
      }

      let failed = results.filter(function (arg0_r) { return !arg0_r.ok; });
      let total_ms = results.reduce(function (arg0_a, arg1_b) { return arg0_a + arg1_b.elapsed_ms; }, 0);
      console.log(`\n[run_viscount_gatekeepers] ${project} stage=${stage}: ${results.length - failed.length}/${results.length} passed (${total_ms} ms total).`);

      //Return statement
      return { results: results, success: failed.length === 0 };
    }
  };

  if (require.main === module) {
    let cli = viscount_gatekeeper_runner.parseCliArgs(process.argv.slice(2));
    if (!cli.project) {
      console.error("Usage: node run_viscount_gatekeepers.js --project <KEY> [--stage A|B|C|D|E|F|S|ALL] [--require-visual-check] [--require-compiled-pdfs]");
      process.exit(2);
    }
    let res = viscount_gatekeeper_runner.runStages(cli);
    process.exit(res.success ? 0 : 1);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { viscount_gatekeeper_runner: viscount_gatekeeper_runner };
  }
}
