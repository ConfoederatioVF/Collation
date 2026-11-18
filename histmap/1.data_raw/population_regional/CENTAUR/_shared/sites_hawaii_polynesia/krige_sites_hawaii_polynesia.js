//Import modules
let fs = require("fs");
let path = require("path");
let { PNG } = require("pngjs");
let { ViscountBiophysicalCovariates } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountBiophysicalCovariates.js"));
let { ViscountHUResidualKriging } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountHUResidualKriging.js"));
let { ViscountMaternKriging } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountMaternKriging.js"));
let { ViscountRuralSuitability } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountRuralSuitability.js"));

//Initialise functions
{
  /**
   * Executes POLARIS-grade Non-Stationary Matérn (`nu = 3/2`) Residual Kriging for Pre-Annexation Hawai'i & American Polynesia
   * (`CENTAUR-II`) and synthesises all 128 HYDE benchmark rural suitability GeoPNGs (`-10000` to `2025 AD`) using 5-arcminute
   * biophysical covariates and de-cliffed HYDE rural habitation.
   *
   * @class HawaiiPolynesiaKrigingRunner
   */
  global.HawaiiPolynesiaKrigingRunner = class {
    static CONFIG_REL = "histmap/1.data_raw/population_regional/CENTAUR/_shared/sites_hawaii_polynesia/config/sites_hawaii_polynesia.json5";
    static PROJECT_ROOT = path.resolve(__dirname, "../../../../../..");

    /**
     * Interpolates chronologically across the 6 kriged Hawaii-Polynesia horizons (`-10000` to `2025 AD`), couples each
     * timestep with constrained 5-covariate NNLS residual kriging weights and exports `2.population_rasters/`.
     * @alias HawaiiPolynesiaKrigingRunner.B_generatePopulationRasters
     *
     * @param {Object} arg0_surface_bundle
     *
     * @returns {Object}
     */
    static B_generatePopulationRasters (arg0_surface_bundle) {
      //Convert from parameters
      let surface = arg0_surface_bundle;

      //Guard clause: delegate to per-HU residual kriging + census/GHSL engine when active
      let rk_cfg = (surface && surface.kriging_bundle && surface.kriging_bundle.config) ? surface.kriging_bundle.config : {};

      if (rk_cfg.kriging_config && rk_cfg.kriging_config.residual_kriging_mode === "hu_hyde_residual")
        return ViscountHUResidualKriging.generateAllBenchmarkPopulationRasters(surface, { is_polynesia: true });

      //Declare local instance variables
      let bio_covs = surface.bio_covs;
      let bundle = surface.kriging_bundle;
      let cfg = bundle.config;
      let ghs_pop_dir = path.join(this.PROJECT_ROOT, "histmap/1.data_raw/population_GHSL/population_rasters/2.rasters");
      let ghsl_dir = path.join(this.PROJECT_ROOT, cfg.kriging_config.covariate_paths.ghsl_urban_folder);
      let grid_h = bundle.mask_data.grid_height;
      let grid_w = bundle.mask_data.grid_width;
      let hab_cache = surface.hab_cache || new Map();
      let horizons_cfg = (cfg.kriging_config && Array.isArray(cfg.kriging_config.chronological_horizons)) ?
        cfg.kriging_config.chronological_horizons : [];
      let hyde_years = cfg.kriging_config.all_hyde_years || [];
      let is_samoa = new Uint8Array(bundle.mask_data.valid_cell_count);
      let meso_px = surface.meso_px || 4;
      let n_obs = bundle.obs_bundle.obs_count;
      let n_valid = bundle.mask_data.valid_cell_count;
      let out_dir = path.join(bundle.mask_data.domain_dir, cfg.output_population_rasters_subfolder || "2.population_rasters");
      let period_totals = bundle.obs_bundle.period_totals || {};
      let raw_potentials = surface.raw_potentials || {};
      let uopp_vals = this.readFloatRasterValid(
        path.join(this.PROJECT_ROOT, cfg.kriging_config.covariate_paths.hyde_uopp_raster),
        bundle.mask_data.valid_indices
      );
      let valid_indices = bundle.mask_data.valid_indices;

      //Function body
      fs.mkdirSync(out_dir, { recursive: true });
      for (let i = 0; i < n_valid; i++) {
        let row = Math.floor(valid_indices[i]/grid_w);
        let lat = 90 - (row + 0.5)*180/grid_h;

        if (lat < 0) is_samoa[i] = 1;
      }

      let horizon_dists = [];

      for (let i = 0; i < horizons_cfg.length; i++) {
        let h_cfg = horizons_cfg[i];
        let active_p = Array.isArray(h_cfg.active_periods) ? h_cfg.active_periods : [];
        let dist = new Float32Array(n_valid);
        let z_h = new Float64Array(n_obs);

        for (let x = 0; x < active_p.length; x++) {
          let pkey = active_p[x];
          let pot = raw_potentials[pkey];
          let pot_sum = 0;
          let p_total = Math.max(1, period_totals[pkey] || 0);

          if (!pot) continue;
          for (let y = 0; y < n_valid; y++) pot_sum += pot[y];
          let p_scale = (pot_sum > 0) ? p_total/pot_sum : 0;

          for (let y = 0; y < n_valid; y++) dist[y] += pot[y]*p_scale;
        }

        for (let x = 0; x < n_obs; x++) {
          let d_sum = 0;

          for (let y = 0; y < active_p.length; y++) {
            let model = bundle.kriging_models[active_p[y]];

            if (model && model.z_adj) {
              let zv = model.z_adj[x];

              d_sum += zv*zv;
            }
          }
          z_h[x] = Math.sqrt(d_sum);
        }

        let d_tot = 0;

        for (let x = 0; x < n_valid; x++) d_tot += dist[x];
        let inv_tot = (d_tot > 1e-12) ? 1.0/d_tot : 0;

        for (let x = 0; x < n_valid; x++) dist[x] *= inv_tot;

        horizon_dists.push({
          dist: dist,
          key: h_cfg.key,
          year: h_cfg.year,
          z_horizon: z_h
        });
      }
      horizon_dists.sort(function (arg0_a, arg1_b) { return arg0_a.year - arg1_b.year; });

      for (let y_idx = 0; y_idx < hyde_years.length; y_idx++) {
        let arch_pot = new Float32Array(n_valid);
        let yr = hyde_years[y_idx];
        let z_year = new Float64Array(n_obs);
        let alpha = 0;
        let dist_a;
        let dist_b;
        let z_a;
        let z_b;

        if (yr <= horizon_dists[0].year) {
          dist_a = horizon_dists[0].dist;
          dist_b = horizon_dists[0].dist;
          z_a = horizon_dists[0].z_horizon;
          z_b = horizon_dists[0].z_horizon;
        } else if (yr >= horizon_dists[horizon_dists.length - 1].year) {
          let last_h = horizon_dists[horizon_dists.length - 1];

          dist_a = last_h.dist;
          dist_b = last_h.dist;
          z_a = last_h.z_horizon;
          z_b = last_h.z_horizon;
        } else {
          for (let k = 0; k < horizon_dists.length - 1; k++) {
            if (yr >= horizon_dists[k].year && yr <= horizon_dists[k + 1].year) {
              dist_a = horizon_dists[k].dist;
              dist_b = horizon_dists[k + 1].dist;
              z_a = horizon_dists[k].z_horizon;
              z_b = horizon_dists[k + 1].z_horizon;
              alpha = (yr - horizon_dists[k].year)/Math.max(1, horizon_dists[k + 1].year - horizon_dists[k].year);
              break;
            }
          }
        }

        for (let i = 0; i < n_obs; i++) z_year[i] = (1 - alpha)*z_a[i] + alpha*z_b[i];
        for (let i = 0; i < n_valid; i++) {
          let samoa_scale = (yr < 950) ? ((yr <= -1000) ? 0.08 : (0.15 + 0.85*Math.max(0, (yr + 1000)/1950))) : 1.0;
          let hi_scale = (yr < 950) ? ((yr < 800) ? 0.001 : (0.05 + 0.95*Math.max(0, (yr - 800)/150))) : 1.0;

          arch_pot[i] = ((1 - alpha)*dist_a[i] + alpha*dist_b[i])*(is_samoa[i] ? samoa_scale : hi_scale);
        }

        let u_hab = ViscountBiophysicalCovariates.computeDeCliffedHabitationField(
          bundle.mask_data,
          bundle.obs_bundle,
          bio_covs,
          yr,
          cfg,
          hab_cache
        );
        let rk = ViscountBiophysicalCovariates.computeResidualKrigingWeights(
          bundle.mask_data,
          bundle.obs_bundle,
          bio_covs,
          u_hab,
          z_year,
          meso_px,
          yr,
          cfg
        );
        let arch_field = new Float32Array(n_valid);
        let arch_sum = 0;
        let out_field = new Float32Array(n_valid);

        for (let i = 0; i < n_valid; i++)
          arch_field[i] = arch_pot[i]*rk.weights[i];

        if (yr <= 1780 && bio_covs.uopp_valid)
          ViscountRuralSuitability.capUrbanCoreFieldToRuralRing(bundle.mask_data, arch_field, bio_covs.uopp_valid, 1.12);

        for (let i = 0; i < n_valid; i++) arch_sum += arch_field[i];

        let hab_mask = bio_covs.hab_mask;
        let target_mass = (yr >= 800) ? Math.max(2e4, Math.round(3e5*Math.exp((yr - 1750)/2500))) : 1e4;
        let arch_scale = (arch_sum > 0) ? target_mass/arch_sum : 1.0;

        for (let i = 0; i < n_valid; i++) arch_field[i] *= arch_scale;

        if (yr <= 1890) {
          for (let i = 0; i < n_valid; i++)
            out_field[i] = (hab_mask && hab_mask[i] === 0) ? 0 : Math.max(1e-4, arch_field[i]);
        } else {
          let ghs_pop = (yr >= 1900) ? this.readFloatRasterValid(path.join(ghs_pop_dir, `GHS_POP_${yr}.png`), valid_indices) : null;
          let ghsl_urb = (yr >= 1900) ? this.readUintRasterValid(path.join(ghsl_dir, `GHSL_${yr}.png`), valid_indices) : null;
          let mod_rur = new Float32Array(n_valid);
          let mod_sum = 0;
          let u_coast = bio_covs.u_coastal;
          let u_eco = bio_covs.u_eco;
          let u_fluv = bio_covs.u_fluvial;
          let u_nat = bio_covs.u_nat;

          for (let i = 0; i < n_valid; i++) {
            let bio_w = 0.45*u_nat[i] + 0.25*u_fluv[i] + 0.20*u_coast[i] + 0.10*u_eco[i];
            let mr = Math.max(0, u_hab[i])*bio_w;

            if (ghs_pop) {
              let u_ghsl = (ghsl_urb && ghsl_urb[i] > 0) ? ghsl_urb[i] : 0;
              let u_frac = (uopp_vals && yr >= 1950) ? Math.min(0.65, uopp_vals[i]/90.0) : 0;
              let g_rur = Math.max(0.05, (ghs_pop[i] - Math.min(ghs_pop[i]*0.85, u_ghsl))*(1 - 0.5*u_frac));

              mr = 0.35*mr + 0.65*g_rur;
            }
            mod_rur[i] = mr;
            mod_sum += mr;
          }

          let mod_scale = (mod_sum > 0 && target_mass > 0) ? target_mass/mod_sum : 1.0;
          let w_mod = Math.min(0.90, 0.90*Math.max(0, (yr - 1890)/60));

          for (let i = 0; i < n_valid; i++) {
            let v = arch_field[i]*(1 - w_mod) + (mod_rur[i]*mod_scale)*w_mod;

            out_field[i] = (v > 0) ? Math.max(1e-4, v) : 0;
          }
        }

        let f_buf = new ArrayBuffer(4);
        let f_dv = new DataView(f_buf);
        let img = new PNG({ colorType: 6, height: grid_h, width: grid_w });

        for (let i = 0; i < n_valid; i++) {
          let px = valid_indices[i]*4;

          f_dv.setFloat32(0, out_field[i], false);
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
     * Reads a Big-Endian float32 RGBA GeoPNG into a Float32Array over valid mask indices.
     * @alias HawaiiPolynesiaKrigingRunner.readFloatRasterValid
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
      if (!fs.existsSync(abs_path)) return null;

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
     * Reads a Big-Endian uint32 RGBA GeoPNG (e.g. GHSL urban mask) over valid mask indices.
     * @alias HawaiiPolynesiaKrigingRunner.readUintRasterValid
     *
     * @param {string} arg0_abs_path
     * @param {Int32Array} arg1_valid_indices
     *
     * @returns {Float32Array|null}
     */
    static readUintRasterValid (arg0_abs_path, arg1_valid_indices) {
      //Convert from parameters
      let abs_path = arg0_abs_path;
      let valid_indices = arg1_valid_indices;

      //Guard clauses
      if (!fs.existsSync(abs_path)) return null;

      //Declare local instance variables
      let data = PNG.sync.read(fs.readFileSync(abs_path)).data;
      let out = new Float32Array(valid_indices.length);

      //Function body
      for (let i = 0; i < valid_indices.length; i++) {
        let p4 = valid_indices[i]*4;

        out[i] = ((data[p4] << 24) | (data[p4 + 1] << 16) | (data[p4 + 2] << 8) | data[p4 + 3]) >>> 0;
      }

      //Return statement
      return out;
    }

    /**
     * Executes full Matérn kriging + 128-year substrata raster synthesis.
     * @alias HawaiiPolynesiaKrigingRunner.run
     *
     * @returns {Object}
     */
    static run () {
      let domain = ViscountMaternKriging.A_loadDomainConfigAndSites(this.CONFIG_REL, { project_root: this.PROJECT_ROOT });
      let obs = ViscountMaternKriging.B_computeEmpiricalBayesIntensities(domain);
      let krig = ViscountMaternKriging.C_fitTwoScaleNonStationaryMatern(obs);
      let surface = ViscountMaternKriging.E_fitCarryCapacityResidualSurface(krig);
      let diag = ViscountMaternKriging.F_exportBenchmarkRastersAndDiagnostics(surface);
      let raster_meta = this.B_generatePopulationRasters(surface);

      //Return statement
      return { diag: diag, raster_meta: raster_meta };
    }
  };
}

if (require.main === module) {
  let res = global.HawaiiPolynesiaKrigingRunner.run();

  console.log(JSON.stringify({
    generated_years: res.raster_meta.generated_years,
    tau1_dimensionless: res.diag.tau1_dimensionless,
    tau2_dimensionless: res.diag.tau2_dimensionless,
    valid_cells: res.diag.valid_cells,
    wls_covariates_active: res.diag.wls_covariates_active
  }, null, 2));
}
