//Import modules
let fs = require("fs");
let path = require("path");
let { JaguarCentaurFrontierHarmoniser } = require(path.join(__dirname, "JaguarCentaurFrontierHarmoniser.js"));
let { JaguarSubadminDasymetric } = require(path.join(__dirname, "JaguarSubadminDasymetric.js"));
let { ViscountHUResidualKriging } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/centaur/ViscountHUResidualKriging.js"));
let { ViscountMaternKriging } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountMaternKriging.js"));
let { ViscountRuralSuitability } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountRuralSuitability.js"));

//Initialise functions
{
  /**
   * Executes POLARIS/MAGNETIC-grade Non-Stationary Matérn (`nu = 3/2`) Multi-Repository Archaeological
   * Residual Kriging across Mesoamerica, Central America, the Caribbean & Bermuda (`JAGUAR`) and
   * synthesises all 128 HYDE benchmark rural suitability GeoPNGs (`-10000` to `2025 AD`).
   *
   * @class JaguarKrigingRunner
   */
  global.JaguarKrigingRunner = class {
    static CONFIG_REL = "histmap/1.data_raw/population_regional/JAGUAR/_shared/sites_jaguar_mesoamerica/config/sites_jaguar_mesoamerica.json5";
    static PROJECT_ROOT = path.resolve(__dirname, "../../../../../..");

    /**
     * Secondary urban-core cap preventing modern Mesoamerican & Caribbean metropolitan footprints
     * (Mexico City, Guadalajara, Monterrey, Havana, San Juan, Guatemala City, Panama City,
     * Santo Domingo, Port-au-Prince) from back-projecting onto pre-industrial kriged surfaces.
     * @alias JaguarKrigingRunner.capJaguarMetroUrbanCores
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_field
     * @param {Float32Array} arg2_uopp_valid
     * @param {number} [arg3_max_mult=0.88]
     */
    static capJaguarMetroUrbanCores (arg0_mask_data, arg1_field, arg2_uopp_valid, arg3_max_mult) {
      //Convert from parameters
      let field = arg1_field;
      let mask_data = arg0_mask_data;
      let max_mult = (arg3_max_mult !== undefined) ? arg3_max_mult : 0.88;
      let uopp_valid = arg2_uopp_valid;

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
        if (field[i] <= 0 || uopp_valid[i] <= 6.5) continue;
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

              if (nv >= 0 && field[nv] > 0 && uopp_valid[nv] <= 5.5) {
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
     * Executes full Matérn kriging + 128-year dasymetric residual raster synthesis, pycnophylactic
     * sub-administrative disaggregation, and CENTAUR northern frontier harmonisation for JAGUAR.
     * @alias JaguarKrigingRunner.run
     *
     * @returns {Object}
     */
    static run () {
      //Declare local instance variables
      let t0 = Date.now();
      let domain = ViscountMaternKriging.A_loadDomainConfigAndSites(this.CONFIG_REL, { project_root: this.PROJECT_ROOT });
      let obs = ViscountMaternKriging.B_computeEmpiricalBayesIntensities(domain);
      let krig = ViscountMaternKriging.C_fitTwoScaleNonStationaryMatern(obs);
      let surface = ViscountMaternKriging.E_fitCarryCapacityResidualSurface(krig);

      let bio_covs = surface.bio_covs;
      let field_keys = Object.keys(surface.fields || {});
      let mask_data = surface.kriging_bundle.mask_data;
      let strict_hab = (bio_covs && bio_covs.hab_mask) ? bio_covs.hab_mask : null;
      let uopp_valid = (bio_covs && bio_covs.uopp_valid) ? bio_covs.uopp_valid : null;

      //Function body
      surface.strict_hab_mask = strict_hab;

      for (let i = 0; i < field_keys.length; i++) {
        let f_arr = surface.fields[field_keys[i]];

        if (!f_arr) continue;
        if (uopp_valid)
          this.capJaguarMetroUrbanCores(mask_data, f_arr, uopp_valid, 0.88);
        if (strict_hab) {
          for (let x = 0; x < f_arr.length; x++) {
            if (strict_hab[x] === 0) f_arr[x] = 0;
          }
        }
      }

      let raster_meta = ViscountHUResidualKriging.generateAllBenchmarkPopulationRasters(surface, { is_polynesia: false });

      if (surface.hab_cache && typeof surface.hab_cache.clear === "function") surface.hab_cache.clear();
      let subadmin_meta = JaguarSubadminDasymetric.applyAllYears(surface, { project_root: this.PROJECT_ROOT });
      let frontier_meta = JaguarCentaurFrontierHarmoniser.harmoniseAllRasters(surface, { project_root: this.PROJECT_ROOT });
      let diag = ViscountMaternKriging.F_exportBenchmarkRastersAndDiagnostics(surface);

      //Propagate provenance breakdown, unique domestic site sum & subadmin HGIS audit into kriging_diagnostics.json
      let diag_p = path.join(__dirname, "config/kriging_diagnostics.json");
      let meta_p = path.join(__dirname, "config/sites_jaguar_mesoamerica_geojson_metadata.json");

      if (fs.existsSync(meta_p) && fs.existsSync(diag_p)) {
        let diag_disk = JSON.parse(fs.readFileSync(diag_p, "utf8"));
        let meta = JSON.parse(fs.readFileSync(meta_p, "utf8"));

        diag_disk.arch_crowd_share = meta.arch_crowd_share;
        diag_disk.arch_regional_share = meta.arch_regional_share;
        diag_disk.domestic_site_count_unique_sum = meta.domestic_site_count_unique_sum;
        diag_disk.jurisdiction_arch_coverage = meta.jurisdiction_arch_coverage;
        diag_disk.source_provenance_breakdown = meta.source_provenance_breakdown;
        diag_disk.subadmin_hgis_mass_conservation = subadmin_meta;
        diag_disk.centaur_frontier_harmonisation = frontier_meta;
        fs.writeFileSync(diag_p, JSON.stringify(diag_disk, null, 2));
      }

      //Return statement
      return {
        diag: diag,
        elapsed_seconds: Number(((Date.now() - t0)/1000).toFixed(2)),
        frontier_meta: frontier_meta,
        raster_meta: raster_meta,
        subadmin_meta: subadmin_meta
      };
    }
  };
}

if (require.main === module) {
  let res = global.JaguarKrigingRunner.run();

  console.log(JSON.stringify({
    elapsed_seconds: res.elapsed_seconds,
    frontier_meta: res.frontier_meta,
    generated_years: res.raster_meta.generated_years,
    subadmin_meta: {
      mass_conservation_passed: res.subadmin_meta.mass_conservation_passed,
      worst_country_rel_err: res.subadmin_meta.worst_country_rel_err,
      worst_unit_rel_err: res.subadmin_meta.worst_unit_rel_err,
      years_scaled: res.subadmin_meta.years_scaled
    },
    tau1_dimensionless: res.diag.tau1_dimensionless,
    tau2_dimensionless: res.diag.tau2_dimensionless,
    valid_cells: res.diag.valid_cells,
    wls_covariates_active: res.diag.wls_covariates_active
  }, null, 2));
}
