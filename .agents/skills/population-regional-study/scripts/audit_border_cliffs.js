//Import modules
let fs = require("fs");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");

//Initialise functions
{
  let border_cliffs_auditor = {
    /**
     * Audits internal single-pixel log10 cliffs and aligned cliff-wall run lengths on one float32 GeoPNG.
     * @alias border_cliffs_auditor.auditSingleRaster
     *
     * @param {string} arg0_png_path
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    auditSingleRaster (arg0_png_path, arg1_options) {
      //Convert from parameters
      let options = arg1_options || {};
      let png_path = arg0_png_path;

      //Declare local instance variables
      let dec = viscount_audit_utils.decodeFloat32Png(png_path);
      let f = dec.data;
      let h = dec.height;
      let max_p99_soft = Number(options.max_p99_soft) || 1.25;
      let max_wall = Number(options.max_wall_px) || 18;
      let v = dec.valid;
      let w = dec.width;

      //Function body
      let diffs = [];
      let max_run = 0;

      //Horizontal step checks + vertical wall run tracking
      let col_run = new Int32Array(w);
      for (let r = 0; r < h; r++) {
        let row_off = r*w;
        let row_run = 0;
        for (let c = 0; c < w - 1; c++) {
          let idx = row_off + c;
          if (v[idx] && v[idx + 1] && f[idx] >= 0.05 && f[idx + 1] >= 0.05) {
            let d = Math.abs(Math.log10(f[idx]) - Math.log10(f[idx + 1]));
            diffs.push(d);
            if (d >= 0.602) {
              col_run[c]++;
              if (col_run[c] > max_run) max_run = col_run[c];
            } else {
              col_run[c] = 0;
            }
          } else {
            col_run[c] = 0;
          }

          if (r < h - 1 && v[idx] && v[idx + w] && f[idx] >= 0.05 && f[idx + w] >= 0.05) {
            let dv = Math.abs(Math.log10(f[idx]) - Math.log10(f[idx + w]));
            diffs.push(dv);
            if (dv >= 0.602) {
              row_run++;
              if (row_run > max_run) max_run = row_run;
            } else {
              row_run = 0;
            }
          } else {
            row_run = 0;
          }
        }
      }

      diffs.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
      let p99 = diffs.length > 0 ? diffs[Math.min(diffs.length - 1, Math.floor(diffs.length*0.99))] : 0.0;
      let errors = [];
      if (p99 > max_p99_soft)
        errors.push(`[CLIFF] ${path.basename(png_path)} p99_soft_jump=${p99.toFixed(3)} > ${max_p99_soft}.`);
      if (max_run >= max_wall)
        errors.push(`[CLIFF_WALL] ${path.basename(png_path)} max_wall_run_px=${max_run} >= ${max_wall}.`);

      //Return statement
      return {
        errors: errors,
        file: path.basename(png_path),
        max_wall_run_px: max_run,
        p99_soft_jump: Number(p99.toFixed(4))
      };
    },

    /**
     * Audits cross-region seams between the target project and completed sibling Viscount projects.
     * @alias border_cliffs_auditor.auditInterRegionSeams
     *
     * @param {string} arg0_project_key
     * @param {string} arg1_domain_dir
     * @param {string} arg2_svea_root
     * @param {Array<string>} arg3_errors
     * @param {Array<string>} arg4_warnings
     *
     * @returns {Object}
     */
    auditInterRegionSeams (arg0_project_key, arg1_domain_dir, arg2_svea_root, arg3_errors, arg4_warnings) {
      //Convert from parameters
      let domain_dir = arg1_domain_dir;
      let errors = arg3_errors;
      let proj_key = String(arg0_project_key || "").toUpperCase();
      let svea_root = arg2_svea_root;
      let warnings = arg4_warnings;

      //Guard clauses
      if (!proj_key || !svea_root) return { seams_checked: 0 };

      //Function body
      //Check active frontier buffer points in domain geojson
      let all_gj = path.join(domain_dir, "geojson/00_all_periods.geojson");
      let frontier_pts = 0;
      if (fs.existsSync(all_gj)) {
        let gj = JSON.parse(fs.readFileSync(all_gj, "utf8"));
        let feats = Array.isArray(gj.features) ? gj.features : [];
        for (let i = 0; i < feats.length; i++)
          if (feats[i] && feats[i].properties && feats[i].properties.is_frontier_buffer)
            frontier_pts++;
      }
      if (frontier_pts === 0)
        warnings.push(`[SEAM_BUFFER] ${proj_key} has 0 is_frontier_buffer cross-frontier conditioning sites in 00_all_periods.geojson.`);

      //Check composed rasters in rasters_4.interpolated_to_GHSL or 2.population_rasters
      let comp_dir = path.join(svea_root, "histmap/3.data_transform/population_Substrata.viscount/rasters_4.interpolated_to_GHSL");
      let seam_dir = fs.existsSync(comp_dir) ? comp_dir : path.join(domain_dir, "2.population_rasters");
      if (!fs.existsSync(seam_dir)) return { frontier_pts: frontier_pts, seams_checked: 0 };

      let probe_years = [-2000, 0, 1000, 1500, 1800, 1900];
      let checked = 0;
      for (let i = 0; i < probe_years.length; i++) {
        let y = probe_years[i];
        let cands = [
          path.join(seam_dir, `popc_${y}.png`),
          path.join(seam_dir, y < 0 ? `popc_${Math.abs(y)}BC.png` : `popc_${y}AD.png`)
        ];
        for (let c = 0; c < cands.length; c++) {
          if (fs.existsSync(cands[c])) {
            let res = this.auditSingleRaster(cands[c], { max_p99_soft: 1.25, max_wall_px: 18 });
            errors.push(...res.errors);
            checked++;
            break;
          }
        }
      }

      //Return statement
      return { frontier_pts: frontier_pts, seams_checked: checked };
    },

    /**
     * Audits a domain directory (`1.kriged_rasters/` + `2.population_rasters/`) or single raster PNG.
     * @alias border_cliffs_auditor.runAudit
     *
     * @param {string} arg0_target
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    runAudit (arg0_target, arg1_options) {
      //Convert from parameters
      let options = arg1_options || {};
      let target = path.resolve(arg0_target);

      //Declare local instance variables
      let errors = [];
      let audited = [];
      let svea_root = viscount_audit_utils.findSveaRoot(target);
      let warnings = [];

      //Guard clauses
      if (!fs.existsSync(target))
        return { audited: 0, errors: [`Target not found: ${target}`], warnings: warnings };

      //Function body
      let st = fs.statSync(target);
      if (st.isFile()) {
        let r = this.auditSingleRaster(target, options);
        audited.push(r);
        errors.push(...r.errors);
      } else {
        let subdirs = ["1.kriged_rasters", "2.population_rasters"];
        for (let i = 0; i < subdirs.length; i++) {
          let d = path.join(target, subdirs[i]);
          if (!fs.existsSync(d)) continue;
          let pngs = fs.readdirSync(d).filter(function (arg0_f) { return /\.png$/i.test(arg0_f); }).sort();
          //Sample representative rasters across the chronological span (max 12 per folder for speed)
          let step = Math.max(1, Math.floor(pngs.length/12));
          for (let x = 0; x < pngs.length; x += step) {
            let r = this.auditSingleRaster(path.join(d, pngs[x]), options);
            audited.push(r);
            errors.push(...r.errors);
          }
        }
      }

      let seam_res = null;
      if (options.check_inter_region) {
        let proj = options.project || viscount_audit_utils.resolveProjectKey(target, svea_root);
        seam_res = this.auditInterRegionSeams(proj, target, svea_root, errors, warnings);
      }

      //Return statement
      return {
        audited_count: audited.length,
        errors: errors,
        seams: seam_res,
        warnings: warnings
      };
    }
  };

  if (require.main === module) {
    let argv = process.argv.slice(2);
    let opts = { check_inter_region: false, project: "" };
    let target = "";
    for (let i = 0; i < argv.length; i++) {
      if (argv[i] === "--check-inter-region") opts.check_inter_region = true;
      else if (argv[i] === "--project" && argv[i + 1]) { opts.project = argv[i + 1]; i++; }
      else if (argv[i].startsWith("--project=")) opts.project = argv[i].slice(10);
      else if (!argv[i].startsWith("--") && !target) target = argv[i];
    }
    if (!target) {
      console.error("[audit_border_cliffs] Usage: node audit_border_cliffs.js <domain_dir_or_png> [--check-inter-region --project <KEY>]");
      process.exit(1);
    }
    let res = border_cliffs_auditor.runAudit(target, opts);
    for (let i = 0; i < res.warnings.length; i++) console.log(`[WARN] ${res.warnings[i]}`);
    for (let i = 0; i < res.errors.length; i++) console.error(`[FAIL] ${res.errors[i]}`);
    console.log(`[audit_border_cliffs] Summary: audited=${res.audited_count}, errors=${res.errors.length}, warnings=${res.warnings.length}`);
    process.exit(res.errors.length > 0 ? 1 : 0);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { border_cliffs_auditor: border_cliffs_auditor };
  }
}
