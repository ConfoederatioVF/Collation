//Initialise functions
{
  let fs = global.fs || require("fs");
  let path = global.path || require("path");
  let { PNG } = global.pngjs || require("pngjs");

  if (!global.population_Substrata_russia_masks && typeof require !== "undefined") {
    try {
      require(path.join(__dirname, "substrata_russia_masks.js"));
    } catch (e) {}
  }

  /**
   * Mosaics, dasymetrically calibrates, and spatiotemporally smooths the Russian (`sites_IA_RAS`, -10000 to 1900 AD)
   * and Kievan Rus (`sites_belarus_ukraine`, -10000 to 1900 AD) kriged population substrata and modern GHSL/HYDE
   * settlement priors (1910 to 2025 AD) across all 14 regional literature-review areal masks and 8 national epoch
   * areal masks (`histmap/1.data_raw/population_regional/POLARIS/`) before compositing into
   * `population_Substrata.outlier_removal`.
   *
   * Logical flow is prefixed with step letters (`A_` through `E_`):
   * - `A_loadManifestAndMasks`: Delegates to `population_Substrata_russia_masks.A_loadManifestAndMasks`.
   * - `B_mosaicKrigedSubstrataForYear`: Loads the kriged `sites_IA_RAS` and `sites_belarus_ukraine` rasters (`-10000..1900`)
   *   and modern GHSL/HYDE spatial priors (`1910..2025`) for a given benchmark year and mosaics them over their domains.
   * - `C_computeCalibratedFieldForYear`: Computes dasymetric calibration multipliers per sub-region (Priority 2 + Priority 1
   *   for `-10000..1900`, reconciled with Priority 3 `national_epoch_masks` for `1400..2025`), smooths the log-multiplier
   *   field across internal and cross-domain (`dom 1 <-> dom 2`) boundaries, re-normalises regional totals, and applies
   *   cross-domain seam blending along the Belarus–Russia, Ukraine–Russia, and Crimea frontiers.
   * - `processRasters`: Applies temporal log-Laplacian regularisation across all 128 HYDE benchmark years (`-10000..2025 AD`),
   *   cleans foreign outlier-mask spillover cells, and composites the calibrated mosaic into `rasters_2.scaled_to_regions/`
   *   with clamped foreign-neighbour feathering.
   * - `E_preserveDomainInGHSLInterpolatedRasters`: Preserves calibrated POLARIS domains in `rasters_3.scaled_to_global/`
   *   and `rasters_4.interpolated_to_GHSL/`.
   *
   * @class population_Substrata_russia
   */
  global.population_Substrata_russia = class {
    static bf = (typeof h3 !== "undefined") ?
      `${h3}/population_Substrata.russia/` :
      ((fs.existsSync("./histmap/3.data_transform/population_Substrata.russia")) ?
        path.resolve("./histmap/3.data_transform/population_Substrata.russia") + path.sep :
        path.join(__dirname, "/"));
    static config_path = (typeof h1 !== "undefined" && fs.existsSync(`${h1}population_regional/POLARIS/russia_areal_masks.json5`)) ?
      path.resolve(`${h1}population_regional/POLARIS/russia_areal_masks.json5`) :
      ((fs.existsSync("./histmap/1.data_raw/population_regional/POLARIS/russia_areal_masks.json5")) ?
        path.resolve("./histmap/1.data_raw/population_regional/POLARIS/russia_areal_masks.json5") :
        path.resolve(__dirname, "../../1.data_raw/population_regional/POLARIS/russia_areal_masks.json5"));
    static project_root = (fs.existsSync("./histmap/1.data_raw")) ?
      path.resolve(".") :
      path.resolve(__dirname, "../../..");

    /**
     * Step A: Loads `histmap/1.data_raw/population_regional/POLARIS/russia_areal_masks.json5`, indexes all specialist (Priority 2),
     * macro (Priority 1), and national epoch (Priority 3) `4320x2160` RGB PNG areal masks, closes western frontier mask gaps,
     * and builds pixel-level domain, cross-domain seam, and exterior foreign-feathering tables.
     * @alias population_Substrata_russia.A_loadManifestAndMasks
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Object}
     */
    static A_loadManifestAndMasks (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Return statement
      return population_Substrata_russia_masks.A_loadManifestAndMasks({
        config_path: options.config_path || this.config_path,
        project_root: options.project_root || this.project_root,
        ...options
      });
    }


    /**
     * Step B: Loads and mosaics the `sites_IA_RAS` and `sites_belarus_ukraine` kriged population rasters (`-10000..1900`)
     * or blended 1900-kriged / GHSL spatial priors (`1910..2025`) for `arg1_year`.
     * @alias population_Substrata_russia.B_mosaicKrigedSubstrataForYear
     *
     * @param {Object} arg0_context - Output from `A_loadManifestAndMasks`
     * @param {number} arg1_year - Benchmark year (`-10000` to `2025`)
     * @param {Float32Array} [arg2_urban_valid] - Optional urban population array to subtract from post-1900 GHSL priors
     *
     * @returns {Float32Array} Valid-cell array of length `arg0_context.n_valid`
     */
    static B_mosaicKrigedSubstrataForYear (arg0_context, arg1_year, arg2_urban_valid) {
      //Convert from parameters
      let context = arg0_context;
      let year = Number(arg1_year);
      let urban_valid = arg2_urban_valid;

      //Declare local instance variables
      let bu_folder = path.join(context.root_dir, context.manifest.substrata_sources.belarus_ukraine.rasters_folder);
      let bu_path = path.join(bu_folder, `popc_${year}.png`);
      let mosaic_valid = new Float32Array(context.n_valid);
      let rus_folder = path.join(context.root_dir, context.manifest.substrata_sources.russia_ia_ras.rasters_folder);
      let rus_path = path.join(rus_folder, `popc_${year}.png`);

      //Function body
      if (year <= 1900) {
        if (fs.existsSync(rus_path)) {
          let rus_png = PNG.sync.read(fs.readFileSync(rus_path));
          let rus_dv = new DataView(rus_png.data.buffer, rus_png.data.byteOffset, rus_png.data.byteLength);
          for (let i = 0; i < context.n_valid; i++) {
            let idx = context.valid_indices[i];
            if (context.pixel_domain[idx] !== 1) continue;
            let val = this.readPositiveFloat32(rus_png.data, rus_dv, idx*4);
            if (val > 0) mosaic_valid[i] = val;
          }
        }

        if (fs.existsSync(bu_path)) {
          let bu_png = PNG.sync.read(fs.readFileSync(bu_path));
          let bu_dv = new DataView(bu_png.data.buffer, bu_png.data.byteOffset, bu_png.data.byteLength);
          for (let i = 0; i < context.n_valid; i++) {
            let idx = context.valid_indices[i];
            if (context.pixel_domain[idx] !== 2) continue;
            let val = this.readPositiveFloat32(bu_png.data, bu_dv, idx*4);
            if (val > 0) mosaic_valid[i] = val;
          }
        }
      } else {
        if (!context._cached_mosaic_1900)
          context._cached_mosaic_1900 = this.B_mosaicKrigedSubstrataForYear(context, 1900);

        let ghsl_year = Math.max(1975, Math.min(2025, year));
        let ghsl_path = path.join(
          context.root_dir,
          "histmap/2.data_cleaning/population_GHSL/cleaned_rasters",
          `GHS_POP_${ghsl_year}.png`
        );
        let r1_path = path.join(
          context.root_dir,
          "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_1.northern_america",
          `popc_${year}.png`
        );
        let prior_path = fs.existsSync(ghsl_path) ? ghsl_path : (fs.existsSync(r1_path) ? r1_path : null);
        let prior_valid = new Float32Array(context.n_valid);

        if (prior_path) {
          if (ghsl_year === 1975 && year < 1975 && context._cached_ghsl_1975) {
            prior_valid = context._cached_ghsl_1975;
          } else {
            let p_png = PNG.sync.read(fs.readFileSync(prior_path));
            let p_dv = new DataView(p_png.data.buffer, p_png.data.byteOffset, p_png.data.byteLength);
            for (let i = 0; i < context.n_valid; i++) {
              let idx = context.valid_indices[i];
              let val = this.readPositiveFloat32(p_png.data, p_dv, idx*4);
              if (val > 0) prior_valid[i] = val;
            }
            if (ghsl_year === 1975 && year < 1975)
              context._cached_ghsl_1975 = prior_valid;
          }
        }

        let w_modern = (year >= 1975) ? 1.0 : Math.max(0, Math.min(1, (year - 1900)/75.0));
        let m1900 = context._cached_mosaic_1900;
        for (let i = 0; i < context.n_valid; i++) {
          let u_sub = (urban_valid && urban_valid[i] > 0) ? urban_valid[i]*0.85 : 0;
          let mod_rur = Math.max(1e-4, prior_valid[i] - u_sub);
          mosaic_valid[i] = Math.max(1e-4, (1 - w_modern)*m1900[i] + w_modern*mod_rur);
        }
      }

      //Return statement
      return mosaic_valid;
    }


    /**
     * Step C: Applies hierarchical areal-mask rural calibration (Priority 2 specialist masks + Priority 1 residual macro-mask)
     * after subtracting urban settlement ground truth (`stadester_urban_<year>.png`), smooths the log-multiplier field
     * across internal and cross-domain zone boundaries, re-normalises regional rural target sums, and applies cross-domain
     * seam blending along internal `dom 1 <-> dom 2` borders.
     * @alias population_Substrata_russia.C_computeCalibratedFieldForYear
     *
     * @param {Object} arg0_context - Output from `A_loadManifestAndMasks`
     * @param {Float32Array} arg1_mosaic_valid - Unscaled mosaicked rural substratum on valid cells
     * @param {number} arg2_year - Benchmark year
     * @param {Float32Array} [arg3_urban_valid] - Urban population on valid cells
     *
     * @returns {Object} `{ calibrated_rural: Float32Array, zone_targets: Array<Object> }`
     */
    static C_computeCalibratedFieldForYear (arg0_context, arg1_mosaic_valid, arg2_year, arg3_urban_valid) {
      //Convert from parameters
      let context = arg0_context;
      let mosaic_valid = arg1_mosaic_valid;
      let year = Number(arg2_year);
      let urban_valid = (arg3_urban_valid) ? arg3_urban_valid : new Float32Array(context.n_valid);

      //Declare local instance variables
      let blur_passes = (context.manifest.smoothing && context.manifest.smoothing.interior_multiplier_blur_passes) || 2;
      let blur_radius = (context.manifest.smoothing && context.manifest.smoothing.interior_multiplier_blur_radius_px) || 4;
      let calibrated = new Float32Array(context.n_valid);
      let height = context.height;
      let log_mult = new Float32Array(context.n_valid);
      let n_valid = context.n_valid;
      let pixel_domain = context.pixel_domain;
      let px_to_valid = context.pixel_to_valid;
      let valid_indices = context.valid_indices;
      let width = context.width;
      let zone_targets = [];

      //Function body
      for (let i = 0; i < n_valid; i++)
        calibrated[i] = Math.max(1e-4, mosaic_valid[i]);

      //1. Priority 2 Specialist Masks calibration (subtracting urban settlement sum per zone with rural hinterland floor)
      for (let i = 0; i < context.specialist_entries.length; i++) {
        let s_entry = context.specialist_entries[i];
        if (year < s_entry.domain[0] || year > s_entry.domain[1]) continue;

        let sub_weights = s_entry.pixel_sub_weight;
        for (let x = 0; x < s_entry.zones.length; x++) {
          let z = s_entry.zones[x];
          if (z.pixels.length === 0) continue;
          let raw_target_pop = this.resolveZoneTargetPopulation(z.population, year);
          if (raw_target_pop < 0) continue;
          let target_pop = raw_target_pop*(z.domain_fraction !== undefined ? z.domain_fraction : 1.0);

          let current_sum = 0;
          let urban_sum = 0;
          for (let y = 0; y < z.pixels.length; y++) {
            let p_idx = z.pixels[y];
            let v_idx = px_to_valid[p_idx];
            if (v_idx >= 0) {
              let w = (sub_weights && sub_weights.has(p_idx)) ? sub_weights.get(p_idx) : 1.0;
              current_sum += calibrated[v_idx]*w;
              urban_sum += urban_valid[v_idx];
            }
          }

          let min_rural_pop = Math.max(z.pixels.length*0.05, Math.min(target_pop*0.35, current_sum*0.45));
          let rural_target_pop = Math.max(min_rural_pop, target_pop - urban_sum);
          let scalar = (current_sum > 0) ? (rural_target_pop/current_sum) : 1.0;
          for (let y = 0; y < z.pixels.length; y++) {
            let p_idx = z.pixels[y];
            let v_idx = px_to_valid[p_idx];
            if (v_idx >= 0) {
              let w = (sub_weights && sub_weights.has(p_idx)) ? sub_weights.get(p_idx) : 1.0;
              let eff_s = Math.max(1e-4, Math.min(1e4, scalar*w));
              log_mult[v_idx] = Math.log(eff_s);
            }
          }

          zone_targets.push({
            domain_code: s_entry.domain_code,
            max_year: s_entry.domain[1],
            pixels: z.pixels,
            target_pop: rural_target_pop
          });
        }
      }

      //2. Priority 1 Macro-Mask (`migration_period`) residual calibration on uncovered Russia pixels
      if (context.macro_entry) {
        let m_entry = context.macro_entry;
        let m_year = Math.max(m_entry.domain[0], Math.min(m_entry.domain[1], year));
        for (let x = 0; x < m_entry.zones.length; x++) {
          let mz = m_entry.zones[x];
          if (mz.pixels.length === 0) continue;
          let macro_target = this.resolveZoneTargetPopulation(mz.population, m_year);
          if (macro_target <= 0) continue;

          let covered_raw_sum = 0;
          let covered_rural_sum = 0;
          let covered_urban_sum = 0;
          let uncovered_pixels = [];
          let uncovered_raw_sum = 0;
          let uncovered_urban_sum = 0;

          for (let y = 0; y < mz.pixels.length; y++) {
            let p_idx = mz.pixels[y];
            let v_idx = px_to_valid[p_idx];
            if (v_idx < 0) continue;
            if (context.pixel_spec_mask[p_idx] >= 0) {
              covered_raw_sum += calibrated[v_idx];
              covered_rural_sum += calibrated[v_idx]*Math.exp(log_mult[v_idx]);
              covered_urban_sum += urban_valid[v_idx];
            } else {
              uncovered_raw_sum += calibrated[v_idx];
              uncovered_urban_sum += urban_valid[v_idx];
              uncovered_pixels.push(p_idx);
            }
          }

          if (uncovered_pixels.length > 0 && uncovered_raw_sum > 0) {
            let covered_total_sum = covered_rural_sum + covered_urban_sum;
            let residual_total_target;
            if (year >= m_entry.domain[0]) {
              residual_total_target = Math.max(uncovered_raw_sum*0.45, macro_target - covered_total_sum);
            } else {
              if (mz._covered_100 === undefined) {
                let c100 = 0;
                let seen_sz = new Map();
                for (let y = 0; y < mz.pixels.length; y++) {
                  let p_idx = mz.pixels[y];
                  let sm = context.pixel_spec_mask[p_idx];
                  let sz = context.pixel_spec_zone[p_idx];
                  if (sm >= 0 && sz >= 0) {
                    let k = `${sm}_${sz}`;
                    seen_sz.set(k, (seen_sz.get(k) || 0) + 1);
                  }
                }
                seen_sz.forEach((cnt, k) => {
                  let parts = k.split("_").map(Number);
                  let se = context.specialist_entries[parts[0]];
                  let zObj = se && se.zones[parts[1]];
                  if (zObj && zObj.pixels.length > 0) {
                    let t100 = this.resolveZoneTargetPopulation(zObj.population, m_entry.domain[0]);
                    if (t100 > 0)
                      c100 += t100*(zObj.domain_fraction || 1.0)*(cnt/zObj.pixels.length);
                  }
                });
                mz._covered_100 = c100;
              }
              let res_100 = Math.max(0, macro_target - (mz._covered_100 || 0));
              let ratio_pre = (mz._covered_100 > 0 && covered_total_sum > 0) ?
                (covered_total_sum/mz._covered_100) :
                ((covered_raw_sum > 0) ? (covered_total_sum/covered_raw_sum) : 1.0);
              residual_total_target = Math.max(uncovered_raw_sum*0.40, res_100*ratio_pre);
            }
            let residual_rural_target = Math.max(
              uncovered_raw_sum*0.35,
              residual_total_target - uncovered_urban_sum
            );
            let res_scalar = Math.max(0.35, Math.min(6.0, residual_rural_target/uncovered_raw_sum));
            let res_log = Math.log(res_scalar);
            for (let y = 0; y < uncovered_pixels.length; y++) {
              let v_idx = px_to_valid[uncovered_pixels[y]];
              if (v_idx >= 0) log_mult[v_idx] = res_log;
            }
            zone_targets.push({
              domain_code: 1,
              max_year: 1900,
              pixels: uncovered_pixels,
              target_pop: residual_rural_target
            });
          }
        }
      }

      //2b. Priority 3 National Epoch Masks (`1400..2026 AD`) calibration across both `dom === 1` and `dom === 2`
      if (year >= 1400 && context.national_epoch_entries && context.national_epoch_entries.length > 0) {
        if (year <= 1900) {
          for (let i = 0; i < n_valid; i++)
            calibrated[i] = Math.max(1e-4, calibrated[i]*Math.exp(log_mult[i]));
          log_mult.fill(0);
          zone_targets = [];
        }

        let active_nat_entry = null;
        for (let i = 0; i < context.national_epoch_entries.length; i++) {
          let ne = context.national_epoch_entries[i];
          if (year >= ne.domain[0] && year <= ne.domain[1])
            active_nat_entry = ne;
        }

        if (active_nat_entry) {
          for (let x = 0; x < active_nat_entry.zones.length; x++) {
            let nz = active_nat_entry.zones[x];
            if (nz.pixels.length === 0) continue;
            let raw_target_pop = this.resolveZoneTargetPopulation(nz.population, year);
            if (raw_target_pop < 0) continue;
            let p3_target_pop = raw_target_pop*(nz.domain_fraction !== undefined ? nz.domain_fraction : 1.0);

            let current_sum = 0;
            let spec_px_count = 0;
            let urban_sum = 0;
            for (let y = 0; y < nz.pixels.length; y++) {
              let p_idx = nz.pixels[y];
              let v_idx = px_to_valid[p_idx];
              if (v_idx >= 0) {
                current_sum += calibrated[v_idx];
                urban_sum += urban_valid[v_idx];
                if (year <= 1900) {
                  let sm = context.pixel_spec_mask[p_idx];
                  if (sm >= 0) {
                    let se = context.specialist_entries[sm];
                    if (se && year >= se.domain[0] && year <= se.domain[1])
                      spec_px_count++;
                  }
                }
              }
            }

            let target_pop = p3_target_pop;
            if (year <= 1900 && spec_px_count > 0) {
              let spec_frac = spec_px_count/nz.pixels.length;
              let w_p3 = 1.0 - 0.35*spec_frac;
              target_pop = w_p3*p3_target_pop + (1 - w_p3)*(current_sum + urban_sum);
            }

            let min_rural_pop = Math.max(nz.pixels.length*0.02, Math.min(target_pop*0.06, current_sum*0.20));
            let rural_target_pop = Math.max(min_rural_pop, target_pop - urban_sum);
            let scalar = (current_sum > 0) ? (rural_target_pop/current_sum) : 1.0;
            let eff_log = Math.log(Math.max(1e-4, Math.min(1e4, scalar)));

            for (let y = 0; y < nz.pixels.length; y++) {
              let v_idx = px_to_valid[nz.pixels[y]];
              if (v_idx >= 0) log_mult[v_idx] = eff_log;
            }

            zone_targets.push({
              domain_code: (nz.dom2_pixels.length > nz.dom1_pixels.length) ? 2 : 1,
              max_year: active_nat_entry.domain[1],
              pixels: nz.pixels,
              target_pop: rural_target_pop
            });
          }
        }
      }

      //3. Spatially smooth `log_mult` across internal and cross-domain (`dom 1 <-> dom 2`) boundaries
      for (let p = 0; p < blur_passes; p++) {
        let horiz = new Float32Array(n_valid);
        for (let i = 0; i < n_valid; i++) {
          let idx = valid_indices[i];
          let row_start = Math.floor(idx/width)*width;
          let c = idx % width;
          let c0 = Math.max(0, c - blur_radius);
          let c1 = Math.min(width - 1, c + blur_radius);
          let sum = 0;
          let cnt = 0;
          for (let cx = c0; cx <= c1; cx++) {
            let n_idx = row_start + cx;
            if (pixel_domain[n_idx] > 0) {
              let nv = px_to_valid[n_idx];
              if (nv >= 0) {
                sum += log_mult[nv];
                cnt++;
              }
            }
          }
          horiz[i] = (cnt > 0) ? (sum/cnt) : log_mult[i];
        }

        for (let i = 0; i < n_valid; i++) {
          let idx = valid_indices[i];
          let r = Math.floor(idx/width);
          let c = idx % width;
          let r0 = Math.max(0, r - blur_radius);
          let r1 = Math.min(height - 1, r + blur_radius);
          let sum = 0;
          let cnt = 0;
          for (let ry = r0; ry <= r1; ry++) {
            let n_idx = ry*width + c;
            if (pixel_domain[n_idx] > 0) {
              let nv = px_to_valid[n_idx];
              if (nv >= 0) {
                sum += horiz[nv];
                cnt++;
              }
            }
          }
          log_mult[i] = (cnt > 0) ? (sum/cnt) : horiz[i];
        }
      }

      //4. Apply smoothed multipliers and re-normalise each zone so regional rural totals are conserved
      for (let i = 0; i < n_valid; i++)
        calibrated[i] = Math.max(1e-4, calibrated[i]*Math.exp(log_mult[i]));

      for (let i = 0; i < zone_targets.length; i++) {
        let zt = zone_targets[i];
        let z_sum = 0;
        for (let x = 0; x < zt.pixels.length; x++) {
          let v_idx = px_to_valid[zt.pixels[x]];
          if (v_idx >= 0) z_sum += calibrated[v_idx];
        }
        if (z_sum > 0 && zt.target_pop >= 0) {
          let corr = zt.target_pop/z_sum;
          for (let x = 0; x < zt.pixels.length; x++) {
            let v_idx = px_to_valid[zt.pixels[x]];
            if (v_idx >= 0) calibrated[v_idx] = Math.max(1e-4, calibrated[v_idx]*corr);
          }
        }
      }

      //5. Cross-domain (`dom 1 <-> dom 2`) seam blending within 6 pixels of internal borders
      {
        let seam_copy = new Float32Array(calibrated);
        for (let i = 0; i < n_valid; i++) {
          let cd = context.cross_dom_dist[i];
          if (cd > 6) continue;
          let idx = valid_indices[i];
          let r = Math.floor(idx/width);
          let c = idx % width;
          let rad = 4;
          let log_sum = 0;
          let w_sum = 0;
          for (let dy = -rad; dy <= rad; dy++) {
            let ry = r + dy;
            if (ry < 0 || ry >= height) continue;
            for (let dx = -rad; dx <= rad; dx++) {
              let cx = c + dx;
              if (cx < 0 || cx >= width) continue;
              let n_idx = ry*width + cx;
              if (pixel_domain[n_idx] > 0) {
                let nv = px_to_valid[n_idx];
                if (nv >= 0 && seam_copy[nv] > 0) {
                  let d2 = dx*dx + dy*dy;
                  let w = Math.exp(-d2/8.0);
                  log_sum += w*Math.log(seam_copy[nv]);
                  w_sum += w;
                }
              }
            }
          }
          if (w_sum > 0 && seam_copy[i] > 0) {
            let blend_w = 0.65*(1 - (cd - 1)/6.0);
            let log_orig = Math.log(seam_copy[i]);
            let log_smooth = log_sum/w_sum;
            calibrated[i] = Math.max(1e-4, Math.exp((1 - blend_w)*log_orig + blend_w*log_smooth));
          }
        }
      }

      //Return statement
      return {
        calibrated_rural: calibrated,
        zone_targets: zone_targets
      };
    }


    /**
     * Step E: Preserves calibrated POLARIS (`dom === 1` and `dom === 2` across `-10000..2025 AD`)
     * populations in `rasters_3.scaled_to_global/` and `rasters_4.interpolated_to_GHSL/` (`1800..2025 AD`).
     * @alias population_Substrata_russia.E_preserveDomainInGHSLInterpolatedRasters
     *
     * @param {Object} [arg0_options]
     */
    static E_preserveDomainInGHSLInterpolatedRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let context = this.A_loadManifestAndMasks(options);
      let ghsl_folder = path.join(
        context.root_dir,
        "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_4.interpolated_to_GHSL"
      );
      let global_folder = path.join(
        context.root_dir,
        "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_3.scaled_to_global"
      );
      let hyde_years = (options.hyde_years) ? options.hyde_years : context.hyde_years;
      let regions_folder = path.join(
        context.root_dir,
        "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_2.scaled_to_regions"
      );
      let years_1800_2025 = hyde_years.filter((yr) => yr >= 1800);

      //Guard clauses
      if (!fs.existsSync(global_folder)) return;

      //Function body
      if (fs.existsSync(regions_folder)) {
        for (let i = 0; i < hyde_years.length; i++) {
          let yr = hyde_years[i];
          let r2_path = path.join(regions_folder, `popc_${yr}.png`);
          let r3_path = path.join(global_folder, `popc_${yr}.png`);
          if (!fs.existsSync(r2_path) || !fs.existsSync(r3_path)) continue;

          let r2_png = PNG.sync.read(fs.readFileSync(r2_path));
          let r2_dv = new DataView(r2_png.data.buffer, r2_png.data.byteOffset, r2_png.data.byteLength);
          let r3_png = PNG.sync.read(fs.readFileSync(r3_path));
          let r3_dv = new DataView(r3_png.data.buffer, r3_png.data.byteOffset, r3_png.data.byteLength);
          let u_valid = this.loadUrbanValidForYear(context, yr);

          if (context.foreign_spillover_pairs && context.foreign_spillover_pairs.length > 0) {
            for (let s = 0; s < context.foreign_spillover_pairs.length; s++) {
              let s_idx = context.foreign_spillover_pairs[s][0];
              let s4 = s_idx*4;
              let v2 = this.readPositiveFloat32(r2_png.data, r2_dv, s4);
              if (v2 > 0) {
                r3_dv.setFloat32(s4, v2, false);
              } else {
                r3_png.data[s4] = 0;
                r3_png.data[s4 + 1] = 0;
                r3_png.data[s4 + 2] = 0;
                r3_png.data[s4 + 3] = 0;
              }
            }
          }
          for (let x = 0; x < context.n_valid; x++) {
            let idx = context.valid_indices[x];
            let p4 = idx*4;
            let v2 = this.readPositiveFloat32(r2_png.data, r2_dv, p4);
            let v_out = Math.max(u_valid[x] + 1e-4, v2);
            if (v_out > 0) {
              r3_dv.setFloat32(p4, v_out, false);
            } else {
              r3_png.data[p4] = 0;
              r3_png.data[p4 + 1] = 0;
              r3_png.data[p4 + 2] = 0;
              r3_png.data[p4 + 3] = 0;
            }
          }

          fs.writeFileSync(r3_path, PNG.sync.write(r3_png));
        }
      }

      if (!fs.existsSync(ghsl_folder)) return;

      for (let i = 0; i < years_1800_2025.length; i++) {
        let yr = years_1800_2025[i];
        let r3_path = path.join(global_folder, `popc_${yr}.png`);
        let r4_path = path.join(ghsl_folder, `popc_${yr}.png`);
        if (!fs.existsSync(r3_path) || !fs.existsSync(r4_path)) continue;

        let r3_png = PNG.sync.read(fs.readFileSync(r3_path));
        let r3_dv = new DataView(r3_png.data.buffer, r3_png.data.byteOffset, r3_png.data.byteLength);
        let r4_png = PNG.sync.read(fs.readFileSync(r4_path));
        let r4_dv = new DataView(r4_png.data.buffer, r4_png.data.byteOffset, r4_png.data.byteLength);
        let u_valid = this.loadUrbanValidForYear(context, yr);

        for (let x = 0; x < context.n_valid; x++) {
          let idx = context.valid_indices[x];
          let p4 = idx*4;
          let v3 = this.readPositiveFloat32(r3_png.data, r3_dv, p4);
          let w_feather = context.feather_weights[x];
          if (w_feather < 0.999 && context.foreign_anchor_idx[x] >= 0) {
            let f_idx = context.foreign_anchor_idx[x];
            let f_val = this.readPositiveFloat32(r4_png.data, r4_dv, f_idx*4);
            if (f_val > 0 && v3 > 0) {
              let f_clamped = Math.max(v3*0.55, Math.min(v3*1.45, f_val));
              v3 = w_feather*v3 + (1 - w_feather)*f_clamped;
            }
          }
          let v_out = Math.max(u_valid[x] + 1e-4, v3);
          if (v_out > 0) {
            r4_dv.setFloat32(p4, v_out, false);
          } else {
            r4_png.data[p4] = 0;
            r4_png.data[p4 + 1] = 0;
            r4_png.data[p4 + 2] = 0;
            r4_png.data[p4 + 3] = 0;
          }
        }

        fs.writeFileSync(r4_path, PNG.sync.write(r4_png));
      }
    }


    /**
     * Helper: Loads the `stadester_urban_<year>.png` (`>= 5,000`) raster and `< 5,000` settlement populations
     * from `stadester.json` onto the valid domain pixels (`context.n_valid`) so all settlements are anchored in
     * the regional substrata `popc` mosaic without inflating zone totals.
     * @alias population_Substrata_russia.loadUrbanValidForYear
     *
     * @param {Object} arg0_context
     * @param {number} arg1_year
     *
     * @returns {Float32Array}
     */
    static loadUrbanValidForYear (arg0_context, arg1_year) {
      //Convert from parameters
      let context = arg0_context;
      let year = Number(arg1_year);

      //Declare local instance variables
      let stadester_dump_path = path.join(
        context.root_dir,
        "histmap/1.data_raw/population_Stadester/uud/stadester.json"
      );
      let sub_urban_data = null;
      let urban_path = path.join(
        context.root_dir,
        "histmap/2.data_cleaning/population_Stadester/stadester_urban_rasters",
        `stadester_urban_${year}.png`
      );
      let urban_valid = new Float32Array(context.n_valid);

      //Function body
      if (fs.existsSync(urban_path)) {
        let u_png = PNG.sync.read(fs.readFileSync(urban_path));
        let u_dv = new DataView(u_png.data.buffer, u_png.data.byteOffset, u_png.data.byteLength);
        for (let i = 0; i < context.n_valid; i++) {
          let idx = context.valid_indices[i];
          let val = this.readPositiveFloat32(u_png.data, u_dv, idx*4);
          if (val > 0) urban_valid[i] = val;
        }
      }

      if (!global.population_Stadester_rasters && typeof require !== "undefined") {
        let rasters_js = path.join(
          context.root_dir,
          "histmap/2.data_cleaning/population_Stadester/stadester_rasters.js"
        );
        if (fs.existsSync(rasters_js)) {
          try { require(rasters_js); } catch (e) {}
        }
      }

      if (global.population_Stadester_rasters && global.population_Stadester_rasters.getSubUrbanSettlementsData) {
        sub_urban_data = global.population_Stadester_rasters.getSubUrbanSettlementsData(year, {
          stadester_file_path: stadester_dump_path
        });
        if (sub_urban_data) {
          for (let i = 0; i < context.n_valid; i++) {
            let idx = context.valid_indices[i];
            let sub_val = sub_urban_data[idx];
            if (sub_val > 0) urban_valid[i] += sub_val;
          }
        }
      }

      //Return statement
      return urban_valid;
    }


    /**
     * Step D: Executes the full timeseries rural calibration, temporal log-Laplacian smoothing, urban-plus-rural
     * synthesis, foreign outlier-mask spillover cleanup, and clamped foreign-neighbour border compositing into
     * `population_Substrata.outlier_removal/rasters_2.scaled_to_regions/`.
     * @alias population_Substrata_russia.processRasters
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Promise<Object>}
     */
    static async processRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let calibrated_series = [];
      let context = this.A_loadManifestAndMasks(options);
      let hyde_years = (options.years) ? options.years : ((options.hyde_years) ? options.hyde_years : context.hyde_years);
      let n_valid = context.n_valid;
      let n_years = hyde_years.length;
      let out_folder = options.output_folder ?
        options.output_folder :
        path.join(context.root_dir, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_2.scaled_to_regions");
      let px_to_valid = context.pixel_to_valid;
      let start_ms = Date.now();
      let temp_weight = (context.manifest.smoothing && Number.isFinite(context.manifest.smoothing.temporal_log_Laplacian_weight)) ?
        context.manifest.smoothing.temporal_log_Laplacian_weight : 0.15;
      let urban_series = [];
      let year_summaries = {};
      let zone_targets_series = [];

      //Function body
      console.log(`[population_Substrata_russia] Calibrating & mosaicking ${n_years} benchmark years across ${n_valid} domain pixels...`);

      for (let i = 0; i < n_years; i++) {
        let yr = hyde_years[i];
        let urban_valid = this.loadUrbanValidForYear(context, yr);
        let mosaic_valid = this.B_mosaicKrigedSubstrataForYear(context, yr, urban_valid);
        let cal_obj = this.C_computeCalibratedFieldForYear(context, mosaic_valid, yr, urban_valid);
        calibrated_series.push(cal_obj.calibrated_rural);
        urban_series.push(urban_valid);
        zone_targets_series.push(cal_obj.zone_targets);
      }

      let temporally_smoothed = calibrated_series.map((arr) => new Float32Array(arr));
      for (let t = 1; t < n_years - 1; t++) {
        let yr = hyde_years[t];
        let prev_arr = calibrated_series[t - 1];
        let curr_arr = calibrated_series[t];
        let next_arr = calibrated_series[t + 1];
        let out_arr = temporally_smoothed[t];
        let dt_prev = Math.max(1, yr - hyde_years[t - 1]);
        let dt_next = Math.max(1, hyde_years[t + 1] - yr);
        let alpha_t = dt_prev/(dt_prev + dt_next);

        for (let i = 0; i < n_valid; i++) {
          let v_curr = curr_arr[i];
          let v_prev = prev_arr[i];
          let v_next = next_arr[i];
          if (v_curr > 0 && v_prev > 0 && v_next > 0) {
            let log_interp = (1 - alpha_t)*Math.log(v_prev) + alpha_t*Math.log(v_next);
            let log_curr = Math.log(v_curr);
            out_arr[i] = Math.max(1e-4, Math.exp((1 - temp_weight)*log_curr + temp_weight*log_interp));
          }
        }

        let z_targets = zone_targets_series[t];
        for (let z_idx = 0; z_idx < z_targets.length; z_idx++) {
          let zt = z_targets[z_idx];
          let z_sum = 0;
          for (let x = 0; x < zt.pixels.length; x++) {
            let v_idx = px_to_valid[zt.pixels[x]];
            if (v_idx >= 0) z_sum += out_arr[v_idx];
          }
          if (z_sum > 0 && zt.target_pop >= 0) {
            let corr = zt.target_pop/z_sum;
            for (let x = 0; x < zt.pixels.length; x++) {
              let v_idx = px_to_valid[zt.pixels[x]];
              if (v_idx >= 0) out_arr[v_idx] = Math.max(1e-4, out_arr[v_idx]*corr);
            }
          }
        }
      }

      if (!fs.existsSync(out_folder)) fs.mkdirSync(out_folder, { recursive: true });

      for (let t = 0; t < n_years; t++) {
        let yr = hyde_years[t];
        let cal_arr = temporally_smoothed[t];
        let u_arr = urban_series[t];
        let target_png_path = path.join(out_folder, `popc_${yr}.png`);
        let fallback_png_path = path.join(
          context.root_dir,
          "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_1.northern_america",
          `popc_${yr}.png`
        );
        let src_png_path = fs.existsSync(target_png_path) ?
          target_png_path :
          (fs.existsSync(fallback_png_path) ? fallback_png_path : null);
        if (!src_png_path) continue;

        let base_png = PNG.sync.read(fs.readFileSync(src_png_path));
        let base_dv = new DataView(base_png.data.buffer, base_png.data.byteOffset, base_png.data.byteLength);
        let rus_sum = 0;
        let bu_sum = 0;

        //Clean foreign land border pixels (`pixel_domain === 0`) where Russian outlier masks spilled across `sub_iso_cr.asc`
        if (context.foreign_spillover_pairs && context.foreign_spillover_pairs.length > 0) {
          for (let s = 0; s < context.foreign_spillover_pairs.length; s++) {
            let s_idx = context.foreign_spillover_pairs[s][0];
            let c_idx = context.foreign_spillover_pairs[s][1];
            let clean_val = this.readPositiveFloat32(base_png.data, base_dv, c_idx*4);
            let s4 = s_idx*4;
            if (clean_val > 0) {
              base_dv.setFloat32(s4, clean_val, false);
            } else {
              base_png.data[s4] = 0;
              base_png.data[s4 + 1] = 0;
              base_png.data[s4 + 2] = 0;
              base_png.data[s4 + 3] = 0;
            }
          }
        }

        for (let i = 0; i < n_valid; i++) {
          let idx = context.valid_indices[i];
          let dom = context.pixel_domain[idx];
          let p4 = idx*4;

          let u_val = u_arr[i];
          let w_feather = context.feather_weights[i];
          let r_val = Math.max(1e-4, cal_arr[i]);
          let r_feathered = r_val;

          if (w_feather < 0.999 && context.foreign_anchor_idx[i] >= 0) {
            let f_idx = context.foreign_anchor_idx[i];
            let f_val = this.readPositiveFloat32(base_png.data, base_dv, f_idx*4);
            if (f_val > 0) {
              let f_clamped = Math.max(r_val*0.55, Math.min(r_val*1.45, f_val));
              r_feathered = Math.max(1e-4, w_feather*r_val + (1 - w_feather)*f_clamped);
            }
          }

          let final_val = u_val + r_feathered;
          if (final_val > 0) {
            base_dv.setFloat32(p4, final_val, false);
          } else {
            base_png.data[p4] = 0;
            base_png.data[p4 + 1] = 0;
            base_png.data[p4 + 2] = 0;
            base_png.data[p4 + 3] = 0;
          }

          if (dom === 1) rus_sum += final_val;
          else if (dom === 2) bu_sum += final_val;
        }

        fs.writeFileSync(target_png_path, PNG.sync.write(base_png));
        year_summaries[yr] = {
          russia_crimea: Math.round(rus_sum),
          belarus_ukraine: Math.round(bu_sum),
          combined: Math.round(rus_sum + bu_sum)
        };
      }

      console.log(`[population_Substrata_russia] Completed compositing ${n_years} benchmark rasters in ${((Date.now() - start_ms)/1000).toFixed(2)}s.`);

      //Return statement
      return {
        elapsed_seconds: Number(((Date.now() - start_ms)/1000).toFixed(2)),
        year_summaries: year_summaries
      };
    }


    /**
     * Helper: Safely reads a positive big-endian IEEE-754 `float32` value from a PNG RGBA buffer.
     * @alias population_Substrata_russia.readPositiveFloat32
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

      //Return statement
      return population_Substrata_russia_masks.readPositiveFloat32(png_data, data_view, p4);
    }


    /**
     * Helper: Resolves a region's target population at `arg1_year` from its `population` dictionary,
     * supporting exact keys, `[min, max]` arrays, or linear interpolation between nearest benchmark years.
     * @alias population_Substrata_russia.resolveZoneTargetPopulation
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
      function extractScalar (val) {
        if (Array.isArray(val) && val.length >= 2) {
          let a = Number(val[0]);
          let b = Number(val[1]);
          if (a > 0 && b > 0) return Math.sqrt(a*b);
          return 0.5*(a + b);
        }
        let n = Number(val);
        return Number.isFinite(n) ? n : -1;
      }

      if (pop_dict[year] !== undefined) {
        let exact = extractScalar(pop_dict[year]);
        if (exact >= 0) return exact;
      }

      let yrs = Object.keys(pop_dict).map(Number).filter(Number.isFinite).sort((a, b) => a - b);
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
  module.exports = global.population_Substrata_russia;
