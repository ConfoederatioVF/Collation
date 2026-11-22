//Import modules
let child_process = require("child_process");
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");
let { StringDecoder } = require("string_decoder");
let { viscount_entity_audit } = require("./viscount_entity_and_continuity_audit");

//Initialise functions
{
  let downstream_ci_cd_verifier = {
    /**
     * Computes bigram Sørensen-Dice similarity between two normalised stems.
     * @alias downstream_ci_cd_verifier.computeBigramDice
     *
     * @param {string} arg0_a
     * @param {string} arg1_b
     *
     * @returns {number}
     */
    computeBigramDice (arg0_a, arg1_b) {
      //Convert from parameters
      let a = String(arg0_a || "");
      let b = String(arg1_b || "");

      //Guard clauses
      if (!a || !b)
        return 0.0;
      if (a === b)
        return 1.0;
      if (a.length < 2 || b.length < 2)
        return 0.0;

      //Declare local instance variables
      let bigrams_a = [];
      let intersection = 0;
      let pool_b = [];

      //Function body
      for (let i = 0; i < a.length - 1; i++)
        bigrams_a.push(a.slice(i, i + 2));
      for (let i = 0; i < b.length - 1; i++)
        pool_b.push(b.slice(i, i + 2));

      for (let i = 0; i < bigrams_a.length; i++) {
        let idx = pool_b.indexOf(bigrams_a[i]);
        if (idx !== -1) {
          intersection++;
          pool_b.splice(idx, 1);
        }
      }

      //Return statement
      return (2.0*intersection)/(bigrams_a.length + (b.length - 1));
    },

    /**
     * Returns true when the declared country/state uses Latin script exclusively across all 14 macro-regions.
     * @alias downstream_ci_cd_verifier.isLatinScriptRegionCountry
     *
     * @param {string} arg0_country
     * @param {Array<number>} [arg1_coords]
     * @param {Object} [arg2_profiles]
     *
     * @returns {boolean}
     */
    isLatinScriptRegionCountry (arg0_country, arg1_coords, arg2_profiles) {
      //Convert from parameters
      let profiles = (arg2_profiles) ? arg2_profiles : viscount_entity_audit.loadSkillProfiles();

      //Return statement
      return viscount_entity_audit.isLatinScriptOnlyCountry(arg0_country, arg1_coords, profiles);
    },

    /**
     * Normalises an entity/place name stem for cross-script matching using global romanisation rules.
     * @alias downstream_ci_cd_verifier.normaliseEntityStem
     *
     * @param {string} arg0_name
     *
     * @returns {string}
     */
    normaliseEntityStem (arg0_name) {
      //Return statement
      return viscount_entity_audit.normaliseEntityStem(arg0_name);
    },

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
        audit_only: false,
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
        else if (tok === "--audit-only")
          args.audit_only = true;
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
      let audit_only = Boolean(options.audit_only);
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
      let continuity_res = viscount_entity_audit.verifyAnnualContinuityAndOrphans(
        target_proj,
        svea_root,
        dataview_root,
        Array.isArray(shard_res.shard_files) ? shard_res.shard_files : [],
        errors
      );
      let meta_quality_res = viscount_entity_audit.verifyCityMetadataQuality(
        target_proj,
        dataview_root,
        Array.isArray(shard_res.shard_files) ? shard_res.shard_files : [],
        errors
      );
      let dv_res = { build_ok: false, cache_warmed: false, meta_versions_present: 0, skipped: audit_only };
      let intellte_res = { cached_rmd: 0, skipped: audit_only, total_rmd: 0, vp_built: false };
      let integrity_res = { checked_cities: 0, matched_cities: 0, skipped: false };

      if (!audit_only) {
        intellte_res = this.verifyIntelltePipelineAndCiCache(target_proj, svea_root, intellte_root, full_build, errors);
        dv_res = this.verifyDataviewCachesAndBuild(dataview_root, errors);
      }

      let indexed_cache_path = path.join(dataview_root, "data/stadester/cache/stadester_2.0_indexed.json");
      if (!audit_only || fs.existsSync(indexed_cache_path)) {
        integrity_res = this.verifyPostIndexEntityIntegrity(
          target_proj,
          dataview_root,
          Array.isArray(shard_res.shard_files) ? shard_res.shard_files : [],
          errors
        );
      } else {
        integrity_res.skipped = true;
      }

      let summary = {
        continuity: continuity_res,
        dataview: dv_res,
        errors: errors,
        integrity: integrity_res,
        intellte: intellte_res,
        metadata_quality: meta_quality_res,
        project: project_key,
        shards: shard_res,
        success: errors.length === 0
      };

      if (errors.length > 0) {
        for (let i = 0; i < errors.length; i++)
          console.error(`[verify_downstream_ci_cd] [FAIL] ${errors[i]}`);
      } else {
        console.log(
          `[verify_downstream_ci_cd] PASS for ${project_key}: shards=${shard_res.dataview_count}, ` +
          `integrity=${integrity_res.matched_cities}, max_yoy=${continuity_res.max_yoy_pct}% (${continuity_res.span[0]}-${continuity_res.span[1]}), ` +
          `rmd_ci_cache=${intellte_res.cached_rmd}/${intellte_res.total_rmd}, dataview_build=${dv_res.skipped ? "SKIPPED" : "OK"}`
        );
      }

      //Return statement
      return summary;
    },

    /**
     * Strips the trailing `-<Country/State>` key suffix from a Stadestér composite city key.
     * @alias downstream_ci_cd_verifier.stripCityCountrySuffix
     *
     * @param {string} arg0_key
     * @param {string} [arg1_country]
     *
     * @returns {string}
     */
    stripCityCountrySuffix (arg0_key, arg1_country) {
      //Convert from parameters
      let country = String(arg1_country || "").trim();
      let key = String(arg0_key || "");

      //Function body
      key = key.replace(/_viscount_regional(?:_\d+)?$/i, "");
      if (country && key.toLowerCase().endsWith("-" + country.toLowerCase()))
        return key.slice(0, key.length - country.length - 1);

      let dash_idx = key.lastIndexOf("-");
      if (dash_idx > 0)
        return key.slice(0, dash_idx);

      //Return statement
      return key;
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
        "let ds = StadesterService.loadDataset('stadester_2.0'); let p = StadesterService.ensureLiteCache('stadester_2.0');",
        "console.log('WARM_LITE_CACHE=' + p);"
      ].join(" ");
      let heap_mb = Math.min(8192, Math.max(2048, Number(process.env.VISCOUNT_MAX_RAM_MB) || 6144));
      let cache_res = child_process.spawnSync(process.execPath, [`--max-old-space-size=${heap_mb}`, "--input-type=module", "-e", cache_script], {
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
      let tsc_res = child_process.spawnSync(process.execPath, [`--max-old-space-size=${heap_mb}`, tsc_bin, "-b"], {
        cwd: dataview_root,
        encoding: "utf8"
      });
      if (tsc_res.status !== 0) {
        errors.push(`Dataview tsc -b failed (exit=${tsc_res.status}): ${(tsc_res.stdout || tsc_res.stderr || "").slice(0, 500)}`);
      } else {
        let vite_res = child_process.spawnSync(process.execPath, [`--max-old-space-size=${heap_mb}`, vite_bin, "build"], {
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
     * Gate 4: Stream-parses `data/stadester/cache/stadester_2.0_indexed.json` in 16 MB chunks
     * to detect entity hijackings (Signature A/B), `_viscount_regional` keys, and foreign-script
     * `other_names` spam in Latin-script countries without hitting V8 string length limits.
     * @alias downstream_ci_cd_verifier.verifyPostIndexEntityIntegrity
     *
     * @param {Object} arg0_proj
     * @param {string} arg1_dataview_root
     * @param {Array<string>} arg2_shard_files
     * @param {Array<string>} arg3_errors
     *
     * @returns {Object}
     */
    verifyPostIndexEntityIntegrity (arg0_proj, arg1_dataview_root, arg2_shard_files, arg3_errors) {
      //Convert from parameters
      let proj = (arg0_proj) ? arg0_proj : {};
      let dataview_root = arg1_dataview_root;
      let shard_files = Array.isArray(arg2_shard_files) ? arg2_shard_files : [];
      let errors = arg3_errors;

      //Declare local instance variables
      let foreign_script_re = /[\u0400-\u04FF\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]/;
      let indexed_path = path.join(dataview_root, "data/stadester/cache/stadester_2.0_indexed.json");
      let latin_foreign_spam = [];
      let matched_cities = 0;
      let profiles = viscount_entity_audit.loadSkillProfiles();
      let proj_countries = new Set();
      let shard_key_set = new Set();
      let sig_a_hijacks = [];
      let sig_b_hijacks = [];
      let viscount_regional_keys = [];

      //Guard clauses
      if (!fs.existsSync(indexed_path)) {
        errors.push(`Post-index integrity check failed: missing ${indexed_path}.`);
        return { matched_cities: 0, skipped: true };
      }

      //Function body
      let raw_countries = Array.isArray(proj.countries) ? proj.countries : [];
      for (let i = 0; i < raw_countries.length; i++)
        proj_countries.add(String(raw_countries[i] || "").trim().toLowerCase());

      for (let i = 0; i < shard_files.length; i++) {
        let shard_abs = path.join(dataview_root, "data/stadester/stadester_2.0", shard_files[i]);
        if (!fs.existsSync(shard_abs)) continue;
        let shard_obj = JSON.parse(fs.readFileSync(shard_abs, "utf8"));
        let s_keys = Object.keys(shard_obj);
        for (let x = 0; x < s_keys.length; x++)
          shard_key_set.add(s_keys[x]);
      }

      let chunk_size = 16*1024*1024;
      let file_stat = fs.statSync(indexed_path);
      let max_chunks = Math.ceil(file_stat.size/chunk_size) + 4;
      let buf = Buffer.allocUnsafe(chunk_size);
      let decoder = new StringDecoder("utf8");
      let fd = fs.openSync(indexed_path, "r");

      let brace_depth = 0;
      let current_key = "";
      let escaped = false;
      let found_cities = false;
      let in_string = false;
      let key_buf = "";
      let phase = "expect_key_or_end";
      let prefix_buf = "";
      let should_collect = false;
      let val_chunks = [];
      let val_slice_start = -1;

      try {
        for (let chunk_idx = 0; chunk_idx < max_chunks; chunk_idx++) {
          let bytes_read = fs.readSync(fd, buf, 0, chunk_size, null);
          let slice = (bytes_read > 0) ? decoder.write(buf.subarray(0, bytes_read)) : decoder.end();
          if (!slice && bytes_read === 0) break;

          let start_pos = 0;
          if (!found_cities) {
            prefix_buf += slice;
            let m = prefix_buf.match(/"cities"\s*:\s*\{/);
            if (!m) {
              if (prefix_buf.length > 64*1024)
                prefix_buf = prefix_buf.slice(-1024);
              if (bytes_read === 0) break;
              continue;
            }
            slice = prefix_buf.slice(m.index + m[0].length);
            prefix_buf = "";
            found_cities = true;
          }

          if (phase === "in_value" && should_collect)
            val_slice_start = 0;

          for (let pos = start_pos; pos < slice.length; pos++) {
            let ch = slice[pos];

            if (phase === "expect_key_or_end") {
              if (ch === '"') {
                phase = "in_key";
                key_buf = "";
                escaped = false;
              } else if (ch === "}") {
                phase = "done";
                break;
              }
            } else if (phase === "in_key") {
              if (escaped) {
                key_buf += ch;
                escaped = false;
              } else if (ch === "\\") {
                key_buf += ch;
                escaped = true;
              } else if (ch === '"') {
                current_key = JSON.parse(`"${key_buf}"`);
                phase = "expect_colon";
              } else {
                key_buf += ch;
              }
            } else if (phase === "expect_colon") {
              if (ch === ":")
                phase = "expect_value";
            } else if (phase === "expect_value") {
              if (ch === "{") {
                phase = "in_value";
                brace_depth = 1;
                in_string = false;
                escaped = false;
                should_collect = shard_key_set.has(current_key) || (current_key.indexOf("_viscount_regional") !== -1);
                if (should_collect) {
                  val_chunks = [];
                  val_slice_start = pos;
                }
              }
            } else if (phase === "in_value") {
              if (in_string) {
                if (escaped)
                  escaped = false;
                else if (ch === "\\")
                  escaped = true;
                else if (ch === '"')
                  in_string = false;
              } else if (ch === '"') {
                in_string = true;
              } else if (ch === "{") {
                brace_depth++;
              } else if (ch === "}") {
                brace_depth--;
                if (brace_depth === 0) {
                  if (should_collect) {
                    val_chunks.push(slice.slice(val_slice_start, pos + 1));
                    let city_obj = JSON.parse(val_chunks.join(""));
                    val_chunks = [];
                    val_slice_start = -1;

                    let city_country = String(city_obj.country || "").trim();
                    let belongs_to_proj = shard_key_set.has(current_key) || proj_countries.has(city_country.toLowerCase());
                    if (belongs_to_proj) {
                      matched_cities++;
                      if (current_key.indexOf("_viscount_regional") !== -1)
                        viscount_regional_keys.push(current_key);

                      if (this.isLatinScriptRegionCountry(city_country, city_obj.coords, profiles)) {
                        let raw_other = city_obj.other_names;
                        let other_arr = Array.isArray(raw_other) ? raw_other : (raw_other ? [raw_other] : []);
                        let has_foreign = false;
                        for (let z = 0; z < other_arr.length; z++) {
                          if (foreign_script_re.test(String(other_arr[z] || ""))) {
                            has_foreign = true;
                            break;
                          }
                        }
                        if (has_foreign)
                          latin_foreign_spam.push(`${current_key} (${city_country})`);
                      }

                      let h_names = Array.isArray(city_obj.historical_names) ? city_obj.historical_names : [];
                      if (h_names.length > 0) {
                        let base_key = this.stripCityCountrySuffix(current_key, city_country);
                        let base_stem = this.normaliseEntityStem(base_key);
                        let city_stem = this.normaliseEntityStem(city_obj.name || "");
                        let equiv_base_city = viscount_entity_audit.areEquivalentExonyms(base_key, city_obj.name || "", profiles);
                        let latest_hn = null;
                        let latest_yf = -99999;

                        for (let z = 0; z < h_names.length; z++) {
                          let rec = h_names[z];
                          if (!rec || !rec.name) continue;
                          let yf = Number(rec.year_frac);
                          if (!Number.isFinite(yf) && rec.date)
                            yf = Number(String(rec.date).split(".")[0]);
                          if (Number.isFinite(yf) && yf >= latest_yf) {
                            latest_yf = yf;
                            latest_hn = rec;
                          }
                        }

                        if (latest_hn && base_stem && city_stem && !equiv_base_city) {
                          let latest_stem = this.normaliseEntityStem(latest_hn.name);
                          let dice_base_latest = viscount_entity_audit.areEquivalentExonyms(base_key, latest_hn.name, profiles) ?
                            1.0 : this.computeBigramDice(base_stem, latest_stem);
                          let dice_city_base = this.computeBigramDice(city_stem, base_stem);
                          let dice_city_latest = viscount_entity_audit.areEquivalentExonyms(city_obj.name || "", latest_hn.name, profiles) ?
                            1.0 : this.computeBigramDice(city_stem, latest_stem);

                          if (latest_yf >= 1995 && dice_base_latest >= 0.80 && dice_city_base < 0.45) {
                            sig_a_hijacks.push(`${current_key} -> ${city_obj.name} (latest ${latest_hn.date || latest_yf}: ${latest_hn.name})`);
                          } else if (latest_yf < 1920 && Number(city_obj.max_year || 0) >= 1950 && dice_city_latest >= 0.80 && dice_city_base < 0.45) {
                            let seen_earlier = false;
                            for (let z = 0; z < h_names.length; z++) {
                              let rec_z = h_names[z];
                              if (!rec_z || !rec_z.name) continue;
                              let yf_z = Number(rec_z.year_frac);
                              if (!Number.isFinite(yf_z) && rec_z.date)
                                yf_z = Number(String(rec_z.date).split(".")[0]);
                              let d_earlier = viscount_entity_audit.areEquivalentExonyms(rec_z.name, base_key, profiles) ?
                                1.0 : this.computeBigramDice(this.normaliseEntityStem(rec_z.name), base_stem);
                              if (Number.isFinite(yf_z) && yf_z < latest_yf && d_earlier >= 0.80) {
                                seen_earlier = true;
                                break;
                              }
                            }
                            if (seen_earlier)
                              sig_b_hijacks.push(`${current_key} -> ${city_obj.name} (max_year=${city_obj.max_year}, latest_hn=${latest_hn.name}@${latest_yf})`);
                          }
                        }
                      }
                    }
                  }
                  should_collect = false;
                  phase = "expect_key_or_end";
                }
              }
            }
          }

          if (phase === "done") break;
          if (phase === "in_value" && should_collect && val_slice_start >= 0) {
            val_chunks.push(slice.slice(val_slice_start));
            val_slice_start = 0;
          }
          if (bytes_read === 0) break;
        }
      } finally {
        fs.closeSync(fd);
      }

      if (!found_cities || matched_cities === 0)
        errors.push(`Post-index integrity check matched 0 cities for ${proj.key} in ${indexed_path}.`);
      if (viscount_regional_keys.length > 0)
        errors.push(`Post-index entity check found ${viscount_regional_keys.length} forbidden _viscount_regional key(s): ${viscount_regional_keys.slice(0, 5).join(", ")}`);
      if (latin_foreign_spam.length > 0)
        errors.push(`Post-index foreign-script other_names spam in Latin-script cities (${latin_foreign_spam.length}): ${latin_foreign_spam.slice(0, 5).join(", ")}`);
      if (sig_a_hijacks.length > 0)
        errors.push(`Signature A modern suburb hijacking (${sig_a_hijacks.length}): ${sig_a_hijacks.slice(0, 5).join(", ")}`);
      if (sig_b_hijacks.length > 0)
        errors.push(`Signature B defunct annex hijacking (${sig_b_hijacks.length}): ${sig_b_hijacks.slice(0, 5).join(", ")}`);

      //Return statement
      return {
        foreign_spam_count: latin_foreign_spam.length,
        matched_cities: matched_cities,
        sig_a_count: sig_a_hijacks.length,
        sig_b_count: sig_b_hijacks.length,
        viscount_regional_count: viscount_regional_keys.length
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
      return {
        dataview_count: counts.dataview_count,
        shard_files: shard_files,
        transform_count: counts.transform_count,
        vis_count: counts.vis_count
      };
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
