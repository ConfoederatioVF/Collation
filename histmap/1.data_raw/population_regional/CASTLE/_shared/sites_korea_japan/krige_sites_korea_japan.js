//Import modules
let fs = require("fs");
let path = require("path");
let { PNG } = require("pngjs");
let { ViscountBiophysicalCovariates } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountBiophysicalCovariates.js"));
let { ViscountHUResidualKriging } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/centaur/ViscountHUResidualKriging.js"));
let { ViscountMaternKriging } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountMaternKriging.js"));
let { ViscountRuralSuitability } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountRuralSuitability.js"));

//Initialise functions
{
  /**
   * Executes POLARIS-grade Non-Stationary Matérn (`nu = 3/2`) Multi-Registry Archaeological Residual Kriging
   * across the Korean Peninsula and Japanese Archipelago (`CASTLE`) and synthesises all 128 HYDE benchmark
   * rural suitability GeoPNGs (`-10000` to `2025 AD`) using 5-arcminute biophysical covariates and urban-masked HYDE.
   *
   * @class KoreaJapanKrigingRunner
   */
  global.KoreaJapanKrigingRunner = class {
    static CONFIG_REL = "histmap/1.data_raw/population_regional/CASTLE/_shared/sites_korea_japan/config/sites_korea_japan.json5";
    static PROJECT_ROOT = path.resolve(__dirname, "../../../../../..");

    /**
     * Step B: Delegates to the unified Viscount dasymetric residual kriging engine (`ViscountHUResidualKriging`)
     * to emit all 128 HYDE benchmark population rasters (`2.population_rasters/popc_<year>.png`).
     * @alias KoreaJapanKrigingRunner.B_generatePopulationRasters
     *
     * @param {Object} arg0_surface_bundle
     *
     * @returns {Object}
     */
    static B_generatePopulationRasters (arg0_surface_bundle) {
      //Convert from parameters
      let surface = arg0_surface_bundle;

      //Return statement
      return ViscountHUResidualKriging.generateAllBenchmarkPopulationRasters(surface, { is_polynesia: false });
    }

    /**
     * Secondary urban-core cap for wide metropolitan plains (`Tokyo`, `Osaka`, `Nagoya`, `Seoul`, `Busan`)
     * capping pre-industrial core cells smoothly to their rural surrounding ring.
     * @alias KoreaJapanKrigingRunner.capMetroUrbanCores
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_field
     * @param {Float32Array} arg2_uopp_valid
     * @param {number} [arg3_max_mult=0.88]
     */
    static capMetroUrbanCores (arg0_mask_data, arg1_field, arg2_uopp_valid, arg3_max_mult) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let field = arg1_field;
      let uopp_valid = arg2_uopp_valid;
      let max_mult = (arg3_max_mult !== undefined) ? arg3_max_mult : 0.88;

      //Guard clauses
      if (!mask_data || !field || !uopp_valid) return;

      //Declare local instance variables
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let v_idx = mask_data.valid_indices;

      //Function body
      let rural_wide = new Float32Array(n_valid);

      for (let i = 0; i < n_valid; i++)
        if (field[i] > 0 && uopp_valid[i] <= 3.8) rural_wide[i] = field[i];

      let wide_mean = ViscountRuralSuitability.smoothPositiveFieldOnGrid(mask_data, rural_wide, 10);

      for (let i = 0; i < n_valid; i++) {
        if (field[i] <= 0 || uopp_valid[i] <= 8.0) continue;
        let ref_val = wide_mean[i];

        if (ref_val <= 0) {
          let gidx = v_idx[i];
          let cx = gidx % grid_w;
          let cy = Math.floor(gidx/grid_w);
          let acc = 0;
          let cnt = 0;

          for (let dy = -14; dy <= 14; dy += 2) {
            let ny = cy + dy;

            if (ny < 0 || ny >= grid_h) continue;
            for (let dx = -14; dx <= 14; dx += 2) {
              let nv = p2v[ny*grid_w + ((cx + dx + grid_w) % grid_w)];

              if (nv >= 0 && field[nv] > 0 && uopp_valid[nv] <= 6.0) {
                acc += field[nv];
                cnt++;
              }
            }
          }
          if (cnt > 0) ref_val = acc/cnt;
        }
        if (ref_val > 0 && field[i] > ref_val*max_mult)
          field[i] = ref_val*max_mult;
      }
    }

    /**
     * Executes full Matérn kriging + 128-year substrata raster synthesis for CASTLE.
     * @alias KoreaJapanKrigingRunner.run
     *
     * @returns {Object}
     */
    static run () {
      let t0 = Date.now();
      let domain = ViscountMaternKriging.A_loadDomainConfigAndSites(this.CONFIG_REL, { project_root: this.PROJECT_ROOT });
      let obs = ViscountMaternKriging.B_computeEmpiricalBayesIntensities(domain);
      let krig = ViscountMaternKriging.C_fitTwoScaleNonStationaryMatern(obs);
      let surface = ViscountMaternKriging.E_fitCarryCapacityResidualSurface(krig);

      let bio_covs = surface.bio_covs;
      let mask_data = surface.kriging_bundle.mask_data;
      let strict_hab = (bio_covs && bio_covs.hab_mask) ? bio_covs.hab_mask : null;

      surface.strict_hab_mask = strict_hab;

      let uopp_valid = (bio_covs && bio_covs.uopp_valid) ? bio_covs.uopp_valid : null;
      let field_keys = Object.keys(surface.fields || {});

      for (let i = 0; i < field_keys.length; i++) {
        let f_arr = surface.fields[field_keys[i]];

        if (!f_arr) continue;
        if (uopp_valid)
          this.capMetroUrbanCores(mask_data, f_arr, uopp_valid, 0.88);
        if (strict_hab) {
          for (let x = 0; x < f_arr.length; x++) {
            if (strict_hab[x] === 0) f_arr[x] = 0;
          }
        }
      }

      let diag = ViscountMaternKriging.F_exportBenchmarkRastersAndDiagnostics(surface);
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
  let res = global.KoreaJapanKrigingRunner.run();

  console.log(JSON.stringify({
    elapsed_seconds: res.elapsed_seconds,
    generated_years: res.raster_meta.generated_years,
    tau1_dimensionless: res.diag.tau1_dimensionless,
    tau2_dimensionless: res.diag.tau2_dimensionless,
    valid_cells: res.diag.valid_cells,
    wls_covariates_active: res.diag.wls_covariates_active
  }, null, 2));
}

