//Import modules
let fs = require("fs");
let path = require("path");
let { PNG } = require("pngjs");
let { ViscountHUResidualKriging } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/centaur/ViscountHUResidualKriging.js"));
let { ViscountMaternKriging } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountMaternKriging.js"));
let { ViscountRuralSuitability } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountRuralSuitability.js"));
let { ViscountUrbanMask } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountUrbanMask.js"));

//Initialise functions
{
  /**
   * Executes POLARIS-grade Non-Stationary Matérn (`nu = 3/2`) Multi-Repository Archaeological + Terra Preta (ADE)
   * Residual Kriging across Operation Viscount Project PRETA (`sites_preta_amazon_brazil`) and synthesises all 128
   * HYDE benchmark rural suitability GeoPNGs (`-10000` to `2025 AD`).
   *
   * Explicitly couples the dedicated kriged Terra Preta (`09_terra_preta_ade_anthrosol`) anthropogenic dark-earth
   * density surface into pre-Columbian and early-contact Amazonian & Guianese horizons (`-4000` to `1650 AD`),
   * while enforcing `ViscountUrbanMask` extended HYDE urban suppression and genuine dasymetric habitability.
   *
   * @class PretaKrigingRunner
   */
  global.PretaKrigingRunner = class {
    static CONFIG_REL = "histmap/1.data_raw/population_regional/PRETA/_shared/sites_preta_amazon_brazil/config/sites_preta_amazon_brazil.json5";
    static PROJECT_ROOT = path.resolve(__dirname, "../../../../../..");

    /**
     * Computes empirical Amazonian Dark Earth (Terra Preta) coupling weight for a given historical year.
     * Peaks at 0.38 during 700-1542 AD in the Amazon/Guianas biome and tapers smoothly to 0 after 1750 AD.
     * @alias PretaKrigingRunner.getTerraPretaBlendWeight
     *
     * @param {number} arg0_year
     *
     * @returns {number}
     */
    static getTerraPretaBlendWeight (arg0_year) {
      //Convert from parameters
      let yr = Number(arg0_year);

      //Guard clauses
      if (yr < -5000 || yr > 1750)
        return 0.0;

      //Function body
      if (yr < -1000)
        return 0.14*(yr + 5000)/4000;
      if (yr < 1000)
        return 0.14 + 0.24*(yr + 1000)/2000;
      if (yr <= 1550)
        return 0.38;

      //Return statement
      return 0.38*Math.max(0, (1750 - yr)/200);
    }

    /**
     * Reads a Big-Endian uint32 RGBA HYDE raster (`popc_*AD.png`) over valid mask indices.
     * @alias PretaKrigingRunner.readUInt32RasterValid
     *
     * @param {string} arg0_abs_path
     * @param {Int32Array} arg1_valid_indices
     *
     * @returns {Float32Array|null}
     */
    static readUInt32RasterValid (arg0_abs_path, arg1_valid_indices) {
      //Convert from parameters
      let abs_path = arg0_abs_path;
      let valid_indices = arg1_valid_indices;

      //Guard clauses
      if (!fs.existsSync(abs_path))
        return null;

      //Declare local instance variables
      let buf = Buffer.from(PNG.sync.read(fs.readFileSync(abs_path)).data);
      let out = new Float32Array(valid_indices.length);

      //Function body
      for (let i = 0; i < valid_indices.length; i++) {
        let v = buf.readUInt32BE(valid_indices[i]*4);

        out[i] = (Number.isFinite(v) && v > 0) ? v : 0;
      }

      //Return statement
      return out;
    }

    /**
     * Reads a Big-Endian float32 RGBA GeoPNG over valid mask indices.
     * @alias PretaKrigingRunner.readFloatRasterValid
     *
     * @param {string} arg0_abs_path
     * @param {Int32Array} arg1_valid_indices
     *
     * @returns {Float32Array|null}
     */
    static readFloatRasterValid (arg0_abs_path, arg1_valid_indices) {
      //Convert from parameters
      let abs_path = arg0_abs_path;
      let valid_indices = arg1_valid_indices;

      //Guard clauses
      if (!fs.existsSync(abs_path))
        return null;

      //Declare local instance variables
      let buf = Buffer.from(PNG.sync.read(fs.readFileSync(abs_path)).data);
      let out = new Float32Array(valid_indices.length);

      //Function body
      for (let i = 0; i < valid_indices.length; i++) {
        let v = buf.readFloatBE(valid_indices[i]*4);

        out[i] = (Number.isFinite(v) && v > 0) ? v : 0;
      }

      //Return statement
      return out;
    }

    /**
     * Computes normalised chronological Terra Preta (ADE) anthropogenic population multiplier schedule (`0..1`).
     * Captures the multi-century sedentary biomass required to form deep Terra Preta anthrosols across
     * Formative-to-Contact Amazonia (-3000 to 1550 AD) before tapering smoothly to 0 by 1750 AD during colonial collapse.
     * @alias PretaKrigingRunner.getTerraPretaEpochFactor
     *
     * @param {number} arg0_year
     *
     * @returns {number}
     */
    static getTerraPretaEpochFactor (arg0_year) {
      let yr = Number(arg0_year);
      if (yr <= -3000 || yr >= 1750) return 0.0;
      if (yr < -500) return 0.35*(yr + 3000)/2500;
      if (yr < 500) return 0.35 + 0.50*(yr + 500)/1000;
      if (yr < 900) return 0.85 + 0.15*(yr - 500)/400;
      if (yr <= 1550) return 1.00;
      return Math.max(0.0, (1750 - yr)/200);
    }

    /**
     * Computes smooth C1-continuous normalised Terra Preta (ADE) anthropogenic intensity index (`0..2.8`)
     * over valid pixels from the already lowland-tapered `09_terra_preta_ade_anthrosol` surface.
     * @alias PretaKrigingRunner.computeTerraPretaIntensityIndex
     *
     * @param {Float32Array} arg0_tp_field
     *
     * @returns {Float32Array}
     */
    static computeTerraPretaIntensityIndex (arg0_tp_field) {
      let tp = arg0_tp_field;
      let out = new Float32Array(tp ? tp.length : 0);
      if (!tp || tp.length === 0) return out;

      let pos = [];
      for (let i = 0; i < tp.length; i++) {
        if (tp[i] > 1e-4) pos.push(tp[i]);
      }
      if (pos.length === 0) return out;
      pos.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
      let p90 = Math.max(1e-4, pos[Math.min(pos.length - 1, Math.floor(pos.length*0.90))]);

      for (let i = 0; i < tp.length; i++) {
        if (tp[i] > 1e-4) {
          let rel = tp[i]/p90;
          out[i] = Math.min(2.0, Math.pow(rel, 0.72));
        }
      }
      return out;
    }

    /**
     * Step B: Synthesises all 128 HYDE benchmark population suitability rasters (`2.population_rasters/popc_<yr>.png`)
     * by interpolating calibrated Matérn archaeological surfaces, coupling the dedicated Terra Preta (ADE) surface
     * in tropical Amazonia/Guianas (`lat >= -18`, `elev < 1250 m`), and transitioning smoothly across 1650-1950 AD into
     * urban-masked rural carrying capacity & GHSL census footprints.
     * @alias PretaKrigingRunner.B_generatePopulationRasters
     *
     * @param {Object} arg0_surface_bundle
     *
     * @returns {Object}
     */
    static B_generatePopulationRasters (arg0_surface_bundle) {
      //Convert from parameters
      let surface = arg0_surface_bundle;
      let rk_cfg = (surface && surface.kriging_bundle && surface.kriging_bundle.config) ? surface.kriging_bundle.config : {};

      //Delegate to unified Viscount dasymetric residual kriging engine when active, then couple lowland Terra Preta (ADE) anthropogenic biomass in pre-contact epochs
      if (rk_cfg.kriging_config && rk_cfg.kriging_config.residual_kriging_mode === "hu_hyde_residual") {
        let base_res = ViscountHUResidualKriging.generateAllBenchmarkPopulationRasters(surface, { is_polynesia: false });
        let tp_fld = (surface && surface.fields) ? surface.fields["09_terra_preta_ade_anthrosol"] : null;
        if (tp_fld && surface.kriging_bundle && surface.kriging_bundle.mask_data) {
          let tp_idx = this.computeTerraPretaIntensityIndex(tp_fld);
          let v_idx = surface.kriging_bundle.mask_data.valid_indices;
          let hab_m = (surface.bio_covs && surface.bio_covs.hab_mask) ? surface.bio_covs.hab_mask : null;
          let hyde_years = rk_cfg.kriging_config.all_hyde_years || [];
          let out_dir = path.join(surface.kriging_bundle.mask_data.domain_dir, rk_cfg.output_population_rasters_subfolder || "2.population_rasters");
          let boosted_cnt = 0;

          for (let h = 0; h < hyde_years.length; h++) {
            let yr = Number(hyde_years[h]);
            let w_ep = this.getTerraPretaEpochFactor(yr);
            if (w_ep <= 0) continue;
            let fp = path.join(out_dir, `popc_${yr}.png`);
            if (!fs.existsSync(fp)) continue;

            let png = PNG.sync.read(fs.readFileSync(fp));
            let dv = new DataView(png.data.buffer, png.data.byteOffset, png.data.byteLength);
            let sum_before = 0;
            let sum_after = 0;
            let tmp = new Float32Array(v_idx.length);
            let alpha_ade = 0.55*w_ep;

            for (let i = 0; i < v_idx.length; i++) {
              let px = v_idx[i]*4;
              let val = dv.getFloat32(px, false);
              if (!Number.isFinite(val) || val <= 0 || (hab_m && yr <= 1650 && hab_m[i] === 0)) {
                tmp[i] = 0;
                continue;
              }
              sum_before += val;
              let mult = 1.0 + alpha_ade*tp_idx[i];
              let nv = val*mult;
              tmp[i] = nv;
              sum_after += nv;
            }
            if (sum_before > 0 && sum_after > 0) {
              let norm_sc = sum_before/sum_after;
              for (let i = 0; i < v_idx.length; i++) {
                let px = v_idx[i]*4;
                let nv = tmp[i]*norm_sc;
                if (nv > 0) {
                  dv.setFloat32(px, nv, false);
                } else {
                  png.data[px] = 0;
                  png.data[px + 1] = 0;
                  png.data[px + 2] = 0;
                  png.data[px + 3] = 0;
                }
              }
              fs.writeFileSync(fp, PNG.sync.write(png, { colorType: 6, deflateLevel: 6 }));
              boosted_cnt++;
            }
          }
          console.log(`[PRETA Terra Preta Coupling] Applied anthropogenic ADE biomass boost to ${boosted_cnt} pre-contact/early-contact benchmark popc rasters.`);
        }
        return base_res;
      }

      //Declare local instance variables
      let bio_covs = surface.bio_covs;
      let bundle = surface.kriging_bundle;
      let cfg = bundle.config;
      let grid_h = bundle.mask_data.grid_height;
      let grid_w = bundle.mask_data.grid_width;
      let hab_mask = bio_covs ? bio_covs.hab_mask : null;
      let horizons_cfg = (cfg.kriging_config && Array.isArray(cfg.kriging_config.chronological_horizons)) ?
        cfg.kriging_config.chronological_horizons : [];
      let hyde_years = cfg.kriging_config.all_hyde_years || [];
      let n_valid = bundle.mask_data.valid_cell_count;
      let out_dir = path.join(bundle.mask_data.domain_dir, cfg.output_population_rasters_subfolder || "2.population_rasters");
      let period_surfaces = surface.fields || surface.raw_potentials || {};
      let tp_surface = period_surfaces["09_terra_preta_ade_anthrosol"] || null;
      let valid_indices = bundle.mask_data.valid_indices;

      //Function body
      fs.mkdirSync(out_dir, { recursive: true });

      //Precompute tropical Amazonia/Guianas smooth latitude weight for Terra Preta coupling (1.0 north of -14, tapering to 0 at -19)
      let tp_lat_weight = new Float32Array(n_valid);
      let tp_norm = new Float32Array(n_valid);
      let tp_sum = 0;

      for (let i = 0; i < n_valid; i++) {
        let row = Math.floor(valid_indices[i]/grid_w);
        let lat = 90.0 - (row + 0.5)*(180.0/grid_h);
        let w_lat = (lat >= -14.0) ? 1.0 : ((lat <= -19.0) ? 0.0 : (lat + 19.0)/5.0);

        tp_lat_weight[i] = w_lat;
        if (tp_surface && w_lat > 0) {
          let v = Math.max(0, tp_surface[i])*w_lat;
          tp_norm[i] = v;
          tp_sum += v;
        }
      }
      if (tp_sum > 0) {
        for (let i = 0; i < n_valid; i++) tp_norm[i] = tp_norm[i]/tp_sum;
      }

      //Normalise each chronological calibrated period surface to unit sum
      let horizon_arrays = [];

      for (let i = 0; i < horizons_cfg.length; i++) {
        let h_cfg = horizons_cfg[i];
        let pkey = (Array.isArray(h_cfg.active_periods) && h_cfg.active_periods.length > 0) ? h_cfg.active_periods[0] : "";
        let src = period_surfaces[pkey];
        let arr = new Float32Array(n_valid);
        let s_tot = 0;

        if (src) {
          for (let x = 0; x < n_valid; x++) {
            let v = Math.max(0, src[x]);
            arr[x] = v;
            s_tot += v;
          }
        }
        if (s_tot > 0) {
          for (let x = 0; x < n_valid; x++) arr[x] = arr[x]/s_tot;
        }
        horizon_arrays.push({ arr: arr, year: Number(h_cfg.year) });
      }
      horizon_arrays.sort(function (arg0_a, arg1_b) { return arg0_a.year - arg1_b.year; });

      //Preload modern HYDE & GHSL pop rasters for colonial-to-modern transition (1700-2025)
      let ghs_pop_dir = path.join(this.PROJECT_ROOT, "histmap/1.data_raw/population_GHSL/population_rasters/2.rasters");
      let hyde_popc_dir = path.join(this.PROJECT_ROOT, cfg.kriging_config.covariate_paths.hyde_popc_folder);
      let hyde_raw_dir = path.join(this.PROJECT_ROOT, cfg.kriging_config.covariate_paths.hyde_raw_rasters_folder);
      let urban_cache = surface.hab_cache || new Map();
      let mod_cache = new Map();

      let loadRuralPrior = (arg0_yr) => {
        let y_key = Math.max(1700, Math.min(2023, Math.round(arg0_yr/10)*10));
        if (arg0_yr >= 2000) y_key = Math.min(2023, arg0_yr);
        if (mod_cache.has(y_key)) return mod_cache.get(y_key);

        let arr = null;
        if (y_key >= 1975) {
          let ghs_y = Math.min(2025, Math.max(1975, Math.round(y_key/5)*5));
          let ghs_p = path.join(ghs_pop_dir, `GHS_POP_E${ghs_y}.png`);
          arr = this.readFloatRasterValid(ghs_p, valid_indices);
        }
        if (!arr && y_key < 1900) {
          //Use SVEA canonical urban-masked & inpainted HYDE popc prior (returns Float32Array of length n_valid)
          let masked_arr = ViscountUrbanMask.loadUrbanMaskedHYDEPopcRaster(bundle.mask_data, y_key, urban_cache, cfg);
          if (masked_arr && masked_arr.length === n_valid) {
            let s_chk = 0;
            for (let x = 0; x < n_valid; x++) s_chk += masked_arr[x];
            if (s_chk > 0) arr = masked_arr;
          }
        }
        if (!arr) {
          let y_str = (y_key < 0) ? `${Math.abs(y_key)}BC` : `${y_key}AD`;
          let p1 = path.join(hyde_popc_dir, `popc_${y_str}.png`);
          let p2 = path.join(hyde_raw_dir, `popc_${y_str}.png`);
          let use_p = fs.existsSync(p1) ? p1 : (fs.existsSync(p2) ? p2 : "");
          if (use_p) arr = this.readFloatRasterValid(use_p, valid_indices);
        }
        mod_cache.set(y_key, arr);
        return arr;
      };

      let f_buf = new ArrayBuffer(4);
      let f_dv = new DataView(f_buf);

      for (let h_idx = 0; h_idx < hyde_years.length; h_idx++) {
        let yr = Number(hyde_years[h_idx]);
        let arch_field = new Float32Array(n_valid);

        //Chronological piecewise-linear interpolation between bracketing Matérn horizons
        if (yr <= horizon_arrays[0].year) {
          arch_field.set(horizon_arrays[0].arr);
        } else if (yr >= horizon_arrays[horizon_arrays.length - 1].year) {
          arch_field.set(horizon_arrays[horizon_arrays.length - 1].arr);
        } else {
          for (let k = 0; k < horizon_arrays.length - 1; k++) {
            let ha = horizon_arrays[k];
            let hb = horizon_arrays[k + 1];
            if (yr >= ha.year && yr <= hb.year) {
              let t = (yr - ha.year)/Math.max(1, hb.year - ha.year);
              for (let x = 0; x < n_valid; x++)
                arch_field[x] = ha.arr[x]*(1 - t) + hb.arr[x]*t;
              break;
            }
          }
        }

        //Couple kriged Terra Preta (ADE) anthropogenic surface in pre-Columbian & early-contact Amazonia
        let w_tp = this.getTerraPretaBlendWeight(yr);
        if (w_tp > 0 && tp_sum > 0) {
          //Compute Amazon-zone arch sum so Terra Preta redistributes density authentically along ADE bluffs without stealing non-Amazon mass
          let amz_arch_sum = 0;
          for (let x = 0; x < n_valid; x++) {
            if (tp_lat_weight[x] > 0) amz_arch_sum += arch_field[x]*tp_lat_weight[x];
          }
          if (amz_arch_sum > 0) {
            for (let x = 0; x < n_valid; x++) {
              let wl = tp_lat_weight[x];
              if (wl > 0) {
                let local_w = w_tp*wl;
                arch_field[x] = arch_field[x]*(1 - local_w) + (tp_norm[x]*amz_arch_sum)*local_w;
              }
            }
          }
        }

        //Transition smoothly after 1600 AD into colonial/modern urban-masked HYDE & GHSL demographic gravity
        let out_field = new Float32Array(n_valid);
        out_field.set(arch_field);

        if (yr > 1600) {
          let mod_rur = loadRuralPrior(yr);
          if (mod_rur) {
            let arch_sum = 0;
            let mod_sum = 0;
            for (let x = 0; x < n_valid; x++) {
              arch_sum += arch_field[x];
              mod_sum += mod_rur[x];
            }
            let mod_scale = (mod_sum > 0 && arch_sum > 0) ? arch_sum/mod_sum : 1.0;
            let w_mod = Math.min(0.94, 0.94*Math.max(0, (yr - 1600)/280));
            for (let x = 0; x < n_valid; x++)
              out_field[x] = arch_field[x]*(1 - w_mod) + (mod_rur[x]*mod_scale)*w_mod;
          }
        }

        //Enforce strict dasymetric habitability suppression on uninhabitable pixels pre-1700
        let final_sum = 0;
        for (let x = 0; x < n_valid; x++) {
          if (yr <= 1650 && hab_mask && hab_mask[x] === 0) {
            out_field[x] = 0;
          } else if (out_field[x] <= 0 || !Number.isFinite(out_field[x])) {
            out_field[x] = 0;
          } else {
            final_sum += out_field[x];
          }
        }

        //Rescale to realistic macro-domain inhabitant scale (~10^6) so float32 stays well above underflow
        let scale_factor = (final_sum > 0) ? 1000000.0/final_sum : 0;
        let img = new PNG({ colorType: 6, height: grid_h, width: grid_w });

        for (let x = 0; x < n_valid; x++) {
          let v = out_field[x]*scale_factor;
          if (v <= 0) continue;
          let px = valid_indices[x]*4;

          f_dv.setFloat32(0, v, false);
          img.data[px] = f_dv.getUint8(0);
          img.data[px + 1] = f_dv.getUint8(1);
          img.data[px + 2] = f_dv.getUint8(2);
          img.data[px + 3] = f_dv.getUint8(3);
        }
        fs.writeFileSync(path.join(out_dir, `popc_${yr}.png`), PNG.sync.write(img, { colorType: 6, deflateLevel: 6 }));
      }

      //Return statement
      return { generated_years: hyde_years.length, out_dir: out_dir };
    }

    /**
     * Executes full Matérn kriging (8 archaeological horizons + 1 Terra Preta ADE surface) & 128-year synthesis.
     * @alias PretaKrigingRunner.run
     *
     * @returns {Object}
     */
    static run () {
      let t0 = Date.now();
      let domain = ViscountMaternKriging.A_loadDomainConfigAndSites(this.CONFIG_REL, { project_root: this.PROJECT_ROOT });
      let obs = ViscountMaternKriging.B_computeEmpiricalBayesIntensities(domain);
      let krig = ViscountMaternKriging.C_fitTwoScaleNonStationaryMatern(obs);
      let surface = ViscountMaternKriging.E_fitCarryCapacityResidualSurface(krig);

      //Apply smooth continuous dasymetric habitability taper across all 8 continental horizons + organic Amazonian ADE domain on Terra Preta
      //(Zero hard centroid-radius discs: preserves natural fluvial/coastal dendritic geometry while preventing wasteland leakage)
      if (surface && surface.fields) {
        let v_idx = surface.kriging_bundle.mask_data.valid_indices;
        let gw = surface.kriging_bundle.mask_data.grid_width;
        let gh = surface.kriging_bundle.mask_data.grid_height;
        let cell_area = surface.kriging_bundle.mask_data.cell_land_area;
        let elev_v = surface.bio_covs ? surface.bio_covs.elev_valid : null;
        let hab_m = surface.bio_covs ? surface.bio_covs.hab_mask : null;
        let hyde_1000 = this.readFloatRasterValid(
          path.join(this.PROJECT_ROOT, "histmap/2.data_cleaning/landuse_HYDE/rasters/popc_1000AD.png"),
          v_idx
        );
        let hyde_1500 = this.readFloatRasterValid(
          path.join(this.PROJECT_ROOT, "histmap/2.data_cleaning/landuse_HYDE/rasters/popc_1500AD.png"),
          v_idx
        );
        let hyde_1900 = this.readFloatRasterValid(
          path.join(this.PROJECT_ROOT, "histmap/2.data_cleaning/landuse_HYDE/rasters/popc_1900AD.png"),
          v_idx
        );

        let f_keys = Object.keys(surface.fields);
        for (let k_idx = 0; k_idx < f_keys.length; k_idx++) {
          let fk = f_keys[k_idx];
          let fld = surface.fields[fk];
          let is_tp = (fk === "09_terra_preta_ade_anthrosol");
          let raw_sum = 0;
          let kept_sum = 0;

          for (let i = 0; i < fld.length; i++) raw_sum += fld[i];
          for (let i = 0; i < fld.length; i++) {
            let g_px = v_idx[i];
            let h_dens = Math.max(
              hyde_1500 ? hyde_1500[i] : 0,
              hyde_1000 ? hyde_1000[i] : 0,
              hyde_1900 ? 0.15*hyde_1900[i] : 0
            )/Math.max(1.0, cell_area[i]);

            if (hab_m && hab_m[i] === 0) {
              fld[i] = 0;
              continue;
            }
            if (is_tp) {
              let row = Math.floor(g_px/gw);
              let col = g_px % gw;
              let lat = 90.0 - (row + 0.5)*(180.0/gh);
              let lon = -180.0 + (col + 0.5)*(360.0/gw);
              let e_m = elev_v ? elev_v[i] : 150.0;
              //Smooth C1 cosine taper restricting Terra Preta anthrosols to tropical lowland Amazonia, Llanos de Moxos & Guianas (elev < 1250m)
              let lat_w = (lat >= -16.5) ? 1.0 : ((lat <= -19.0) ? 0.0 : 0.5*(1.0 + Math.cos(Math.PI*(-16.5 - lat)/2.5)));
              let lon_w = (lon <= -46.5) ? 1.0 : ((lon >= -44.0) ? 0.0 : 0.5*(1.0 + Math.cos(Math.PI*(lon + 46.5)/2.5)));
              let elev_w = (e_m <= 650.0) ? 1.0 : ((e_m >= 1250.0) ? 0.0 : 0.5*(1.0 + Math.cos(Math.PI*(e_m - 650.0)/600.0)));
              let tp_w = lat_w*lon_w*elev_w;
              fld[i] = fld[i]*tp_w;
              if (fld[i] < 0.004) fld[i] = 0;
              kept_sum += fld[i];
            } else {
              kept_sum += fld[i];
            }
          }
          if (kept_sum > 0 && raw_sum > 0) {
            let sc = raw_sum/kept_sum;
            for (let i = 0; i < fld.length; i++) fld[i] *= sc;
          }
        }

        //Upweight pre-contact horizons (04..08) along lowland Terra Preta (ADE) corridors to reflect the high sedentary
        //anthropogenic biomass required to form deep dark-earth anthrosols, overcoming IPHAN Eastern Brazil CRM survey bias
        let tp_tapered = surface.fields["09_terra_preta_ade_anthrosol"];
        if (tp_tapered) {
          let tp_idx = this.computeTerraPretaIntensityIndex(tp_tapered);
          let horizon_tp_weights = {
            "04_formative_early_ade": 0.35,
            "05_classic_amazonian_ade_expansion": 0.75,
            "06_polychrome_mound_chiefdoms": 0.95,
            "07_late_precolumbian_chiefdoms": 1.00,
            "08_contact_horizon": 1.00
          };
          let h_keys = Object.keys(horizon_tp_weights);
          for (let h_i = 0; h_i < h_keys.length; h_i++) {
            let hk = h_keys[h_i];
            let h_fld = surface.fields[hk];
            if (!h_fld) continue;
            let hw = horizon_tp_weights[hk];
            let s0 = 0;
            let s1 = 0;
            for (let i = 0; i < h_fld.length; i++) {
              s0 += h_fld[i];
              if (h_fld[i] > 0 && tp_idx[i] > 0)
                h_fld[i] = h_fld[i]*(1.0 + 0.65*hw*tp_idx[i]);
              s1 += h_fld[i];
            }
            if (s0 > 0 && s1 > 0) {
              let norm_s = s0/s1;
              for (let i = 0; i < h_fld.length; i++) h_fld[i] *= norm_s;
            }
          }
        }
      }

      let diag = ViscountMaternKriging.F_exportBenchmarkRastersAndDiagnostics(surface);

      //Move dedicated Terra Preta ADE raster to `1.kriged_terra_preta/` so `1.kriged_rasters/` holds strictly the 8 continental horizons
      let k_dir = path.join(surface.kriging_bundle.mask_data.domain_dir, "1.kriged_rasters");
      let tp_dir = path.join(surface.kriging_bundle.mask_data.domain_dir, "1.kriged_terra_preta");
      let tp_src = path.join(k_dir, "09_terra_preta_ade_anthrosol.png");
      if (fs.existsSync(tp_src)) {
        fs.mkdirSync(tp_dir, { recursive: true });
        fs.copyFileSync(tp_src, path.join(tp_dir, "09_terra_preta_ade_anthrosol.png"));
        fs.unlinkSync(tp_src);
      }
      let raster_meta = this.B_generatePopulationRasters(surface);

      //Return statement
      return {
        diag: diag,
        elapsed_seconds: Number(((Date.now() - t0)/1000).toFixed(2)),
        raster_meta: raster_meta
      };
    }
  };
}

if (require.main === module) {
  let res = global.PretaKrigingRunner.run();

  console.log(JSON.stringify({
    elapsed_seconds: res.elapsed_seconds,
    generated_years: res.raster_meta.generated_years,
    tau1_dimensionless: res.diag.tau1_dimensionless,
    tau2_dimensionless: res.diag.tau2_dimensionless,
    valid_cells: res.diag.valid_cells,
    wls_covariates_active: res.diag.wls_covariates_active
  }, null, 2));
}
