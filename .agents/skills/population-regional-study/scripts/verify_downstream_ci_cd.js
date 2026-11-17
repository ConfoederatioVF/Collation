//Import modules
let child_process = require("child_process");
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");

//Initialise functions
{
  let downstream_ci_cd_verifier = {
    /**
     * Parses CLI flags for `verify_downstream_ci_cd.js`.
     * @alias downstream_ci_cd_verifier.parseCliArgs
     *
     * @param {Array<string>} arg0_argv
     *
     * @returns {Object}
     */
    parseCliArgs (arg0_argv) {
      //Convert from parameters
      let argv = Array.isArray(arg0_argv) ? arg0_argv : [];

      //Declare local instance variables
      let args = {
        dataview_root: "",
        full_build: false,
        intellte_root: "",
        project: "",
        svea_root: ""
      };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok.startsWith("--project="))
          args.project = tok.slice(10).trim().toUpperCase();
        else if (tok.startsWith("--svea-root="))
          args.svea_root = tok.slice(12).trim();
        else if (tok.startsWith("--intellte-root="))
          args.intellte_root = tok.slice(16).trim();
        else if (tok.startsWith("--dataview-root="))
          args.dataview_root = tok.slice(16).trim();
        else if (tok === "--full-build")
          args.full_build = true;
      }

      //Return statement
      return args;
    },

    /**
     * Executes all three cross-repository CI/CD verification gates for an Operation Viscount region.
     * @alias downstream_ci_cd_verifier.runVerification
     *
     * @param {Object} [arg0_options]
     *  @param {string} arg0_options.project
     *  @param {string} [arg0_options.svea_root]
     *  @param {string} [arg0_options.intellte_root]
     *  @param {string} [arg0_options.dataview_root]
     *  @param {boolean} [arg0_options.full_build=false]
     *
     * @returns {Object} Gate verification summary
     */
    runVerification (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let dataview_root = (options.dataview_root) ? path.resolve(options.dataview_root) :
        (process.env.DATAVIEW_ROOT ? path.resolve(process.env.DATAVIEW_ROOT) :
          path.resolve(__dirname, "../../../../../Project 1436 - Dataview"));
      let errors = [];
      let full_build = Boolean(options.full_build);
      let intellte_root = (options.intellte_root) ? path.resolve(options.intellte_root) :
        (process.env.INTELLTE_ROOT ? path.resolve(process.env.INTELLTE_ROOT) :
          path.resolve("E:/Active Projects/Project 1746 - Intellte"));
      let project_key = String(options.project || "").trim().toUpperCase();
      let svea_root = (options.svea_root) ? path.resolve(options.svea_root) :
        path.resolve(__dirname, "../../../..");

      //Guard clauses
      if (!project_key) {
        console.error("[verify_downstream_ci_cd] Missing required --project=<KEY> argument.");
        return { errors: ["Missing --project"], success: false };
      }

      let prec_path = path.join(svea_root, "histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5");
      if (!fs.existsSync(prec_path)) {
        console.error(`[verify_downstream_ci_cd] Registry missing: ${prec_path}`);
        return { errors: [`Missing registry: ${prec_path}`], success: false };
      }

      //Function body
      let prec_obj = JSON5.parse(fs.readFileSync(prec_path, "utf8"));
      let projects = Array.isArray(prec_obj.projects) ? prec_obj.projects : [];
      let target_proj = null;

      for (let i = 0; i < projects.length; i++) {
        if (String(projects[i].key || "").toUpperCase() === project_key) {
          target_proj = projects[i];
          break;
        }
      }
      if (!target_proj) {
        console.error(`[verify_downstream_ci_cd] Unknown Viscount project key: ${project_key}`);
        return { errors: [`Unknown project: ${project_key}`], success: false };
      }

      let shard_res = this.verifySveaToDataviewShards(target_proj, svea_root, dataview_root, errors);
      let intellte_res = this.verifyIntelltePipelineAndCiCache(target_proj, svea_root, intellte_root, full_build, errors);
      let dv_res = this.verifyDataviewCachesAndBuild(dataview_root, errors);

      let summary = {
        dataview: dv_res,
        errors: errors,
        intellte: intellte_res,
        project: project_key,
        shards: shard_res,
        success: errors.length === 0
      };

      if (errors.length > 0) {
        for (let i = 0; i < errors.length; i++)
          console.error(`[verify_downstream_ci_cd] [FAIL] ${errors[i]}`);
      } else {
        console.log(`[verify_downstream_ci_cd] PASS for ${project_key}: shards=${shard_res.dataview_count}, rmd_ci_cache=${intellte_res.cached_rmd}/${intellte_res.total_rmd}, dataview_build=OK`);
      }

      //Return statement
      return summary;
    },

    /**
     * Gate 3: Verifies per-version Dataview metadata isolation, re-warms `stadester_2.0` caches
     * and runs Dataview `tsc -b` + `vite build` production compilation.
     * @alias downstream_ci_cd_verifier.verifyDataviewCachesAndBuild
     *
     * @param {string} arg0_dataview_root
     * @param {Array<string>} arg1_errors
     *
     * @returns {Object}
     */
    verifyDataviewCachesAndBuild (arg0_dataview_root, arg1_errors) {
      //Convert from parameters
      let dataview_root = arg0_dataview_root;
      let errors = arg1_errors;

      //Declare local instance variables
      let build_ok = false;
      let cache_warmed = false;
      let meta_versions_present = 0;

      //Guard clauses
      if (!fs.existsSync(dataview_root)) {
        errors.push(`Dataview repository root not found: ${dataview_root}`);
        return { build_ok: false, cache_warmed: false, meta_versions_present: 0 };
      }

      //Function body
      let version_meta_paths = [
        path.join(dataview_root, "data/stadester/stadester_2.0/city_metadata.json"),
        path.join(dataview_root, "data/stadester/stadester_1.1/city_metadata.json"),
        path.join(dataview_root, "data/stadester/stadester_1.0/city_metadata.json")
      ];
      for (let i = 0; i < version_meta_paths.length; i++) {
        if (fs.existsSync(version_meta_paths[i]))
          meta_versions_present++;
        else
          errors.push(`Missing Dataview per-version metadata file: ${version_meta_paths[i]}`);
      }

      let cache_script = [
        "import { StadesterService } from './core/server/stadester_service.ts';",
        "let p = StadesterService.ensureLiteCache('stadester_2.0');",
        "console.log('WARM_LITE_CACHE=' + p);"
      ].join(" ");
      let cache_res = child_process.spawnSync(process.execPath, ["--input-type=module", "-e", cache_script], {
        cwd: dataview_root,
        encoding: "utf8"
      });
      if (cache_res.status !== 0) {
        errors.push(`Dataview stadester_2.0 cache re-warming failed (exit=${cache_res.status}): ${(cache_res.stderr || "").slice(0, 400)}`);
      } else {
        let lite_path = path.join(dataview_root, "data/stadester/cache/stadester_2.0_lite.json");
        let idx_path = path.join(dataview_root, "data/stadester/cache/stadester_2.0_indexed.json");
        if (fs.existsSync(lite_path) && fs.existsSync(idx_path))
          cache_warmed = true;
        else
          errors.push("Dataview cache re-warming completed without producing both stadester_2.0_lite.json and stadester_2.0_indexed.json.");
      }

      let tsc_bin = path.join(dataview_root, "node_modules/typescript/bin/tsc");
      let vite_bin = path.join(dataview_root, "node_modules/vite/bin/vite.js");
      let tsc_res = child_process.spawnSync(process.execPath, ["--max-old-space-size=16384", tsc_bin, "-b"], {
        cwd: dataview_root,
        encoding: "utf8"
      });
      if (tsc_res.status !== 0) {
        errors.push(`Dataview tsc -b failed (exit=${tsc_res.status}): ${(tsc_res.stdout || tsc_res.stderr || "").slice(0, 500)}`);
      } else {
        let vite_res = child_process.spawnSync(process.execPath, ["--max-old-space-size=16384", vite_bin, "build"], {
          cwd: dataview_root,
          encoding: "utf8"
        });
        let dist_index = path.join(dataview_root, "dist/index.html");
        if (vite_res.status !== 0 || !fs.existsSync(dist_index))
          errors.push(`Dataview vite build failed (exit=${vite_res.status}): ${(vite_res.stderr || "").slice(0, 500)}`);
        else
          build_ok = true;
      }

      //Return statement
      return {
        build_ok: build_ok,
        cache_warmed: cache_warmed,
        meta_versions_present: meta_versions_present
      };
    },

    /**
     * Gate 2: Runs Intellte sync + incremental compilation and verifies 100% LF-normalised
     * `rmd_dom` cache coverage required by GitHub Actions Linux builds.
     * @alias downstream_ci_cd_verifier.verifyIntelltePipelineAndCiCache
     *
     * @param {Object} arg0_proj
     * @param {string} arg1_svea_root
     * @param {string} arg2_intellte_root
     * @param {boolean} arg3_full_build
     * @param {Array<string>} arg4_errors
     *
     * @returns {Object}
     */
    verifyIntelltePipelineAndCiCache (arg0_proj, arg1_svea_root, arg2_intellte_root, arg3_full_build, arg4_errors) {
      //Convert from parameters
      let proj = arg0_proj;
      let svea_root = arg1_svea_root;
      let intellte_root = arg2_intellte_root;
      let full_build = Boolean(arg3_full_build);
      let errors = arg4_errors;

      //Declare local instance variables
      let cached_rmd = 0;
      let concept_id = String(proj.intellte_concept_id || "");
      let sync_script = path.join(intellte_root, "core/framework/node/sync_viscount_region.js");
      let total_rmd = 0;
      let vp_built = false;

      //Guard clauses
      if (!fs.existsSync(sync_script)) {
        errors.push(`Intellte sync script not found: ${sync_script}`);
        return { cached_rmd: 0, total_rmd: 0, vp_built: false };
      }

      //Function body
      let sync_res = child_process.spawnSync(process.execPath, [
        sync_script,
        `--project=${proj.key}`,
        `--svea-root=${svea_root}`,
        "--build"
      ], {
        cwd: intellte_root,
        stdio: "inherit"
      });
      if (sync_res.status !== 0) {
        errors.push(`Intellte sync_viscount_region --build failed for ${proj.key} (exit=${sync_res.status}).`);
        return { cached_rmd: 0, total_rmd: 0, vp_built: false };
      }

      let worker_jobs_dir = path.join(intellte_root, "docs/.vitepress/cache/rmd_dom/worker_jobs");
      if (fs.existsSync(worker_jobs_dir))
        errors.push(`Stale tracked temp directory present inside rmd_dom cache: ${worker_jobs_dir}`);

      let record_index_md = path.join(intellte_root, "docs/records", concept_id, "index.md");
      if (!fs.existsSync(record_index_md))
        errors.push(`Missing generated VitePress index markdown for ${concept_id}: ${record_index_md}`);

      let { IntellteDiscovery } = require(path.join(intellte_root, "core/framework/node/A_discover_records.js"));
      let { MarkdownRenderer } = require(path.join(intellte_root, "core/framework/node/MarkdownRenderer.js"));
      let manifest = IntellteDiscovery.A_discoverRecords(intellte_root, { only_concept_id: concept_id });
      let renderer = new MarkdownRenderer({ root_dir: intellte_root });
      let rec_list = Array.isArray(manifest && manifest.records) ? manifest.records : [];

      for (let i = 0; i < rec_list.length; i++) {
        let versions = Array.isArray(rec_list[i].versions) ? rec_list[i].versions : [];
        for (let x = 0; x < versions.length; x++) {
          let ver = versions[x];
          if (!ver.has_rmd || !ver.rmd_abs) continue;
          total_rmd++;
          if (!fs.existsSync(ver.rmd_abs)) {
            errors.push(`Missing synced Rmd file in Intellte: ${ver.rmd_abs}`);
            continue;
          }
          let fm = renderer.parseFrontmatter(fs.readFileSync(ver.rmd_abs, "utf8")).frontmatter || {};
          let cache_info = renderer.getRmdCacheKeyInfo(ver.rmd_abs, {
            artefact_base_url: ver.artefact_base_url,
            has_hero_figure: Boolean(fm.hero_figure)
          });
          if (fs.existsSync(cache_info.cache_file) && renderer.isValidEvaluatedMarkdown(fs.readFileSync(cache_info.cache_file, "utf8")))
            cached_rmd++;
          else
            errors.push(`Missing valid Linux-CI LF rmd_dom cache for ${concept_id}/${ver.version}: expected ${cache_info.cache_file}`);
        }
      }

      if (total_rmd === 0)
        errors.push(`No compiled Rmd versions discovered in Intellte for ${concept_id}.`);

      if (full_build) {
        let vp_bin = path.join(intellte_root, "node_modules/vitepress/bin/vitepress.js");
        let vp_res = child_process.spawnSync(process.execPath, [vp_bin, "build", "docs"], {
          cwd: intellte_root,
          encoding: "utf8"
        });
        let vp_dist_index = path.join(intellte_root, "docs/.vitepress/dist/records", concept_id, "index.html");
        if (vp_res.status !== 0 || !fs.existsSync(vp_dist_index))
          errors.push(`Intellte vitepress build docs failed or omitted ${vp_dist_index} (exit=${vp_res.status}).`);
        else
          vp_built = true;
      }

      //Return statement
      return {
        cached_rmd: cached_rmd,
        total_rmd: total_rmd,
        vp_built: vp_built
      };
    },

    /**
     * Gate 1: Verifies SVEA transform/visualisation and Dataview Stadestér 2.0 manifest parity
     * and audits the regional shard against `.sources` schema compliance.
     * @alias downstream_ci_cd_verifier.verifySveaToDataviewShards
     *
     * @param {Object} arg0_proj
     * @param {string} arg1_svea_root
     * @param {string} arg2_dataview_root
     * @param {Array<string>} arg3_errors
     *
     * @returns {Object}
     */
    verifySveaToDataviewShards (arg0_proj, arg1_svea_root, arg2_dataview_root, arg3_errors) {
      //Convert from parameters
      let proj = arg0_proj;
      let svea_root = arg1_svea_root;
      let dataview_root = arg2_dataview_root;
      let errors = arg3_errors;

      //Declare local instance variables
      let counts = { dataview_count: -1, transform_count: -1, vis_count: -1 };
      let manifest_dirs = [
        { key: "transform_count", path: path.join(svea_root, "histmap/3.data_transform/population_Stadester.transform/stadester/stadester_manifest.json") },
        { key: "vis_count", path: path.join(svea_root, "histmap/5.data_visualisation/stadester/stadester_2.0/stadester_manifest.json") },
        { key: "dataview_count", path: path.join(dataview_root, "data/stadester/stadester_2.0/stadester_manifest.json") }
      ];
      let shard_files = [];

      //Function body
      for (let i = 0; i < manifest_dirs.length; i++) {
        let item = manifest_dirs[i];
        if (!fs.existsSync(item.path)) {
          errors.push(`Missing Stadestér 2.0 manifest: ${item.path}`);
          continue;
        }
        let manifest = JSON.parse(fs.readFileSync(item.path, "utf8"));
        if (String(manifest.version || "") !== "2.0")
          errors.push(`Expected manifest version "2.0" in ${item.path}, found ${JSON.stringify(manifest.version)}`);

        let regions = Array.isArray(manifest.regions) ? manifest.regions : [];
        let reg_entry = null;
        for (let x = 0; x < regions.length; x++) {
          if (String(regions[x].key || "").toUpperCase() === proj.key) {
            reg_entry = regions[x];
            break;
          }
        }
        if (!reg_entry) {
          errors.push(`Project ${proj.key} absent from manifest ${item.path}`);
        } else {
          counts[item.key] = Number(reg_entry.count) || 0;
          if (item.key === "dataview_count")
            shard_files = Array.isArray(reg_entry.files) ? reg_entry.files : [];
        }
      }

      if (counts.transform_count >= 0 && counts.vis_count >= 0 && counts.transform_count !== counts.vis_count)
        errors.push(`Shard count mismatch for ${proj.key}: transform=${counts.transform_count} vs vis=${counts.vis_count}`);
      if (counts.transform_count >= 0 && counts.dataview_count >= 0 && counts.transform_count !== counts.dataview_count)
        errors.push(`Shard count mismatch for ${proj.key}: transform=${counts.transform_count} vs dataview=${counts.dataview_count}`);

      let exhaust_script = path.join(svea_root, ".agents/skills/population-regional-study/scripts/verify_gazetteer_exhaustiveness.py");
      for (let i = 0; i < shard_files.length; i++) {
        let shard_abs = path.join(dataview_root, "data/stadester/stadester_2.0", shard_files[i]);
        if (!fs.existsSync(shard_abs)) {
          errors.push(`Missing Dataview shard file: ${shard_abs}`);
          continue;
        }
        let audit_res = child_process.spawnSync("python", [
          exhaust_script,
          shard_abs,
          "--require-sources",
          "--mode=compiled"
        ], {
          cwd: svea_root,
          encoding: "utf8"
        });
        if (audit_res.status !== 0)
          errors.push(`verify_gazetteer_exhaustiveness failed on ${shard_abs}: ${(audit_res.stderr || audit_res.stdout || "").slice(0, 400)}`);
      }

      //Return statement
      return counts;
    }
  };

  if (require.main === module) {
    let cli_args = downstream_ci_cd_verifier.parseCliArgs(process.argv.slice(2));
    let summary = downstream_ci_cd_verifier.runVerification(cli_args);
    process.exit(summary.success ? 0 : 1);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { downstream_ci_cd_verifier: downstream_ci_cd_verifier };
  }
}
