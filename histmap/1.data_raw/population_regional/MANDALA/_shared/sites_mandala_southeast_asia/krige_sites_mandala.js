//Import modules
let path = require("path");
let { ViscountHUResidualKriging } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/centaur/ViscountHUResidualKriging.js"));
let { ViscountMaternKriging } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountMaternKriging.js"));
let { ViscountRuralSuitability } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountRuralSuitability.js"));

//Initialise functions
{
  /**
   * Executes POLARIS-grade Non-Stationary Matérn (`nu = 3/2`) Multi-Repository Archaeological Residual Kriging
   * across Mainland and Maritime South-East Asia (`MANDALA`, excluding West New Guinea) and
   * synthesises all 128 HYDE benchmark rural suitability GeoPNGs (`-10000` to `2025 AD`).
   *
   * @class MandalaKrigingRunner
   */
  global.MandalaKrigingRunner = class {
    static CONFIG_REL = "histmap/1.data_raw/population_regional/MANDALA/_shared/sites_mandala_southeast_asia/config/sites_mandala_southeast_asia.json5";
    static PROJECT_ROOT = path.resolve(__dirname, "../../../../../..");

    /**
     * Secondary urban-core cap for wide South-East Asian metropolitan belts (Jabodetabek/Jakarta,
     * Metro Manila, Bangkok, Ho Chi Minh City, Hanoi, Singapore-Johor, Kuala Lumpur-Klang, Surabaya, Yangon)
     * so pre-industrial surfaces never backproject modern urban sprawl.
     * @alias MandalaKrigingRunner.capMegaUrbanCores
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_field
     * @param {Float32Array} arg2_uopp_valid
     * @param {number} [arg3_max_mult=0.88]
     */
    static capMegaUrbanCores (arg0_mask_data, arg1_field, arg2_uopp_valid, arg3_max_mult) {
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
      let rural_wide = new Float32Array(n_valid);
      let v_idx = mask_data.valid_indices;

      //Function body
      for (let i = 0; i < n_valid; i++)
        if (field[i] > 0 && uopp_valid[i] <= 3.8) rural_wide[i] = field[i];

      let wide_mean = ViscountRuralSuitability.smoothPositiveFieldOnGrid(mask_data, rural_wide, 12);

      for (let i = 0; i < n_valid; i++) {
        if (field[i] <= 0 || uopp_valid[i] <= 8.0) continue;
        let ref_val = wide_mean[i];

        if (ref_val <= 0) {
          let gidx = v_idx[i];
          let cx = gidx % grid_w;
          let cy = Math.floor(gidx/grid_w);
          let acc = 0;
          let cnt = 0;

          for (let dy = -16; dy <= 16; dy += 2) {
            let ny = cy + dy;

            if (ny < 0 || ny >= grid_h) continue;
            for (let dx = -16; dx <= 16; dx += 2) {
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
     * Executes full Matérn kriging + 128-year dasymetric residual raster synthesis for MANDALA.
     * @alias MandalaKrigingRunner.run
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
          this.capMegaUrbanCores(mask_data, f_arr, uopp_valid, 0.88);
        if (strict_hab) {
          for (let x = 0; x < f_arr.length; x++) {
            if (strict_hab[x] === 0) f_arr[x] = 0;
          }
        }
      }

      let diag = ViscountMaternKriging.F_exportBenchmarkRastersAndDiagnostics(surface);
      let raster_meta = ViscountHUResidualKriging.generateAllBenchmarkPopulationRasters(surface, { is_polynesia: false });

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
  let res = global.MandalaKrigingRunner.run();

  console.log(JSON.stringify({
    elapsed_seconds: res.elapsed_seconds,
    generated_years: res.raster_meta.generated_years,
    tau1_dimensionless: res.diag.tau1_dimensionless,
    tau2_dimensionless: res.diag.tau2_dimensionless,
    valid_cells: res.diag.valid_cells,
    wls_covariates_active: res.diag.wls_covariates_active
  }, null, 2));
}
