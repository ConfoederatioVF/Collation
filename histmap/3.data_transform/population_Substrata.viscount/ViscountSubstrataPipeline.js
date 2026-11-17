//Import modules
let fs = global.fs || require("fs");
let JSON5 = global.JSON5 || require("json5");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

if (!global.StadesterPartitionIO && typeof require !== "undefined") {
  try { require(path.resolve(__dirname, "../../2.data_cleaning/population_Stadester/StadesterPartitionIO.js")); } catch (e) {}
}
if (!global.ViscountSubstrataMosaic && typeof require !== "undefined") {
  try { require(path.join(__dirname, "ViscountSubstrataMosaic.js")); } catch (e) {}
}
if (!global.population_Substrata_russia && typeof require !== "undefined") {
  try { require(path.resolve(__dirname, "../population_Substrata.russia/population_Substrata_russia.js")); } catch (e) {}
}

//Initialise functions
{
  /**
   * Master coordinator for Operation Viscount regional population substrata calibration and border resolution.
   * Discovers all registered Viscount configs (`config/*.json5` + `2.data_cleaning/population_Stadester/config/viscount_precedence.json5`),
   * evaluates active projects in strict inverse (`z-index`) priority order (`z_priority = order`: `14` down to `1`),
   * applies `ViscountSubstrataMosaic.resolveMultiProjectZIndexLocks()` across shared frontiers, and preserves
   * calibrated Viscount domains across downstream global scaling and GHSL interpolation steps.
   *
   * @class ViscountSubstrataPipeline
   */
  global.ViscountSubstrataPipeline = class {
    /**
     * Step A: Discovers active Viscount substrata configs and loads their pixel mask contexts
     * sorted descending by `z_priority` (`14 -> 1`).
     * @alias ViscountSubstrataPipeline.A_discoverActiveViscountContexts
     *
     * @param {Object} [arg0_options]
     *  @param {string} [arg0_options.project_root]
     *
     * @returns {Object} `{ contexts: Array<Object>, owner_z_grid: Uint8Array, lock_stats: Array<Object>, root_dir: string }`
     */
    static A_discoverActiveViscountContexts (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let config_dir = path.join(__dirname, "config");
      let contexts = [];
      let lock_result;
      let registry = (global.StadesterPartitionIO) ?
        global.StadesterPartitionIO.loadPrecedenceRegistry(options.precedence_config_path) : { projects_by_key: {} };
      let root_dir = (options.project_root) ? options.project_root : ((fs.existsSync("./histmap/1.data_raw")) ?
        path.resolve(".") : path.resolve(__dirname, "../../.."));

      //Guard clauses
      if (!fs.existsSync(config_dir)) {
        console.error(`[ViscountSubstrataPipeline] Missing config directory: ${config_dir}`);
        return { contexts: [], lock_stats: [], owner_z_grid: null, root_dir: root_dir };
      }

      //Function body
      let cfg_files = fs.readdirSync(config_dir).filter(function (arg0_f) {
        return arg0_f.endsWith(".json5") || arg0_f.endsWith(".json");
      });

      let descriptors = [];
      for (let i = 0; i < cfg_files.length; i++) {
        let abs_cfg = path.join(config_dir, cfg_files[i]);
        try {
          let raw = JSON5.parse(fs.readFileSync(abs_cfg, "utf8"));
          let proj_key = String(raw.key || "").toUpperCase();
          let reg_proj = (registry.projects_by_key && registry.projects_by_key[proj_key]) ? registry.projects_by_key[proj_key] : {};
          descriptors.push({
            ...reg_proj,
            ...raw,
            key: proj_key,
            order: Number(raw.order || reg_proj.order || 1),
            z_priority: Number(raw.z_priority || reg_proj.z_priority || raw.order || reg_proj.order || 1)
          });
        } catch (e) {
          console.error(`[ViscountSubstrataPipeline] Failed to parse config ${abs_cfg}:`, e);
        }
      }

      //Sort strictly descending by z_priority (14 -> 1)
      descriptors.sort(function (arg0_a, arg1_b) {
        return (arg1_b.z_priority || arg1_b.order || 0) - (arg0_a.z_priority || arg0_a.order || 0);
      });

      for (let i = 0; i < descriptors.length; i++) {
        let desc = descriptors[i];
        let manifest_abs = desc.areal_masks_manifest ? path.resolve(root_dir, desc.areal_masks_manifest) : "";
        if (!manifest_abs || !fs.existsSync(manifest_abs)) continue;

        let ctx = null;
        if (desc.pipeline_mode === "polaris_russia_delegate" && typeof global.population_Substrata_russia !== "undefined") {
          ctx = global.population_Substrata_russia.A_loadManifestAndMasks({
            config_path: manifest_abs,
            project_root: root_dir,
            ...options
          });
          if (ctx) {
            ctx.key = desc.key;
            ctx.order = desc.order;
            ctx.pipeline_mode = "polaris_russia_delegate";
            ctx.seam_feather_px = desc.seam_feather_px || 24;
            ctx.z_priority = desc.z_priority;
          }
        } else {
          ctx = global.ViscountSubstrataMosaic.loadGenericProjectContext(desc, {
            project_root: root_dir,
            ...options
          });
        }

        if (ctx && ctx.n_valid > 0)
          contexts.push(ctx);
      }

      lock_result = global.ViscountSubstrataMosaic.resolveMultiProjectZIndexLocks(contexts, options);

      //Return statement
      return {
        contexts: contexts,
        lock_stats: lock_result.stats,
        owner_z_grid: lock_result.owner_z_grid,
        root_dir: root_dir
      };
    }


    /**
     * Step B: Evaluates calibrated substrata mosaics across all active Viscount projects in descending
     * `z_priority` order (`14 -> 1`) and blends exterior border belts one-sidedly onto lower-order regions.
     * @alias ViscountSubstrataPipeline.B_processOrderedProjects
     *
     * @param {Object} arg0_discovery
     * @param {Object} [arg1_options]
     *
     * @returns {Promise<Object>}
     */
    static async B_processOrderedProjects (arg0_discovery, arg1_options) {
      //Convert from parameters
      let discovery = arg0_discovery;
      let options = (arg1_options) ? arg1_options : {};

      //Guard clauses
      if (!discovery || !Array.isArray(discovery.contexts) || discovery.contexts.length === 0)
        return { project_summaries: {} };

      //Declare local instance variables
      let out_folder = (options.output_folder) ? options.output_folder :
        path.join(discovery.root_dir, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_2.scaled_to_regions");
      let project_summaries = {};

      //Function body
      for (let i = 0; i < discovery.contexts.length; i++) {
        let ctx = discovery.contexts[i];
        console.log(`[ViscountSubstrataPipeline] Resolving ${ctx.key} (order=${ctx.order}, z_priority=${ctx.z_priority}, active_pixels=${ctx.n_valid}, superseded=${ctx.superseded_pixel_count || 0})...`);

        if (ctx.pipeline_mode === "polaris_russia_delegate" && typeof global.population_Substrata_russia !== "undefined") {
          let rus = global.population_Substrata_russia;
          if (ctx.superseded_pixel_count > 0) {
            //Evaluate POLARIS on the un-superseded residual mask and blend lower-order exterior frontier belt
            let rus_res = await this.runDelegateContextWithLock(ctx, rus, out_folder, options);
            project_summaries[ctx.key] = rus_res;
          } else {
            project_summaries[ctx.key] = await rus.processRasters({
              config_path: path.resolve(discovery.root_dir, "histmap/1.data_raw/population_regional/POLARIS/russia_areal_masks.json5"),
              project_root: discovery.root_dir,
              ...options
            });
          }
        } else {
          project_summaries[ctx.key] = global.ViscountSubstrataMosaic.calibrateAndCompositeGenericProject(ctx, {
            output_folder: out_folder,
            ...options
          });
        }
      }

      //Return statement
      return { project_summaries: project_summaries };
    }


    /**
     * Preserves all calibrated Viscount domains (`14 -> 1` in `z_priority DESC` order) across downstream
     * `rasters_3.scaled_to_global/` and `rasters_4.interpolated_to_GHSL/` rasters.
     * @alias ViscountSubstrataPipeline.E_preserveAllViscountDomainsInGlobalRasters
     *
     * @param {Object} [arg0_options]
     */
    static E_preserveAllViscountDomainsInGlobalRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let discovery = options._viscount_discovery || this.A_discoverActiveViscountContexts(options);
      let root_dir = discovery.root_dir;
      let r2_dir = path.join(root_dir, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_2.scaled_to_regions");
      let r3_dir = path.join(root_dir, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_3.scaled_to_global");
      let r4_dir = path.join(root_dir, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_4.interpolated_to_GHSL");

      //Guard clauses
      if (!discovery || !discovery.contexts || discovery.contexts.length === 0) return;

      //Function body
      let first_ctx = discovery.contexts[0];
      if (discovery.contexts.length === 1 && first_ctx.key === "POLARIS" && typeof global.population_Substrata_russia !== "undefined") {
        global.population_Substrata_russia.E_preserveDomainInGHSLInterpolatedRasters({
          config_path: path.resolve(root_dir, "histmap/1.data_raw/population_regional/POLARIS/russia_areal_masks.json5"),
          project_root: root_dir,
          ...options
        });
        return;
      }

      let target_dirs = [r3_dir, r4_dir];
      for (let d = 0; d < target_dirs.length; d++) {
        let t_dir = target_dirs[d];
        if (!fs.existsSync(t_dir)) continue;

        let files = fs.readdirSync(t_dir).filter(function (arg0_f) { return /^popc_-?\d+\.png$/.test(arg0_f); });
        for (let f = 0; f < files.length; f++) {
          let r2_path = path.join(r2_dir, files[f]);
          let dst_path = path.join(t_dir, files[f]);
          if (!fs.existsSync(r2_path)) continue;

          let r2_png = PNG.sync.read(fs.readFileSync(r2_path));
          let dst_png = PNG.sync.read(fs.readFileSync(dst_path));
          let r2_dv = new DataView(r2_png.data.buffer, r2_png.data.byteOffset, r2_png.data.byteLength);
          let dst_dv = new DataView(dst_png.data.buffer, dst_png.data.byteOffset, dst_png.data.byteLength);

          for (let i = 0; i < discovery.contexts.length; i++) {
            let ctx = discovery.contexts[i];
            for (let x = 0; x < ctx.valid_indices.length; x++) {
              let idx = ctx.valid_indices[x];
              let val = global.ViscountSubstrataMosaic.readPositiveFloat32(r2_png.data, r2_dv, idx*4);
              let p4 = idx*4;
              if (val > 0) {
                dst_dv.setFloat32(p4, val, false);
              } else {
                dst_png.data[p4] = 0;
                dst_png.data[p4 + 1] = 0;
                dst_png.data[p4 + 2] = 0;
                dst_png.data[p4 + 3] = 0;
              }
            }
          }
          fs.writeFileSync(dst_path, PNG.sync.write(dst_png));
        }
      }
    }


    /**
     * Master pipeline entry point executed by `population_Substrata_outlier_removal`.
     * @alias ViscountSubstrataPipeline.processRasters
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Promise<Object>}
     */
    static async processRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let discovery = this.A_discoverActiveViscountContexts(options);

      //Function body
      options._viscount_discovery = discovery;

      //Return statement
      return await this.B_processOrderedProjects(discovery, options);
    }


    /**
     * Helper executing the `POLARIS` (`population_Substrata_russia`) delegate on a `z-index`-locked residual mask,
     * applying one-sided $C^1$ seam feathering along any frontier shared with higher-order Viscount neighbours.
     * @alias ViscountSubstrataPipeline.runDelegateContextWithLock
     *
     * @param {Object} arg0_context
     * @param {Object} arg1_rus_module
     * @param {string} arg2_out_folder
     * @param {Object} [arg3_options]
     *
     * @returns {Promise<Object>}
     */
    static async runDelegateContextWithLock (arg0_context, arg1_rus_module, arg2_out_folder, arg3_options) {
      //Convert from parameters
      let ctx = arg0_context;
      let rus = arg1_rus_module;
      let out_folder = arg2_out_folder;
      let options = (arg3_options) ? arg3_options : {};

      //Declare local instance variables
      let calibrated_series = [];
      let hyde_years = (options.years) ? options.years : ((options.hyde_years) ? options.hyde_years : ctx.hyde_years);
      let start_ms = Date.now();
      let urban_series = [];
      let year_summaries = {};

      //Function body
      for (let i = 0; i < hyde_years.length; i++) {
        let yr = hyde_years[i];
        let urban_valid = rus.loadUrbanValidForYear(ctx, yr);
        let mosaic_valid = rus.B_mosaicKrigedSubstrataForYear(ctx, yr, urban_valid);
        let cal_obj = rus.C_computeCalibratedFieldForYear(ctx, mosaic_valid, yr, urban_valid);
        calibrated_series.push(cal_obj.calibrated_rural);
        urban_series.push(urban_valid);
      }

      if (!fs.existsSync(out_folder)) fs.mkdirSync(out_folder, { recursive: true });
      for (let t = 0; t < hyde_years.length; t++) {
        let yr = hyde_years[t];
        let dst_path = path.join(out_folder, `popc_${yr}.png`);
        let fallback_path = path.join(ctx.root_dir, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_outliers_removed", `popc_${yr}.png`);
        let src_path = fs.existsSync(dst_path) ? dst_path : (fs.existsSync(fallback_path) ? fallback_path : null);
        if (!src_path) continue;

        let base_png = PNG.sync.read(fs.readFileSync(src_path));
        let base_dv = new DataView(base_png.data.buffer, base_png.data.byteOffset, base_png.data.byteLength);
        let cal_arr = calibrated_series[t];
        let u_arr = urban_series[t];
        let sum_val = 0;

        for (let i = 0; i < ctx.n_valid; i++) {
          let idx = ctx.valid_indices[i];
          let val = u_arr[i] + Math.max(1e-4, cal_arr[i]);
          base_dv.setFloat32(idx*4, val, false);
          sum_val += val;
        }

        global.ViscountSubstrataMosaic.applyOneSidedSeamBlend(ctx, base_png.data, base_dv, options);
        fs.writeFileSync(dst_path, PNG.sync.write(base_png));
        year_summaries[yr] = { combined: Math.round(sum_val) };
      }

      //Return statement
      return {
        elapsed_seconds: Number(((Date.now() - start_ms)/1000).toFixed(2)),
        year_summaries: year_summaries
      };
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountSubstrataPipeline: global.ViscountSubstrataPipeline };
