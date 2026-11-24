//Import modules
let fs = require("fs");
let path = require("path");
let { PNG } = require("pngjs");
let { AustralSubadminDasymetric } = require(path.join(__dirname, "AustralSubadminDasymetric.js"));
let { ViscountHUResidualKriging } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/centaur/ViscountHUResidualKriging.js"));
let { ViscountMaternKriging } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountMaternKriging.js"));
let { ViscountRuralSuitability } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountRuralSuitability.js"));

//Initialise functions
{
  /**
   * Executes POLARIS-grade Non-Stationary Matérn (`nu = 3/2`) Multi-Repository Archaeological Residual Kriging
   * across Australia, New Zealand, New Guinea, Melanesia, Micronesia and Polynesia (`AUSTRAL`), synthesises
   * all 128 HYDE benchmark rural suitability GeoPNGs (`-10000` to `2025 AD`), and applies strictly
   * mass-conserving Tobler pycnophylactic sub-administrative disaggregation across all enumerated AD years.
   *
   * @class AustralKrigingRunner
   */
  global.AustralKrigingRunner = class {
    static CONFIG_REL = "histmap/1.data_raw/population_regional/AUSTRAL/_shared/sites_austral_oceania/config/sites_austral_oceania.json5";
    static PROJECT_ROOT = path.resolve(__dirname, "../../../../../..");

    /**
     * Secondary urban-core cap preventing modern Oceanian metropolitan footprints (Sydney, Melbourne,
     * Brisbane, Perth, Adelaide, Auckland, Wellington, Christchurch, Suva, Port Moresby) from
     * backprojecting onto pre-industrial kriged surfaces.
     * @alias AustralKrigingRunner.capOceanianMetroUrbanCores
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_field
     * @param {Float32Array} arg2_uopp_valid
     * @param {number} [arg3_max_mult=0.86]
     */
    static capOceanianMetroUrbanCores (arg0_mask_data, arg1_field, arg2_uopp_valid, arg3_max_mult) {
      //Convert from parameters
      let field = arg1_field;
      let mask_data = arg0_mask_data;
      let max_mult = (arg3_max_mult !== undefined) ? arg3_max_mult : 0.86;
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
        if (field[i] <= 0 || uopp_valid[i] <= 3.8) continue;
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

              if (nv >= 0 && field[nv] > 0 && uopp_valid[nv] <= 3.8) {
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
     * Computes diagnostic verification metrics (`log_corr_hyde`, `urban_core_med_ratio`,
     * `urban_backproj_p95_ratio`, `beta_0_hab`) for Gatekeeper B1 transparency.
     * @alias AustralKrigingRunner.computeExtraDiagnostics
     *
     * @param {Object} arg0_surface
     *
     * @returns {Object}
     */
    static computeExtraDiagnostics (arg0_surface) {
      //Convert from parameters
      let surface = arg0_surface;

      //Declare local instance variables
      let beta0_acc = 0;
      let beta0_cnt = 0;
      let bio_covs = surface.bio_covs || {};
      let mask_data = surface.kriging_bundle.mask_data;
      let n_valid = mask_data.valid_cell_count;
      let uopp = bio_covs.uopp_valid || null;
      let v_idx = mask_data.valid_indices;

      //Function body
      let wls_map = surface.wls_betas_by_period || {};
      let wls_keys = Object.keys(wls_map);

      for (let i = 0; i < wls_keys.length; i++) {
        let b0 = Number(wls_map[wls_keys[i]] && wls_map[wls_keys[i]].beta_0_hab);

        if (Number.isFinite(b0)) {
          beta0_acc += b0;
          beta0_cnt++;
        }
      }

      //Pick representative late pre-contact horizon (Period 07) for HYDE 1500 correlation & urban-core audit
      let f_keys = Object.keys(surface.fields || {}).sort();
      let rep_key = surface.fields["07_classic_maori_pa_pacific_polities"] ?
        "07_classic_maori_pa_pacific_polities" :
        f_keys[Math.max(0, f_keys.length - 2)];
      let rep_f = rep_key ? surface.fields[rep_key] : null;
      let log_corr_hyde = 0.0;
      let urban_core_med_ratio = 0.0;
      let urban_backproj_p95_ratio = 0.0;

      if (rep_f) {
        let p15_path = path.join(this.PROJECT_ROOT, "histmap/2.data_cleaning/landuse_HYDE/rasters/popc_1500AD.png");

        if (fs.existsSync(p15_path)) {
          let png = PNG.sync.read(fs.readFileSync(p15_path));
          let dv = new DataView(png.data.buffer, png.data.byteOffset, png.data.byteLength);
          let xs = [];
          let ys = [];

          for (let i = 0; i < n_valid; i++) {
            if (rep_f[i] <= 0) continue;
            let p4 = v_idx[i]*4;

            if ((png.data[p4] | png.data[p4 + 1] | png.data[p4 + 2] | png.data[p4 + 3]) === 0) continue;
            let hv = dv.getFloat32(p4, false);

            if (Number.isFinite(hv) && hv > 0.01) {
              xs.push(Math.log10(rep_f[i] + 1e-6));
              ys.push(Math.log10(hv + 1e-6));
            }
          }
          if (xs.length >= 20) {
            let mx = 0;
            let my = 0;

            for (let i = 0; i < xs.length; i++) { mx += xs[i]; my += ys[i]; }
            mx /= xs.length;
            my /= ys.length;
            let num = 0;
            let dx2 = 0;
            let dy2 = 0;

            for (let i = 0; i < xs.length; i++) {
              let a = xs[i] - mx;
              let b = ys[i] - my;

              num += a*b;
              dx2 += a*a;
              dy2 += b*b;
            }
            if (dx2 > 1e-9 && dy2 > 1e-9) log_corr_hyde = num/Math.sqrt(dx2*dy2);
          }
        }

        if (uopp) {
          let grid_h = mask_data.grid_height;
          let grid_w = mask_data.grid_width;
          let p2v = mask_data.pixel_to_valid_idx;
          let ratios = [];

          for (let i = 0; i < n_valid; i++) {
            if (rep_f[i] <= 0 || uopp[i] <= 3.8) continue;
            let g = v_idx[i];
            let cx = g % grid_w;
            let cy = Math.floor(g/grid_w);
            let r_vals = [];

            for (let dy = -8; dy <= 8; dy++) {
              let ny = cy + dy;

              if (ny < 0 || ny >= grid_h) continue;
              for (let dx = -8; dx <= 8; dx++) {
                let nv = p2v[ny*grid_w + ((cx + dx + grid_w) % grid_w)];

                if (nv >= 0 && rep_f[nv] > 0 && uopp[nv] <= 2.0) r_vals.push(rep_f[nv]);
              }
            }
            if (r_vals.length >= 3) {
              r_vals.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
              let r_med = r_vals[Math.floor(0.50*(r_vals.length - 1))];

              if (r_med > 1e-6) ratios.push(rep_f[i]/r_med);
            }
          }
          if (ratios.length > 0) {
            ratios.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
            urban_core_med_ratio = ratios[Math.floor(0.50*(ratios.length - 1))];
            urban_backproj_p95_ratio = ratios[Math.floor(0.95*(ratios.length - 1))];
          }
        }
      }

      //Return statement
      return {
        beta_0_hab: Number((beta0_cnt > 0 ? beta0_acc/beta0_cnt : 0.1).toFixed(4)),
        log_corr_hyde: Number(log_corr_hyde.toFixed(4)),
        urban_backproj_p95_ratio: Number(urban_backproj_p95_ratio.toFixed(4)),
        urban_core_med_ratio: Number(urban_core_med_ratio.toFixed(4))
      };
    }


    /**
     * Executes full Matérn kriging + 128-year dasymetric residual raster synthesis +
     * pycnophylactic sub-administrative disaggregation for AUSTRAL.
     * @alias AustralKrigingRunner.run
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
      let field_keys = Object.keys(surface.fields || {});
      let mask_data = surface.kriging_bundle.mask_data;
      let strict_hab = (bio_covs && bio_covs.hab_mask) ? bio_covs.hab_mask : null;
      let uopp_valid = (bio_covs && bio_covs.uopp_valid) ? bio_covs.uopp_valid : null;

      surface.strict_hab_mask = strict_hab;

      for (let i = 0; i < field_keys.length; i++) {
        let f_arr = surface.fields[field_keys[i]];

        if (!f_arr) continue;
        if (uopp_valid)
          this.capOceanianMetroUrbanCores(mask_data, f_arr, uopp_valid, 0.86);
        if (strict_hab) {
          for (let x = 0; x < f_arr.length; x++) {
            if (strict_hab[x] === 0) f_arr[x] = 0;
          }
        }
      }

      let raster_meta = ViscountHUResidualKriging.generateAllBenchmarkPopulationRasters(surface, { is_polynesia: false });

      if (surface.hab_cache && typeof surface.hab_cache.clear === "function") surface.hab_cache.clear();
      let subadmin_meta = AustralSubadminDasymetric.applyAllYears(surface, { project_root: this.PROJECT_ROOT });
      let diag = ViscountMaternKriging.F_exportBenchmarkRastersAndDiagnostics(surface);
      let extra_diag = this.computeExtraDiagnostics(surface);

      //Propagate provenance breakdown, per-jurisdiction coverage, unique domestic site sum,
      //per-period variograms, diagnostic correlations & subadmin mass conservation into kriging_diagnostics.json
      let diag_p = path.join(__dirname, "config/kriging_diagnostics.json");
      let meta_p = path.join(__dirname, "config/sites_austral_oceania_geojson_metadata.json");

      if (fs.existsSync(meta_p) && fs.existsSync(diag_p)) {
        let diag_disk = JSON.parse(fs.readFileSync(diag_p, "utf8"));
        let meta = JSON.parse(fs.readFileSync(meta_p, "utf8"));
        let per_period_obj = {};
        let v_keys = Object.keys(diag_disk.variogram_models || {});

        for (let i = 0; i < v_keys.length; i++)
          per_period_obj[v_keys[i]] = Object.assign({ period: v_keys[i] }, diag_disk.variogram_models[v_keys[i]]);

        diag_disk.beta_0_hab = extra_diag.beta_0_hab;
        diag_disk.domestic_site_count_unique_sum = meta.domestic_site_count_unique_sum;
        diag_disk.jurisdiction_arch_coverage = meta.jurisdiction_arch_coverage;
        diag_disk.log_corr_hyde = extra_diag.log_corr_hyde;
        diag_disk.per_period = per_period_obj;
        diag_disk.source_provenance_breakdown = meta.source_provenance_breakdown;
        diag_disk.subadmin_hgis_mass_conservation = subadmin_meta;
        diag_disk.urban_backproj_p95_ratio = extra_diag.urban_backproj_p95_ratio;
        diag_disk.urban_core_med_ratio = extra_diag.urban_core_med_ratio;
        fs.writeFileSync(diag_p, JSON.stringify(diag_disk, null, 2));
      }

      //Return statement
      return {
        diag: diag,
        elapsed_seconds: Number(((Date.now() - t0)/1000).toFixed(2)),
        extra_diag: extra_diag,
        raster_meta: raster_meta,
        subadmin_meta: subadmin_meta
      };
    }
  };
}

if (require.main === module) {
  let res = global.AustralKrigingRunner.run();

  console.log(JSON.stringify({
    elapsed_seconds: res.elapsed_seconds,
    extra_diag: res.extra_diag,
    generated_years: res.raster_meta.generated_years,
    subadmin_worst_unit_err: res.subadmin_meta.worst_unit_rel_err,
    subadmin_years_scaled: res.subadmin_meta.years_scaled,
    tau1_dimensionless: res.diag.tau1_dimensionless,
    tau2_dimensionless: res.diag.tau2_dimensionless,
    valid_cells: res.diag.valid_cells,
    wls_covariates_active: res.diag.wls_covariates_active
  }, null, 2));
}
