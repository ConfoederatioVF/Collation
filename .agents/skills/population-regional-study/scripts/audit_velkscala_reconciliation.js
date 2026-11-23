//Import modules
let fs = require("fs");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");

//Initialise functions
{
  let velkscala_reconciliation_auditor = {
    CIRCULAR_RURAL_PAT: /stadester_rural_/i,
    FLOAT32_ALPHA_PAT: /(?:png|img)(?:_obj)?\.data\[[^\]]*\+\s*3\]\s*>\s*0/,
    SKIP_DIRS: new Set(["_gis_cache", "node_modules", ".git", "diagnostics_visual", "figures", "papers"]),

    /**
     * Runs static script anti-pattern checks, Velkscala raster reconciliation probes (Swiss-cheese + sub-5k floor),
     * and 3-Phase metro conservation & 1974->1975 DEGURBA continuity checks across a Viscount macro-region.
     * @alias velkscala_reconciliation_auditor.auditVelkscala
     *
     * @param {string} arg0_project
     * @param {Array<number>} arg1_years
     * @param {Object} [arg2_options]
     *
     * @returns {{ errors: Array<string>, summary: Object, warnings: Array<string> }}
     */
    auditVelkscala (arg0_project, arg1_years, arg2_options) {
      //Convert from parameters
      let opts = (arg2_options) ? arg2_options : {};
      let project_key = String(arg0_project || "").toUpperCase();
      let years = Array.isArray(arg1_years) ? arg1_years : [-2000, 0, 900, 1400, 1900];

      //Declare local instance variables
      let errors = [];
      let svea_root = opts.svea_root || viscount_audit_utils.findSveaRoot(process.cwd());
      let warnings = [];

      //Guard clauses
      if (!svea_root)
        return { errors: ["Unable to locate SVEA repository root."], summary: {}, warnings: warnings };

      let ctx = this.resolveProjectContext(project_key, svea_root);
      if (!ctx.proj_entry && !opts.velkscala_dir)
        return { errors: [`Unknown Viscount project key: ${project_key}`], summary: {}, warnings: warnings };

      //Function body
      // 1. Static script anti-pattern scan
      let scan_dirs = [path.join(svea_root, "histmap/1.data_raw/population_regional", project_key)];
      if (opts.scan_dir) scan_dirs.push(opts.scan_dir);
      let scan_errs = this.scanScriptsForAntipatterns(scan_dirs);
      for (let i = 0; i < scan_errs.length; i++) errors.push(scan_errs[i]);

      let velk_dir = opts.velkscala_dir || path.join(svea_root, "histmap/2.data_cleaning/population_Velkscala");
      let pop_dir = path.join(velk_dir, "population_rasters");
      let rur_dir = path.join(velk_dir, "population_rural_rasters");
      if (!fs.existsSync(pop_dir) || !fs.existsSync(rur_dir)) {
        if (opts.scan_only)
          return { errors: errors, summary: { rasters_checked: 0, scripts_scanned: true }, warnings: warnings };
        errors.push(`Missing Velkscala raster folders in ${velk_dir}`);
        return { errors: errors, summary: {}, warnings: warnings };
      }

      let union_mask = this.buildProjectUnionMask(ctx.proj_entry, svea_root, 4320, 2160);
      let shard_data = this.loadProjectShards(ctx.proj_entry, svea_root);
      let cities = shard_data.cities;
      let shard_mtime = shard_data.newest_mtime;
      let has_micro_islands = Boolean(ctx.defaults && ctx.defaults.has_micro_islands);
      let rad = has_micro_islands ? 2 : 1;

      // 2. Check 3-Phase metro reconciliation & 1974->1975 DEGURBA continuity on compiled shards
      let metro_stats = this.auditMetroContinuity(cities, errors, warnings);

      let land_p = path.join(svea_root, "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png");
      let land_valid = null;
      if (fs.existsSync(land_p) && !opts.velkscala_dir) {
        let land_dec = viscount_audit_utils.decodeUint32Png(land_p);
        land_valid = new Uint8Array(land_dec.width*land_dec.height);
        for (let i = 0; i < land_valid.length; i++)
          land_valid[i] = land_dec.data[i] > 0 ? 1 : 0;
      }

      let yr_stats = [];
      for (let yi = 0; yi < years.length; yi++) {
        let yr = years[yi];
        let pop_p = path.join(pop_dir, `population_${yr}.png`);
        let rur_p = path.join(rur_dir, `population_rural_${yr}.png`);
        if (!fs.existsSync(pop_p) || !fs.existsSync(rur_p)) {
          warnings.push(`Skipped missing Velkscala pair for yr=${yr}.`);
          continue;
        }

        let pop_dec = viscount_audit_utils.decodeFloat32Png(pop_p);
        let rur_dec = viscount_audit_utils.decodeFloat32Png(rur_p);
        let h = pop_dec.height;
        let w = pop_dec.width;
        let pop = pop_dec.data;
        let rur = rur_dec.data;
        let use_union = Boolean(union_mask && union_mask.length === w*h);
        let use_land = Boolean(land_valid && land_valid.length === w*h);

        let hole_cnt = 0;
        let inhabited_px = 0;
        for (let r = 0; r < h; r++) {
          let row_off = r*w;
          for (let c = 0; c < w; c++) {
            let idx = row_off + c;
            let in_reg = (!use_union || union_mask[idx] === 1) && (!use_land || land_valid[idx] === 1);
            if (!in_reg) continue;
            if (pop[idx] > 0) inhabited_px++;
            if (r > 0 && r < h - 1 && c > 0 && c < w - 1 && rur[idx] === 0 && pop[idx] === 0) {
              if (rur[idx - w - 1] > 5 && rur[idx - w] > 5 && rur[idx - w + 1] > 5 &&
                  rur[idx - 1] > 5 && rur[idx + 1] > 5 &&
                  rur[idx + w - 1] > 5 && rur[idx + w] > 5 && rur[idx + w + 1] > 5) {
                hole_cnt++;
              }
            }
          }
        }

        let max_allowed_holes = Math.max(15, Math.floor(0.0005*inhabited_px));
        if (hole_cnt > max_allowed_holes)
          errors.push(`[SWISS_CHEESE] yr=${yr}: detected ${hole_cnt} isolated exact-zero interior rural pixel(s) (limit <= ${max_allowed_holes}, indicates float32 alpha-byte decoding bug).`);

        // Sub-5k floor check
        let sub5k_checked = 0;
        let sub5k_dropped = 0;
        if (yr > 1 && cities.length > 0) {
          for (let i = 0; i < cities.length; i++) {
            let c_obj = cities[i];
            let pv = (c_obj.population && c_obj.population[String(yr)] !== undefined) ? Number(c_obj.population[String(yr)]) : 0;
            if (!(pv > 0 && pv < 5000)) continue;
            let coords = c_obj.coords;
            if (!Array.isArray(coords) || coords.length < 2) continue;
            let rr = Math.min(h - 1, Math.max(0, Math.floor((90.0 - Number(coords[0]))*h/180.0)));
            let cc = Math.min(w - 1, Math.max(0, Math.floor((Number(coords[1]) + 180.0)*w/360.0)));
            if (use_union && !union_mask[rr*w + cc]) continue;
            sub5k_checked++;
            let win_max = 0;
            for (let dr = -rad; dr <= rad; dr++) {
              let nr = rr + dr;
              if (nr < 0 || nr >= h) continue;
              for (let dc = -rad; dc <= rad; dc++) {
                let nc = cc + dc;
                if (nc < 0 || nc >= w) continue;
                let v = pop[nr*w + nc];
                if (v > win_max) win_max = v;
              }
            }
            if (win_max < 0.5*pv) sub5k_dropped++;
          }
          if (sub5k_checked >= 20) {
            let drop_ratio = sub5k_dropped/sub5k_checked;
            let velk_mtime = fs.statSync(pop_p).mtimeMs/1000.0;
            if (drop_ratio > 0.05) {
              let msg = `[SUB5K_DROP] yr=${yr}: ${sub5k_dropped}/${sub5k_checked} (${(drop_ratio*100).toFixed(1)}%) sub-5k settlements lack gridcell floor support in population_Velkscala.`;
              if (shard_mtime > velk_mtime + 60.0 && !opts.require_fresh_velkscala)
                warnings.push(`${msg} (Note: Velkscala PNG predates newest Stadestér shard; rebuild Velkscala to sync.)`);
              else
                errors.push(msg);
            }
          }
        }

        yr_stats.push({ holes: hole_cnt, sub5k_checked: sub5k_checked, sub5k_dropped: sub5k_dropped, yr: yr });
      }

      //Return statement
      return {
        errors: errors,
        summary: { metro_continuity: metro_stats, project: project_key, years_checked: yr_stats },
        warnings: warnings
      };
    },

    /**
     * Checks compiled shards for negative-residual metro leaks and 1974->1975 DEGURBA boundary shocks.
     * @alias velkscala_reconciliation_auditor.auditMetroContinuity
     *
     * @param {Array<Object>} arg0_cities
     * @param {Array<string>} arg1_errors
     * @param {Array<string>} arg2_warnings
     *
     * @returns {Object}
     */
    auditMetroContinuity (arg0_cities, arg1_errors, arg2_warnings) {
      //Convert from parameters
      let cities = Array.isArray(arg0_cities) ? arg0_cities : [];
      let errors = arg1_errors;
      let warnings = arg2_warnings;

      //Declare local instance variables
      let degurba_shocks = [];
      let negative_metro_vals = 0;

      //Function body
      for (let i = 0; i < cities.length; i++) {
        let c = cities[i];
        let pop = (c && c.population && typeof c.population === "object") ? c.population : null;
        if (!pop) continue;
        let is_metro = (c.extent_type === "metro") || /agglomeration|metropolitan/i.test(String(c.name || ""));
        let ykeys = Object.keys(pop);
        for (let x = 0; x < ykeys.length; x++) {
          let v = Number(pop[ykeys[x]]);
          if (Number.isFinite(v) && v < 0) negative_metro_vals++;
        }
        if (is_metro && pop["1974"] > 50000 && pop["1975"] > 0) {
          let r = Number(pop["1975"])/Number(pop["1974"]);
          if (r > 1.35 || r < 0.70)
            degurba_shocks.push(`${c.name}(1974=${Math.round(pop["1974"])}->1975=${Math.round(pop["1975"])})`);
        }
      }

      if (negative_metro_vals > 0)
        errors.push(`[METRO_RECON] Detected ${negative_metro_vals} negative population value(s) in compiled shards; negative metro residuals must be redistributed and the metro datapoint removed for year t.`);
      if (degurba_shocks.length > 0)
        warnings.push(`[METRO_DEGURBA] ${degurba_shocks.length} metro datapoint(s) show >35% jump across 1974->1975 DEGURBA boundary: ${degurba_shocks.slice(0, 5).join(", ")}`);

      //Return statement
      return { degurba_shocks: degurba_shocks.length, negative_metro_vals: negative_metro_vals };
    },

    /**
     * Builds boolean union mask from `areal_masks_manifest` if available.
     * @alias velkscala_reconciliation_auditor.buildProjectUnionMask
     *
     * @param {Object|null} arg0_proj
     * @param {string} arg1_svea_root
     * @param {number} [arg2_width=4320]
     * @param {number} [arg3_height=2160]
     *
     * @returns {Uint8Array|null}
     */
    buildProjectUnionMask (arg0_proj, arg1_svea_root, arg2_width, arg3_height) {
      //Convert from parameters
      let h = Number(arg3_height) || 2160;
      let proj = arg0_proj;
      let svea_root = arg1_svea_root;
      let w = Number(arg2_width) || 4320;

      //Guard clauses
      if (!proj || !proj.areal_masks_manifest) return null;
      let am_abs = path.join(svea_root, proj.areal_masks_manifest);
      if (!fs.existsSync(am_abs)) return null;

      //Declare local instance variables
      let am = viscount_audit_utils.loadJsonOrJson5(am_abs);
      let any_set = false;
      let items = [];
      let union_m = new Uint8Array(w*h);

      //Function body
      if (am && am.macro_mask && typeof am.macro_mask === "object") items.push(am.macro_mask);
      if (am && Array.isArray(am.specialist_masks)) items = items.concat(am.specialist_masks);

      for (let i = 0; i < items.length; i++) {
        let mp = items[i] && items[i].mask_path;
        if (!mp) continue;
        let m_abs = path.isAbsolute(mp) ? mp : path.join(svea_root, mp);
        if (!fs.existsSync(m_abs)) continue;
        let dec = viscount_audit_utils.decodeRgbaPng(m_abs);
        if (dec.width !== w || dec.height !== h) continue;
        let buf = dec.data;
        for (let p = 0; p < w*h; p++) {
          let p4 = p*4;
          if (buf[p4 + 3] > 0 && (buf[p4] + buf[p4 + 1] + buf[p4 + 2]) > 0) {
            union_m[p] = 1;
            any_set = true;
          }
        }
      }

      //Return statement
      return any_set ? union_m : null;
    },

    /**
     * Loads compiled shard settlements for `arg0_proj` from Stadestér 2.0 visualisation outputs.
     * @alias velkscala_reconciliation_auditor.loadProjectShards
     *
     * @param {Object|null} arg0_proj
     * @param {string} arg1_svea_root
     *
     * @returns {{ cities: Array<Object>, newest_mtime: number }}
     */
    loadProjectShards (arg0_proj, arg1_svea_root) {
      //Convert from parameters
      let proj = arg0_proj;
      let svea_root = arg1_svea_root;

      //Guard clauses
      if (!proj) return { cities: [], newest_mtime: 0 };
      let shard_dir = path.join(svea_root, "histmap/5.data_visualisation/stadester/stadester_2.0");
      let man_path = path.join(shard_dir, "stadester_manifest.json");
      if (!fs.existsSync(man_path)) return { cities: [], newest_mtime: 0 };

      //Declare local instance variables
      let cities = [];
      let man = JSON.parse(fs.readFileSync(man_path, "utf8"));
      let newest_mtime = 0;
      let target_key = String(proj.key || "").toUpperCase();
      let regions = Array.isArray(man.regions) ? man.regions : [];
      let reg = null;

      //Function body
      for (let i = 0; i < regions.length; i++) {
        if (String(regions[i].key || "").toUpperCase() === target_key) {
          reg = regions[i];
          break;
        }
      }
      if (!reg || !Array.isArray(reg.files)) return { cities: [], newest_mtime: 0 };

      for (let i = 0; i < reg.files.length; i++) {
        let fp = path.join(shard_dir, reg.files[i]);
        if (!fs.existsSync(fp)) continue;
        let mt = fs.statSync(fp).mtimeMs/1000.0;
        if (mt > newest_mtime) newest_mtime = mt;
        let data = JSON.parse(fs.readFileSync(fp, "utf8"));
        if (data && typeof data === "object") {
          let vals = Object.values(data);
          for (let x = 0; x < vals.length; x++) cities.push(vals[x]);
        }
      }

      //Return statement
      return { cities: cities, newest_mtime: newest_mtime };
    },

    /**
     * Parses CLI flags.
     * @alias velkscala_reconciliation_auditor.parseCliArgs
     *
     * @param {Array<string>} arg0_argv
     *
     * @returns {Object}
     */
    parseCliArgs (arg0_argv) {
      //Convert from parameters
      let argv = Array.isArray(arg0_argv) ? arg0_argv : [];

      //Declare local instance variables
      let out = {
        project: "",
        require_fresh_velkscala: false,
        scan_dir: null,
        scan_only: false,
        velkscala_dir: null,
        years: [-2000, 0, 900, 1400, 1900]
      };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok === "--project" && i + 1 < argv.length) out.project = argv[++i];
        else if (tok.startsWith("--project=")) out.project = tok.slice(10);
        else if (tok === "--years" && i + 1 < argv.length)
          out.years = argv[++i].split(",").map(Number).filter(Number.isFinite);
        else if (tok.startsWith("--years="))
          out.years = tok.slice(8).split(",").map(Number).filter(Number.isFinite);
        else if (tok === "--scan-dir" && i + 1 < argv.length) out.scan_dir = argv[++i];
        else if (tok.startsWith("--scan-dir=")) out.scan_dir = tok.slice(11);
        else if (tok === "--velkscala-dir" && i + 1 < argv.length) out.velkscala_dir = argv[++i];
        else if (tok.startsWith("--velkscala-dir=")) out.velkscala_dir = tok.slice(16);
        else if (tok === "--scan-only") out.scan_only = true;
        else if (tok === "--require-fresh-velkscala") out.require_fresh_velkscala = true;
      }

      //Return statement
      return out;
    },

    /**
     * Loads precedence entry and macro-region defaults for a Viscount project.
     * @alias velkscala_reconciliation_auditor.resolveProjectContext
     *
     * @param {string} arg0_project_key
     * @param {string} arg1_svea_root
     *
     * @returns {{ defaults: Object, proj_entry: Object|null }}
     */
    resolveProjectContext (arg0_project_key, arg1_svea_root) {
      //Convert from parameters
      let key = String(arg0_project_key || "").toUpperCase();
      let svea_root = arg1_svea_root;

      //Declare local instance variables
      let prec_p = path.join(svea_root, "histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5");
      let prof = viscount_audit_utils.loadSkillProfiles(svea_root);
      let proj_entry = null;

      //Function body
      if (fs.existsSync(prec_p)) {
        let prec = viscount_audit_utils.loadJsonOrJson5(prec_p);
        let list = Array.isArray(prec.projects) ? prec.projects : [];
        for (let i = 0; i < list.length; i++) {
          if (String(list[i].key || "").toUpperCase() === key) {
            proj_entry = list[i];
            break;
          }
        }
      }

      //Return statement
      return {
        defaults: (prof && prof.macro_region_defaults && prof.macro_region_defaults[key]) ? prof.macro_region_defaults[key] : {},
        proj_entry: proj_entry
      };
    },

    /**
     * Scans regional pipeline & kriging scripts for float32 alpha-byte bugs and circular `stadester_rural_*` reads.
     * @alias velkscala_reconciliation_auditor.scanScriptsForAntipatterns
     *
     * @param {Array<string>} arg0_dirs
     *
     * @returns {Array<string>}
     */
    scanScriptsForAntipatterns (arg0_dirs) {
      //Convert from parameters
      let dirs = Array.isArray(arg0_dirs) ? arg0_dirs : [];

      //Declare local instance variables
      let errors = [];

      //Function body
      for (let d = 0; d < dirs.length; d++) {
        let root_dir = dirs[d];
        if (!root_dir || !fs.existsSync(root_dir) || !fs.statSync(root_dir).isDirectory()) continue;
        let files = viscount_audit_utils.walkFiles(root_dir, function (arg0_full, arg1_name) {
          return /\.(?:js|py)$/i.test(arg1_name);
        }, this.SKIP_DIRS);

        for (let i = 0; i < files.length; i++) {
          let fp = files[i];
          let fn_low = path.basename(fp).toLowerCase();
          let is_krige = fn_low.includes("krige") || fn_low.includes("matern");
          let lines = fs.readFileSync(fp, "utf8").split(/\r?\n/);
          let rel = path.relative(root_dir, fp).replace(/\\/g, "/");
          for (let idx = 0; idx < lines.length; idx++) {
            let ln = lines[idx];
            if (this.FLOAT32_ALPHA_PAT.test(ln) && !ln.includes("getFloat32") && !ln.includes("|"))
              errors.push(`[FLOAT32_BUG] ${rel}:${idx + 1}: unsafe \`png.data[... + 3] > 0\` alpha check zeroes valid IEEE-754 float32 pixels with 0x00 low mantissa byte; use 4-byte OR + DataView.getFloat32.`);
            if (is_krige && this.CIRCULAR_RURAL_PAT.test(ln))
              errors.push(`[CIRCULAR_READ] ${rel}:${idx + 1}: kriging script reads downstream \`stadester_rural_*\` raster.`);
          }
        }
      }

      //Return statement
      return errors;
    }
  };

  if (require.main === module) {
    let cli = velkscala_reconciliation_auditor.parseCliArgs(process.argv.slice(2));
    if (!cli.project) {
      console.error("Usage: node audit_velkscala_reconciliation.js --project <KEY> [--years -2000,0,900,1400,1900] [--scan-only]");
      process.exit(2);
    }
    let res = velkscala_reconciliation_auditor.auditVelkscala(cli.project, cli.years, cli);
    for (let i = 0; i < Math.min(30, res.warnings.length); i++)
      console.log(`[WARN] ${res.warnings[i]}`);
    for (let i = 0; i < Math.min(30, res.errors.length); i++)
      console.error(`[FAIL] ${res.errors[i]}`);
    console.log(`[audit_velkscala_reconciliation] Summary: ${JSON.stringify(res.summary)}`);
    process.exit(res.errors.length === 0 ? 0 : 1);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { velkscala_reconciliation_auditor: velkscala_reconciliation_auditor };
  }
}
