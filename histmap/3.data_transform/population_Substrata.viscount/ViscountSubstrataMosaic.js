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
      let ccf_cfg = (context.manifest && context.manifest.county_census_frontier && context.manifest.county_census_frontier.enabled) ? context.manifest.county_census_frontier : null;
      let ccf_cls = global.ViscountCountyCensusFrontier || null;
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
      if (ccf_cfg && !ccf_cls) {
        let ccf_p = path.resolve(context.root_dir || process.cwd(), ccf_cfg.module_path || "histmap/3.data_transform/population_Substrata.viscount/centaur/ViscountCountyCensusFrontier.js");
        if (fs.existsSync(ccf_p)) ccf_cls = require(ccf_p).ViscountCountyCensusFrontier;
      }
      let active_zone_series = [];
      let border_wt_series = [];
      let calibrated_series = [];
      let source_keys = Object.keys((context.manifest && context.manifest.substrata_sources) ? context.manifest.substrata_sources : {});
      let urban_series = [];
      let zone_targets_series = [];

      for (let i = 0; i < hyde_years.length; i++) {
        let yr = hyde_years[i];
        let urban_valid = new Float32Array(n_valid);
        let base_path = path.join(context.root_dir, "histmap/2.data_cleaning/population_Stadester/stadester_base_rasters", `stadester_base_${yr}.png`);
        let urban_path = path.join(context.root_dir, "histmap/2.data_cleaning/population_Stadester/stadester_urban_rasters", `stadester_urban_${yr}.png`);
        let u_read_path = fs.existsSync(base_path) ? base_path : urban_path;

        if (fs.existsSync(u_read_path)) {
          let u_png = PNG.sync.read(fs.readFileSync(u_read_path));
          let u_dv = new DataView(u_png.data.buffer, u_png.data.byteOffset, u_png.data.byteLength);
          for (let x = 0; x < n_valid; x++) {
            let u_val = this.readPositiveFloat32(u_png.data, u_dv, context.valid_indices[x]*4);

            urban_valid[x] = (u_val >= 0.01) ? u_val : 0;
          }
        }
        if (yr <= 0) {
          let c14_urb_path = path.join(context.root_dir, "histmap/2.data_cleaning/population_c14bazAAR/3.rasters_urban", `urbc_${yr}.png`);
          if (fs.existsSync(c14_urb_path)) {
            let c14_png = PNG.sync.read(fs.readFileSync(c14_urb_path));
            let c14_dv = new DataView(c14_png.data.buffer, c14_png.data.byteOffset, c14_png.data.byteLength);
            for (let x = 0; x < n_valid; x++) {
              let c14_val = this.readPositiveFloat32(c14_png.data, c14_dv, context.valid_indices[x]*4);

              if (c14_val > urban_valid[x]) urban_valid[x] = c14_val;
            }
          }
        }
        if (global.population_Stadester_rasters && typeof global.population_Stadester_rasters.getSubUrbanSettlementsData === "function") {
          let sub_urb = global.population_Stadester_rasters.getSubUrbanSettlementsData(yr, {
            stadester_file_path: path.join(context.root_dir, "histmap/3.data_transform/population_Stadester.transform/stadester"),
            viscount_key: context.key
          });

          if (sub_urb) {
            for (let x = 0; x < n_valid; x++) {
              let sv = sub_urb[context.valid_indices[x]];

              if (sv > 0) urban_valid[x] += sv;
            }
          }
        }

        let rural_valid = new Float32Array(n_valid);
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
        let active_zone_of_v = new Int32Array(n_valid).fill(-1);
        let ccf_active = Boolean(ccf_cfg && ccf_cls && yr >= ccf_cfg.start_year && yr <= ccf_cfg.end_year);
        let county_mask = ccf_active ? ccf_cls.D_loadMosaicCountyMaskForYear(context, yr, ccf_cfg) : null;
        let zone_targets_by_id = [];
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
              let settled_sum = 0;
              let z_id = zone_targets_by_id.length;
              let ccf_res = county_mask ? ccf_cls.E_calibrateZoneWithCountyFrontier(context, zone, county_mask, base_rural, urban_valid, rural_valid, touched, active_zone_of_v, z_id, target_pop, ccf_cfg) : null;
              if (ccf_res && ccf_res.handled) { zone_targets_by_id.push(ccf_res); continue; }
              for (let a = 0; a < zone.pixels.length; a++) {
                let v_idx = context.pixel_to_valid[zone.pixels[a]];
                if (v_idx >= 0) {
                  active_zone_of_v[v_idx] = z_id;
                  if (base_rural[v_idx] > 0) curr_sum += base_rural[v_idx];
                  if (urban_valid[v_idx] > 0) settled_sum += urban_valid[v_idx];
                }
              }

              let rural_target_pop = 0;
              let settled_scale = 0;

              if (target_pop > 0) {
                if (settled_sum < 0.90*target_pop) {
                  rural_target_pop = target_pop - settled_sum;
                  settled_scale = 1.0;
                } else {
                  rural_target_pop = 0.10*target_pop;
                  settled_scale = 0.90*target_pop/settled_sum;
                }
              }
              zone_targets_by_id.push({ rural_target_pop: rural_target_pop, settled_scale: settled_scale, target_pop: target_pop });
              if (curr_sum > 0 && rural_target_pop > 0) {
                let scalar = rural_target_pop/curr_sum;
                for (let a = 0; a < zone.pixels.length; a++) {
                  let v_idx = context.pixel_to_valid[zone.pixels[a]];
                  if (v_idx >= 0 && base_rural[v_idx] > 0) {
                    rural_valid[v_idx] = Math.max(1e-4, base_rural[v_idx]*scalar);
                    touched[v_idx] = 1;
                  }
                }
              } else if (curr_sum === 0 && rural_target_pop > 0) {
                let target_px = [];

                if (zone.pixels.length > 25 && context.fallback_hab_mask) {
                  for (let a = 0; a < zone.pixels.length; a++) {
                    let px = zone.pixels[a];

                    if (context.pixel_to_valid[px] >= 0 && context.fallback_hab_mask[px] === 1)
                      target_px.push(px);
                  }
                }
                if (target_px.length === 0 && zone.pixels.length <= 25) target_px = zone.pixels;
                if (target_px.length > 0) {
                  let per_px = rural_target_pop/target_px.length;

                  for (let a = 0; a < target_px.length; a++) {
                    let v_idx = context.pixel_to_valid[target_px[a]];
                    if (v_idx >= 0) {
                      rural_valid[v_idx] = Math.max(1e-4, per_px);
                      base_rural[v_idx] = rural_valid[v_idx];
                      touched[v_idx] = 1;
                    }
                  }
                }
              } else if (target_pop === 0) {
                for (let a = 0; a < zone.pixels.length; a++) {
                  let v_idx = context.pixel_to_valid[zone.pixels[a]];
                  if (v_idx >= 0) {
                    rural_valid[v_idx] = 0;
                    touched[v_idx] = 0;
                  }
                }
              }
            }
          }
        }

        //3-pass separable tent smoothing of log-multipliers within each source domain (zero uninhabited leakage)
        let blur_r = (context.manifest && context.manifest.smoothing && Number.isFinite(context.manifest.smoothing.interior_multiplier_blur_radius_px)) ?
          context.manifest.smoothing.interior_multiplier_blur_radius_px : 5;
        let blur_passes = (context.manifest && context.manifest.smoothing && Number.isFinite(context.manifest.smoothing.interior_multiplier_blur_passes)) ?
          Math.max(3, context.manifest.smoothing.interior_multiplier_blur_passes) : 3;
        if (ccf_active && Number.isFinite(ccf_cfg.interior_multiplier_blur_radius_px)) blur_r = Number(ccf_cfg.interior_multiplier_blur_radius_px);
        if (ccf_active && Number.isFinite(ccf_cfg.interior_multiplier_blur_passes)) blur_passes = Number(ccf_cfg.interior_multiplier_blur_passes);
        let log_mult = new Float32Array(n_valid);
        let tmp_mult = new Float32Array(n_valid);

        for (let v = 0; v < n_valid; v++) {
          log_mult[v] = (touched[v] && base_rural[v] > 0) ?
            Math.log(Math.max(1e-6, rural_valid[v])/Math.max(1e-6, base_rural[v])) : 0;
        }

        for (let pass = 0; blur_r > 0 && pass < blur_passes; pass++) {
          for (let v = 0; v < n_valid; v++) {
            if (!touched[v] || base_rural[v] <= 0) { tmp_mult[v] = 0; continue; }
            let px = context.valid_indices[v];
            let dom_id = context.pixel_domain[px];
            let r = Math.floor(px/context.width);
            let c = px % context.width;
            let acc = 0;
            let wt_sum = 0;

            for (let dc = -blur_r; dc <= blur_r; dc++) {
              let nc = (c + dc + context.width) % context.width;
              let nv = context.pixel_to_valid[r*context.width + nc];
              if (nv >= 0 && touched[nv] && base_rural[nv] > 0 && context.pixel_domain[context.valid_indices[nv]] === dom_id) {
                let wt = blur_r + 1 - Math.abs(dc);
                acc += log_mult[nv]*wt;
                wt_sum += wt;
              }
            }
            tmp_mult[v] = (wt_sum > 0) ? acc/wt_sum : log_mult[v];
          }
          for (let v = 0; v < n_valid; v++) {
            if (!touched[v] || base_rural[v] <= 0) continue;
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
              if (nv >= 0 && touched[nv] && base_rural[nv] > 0 && context.pixel_domain[context.valid_indices[nv]] === dom_id) {
                let wt = blur_r + 1 - Math.abs(dr);
                acc += tmp_mult[nv]*wt;
                wt_sum += wt;
              }
            }
            log_mult[v] = (wt_sum > 0) ? acc/wt_sum : tmp_mult[v];
          }
        }

        for (let v = 0; v < n_valid; v++) {
          if (!touched[v] || base_rural[v] <= 0) {
            if (rural_valid[v] <= 0) rural_valid[v] = 0;
            continue;
          }
          rural_valid[v] = Math.max(1e-4, base_rural[v]*Math.exp(log_mult[v]));
        }
        let w_int = this.computeZoneInteriorWeights(context, active_zone_of_v);

        this.conserveZoneTargetsInteriorPinned(rural_valid, active_zone_of_v, w_int, zone_targets_by_id);

        active_zone_series.push(active_zone_of_v);
        border_wt_series.push(w_int);
        calibrated_series.push(rural_valid);
        urban_series.push(urban_valid);
        zone_targets_series.push(zone_targets_by_id);
      }

      for (let t = 0; t < hyde_years.length; t++) {
        let yr = hyde_years[t];
        let out_png_path = path.join(out_folder, `popc_${yr}.png`);
        let fallback_path = path.join(context.root_dir, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_outliers_removed", `popc_${yr}.png`);
        let read_path = fs.existsSync(out_png_path) ? out_png_path : (fs.existsSync(fallback_path) ? fallback_path : null);
        if (!read_path) continue;

        let active_zones = active_zone_series[t];
        let cal_arr = calibrated_series[t];
        let out_png = PNG.sync.read(fs.readFileSync(read_path));
        let out_dv = new DataView(out_png.data.buffer, out_png.data.byteOffset, out_png.data.byteLength);
        let smoothed_r = new Float32Array(n_valid);
        let total_pop = 0;
        let u_arr = urban_series[t];
        let w_int = border_wt_series[t];
        let z_targets = zone_targets_series[t];
        let t_w = (ccf_cfg && yr >= ccf_cfg.start_year && yr <= ccf_cfg.end_year && Number.isFinite(ccf_cfg.temporal_log_Laplacian_weight)) ? Number(ccf_cfg.temporal_log_Laplacian_weight) : temp_weight;

        for (let i = 0; i < n_valid; i++) {
          if (cal_arr[i] > 0) {
            let prev_v = (t > 0 && calibrated_series[t - 1][i] > 0) ? calibrated_series[t - 1][i] : cal_arr[i];
            let next_v = (t + 1 < hyde_years.length && calibrated_series[t + 1][i] > 0) ? calibrated_series[t + 1][i] : cal_arr[i];

            smoothed_r[i] = Math.max(1e-4, Math.exp((1 - t_w)*Math.log(cal_arr[i]) + 0.5*t_w*(Math.log(prev_v) + Math.log(next_v))));
          }
        }
        this.conserveZoneTargetsInteriorPinned(smoothed_r, active_zones, w_int, z_targets);

        //Fill isolated inland zero pinholes surrounded by 8 neighbours > 5,0
        let ph_updates = [];
        for (let i = 0; i < n_valid; i++) {
          let az = active_zones[i];
          if (smoothed_r[i] > 0 || (az >= 0 && z_targets[az].target_pop === 0)) continue;
          let g = context.valid_indices[i];
          let cy = Math.floor(g/context.width);
          let cx = g % context.width;
          if (cy <= 0 || cy >= context.height - 1) continue;
          let acc = 0;
          let cnt = 0;

          for (let dy = -1; dy <= 1; dy++) {
            for (let dx = -1; dx <= 1; dx++) {
              if (dx === 0 && dy === 0) continue;
              let nv = context.pixel_to_valid[(cy + dy)*context.width + ((cx + dx + context.width) % context.width)];
              if (nv >= 0 && smoothed_r[nv] > 5.0) { acc += smoothed_r[nv]; cnt++; }
            }
          }
          if (cnt === 8) ph_updates.push([i, 0.25*(acc/8.0)]);
        }
        for (let p = 0; p < ph_updates.length; p++) smoothed_r[ph_updates[p][0]] = ph_updates[p][1];

        for (let i = 0; i < n_valid; i++) {
          let az = active_zones[i];
          let idx = context.valid_indices[i];
          let p4 = idx*4;
          let u_sc = (az >= 0 && z_targets[az]) ? z_targets[az].settled_scale : 1.0;
          let val = (az >= 0 && z_targets[az].target_pop === 0) ? 0 : (smoothed_r[i] + u_arr[i]*u_sc);

          if (val > 0) {
            out_dv.setFloat32(p4, val, false);
            total_pop += val;
          } else {
            out_png.data[p4] = 0;
            out_png.data[p4 + 1] = 0;
            out_png.data[p4 + 2] = 0;
            out_png.data[p4 + 3] = 0;
          }
        }

        this.applyOneSidedSeamBlend(context, out_png.data, out_dv, options);
        fs.writeFileSync(out_png_path, PNG.sync.write(out_png, { colorType: 6, deflateLevel: 1, filterType: 0 }));
        year_summaries[yr] = { combined: Math.round(total_pop) };
      }

      //Return statement
      return {
        elapsed_seconds: Number(((Date.now() - start_ms)/1000).toFixed(2)),
        year_summaries: year_summaries
      };
    }


    /**
     * Computes cached boundary-pinned interior weights `w_int` (`0` on zone borders, approaching `1` inside)
     * using an 8-neighbour chamfer distance transform so zone conservation never injects 1-px border steps.
     * @alias ViscountSubstrataMosaic.computeZoneInteriorWeights
     */
    static computeZoneInteriorWeights (arg0_context, arg1_active_zones) {
      let context = arg0_context;
      let az = arg1_active_zones;
      let n_valid = context.n_valid;
      let sig = 2166136261;

      for (let s_i = 0; s_i < n_valid; s_i += 8)
        sig = Math.imul(sig ^ (az[s_i] + 2), 16777619) >>> 0;

      if (context._last_zone_sig === sig && context._last_zone_w_int)
        return context._last_zone_w_int;

      let buckets = [];
      let d_max = 30;
      let h = context.height;
      let p2v = context.pixel_to_valid;
      let tent = new Uint8Array(n_valid).fill(d_max);
      let v_idx = context.valid_indices;
      let w = context.width;

      for (let d = 0; d < d_max; d++) buckets.push([]);
      for (let i = 0; i < n_valid; i++) {
        if (az[i] < 0) continue;
        let g = v_idx[i];
        let cx = g % w;
        let cy = Math.floor(g/w);
        let nbs = [
          p2v[cy*w + ((cx + w - 1) % w)],
          p2v[cy*w + ((cx + 1) % w)],
          (cy > 0) ? p2v[(cy - 1)*w + cx] : -1,
          (cy + 1 < h) ? p2v[(cy + 1)*w + cx] : -1
        ];

        for (let k = 0; k < 4; k++) {
          let nv = nbs[k];

          if (nv >= 0 && az[nv] >= 0 && az[nv] !== az[i]) {
            tent[i] = 0;
            buckets[0].push(i);
            break;
          }
        }
      }

      for (let d = 0; d < d_max; d++) {
        let q = buckets[d];

        for (let qi = 0; qi < q.length; qi++) {
          let cur = q[qi];

          if (d > tent[cur]) continue;
          let g = v_idx[cur];
          let cx = g % w;
          let cy = Math.floor(g/w);

          for (let dy = -1; dy <= 1; dy++) {
            let nr = cy + dy;

            if (nr < 0 || nr >= h) continue;
            for (let dx = -1; dx <= 1; dx++) {
              if (dx === 0 && dy === 0) continue;
              let nv = p2v[nr*w + ((cx + dx + w) % w)];

              if (nv < 0 || az[nv] < 0) continue;
              let nd = d + ((dx === 0 || dy === 0) ? 3 : 4);

              if (nd < d_max && nd < tent[nv]) {
                tent[nv] = nd;
                buckets[nd].push(nv);
              }
            }
          }
        }
      }

      let w_int = new Float32Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let db = tent[i]/3.0;

        w_int[i] = 1.0 - Math.exp(-(db*db)/32.0);
      }
      context._last_zone_sig = sig;
      context._last_zone_w_int = w_int;

      //Return statement
      return w_int;
    }


    /**
     * Re-normalises zone rural targets onto zone interiors while holding border pixels continuous (`w_int = 0`).
     * @alias ViscountSubstrataMosaic.conserveZoneTargetsInteriorPinned
     */
    static conserveZoneTargetsInteriorPinned (arg0_field, arg1_active_zones, arg2_w_int, arg3_zone_targets) {
      let f = arg0_field;
      let az = arg1_active_zones;
      let w_int = arg2_w_int;
      let z_targets = arg3_zone_targets;
      let fixed_s = new Float64Array(z_targets.length);
      let free_s = new Float64Array(z_targets.length);
      let mult = new Float64Array(z_targets.length).fill(1.0);

      for (let i = 0; i < f.length; i++) {
        if (f[i] <= 0 || az[i] < 0) continue;
        let wi = w_int[i];

        fixed_s[az[i]] += f[i]*(1.0 - wi);
        free_s[az[i]] += f[i]*wi;
      }
      for (let z = 0; z < z_targets.length; z++) {
        let tgt = z_targets[z].rural_target_pop;

        if (tgt > 0 && free_s[z] > 1e-6) {
          let m_val = (tgt - fixed_s[z])/free_s[z];

          mult[z] = (m_val >= 0.15 && m_val <= 6.0) ? m_val : -(tgt/(fixed_s[z] + free_s[z]));
        }
      }
      for (let i = 0; i < f.length; i++) {
        let zid = az[i];

        if (f[i] <= 0 || zid < 0) continue;
        let mv = mult[zid];

        if (mv < 0) {
          f[i] = Math.max(1e-4, f[i]*(-mv));
        } else {
          let wi = w_int[i];

          f[i] = Math.max(1e-4, f[i]*((1.0 - wi) + wi*mv));
        }
      }
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
      let fallback_hab_mask = new Uint8Array(width*height);
      let manifest_obj = JSON5.parse(fs.readFileSync(manifest_abs, "utf8"));
      let n_pixels = width*height;
      let pixel_domain = new Uint8Array(n_pixels);
      let sources = manifest_obj.substrata_sources || {};
      let src_keys = Object.keys(sources);

      for (let i = 0; i < src_keys.length; i++) {
        let src = sources[src_keys[i]];
        let dom_code = (src.domain_code !== undefined) ? src.domain_code : (i + 1);
        let domain_mask_abs = src.domain_mask_png ? path.resolve(root_dir, src.domain_mask_png) : "";
        let sample_yr = (src.sample_year !== undefined) ? src.sample_year : 1000;
        let sample_path = path.join(root_dir, src.rasters_folder || "", `popc_${sample_yr}.png`);

        if (domain_mask_abs && fs.existsSync(domain_mask_abs)) {
          let dm_png = PNG.sync.read(fs.readFileSync(domain_mask_abs));

          for (let idx = 0; idx < n_pixels; idx++) {
            if (pixel_domain[idx] !== 0) continue;
            let p4 = idx*4;

            if (dm_png.data[p4 + 3] > 0 && (dm_png.data[p4] | dm_png.data[p4 + 1] | dm_png.data[p4 + 2]) !== 0)
              pixel_domain[idx] = dom_code;
          }
        }
        if (fs.existsSync(sample_path)) {
          let s_png = PNG.sync.read(fs.readFileSync(sample_path));
          for (let idx = 0; idx < n_pixels; idx++) {
            if (pixel_domain[idx] !== 0) continue;
            let p4 = idx*4;
            if ((s_png.data[p4] | s_png.data[p4 + 1] | s_png.data[p4 + 2] | s_png.data[p4 + 3]) !== 0)
              pixel_domain[idx] = dom_code;
          }
        }
        let doc_px_abs = src.documented_site_pixels_json ? path.resolve(root_dir, src.documented_site_pixels_json) : "";

        if (doc_px_abs && fs.existsSync(doc_px_abs)) {
          let doc_obj = JSON.parse(fs.readFileSync(doc_px_abs, "utf8"));
          let px_list = Array.isArray(doc_obj.pixels) ? doc_obj.pixels : [];

          for (let p = 0; p < px_list.length; p++) {
            let sc = Math.max(0, Math.min(width - 1, Math.round(Number(px_list[p][0]))));
            let sr = Math.max(0, Math.min(height - 1, Math.round(Number(px_list[p][1]))));
            let lat = 90 - (sr + 0.5)*180/height;

            if (lat <= 74.0) fallback_hab_mask[sr*width + sc] = 1;
          }
        }
      }

      let hyde_1900_abs = path.resolve(root_dir, "histmap/2.data_cleaning/landuse_HYDE/rasters_scaled_to_global/popc_1900.png");

      if (fs.existsSync(hyde_1900_abs)) {
        let h19_png = PNG.sync.read(fs.readFileSync(hyde_1900_abs));
        let h19_dv = new DataView(h19_png.data.buffer, h19_png.data.byteOffset, h19_png.data.byteLength);

        for (let idx = 0; idx < n_pixels; idx++) {
          if (pixel_domain[idx] === 0) continue;
          let lat = 90 - (Math.floor(idx/width) + 0.5)*180/height;

          if (lat <= 74.0 && this.readPositiveFloat32(h19_png.data, h19_dv, idx*4) > 0)
            fallback_hab_mask[idx] = 1;
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
        fallback_hab_mask: fallback_hab_mask,
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
