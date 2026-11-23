//Import modules
let fs = require("fs");
let path = require("path");
let { municipal_district_consolidator } = require("./consolidate_municipal_districts");
let { viscount_audit_utils } = require("./viscount_audit_utils");
let { viscount_entity_audit } = require("./viscount_entity_and_continuity_audit");

//Initialise functions
{
  let gazetteer_exhaustiveness_verifier = {
    DUMMY_EXCLUSION_RE: /(?:unnamed|unlocated)\s+seasonal\s+camp|generic\s+camp|placeholder\s+camp|stub\s+entry/i,
    SCRIPT_HEURISTIC_PATTERNS: [
      { msg: "Gibson Top-100 US cities compendium (`twps0027`)", re: /\btwps0027\b/ },
      { msg: "Top-100 city compendium shortcut", re: /\btop_100_cities\b|\btop100_us\b/ },
      { msg: "SQL LIMIT <= 250 cap", re: /\bLIMIT\s+(?:50|100|120|150|200|250)\b/i },
      { msg: "Hard max_settlements <= 250 quota cap", re: /\bmax_settlements\s*=\s*(?:[1-9]\d?|1\d\d|2[0-4]\d|250)\b/ },
      { msg: "Hardcoded synthetic uniform tier array / sine wave population generator", re: /math\.sin\s*\([^)]*\)\s*\*.*pop|placeholder_tiers\s*=/i }
    ],
    VALID_EXCLUDE_REASONS: new Set([
      "outside_study_bounds",
      "subordinate_suburb_merged",
      "intra_municipal_subdivision",
      "unlocated_historical_toponym",
      "duplicate_alias",
      "seasonal_encampment_unquantified",
      "superseded_by_higher_priority_tier"
    ]),

    /**
     * Audits a single settlement gazetteer file (or compiled shard) in regional or compiled mode.
     * @alias gazetteer_exhaustiveness_verifier.auditSingleFile
     *
     * @param {string} arg0_file_path
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    auditSingleFile (arg0_file_path, arg1_options) {
      //Convert from parameters
      let file_path = path.resolve(arg0_file_path);
      let options = arg1_options || {};

      //Declare local instance variables
      let errors = [];
      let svea_root = options.svea_root || viscount_audit_utils.findSveaRoot(file_path);
      let profiles = options.profiles || viscount_audit_utils.loadSkillProfiles(svea_root);
      let dist_guards = profiles.population_distribution_guards || {};
      let mode = options.mode || (file_path.replace(/\\/g, "/").toLowerCase().includes("population_regional") ? "regional" : "compiled");
      let proj_key = options.project || viscount_audit_utils.resolveProjectKey(file_path, svea_root);
      let proj_def = (proj_key && profiles.macro_region_defaults) ? (profiles.macro_region_defaults[proj_key] || {}) : {};
      let warnings = [];

      //Guard clauses
      if (!fs.existsSync(file_path))
        return { errors: [`Missing settlements file: ${file_path}`], stats: {}, warnings: warnings };

      //Function body
      let raw = viscount_audit_utils.loadJsonOrJson5(file_path);
      let entries = [];
      if (Array.isArray(raw)) {
        for (let i = 0; i < raw.length; i++)
          if (raw[i] && typeof raw[i] === "object") entries.push(raw[i]);
      } else if (raw && typeof raw === "object") {
        let ks = Object.keys(raw);
        for (let i = 0; i < ks.length; i++) {
          let v = raw[ks[i]];
          if (v && typeof v === "object") entries.push(Object.assign({ key: ks[i] }, v));
        }
      }

      let count = entries.length;
      if (count === 0)
        return { errors: [`Empty settlement gazetteer: ${path.basename(file_path)}`], stats: { settlements_count: 0 }, warnings: warnings };

      let bad_coords = 0;
      let by_key = new Map();
      let corrupt_names = 0;
      let intra_district_leaks = [];
      let legacy_type = 0;
      let max_year = -99999;
      let missing_sources = 0;
      let peaks = [];
      let pre_foundation = [];
      let suspicious_names = [];
      let unreconciled_aggs = [];
      let viscount_regional_keys = 0;
      let year_counts = new Map();
      let zero_pop = 0;

      //Spatial grid for fast <= 25 km variant-duplicate & <= 1.5 km modern twin detection
      let grid = new Map();
      let modern_year = Number(options.modern_census_year || proj_def.default_modern_census_year || 1850);

      for (let i = 0; i < count; i++) {
        let city = entries[i];
        let ckey = String(city.key || city.name || `entry_${i}`);
        let cname = String(city.name || ckey).trim();
        by_key.set(ckey, city);

        if (ckey.includes("_viscount_regional")) viscount_regional_keys++;
        if (this.isCorruptName(cname, mode === "compiled")) corrupt_names++;

        let is_arch = viscount_entity_audit.hasArchSiteQualifier(cname, profiles);
        if (!city.verified_settlement && !is_arch) {
          let susp = viscount_entity_audit.isSuspiciousToponym(cname, profiles);
          if (susp) suspicious_names.push(`${cname} (${susp})`);
          if (mode === "regional" && municipal_district_consolidator.isIntraMunicipalSubdivision(cname, profiles))
            intra_district_leaks.push(cname);
        }

        if (/\(agglomeration\)/i.test(`${ckey} ${cname}`) && city.population_scope !== "metro")
          unreconciled_aggs.push(ckey);

        if (city.type !== undefined && !Array.isArray(city.sources)) legacy_type++;
        if (options.require_sources && (!Array.isArray(city.sources) || city.sources.length === 0))
          missing_sources++;

        let coords = city.coords;
        let lat = NaN;
        let lon = NaN;
        if (!Array.isArray(coords) || coords.length < 2) {
          bad_coords++;
        } else {
          lat = Number(coords[0]);
          lon = Number(coords[1]);
          if (!Number.isFinite(lat) || !Number.isFinite(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180)
            bad_coords++;
        }

        let pop = city.population;
        let found_yr = Number(city.foundation_year);
        let c_peak = 0;
        let c_min_yr = 99999;
        let c_max_yr = -99999;
        let valid_pos = 0;

        if (pop && typeof pop === "object") {
          let ykeys = Object.keys(pop);
          for (let y = 0; y < ykeys.length; y++) {
            let yi = Number(ykeys[y]);
            let fv = Number(pop[ykeys[y]]);
            if (!Number.isFinite(yi) || !Number.isFinite(fv)) continue;
            if (fv > 0) {
              valid_pos++;
              if (fv > c_peak) c_peak = fv;
              if (yi < c_min_yr) c_min_yr = yi;
              if (yi > c_max_yr) c_max_yr = yi;
              if (yi > max_year) max_year = yi;
              year_counts.set(yi, (year_counts.get(yi) || 0) + 1);
            } else if (mode === "regional") {
              errors.push(`Non-positive population ${fv} at year ${yi} in ${ckey}.`);
              break;
            }
          }
        }

        if (valid_pos === 0) {
          zero_pop++;
        } else {
          peaks.push(c_peak);
          if (Number.isFinite(found_yr) && c_min_yr < found_yr - 5)
            pre_foundation.push(`${ckey}(min=${c_min_yr}<found=${found_yr})`);
        }

        if (Number.isFinite(lat) && Number.isFinite(lon)) {
          let gx = Math.floor(lat*2);
          let gy = Math.floor(lon*2);
          let gk = `${gx},${gy}`;
          if (!grid.has(gk)) grid.set(gk, []);
          grid.get(gk).push({
            city: city,
            country: String(city.country || "").trim().toLowerCase(),
            idx: i,
            key: ckey,
            lat: lat,
            lon: lon,
            max_yr: c_max_yr,
            name: cname,
            scope: String(city.population_scope || "city_proper"),
            stem: viscount_entity_audit.normaliseEntityStem(cname)
          });
        }
      }

      if (viscount_regional_keys > 0)
        errors.push(`Forbidden '_viscount_regional' suffix on ${viscount_regional_keys} key(s).`);
      if (bad_coords > 0) errors.push(`${bad_coords} settlement(s) have missing/invalid coordinates.`);
      if (corrupt_names > 0) errors.push(`${corrupt_names} corrupted city name(s) detected.`);
      if (legacy_type > 0) errors.push(`${legacy_type} settlement(s) use legacy 'type' instead of 'sources' list.`);
      if (missing_sources > 0) errors.push(`${missing_sources} settlement(s) missing non-empty 'sources' list.`);
      if (zero_pop > 0 && mode === "regional") errors.push(`${zero_pop} regional settlement(s) lack positive populations.`);
      if (pre_foundation.length > 0)
        errors.push(`[ANACHRONISM] ${pre_foundation.length} settlement(s) appear before foundation_year: ${pre_foundation.slice(0, 5).join(", ")}`);
      if (suspicious_names.length > 0)
        errors.push(`[SUSPICIOUS_NAME] ${suspicious_names.length} temple/monument/admin name(s): ${suspicious_names.slice(0, 5).join(", ")}`);
      if (intra_district_leaks.length > 0)
        warnings.push(`[INTRA_MUNICIPAL_DISTRICT] ${intra_district_leaks.length} potential intra-municipal subdivision(s) inside municipal limits: ${intra_district_leaks.slice(0, 5).join(", ")}`);
      if (unreconciled_aggs.length > 0)
        errors.push(`[DOUBLE_COUNT] ${unreconciled_aggs.length} untagged (agglomeration) record(s) lacking population_scope="metro": ${unreconciled_aggs.slice(0, 5).join(", ")}`);

      //1. Anti-heuristic pseudo-uniform distribution / shelf / narrow-IQR check (regional mode)
      let dist_stats = {};
      let min_n = Number(dist_guards.min_check_sample_size) || 50;
      if (mode === "regional" && peaks.length >= min_n) {
        let freq = new Map();
        for (let i = 0; i < peaks.length; i++) {
          let p = Math.round(peaks[i]);
          freq.set(p, (freq.get(p) || 0) + 1);
        }
        let counts_desc = Array.from(freq.values()).sort(function (arg0_a, arg1_b) { return arg1_b - arg0_a; });
        let top1_share = counts_desc[0]/peaks.length;
        let top3_share = ((counts_desc[0] || 0) + (counts_desc[1] || 0) + (counts_desc[2] || 0))/peaks.length;
        let uniq_ratio = freq.size/peaks.length;

        let sorted_log = peaks.map(function (arg0_v) { return Math.log10(Math.max(1, arg0_v)); })
          .sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
        let q25 = sorted_log[Math.floor(sorted_log.length*0.25)];
        let q75 = sorted_log[Math.floor(sorted_log.length*0.75)];
        let iqr_log = q75 - q25;

        dist_stats = {
          iqr_log10: Number(iqr_log.toFixed(3)),
          top1_peak_share: Number(top1_share.toFixed(4)),
          top3_peak_share: Number(top3_share.toFixed(4)),
          unique_peak_ratio: Number(uniq_ratio.toFixed(4))
        };

        if (top1_share > (Number(dist_guards.max_single_peak_share) || 0.035))
          errors.push(`[PSEUDO_UNIFORM] Single peak population repeats across ${(top1_share*100).toFixed(1)}% of settlements (> 3.5%); remove flat clamps/placeholder tiers.`);
        if (top3_share > (Number(dist_guards.max_top3_peak_share) || 0.12))
          errors.push(`[PSEUDO_UNIFORM] Top-3 peak populations account for ${(top3_share*100).toFixed(1)}% of settlements (> 12%); populations must be derived strictly from historical evidence.`);
        if (max_year <= 1900 && uniq_ratio < (Number(dist_guards.min_unique_peak_ratio) || 0.55))
          warnings.push(`[PSEUDO_UNIFORM] Pre-modern unique peak ratio is ${(uniq_ratio*100).toFixed(1)}% (< 55%); check for bucketed tiers.`);
        if (iqr_log < (Number(dist_guards.min_interquartile_log10_spread) || 0.40))
          warnings.push(`[PSEUDO_UNIFORM] Narrow log10 population IQR (${iqr_log.toFixed(2)} < 0.40) indicates possible synthetic uniform distribution.`);
      }

      //2. Variant-spelling duplicates <= 25 km & modern same-country twins <= 1.5 km (same scope)
      let variant_dups = [];
      let close_twins = [];
      let grid_entries = Array.from(grid.values());
      for (let g = 0; g < grid_entries.length; g++) {
        let bucket = grid_entries[g];
        for (let i = 0; i < bucket.length; i++) {
          let a = bucket[i];
          let gx = Math.floor(a.lat*2);
          let gy = Math.floor(a.lon*2);
          for (let dx = 0; dx <= 1; dx++) {
            for (let dy = -1; dy <= 1; dy++) {
              if (dx === 0 && dy < 0) continue;
              let nb = grid.get(`${gx + dx},${gy + dy}`);
              if (!nb) continue;
              let start_x = (dx === 0 && dy === 0) ? (i + 1) : 0;
              for (let x = start_x; x < nb.length; x++) {
                let b = nb[x];
                if (Math.abs(a.lat - b.lat) > 0.25 || Math.abs(a.lon - b.lon) > 0.45) continue;
                //Allow reconciled (metro, city_proper) pairs explicitly
                if (a.scope !== b.scope && (a.scope === "metro" || b.scope === "metro")) continue;
                let d_km = viscount_audit_utils.haversineKm(a.lat, a.lon, b.lat, b.lon);
                if (d_km <= 1.5 && a.country && a.country === b.country && a.max_yr >= modern_year && b.max_yr >= modern_year) {
                  if (mode === "compiled" || options.check_close_pairs)
                    close_twins.push(`${a.name}<->${b.name} (${d_km.toFixed(2)} km)`);
                } else if (d_km <= 25.0 && a.stem && b.stem && (a.stem === b.stem || viscount_entity_audit.areEquivalentExonyms(a.name, b.name, profiles))) {
                  if (a.name.toLowerCase() !== b.name.toLowerCase() || d_km <= 5.0)
                    variant_dups.push(`${a.name}<->${b.name} (${d_km.toFixed(1)} km)`);
                }
              }
            }
          }
        }
      }
      if (variant_dups.length > 0)
        errors.push(`[VARIANT_DUP] ${variant_dups.length} variant-spelling/exonym duplicate pair(s) <= 25 km: ${variant_dups.slice(0, 5).join(", ")}`);
      if (close_twins.length > 0)
        errors.push(`[TWINS] ${close_twins.length} same-country modern pair(s) <= 1.5 km: ${close_twins.slice(0, 5).join(", ")}`);

      //3. Regional anti-stub floor + ledger saturation + spatial polygon bounds
      if (mode === "regional" && !options.skip_baseline && count < 35)
        errors.push(`[GUARDRAIL] Regional gazetteer has only ${count} settlements (< 35 anti-stub floor).`);

      let ledger_path = options.ledger || file_path.replace(/_settlements\.json$/i, "_source_ledger.json5");
      let ledger_stats = { excluded: 0, included: 0, total_candidates: 0, unaccounted: 0 };
      if (mode === "regional" && fs.existsSync(ledger_path)) {
        let ledger = viscount_audit_utils.loadJsonOrJson5(ledger_path);
        let cands = Array.isArray(ledger.candidates) ? ledger.candidates : (Array.isArray(ledger) ? ledger : []);
        ledger_stats.total_candidates = cands.length;
        for (let i = 0; i < cands.length; i++) {
          let c = cands[i];
          let st = String(c.status || "").trim().toLowerCase();
          let ck = String(c.settlement_key || c.key || c.name || "");
          if (st === "included") {
            ledger_stats.included++;
          } else if (st === "excluded") {
            ledger_stats.excluded++;
            let r = String(c.reason || "").trim();
            if (!this.VALID_EXCLUDE_REASONS.has(r) || String(c.justification || "").trim().length < 8)
              errors.push(`[LEDGER] Excluded candidate "${ck}" lacks valid reason or justification.`);
            if (this.DUMMY_EXCLUSION_RE.test(ck))
              errors.push(`[GUARDRAIL] Dummy exclusion placeholder in ledger: "${ck}".`);
          } else {
            ledger_stats.unaccounted++;
          }
        }
        if (ledger_stats.unaccounted > 0)
          errors.push(`[SATURATION] ${ledger_stats.unaccounted} unaccounted candidate(s) in ${path.basename(ledger_path)}.`);
        let sat = ledger.saturation_audit || {};
        if (options.require_saturation && Number.isFinite(Number(sat.marginal_gain_pct)) && Number(sat.marginal_gain_pct) > 2.0)
          errors.push(`[SATURATION] marginal_gain_pct=${sat.marginal_gain_pct}% > 2.0% saturation threshold.`);
      } else if (options.require_saturation && mode === "regional") {
        errors.push(`[SATURATION] Missing required source ledger: ${ledger_path}`);
      }

      //4. Spatial sovereign polygon bounds check (using cached Natural Earth index)
      if (options.audit_spatial_bounds && svea_root) {
        let ne_idx = viscount_audit_utils.buildCountryPolygonIndex(svea_root, profiles);
        if (ne_idx) {
          let overrides = profiles.adm0_canonical_overrides || {};
          let buf_deg = proj_def.has_micro_islands ? 0.65 : 0.28;
          let out_bounds = [];
          for (let i = 0; i < entries.length; i++) {
            let c = entries[i];
            if (!Array.isArray(c.coords) || c.coords.length < 2) continue;
            let raw_ctry = String(c.country || "").trim().toLowerCase();
            if (!raw_ctry) continue;
            let mapped = String(overrides[raw_ctry] || raw_ctry).toLowerCase();
            let recs = ne_idx.by_name.get(mapped) || ne_idx.by_name.get(raw_ctry);
            if (!recs) continue;
            if (!viscount_audit_utils.isPointNearCountryPolygons(Number(c.coords[0]), Number(c.coords[1]), recs, buf_deg))
              out_bounds.push(`${c.name || c.key}(${c.country})`);
          }
          if (out_bounds.length > Math.max(3, Math.floor(count*0.02)))
            errors.push(`[SPATIAL_BOUNDS] ${out_bounds.length} settlement(s) fall outside sovereign polygon bounds: ${out_bounds.slice(0, 5).join(", ")}`);
        }
      }

      //5. Temporal density / decennial continuity
      if (options.audit_temporal_density) {
        let post1995_only = 0;
        let active_modern = 0;
        for (let i = 0; i < entries.length; i++) {
          let pop = entries[i].population || {};
          let yrs = Object.keys(pop).map(Number).filter(function (arg0_y) { return Number.isFinite(arg0_y) && Number(pop[arg0_y]) > 0; });
          if (yrs.length === 0) continue;
          let mn = Math.min(...yrs);
          let mx = Math.max(...yrs);
          if (mx >= 1950) {
            active_modern++;
            if (mn >= 1995) post1995_only++;
          }
        }
        if (active_modern >= 30) {
          let ratio = post1995_only/active_modern;
          if (ratio > (Number(dist_guards.max_post_1995_only_ratio) || 0.45))
            warnings.push(`[TEMPORAL_DENSITY] post_1995_only_ratio=${(ratio*100).toFixed(1)}% > 45% (${post1995_only}/${active_modern}).`);
        }
      }

      //Return statement
      return {
        errors: errors,
        file: path.basename(file_path),
        stats: Object.assign({
          corrupt_names: corrupt_names,
          mode: mode,
          settlements_count: count,
          variant_dups: variant_dups.length
        }, dist_stats, ledger_stats),
        warnings: warnings
      };
    },

    /**
     * Batch-audits an entire project directory (all `*_settlements.json` chapters in one fast Node process,
     * plus `_shared/` anti-heuristic script scan and optional `chronology_targets` check).
     * @alias gazetteer_exhaustiveness_verifier.auditProjectDir
     *
     * @param {string} arg0_project_dir
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    auditProjectDir (arg0_project_dir, arg1_options) {
      //Convert from parameters
      let options = arg1_options || {};
      let project_dir = path.resolve(arg0_project_dir);

      //Declare local instance variables
      let all_errors = [];
      let all_warnings = [];
      let per_file = [];
      let svea_root = viscount_audit_utils.findSveaRoot(project_dir);
      let profiles = viscount_audit_utils.loadSkillProfiles(svea_root);
      let proj_key = viscount_audit_utils.resolveProjectKey(project_dir, svea_root);

      //Function body
      let files = viscount_audit_utils.walkFiles(project_dir, function (arg0_p, arg1_n) {
        return /_settlements\.json$/i.test(arg1_n);
      });
      let shared_opts = Object.assign({}, options, { profiles: profiles, project: proj_key, svea_root: svea_root });

      for (let i = 0; i < files.length; i++) {
        let res = this.auditSingleFile(files[i], shared_opts);
        per_file.push(res);
        for (let e = 0; e < res.errors.length; e++)
          all_errors.push(`[${res.file}] ${res.errors[e]}`);
        for (let w = 0; w < res.warnings.length; w++)
          all_warnings.push(`[${res.file}] ${res.warnings[w]}`);
      }

      //Scan _shared scripts once for truncation/heuristic shortcuts
      let shared_dir = path.join(project_dir, "_shared");
      if (fs.existsSync(shared_dir) && !options.skip_script_scan) {
        let scripts = viscount_audit_utils.walkFiles(shared_dir, function (arg0_p, arg1_n) {
          return /\.(?:py|js)$/i.test(arg1_n);
        });
        for (let i = 0; i < scripts.length; i++) {
          let txt = fs.readFileSync(scripts[i], "utf8");
          for (let p = 0; p < this.SCRIPT_HEURISTIC_PATTERNS.length; p++) {
            if (this.SCRIPT_HEURISTIC_PATTERNS[p].re.test(txt))
              all_errors.push(`[HEURISTIC_SCRIPT] ${path.relative(project_dir, scripts[i])}: ${this.SCRIPT_HEURISTIC_PATTERNS[p].msg}`);
          }
        }
      }

      //Return statement
      return {
        chapters_audited: files.length,
        errors: all_errors,
        per_file: per_file,
        project: proj_key || "UNKNOWN",
        warnings: all_warnings
      };
    },

    /**
     * Checks whether a city display name is corrupted.
     * @alias gazetteer_exhaustiveness_verifier.isCorruptName
     *
     * @param {string} arg0_name
     * @param {boolean} [arg1_allow_backtick=false]
     *
     * @returns {boolean}
     */
    isCorruptName (arg0_name, arg1_allow_backtick) {
      //Convert from parameters
      let allow_bt = Boolean(arg1_allow_backtick);
      let s = String(arg0_name || "").trim();

      //Guard clauses
      if (!s || s === "0" || s === "Unknown" || s === "Settlement") return true;
      if (/^[?\s\-_.,]+$/.test(s)) return true;
      if (s.includes("?") || s.includes("\uFFFD") || s.includes("\u00EF\u00BF\u00BD")) return true;
      if (!allow_bt && s.includes("`")) return true;

      //Return statement
      return false;
    },

    /**
     * Parses CLI flags for `verify_gazetteer_exhaustiveness.js`.
     * @alias gazetteer_exhaustiveness_verifier.parseCliArgs
     *
     * @param {Array<string>} arg0_argv
     *
     * @returns {Object}
     */
    parseCliArgs (arg0_argv) {
      //Convert from parameters
      let argv = Array.isArray(arg0_argv) ? arg0_argv : [];

      //Declare local instance variables
      let args = {
        audit_spatial_bounds: false,
        audit_temporal_density: false,
        check_close_pairs: false,
        files: [],
        ledger: "",
        mode: "",
        project_dir: "",
        require_saturation: false,
        require_sources: false,
        skip_baseline: false,
        skip_script_scan: false
      };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok === "--require-sources") args.require_sources = true;
        else if (tok === "--require-saturation") args.require_saturation = true;
        else if (tok === "--audit-temporal-density") args.audit_temporal_density = true;
        else if (tok === "--audit-spatial-bounds") args.audit_spatial_bounds = true;
        else if (tok === "--check-close-pairs") args.check_close_pairs = true;
        else if (tok === "--skip-baseline") args.skip_baseline = true;
        else if (tok === "--skip-script-scan") args.skip_script_scan = true;
        else if (tok === "--ledger" && argv[i + 1]) { args.ledger = argv[i + 1]; i++; }
        else if (tok.startsWith("--ledger=")) args.ledger = tok.slice(9);
        else if (tok === "--mode" && argv[i + 1]) { args.mode = argv[i + 1]; i++; }
        else if (tok.startsWith("--mode=")) args.mode = tok.slice(7);
        else if (tok === "--project-dir" && argv[i + 1]) { args.project_dir = argv[i + 1]; i++; }
        else if (tok.startsWith("--project-dir=")) args.project_dir = tok.slice(14);
        else if (!tok.startsWith("--")) args.files.push(tok);
      }

      //Return statement
      return args;
    }
  };

  if (require.main === module) {
    let cli = gazetteer_exhaustiveness_verifier.parseCliArgs(process.argv.slice(2));
    let t0 = Date.now();
    let res;
    if (cli.project_dir) {
      res = gazetteer_exhaustiveness_verifier.auditProjectDir(cli.project_dir, cli);
    } else if (cli.files.length > 0) {
      let errs = [];
      let warns = [];
      for (let i = 0; i < cli.files.length; i++) {
        let r = gazetteer_exhaustiveness_verifier.auditSingleFile(cli.files[i], cli);
        errs.push(...r.errors);
        warns.push(...r.warnings);
      }
      res = { chapters_audited: cli.files.length, errors: errs, warnings: warns };
    } else {
      console.error("[verify_gazetteer_exhaustiveness] Usage: node verify_gazetteer_exhaustiveness.js (--project-dir <dir> | <file...>) [--require-sources --require-saturation --audit-temporal-density --audit-spatial-bounds]");
      process.exit(1);
    }
    let dt = Date.now() - t0;
    for (let i = 0; i < Math.min(40, res.warnings.length); i++) console.log(`[WARN] ${res.warnings[i]}`);
    for (let i = 0; i < Math.min(40, res.errors.length); i++) console.error(`[FAIL] ${res.errors[i]}`);
    console.log(`[verify_gazetteer_exhaustiveness] Audited ${res.chapters_audited} file(s) in ${dt} ms: errors=${res.errors.length}, warnings=${res.warnings.length}`);
    process.exit(res.errors.length > 0 ? 1 : 0);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { gazetteer_exhaustiveness_verifier: gazetteer_exhaustiveness_verifier };
  }
}
