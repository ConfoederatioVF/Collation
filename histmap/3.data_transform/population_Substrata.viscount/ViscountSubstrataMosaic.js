//Import modules
let fs = global.fs || require("fs");
let JSON5 = global.JSON5 || require("json5");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * Generalised Operation Viscount regional substrata loader, hierarchical dasymetric calibrator
   * and inverse (`z-index`) borderland mosaic engine (`z_priority = order`: `14` down to `1`).
   * Higher-order projects claim shared frontier pixels first and keep 100% exact mass conservation,
   * whilst lower-order neighbours calibrate only residual uncovered pixels and absorb a one-sided
   * $C^1$ raised-cosine exterior seam transition (`200 km` / `24 px`).
   *
   * @class ViscountSubstrataMosaic
   */
  global.ViscountSubstrataMosaic = class {
    /**
     * Applies one-sided $C^1$ raised-cosine exterior seam feathering strictly onto a lower-order project's
     * frontier belt (`z_seam_blend`), reading locked higher-order densities from the active composed raster.
     * @alias ViscountSubstrataMosaic.applyOneSidedSeamBlend
     *
     * @param {Object} arg0_lower_context
     * @param {Buffer|Uint8Array} arg1_png_data
     * @param {DataView} arg2_png_dv
     * @param {Object} [arg3_options]
     *
     * @returns {number} Count of frontier belt pixels blended
     */
    static applyOneSidedSeamBlend (arg0_lower_context, arg1_png_data, arg2_png_dv, arg3_options) {
      //Convert from parameters
      let context = arg0_lower_context;
      let png_data = arg1_png_data;
      let png_dv = arg2_png_dv;
      let options = (arg3_options) ? arg3_options : {};

      //Guard clauses
      if (!context || !context.z_seam_blend || !png_data || !png_dv) return 0;

      //Declare local instance variables
      let anchor_pixels = context.z_seam_blend.anchor_pixel;
      let blended_count = 0;
      let max_ratio = Number(options.max_seam_ratio) || 2.25;
      let min_ratio = Number(options.min_seam_ratio) || 0.45;
      let valid_indices = context.valid_indices;
      let weights = context.z_seam_blend.weights;

      //Function body
      for (let i = 0; i < valid_indices.length; i++) {
        let w = weights[i];
        if (w >= 0.999) continue;

        let anchor_idx = anchor_pixels[i];
        if (anchor_idx < 0) continue;

        let idx = valid_indices[i];
        let a_val = this.readPositiveFloat32(png_data, png_dv, anchor_idx*4);
        let l_val = this.readPositiveFloat32(png_data, png_dv, idx*4);
        if (a_val <= 0 || l_val <= 0) continue;

        let clamped_anchor = Math.max(l_val*min_ratio, Math.min(l_val*max_ratio, a_val));
        let blended = Math.max(1e-4, w*l_val + (1 - w)*clamped_anchor);
        png_dv.setFloat32(idx*4, blended, false);
        blended_count++;
      }

      //Return statement
      return blended_count;
    }


    /**
     * Calibrates and composites a generic Viscount project context into `rasters_2.scaled_to_regions/`
     * when it does not use a specialised legacy delegator.
     * @alias ViscountSubstrataMosaic.calibrateAndCompositeGenericProject
     *
     * @param {Object} arg0_context
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    static calibrateAndCompositeGenericProject (arg0_context, arg1_options) {
      //Convert from parameters
      let context = arg0_context;
      let options = (arg1_options) ? arg1_options : {};

      //Guard clauses
      if (!context || !context.valid_indices || context.valid_indices.length === 0)
        return { elapsed_seconds: 0, year_summaries: {} };

      //Declare local instance variables
      let hyde_years = (options.years) ? options.years : ((options.hyde_years) ? options.hyde_years : context.hyde_years);
      let n_valid = context.n_valid;
      let out_folder = (options.output_folder) ? options.output_folder :
        path.join(context.root_dir, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_2.scaled_to_regions");
      let start_ms = Date.now();
      let temp_weight = (context.manifest && context.manifest.smoothing && Number.isFinite(context.manifest.smoothing.temporal_log_Laplacian_weight)) ?
        context.manifest.smoothing.temporal_log_Laplacian_weight : 0.15;
      let year_summaries = {};

      //Function body
      if (!fs.existsSync(out_folder)) fs.mkdirSync(out_folder, { recursive: true });
      let source_keys = Object.keys((context.manifest && context.manifest.substrata_sources) ? context.manifest.substrata_sources : {});
      let calibrated_series = [];
      let urban_series = [];

      for (let i = 0; i < hyde_years.length; i++) {
        let yr = hyde_years[i];
        let urban_valid = new Float32Array(n_valid);
        let urban_path = path.join(context.root_dir, "histmap/2.data_cleaning/population_Stadester/stadester_urban_rasters", `stadester_urban_${yr}.png`);
        if (fs.existsSync(urban_path)) {
          let u_png = PNG.sync.read(fs.readFileSync(urban_path));
          let u_dv = new DataView(u_png.data.buffer, u_png.data.byteOffset, u_png.data.byteLength);
          for (let x = 0; x < n_valid; x++)
            urban_valid[x] = this.readPositiveFloat32(u_png.data, u_dv, context.valid_indices[x]*4);
        }

        let rural_valid = new Float32Array(n_valid).fill(1e-4);
        for (let s = 0; s < source_keys.length; s++) {
          let src_cfg = context.manifest.substrata_sources[source_keys[s]];
          let src_dom = (src_cfg.domain_code !== undefined) ? src_cfg.domain_code : (s + 1);
          let src_file = path.join(context.root_dir, src_cfg.rasters_folder, `popc_${yr}.png`);
          if (!fs.existsSync(src_file)) continue;

          let s_png = PNG.sync.read(fs.readFileSync(src_file));
          let s_dv = new DataView(s_png.data.buffer, s_png.data.byteOffset, s_png.data.byteLength);
          for (let x = 0; x < n_valid; x++) {
            let idx = context.valid_indices[x];
            if (context.pixel_domain[idx] !== src_dom) continue;
            let val = this.readPositiveFloat32(s_png.data, s_dv, idx*4);
            if (val > 0) rural_valid[x] = val;
          }
        }

        let base_rural = Float32Array.from(rural_valid);
        let target_groups = [
          context.macro_entry ? [context.macro_entry] : [],
          context.specialist_entries || [],
          context.national_epoch_entries || []
        ];
        let touched = new Uint8Array(n_valid);

        for (let g = 0; g < target_groups.length; g++) {
          let group = target_groups[g];
          for (let x = 0; x < group.length; x++) {
            let entry = group[x];
            if (entry.domain && (yr < entry.domain[0] || yr > entry.domain[1])) continue;
            let zones = entry.zones || [];
            for (let z = 0; z < zones.length; z++) {
              let zone = zones[z];
              if (!zone.pixels || zone.pixels.length === 0) continue;
              if (zone.domain && (yr < zone.domain[0] || yr > zone.domain[1])) continue;
              let raw_target = this.resolveZoneTargetPopulation(zone.population, yr);
              if (raw_target < 0) continue;
              let target_pop = raw_target*(zone.domain_fraction !== undefined ? zone.domain_fraction : 1.0);
              let curr_sum = 0;
              let urb_sum = 0;
              for (let a = 0; a < zone.pixels.length; a++) {
                let v_idx = context.pixel_to_valid[zone.pixels[a]];
                if (v_idx >= 0) {
                  curr_sum += base_rural[v_idx];
                  urb_sum += urban_valid[v_idx];
                }
              }
              let rural_target = Math.max(zone.pixels.length*0.05, target_pop - urb_sum);
              let scalar = (curr_sum > 0) ? rural_target/curr_sum : 1.0;
              for (let a = 0; a < zone.pixels.length; a++) {
                let v_idx = context.pixel_to_valid[zone.pixels[a]];
                if (v_idx >= 0) {
                  rural_valid[v_idx] = Math.max(1e-4, base_rural[v_idx]*scalar);
                  touched[v_idx] = 1;
                }
              }
            }
          }
        }

        //2-pass separable spatial smoothing of log-multipliers within each source domain to prevent state/HUC wall cliffs
        let blur_r = (context.manifest && context.manifest.smoothing && Number.isFinite(context.manifest.smoothing.interior_multiplier_blur_radius_px)) ?
          context.manifest.smoothing.interior_multiplier_blur_radius_px : 5;
        let blur_passes = (context.manifest && context.manifest.smoothing && Number.isFinite(context.manifest.smoothing.interior_multiplier_blur_passes)) ?
          context.manifest.smoothing.interior_multiplier_blur_passes : 2;
        let log_mult = new Float32Array(n_valid);
        let pre_smooth_sum = 0;
        let tmp_mult = new Float32Array(n_valid);

        for (let v = 0; v < n_valid; v++) {
          if (touched[v]) {
            pre_smooth_sum += rural_valid[v];
            log_mult[v] = Math.log(Math.max(1e-6, rural_valid[v])/Math.max(1e-6, base_rural[v]));
          } else {
            log_mult[v] = 0;
          }
        }

        for (let pass = 0; pass < blur_passes; pass++) {
          for (let v = 0; v < n_valid; v++) {
            if (!touched[v]) { tmp_mult[v] = 0; continue; }
            let px = context.valid_indices[v];
            let dom_id = context.pixel_domain[px];
            let r = Math.floor(px/context.width);
            let c = px % context.width;
            let acc = 0;
            let wt_sum = 0;

            for (let dc = -blur_r; dc <= blur_r; dc++) {
              let nc = (c + dc + context.width) % context.width;
              let nv = context.pixel_to_valid[r*context.width + nc];
              if (nv >= 0 && touched[nv] && context.pixel_domain[context.valid_indices[nv]] === dom_id) {
                let wt = blur_r + 1 - Math.abs(dc);
                acc += log_mult[nv]*wt;
                wt_sum += wt;
              }
            }
            tmp_mult[v] = (wt_sum > 0) ? acc/wt_sum : log_mult[v];
          }
          for (let v = 0; v < n_valid; v++) {
            if (!touched[v]) continue;
            let px = context.valid_indices[v];
            let dom_id = context.pixel_domain[px];
            let r = Math.floor(px/context.width);
            let c = px % context.width;
            let acc = 0;
            let wt_sum = 0;

            for (let dr = -blur_r; dr <= blur_r; dr++) {
              let nr = r + dr;
              if (nr < 0 || nr >= context.height) continue;
              let nv = context.pixel_to_valid[nr*context.width + c];
              if (nv >= 0 && touched[nv] && context.pixel_domain[context.valid_indices[nv]] === dom_id) {
                let wt = blur_r + 1 - Math.abs(dr);
                acc += tmp_mult[nv]*wt;
                wt_sum += wt;
              }
            }
            log_mult[v] = (wt_sum > 0) ? acc/wt_sum : tmp_mult[v];
          }
        }

        let smoothed_sum = 0;
        for (let v = 0; v < n_valid; v++) {
          if (!touched[v]) continue;
          rural_valid[v] = Math.max(1e-4, base_rural[v]*Math.exp(log_mult[v]));
          smoothed_sum += rural_valid[v];
        }
        if (smoothed_sum > 0 && pre_smooth_sum > 0) {
          let norm_k = pre_smooth_sum/smoothed_sum;
          for (let v = 0; v < n_valid; v++)
            if (touched[v]) rural_valid[v] = Math.max(1e-4, rural_valid[v]*norm_k);
        }

        calibrated_series.push(rural_valid);
        urban_series.push(urban_valid);
      }

      for (let t = 0; t < hyde_years.length; t++) {
        let yr = hyde_years[t];
        let out_png_path = path.join(out_folder, `popc_${yr}.png`);
        let fallback_path = path.join(context.root_dir, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_outliers_removed", `popc_${yr}.png`);
        let read_path = fs.existsSync(out_png_path) ? out_png_path : (fs.existsSync(fallback_path) ? fallback_path : null);
        if (!read_path) continue;

        let out_png = PNG.sync.read(fs.readFileSync(read_path));
        let out_dv = new DataView(out_png.data.buffer, out_png.data.byteOffset, out_png.data.byteLength);
        let cal_arr = calibrated_series[t];
        let u_arr = urban_series[t];
        let total_pop = 0;

        for (let i = 0; i < n_valid; i++) {
          let idx = context.valid_indices[i];
          let prev_v = (t > 0) ? calibrated_series[t - 1][i] : cal_arr[i];
          let next_v = (t + 1 < hyde_years.length) ? calibrated_series[t + 1][i] : cal_arr[i];
          let smoothed_r = (cal_arr[i] > 0 && prev_v > 0 && next_v > 0) ?
            Math.exp((1 - temp_weight)*Math.log(cal_arr[i]) + 0.5*temp_weight*(Math.log(prev_v) + Math.log(next_v))) :
            cal_arr[i];
          let val = u_arr[i] + Math.max(1e-4, smoothed_r);
          out_dv.setFloat32(idx*4, val, false);
          total_pop += val;
        }

        this.applyOneSidedSeamBlend(context, out_png.data, out_dv, options);
        fs.writeFileSync(out_png_path, PNG.sync.write(out_png, { colorType: 6, deflateLevel: 3 }));
        year_summaries[yr] = { combined: Math.round(total_pop) };
      }

      //Return statement
      return {
        elapsed_seconds: Number(((Date.now() - start_ms)/1000).toFixed(2)),
        year_summaries: year_summaries
      };
    }


    /**
     * Filters any zone list (`macro_entry`, `specialist_entries`, `national_epoch_entries`) to exclude pixels
     * claimed by a higher-`z_priority` project and adjusts `domain_fraction` proportionally on split border zones.
     * @alias ViscountSubstrataMosaic.filterMaskEntriesByOwnership
     *
     * @param {Array<Object>} arg0_entries
     * @param {Uint8Array} arg1_owner_z_grid
     * @param {number} arg2_proj_z
     */
    static filterMaskEntriesByOwnership (arg0_entries, arg1_owner_z_grid, arg2_proj_z) {
      //Convert from parameters
      let entries = Array.isArray(arg0_entries) ? arg0_entries : [];
      let owner_z_grid = arg1_owner_z_grid;
      let proj_z = Number(arg2_proj_z);

      //Function body
      for (let i = 0; i < entries.length; i++) {
        let entry = entries[i];
        if (!entry || !Array.isArray(entry.zones)) continue;

        for (let x = 0; x < entry.zones.length; x++) {
          let zone = entry.zones[x];
          if (!Array.isArray(zone.pixels) || zone.pixels.length === 0) continue;

          let orig_len = zone.pixels.length;
          let kept = [];
          for (let y = 0; y < orig_len; y++) {
            let idx = zone.pixels[y];
            if (owner_z_grid[idx] === 0 || owner_z_grid[idx] === proj_z)
              kept.push(idx);
          }

          if (kept.length !== orig_len) {
            let base_frac = (zone.domain_fraction !== undefined) ? zone.domain_fraction : 1.0;
            if (!zone.preserve_full_target && orig_len > 0)
              zone.domain_fraction = base_frac*(kept.length/orig_len);
            zone.pixels = kept;
          }
        }
      }
    }


    /**
     * Loads a generic Viscount regional manifest (`<project>_areal_masks.json5`) into the unified mosaic context.
     * @alias ViscountSubstrataMosaic.loadGenericProjectContext
     *
     * @param {Object} arg0_project_cfg
     * @param {Object} [arg1_options]
     *
     * @returns {Object|null}
     */
    static loadGenericProjectContext (arg0_project_cfg, arg1_options) {
      //Convert from parameters
      let proj_cfg = arg0_project_cfg;
      let options = (arg1_options) ? arg1_options : {};

      //Declare local instance variables
      let height = 2160;
      let root_dir = (options.project_root) ? options.project_root : ((fs.existsSync("./histmap/1.data_raw")) ?
        path.resolve(".") : path.resolve(__dirname, "../../.."));
      let manifest_abs = path.resolve(root_dir, proj_cfg.areal_masks_manifest || "");
      let width = 4320;

      //Guard clauses
      if (!manifest_abs || !fs.existsSync(manifest_abs)) return null;

      //Function body
      let manifest_obj = JSON5.parse(fs.readFileSync(manifest_abs, "utf8"));
      let n_pixels = width*height;
      let pixel_domain = new Uint8Array(n_pixels);
      let sources = manifest_obj.substrata_sources || {};
      let src_keys = Object.keys(sources);

      for (let i = 0; i < src_keys.length; i++) {
        let src = sources[src_keys[i]];
        let dom_code = (src.domain_code !== undefined) ? src.domain_code : (i + 1);
        let sample_yr = (src.sample_year !== undefined) ? src.sample_year : 1000;
        let sample_path = path.join(root_dir, src.rasters_folder || "", `popc_${sample_yr}.png`);
        if (!fs.existsSync(sample_path)) continue;

        let s_png = PNG.sync.read(fs.readFileSync(sample_path));
        for (let idx = 0; idx < n_pixels; idx++) {
          if (pixel_domain[idx] !== 0) continue;
          let p4 = idx*4;
          if ((s_png.data[p4] | s_png.data[p4 + 1] | s_png.data[p4 + 2] | s_png.data[p4 + 3]) !== 0)
            pixel_domain[idx] = dom_code;
        }
      }

      let loadMaskGroup = function (arg0_list) {
        let out = [];
        let list = Array.isArray(arg0_list) ? arg0_list : [];
        for (let i = 0; i < list.length; i++) {
          let meta = list[i];
          let cfg_abs = path.resolve(root_dir, meta.json5_path || "");
          let png_abs = path.resolve(root_dir, meta.mask_path || "");
          if (!fs.existsSync(cfg_abs) || !fs.existsSync(png_abs)) continue;

          let m_json = JSON5.parse(fs.readFileSync(cfg_abs, "utf8"));
          let m_png = PNG.sync.read(fs.readFileSync(png_abs));
          let col_map = new Map();
          let zones = [];
          let r_keys = Object.keys(m_json.regions || {});
          for (let x = 0; x < r_keys.length; x++) {
            let zc = m_json.regions[r_keys[x]];
            let col = zc.colour || zc.color;
            if (Array.isArray(col) && col.length >= 3) {
              col_map.set(`${col[0]},${col[1]},${col[2]}`, zones.length);
              zones.push({ colour: col, domain: zc.domain || null, domain_fraction: 1.0, key: r_keys[x], pixels: [], population: zc.population || {} });
            }
          }
          for (let idx = 0; idx < n_pixels; idx++) {
            if (pixel_domain[idx] === 0) continue;
            let p4 = idx*4;
            if (m_png.data[p4 + 3] === 0) continue;
            let z_idx = col_map.get(`${m_png.data[p4]},${m_png.data[p4 + 1]},${m_png.data[p4 + 2]}`);
            if (z_idx !== undefined) zones[z_idx].pixels.push(idx);
          }
          out.push({ domain: meta.domain || m_json.domain, id: meta.id, zones: zones });
        }
        return out;
      };

      let valid_indices = [];
      let pixel_to_valid = new Int32Array(n_pixels).fill(-1);
      for (let idx = 0; idx < n_pixels; idx++) {
        if (pixel_domain[idx] > 0) {
          pixel_to_valid[idx] = valid_indices.length;
          valid_indices.push(idx);
        }
      }

      //Return statement
      return {
        height: height,
        hyde_years: manifest_obj.hyde_years || [],
        key: proj_cfg.key,
        macro_entry: manifest_obj.macro_mask ? loadMaskGroup([manifest_obj.macro_mask])[0] || null : null,
        manifest: manifest_obj,
        n_valid: valid_indices.length,
        national_epoch_entries: loadMaskGroup(manifest_obj.national_epoch_masks),
        order: proj_cfg.order,
        pixel_domain: pixel_domain,
        pixel_to_valid: pixel_to_valid,
        root_dir: root_dir,
        seam_feather_px: proj_cfg.seam_feather_px || 24,
        specialist_entries: loadMaskGroup(manifest_obj.specialist_masks),
        valid_indices: Int32Array.from(valid_indices),
        width: width,
        z_priority: proj_cfg.z_priority
      };
    }


    /**
     * Safely reads a positive big-endian IEEE-754 `float32` value from a PNG RGBA buffer.
     * @alias ViscountSubstrataMosaic.readPositiveFloat32
     *
     * @param {Buffer|Uint8Array} arg0_png_data
     * @param {DataView} arg1_data_view
     * @param {number} arg2_byte_offset
     *
     * @returns {number}
     */
    static readPositiveFloat32 (arg0_png_data, arg1_data_view, arg2_byte_offset) {
      //Convert from parameters
      let png_data = arg0_png_data;
      let data_view = arg1_data_view;
      let p4 = arg2_byte_offset;

      //Guard clauses
      if ((png_data[p4] | png_data[p4 + 1] | png_data[p4 + 2] | png_data[p4 + 3]) === 0)
        return 0;

      //Declare local instance variables
      let val = data_view.getFloat32(p4, false);

      //Return statement
      return (Number.isFinite(val) && val > 0) ? val : 0;
    }


    /**
     * Enforces inverse (`z-index`) precedence across an ordered array of active Viscount project contexts
     * (`z_priority` descending: `14` down to `1`). Higher-order projects lock their active pixels first;
     * lower-order projects drop superseded pixels and receive one-sided $C^1$ cosine seam blend tables.
     * @alias ViscountSubstrataMosaic.resolveMultiProjectZIndexLocks
     *
     * @param {Array<Object>} arg0_ordered_contexts
     * @param {Object} [arg1_options]
     *
     * @returns {Object} `{ owner_z_grid: Uint8Array, stats: Array<Object> }`
     */
    static resolveMultiProjectZIndexLocks (arg0_ordered_contexts, arg1_options) {
      //Convert from parameters
      let ordered_contexts = Array.isArray(arg0_ordered_contexts) ? arg0_ordered_contexts.slice() : [];
      let options = (arg1_options) ? arg1_options : {};

      //Declare local instance variables
      let height = 2160;
      let n_pixels = 4320*2160;
      let owner_z_grid = new Uint8Array(n_pixels);
      let stats = [];
      let width = 4320;

      //Sort strictly descending by z_priority (14 -> 1)
      ordered_contexts.sort(function (arg0_a, arg1_b) {
        return (arg1_b.z_priority || arg1_b.order || 0) - (arg0_a.z_priority || arg0_a.order || 0);
      });

      //Function body
      for (let i = 0; i < ordered_contexts.length; i++) {
        let ctx = ordered_contexts[i];
        let kept_valid = [];
        let old_valid = ctx.valid_indices || [];
        let proj_z = Number(ctx.z_priority || ctx.order || 1);
        let superseded_count = 0;

        for (let x = 0; x < old_valid.length; x++) {
          let idx = old_valid[x];
          let existing_owner = owner_z_grid[idx];
          if (existing_owner === 0 || existing_owner === proj_z) {
            owner_z_grid[idx] = proj_z;
            kept_valid.push(idx);
          } else {
            superseded_count++;
            if (ctx.pixel_domain) ctx.pixel_domain[idx] = 0;
            if (ctx.pixel_to_valid) ctx.pixel_to_valid[idx] = -1;
          }
        }

        if (superseded_count > 0) {
          let new_px_to_v = new Int32Array(n_pixels).fill(-1);
          for (let x = 0; x < kept_valid.length; x++)
            new_px_to_v[kept_valid[x]] = x;

          ctx.n_valid = kept_valid.length;
          ctx.pixel_to_valid = new_px_to_v;
          ctx.valid_indices = Int32Array.from(kept_valid);

          if (ctx.macro_entry)
            this.filterMaskEntriesByOwnership([ctx.macro_entry], owner_z_grid, proj_z);
          this.filterMaskEntriesByOwnership(ctx.specialist_entries, owner_z_grid, proj_z);
          this.filterMaskEntriesByOwnership(ctx.national_epoch_entries, owner_z_grid, proj_z);
        }

        //Construct one-sided C^1 raised-cosine seam feather belt exclusively inside lower-order exterior buffer
        let seam_px = Number(options.seam_feather_px || ctx.seam_feather_px || 24);
        let anchor_grid = new Int32Array(n_pixels).fill(-1);
        let bfs_dist = new Uint16Array(n_pixels).fill(65535);
        let bfs_q = [];
        let head = 0;

        for (let x = 0; x < kept_valid.length; x++) {
          let idx = kept_valid[x];
          let r = Math.floor(idx/width);
          let c = idx % width;
          let nbrs = [
            (r > 0) ? idx - width : -1,
            (r + 1 < height) ? idx + width : -1,
            (c > 0) ? idx - 1 : -1,
            (c + 1 < width) ? idx + 1 : -1
          ];
          for (let y = 0; y < 4; y++) {
            let n_idx = nbrs[y];
            if (n_idx >= 0 && owner_z_grid[n_idx] > proj_z) {
              bfs_dist[idx] = 1;
              anchor_grid[idx] = n_idx;
              bfs_q.push(idx);
              break;
            }
          }
        }

        while (head < bfs_q.length) {
          let curr = bfs_q[head++];
          let d = bfs_dist[curr];
          if (d >= seam_px) continue;
          let r = Math.floor(curr/width);
          let c = curr % width;
          let nbrs = [
            (r > 0) ? curr - width : -1,
            (r + 1 < height) ? curr + width : -1,
            (c > 0) ? curr - 1 : -1,
            (c + 1 < width) ? curr + 1 : -1
          ];
          for (let y = 0; y < 4; y++) {
            let n_idx = nbrs[y];
            if (n_idx >= 0 && owner_z_grid[n_idx] === proj_z && bfs_dist[n_idx] > d + 1) {
              bfs_dist[n_idx] = d + 1;
              anchor_grid[n_idx] = anchor_grid[curr];
              bfs_q.push(n_idx);
            }
          }
        }

        let seam_anchors = new Int32Array(kept_valid.length).fill(-1);
        let seam_weights = new Float32Array(kept_valid.length).fill(1.0);
        for (let x = 0; x < kept_valid.length; x++) {
          let idx = kept_valid[x];
          let d = bfs_dist[idx];
          if (d <= seam_px) {
            seam_anchors[x] = anchor_grid[idx];
            seam_weights[x] = 0.5*(1 - Math.cos(Math.PI*d/Math.max(1, seam_px)));
          }
        }

        ctx.superseded_pixel_count = superseded_count;
        ctx.z_seam_blend = {
          anchor_pixel: seam_anchors,
          weights: seam_weights
        };

        stats.push({
          kept_pixels: kept_valid.length,
          key: ctx.key,
          seam_belt_pixels: bfs_q.length,
          superseded_pixels: superseded_count,
          z_priority: proj_z
        });
      }

      //Return statement
      return { owner_z_grid: owner_z_grid, stats: stats };
    }


    /**
     * Resolves a region's target population at `arg1_year` from exact keys, `[min, max]` geometric means
     * or linear interpolation.
     * @alias ViscountSubstrataMosaic.resolveZoneTargetPopulation
     *
     * @param {Object} arg0_pop_dict
     * @param {number} arg1_year
     *
     * @returns {number}
     */
    static resolveZoneTargetPopulation (arg0_pop_dict, arg1_year) {
      //Convert from parameters
      let pop_dict = arg0_pop_dict;
      let year = Number(arg1_year);

      //Guard clauses
      if (!pop_dict || typeof pop_dict !== "object") return -1;

      //Function body
      let extractScalar = function (arg0_val) {
        if (Array.isArray(arg0_val) && arg0_val.length >= 2) {
          let a = Number(arg0_val[0]);
          let b = Number(arg0_val[1]);
          if (a > 0 && b > 0) return Math.sqrt(a*b);
          return 0.5*(a + b);
        }
        let n = Number(arg0_val);
        return Number.isFinite(n) ? n : -1;
      };

      if (pop_dict[year] !== undefined) {
        let exact = extractScalar(pop_dict[year]);
        if (exact >= 0) return exact;
      }

      let yrs = Object.keys(pop_dict).map(Number).filter(Number.isFinite).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
      if (yrs.length === 0) return -1;
      if (year <= yrs[0]) return extractScalar(pop_dict[yrs[0]]);
      if (year >= yrs[yrs.length - 1]) return extractScalar(pop_dict[yrs[yrs.length - 1]]);

      for (let i = 0; i < yrs.length - 1; i++) {
        if (year >= yrs[i] && year <= yrs[i + 1]) {
          let v0 = extractScalar(pop_dict[yrs[i]]);
          let v1 = extractScalar(pop_dict[yrs[i + 1]]);
          let t = (year - yrs[i])/Math.max(1, yrs[i + 1] - yrs[i]);
          return (1 - t)*v0 + t*v1;
        }
      }

      //Return statement
      return -1;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountSubstrataMosaic: global.ViscountSubstrataMosaic };
