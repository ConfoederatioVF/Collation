//Import modules
let fs = require("fs");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");
let { viscount_entity_audit } = require("./viscount_entity_and_continuity_audit");

//Initialise functions
{
  let city_metadata_auditor = {
    ARTICLE_INVERT_RE: /^.+,\s*(?:Al|El|As|Ash|Ar|Az|Ad|An|At|Le|La|Les|L'|Los|Las|Il|Lo|De|Den|Het|Der|Die|Das|The)$/i,
    FOREIGN_SCRIPT_RE: /[\u0400-\u04FF\u0600-\u06FF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]/,
    MULTI_COMMA_ADDR_RE: /^[^,]+,\s*[^,]+,\s*[^,]+$/,
    PAREN_RE: /\([^)]*\)/,

    /**
     * Audits partitioned `city_metadata/` (or legacy `city_metadata.json`) for structural integrity,
     * unified capital-city naming, zero collisions, zero corruptions, zero intra-municipal district leaks,
     * and optional toponymy auditor sign-off.
     * @alias city_metadata_auditor.auditMetadata
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Object}
     */
    auditMetadata (arg0_options) {
      //Convert from parameters
      let opts = (arg0_options) ? arg0_options : {};
      let dataset_id = String(opts.dataset || "stadester_2.0").replace(/\.json$/i, "");
      let project_key = String(opts.project || "").toUpperCase();
      let svea_root = opts.svea_root ? path.resolve(opts.svea_root) : (viscount_audit_utils.findSveaRoot(__dirname) || path.resolve(__dirname, "../../../.."));
      let dataview_root = opts.dataview_root ? path.resolve(opts.dataview_root) :
        (process.env.DATAVIEW_ROOT ? path.resolve(process.env.DATAVIEW_ROOT) : path.resolve(svea_root, "../Project 1436 - Dataview"));

      //Declare local instance variables
      let errors = [];
      let profiles = viscount_audit_utils.loadSkillProfiles(svea_root);
      let mun_rules = (profiles && profiles.municipal_decomposition_rules) ? profiles.municipal_decomposition_rules : {};
      let mun_regexes = (Array.isArray(mun_rules.intra_municipal_suffix_regexes) ? mun_rules.intra_municipal_suffix_regexes : []).map(function (arg0_r) {
        return new RegExp(arg0_r, "i");
      });
      let stadester_dir = path.join(dataview_root, "data/stadester", dataset_id);
      let part_dir = path.join(stadester_dir, "city_metadata");
      let man_path = path.join(part_dir, "city_metadata_manifest.json");
      let mono_path = path.join(stadester_dir, "city_metadata.json");
      let warnings = [];

      //Function body
      let loaded_records = [];
      let capitals_records = [];
      let is_partitioned = fs.existsSync(man_path);

      if (is_partitioned) {
        let man = JSON.parse(fs.readFileSync(man_path, "utf8"));
        let shards = Array.isArray(man.shards) ? man.shards : [];
        let has_cap_shard = false;
        for (let i = 0; i < shards.length; i++) {
          let sh = shards[i];
          let sp = path.join(part_dir, sh.file);
          if (!fs.existsSync(sp)) {
            errors.push(`[PARTITION] Missing shard file referenced in manifest: ${sh.file}`);
            continue;
          }
          let is_cap = sh.key === "CAPITALS" || sh.file === "00_capitals.json";
          if (is_cap) has_cap_shard = true;
          if (project_key && !is_cap && sh.key !== project_key) continue;

          let arr = JSON.parse(fs.readFileSync(sp, "utf8"));
          for (let x = 0; x < arr.length; x++) {
            loaded_records.push({ rec: arr[x], shard: sh.file });
            if (is_cap) capitals_records.push(arr[x]);
          }
        }
        if (!has_cap_shard)
          errors.push("[CAPITALS] Partitioned city_metadata_manifest.json missing Priority Tier 0 `00_capitals.json`.");
      } else if (fs.existsSync(mono_path)) {
        warnings.push("[PARTITION] Auditing legacy monolithic city_metadata.json; run partition_city_metadata.js to partition.");
        let arr = JSON.parse(fs.readFileSync(mono_path, "utf8"));
        for (let i = 0; i < arr.length; i++) loaded_records.push({ rec: arr[i], shard: "city_metadata.json" });
      } else {
        errors.push(`Neither partitioned city_metadata/ nor monolithic city_metadata.json exists in ${stadester_dir}`);
        return { errors: errors, stats: {}, success: false, warnings: warnings };
      }

      // Audit individual records
      let stats = {
        backtick_or_mojibake: 0,
        bad_dates: 0,
        capitals_checked: capitals_records.length,
        capitals_missing_name: 0,
        collisions: 0,
        foreign_script_spam: 0,
        inverted_articles: 0,
        multi_comma_addr: 0,
        municipal_leaks: 0,
        parenthetical_names: 0,
        records_checked: loaded_records.length
      };

      let bad_samples = {
        backtick: [],
        collisions: [],
        dates: [],
        inverted: [],
        multi_comma: [],
        municipal: [],
        paren: []
      };

      let grid = new Map();
      for (let i = 0; i < loaded_records.length; i++) {
        let rec = loaded_records[i].rec;
        let shard_fn = loaded_records[i].shard;
        if (!rec || typeof rec !== "object") continue;

        let nm = String(rec.name || "").trim();
        let coords = Array.isArray(rec.coords) ? rec.coords : [];
        let lng = Number(coords[0]);
        let lat = Number(coords[1]);
        let is_cap_shard = shard_fn === "00_capitals.json";

        if (is_cap_shard) {
          let has_cap_data = Boolean(
            (rec.capital && typeof rec.capital === "object" && Object.keys(rec.capital).length > 0) ||
            (Array.isArray(rec.capital_records) && rec.capital_records.length > 0)
          );
          if (!nm || !Array.isArray(rec.historical_names) || rec.historical_names.length === 0 || !has_cap_data)
            stats.capitals_missing_name++;
        }

        if (!nm || nm.includes("`") || nm.includes("?") || nm.includes("\uFFFD") || nm === "0" || nm === "Unknown") {
          stats.backtick_or_mojibake++;
          if (bad_samples.backtick.length < 5) bad_samples.backtick.push(`${shard_fn}:${nm}`);
        }
        if (this.ARTICLE_INVERT_RE.test(nm)) {
          stats.inverted_articles++;
          if (bad_samples.inverted.length < 5) bad_samples.inverted.push(`${shard_fn}:${nm}`);
        }
        if (this.MULTI_COMMA_ADDR_RE.test(nm) && /\d{3,}/.test(nm)) {
          stats.multi_comma_addr++;
          if (bad_samples.multi_comma.length < 5) bad_samples.multi_comma.push(`${shard_fn}:${nm}`);
        }
        if (this.PAREN_RE.test(nm)) {
          stats.parenthetical_names++;
          if (bad_samples.paren.length < 5) bad_samples.paren.push(`${shard_fn}:${nm}`);
        }
        if (!rec.verified_settlement) {
          for (let m = 0; m < mun_regexes.length; m++) {
            if (mun_regexes[m].test(nm)) {
              stats.municipal_leaks++;
              if (bad_samples.municipal.length < 5) bad_samples.municipal.push(`${shard_fn}:${nm}`);
              break;
            }
          }
        }

        // Check historical_names dates & clean strings
        let hn = Array.isArray(rec.historical_names) ? rec.historical_names : [];
        let prev_yr = -999999;
        for (let x = 0; x < hn.length; x++) {
          let h = hn[x];
          if (!h || !viscount_entity_audit.isValidCalendarDate(h.date)) {
            stats.bad_dates++;
            if (bad_samples.dates.length < 5) bad_samples.dates.push(`${nm}:${h ? h.date : "null"}`);
            continue;
          }
          let yr = Number(String(h.date).split(".")[0]);
          if (yr < prev_yr) {
            stats.bad_dates++;
            if (bad_samples.dates.length < 5) bad_samples.dates.push(`${nm}:unsorted(${prev_yr}->${yr})`);
          }
          prev_yr = yr;
          let hname = String(h.name || "");
          if (hname.includes("`") || hname.includes("?") || hname.includes("\uFFFD")) {
            stats.backtick_or_mojibake++;
            if (bad_samples.backtick.length < 5) bad_samples.backtick.push(`${nm}->${hname}`);
          }
          if (this.PAREN_RE.test(hname)) {
            stats.parenthetical_names++;
            if (bad_samples.paren.length < 5) bad_samples.paren.push(`${nm}->${hname}`);
          }
        }

        // Check foreign-script spam in Latin-only countries
        if (rec.country && Array.isArray(rec.other_names) &&
            viscount_entity_audit.isLatinScriptOnlyCountry(rec.country, [lat, lng], profiles)) {
          for (let x = 0; x < rec.other_names.length; x++) {
            if (this.FOREIGN_SCRIPT_RE.test(String(rec.other_names[x] || "")))
              stats.foreign_script_spam++;
          }
        }

        // Spatial collision check (<= 1.5 km same-stem or <= 0.15 km exact duplicate)
        if (Number.isFinite(lat) && Number.isFinite(lng)) {
          let stem = viscount_entity_audit.normaliseEntityStem(nm);
          let gx = Math.round(lat*20);
          let gy = Math.round(lng*20);
          for (let dx = -1; dx <= 1; dx++) {
            for (let dy = -1; dy <= 1; dy++) {
              let b = grid.get(`${gx + dx},${gy + dy}`);
              if (!b) continue;
              for (let z = 0; z < b.length; z++) {
                let d_km = viscount_audit_utils.haversineKm(lat, lng, b[z].lat, b[z].lng);
                if (d_km <= 0.15 || (d_km <= 1.5 && stem && b[z].stem === stem)) {
                  stats.collisions++;
                  if (bad_samples.collisions.length < 5)
                    bad_samples.collisions.push(`${nm}<->${b[z].name} (${d_km.toFixed(2)} km)`);
                }
              }
            }
          }
          let gk = `${gx},${gy}`;
          if (!grid.has(gk)) grid.set(gk, []);
          grid.get(gk).push({ lat: lat, lng: lng, name: nm, stem: stem });
        }
      }

      if (stats.capitals_missing_name > 0)
        errors.push(`[CAPITALS] ${stats.capitals_missing_name} capital record(s) in 00_capitals.json lack clean name, historical_names or capital_records.`);
      if (stats.backtick_or_mojibake > 0)
        errors.push(`[ENCODING] ${stats.backtick_or_mojibake} backtick/mojibake/placeholder name(s): ${bad_samples.backtick.join(", ")}`);
      if (stats.inverted_articles > 0)
        errors.push(`[INVERTED_ARTICLE] ${stats.inverted_articles} comma-inverted article name(s): ${bad_samples.inverted.join(", ")}`);
      if (stats.multi_comma_addr > 0)
        errors.push(`[ADDRESS_JUNK] ${stats.multi_comma_addr} multi-comma street/postal address record(s): ${bad_samples.multi_comma.join(", ")}`);
      if (stats.parenthetical_names > 0)
        errors.push(`[PARENTHETICAL] ${stats.parenthetical_names} parenthetical name(s): ${bad_samples.paren.join(", ")}`);
      if (stats.bad_dates > 0)
        errors.push(`[BAD_DATES] ${stats.bad_dates} invalid or unsorted historical_names date(s): ${bad_samples.dates.join(", ")}`);
      if (stats.collisions > 0)
        errors.push(`[COLLISIONS] ${stats.collisions} coordinate/stem duplicate collision(s) <= 1,5 km: ${bad_samples.collisions.join(", ")}`);
      if (stats.municipal_leaks > 0) {
        let msg = `[MUNICIPAL_DECOMP] ${stats.municipal_leaks} intra-municipal district/arrondissement/borough record(s): ${bad_samples.municipal.join(", ")}`;
        if (project_key) errors.push(msg);
        else warnings.push(msg);
      }
      if (stats.foreign_script_spam > 0)
        warnings.push(`[FOREIGN_SCRIPT] ${stats.foreign_script_spam} foreign-script alias(es) in Latin-only countries.`);

      // Optional separate toponymy_auditor sign-off check
      if (opts.require_auditor_signoff) {
        let signoff_p = opts.signoff_path ? path.resolve(opts.signoff_path) :
          path.join(svea_root, "tests/toponymy_batches", project_key.toLowerCase() || "all_projects", "auditor_signoff.json");
        if (!fs.existsSync(signoff_p)) {
          errors.push(`[AUDITOR_SIGNOFF] Missing separate toponymy_auditor sign-off: ${signoff_p}`);
        } else {
          let so = JSON.parse(fs.readFileSync(signoff_p, "utf8"));
          if (so.approved !== true || Number(so.errors_remaining || 0) !== 0)
            errors.push(`[AUDITOR_SIGNOFF] toponymy_auditor rejected or left ${so.errors_remaining} unresolved historical error(s).`);
        }
      }

      //Return statement
      return { errors: errors, stats: stats, success: errors.length === 0, warnings: warnings };
    },

    /**
     * Parses CLI arguments.
     * @alias city_metadata_auditor.parseCliArgs
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
        dataset: "stadester_2.0",
        dataview_root: "",
        json: false,
        project: "",
        require_auditor_signoff: false,
        signoff_path: "",
        svea_root: ""
      };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok.startsWith("--project=")) out.project = tok.slice(10).trim().toUpperCase();
        else if (tok === "--project" && i + 1 < argv.length) out.project = argv[++i].trim().toUpperCase();
        else if (tok.startsWith("--dataset=")) out.dataset = tok.slice(10).trim();
        else if (tok.startsWith("--dataview-root=")) out.dataview_root = tok.slice(16).trim();
        else if (tok.startsWith("--svea-root=")) out.svea_root = tok.slice(12).trim();
        else if (tok.startsWith("--signoff-path=")) out.signoff_path = tok.slice(15).trim();
        else if (tok === "--require-auditor-signoff") out.require_auditor_signoff = true;
        else if (tok === "--json") out.json = true;
      }

      //Return statement
      return out;
    }
  };

  if (require.main === module) {
    let cli = city_metadata_auditor.parseCliArgs(process.argv.slice(2));
    let res = city_metadata_auditor.auditMetadata(cli);
    if (cli.json) {
      console.log(JSON.stringify(res, null, 2));
    } else {
      for (let i = 0; i < Math.min(30, res.warnings.length); i++)
        console.log(`[WARN] ${res.warnings[i]}`);
      for (let i = 0; i < Math.min(40, res.errors.length); i++)
        console.error(`[FAIL] ${res.errors[i]}`);
      console.log(`[audit_city_metadata] ${cli.project || "ALL"}: ${res.stats.records_checked || 0} record(s), ${res.errors.length} error(s), ${res.warnings.length} warning(s).`);
    }
    process.exit(res.success ? 0 : 1);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { city_metadata_auditor: city_metadata_auditor };
  }
}
