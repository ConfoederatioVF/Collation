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
    NON_LATIN_CANONICAL_RE: /(?:[\u0370-\u03B7\u03B9-\u03FF]|[\u0370-\u03FF]{2,}|[\u0400-\u052F\u0530-\u058F\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\u0900-\u0DFF\u0E00-\u10FF\u1200-\u137F\u1780-\u17FF\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uAC00-\uD7AF])/,
    PAREN_RE: /\([^)]*\)/,

    /**
     * Audits partitioned `city_metadata/` (or legacy `city_metadata.json`) for structural integrity,
     * unified capital-city naming, spatial bbox validity, Latin canonical transliteration, zero
     * case-insensitive `.other_names` duplicates, zero collisions, zero intra-municipal district leaks,
     * and optional 2-pass toponymy sign-off (`pass1/auditor_signoff.json` + `pass2/pass2_whg_geohack_report.json`).
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
      let state_capitals_obj = this.loadStateCapitalsMap(dataview_root);
      let states_map = this.loadStatesMap(dataview_root);
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
        ancient_name_persistence: 0,
        apostrophe_hacek: 0,
        backtick_or_mojibake: 0,
        bad_dates: 0,
        capitals_checked: capitals_records.length,
        capitals_missing_name: 0,
        collisions: 0,
        duplicate_other_names: 0,
        english_or_ascii_exonym: 0,
        excel_errors: 0,
        foreign_script_spam: 0,
        gis_or_arch_junk: 0,
        html_entities: 0,
        inverted_articles: 0,
        multi_comma_addr: 0,
        municipal_leaks: 0,
        non_latin_canonical: 0,
        out_of_bbox_capitals: 0,
        parenthetical_names: 0,
        records_checked: loaded_records.length,
        semicolon_spam: 0,
        split_capitals: 0,
        suburb_hijacks: 0
      };

      let bad_samples = {
        ancient_persist: [],
        apost_hacek: [],
        backtick: [],
        collisions: [],
        dates: [],
        dup_other: [],
        exonym: [],
        excel: [],
        gis_junk: [],
        html_ent: [],
        inverted: [],
        multi_comma: [],
        municipal: [],
        non_latin: [],
        out_of_bbox: [],
        paren: [],
        semi: [],
        split_cap: [],
        suburb_hijack: []
      };

      let excel_re = /#(?:N\/A|REF!|VALUE!|DIV\/0!|NAME\?|NUM!|NULL!)\b/i;
      let html_ent_re = /&nbsp;|&apos;|&#39;|andapos;/i;
      let apost_hacek_re = /(?:^|[\s\-])['\u2019]{1,2}(?:[CcSsZz][aeoiuyhklmnprstvčšž]|s['\u2019]c)|[a-z]['\u2019]{1,2}[csz]['\u2019]{1,2}[csz]|[a-z]['\u2019]{1,2}[sS][čšž]|['\u2019]{1,2}[CcSsZz][čšž]|''[CcSsZz]|`'[CcSsZz]/;
      let english_ascii_exonym_re = /^(?:Vienna|Munich|Muenchen|Munchen|Nuremberg|Cologne|Dusseldorf|Wurzburg|Luneburg|Lunen|Grunberg|Butow|Koslin|Prague|Warsaw|Cracow|Florence|Naples|Copenhagen|Gorzow Wielkopolski|Poznan|Wroclaw|Miedzyrzecz|Wrzesnia|Srem|Nowy Tomysl|Miedzychod|Ostrow Wielkopolski|Bytow|Zielona Gora)$/i;
      let gis_arch_junk_re = /_wfl|_none|proyecto_|cmn_|SitioNN_Fase_|\b(?:petroglifos|petroglyph|parcela\s+[a-z0-9]|dhibi|rockshelter|borough high street|royal opera house|transport museum|boulevard périphérique)\b|\\|\s\+\s|\b(?:a\.d\.|b\.Pr\.|i\.d\.OPf\.|v\.d\.|s\.r\.o\.|uniwersytet)\b|^(?:universitäts- und hansestadt|hansestadt|kreisfreie stadt|landeshauptstadt|bergstadt|stadt\s)/i;
      let suburb_hijack_re = /-l[eè]s-|\b\d{2}\b|weststadt|oststadt|nordstadt|südstadt/i;
      let ancient_persist_re = /^(?:Bagdata|Birtha|Seleucia on the Tigris|Ctesiphon|Pataliputra)$/i;

      let cap_grid = new Map();
      let grid = new Map();
      for (let i = 0; i < loaded_records.length; i++) {
        let rec = loaded_records[i].rec;
        let shard_fn = loaded_records[i].shard;
        if (!rec || typeof rec !== "object") continue;

        let hn = this.extractHistoricalEntries(rec);
        let nm = this.extractDisplayName(rec, hn);
        let coords = Array.isArray(rec.coords) ? rec.coords : [];
        let lng = Number(coords[0]);
        let lat = Number(coords[1]);
        let is_cap_shard = shard_fn === "00_capitals.json";

        if (is_cap_shard) {
          let has_cap_data = Boolean(
            (rec.capital && typeof rec.capital === "object" && Object.keys(rec.capital).length > 0) ||
            (Array.isArray(rec.capital_records) && rec.capital_records.length > 0)
          );
          if (!nm || hn.length === 0 || !has_cap_data)
            stats.capitals_missing_name++;

          // Cross-continent out-of-bbox capital validation
          if (Number.isFinite(lat) && Number.isFinite(lng) && states_map.size > 0) {
            let cap_sids = this.collectCapitalStateIds(rec);
            for (let x = 0; x < cap_sids.length; x++) {
              if (!this.isValidCapitalBinding(lng, lat, rec.country || "", cap_sids[x], states_map, state_capitals_obj)) {
                stats.out_of_bbox_capitals++;
                if (bad_samples.out_of_bbox.length < 5)
                  bad_samples.out_of_bbox.push(`${nm}(${rec.country || "?"})->state:${cap_sids[x]}`);
              }
            }
          }
        }

        if (!nm || nm.includes("`") || nm.includes("?") || nm.includes("\uFFFD") || nm === "0" || /^0[-_a-zA-Z\s]/.test(nm) || nm === "Unknown") {
          stats.backtick_or_mojibake++;
          if (bad_samples.backtick.length < 5) bad_samples.backtick.push(`${shard_fn}:${nm}`);
        }
        let all_str_checks = [nm].concat(hn.map(function (arg0_h) { return String(arg0_h && arg0_h.name || ""); })).concat(Array.isArray(rec.other_names) ? rec.other_names.map(String) : []);
        for (let sc_i = 0; sc_i < all_str_checks.length; sc_i++) {
          let sv = String(all_str_checks[sc_i] || "").trim();
          if (!sv) continue;
          if (excel_re.test(sv)) {
            stats.excel_errors++;
            if (bad_samples.excel.length < 5) bad_samples.excel.push(`${shard_fn}:${nm}=>${sv}`);
          }
          if (html_ent_re.test(sv)) {
            stats.html_entities++;
            if (bad_samples.html_ent.length < 5) bad_samples.html_ent.push(`${shard_fn}:${nm}=>${sv}`);
          }
          if (sv.includes(";")) {
            stats.semicolon_spam++;
            if (bad_samples.semi.length < 5) bad_samples.semi.push(`${shard_fn}:${nm}=>${sv}`);
          }
          let is_tib = (rec.country === "China" && /'(?:brog|brong|char)/i.test(sv));
          if (apost_hacek_re.test(sv) && !/^'s-/.test(sv) && !is_tib) {
            stats.apostrophe_hacek++;
            if (bad_samples.apost_hacek.length < 5) bad_samples.apost_hacek.push(`${shard_fn}:${nm}=>${sv}`);
          }
        }
        if (nm && this.NON_LATIN_CANONICAL_RE.test(nm)) {
          stats.non_latin_canonical++;
          if (bad_samples.non_latin.length < 5) bad_samples.non_latin.push(`${shard_fn}:${nm}`);
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
        let us_ca_au_re = /^(?:United States|United States of America|Canada|Australia|Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming)$/i;
        let rec_ctry = String(rec.country || "").trim();
        let is_exonym_defect = english_ascii_exonym_re.test(nm) && !us_ca_au_re.test(rec_ctry) &&
          shard_fn !== "01_centaur.json" && shard_fn !== "13_austral.json" &&
          !(/^Cologne$/i.test(nm) && !/Germany/i.test(rec_ctry)) &&
          !(/^Srem$/i.test(nm) && !/Poland|Germany/i.test(rec_ctry)) &&
          !(/^Munich$/i.test(nm) && !/Germany|Austria|Switzerland/i.test(rec_ctry));
        if (is_exonym_defect) {
          stats.english_or_ascii_exonym++;
          if (bad_samples.exonym.length < 5) bad_samples.exonym.push(`${shard_fn}:${nm}(${rec.country || "?"})`);
        }
        if (gis_arch_junk_re.test(nm)) {
          stats.gis_or_arch_junk++;
          if (bad_samples.gis_junk.length < 5) bad_samples.gis_junk.push(`${shard_fn}:${nm}`);
        }
        if (is_cap_shard) {
          for (let h_s = 0; h_s < hn.length; h_s++) {
            let h_snm = String(hn[h_s].name || "");
            if (suburb_hijack_re.test(h_snm)) {
              stats.suburb_hijacks++;
              if (bad_samples.suburb_hijack.length < 5) bad_samples.suburb_hijack.push(`${nm}=>${h_snm}`);
              break;
            }
          }
        }
        for (let h_a = 0; h_a < hn.length; h_a++) {
          let h_yr = Number(String(hn[h_a].date || "").split(".")[0]);
          let h_anm = String(hn[h_a].name || "");
          if (h_yr >= 800 && ancient_persist_re.test(h_anm)) {
            stats.ancient_name_persistence++;
            if (bad_samples.ancient_persist.length < 5) bad_samples.ancient_persist.push(`${nm}:${hn[h_a].date}=${h_anm}`);
          }
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

        // Check historical_names / compact names dates, clean strings, and Latin script
        let canonical_ci_set = new Set();
        if (nm) canonical_ci_set.add(nm.toLowerCase());
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
          let hname = String(h.name || "").trim();
          if (hname) canonical_ci_set.add(hname.toLowerCase());
          if (hname.includes("`") || hname.includes("?") || hname.includes("\uFFFD")) {
            stats.backtick_or_mojibake++;
            if (bad_samples.backtick.length < 5) bad_samples.backtick.push(`${nm}->${hname}`);
          }
          if (hname && this.NON_LATIN_CANONICAL_RE.test(hname)) {
            stats.non_latin_canonical++;
            if (bad_samples.non_latin.length < 5) bad_samples.non_latin.push(`${nm}->${hname}`);
          }
          if (this.PAREN_RE.test(hname)) {
            stats.parenthetical_names++;
            if (bad_samples.paren.length < 5) bad_samples.paren.push(`${nm}->${hname}`);
          }
        }

        // Case-insensitive duplicate check in other_names (including repeats of name or historical_names)
        if (Array.isArray(rec.other_names) && rec.other_names.length > 0) {
          let seen_other_ci = new Set(canonical_ci_set);
          for (let x = 0; x < rec.other_names.length; x++) {
            let alias_str = String(rec.other_names[x] || "").trim();
            let alias_low = alias_str.toLowerCase();
            if (!alias_low || seen_other_ci.has(alias_low)) {
              stats.duplicate_other_names++;
              if (bad_samples.dup_other.length < 5)
                bad_samples.dup_other.push(`${shard_fn}:${nm}[${alias_str}]`);
            } else {
              seen_other_ci.add(alias_low);
            }
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

        // Spatial collision check (<= 1,5 km same-stem or <= 0,15 km exact duplicate)
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

          // Split same-municipality capital duplicate check inside 00_capitals.json (<= 3,0 km)
          if (is_cap_shard) {
            let cap_sids = new Set(this.collectCapitalStateIds(rec));
            let alias_stems = this.collectAllStems(rec, hn);
            let cgx = Math.round(lat*10);
            let cgy = Math.round(lng*10);
            for (let dx = -1; dx <= 1; dx++) {
              for (let dy = -1; dy <= 1; dy++) {
                let cb = cap_grid.get(`${cgx + dx},${cgy + dy}`);
                if (!cb) continue;
                for (let z = 0; z < cb.length; z++) {
                  let ot = cb[z];
                  let d_km = viscount_audit_utils.haversineKm(lat, lng, ot.lat, ot.lng);
                  if (d_km > 3.0) continue;
                  let is_same_cap = d_km <= 0.35;
                  if (!is_same_cap && stem && ot.stem && (stem === ot.stem || viscount_entity_audit.areEquivalentExonyms(nm, ot.name, profiles)))
                    is_same_cap = true;
                  if (!is_same_cap) {
                    cap_sids.forEach(function (arg0_sid) {
                      if (ot.cap_sids.has(arg0_sid)) is_same_cap = true;
                    });
                  }
                  if (!is_same_cap) {
                    alias_stems.forEach(function (arg0_st) {
                      if (ot.alias_stems.has(arg0_st)) is_same_cap = true;
                    });
                  }
                  if (is_same_cap) {
                    stats.split_capitals++;
                    if (bad_samples.split_cap.length < 5)
                      bad_samples.split_cap.push(`${nm}<->${ot.name} (${d_km.toFixed(2)} km)`);
                  }
                }
              }
            }
            let cgk = `${cgx},${cgy}`;
            if (!cap_grid.has(cgk)) cap_grid.set(cgk, []);
            cap_grid.get(cgk).push({ alias_stems: alias_stems, cap_sids: cap_sids, lat: lat, lng: lng, name: nm, stem: stem });
          }
        }
      }

      if (stats.capitals_missing_name > 0)
        errors.push(`[CAPITALS] ${stats.capitals_missing_name} capital record(s) in 00_capitals.json lack clean name, historical_names or capital_records.`);
      if (stats.out_of_bbox_capitals > 0)
        errors.push(`[CAPITAL_BBOX] ${stats.out_of_bbox_capitals} cross-continent out-of-bbox capital binding(s) in 00_capitals.json: ${bad_samples.out_of_bbox.join(", ")}`);
      if (stats.split_capitals > 0)
        errors.push(`[SPLIT_CAPITALS] ${stats.split_capitals} split same-municipality capital duplicate(s) <= 3,0 km in 00_capitals.json: ${bad_samples.split_cap.join(", ")}`);
      if (stats.duplicate_other_names > 0)
        errors.push(`[DUP_OTHER_NAMES] ${stats.duplicate_other_names} case-insensitive duplicate or redundant .other_names entry/entries: ${bad_samples.dup_other.join(", ")}`);
      if (stats.non_latin_canonical > 0)
        errors.push(`[NON_LATIN_CANONICAL] ${stats.non_latin_canonical} non-Latin glyph(s) in canonical .name/.historical_names: ${bad_samples.non_latin.join(", ")}`);
      if (stats.backtick_or_mojibake > 0)
        errors.push(`[ENCODING] ${stats.backtick_or_mojibake} backtick/mojibake/placeholder name(s): ${bad_samples.backtick.join(", ")}`);
      if (stats.excel_errors > 0)
        errors.push(`[EXCEL_ERROR] ${stats.excel_errors} Excel error token(s): ${bad_samples.excel.join(", ")}`);
      if (stats.html_entities > 0)
        errors.push(`[HTML_ENTITY] ${stats.html_entities} unescaped HTML/XML entity name(s): ${bad_samples.html_ent.join(", ")}`);
      if (stats.apostrophe_hacek > 0)
        errors.push(`[APOSTROPHE_HACEK] ${stats.apostrophe_hacek} apostrophe-hacek corruption(s): ${bad_samples.apost_hacek.join(", ")}`);
      if (stats.semicolon_spam > 0)
        errors.push(`[SEMICOLON_SPAM] ${stats.semicolon_spam} semicolon-delimited spam/merged name(s): ${bad_samples.semi.join(", ")}`);
      if (stats.inverted_articles > 0)
        errors.push(`[INVERTED_ARTICLE] ${stats.inverted_articles} comma-inverted article name(s): ${bad_samples.inverted.join(", ")}`);
      if (stats.multi_comma_addr > 0)
        errors.push(`[ADDRESS_JUNK] ${stats.multi_comma_addr} multi-comma street/postal address record(s): ${bad_samples.multi_comma.join(", ")}`);
      if (stats.parenthetical_names > 0)
        errors.push(`[PARENTHETICAL] ${stats.parenthetical_names} parenthetical name(s): ${bad_samples.paren.join(", ")}`);
      if (stats.bad_dates > 0)
        errors.push(`[BAD_DATES] ${stats.bad_dates} invalid or unsorted historical_names date(s): ${bad_samples.dates.join(", ")}`);
      if (stats.suburb_hijacks > 0)
        errors.push(`[SUBURB_HIJACK] ${stats.suburb_hijacks} suburb/quarter-hijacked capital timeline(s): ${bad_samples.suburb_hijack.join(", ")}`);
      if (stats.english_or_ascii_exonym > 0)
        errors.push(`[ENGLISH_EXONYM_OR_STRIPPED_DIACRITIC] ${stats.english_or_ascii_exonym} non-endonymic/stripped-ASCII name(s): ${bad_samples.exonym.join(", ")}`);
      if (stats.ancient_name_persistence > 0)
        errors.push(`[ANCIENT_NAME_PERSISTENCE] ${stats.ancient_name_persistence} ancient name(s) persisting >= 800 AD: ${bad_samples.ancient_persist.join(", ")}`);
      if (stats.gis_or_arch_junk > 0)
        errors.push(`[GIS_OR_ARCH_JUNK] ${stats.gis_or_arch_junk} GIS/arch/title/abbreviation junk name(s): ${bad_samples.gis_junk.join(", ")}`);
      if (stats.collisions > 0)
        errors.push(`[COLLISIONS] ${stats.collisions} coordinate/stem duplicate collision(s) <= 1,5 km: ${bad_samples.collisions.join(", ")}`);
      if (stats.municipal_leaks > 0) {
        let msg = `[MUNICIPAL_DECOMP] ${stats.municipal_leaks} intra-municipal district/arrondissement/borough record(s): ${bad_samples.municipal.join(", ")}`;
        if (project_key) errors.push(msg);
        else warnings.push(msg);
      }
      if (stats.foreign_script_spam > 0)
        warnings.push(`[FOREIGN_SCRIPT] ${stats.foreign_script_spam} foreign-script alias(es) in Latin-only countries.`);

      // Optional 2-pass toponymy sign-off check (Pass 1 auditor + Pass 2 deterministic WHG/GeoHack report)
      if (opts.require_auditor_signoff) {
        let batch_root = path.join(svea_root, "tests/toponymy_batches", project_key.toLowerCase() || "all_projects");
        let pass1_signoff = path.join(batch_root, "pass1/auditor_signoff.json");
        let legacy_signoff = path.join(batch_root, "auditor_signoff.json");
        let signoff_p = opts.signoff_path ? path.resolve(opts.signoff_path) :
          (fs.existsSync(pass1_signoff) ? pass1_signoff : legacy_signoff);

        if (!fs.existsSync(signoff_p)) {
          errors.push(`[AUDITOR_SIGNOFF] Missing separate Pass-1 toponymy_auditor sign-off: ${signoff_p}`);
        } else {
          let so = JSON.parse(fs.readFileSync(signoff_p, "utf8"));
          if (so.approved !== true || Number(so.errors_remaining || 0) !== 0)
            errors.push(`[AUDITOR_SIGNOFF] Pass-1 toponymy_auditor rejected or left ${so.errors_remaining} unresolved historical error(s).`);
          if (so.max_concurrency !== undefined && Number(so.max_concurrency) > 24)
            errors.push(`[AUDITOR_SIGNOFF] Pass-1 swarm exceeded n <= 24 concurrency cap (${so.max_concurrency}).`);
        }

        let pass2_residuals = path.join(batch_root, "pass2/residuals.json");
        if (fs.existsSync(pass2_residuals)) {
          let pass2_report = path.join(batch_root, "pass2/pass2_whg_geohack_report.json");
          if (!fs.existsSync(pass2_report)) {
            errors.push(`[PASS2_REPORT] Pass-2 residuals exist without deterministic WHG/GeoHack report: ${pass2_report}`);
          } else {
            let rep = JSON.parse(fs.readFileSync(pass2_report, "utf8"));
            if (Number(rep.llm_agents_used || 0) !== 0)
              errors.push(`[PASS2_REPORT] Pass-2 report logged non-zero LLM agents (${rep.llm_agents_used}); Pass 2 must use 0 LLM agents.`);
          }
        }
      }

      //Return statement
      return { errors: errors, stats: stats, success: errors.length === 0, warnings: warnings };
    },

    /**
     * Collects all normalised entity stems across a record's canonical name, historical timeline, and aliases.
     * @alias city_metadata_auditor.collectAllStems
     *
     * @param {Object} arg0_rec
     * @param {Array<{ date: string, name: string }>} arg1_hist_entries
     *
     * @returns {Set<string>}
     */
    collectAllStems (arg0_rec, arg1_hist_entries) {
      //Convert from parameters
      let hn = Array.isArray(arg1_hist_entries) ? arg1_hist_entries : [];
      let rec = (arg0_rec && typeof arg0_rec === "object") ? arg0_rec : {};

      //Declare local instance variables
      let stems = new Set();

      //Function body
      let add_stem = function (arg0_str) {
        let st = viscount_entity_audit.normaliseEntityStem(arg0_str);
        if (st && st.length >= 3) stems.add(st);
      };
      add_stem(rec.name);
      for (let i = 0; i < hn.length; i++) add_stem(hn[i].name);
      if (Array.isArray(rec.other_names)) {
        for (let i = 0; i < rec.other_names.length; i++) add_stem(rec.other_names[i]);
      }

      //Return statement
      return stems;
    },

    /**
     * Collects all distinct state_id keys bound to a capital record (`rec.capital` or `rec.capital_records`).
     * @alias city_metadata_auditor.collectCapitalStateIds
     *
     * @param {Object} arg0_rec
     *
     * @returns {Array<string>}
     */
    collectCapitalStateIds (arg0_rec) {
      //Convert from parameters
      let rec = (arg0_rec && typeof arg0_rec === "object") ? arg0_rec : {};

      //Declare local instance variables
      let sids = new Set();

      //Function body
      if (rec.capital && typeof rec.capital === "object") {
        let vals = Object.values(rec.capital);
        for (let i = 0; i < vals.length; i++) {
          if (vals[i] !== null && vals[i] !== undefined) sids.add(String(vals[i]));
        }
      }
      if (Array.isArray(rec.capital_records)) {
        for (let i = 0; i < rec.capital_records.length; i++) {
          let cr = rec.capital_records[i];
          if (cr && cr.state_id !== undefined && cr.state_id !== null)
            sids.add(String(cr.state_id));
        }
      }

      //Return statement
      return Array.from(sids);
    },

    /**
     * Resolves display name from either `rec.name` or the latest chronological entry of compact `rec.names`.
     * @alias city_metadata_auditor.extractDisplayName
     *
     * @param {Object} arg0_rec
     * @param {Array<{ date: string, name: string }>} arg1_hist_entries
     *
     * @returns {string}
     */
    extractDisplayName (arg0_rec, arg1_hist_entries) {
      //Convert from parameters
      let hn = Array.isArray(arg1_hist_entries) ? arg1_hist_entries : [];
      let rec = (arg0_rec && typeof arg0_rec === "object") ? arg0_rec : {};

      //Guard clauses
      if (rec.name && String(rec.name).trim())
        return String(rec.name).trim();
      if (hn.length > 0 && hn[hn.length - 1] && hn[hn.length - 1].name)
        return String(hn[hn.length - 1].name).trim();

      //Return statement
      return "";
    },

    /**
     * Extracts historical timeline entries from EITHER Dataview `historical_names: [{ date, name }]`
     * OR compact `names: { "yyyy.m.d": "Name" }` map.
     * @alias city_metadata_auditor.extractHistoricalEntries
     *
     * @param {Object} arg0_rec
     *
     * @returns {Array<{ date: string, name: string }>}
     */
    extractHistoricalEntries (arg0_rec) {
      //Convert from parameters
      let rec = (arg0_rec && typeof arg0_rec === "object") ? arg0_rec : {};

      //Guard clauses
      if (Array.isArray(rec.historical_names))
        return rec.historical_names;

      //Function body
      if (rec.names && typeof rec.names === "object" && !Array.isArray(rec.names)) {
        let out = [];
        let keys = Object.keys(rec.names);
        for (let i = 0; i < keys.length; i++)
          out.push({ date: String(keys[i]), name: String(rec.names[keys[i]] || "") });
        out.sort(function (arg0_a, arg1_b) {
          let pa = String(arg0_a.date || "").split(".").map(Number);
          let pb = String(arg1_b.date || "").split(".").map(Number);
          if ((pa[0] || 0) !== (pb[0] || 0)) return (pa[0] || 0) - (pb[0] || 0);
          if ((pa[1] || 1) !== (pb[1] || 1)) return (pa[1] || 1) - (pb[1] || 1);
          return (pa[2] || 1) - (pb[2] || 1);
        });
        return out;
      }

      //Return statement
      return [];
    },

    /**
     * Validates that a `[lng, lat]` coordinate lies inside a state's `states.json` bbox (3 deg margin)
     * or matches an explicit country-consistent entry in `state_capitals.json`.
     * @alias city_metadata_auditor.isValidCapitalBinding
     *
     * @param {number} arg0_lng
     * @param {number} arg1_lat
     * @param {string} arg2_country
     * @param {string|number} arg3_state_id
     * @param {Map<string, Object>} arg4_states_map
     * @param {Object} arg5_state_capitals_obj
     *
     * @returns {boolean}
     */
    isValidCapitalBinding (arg0_lng, arg1_lat, arg2_country, arg3_state_id, arg4_states_map, arg5_state_capitals_obj) {
      //Convert from parameters
      let country_low = String(arg2_country || "").trim().toLowerCase();
      let lat = Number(arg1_lat);
      let lng = Number(arg0_lng);
      let sid_str = String(arg3_state_id);
      let state_capitals = arg5_state_capitals_obj || {};
      let states_map = arg4_states_map;

      //Function body
      let st = states_map ? states_map.get(sid_str) : null;
      if (!st || !Array.isArray(st.bbox) || st.bbox.length < 4)
        return true;

      let [x0, y0, x1, y1] = st.bbox;
      if (lng >= x0 - 3.0 && lng <= x1 + 3.0 && lat >= y0 - 3.0 && lat <= y1 + 3.0)
        return true;

      let sc = state_capitals[sid_str];
      if (sc && Array.isArray(sc.timeline) && country_low) {
        for (let i = 0; i < sc.timeline.length; i++) {
          let tk = String(sc.timeline[i].key || "").toLowerCase();
          if (tk && (tk.endsWith("-" + country_low) || tk.includes("-" + country_low + "-")))
            return true;
        }
      }

      //Return statement
      return false;
    },

    /**
     * Loads `data/stadester/state_capitals.json` from Dataview if present.
     * @alias city_metadata_auditor.loadStateCapitalsMap
     *
     * @param {string} arg0_dataview_root
     *
     * @returns {Object}
     */
    loadStateCapitalsMap (arg0_dataview_root) {
      //Convert from parameters
      let dataview_root = arg0_dataview_root;

      //Declare local instance variables
      let sc_path = path.join(dataview_root, "data/stadester/state_capitals.json");

      //Guard clauses
      if (!fs.existsSync(sc_path)) return {};

      //Function body
      try {
        return JSON.parse(fs.readFileSync(sc_path, "utf8"));
      } catch (e) {
        return {};
      }
    },

    /**
     * Loads `data/atlas/temp/states.json` into a Map keyed by string `state_id`.
     * @alias city_metadata_auditor.loadStatesMap
     *
     * @param {string} arg0_dataview_root
     *
     * @returns {Map<string, Object>}
     */
    loadStatesMap (arg0_dataview_root) {
      //Convert from parameters
      let dataview_root = arg0_dataview_root;

      //Declare local instance variables
      let out = new Map();
      let st_path = path.join(dataview_root, "data/atlas/temp/states.json");

      //Guard clauses
      if (!fs.existsSync(st_path)) return out;

      //Function body
      try {
        let arr = JSON.parse(fs.readFileSync(st_path, "utf8"));
        if (Array.isArray(arr)) {
          for (let i = 0; i < arr.length; i++) {
            if (arr[i] && arr[i].id !== undefined)
              out.set(String(arr[i].id), arr[i]);
          }
        }
      } catch (e) {}

      //Return statement
      return out;
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
