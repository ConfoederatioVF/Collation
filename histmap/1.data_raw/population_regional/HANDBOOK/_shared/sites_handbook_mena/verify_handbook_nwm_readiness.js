//Import modules
let fs = require("fs");
let path = require("path");

global.fs = fs;
global.JSON5 = require("json5");
global.path = path;
global.pngjs = require("pngjs");

let PROJECT_ROOT = path.resolve(__dirname, "../../../../../..");
global.h1 = path.join(PROJECT_ROOT, "histmap/1.data_raw");
global.h2 = path.join(PROJECT_ROOT, "histmap/2.data_cleaning");
global.h3 = path.join(PROJECT_ROOT, "histmap/3.data_transform");

require(path.join(PROJECT_ROOT, "histmap/2.data_cleaning/population_Stadester/StadesterPartitionIO.js"));
require(path.join(PROJECT_ROOT, "histmap/3.data_transform/population_Substrata.viscount/ViscountSubstrataSeamBlend.js"));
require(path.join(PROJECT_ROOT, "histmap/3.data_transform/population_Substrata.viscount/ViscountSubstrataMosaic.js"));
require(path.join(PROJECT_ROOT, "histmap/3.data_transform/population_Substrata.viscount/ViscountSubstrataPipeline.js"));

//Initialise functions
{
  /**
   * Read-only NWM Stage A compositing & inter-Viscount seam dry-run verifier for Project HANDBOOK.
   * Confirms `ViscountSubstrataPipeline` discovers HANDBOOK (`z_priority: 9`), resolves all z-index locks
   * cleanly with SARAY (8), INDUS (5), JADE (4) and POLARIS (2), and composites the 5 Gatekeeper C2
   * benchmark years (`-2000, 0, 1000, 1500, 1900`) into an isolated local QA directory without mutating
   * global Stadestér, Velkscala or Substrata production rasters.
   *
   * @class HandbookNwmReadinessVerifier
   */
  global.HandbookNwmReadinessVerifier = class {
    static BENCHMARK_YEARS = [-2000, 0, 1000, 1500, 1900];

    /**
     * Executes isolated NWM Stage A discovery and 5-year seam compositing into `seam_qa_composed/`.
     * @alias HandbookNwmReadinessVerifier.run
     *
     * @returns {Promise<Object>}
     */
    static async run () {
      let t0 = Date.now();
      let qa_dir = path.join(__dirname, "seam_qa_composed");
      let prod_r2 = path.join(PROJECT_ROOT, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_2.scaled_to_regions");
      let keep_existing = process.argv.includes("--keep-existing");
      let proj_arg = process.argv.find(function (arg0_a) { return arg0_a.startsWith("--projects="); });
      let only_projects = proj_arg ? proj_arg.slice(11).split(",").map(function (arg0_s) { return arg0_s.trim().toUpperCase(); }).filter(Boolean) :
        ["HANDBOOK", "SARAY", "INDUS", "JADE", "POLARIS"];

      if (!fs.existsSync(qa_dir)) fs.mkdirSync(qa_dir, { recursive: true });
      if (!keep_existing) {
        for (let i = 0; i < this.BENCHMARK_YEARS.length; i++) {
          let fn = `popc_${this.BENCHMARK_YEARS[i]}.png`;
          let src = path.join(prod_r2, fn);
          let dst = path.join(qa_dir, fn);

          if (fs.existsSync(src)) fs.copyFileSync(src, dst);
        }
      }

      let discovery = global.ViscountSubstrataPipeline.A_discoverActiveViscountContexts({
        project_root: PROJECT_ROOT
      });
      let hb_ctx = discovery.contexts.find(function (arg0_c) { return arg0_c.key === "HANDBOOK"; });

      if (!hb_ctx) {
        console.error("[HandbookNwmReadinessVerifier] HANDBOOK was not discovered by ViscountSubstrataPipeline!");
        process.exit(1);
      }

      let res = await global.ViscountSubstrataPipeline.B_processOrderedProjects(discovery, {
        only_projects: only_projects,
        output_folder: qa_dir,
        years: this.BENCHMARK_YEARS
      });

      //Return statement
      return {
        discovered_projects: discovery.contexts.map(function (arg0_c) {
          return { key: arg0_c.key, n_valid: arg0_c.n_valid, order: arg0_c.order, superseded: arg0_c.superseded_pixel_count || 0, z_priority: arg0_c.z_priority };
        }),
        elapsed_seconds: Number(((Date.now() - t0)/1000).toFixed(2)),
        qa_dir: qa_dir,
        summaries: Object.keys(res.project_summaries || {})
      };
    }
  };
}

if (require.main === module) {
  global.HandbookNwmReadinessVerifier.run().then(function (arg0_out) {
    console.log(JSON.stringify(arg0_out, null, 2));
  }).catch(function (arg0_err) {
    console.error(arg0_err);
    process.exit(1);
  });
}
