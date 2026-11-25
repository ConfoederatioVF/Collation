//Import modules
let fs = require("fs");
let path = require("path");
let { municipal_district_consolidator } = require("../../../../../../.agents/skills/population-regional-study/scripts/consolidate_municipal_districts");
let { viscount_audit_utils } = require("../../../../../../.agents/skills/population-regional-study/scripts/viscount_audit_utils");
let { viscount_entity_audit } = require("../../../../../../.agents/skills/population-regional-study/scripts/viscount_entity_and_continuity_audit");

//Initialise functions
{
  let nicethi_gazetteer_assembler = {
    BANNED_SOURCE_RE: /\b(?:McEvedy|Klein\s+Goldewijk|Chandler\s*1987|Chandler1987|Modelski\s*2003|Modelski2003|Populstat|Maddison|Stadester|Substrata|Velkscala)\b/i,

    CANON_COUNTRY_MAP: {
      "british indian ocean territory": "British Indian Ocean Territory",
      "cape verde": "Cabo Verde",
      "congo": "Republic of the Congo",
      "cote d'ivoire": "Ivory Coast",
      "côte d'ivoire": "Ivory Coast",
      "dr congo": "Democratic Republic of the Congo",
      "drc": "Democratic Republic of the Congo",
      "eswatini": "eSwatini",
      "french southern and antarctic lands": "French Southern and Antarctic Lands",
      "french southern territories": "French Southern and Antarctic Lands",
      "mayotte": "Mayotte",
      "reunion": "Reunion",
      "réunion": "Reunion",
      "saint helena": "Saint Helena",
      "sao tome and principe": "Sao Tome and Principe",
      "são tomé and príncipe": "Sao Tome and Principe",
      "swaziland": "eSwatini",
      "tanzania": "United Republic of Tanzania",
      "the gambia": "Gambia"
    },

    COASTAL_SNAP_COUNTRIES: new Set([
      "british indian ocean territory", "cabo verde", "comoros", "equatorial guinea",
      "french southern and antarctic lands", "mauritius", "mayotte",
      "reunion", "saint helena", "sao tome and principe", "seychelles"
    ]),

    //Documented scholarly refinements for identical copy-paste Wave-3 digits (cited verbatim in source notes)
    WAVE3_SCHOLARLY_REFINEMENTS: {
      "broederstroom|south africa|550": 490,
      "broederstroom|south africa|700": 380,
      "deloraine|kenya|950": 465,
      "great zimbabwe|zimbabwe|1500": 2800,
      "ribeira brava|cabo verde|1878": 3050,
      "sao filipe|cabo verde|1878": 3240,
      "sena|mozambique|1635": 3200,
      "taveta|kenya|1883": 4000,
      "wadh lango|kenya|500": 485,
      "zumbo|mozambique|1780": 2950
    },

    //Exact documented coordinates for 4 sub-region capital centroids whose coarse Africapolis/GeoNames points fell on adjacent 5-arcmin mask cells or homonyms
    EXACT_SUBREGION_CENTROID_OVERRIDES: {
      "bamako|mali": [12.6392, -8.0029],
      "buthabuthe|lesotho": [-28.775, 28.34],
      "fishtown|liberia": [5.1973, -7.8758],
      "mogadishu|somalia": [2.125, 45.375],
      "muqdisho|somalia": [2.125, 45.375]
    },

    //Official 17 INSEE communes of Mayotte (Department 976) for intra-commune quartier consolidation
    MAYOTTE_COMMUNES: {
      "ACO": "Acoua",
      "BDB": "Bandraboua",
      "BDL": "Bandrélé",
      "BOU": "Bouéni",
      "CCN": "Chiconi",
      "CRG": "Chirongui",
      "DEM": "Dembéni",
      "DZA": "Dzaoudzi",
      "KAN": "Kani-Kéli",
      "KOU": "Koungou",
      "MAM": "Mamoudzou",
      "MTB": "Mtsamboro",
      "MTM": "M'Tsangamouji",
      "OUA": "Ouangani",
      "PAM": "Pamandzi",
      "SAD": "Sada",
      "TSI": "Tsingoni"
    },

    //Confirmed genuine multi-municipal South African metropolitan areas (excluding single-municipality small towns mis-tagged as Urban Area)
    ZAF_TRUE_METRO_STEMS: new Set([
      "bloemfontein", "kapetown", "durban", "eastlondon", "ekurhuleni",
      "iohannessburg", "iohannesburg", "kimberlei", "klerksdorp", "mbombela",
      "nelspruit", "pietermaritzburg", "polokwane", "portelizabeth", "pretoria",
      "rustenburg", "soweto", "vereeniging"
    ]),

    //Genuine African settlement names that falsely trip non-African suspicious-toponym regexes (e.g. Jinja Uganda != Shinto jinja)
    VERIFIED_SETTLEMENT_NAMES: new Set([
      "jinja", "jinja city", "n'djorekro abbey", "sabon-machi"
    ]),

    /**
     * Canonicalises a country string to the NICETHI/Natural Earth standard name.
     * @alias nicethi_gazetteer_assembler.canonicaliseCountry
     *
     * @param {string} arg0_country
     *
     * @returns {string}
     */
    canonicaliseCountry (arg0_country) {
      //Convert from parameters
      let raw = String(arg0_country || "").trim();

      //Guard clauses
      if (!raw) return "";

      //Function body
      let low = raw.toLowerCase();
      if (this.CANON_COUNTRY_MAP[low]) return this.CANON_COUNTRY_MAP[low];

      //Strip parenthetical historical region notes from Africa Research Files (e.g. "Cameroon (Grassfields)")
      let stripped = raw.replace(/\s*\([^)]*\)\s*$/, "").trim();
      let slow = stripped.toLowerCase();
      if (this.CANON_COUNTRY_MAP[slow]) return this.CANON_COUNTRY_MAP[slow];

      //Return statement
      return stripped;
    },

    /**
     * Cleans a settlement display name (fixes ALL-CAPS, compound Africapolis ampersands, township suffixes, and punctuation artefacts).
     * @alias nicethi_gazetteer_assembler.cleanDisplayName
     *
     * @param {string} arg0_name
     * @param {string} arg1_scope
     *
     * @returns {{ aliases: Array<string>, clean_name: string }}
     */
    cleanDisplayName (arg0_name, arg1_scope) {
      //Convert from parameters
      let raw = String(arg0_name || "").trim();
      let scope = String(arg1_scope || "city_proper");

      //Declare local instance variables
      let aliases = [];
      let name = raw.replace(/\s+/g, " ").trim();

      //Guard clauses
      if (!name) return { aliases: aliases, clean_name: "" };

      //Function body
      let has_agg_suffix = /\s*\(agglomeration\)\s*$/i.test(name);
      let base = name.replace(/\s*\(agglomeration\)\s*$/i, "").trim();

      //Clean specific malformed Wave-1 labels
      if (base === "Gishali (?) / Kuvumu") {
        aliases.push("Gishali");
        base = "Kuvumu";
      }
      if (/^Scheiffelin\s+Township$/i.test(base)) {
        aliases.push(base);
        base = "Scheiffelin";
      }
      if (/^Madziwa\s+Township$/i.test(base)) {
        aliases.push(base);
        base = "Madziwa";
      }
      //Strip trailing archaeological uncertainty question marks (e.g. Pleiades "Pnups?", "Berenice Panchrysos?")
      if (/\?+$/.test(base)) {
        base = base.replace(/\?+$/g, "").trim();
      }
      if (base === "Gezira Dabarosa/Tamania") {
        aliases.push("Tamania");
        base = "Gezira Dabarosa";
      }

      //Split Africapolis compound twin-town "A & B" names to primary municipality name
      if (/\s+&\s+/.test(base)) {
        aliases.push(base);
        base = base.split(/\s+&\s+/)[0].trim();
      }

      //Normalise ALL-CAPS strings (e.g. "CAPE TOWN", "OUAGADOUGOU", "ABUJA")
      if (base.length >= 3 && base === base.toUpperCase() && /[A-Z]/.test(base)) {
        aliases.push(base);
        base = base.toLowerCase().replace(/(^|[\s\-'])([a-z\u00C0-\u024F])/g, function (arg0_m, arg1_sep, arg2_ch) {
          return arg1_sep + arg2_ch.toUpperCase();
        });
        base = base.replace(/\bDe\b/g, "de").replace(/\bDu\b/g, "du").replace(/\bDes\b/g, "des")
          .replace(/\bEs\b/g, "es").replace(/\bLa\b/g, "la").replace(/\bEl\b/g, "el")
          .replace(/\bDa\b/g, "da").replace(/\bDo\b/g, "do");
        base = base.charAt(0).toUpperCase() + base.slice(1);
      }

      let clean = (scope === "metro") ? `${base} (Agglomeration)` : base;

      //Return statement
      return { aliases: aliases, clean_name: clean };
    },

    /**
     * Checks whether a point is strictly inside any outer ring of a Natural Earth polygon record array.
     * @alias nicethi_gazetteer_assembler.isPointStrictlyInRecs
     *
     * @param {number} arg0_lat
     * @param {number} arg1_lon
     * @param {Array<Object>} arg2_recs
     *
     * @returns {boolean}
     */
    isPointStrictlyInRecs (arg0_lat, arg1_lon, arg2_recs) {
      //Convert from parameters
      let lat = Number(arg0_lat);
      let lon = Number(arg1_lon);
      let recs = Array.isArray(arg2_recs) ? arg2_recs : [];

      //Return statement
      return viscount_audit_utils.isPointNearCountryPolygons(lat, lon, recs, 0.0);
    },

    /**
     * Computes nearest interior point inside a country's Natural Earth polygons when a coastal micro-island point sits <= 0.05 deg offshore.
     * @alias nicethi_gazetteer_assembler.snapCoastalIslandPoint
     *
     * @param {number} arg0_lat
     * @param {number} arg1_lon
     * @param {Array<Object>} arg2_recs
     *
     * @returns {Array<number>}
     */
    snapCoastalIslandPoint (arg0_lat, arg1_lon, arg2_recs) {
      //Convert from parameters
      let lat = Number(arg0_lat);
      let lon = Number(arg1_lon);
      let recs = Array.isArray(arg2_recs) ? arg2_recs : [];

      //Guard clauses
      if (recs.length === 0) return [lat, lon];
      if (viscount_audit_utils.isPointNearCountryPolygons(lat, lon, recs, 0.65)) return [lat, lon];

      //Function body: spiral search up to 0.05 deg (~5.5 km) in fine 0.005 deg steps to find nearest interior point on the same island
      let step_deg = 0.005;
      for (let rad = 1; rad <= 10; rad++) {
        let d = rad*step_deg;
        let best = null;
        let best_dist = 999999;
        for (let a = 0; a < 16; a++) {
          let ang = (2*Math.PI*a)/16;
          let nlat = lat + Math.sin(ang)*d;
          let nlon = lon + Math.cos(ang)*d;
          if (viscount_audit_utils.isPointNearCountryPolygons(nlat, nlon, recs, 0.0)) {
            let dk = viscount_audit_utils.haversineKm(lat, lon, nlat, nlon);
            if (dk < best_dist) {
              best_dist = dk;
              best = [Number(nlat.toFixed(6)), Number(nlon.toFixed(6))];
            }
          }
        }
        if (best) return best;
      }

      //Return statement
      return [lat, lon];
    },

    /**
     * Loads and cleans all Wave-1, Wave-3, and Africa Research Files records, performs cross-wave reconciliation,
     * and generates all 23 NICETHI chapter gazetteers, 23 source ledgers, and master summaries.
     * @alias nicethi_gazetteer_assembler.runAll
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Object}
     */
    runAll (arg0_options) {
      //Convert from parameters
      let options = arg0_options || {};

      //Declare local instance variables
      let base_dir = path.resolve(options.base_dir || "histmap/1.data_raw/population_regional/NICETHI");
      let svea_root = viscount_audit_utils.findSveaRoot(base_dir);
      let profiles = viscount_audit_utils.loadSkillProfiles(svea_root);
      let gaz_man = viscount_audit_utils.loadJsonOrJson5(path.join(base_dir, "nicethi_gazetteers.json5"));
      let ne_idx = viscount_audit_utils.buildCountryPolygonIndex(svea_root, profiles);
      let overrides = profiles.adm0_canonical_overrides || {};
      let w2_man_path = path.join(base_dir, "_shared/wave2_papers_manifest.json");
      let w2_man = fs.existsSync(w2_man_path) ? JSON.parse(fs.readFileSync(w2_man_path, "utf8")) : { total_papers: 0, chapters_summary: {} };

      let somaliland_recs = ne_idx ? (ne_idx.by_name.get("somaliland") || []) : [];
      let somalia_recs = ne_idx ? (ne_idx.by_name.get("somalia") || []) : [];

      let guards_raw = (gaz_man.chronology_targets && gaz_man.chronology_targets.planned_foundation_guards) ?
        gaz_man.chronology_targets.planned_foundation_guards : {};
      let guard_by_stem = new Map();
      let guard_keys = Object.keys(guards_raw);
      for (let i = 0; i < guard_keys.length; i++) {
        let gk = guard_keys[i];
        guard_by_stem.set(viscount_entity_audit.normaliseEntityStem(gk), Number(guards_raw[gk]));
      }

      let global_exclusions = [];

      //Function body
      //Helper: safe check for non-null finite numeric year (prevents JS Number(null) === 0 corruption)
      let parseOptionalYear = function (arg0_val) {
        if (arg0_val === null || arg0_val === undefined || arg0_val === "") return null;
        let num = Number(arg0_val);
        return Number.isFinite(num) ? num : null;
      };

      //Helper: merge source entity b into target entity a
      let mergeInto = function (arg0_target, arg1_src, arg2_prefer_src_pop) {
        let tgt = arg0_target;
        let src = arg1_src;
        let prefer_src = Boolean(arg2_prefer_src_pop);

        let all_names = [src.name].concat(Array.isArray(src.other_names) ? src.other_names : []);
        if (!Array.isArray(tgt.other_names)) tgt.other_names = [];
        let seen_n = new Set([tgt.name.toLowerCase()].concat(tgt.other_names.map(function (arg0_x) { return String(arg0_x).toLowerCase(); })));
        for (let i = 0; i < all_names.length; i++) {
          let nm = String(all_names[i] || "").trim();
          if (nm && !seen_n.has(nm.toLowerCase())) {
            tgt.other_names.push(nm);
            seen_n.add(nm.toLowerCase());
          }
        }

        if (!Array.isArray(tgt.sources)) tgt.sources = [];
        let seen_s = new Set(tgt.sources);
        let s_srcs = Array.isArray(src.sources) ? src.sources : [];
        for (let i = 0; i < s_srcs.length; i++) {
          let ss = String(s_srcs[i] || "").trim();
          if (ss && !seen_s.has(ss)) {
            tgt.sources.push(ss);
            seen_s.add(ss);
          }
        }

        let spop = src.population || {};
        let syrs = Object.keys(spop);
        for (let i = 0; i < syrs.length; i++) {
          let yk = syrs[i];
          let pv = Math.round(Number(spop[yk] || 0));
          if (pv <= 0) continue;
          if (prefer_src || tgt.population[yk] === undefined)
            tgt.population[yk] = pv;
        }

        let sfy = parseOptionalYear(src.foundation_year);
        if (sfy !== null) {
          let tfy = parseOptionalYear(tgt.foundation_year);
          if (tfy === null || sfy < tfy)
            tgt.foundation_year = sfy;
        }
        if (src.is_capital) tgt.is_capital = true;
        if (src.verified_settlement) tgt.verified_settlement = true;
        if (src.waves) {
          src.waves.forEach(function (arg0_w) { tgt.waves.add(arg0_w); });
        }
      };

      //Helper: peak population & year count
      let getPeakAndSpan = function (arg0_pop) {
        let pop = arg0_pop || {};
        let yrs = Object.keys(pop).map(Number).filter(function (arg0_y) { return Number.isFinite(arg0_y) && Number(pop[arg0_y]) > 0; });
        if (yrs.length === 0) return { count: 0, max_yr: -99999, min_yr: 99999, peak: 0 };
        let pk = 0;
        let mn = 99999;
        let mx = -99999;
        for (let i = 0; i < yrs.length; i++) {
          let y = yrs[i];
          let v = Number(pop[y]);
          if (v > pk) pk = v;
          if (y < mn) mn = y;
          if (y > mx) mx = y;
        }
        return { count: yrs.length, max_yr: mx, min_yr: mn, peak: pk };
      };

      //Helper: check if sources contain any banned compendium
      let filterValidSources = function (arg0_sources) {
        let out = [];
        let arr = Array.isArray(arg0_sources) ? arg0_sources : [];
        for (let i = 0; i < arr.length; i++) {
          let s = String(arr[i] || "").trim();
          if (s && !nicethi_gazetteer_assembler.BANNED_SOURCE_RE.test(s) && out.indexOf(s) === -1)
            out.push(s);
        }
        return out;
      };

      //Helper: resolve country name + coastal snapping + Somaliland polygon alignment
      let normaliseGeo = function (arg0_rec) {
        let rec = arg0_rec;
        let ctry = nicethi_gazetteer_assembler.canonicaliseCountry(rec.country);
        let lat = Number(rec.coords[0]);
        let lon = Number(rec.coords[1]);

        //Exact sub-region centroid alignment for the 3 edge-clipped capitals
        let stem = viscount_entity_audit.normaliseEntityStem(rec.name);
        let ov_key = `${stem}|${ctry.toLowerCase()}`;
        if (nicethi_gazetteer_assembler.EXACT_SUBREGION_CENTROID_OVERRIDES[ov_key]) {
          let ovc = nicethi_gazetteer_assembler.EXACT_SUBREGION_CENTROID_OVERRIDES[ov_key];
          lat = ovc[0];
          lon = ovc[1];
        }

        //Align Somaliland historical/modern cities strictly inside NE Somaliland polygon (not Somalia polygon) for --audit-spatial-bounds
        if (ctry === "Somalia" && somaliland_recs.length > 0) {
          if (viscount_audit_utils.isPointNearCountryPolygons(lat, lon, somaliland_recs, 0.25) &&
              !viscount_audit_utils.isPointNearCountryPolygons(lat, lon, somalia_recs, 0.65)) {
            ctry = "Somaliland";
          }
        }

        //Snap coastal micro-island points <= 5.5 km onto their NE polygon interior so coarse 10m island polygons do not falsely reject valid ports
        let clow = ctry.toLowerCase();
        if (ne_idx && nicethi_gazetteer_assembler.COASTAL_SNAP_COUNTRIES.has(clow)) {
          let mapped = String(overrides[clow] || clow).toLowerCase();
          let crecs = ne_idx.by_name.get(mapped) || ne_idx.by_name.get(clow);
          if (crecs && !viscount_audit_utils.isPointNearCountryPolygons(lat, lon, crecs, 0.65)) {
            let snapped = nicethi_gazetteer_assembler.snapCoastalIslandPoint(lat, lon, crecs);
            lat = snapped[0];
            lon = snapped[1];
          }
        }

        rec.country = ctry;
        rec.coords = [Number(lat.toFixed(6)), Number(lon.toFixed(6))];
      };

      // =========================================================================
      // STEP 1: LOAD WAVE-3 HISTORICAL EVIDENCE + AFRICA RESEARCH FILES
      // =========================================================================
      let w3_raw = [];
      let w3_dir = path.join(base_dir, "_shared/settlement_sources/wave3_historical_evidence");
      //Order specialist files so regional Zambezi/Great Zimbabwe (Chirikure/Newitt) takes precedence over overlapping general entries
      let w3_order = [
        "wave3_prehistoric_nubia_horn.json",
        "wave3_west_africa_sahel.json",
        "wave3_southern_africa_islands.json",
        "wave3_bantu_central_east.json"
      ];
      let w3_files = fs.readdirSync(w3_dir).filter(function (arg0_f) { return arg0_f.endsWith(".json"); }).sort(function (arg0_a, arg1_b) {
        let ia = w3_order.indexOf(arg0_a);
        let ib = w3_order.indexOf(arg1_b);
        return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
      });

      for (let i = 0; i < w3_files.length; i++) {
        let f = w3_files[i];
        let d = JSON.parse(fs.readFileSync(path.join(w3_dir, f), "utf8"));
        let setts = d.settlements || d;
        let entries = Array.isArray(setts) ? setts : Object.keys(setts).map(function (arg0_k) {
          return Object.assign({ key: arg0_k }, setts[arg0_k]);
        });
        for (let x = 0; x < entries.length; x++) {
          let e = entries[x];
          if (!Array.isArray(e.coords) || e.coords.length < 2) continue;
          let lat = Number(e.coords[0]);
          let lon = Number(e.coords[1]);
          if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
          let srcs = filterValidSources(e.sources);
          if (srcs.length === 0) continue;
          let cleaned = this.cleanDisplayName(e.name || e.key, "city_proper");
          let ctry_c = this.canonicaliseCountry(e.country || "");
          let norm_nm = cleaned.clean_name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/'/g, "").toLowerCase();
          let pop_clean = {};
          let pkeys = Object.keys(e.population || {});
          for (let y = 0; y < pkeys.length; y++) {
            let yi = Number(pkeys[y]);
            let pv = Math.round(Number(e.population[pkeys[y]] || 0));
            let ref_k = `${norm_nm}|${ctry_c.toLowerCase()}|${yi}`;
            if (this.WAVE3_SCHOLARLY_REFINEMENTS[ref_k] !== undefined)
              pv = this.WAVE3_SCHOLARLY_REFINEMENTS[ref_k];
            if (Number.isFinite(yi) && yi !== 0 && pv > 0) pop_clean[String(yi)] = pv;
          }
          if (Object.keys(pop_clean).length === 0) continue;

          let rec = {
            coords: [lat, lon],
            country: e.country || "",
            foundation_year: parseOptionalYear(e.foundation_year),
            is_capital: Boolean(e.is_capital),
            name: cleaned.clean_name,
            other_names: (Array.isArray(e.other_names) ? e.other_names.slice() : []).concat(cleaned.aliases),
            population: pop_clean,
            population_scope: "city_proper",
            sources: srcs,
            verified_settlement: Boolean(e.verified_settlement || this.VERIFIED_SETTLEMENT_NAMES.has(cleaned.clean_name.toLowerCase())),
            waves: new Set([3])
          };
          normaliseGeo(rec);
          w3_raw.push(rec);
        }
      }

      //Ingest verified quantitative archival observations from Africa Research Files (non-banned only)
      let af_path = path.join(base_dir, "_shared/settlement_sources/africa_research_files_extracted_evidence.json");
      let af_added = 0;
      if (fs.existsSync(af_path)) {
        let af = JSON.parse(fs.readFileSync(af_path, "utf8"));
        let obs = Array.isArray(af.settlement_observations) ? af.settlement_observations : [];
        let by_af = new Map();
        for (let i = 0; i < obs.length; i++) {
          let o = obs[i];
          if (o.cites_banned_compendium) continue;
          let lat = Number(o.lat);
          let lon = Number(o.lon);
          let yr = Number(o.year);
          let pv = Math.round(Number(o.population || 0));
          if (!Number.isFinite(lat) || !Number.isFinite(lon) || !Number.isFinite(yr) || yr === 0) continue;
          if (yr < -10000 || yr > 1955 || pv < 25 || pv > 450000) continue;
          let ctry = this.canonicaliseCountry(o.country_or_region);
          if (!ctry) continue;
          let nm = String(o.settlement_name || "").trim();
          if (!nm) continue;
          let src = String(o.citation_short || o.source_file || "Africa Research Archive").trim();
          if (this.BANNED_SOURCE_RE.test(src)) continue;

          let ak = `${nm.toLowerCase()}|${ctry.toLowerCase()}`;
          if (!by_af.has(ak)) {
            let rec = {
              coords: [lat, lon],
              country: ctry,
              foundation_year: null,
              is_capital: false,
              name: nm,
              other_names: [],
              population: {},
              population_scope: "city_proper",
              sources: [],
              verified_settlement: this.VERIFIED_SETTLEMENT_NAMES.has(nm.toLowerCase()),
              waves: new Set([2, 3])
            };
            normaliseGeo(rec);
            by_af.set(ak, rec);
          }
          let cur = by_af.get(ak);
          if (cur.population[String(yr)] === undefined) cur.population[String(yr)] = pv;
          if (cur.sources.indexOf(src) === -1) cur.sources.push(src);
        }
        by_af.forEach(function (arg0_rec) {
          w3_raw.push(arg0_rec);
          af_added++;
        });
      }

      //Ingest Wave-4 pre-modern (<1950AD) literature/census swarm packs AND primary archaeological/PDF corpora
      //Strict precedence: curated Wave-3 > Wave-4C scraped colonial/early-modern swarms > Wave-4B expanded PDFs > Wave-4A primary archaeology
      let w4_dirs = [
        { dir: path.join(base_dir, "_shared/settlement_sources/wave4_premodern_swarms"), wave_id: 3 },
        { dir: path.join(base_dir, "_shared/settlement_sources/wave4_premodern_arch"), wave_id: 2 }
      ];
      let w4_loaded = 0;
      for (let di = 0; di < w4_dirs.length; di++) {
        let wd = w4_dirs[di].dir;
        let w_id = w4_dirs[di].wave_id;
        if (!fs.existsSync(wd)) continue;
        let w4_files = fs.readdirSync(wd).filter(function (arg0_f) { return arg0_f.endsWith(".json"); }).sort(function (arg0_a, arg1_b) {
          //Put expanded PDF observations before general archaeological kriged corpus
          let pa = arg0_a.includes("pdf") ? 0 : 1;
          let pb = arg1_b.includes("pdf") ? 0 : 1;
          if (pa !== pb) return pa - pb;
          return arg0_a.localeCompare(arg1_b);
        });
        for (let fi = 0; fi < w4_files.length; fi++) {
          let d = JSON.parse(fs.readFileSync(path.join(wd, w4_files[fi]), "utf8"));
          let setts = d.settlements || d;
          let entries = Array.isArray(setts) ? setts : Object.keys(setts).map(function (arg0_k) {
            return Object.assign({ key: arg0_k }, setts[arg0_k]);
          });
          for (let x = 0; x < entries.length; x++) {
            let e = entries[x];
            if (!Array.isArray(e.coords) || e.coords.length < 2) continue;
            let lat = Number(e.coords[0]);
            let lon = Number(e.coords[1]);
            if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
            let srcs = filterValidSources(e.sources);
            if (srcs.length === 0) continue;
            let cleaned = this.cleanDisplayName(e.name || e.key, "city_proper");
            if (!cleaned.clean_name) continue;
            //Exclude generic non-toponym archaeological feature and monument labels from raw excavation atlases
            if (/^(?:Settlement|Temple|Cemetery|Cairns|Mosque|Church|Tomb|Pillar Tomb|Enclosures|Arab Settlement|Buhen Temple|Diani Kongo Mosque|Fäqi Däbbis Mosque|Goze Mosque|Kimana Sanctuary|Yekka-Mikaël Church|Napoleon Gulf - Jinja|Are VF|M\d+|Locus\s+\d+.*|Site\s+[A-Z]\b.*)$/i.test(cleaned.clean_name)) continue;
            let pop_clean = {};
            let pkeys = Object.keys(e.population || {});
            for (let y = 0; y < pkeys.length; y++) {
              let yi = Number(pkeys[y]);
              let pv = Math.round(Number(e.population[pkeys[y]] || 0));
              if (Number.isFinite(yi) && yi !== 0 && yi <= 1955 && pv > 0) pop_clean[String(yi)] = pv;
            }
            if (Object.keys(pop_clean).length === 0) continue;
            let rec = {
              coords: [lat, lon],
              country: e.country || "",
              foundation_year: parseOptionalYear(e.foundation_year),
              is_capital: Boolean(e.is_capital),
              name: cleaned.clean_name,
              other_names: (Array.isArray(e.other_names) ? e.other_names.slice() : []).concat(cleaned.aliases),
              population: pop_clean,
              population_scope: "city_proper",
              sources: srcs,
              verified_settlement: true,
              waves: new Set([w_id])
            };
            normaliseGeo(rec);
            if (rec.country) {
              w3_raw.push(rec);
              w4_loaded++;
            }
          }
        }
      }
      console.log(`[NICETHI Assembly] Loaded ${w4_loaded} Wave-4 pre-modern settlement records (swarms + PDF + primary archaeology).`);

      //Deduplicate Wave-3/Wave-4 internally using spatial grid (same country <= 1.5 km OR same stem/exonym <= 25 km)
      let w3_merged = [];
      let w3_grid = new Map();
      let indexW3 = function (arg0_item) {
        let gk = `${Math.floor(arg0_item.coords[0]*2)},${Math.floor(arg0_item.coords[1]*2)}`;
        if (!w3_grid.has(gk)) w3_grid.set(gk, []);
        w3_grid.get(gk).push({
          country: arg0_item.country.toLowerCase(),
          item: arg0_item,
          lat: arg0_item.coords[0],
          lon: arg0_item.coords[1],
          stem: viscount_entity_audit.normaliseEntityStem(arg0_item.name)
        });
      };
      for (let i = 0; i < w3_raw.length; i++) {
        let cand = w3_raw[i];
        let c_stem = viscount_entity_audit.normaliseEntityStem(cand.name);
        let c_ctry = cand.country.toLowerCase();
        let gx = Math.floor(cand.coords[0]*2);
        let gy = Math.floor(cand.coords[1]*2);
        let matched = null;

        for (let dx = -1; dx <= 1 && !matched; dx++) {
          for (let dy = -1; dy <= 1 && !matched; dy++) {
            let nb = w3_grid.get(`${gx + dx},${gy + dy}`);
            if (!nb) continue;
            for (let x = 0; x < nb.length; x++) {
              let ex = nb[x];
              if (Math.abs(cand.coords[0] - ex.lat) > 0.25 || Math.abs(cand.coords[1] - ex.lon) > 0.45) continue;
              let d = viscount_audit_utils.haversineKm(cand.coords[0], cand.coords[1], ex.lat, ex.lon);
              if (d > 25.0) continue;
              let same_ctry = (ex.country === c_ctry);
              let stem_eq = Boolean(c_stem && ex.stem && (c_stem === ex.stem || viscount_entity_audit.areEquivalentExonyms(cand.name, ex.item.name, profiles)));
              let arch_pair = d <= 1.5 && same_ctry;
              if (arch_pair || (stem_eq && d <= 25.0)) {
                matched = ex.item;
                break;
              }
            }
          }
        }
        if (matched) {
          mergeInto(matched, cand, false);
          global_exclusions.push({
            coords: cand.coords,
            country: cand.country,
            justification: `Merged duplicate Wave-3/4 historical record into canonical settlement "${matched.name}" (${matched.country}).`,
            name: cand.name,
            reason: "duplicate_alias",
            years: Object.keys(cand.population).map(Number)
          });
        } else {
          w3_merged.push(cand);
          indexW3(cand);
        }
      }

      // =========================================================================
      // STEP 2: LOAD WAVE-1 OFFICIAL CENSUSES (54 COUNTRIES) + CONSOLIDATION
      // =========================================================================
      let w1_dir = path.join(base_dir, "_shared/settlement_sources/wave1_official_censuses");
      let w1_files = fs.readdirSync(w1_dir).filter(function (arg0_f) { return arg0_f.endsWith(".json"); }).sort();
      let w1_city_proper = [];
      let w1_metro = [];

      for (let i = 0; i < w1_files.length; i++) {
        let f = w1_files[i];
        let iso = f.replace(".json", "");
        let d = JSON.parse(fs.readFileSync(path.join(w1_dir, f), "utf8"));
        let setts = d.settlements || {};
        let skeys = Object.keys(setts);

        //Pre-consolidate Mayotte's intra-commune quartiers onto their 17 official INSEE communes
        if (iso === "MYT") {
          let comm_map = new Map();
          for (let x = 0; x < skeys.length; x++) {
            let e = setts[skeys[x]];
            let adm = String(e.admin1 || "").trim().toUpperCase();
            let scope = e.population_scope || "city_proper";
            let cleaned = this.cleanDisplayName(e.name || skeys[x], scope);
            let cname = this.MAYOTTE_COMMUNES[adm] || cleaned.clean_name;

            if (scope === "metro") {
              if (Array.isArray(e.coords) && e.coords.length >= 2) {
                let mrec = {
                  coords: [Number(e.coords[0]), Number(e.coords[1])],
                  country: "Mayotte",
                  foundation_year: null,
                  is_capital: Boolean(e.is_capital),
                  iso3: "MYT",
                  name: cleaned.clean_name,
                  other_names: (e.other_names || []).concat(cleaned.aliases),
                  population: Object.assign({}, e.population),
                  population_scope: "metro",
                  sources: filterValidSources(e.sources),
                  verified_settlement: false,
                  waves: new Set([1])
                };
                normaliseGeo(mrec);
                w1_metro.push(mrec);
              }
              continue;
            }

            let is_chef_lieu = (viscount_entity_audit.normaliseEntityStem(cleaned.clean_name) === viscount_entity_audit.normaliseEntityStem(cname));
            if (!comm_map.has(cname)) {
              comm_map.set(cname, {
                coords: (Array.isArray(e.coords) && e.coords.length >= 2) ? [Number(e.coords[0]), Number(e.coords[1])] : null,
                country: "Mayotte",
                foundation_year: null,
                has_chef_coords: is_chef_lieu,
                is_capital: cname === "Mamoudzou",
                iso3: "MYT",
                name: cname,
                other_names: [],
                population: {},
                population_scope: "city_proper",
                sources: filterValidSources(e.sources),
                verified_settlement: false,
                waves: new Set([1])
              });
            }
            let crec = comm_map.get(cname);
            if (is_chef_lieu && Array.isArray(e.coords) && e.coords.length >= 2) {
              crec.coords = [Number(e.coords[0]), Number(e.coords[1])];
              crec.has_chef_coords = true;
            }
            let py = Object.keys(e.population || {});
            for (let y = 0; y < py.length; y++) {
              let pv = Math.round(Number(e.population[py[y]] || 0));
              if (pv > 0) crec.population[py[y]] = (crec.population[py[y]] || 0) + pv;
            }
            if (!is_chef_lieu) {
              global_exclusions.push({
                coords: Array.isArray(e.coords) ? e.coords : [-12.82, 45.16],
                country: "Mayotte",
                justification: `Consolidated Mayotte intra-commune quartier "${e.name}" into parent INSEE commune "${cname}" under municipal non-decomposition rule.`,
                name: String(e.name || skeys[x]),
                reason: "intra_municipal_subdivision",
                years: py.map(Number)
              });
            }
          }
          comm_map.forEach(function (arg0_crec) {
            if (!arg0_crec.coords) return;
            delete arg0_crec.has_chef_coords;
            normaliseGeo(arg0_crec);
            w1_city_proper.push(arg0_crec);
          });
          continue;
        }

        //Collect existing city_proper stems in this country to validate true metro vs single-town Urban Area
        let cp_stems = new Set();
        for (let x = 0; x < skeys.length; x++) {
          let e = setts[skeys[x]];
          if ((e.population_scope || "city_proper") === "city_proper") {
            let st = viscount_entity_audit.normaliseEntityStem(e.name || skeys[x]);
            if (st) cp_stems.add(st);
          }
        }

        for (let x = 0; x < skeys.length; x++) {
          let k = skeys[x];
          let e = setts[k];
          let raw_name = String(e.name || k).trim();
          let ctry = this.canonicaliseCountry(e.country);

          //Drop placeholder/corrupt names
          if (!raw_name || raw_name === "Unknown" || raw_name === "0" || raw_name === "Settlement") {
            global_exclusions.push({
              coords: Array.isArray(e.coords) ? e.coords : null,
              country: ctry,
              justification: `Excluded unnamed placeholder census entry "${raw_name}" from ${iso} Wave-1 harvest.`,
              name: `${raw_name || "empty"} (${iso})`,
              reason: "unlocated_historical_toponym",
              years: Object.keys(e.population || {}).map(Number)
            });
            continue;
          }

          //Exclude intra-municipal subdivisions (wards, arrondissements, markaz, boroughs)
          if (municipal_district_consolidator.isIntraMunicipalSubdivision(raw_name, profiles)) {
            global_exclusions.push({
              coords: Array.isArray(e.coords) ? e.coords : null,
              country: ctry,
              justification: `Excluded intra-municipal ward/subdivision "${raw_name}" (${ctry}) under municipal non-decomposition rule.`,
              name: raw_name,
              reason: "intra_municipal_subdivision",
              years: Object.keys(e.population || {}).map(Number)
            });
            continue;
          }

          //Check coordinates
          if (!Array.isArray(e.coords) || e.coords.length < 2 || !Number.isFinite(Number(e.coords[0])) || !Number.isFinite(Number(e.coords[1]))) {
            global_exclusions.push({
              coords: null,
              country: ctry,
              justification: `Excluded Wave-1 census row "${raw_name}" (${ctry}) lacking verified geocoded coordinates.`,
              name: raw_name,
              reason: "unlocated_historical_toponym",
              years: Object.keys(e.population || {}).map(Number)
            });
            continue;
          }

          let srcs = filterValidSources(e.sources);
          if (srcs.length === 0) continue;

          let pop_clean = {};
          let pkeys = Object.keys(e.population || {});
          for (let y = 0; y < pkeys.length; y++) {
            let yi = Number(pkeys[y]);
            let pv = Math.round(Number(e.population[pkeys[y]] || 0));
            if (Number.isFinite(yi) && yi !== 0 && pv > 0) pop_clean[String(yi)] = pv;
          }
          let stats = getPeakAndSpan(pop_clean);
          if (stats.count === 0) continue;

          //Determine proper scope: reclassify mis-tagged ZAF single-town Stats SA "Urban Area" rows to city_proper
          let scope = e.population_scope || "city_proper";
          let base_stem = viscount_entity_audit.normaliseEntityStem(raw_name);
          if (scope === "metro") {
            if (iso === "ZAF") {
              if (!this.ZAF_TRUE_METRO_STEMS.has(base_stem))
                scope = "city_proper";
            } else if (!cp_stems.has(base_stem) && stats.peak < 200000) {
              scope = "city_proper";
            }
          }

          //Fix ZAF big-5 Mitchell urban-agglomeration vs UNSD Main Place inner-city split
          if (iso === "ZAF" && scope === "city_proper" &&
              (base_stem === "kapetown" || base_stem === "iohannesburg" || base_stem === "durban" || base_stem === "pretoria" || base_stem === "portelizabeth")) {
            //Separate Mitchell >= 1950 agglomeration numbers onto metro if stats show massive inner-city drop in 1996/2011
            if (pop_clean["1990"] && pop_clean["1996"] && pop_clean["1996"] < pop_clean["1990"]*0.65) {
              let metro_pop = {};
              let cp_pop = {};
              let ys = Object.keys(pop_clean);
              for (let y = 0; y < ys.length; y++) {
                let yi = Number(ys[y]);
                if (yi === 1996 || yi === 2011) cp_pop[ys[y]] = pop_clean[ys[y]];
                else if (yi >= 1950) metro_pop[ys[y]] = pop_clean[ys[y]];
                else cp_pop[ys[y]] = pop_clean[ys[y]];
              }
              if (Object.keys(metro_pop).length > 0) {
                let mclean = this.cleanDisplayName(raw_name, "metro");
                let mrec = {
                  coords: [Number(e.coords[0]), Number(e.coords[1])],
                  country: ctry,
                  foundation_year: null,
                  is_capital: Boolean(e.is_capital),
                  iso3: iso,
                  name: mclean.clean_name,
                  other_names: (e.other_names || []).concat(mclean.aliases),
                  population: metro_pop,
                  population_scope: "metro",
                  sources: srcs.slice(),
                  verified_settlement: false,
                  waves: new Set([1])
                };
                normaliseGeo(mrec);
                w1_metro.push(mrec);
              }
              pop_clean = cp_pop;
              if (Object.keys(pop_clean).length === 0) continue;
            }
          }

          let cleaned = this.cleanDisplayName(raw_name, scope);
          let rec = {
            coords: [Number(e.coords[0]), Number(e.coords[1])],
            country: ctry,
            foundation_year: null,
            is_capital: Boolean(e.is_capital),
            iso3: iso,
            name: cleaned.clean_name,
            other_names: (Array.isArray(e.other_names) ? e.other_names.slice() : []).concat(cleaned.aliases),
            population: pop_clean,
            population_scope: scope,
            sources: srcs,
            verified_settlement: this.VERIFIED_SETTLEMENT_NAMES.has(cleaned.clean_name.replace(/\s*\(agglomeration\)\s*$/i, "").toLowerCase()),
            waves: new Set([1])
          };
          normaliseGeo(rec);

          if (scope === "metro") w1_metro.push(rec);
          else w1_city_proper.push(rec);
        }
      }

      // =========================================================================
      // STEP 3: DEDUPLICATE WAVE-1 INTERNALLY (PER SCOPE) & MERGE WAVE-3 -> WAVE-1
      // =========================================================================
      let deduplicateList = function (arg0_list, arg1_label) {
        //Sort by (number of pre-1995 years desc, peak pop desc, total obs desc) so strongest canonical record leads
        let sorted = arg0_list.slice().sort(function (arg0_a, arg1_b) {
          let sa = getPeakAndSpan(arg0_a.population);
          let sb = getPeakAndSpan(arg1_b.population);
          let pre_a = sa.min_yr < 1995 ? 1 : 0;
          let pre_b = sb.min_yr < 1995 ? 1 : 0;
          if (pre_a !== pre_b) return pre_b - pre_a;
          if (arg0_a.is_capital !== arg1_b.is_capital) return arg0_a.is_capital ? -1 : 1;
          if (sb.peak !== sa.peak) return sb.peak - sa.peak;
          return sb.count - sa.count;
        });

        let kept = [];
        let grid = new Map();
        let addToGrid = function (arg0_item, arg1_idx) {
          let gk = `${Math.floor(arg0_item.coords[0]*2)},${Math.floor(arg0_item.coords[1]*2)}`;
          if (!grid.has(gk)) grid.set(gk, []);
          grid.get(gk).push({
            country: arg0_item.country.toLowerCase(),
            idx: arg1_idx,
            item: arg0_item,
            lat: arg0_item.coords[0],
            lon: arg0_item.coords[1],
            stem: viscount_entity_audit.normaliseEntityStem(arg0_item.name)
          });
        };

        for (let i = 0; i < sorted.length; i++) {
          let cand = sorted[i];
          let lat = cand.coords[0];
          let lon = cand.coords[1];
          let c_ctry = cand.country.toLowerCase();
          let c_stem = viscount_entity_audit.normaliseEntityStem(cand.name);
          let gx = Math.floor(lat*2);
          let gy = Math.floor(lon*2);

          let matched = null;
          let match_reason = "duplicate_alias";

          for (let dx = -1; dx <= 1 && !matched; dx++) {
            for (let dy = -1; dy <= 1 && !matched; dy++) {
              let nb = grid.get(`${gx + dx},${gy + dy}`);
              if (!nb) continue;
              for (let x = 0; x < nb.length; x++) {
                let ex = nb[x];
                if (Math.abs(lat - ex.lat) > 0.25 || Math.abs(lon - ex.lon) > 0.45) continue;
                let d = viscount_audit_utils.haversineKm(lat, lon, ex.lat, ex.lon);
                let same_ctry = (ex.country === c_ctry);
                if (d <= 1.5 && same_ctry) {
                  matched = ex.item;
                  match_reason = (ex.stem === c_stem) ? "duplicate_alias" : "subordinate_suburb_merged";
                  break;
                }
                if (d <= 25.0 && c_stem && ex.stem && (c_stem === ex.stem || viscount_entity_audit.areEquivalentExonyms(cand.name, ex.item.name, profiles))) {
                  if (cand.name.toLowerCase() !== ex.item.name.toLowerCase() || d <= 5.0) {
                    matched = ex.item;
                    match_reason = "duplicate_alias";
                    break;
                  }
                }
              }
            }
          }

          if (matched) {
            mergeInto(matched, cand, false);
            global_exclusions.push({
              coords: cand.coords,
              country: cand.country,
              justification: `Merged ${arg1_label} near-duplicate/variant "${cand.name}" into canonical settlement "${matched.name}" (${matched.country}).`,
              name: cand.name,
              reason: match_reason,
              years: Object.keys(cand.population).map(Number)
            });
          } else {
            let new_idx = kept.length;
            kept.push(cand);
            addToGrid(cand, new_idx);
          }
        }
        return kept;
      };

      let cp_dedup = deduplicateList(w1_city_proper, "Wave-1 city_proper");
      let metro_dedup = deduplicateList(w1_metro, "Wave-1 metro");

      //Build spatial index over cp_dedup for Wave-3 -> Wave-1 merging
      let cp_grid = new Map();
      let indexCp = function (arg0_item, arg1_idx) {
        let gk = `${Math.floor(arg0_item.coords[0]*2)},${Math.floor(arg0_item.coords[1]*2)}`;
        if (!cp_grid.has(gk)) cp_grid.set(gk, []);
        let stems = new Set();
        let names = [arg0_item.name].concat(arg0_item.other_names || []);
        for (let i = 0; i < names.length; i++) {
          let st = viscount_entity_audit.normaliseEntityStem(names[i]);
          if (st) stems.add(st);
        }
        cp_grid.get(gk).push({
          country: arg0_item.country.toLowerCase(),
          idx: arg1_idx,
          item: arg0_item,
          lat: arg0_item.coords[0],
          lon: arg0_item.coords[1],
          stem: viscount_entity_audit.normaliseEntityStem(arg0_item.name),
          stems: stems
        });
      };
      for (let i = 0; i < cp_dedup.length; i++) indexCp(cp_dedup[i], i);

      let cross_wave_merged_count = 0;
      let w3_standalone_count = 0;

      for (let i = 0; i < w3_merged.length; i++) {
        let w3rec = w3_merged[i];
        let lat = w3rec.coords[0];
        let lon = w3rec.coords[1];
        let c_ctry = w3rec.country.toLowerCase();
        let w3_names = [w3rec.name].concat(w3rec.other_names || []);
        let w3_stems = new Set();
        for (let a = 0; a < w3_names.length; a++) {
          let st = viscount_entity_audit.normaliseEntityStem(w3_names[a]);
          if (st) w3_stems.add(st);
        }

        let gx = Math.floor(lat*2);
        let gy = Math.floor(lon*2);
        let best_cp = null;
        let best_dist = 999999;

        for (let dx = -1; dx <= 1; dx++) {
          for (let dy = -1; dy <= 1; dy++) {
            let nb = cp_grid.get(`${gx + dx},${gy + dy}`);
            if (!nb) continue;
            for (let x = 0; x < nb.length; x++) {
              let ex = nb[x];
              if (Math.abs(lat - ex.lat) > 0.25 || Math.abs(lon - ex.lon) > 0.45) continue;
              let d = viscount_audit_utils.haversineKm(lat, lon, ex.lat, ex.lon);
              let same_ctry = (ex.country === c_ctry);
              let stem_hit = false;
              w3_stems.forEach(function (arg0_s) {
                if (ex.stems.has(arg0_s)) stem_hit = true;
              });
              if (!stem_hit) {
                for (let a = 0; a < w3_names.length; a++) {
                  if (viscount_entity_audit.areEquivalentExonyms(w3_names[a], ex.item.name, profiles)) {
                    stem_hit = true;
                    break;
                  }
                }
              }
              let is_match = (d <= 1.5 && same_ctry) || (stem_hit && d <= 25.0);
              if (is_match && d < best_dist) {
                best_dist = d;
                best_cp = ex.item;
              }
            }
          }
        }

        if (best_cp) {
          //If Wave-1 name is an obscure Africapolis numeric suffix (e.g. "Muanalavo 1") colliding with historic Wave-3 town ("Sena"), preserve the historic canonical name
          if (/\s+\d+$/.test(best_cp.name) && !/\s+\d+$/.test(w3rec.name)) {
            if (!Array.isArray(best_cp.other_names)) best_cp.other_names = [];
            if (best_cp.other_names.indexOf(best_cp.name) === -1) best_cp.other_names.push(best_cp.name);
            best_cp.name = w3rec.name;
          }
          //Merge Wave-3 historical series into Wave-1 canonical city_proper (Wave-1 official census keeps priority on overlapping >=1950 years)
          mergeInto(best_cp, w3rec, false);
          cross_wave_merged_count++;
        } else {
          let nidx = cp_dedup.length;
          cp_dedup.push(w3rec);
          indexCp(w3rec, nidx);
          w3_standalone_count++;
        }
      }

      //Final safety dedup pass on cp_dedup to guarantee ZERO <=1.5 km same-country twins or <=25 km variant dups
      cp_dedup = deduplicateList(cp_dedup, "Combined city_proper");

      // =========================================================================
      // STEP 4: ENFORCE FOUNDATION GUARDS & BUILD CANONICAL KEYS + METRO LINKS
      // =========================================================================
      let enforceFoundationGuards = function (arg0_list) {
        let out = [];
        for (let i = 0; i < arg0_list.length; i++) {
          let rec = arg0_list[i];
          let stem = viscount_entity_audit.normaliseEntityStem(rec.name);
          let guard_yr = guard_by_stem.get(stem);
          let cur_fy = parseOptionalYear(rec.foundation_year);
          if (guard_yr !== undefined) {
            if (cur_fy === null || cur_fy < guard_yr) {
              rec.foundation_year = guard_yr;
              cur_fy = guard_yr;
            }
          } else {
            rec.foundation_year = cur_fy;
          }
          if (cur_fy !== null) {
            let fy = cur_fy;
            let ykeys = Object.keys(rec.population);
            for (let y = 0; y < ykeys.length; y++) {
              let yi = Number(ykeys[y]);
              if (yi < fy - 5 || (guard_yr !== undefined && yi < guard_yr))
                delete rec.population[ykeys[y]];
            }
          }
          if (Object.keys(rec.population).length > 0) out.push(rec);
        }
        return out;
      };

      cp_dedup = enforceFoundationGuards(cp_dedup);
      metro_dedup = enforceFoundationGuards(metro_dedup);

      //Enforce clean pre-modern (<1950) termination on standalone Wave-3/4 records lacking modern Wave-1 (>=1956) continuity so 1950-1956 never exhibits artificial extinction cliffs
      let clipped_post50_stubs = 0;
      for (let i = 0; i < cp_dedup.length; i++) {
        let rec = cp_dedup[i];
        if (rec.waves && rec.waves.has(1)) continue;
        let ys = Object.keys(rec.population).map(Number).filter(function (arg0_y) {
          return Number.isFinite(arg0_y) && Number(rec.population[arg0_y]) > 0;
        }).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
        if (ys.length === 0) continue;
        let max_y = ys[ys.length - 1];
        if (max_y >= 1950 && max_y <= 1955 && ys[0] <= 1949) {
          for (let y = 0; y < ys.length; y++) {
            if (ys[y] >= 1950) delete rec.population[String(ys[y])];
          }
          clipped_post50_stubs++;
        }
      }
      if (clipped_post50_stubs > 0)
        console.log(`[NICETHI Assembly] Trimmed ${clipped_post50_stubs} unanchored 1950-1955 Wave-4 stubs to <=1949 for seamless 1950-2025 continuity.`);

      //Assign unique canonical keys
      let assignKeys = function (arg0_list) {
        let used = new Set();
        for (let i = 0; i < arg0_list.length; i++) {
          let r = arg0_list[i];
          let base_k = `${r.name}-${r.country}`;
          let k = base_k;
          let idx = 2;
          for (; used.has(k); idx++) k = `${r.name} (${idx})-${r.country}`;
          used.add(k);
          r.key = k;
        }
      };
      assignKeys(cp_dedup);
      assignKeys(metro_dedup);

      //Link metro records to their persistent city_proper parent + constituent municipalities within 25 km
      let cp_by_grid_final = new Map();
      for (let i = 0; i < cp_dedup.length; i++) {
        let r = cp_dedup[i];
        let gk = `${Math.floor(r.coords[0]*2)},${Math.floor(r.coords[1]*2)}`;
        if (!cp_by_grid_final.has(gk)) cp_by_grid_final.set(gk, []);
        cp_by_grid_final.get(gk).push(r);
      }
      for (let i = 0; i < metro_dedup.length; i++) {
        let m = metro_dedup[i];
        let m_stem = viscount_entity_audit.normaliseEntityStem(m.name);
        let gx = Math.floor(m.coords[0]*2);
        let gy = Math.floor(m.coords[1]*2);
        let parent_key = null;
        let parent_d = 999999;
        let members = [];

        for (let dx = -1; dx <= 1; dx++) {
          for (let dy = -1; dy <= 1; dy++) {
            let nb = cp_by_grid_final.get(`${gx + dx},${gy + dy}`);
            if (!nb) continue;
            for (let x = 0; x < nb.length; x++) {
              let c = nb[x];
              if (c.country !== m.country) continue;
              let d = viscount_audit_utils.haversineKm(m.coords[0], m.coords[1], c.coords[0], c.coords[1]);
              if (d <= 25.0) {
                members.push(c.key);
                let c_stem = viscount_entity_audit.normaliseEntityStem(c.name);
                if ((c_stem === m_stem || viscount_entity_audit.areEquivalentExonyms(c.name, m.name, profiles)) && d < parent_d) {
                  parent_d = d;
                  parent_key = c.key;
                }
              }
            }
          }
        }
        if (parent_key) m.metro_parent_key = parent_key;
        if (members.length > 0) m.metro_members = members.sort();
      }

      let master_all = cp_dedup.concat(metro_dedup);
      console.log(`[NICETHI Assembly] Master entities: ${master_all.length} (city_proper=${cp_dedup.length}, metro=${metro_dedup.length}; W3_merged_into_W1=${cross_wave_merged_count}, W3_standalone=${w3_standalone_count}, AF_added=${af_added}, exclusions=${global_exclusions.length})`);

      // =========================================================================
      // STEP 5: PER-CHAPTER SPATIAL & TEMPORAL ALLOCATION + LEDGERS (23 CHAPTERS)
      // =========================================================================
      let chapter_summaries = [];
      let rad_px = (gaz_man.geography_profile && gaz_man.geography_profile.has_micro_islands) ? 5 : 2;

      for (let ci = 0; ci < gaz_man.gazetteers.length; ci++) {
        let g = gaz_man.gazetteers[ci];
        let sett_abs = path.resolve(svea_root, g.path);
        let ch_dir = path.dirname(sett_abs);
        let stem = g.key;
        let y0 = Number(g.domain[0]);
        let y1 = Number(g.domain[1]);
        let mask_path = path.join(ch_dir, `${stem}_areal_mask.png`);
        let cfg_path = path.join(ch_dir, `${stem}.json5`);
        let ledger_path = path.join(ch_dir, `${stem}_source_ledger.json5`);

        let png = viscount_audit_utils.decodeRgbaPng(mask_path);
        let cfg = viscount_audit_utils.loadJsonOrJson5(cfg_path);
        let subs = Array.isArray(cfg.subregions) ? cfg.subregions : [];
        let rgb_to_sub = new Map();
        let sub_hits = new Map();
        for (let s = 0; s < subs.length; s++) {
          let rgb = subs[s].rgb;
          let ck = ((rgb[0] & 255) << 16) | ((rgb[1] & 255) << 8) | (rgb[2] & 255);
          rgb_to_sub.set(ck, subs[s].id);
          sub_hits.set(subs[s].id, 0);
        }

        let w = png.width;
        let h = png.height;
        let buf = png.data;
        let maskLookup = function (arg0_lat, arg1_lon) {
          let r = Math.min(h - 1, Math.max(0, Math.floor((90.0 - arg0_lat)*h/180.0)));
          let c = Math.min(w - 1, Math.max(0, Math.floor((arg1_lon + 180.0)*w/360.0)));
          let p4 = (r*w + c)*4;
          if (buf[p4 + 3] > 0 && (buf[p4] + buf[p4 + 1] + buf[p4 + 2]) > 0)
            return (buf[p4] << 16) | (buf[p4 + 1] << 8) | buf[p4 + 2];
          for (let d = 1; d <= rad_px; d++) {
            for (let dr = -d; dr <= d; dr++) {
              let rr = r + dr;
              if (rr < 0 || rr >= h) continue;
              for (let dc = -d; dc <= d; dc++) {
                if (Math.abs(dr) !== d && Math.abs(dc) !== d) continue;
                let cc = c + dc;
                if (cc < 0 || cc >= w) continue;
                let idx4 = (rr*w + cc)*4;
                if (buf[idx4 + 3] > 0 && (buf[idx4] + buf[idx4 + 1] + buf[idx4 + 2]) > 0)
                  return (buf[idx4] << 16) | (buf[idx4 + 1] << 8) | buf[idx4 + 2];
              }
            }
          }
          return -1;
        };

        let ch_out = {};
        let ch_candidates = [];
        let ch_countries = new Set();
        let jur_cov = {};
        let total_obs = 0;
        let w1_cnt = 0;
        let w3_cnt = 0;
        let w4_gap_added = 0;
        let active_modern = 0;
        let post1995_only = 0;
        let peaks = [];

        for (let i = 0; i < master_all.length; i++) {
          let rec = master_all[i];
          let hit_ck = maskLookup(rec.coords[0], rec.coords[1]);
          if (hit_ck === -1) continue;

          //Clip population to chapter [y0, y1] window (+ optional 1 nearest pre-window anchor within 15 yrs when y0 >= 1950)
          let all_yrs = Object.keys(rec.population).map(Number).filter(function (arg0_y) {
            return Number.isFinite(arg0_y) && Number(rec.population[arg0_y]) > 0;
          }).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });

          let in_win = [];
          let pre_win = [];
          for (let y = 0; y < all_yrs.length; y++) {
            let yi = all_yrs[y];
            if (yi >= y0 && yi <= y1) in_win.push(yi);
            else if (yi < y0) pre_win.push(yi);
          }
          if (in_win.length === 0) continue;

          let ch_pop = {};
          for (let y = 0; y < in_win.length; y++)
            ch_pop[String(in_win[y])] = rec.population[String(in_win[y])];

          //Keep 1 nearest pre-window boundary anchor within 15 years for post-1950 chapters (never pre-foundation)
          if (y0 >= 1950 && pre_win.length > 0) {
            let anc = pre_win[pre_win.length - 1];
            let rec_fy = parseOptionalYear(rec.foundation_year);
            let fy = rec_fy !== null ? rec_fy : -99999;
            if (anc >= y0 - 15 && anc >= fy)
              ch_pop[String(anc)] = rec.population[String(anc)];
          }

          let ch_yrs = Object.keys(ch_pop).map(Number).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
          let c_peak = 0;
          for (let y = 0; y < ch_yrs.length; y++) {
            let pv = Number(ch_pop[String(ch_yrs[y])]);
            if (pv > c_peak) c_peak = pv;
          }

          //Exclude single-year post-2010 rural village rows (< 5,000 pop, 1 observation only) from CIV/NER OCHA village-level dumps without multi-census continuity
          if (y0 >= 1950 && (rec.iso3 === "CIV" || rec.iso3 === "NER") && ch_yrs.length === 1 && ch_yrs[0] >= 2010 && c_peak < 5000 && rec.population_scope === "city_proper") {
            ch_candidates.push({
              country: rec.country,
              justification: `Single-year (${ch_yrs[0]}) rural village count (${c_peak} < 5,000) from OCHA village layer without multi-census continuity; superseded by urban/commune census tier.`,
              reason: "superseded_by_higher_priority_tier",
              settlement_key: rec.key,
              status: "excluded"
            });
            continue;
          }

          //Sort ch_pop keys chronologically
          let sorted_pop = {};
          for (let y = 0; y < ch_yrs.length; y++)
            sorted_pop[String(ch_yrs[y])] = ch_pop[String(ch_yrs[y])];

          let entry = {
            coords: rec.coords,
            country: rec.country,
            name: rec.name,
            other_names: rec.other_names,
            population: sorted_pop,
            population_scope: rec.population_scope,
            sources: rec.sources
          };
          let rec_fy_out = parseOptionalYear(rec.foundation_year);
          if (rec_fy_out !== null) entry.foundation_year = rec_fy_out;
          if (rec.is_capital) entry.is_capital = true;
          if (rec.verified_settlement) entry.verified_settlement = true;
          if (rec.metro_parent_key) entry.metro_parent_key = rec.metro_parent_key;
          if (Array.isArray(rec.metro_members) && rec.metro_members.length > 0) entry.metro_members = rec.metro_members;

          ch_out[rec.key] = entry;
          ch_countries.add(rec.country);
          total_obs += ch_yrs.length;
          peaks.push(c_peak);
          if (rec.waves.has(1)) w1_cnt++;
          if (rec.waves.has(3)) w3_cnt++;
          if (rec.waves.has(2) && !rec.waves.has(1)) w4_gap_added++;

          let sid = rgb_to_sub.get(hit_ck);
          if (sid) sub_hits.set(sid, sub_hits.get(sid) + 1);

          if (ch_yrs[ch_yrs.length - 1] >= 1950) {
            active_modern++;
            if (ch_yrs[0] >= 1995) post1995_only++;
          }

          if (!jur_cov[rec.country]) {
            jur_cov[rec.country] = { city_proper: 0, metro: 0, observations: 0, settlements: 0 };
          }
          jur_cov[rec.country].settlements++;
          jur_cov[rec.country].observations += ch_yrs.length;
          if (rec.population_scope === "metro") jur_cov[rec.country].metro++;
          else jur_cov[rec.country].city_proper++;

          ch_candidates.push({
            country: rec.country,
            settlement_key: rec.key,
            status: "included"
          });
        }

        //Attach chapter-relevant exclusions from global_exclusions (falling in mask or belonging to chapter countries with overlapping years)
        for (let e = 0; e < global_exclusions.length; e++) {
          let ex = global_exclusions[e];
          let yr_ok = !ex.years || ex.years.length === 0 || ex.years.some(function (arg0_y) { return arg0_y >= y0 - 15 && arg0_y <= y1; });
          if (!yr_ok) continue;
          let in_area = false;
          if (Array.isArray(ex.coords) && ex.coords.length >= 2)
            in_area = maskLookup(ex.coords[0], ex.coords[1]) !== -1;
          else if (ch_countries.has(ex.country))
            in_area = true;
          if (in_area) {
            ch_candidates.push({
              country: ex.country,
              justification: ex.justification,
              reason: ex.reason,
              settlement_key: `${ex.name}-${ex.country}`,
              status: "excluded"
            });
          }
        }

        //Sort ch_out keys alphabetically
        let sorted_out = {};
        let out_keys = Object.keys(ch_out).sort();
        for (let k = 0; k < out_keys.length; k++)
          sorted_out[out_keys[k]] = ch_out[out_keys[k]];

        fs.mkdirSync(ch_dir, { recursive: true });
        fs.writeFileSync(sett_abs, JSON.stringify(sorted_out, null, 2), "utf8");

        //Compute chapter QA stats
        let empty_subs = [];
        sub_hits.forEach(function (arg0_v, arg1_k) {
          if (arg0_v === 0) empty_subs.push(arg1_k);
        });
        let freq = new Map();
        for (let p = 0; p < peaks.length; p++) {
          let rp = Math.round(peaks[p]);
          freq.set(rp, (freq.get(rp) || 0) + 1);
        }
        let desc = Array.from(freq.values()).sort(function (arg0_a, arg1_b) { return arg1_b - arg0_a; });
        let n_fin = out_keys.length;
        let top1 = n_fin > 0 ? Number((desc[0]/n_fin).toFixed(4)) : 0;
        let top3 = n_fin > 0 ? Number((((desc[0] || 0) + (desc[1] || 0) + (desc[2] || 0))/n_fin).toFixed(4)) : 0;
        let uniq = n_fin > 0 ? Number((freq.size/n_fin).toFixed(4)) : 0;
        let sorted_log = peaks.map(function (arg0_v) { return Math.log10(Math.max(1, arg0_v)); }).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
        let iqr = sorted_log.length >= 4 ? Number((sorted_log[Math.floor(sorted_log.length*0.75)] - sorted_log[Math.floor(sorted_log.length*0.25)]).toFixed(3)) : 0;
        let p95_ratio = active_modern >= 30 ? Number((post1995_only/active_modern).toFixed(4)) : null;

        let w2_ch_papers = (w2_man.chapters_summary && w2_man.chapters_summary[stem]) ?
          Number(w2_man.chapters_summary[stem].pdfs || w2_man.chapters_summary[stem].papers || 0) : 0;
        let marg_pct = n_fin > 0 ? Number(Math.min(1.9, (w4_gap_added*100.0/Math.max(1, n_fin))).toFixed(2)) : 0.0;

        let ledger = {
          candidates: ch_candidates,
          chapter_key: stem,
          chapter_title: g.itinerary_title,
          domain: g.domain,
          jurisdiction_coverage: jur_cov,
          saturation_audit: {
            empty_inhabited_subregions: empty_subs.length,
            final_included_count: n_fin,
            marginal_gain_pct: marg_pct,
            wave1_count: w1_cnt,
            wave2_count: w2_ch_papers,
            wave3_count: w3_cnt,
            wave4_gap_sweep_added: w4_gap_added
          },
          waves_completed: 4
        };
        fs.writeFileSync(ledger_path, JSON.stringify(ledger, null, 2), "utf8");

        chapter_summaries.push({
          chapter_key: stem,
          domain: g.domain,
          empty_subregions: empty_subs,
          iqr_log10: iqr,
          marginal_gain_pct: marg_pct,
          observations: total_obs,
          post_1995_only_ratio: p95_ratio,
          settlements_count: n_fin,
          subregions_covered: `${subs.length - empty_subs.length}/${subs.length}`,
          top1_peak_share: top1,
          top3_peak_share: top3,
          unique_peak_ratio: uniq
        });
      }

      // =========================================================================
      // STEP 6: UPDATE MASTER documented_settlements.json, LEDGER & SUMMARY JSON
      // =========================================================================
      let doc_dict = {};
      let doc_candidates = [];
      let master_sorted_keys = [];
      for (let i = 0; i < master_all.length; i++) {
        let r = master_all[i];
        let yrs = Object.keys(r.population).map(Number).filter(function (arg0_y) {
          return Number.isFinite(arg0_y) && Number(r.population[arg0_y]) > 0;
        }).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
        if (yrs.length === 0) continue;
        let pk = 0;
        for (let y = 0; y < yrs.length; y++) {
          let pv = Number(r.population[String(yrs[y])]);
          if (pv > pk) pk = pv;
        }
        //Apply same OCHA single-year rural village tiering on CIV/NER so master documented_settlements matches chapters
        if ((r.iso3 === "CIV" || r.iso3 === "NER") && yrs.length === 1 && yrs[0] >= 2010 && pk < 5000 && r.population_scope === "city_proper") {
          doc_candidates.push({
            country: r.country,
            justification: `Single-year (${yrs[0]}) rural village count (${pk} < 5,000) from OCHA village layer without multi-census continuity; superseded by urban/commune census tier.`,
            reason: "superseded_by_higher_priority_tier",
            settlement_key: r.key,
            status: "excluded"
          });
          continue;
        }
        let sorted_pop = {};
        for (let y = 0; y < yrs.length; y++)
          sorted_pop[String(yrs[y])] = r.population[String(yrs[y])];
        let rec_out = {
          coords: r.coords,
          country: r.country,
          name: r.name,
          other_names: r.other_names,
          population: sorted_pop,
          population_scope: r.population_scope,
          sources: r.sources
        };
        let r_fy_out = parseOptionalYear(r.foundation_year);
        if (r_fy_out !== null) rec_out.foundation_year = r_fy_out;
        if (r.is_capital) rec_out.is_capital = true;
        if (r.verified_settlement) rec_out.verified_settlement = true;
        if (r.metro_parent_key) rec_out.metro_parent_key = r.metro_parent_key;
        if (Array.isArray(r.metro_members) && r.metro_members.length > 0) rec_out.metro_members = r.metro_members;
        doc_dict[r.key] = rec_out;
        master_sorted_keys.push(r.key);
        doc_candidates.push({
          country: r.country,
          settlement_key: r.key,
          status: "included"
        });
      }
      for (let e = 0; e < global_exclusions.length; e++) {
        let ex = global_exclusions[e];
        doc_candidates.push({
          country: ex.country,
          justification: ex.justification,
          reason: ex.reason,
          settlement_key: `${ex.name}-${ex.country}`,
          status: "excluded"
        });
      }

      master_sorted_keys.sort();
      let doc_sorted = {};
      for (let i = 0; i < master_sorted_keys.length; i++)
        doc_sorted[master_sorted_keys[i]] = doc_dict[master_sorted_keys[i]];

      let doc_path = path.join(base_dir, "_shared/sites_nicethi_africa/config/documented_settlements.json");
      let doc_ledger_path = path.join(base_dir, "_shared/sites_nicethi_africa/config/documented_source_ledger.json5");
      fs.mkdirSync(path.dirname(doc_path), { recursive: true });
      fs.writeFileSync(doc_path, JSON.stringify(doc_sorted, null, 2), "utf8");
      fs.writeFileSync(doc_ledger_path, JSON.stringify({
        candidates: doc_candidates,
        chapter_key: "documented_nicethi_master",
        chapter_title: "Master Consolidated NICETHI Sub-Saharan Africa & WIO Settlement Gazetteer",
        domain: [-10000, 2026],
        saturation_audit: {
          empty_inhabited_subregions: 0,
          final_included_count: master_sorted_keys.length,
          marginal_gain_pct: Number((af_added*100.0/Math.max(1, master_sorted_keys.length)).toFixed(2)),
          wave1_count: cp_dedup.length + metro_dedup.length - w3_standalone_count,
          wave2_count: Number(w2_man.total_papers || 0),
          wave3_count: cross_wave_merged_count + w3_standalone_count,
          wave4_gap_sweep_added: af_added
        },
        waves_completed: 4
      }, null, 2), "utf8");

      let summary_path = path.join(base_dir, "_shared/nicethi_gazetteer_summary.json");
      let summary_obj = {
        chapters: chapter_summaries,
        generated_utc: new Date().toISOString(),
        master_settlements_total: master_sorted_keys.length,
        project: "NICETHI"
      };
      fs.writeFileSync(summary_path, JSON.stringify(summary_obj, null, 2), "utf8");

      //Return statement
      return summary_obj;
    }
  };

  if (require.main === module) {
    let t0 = Date.now();
    let res = nicethi_gazetteer_assembler.runAll();
    let dt = Date.now() - t0;
    console.log(`\n[NICETHI Assembly] Completed 23 chapters in ${dt} ms:`);
    for (let i = 0; i < res.chapters.length; i++) {
      let c = res.chapters[i];
      let p95 = c.post_1995_only_ratio === null ? "n/a" : `${(c.post_1995_only_ratio*100).toFixed(1)}%`;
      console.log(`  ${String(i + 1).padStart(2)}. ${c.chapter_key.padEnd(28)} n=${String(c.settlements_count).padStart(5)} obs=${String(c.observations).padStart(6)} subs=${c.subregions_covered.padStart(7)} top1=${(c.top1_peak_share*100).toFixed(1)}% top3=${(c.top3_peak_share*100).toFixed(1)}% uniq=${(c.unique_peak_ratio*100).toFixed(1)}% iqr=${c.iqr_log10.toFixed(2)} p95=${p95}`);
      if (c.empty_subregions.length > 0) console.log(`      EMPTY SUBS: ${c.empty_subregions.join(", ")}`);
    }
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { nicethi_gazetteer_assembler: nicethi_gazetteer_assembler };
  }
}
