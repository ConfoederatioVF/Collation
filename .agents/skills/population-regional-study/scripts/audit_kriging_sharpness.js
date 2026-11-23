//Import modules
let fs = require("fs");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");

//Initialise functions
{
  let kriging_sharpness_auditor = {
    /**
     * Audits dual HYDE 3.5 + KK10 believed-density catchment tightening AND global minimum catchment floor.
     * @alias kriging_sharpness_auditor.auditCatchmentDensityTiers
     *
     * @param {string} arg0_domain_dir
     * @param {string} arg1_svea_root
     * @param {Uint8Array} arg2_mask
     * @param {Object} arg3_profiles
     * @param {Array<string>} arg4_errors
     * @param {Array<string>} arg5_warnings
     *
     * @returns {Object}
     */
    auditCatchmentDensityTiers (arg0_domain_dir, arg1_svea_root, arg2_mask, arg3_profiles, arg4_errors, arg5_warnings) {
      //Convert from parameters
      let domain_dir = arg0_domain_dir;
      let errors = arg4_errors;
      let mask = arg2_mask;
      let profiles = arg3_profiles || {};
      let svea_root = arg1_svea_root;
      let warnings = arg5_warnings;

      //Declare local instance variables
      let all_gj_path = path.join(domain_dir, "geojson/00_all_periods.geojson");
      let policy = profiles.catchment_density_policy || {};
      let tiers = Array.isArray(policy.tiers) ? policy.tiers : [
        { id: "dense_core", max_area_km2: 1800, min_inh_per_km2: 25.0 },
        { id: "settled_belt", max_area_km2: 3000, min_inh_per_km2: 5.0 },
        { id: "moderate_rural", max_area_km2: 6000, min_inh_per_km2: 1.0 },
        { id: "sparse_margin", max_area_km2: 14000, min_inh_per_km2: 0.05 },
        { id: "minimum_floor", max_area_km2: 25000, min_inh_per_km2: 0.0 }
      ];

      //Guard clauses
      if (!svea_root || !fs.existsSync(all_gj_path)) return { checked: 0 };

      //Function body
      let la_path = path.join(svea_root, "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png");
      let hyde_1500 = path.join(svea_root, "histmap/2.data_cleaning/landuse_HYDE/rasters/popc_1500AD.png");
      let kk10_1500 = path.join(svea_root, "histmap/1.data_raw/population_KK10LUH2/KK10/KK10_1500.png");
      let la = fs.existsSync(la_path) ? viscount_audit_utils.decodeUint32Png(la_path) : null;
      let hyde = fs.existsSync(hyde_1500) ? viscount_audit_utils.decodeFloat32Png(hyde_1500) : null;
      let kk10 = fs.existsSync(kk10_1500) ? viscount_audit_utils.decodeFloat32Png(kk10_1500) : null;
      let gj = JSON.parse(fs.readFileSync(all_gj_path, "utf8"));
      let feats = Array.isArray(gj.features) ? gj.features : [];

      let checked = 0;
      let compliant = 0;
      let domestic_area_sum = 0.0;
      let global_max_cap = Number(policy.global_max_catchment_area_km2) || 25000;
      let over_global_cap = 0;
      let w = la ? la.width : 4320;
      let h = la ? la.height : 2160;

      for (let i = 0; i < feats.length; i++) {
        let props = (feats[i] && feats[i].properties) || {};
        if (props.is_frontier_buffer) continue;
        let area_km2 = Number(props.area_km2 || props.catchment_area_km2 || props.effective_area_km2 || 0);
        if (!Number.isFinite(area_km2) || area_km2 <= 0) continue;
        checked++;
        domestic_area_sum += area_km2;
        if (area_km2 > global_max_cap) over_global_cap++;

        let geom = feats[i].geometry;
        let coords = (geom && geom.type === "Point" && Array.isArray(geom.coordinates)) ? geom.coordinates : null;
        let d_believed = 0.0;
        if (coords && la) {
          let r = Math.min(h - 1, Math.max(0, Math.floor((90.0 - Number(coords[1]))*h/180.0)));
          let c = Math.min(w - 1, Math.max(0, Math.floor((Number(coords[0]) + 180.0)*w/360.0)));
          let idx = r*w + c;
          let cell_la = Math.max(1.0, la.data[idx]);
          let d_h = hyde ? (hyde.data[idx]/cell_la) : 0.0;
          let d_k = kk10 ? (kk10.data[idx]/cell_la) : 0.0;
          d_believed = Math.max(d_h, d_k);
        }

        let allowed_area = global_max_cap;
        for (let t = 0; t < tiers.length; t++) {
          if (d_believed >= Number(tiers[t].min_inh_per_km2 || 0)) {
            allowed_area = Number(tiers[t].max_area_km2 || global_max_cap);
            break;
          }
        }
        if (area_km2 <= allowed_area*1.15) compliant++;
      }

      let compliance_ratio = checked > 0 ? (compliant/checked) : 1.0;
      let density_per_100k = domestic_area_sum > 0 ? (checked*100000.0/domestic_area_sum) : 0.0;
      let min_per_100k = Number(policy.min_catchments_per_100k_km2) || 5.0;
      let min_comp = Number(policy.min_tier_compliance_ratio) || 0.90;

      if (over_global_cap > 0)
        errors.push(`[CATCHMENT_FLOOR] ${over_global_cap} domestic catchment(s) exceed global max area ceiling ${global_max_cap} km².`);
      if (checked >= 20 && density_per_100k < min_per_100k)
        errors.push(`[CATCHMENT_FLOOR] Catchment density ${density_per_100k.toFixed(2)} per 100k km² is below minimum floor ${min_per_100k}.`);
      if (checked >= 20 && compliance_ratio < min_comp)
        warnings.push(`[HYDE_KK10_TIERS] Only ${(compliance_ratio*100).toFixed(1)}% of catchments meet dual HYDE 3.5 + KK10 believed-density ceilings (target >= ${(min_comp*100).toFixed(0)}%).`);

      //Return statement
      return {
        checked: checked,
        compliance_ratio: Number(compliance_ratio.toFixed(4)),
        density_per_100k_km2: Number(density_per_100k.toFixed(2)),
        over_global_cap: over_global_cap
      };
    },

    /**
     * Audits dasymetric habitability suppression, HYDE correlation, spatial sharpness (`hp15`/`dx`),
     * and Manhattan-diamond directional anisotropy across representative kriged rasters.
     * @alias kriging_sharpness_auditor.auditRastersAndSharpness
     *
     * @param {string} arg0_domain_dir
     * @param {string} arg1_svea_root
     * @param {Uint8Array} arg2_mask
     * @param {Object} arg3_floors
     * @param {Array<string>} arg4_errors
     * @param {Array<string>} arg5_warnings
     *
     * @returns {Object}
     */
    auditRastersAndSharpness (arg0_domain_dir, arg1_svea_root, arg2_mask, arg3_floors, arg4_errors, arg5_warnings) {
      //Convert from parameters
      let domain_dir = arg0_domain_dir;
      let errors = arg4_errors;
      let floors = arg3_floors || {};
      let mask = arg2_mask;
      let svea_root = arg1_svea_root;
      let warnings = arg5_warnings;

      //Declare local instance variables
      let k_dir = path.join(domain_dir, "1.kriged_rasters");
      let la_path = svea_root ? path.join(svea_root, "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png") : "";
      let p15_path = svea_root ? path.join(svea_root, "histmap/2.data_cleaning/landuse_HYDE/rasters/popc_1500AD.png") : "";
      let p10_path = svea_root ? path.join(svea_root, "histmap/2.data_cleaning/landuse_HYDE/rasters/popc_1000AD.png") : "";
      let p19_path = svea_root ? path.join(svea_root, "histmap/2.data_cleaning/landuse_HYDE/rasters/popc_1900AD.png") : "";
      let kk10_path = svea_root ? path.join(svea_root, "histmap/1.data_raw/population_KK10LUH2/KK10/KK10_1500.png") : "";

      //Guard clauses
      if (!fs.existsSync(k_dir)) return { audited_rasters: 0 };
      let k_files = fs.readdirSync(k_dir).filter(function (arg0_f) { return /\.png$/i.test(arg0_f); }).sort()
        .map(function (arg0_f) { return path.join(k_dir, arg0_f); });
      if (k_files.length === 0) return { audited_rasters: 0 };

      //Function body
      let rep_idxs = Array.from(new Set([0, Math.floor(k_files.length/2), k_files.length - 1]));
      let la = (la_path && fs.existsSync(la_path)) ? viscount_audit_utils.decodeUint32Png(la_path) : null;
      let p15 = (p15_path && fs.existsSync(p15_path)) ? viscount_audit_utils.decodeFloat32Png(p15_path) : null;
      let p10 = (p10_path && fs.existsSync(p10_path)) ? viscount_audit_utils.decodeFloat32Png(p10_path) : null;
      let p19 = (p19_path && fs.existsSync(p19_path)) ? viscount_audit_utils.decodeFloat32Png(p19_path) : null;
      let kk10 = (kk10_path && fs.existsSync(kk10_path)) ? viscount_audit_utils.decodeFloat32Png(kk10_path) : null;

      let w = la ? la.width : 4320;
      let h = la ? la.height : 2160;
      let hab = null;

      if (la && p15) {
        let gj_dir = path.join(domain_dir, "geojson");
        let site_grid = new Uint8Array(w*h);
        let site_cnt = 0;
        if (fs.existsSync(gj_dir)) {
          let gjs = fs.readdirSync(gj_dir).filter(function (arg0_f) { return /\.geojson$/i.test(arg0_f); });
          for (let i = 0; i < gjs.length; i++) {
            try {
              let gj = JSON.parse(fs.readFileSync(path.join(gj_dir, gjs[i]), "utf8"));
              let feats = Array.isArray(gj.features) ? gj.features : [];
              for (let x = 0; x < feats.length; x++) {
                let geom = feats[x] && feats[x].geometry;
                if (!geom || geom.type !== "Point" || !Array.isArray(geom.coordinates)) continue;
                let r = Math.min(h - 1, Math.max(0, Math.floor((90.0 - Number(geom.coordinates[1]))*h/180.0)));
                let c = Math.min(w - 1, Math.max(0, Math.floor((Number(geom.coordinates[0]) + 180.0)*w/360.0)));
                site_grid[r*w + c] = 1;
                site_cnt++;
              }
            } catch (e) {}
          }
        }
        if (site_cnt > 0) {
          let edt = viscount_audit_utils.computeExactEdt2d(site_grid, w, h);
          hab = new Uint8Array(w*h);
          for (let i = 0; i < w*h; i++) {
            let cell_la = Math.max(1.0, la.data[i]);
            let d_h = Math.max(p15.data[i], p10 ? p10.data[i] : 0, p19 ? 0.15*p19.data[i] : 0)/cell_la;
            let d_k = kk10 ? (kk10.data[i]/cell_la) : 0;
            if (edt[i] <= 6.0 || d_h >= 0.002 || d_k >= 0.002) hab[i] = 1;
          }
        }
      }

      let max_aniso = 0.0;
      let max_leak = 0.0;
      let max_mass = 0.0;
      let min_dx = 999.0;
      let min_hp15 = 999.0;

      for (let i = 0; i < rep_idxs.length; i++) {
        let kp = k_files[rep_idxs[i]];
        let dec = viscount_audit_utils.decodeFloat32Png(kp);
        let kf = dec.data;
        let kv = dec.valid;

        //Compute spatial detail (dx_mean, hp15_mean) & Manhattan vs diagonal gradient anisotropy
        let sum_ax = 0.0;
        let sum_diag = 0.0;
        let sum_dx = 0.0;
        let sum_hp = 0.0;
        let n_grad = 0;

        let n_unhab = 0;
        let n_unhab_pos = 0;
        let tot_mass = 0.0;
        let unhab_mass = 0.0;

        for (let r = 1; r < h - 1; r++) {
          let row_off = r*w;
          for (let c = 1; c < w - 1; c++) {
            let idx = row_off + c;
            let in_m = mask ? mask[idx] : kv[idx];
            if (!in_m || (la && la.data[idx] <= 0)) continue;

            let val = kf[idx];
            tot_mass += val;
            if (hab && !hab[idx]) {
              n_unhab++;
              if (val > 1e-6) {
                n_unhab_pos++;
                unhab_mass += val;
              }
            }

            if (val > 0) {
              let lv = Math.log10(val + 1e-6);
              let lv_r = kf[idx + 1] > 0 ? Math.log10(kf[idx + 1] + 1e-6) : lv;
              let lv_d = kf[idx + w] > 0 ? Math.log10(kf[idx + w] + 1e-6) : lv;
              let lv_dr = kf[idx + w + 1] > 0 ? Math.log10(kf[idx + w + 1] + 1e-6) : lv;
              let lv_dl = kf[idx + w - 1] > 0 ? Math.log10(kf[idx + w - 1] + 1e-6) : lv;
              let ax = 0.5*(Math.abs(lv_r - lv) + Math.abs(lv_d - lv));
              let dg = 0.5*(Math.abs(lv_dr - lv) + Math.abs(lv_dl - lv))/Math.SQRT2;
              sum_ax += ax;
              sum_diag += dg;
              sum_dx += ax;
              //Local 3x3 high-pass deviation proxy
              let nb = (lv_r + lv_d + lv_dr + lv_dl)*0.25;
              sum_hp += Math.abs(lv - nb);
              n_grad++;
            }
          }
        }

        if (n_unhab >= 50) {
          let leak = n_unhab_pos/n_unhab;
          let mshare = tot_mass > 0 ? (unhab_mass/tot_mass) : 0;
          if (leak > max_leak) max_leak = leak;
          if (mshare > max_mass) max_mass = mshare;
        }
        if (n_grad >= 100) {
          let dx_m = sum_dx/n_grad;
          let hp_m = (sum_hp/n_grad)*1.65;
          let aniso = (sum_diag > 1e-9) ? (sum_ax/sum_diag) : 1.0;
          if (dx_m < min_dx) min_dx = dx_m;
          if (hp_m < min_hp15) min_hp15 = hp_m;
          if (aniso > max_aniso) max_aniso = aniso;
        }
      }

      if (max_leak > (Number(floors.max_unhab_leak_ratio) || 0.03))
        errors.push(`[HABITABILITY] Uninhabitable cell leak ratio ${max_leak.toFixed(4)} exceeds 0.03.`);
      if (max_mass > (Number(floors.max_unhab_mass_share) || 0.015))
        errors.push(`[HABITABILITY] Uninhabitable cell mass share ${max_mass.toFixed(4)} exceeds 0.015.`);
      if (min_hp15 < 900 && min_hp15 < (Number(floors.min_hp15_mean) || 0.20))
        errors.push(`[SHARPNESS] Kriged raster hp15 spatial detail ${min_hp15.toFixed(4)} < ${floors.min_hp15_mean || 0.20} floor (tighten HYDE+KK10 catchments).`);
      if (min_dx < 900 && min_dx < (Number(floors.min_dx_mean) || 0.14))
        errors.push(`[SHARPNESS] Kriged raster dx gradient ${min_dx.toFixed(4)} < ${floors.min_dx_mean || 0.14} floor.`);
      if (max_aniso > (Number(floors.max_manhattan_anisotropy_ratio) || 1.35))
        warnings.push(`[ANISOTROPY] Elevated axis/diagonal gradient anisotropy ${max_aniso.toFixed(3)} (> 1.35); check for Manhattan BFS diamond artefacts.`);

      //Return statement
      return {
        audited_rasters: rep_idxs.length,
        max_anisotropy: Number(max_aniso.toFixed(4)),
        max_unhab_leak_ratio: Number(max_leak.toFixed(4)),
        max_unhab_mass_share: Number(max_mass.toFixed(4)),
        min_dx_mean: min_dx < 900 ? Number(min_dx.toFixed(4)) : null,
        min_hp15_mean: min_hp15 < 900 ? Number(min_hp15.toFixed(4)) : null
      };
    },

    /**
     * Runs full Stage B1 + B3 kriging sharpness, provenance, HYDE+KK10 catchment, subadmin mass conservation,
     * and signed visual manifest verification on a kriging domain directory.
     * @alias kriging_sharpness_auditor.runAudit
     *
     * @param {string} arg0_domain_dir
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    runAudit (arg0_domain_dir, arg1_options) {
      //Convert from parameters
      let domain_dir = path.resolve(arg0_domain_dir);
      let options = arg1_options || {};

      //Declare local instance variables
      let diag_path = path.join(domain_dir, "config/kriging_diagnostics.json");
      let errors = [];
      let svea_root = viscount_audit_utils.findSveaRoot(domain_dir);
      let profiles = viscount_audit_utils.loadSkillProfiles(svea_root);
      let floors = profiles.kriging_sharpness_floors || {};
      let prov_caps = profiles.provenance_caps || {};
      let proj_key = viscount_audit_utils.resolveProjectKey(domain_dir, svea_root);
      let warnings = [];

      //Guard clauses
      if (!fs.existsSync(diag_path))
        return { errors: [`Missing kriging_diagnostics.json: ${diag_path}`], warnings: warnings };

      //Function body
      let diag = viscount_audit_utils.loadJsonOrJson5(diag_path);
      let max_tau1 = Number(floors.max_raw_tau1) || 1.80;
      let max_nug = Number(floors.max_nugget_to_sill_ratio) || 0.45;

      //1. Check global and per-period variogram diagnostics
      let periods = Array.isArray(diag.periods) ? diag.periods :
        (diag.per_period && typeof diag.per_period === "object" ? Object.values(diag.per_period) : []);
      for (let i = 0; i < periods.length; i++) {
        let p = periods[i];
        if (!p || typeof p !== "object") continue;
        let label = p.period || p.id || `period_${i}`;
        let tau1 = Number(p.raw_tau1_dimensionless !== undefined ? p.raw_tau1_dimensionless : p.tau1_dimensionless);
        let nug = Number(p.raw_nugget_to_sill_ratio !== undefined ? p.raw_nugget_to_sill_ratio : p.nugget_to_sill_ratio);
        if (Number.isFinite(tau1) && tau1 > max_tau1)
          errors.push(`[VARIOGRAM] ${label} raw_tau1_dimensionless=${tau1.toFixed(3)} > ${max_tau1}.`);
        if (Number.isFinite(nug) && nug >= max_nug)
          errors.push(`[VARIOGRAM] ${label} raw_nugget_to_sill_ratio=${nug.toFixed(3)} >= ${max_nug}.`);
      }

      if (diag.urban_mask_applied === false)
        errors.push("[URBAN_MASK] urban_mask_applied is false; ViscountUrbanMask is mandatory across all pre-industrial benchmarks.");
      if (Number.isFinite(Number(diag.urban_core_med_ratio)) && Number(diag.urban_core_med_ratio) > (Number(floors.max_urban_core_med_ratio) || 1.60))
        errors.push(`[URBAN_MASK] urban_core_med_ratio=${diag.urban_core_med_ratio} > 1.60.`);
      if (Number.isFinite(Number(diag.urban_backproj_p95_ratio)) && Number(diag.urban_backproj_p95_ratio) > (Number(floors.max_urban_backproj_p95_ratio) || 1.65))
        errors.push(`[URBAN_MASK] urban_backproj_p95_ratio=${diag.urban_backproj_p95_ratio} > 1.65.`);
      if (Number.isFinite(Number(diag.beta_0_hab)) && Number(diag.beta_0_hab) <= 0)
        errors.push(`[HABITABILITY] beta_0_hab=${diag.beta_0_hab} must be > 0.`);
      if (Number.isFinite(Number(diag.log_corr_hyde)) && Number(diag.log_corr_hyde) < (Number(floors.min_log_corr_hyde) || 0.25))
        errors.push(`[HYDE_CORR] log_corr_hyde=${diag.log_corr_hyde} < 0.25.`);

      //2. Check archaeological provenance caps (domain-wide & per jurisdiction)
      let prov = diag.source_provenance_breakdown || {};
      let crowd_share = Number(prov.crowd_share !== undefined ? prov.crowd_share : diag.arch_crowd_share);
      let reg_share = Number(prov.regional_share !== undefined ? prov.regional_share : diag.arch_regional_share);
      if (Number.isFinite(crowd_share) && crowd_share > (Number(prov_caps.max_crowd_kriging_share) || 0.25))
        errors.push(`[PROVENANCE] Domain archaeological crowd share ${(crowd_share*100).toFixed(1)}% > 25%.`);
      if (Number.isFinite(reg_share) && reg_share < (Number(prov_caps.min_regional_arch_share) || 0.50))
        errors.push(`[PROVENANCE] Domain regional/monograph archaeological share ${(reg_share*100).toFixed(1)}% < 50%.`);

      let j_cov = diag.jurisdiction_arch_coverage || {};
      if (proj_key && profiles.jurisdiction_source_matrix && profiles.jurisdiction_source_matrix[proj_key]) {
        let req_j = profiles.jurisdiction_source_matrix[proj_key].required_jurisdictions || [];
        for (let i = 0; i < req_j.length; i++) {
          let jid = req_j[i].id;
          let rec = j_cov[jid];
          if (!rec) {
            warnings.push(`[PROVENANCE] Missing explicit jurisdiction_arch_coverage entry for "${jid}".`);
          } else {
            if (Number(rec.regional_sites || rec.primary_sites || 0) <= 0)
              errors.push(`[PROVENANCE] Jurisdiction "${jid}" has 0 primary regional/monograph archaeological sites.`);
            if (Number(rec.crowd_share || 0) > (Number(prov_caps.max_crowd_kriging_share) || 0.25))
              errors.push(`[PROVENANCE] Jurisdiction "${jid}" crowd share ${(Number(rec.crowd_share)*100).toFixed(1)}% > 25%.`);
          }
        }
      }

      //3. Load domain mask + check c14 multiplier, HYDE+KK10 catchments & raster sharpness
      let mask_info = this.loadDomainMask(domain_dir, svea_root);
      let c14_base = mask_info ? viscount_audit_utils.countC14SitesInMask(svea_root, mask_info.mask) : null;
      let dom_sites = Number(diag.domestic_site_count_unique_sum || diag.domain_sites || 0);
      if (c14_base && c14_base > 0 && dom_sites > 0) {
        let mult = dom_sites/c14_base;
        if (mult < (Number(floors.min_c14_multiplier) || 2.5))
          errors.push(`[ARCH_FLOOR] Domain sites (${dom_sites}) = ${mult.toFixed(2)}x c14 baseline (${c14_base}) < 2.5x anti-stub floor.`);
      }

      let catch_stats = this.auditCatchmentDensityTiers(domain_dir, svea_root, mask_info ? mask_info.mask : null, profiles, errors, warnings);
      let raster_stats = this.auditRastersAndSharpness(domain_dir, svea_root, mask_info ? mask_info.mask : null, floors, errors, warnings);

      //4. Subadmin pycnophylactic mass conservation audit if present
      let mass_cands = [
        path.join(domain_dir, "config/subadmin_mass_conservation_audit.json"),
        path.resolve(domain_dir, "../subadmin_hgis/subadmin_mass_conservation_audit.json")
      ];
      for (let i = 0; i < mass_cands.length; i++) {
        if (fs.existsSync(mass_cands[i])) {
          let ma = viscount_audit_utils.loadJsonOrJson5(mass_cands[i]);
          let worst = Number(ma.worst_unit_rel_err !== undefined ? ma.worst_unit_rel_err : ma.global_max_unit_rel_err);
          if (Number.isFinite(worst) && worst > (Number(floors.max_subadmin_mass_rel_err) || 0.0001))
            errors.push(`[MASS_CONSERVATION] worst_unit_rel_err=${worst} exceeds 1e-4 limit in ${path.basename(mass_cands[i])}.`);
          break;
        }
      }

      //5. Visual verification manifest sign-off check (Stage B3)
      if (options.require_visual_manifest) {
        let vmp = path.join(domain_dir, "config/visual_verification_manifest.json");
        if (!fs.existsSync(vmp)) {
          errors.push(`[VISUAL_MANIFEST] Missing signed visual_verification_manifest.json: ${vmp}`);
        } else {
          let vm = viscount_audit_utils.loadJsonOrJson5(vmp);
          let sheets = Array.isArray(vm.inspected_sheets) ? vm.inspected_sheets : [];
          if (sheets.length === 0)
            errors.push("[VISUAL_MANIFEST] inspected_sheets is empty in visual_verification_manifest.json.");
          for (let i = 0; i < sheets.length; i++) {
            let s = sheets[i];
            if (!s.inspected_via_read_file || String(s.cartographic_notes || "").trim().length < 60)
              errors.push(`[VISUAL_MANIFEST] Sheet ${s.file || i} lacks inspected_via_read_file=true or >= 60-char cartographic_notes.`);
          }
        }
      }

      //Return statement
      return {
        catchments: catch_stats,
        domain_sites: dom_sites,
        errors: errors,
        project: proj_key || "UNKNOWN",
        rasters: raster_stats,
        warnings: warnings
      };
    },

    /**
     * Resolves the `4320x2160` boolean land mask for a kriging domain.
     * @alias kriging_sharpness_auditor.loadDomainMask
     *
     * @param {string} arg0_domain_dir
     * @param {string} arg1_svea_root
     *
     * @returns {{ height: number, mask: Uint8Array, width: number }|null}
     */
    loadDomainMask (arg0_domain_dir, arg1_svea_root) {
      //Convert from parameters
      let domain_dir = arg0_domain_dir;
      let svea_root = arg1_svea_root;

      //Function body
      let cfg_dir = path.join(domain_dir, "config");
      if (fs.existsSync(cfg_dir)) {
        let files = fs.readdirSync(cfg_dir).filter(function (arg0_f) { return /\.json5$/i.test(arg0_f); }).sort();
        for (let i = 0; i < files.length; i++) {
          let cfg = viscount_audit_utils.loadJsonOrJson5(path.join(cfg_dir, files[i]));
          let m_rel = cfg && cfg.kriging_config && cfg.kriging_config.domain_mask_png;
          if (m_rel && svea_root) {
            let m_abs = path.isAbsolute(m_rel) ? m_rel : path.join(svea_root, m_rel);
            if (fs.existsSync(m_abs)) {
              let dec = viscount_audit_utils.decodeRgbaPng(m_abs);
              let mask = new Uint8Array(dec.width*dec.height);
              for (let p = 0; p < mask.length; p++) {
                let p4 = p*4;
                if (dec.data[p4 + 3] > 0 && (dec.data[p4] + dec.data[p4 + 1] + dec.data[p4 + 2]) > 0)
                  mask[p] = 1;
              }
              return { height: dec.height, mask: mask, width: dec.width };
            }
          }
        }
      }

      let k_dir = path.join(domain_dir, "1.kriged_rasters");
      if (fs.existsSync(k_dir)) {
        let pngs = fs.readdirSync(k_dir).filter(function (arg0_f) { return /\.png$/i.test(arg0_f); }).sort();
        if (pngs.length > 0) {
          let dec = viscount_audit_utils.decodeFloat32Png(path.join(k_dir, pngs[0]));
          return { height: dec.height, mask: dec.valid, width: dec.width };
        }
      }

      //Return statement
      return null;
    }
  };

  if (require.main === module) {
    let argv = process.argv.slice(2);
    let target = "";
    let req_vm = false;
    for (let i = 0; i < argv.length; i++) {
      if (argv[i] === "--require-visual-manifest") req_vm = true;
      else if (!argv[i].startsWith("--") && !target) target = argv[i];
    }
    if (!target) {
      console.error("[audit_kriging_sharpness] Usage: node audit_kriging_sharpness.js <domain_dir> [--require-visual-manifest]");
      process.exit(1);
    }
    let res = kriging_sharpness_auditor.runAudit(target, { require_visual_manifest: req_vm });
    for (let i = 0; i < res.warnings.length; i++) console.log(`[WARN] ${res.warnings[i]}`);
    for (let i = 0; i < res.errors.length; i++) console.error(`[FAIL] ${res.errors[i]}`);
    console.log(`[audit_kriging_sharpness] Summary: ${JSON.stringify({ catchments: res.catchments, errors: res.errors.length, project: res.project, rasters: res.rasters, warnings: res.warnings.length })}`);
    process.exit(res.errors.length > 0 ? 1 : 0);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { kriging_sharpness_auditor: kriging_sharpness_auditor };
  }
}
