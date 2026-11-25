//Import modules
let fs = require("fs");
let https = require("https");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");
let { viscount_entity_audit } = require("./viscount_entity_and_continuity_audit");

//Initialise functions
{
  let residual_toponymy_resolver = {
    ARTICLE_INVERT_RE: /^(.+?),\s*(Al|El|As|Ash|Ar|Az|Ad|An|At|Le|La|Les|L'|Los|Las|Il|Lo|De|Den|Het|Der|Die|Das|The)$/i,
    CYRILLIC_MAP: {
      "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ё": "Yo", "Ж": "Zh", "З": "Z", "И": "I",
      "Й": "Y", "К": "K", "Л": "L", "М": "M", "Н": "N", "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T",
      "У": "U", "Ф": "F", "Х": "Kh", "Ц": "Ts", "Ч": "Ch", "Ш": "Sh", "Щ": "Shch", "Ъ": "", "Ы": "Y", "Ь": "",
      "Э": "E", "Ю": "Yu", "Я": "Ya", "І": "I", "Ї": "Yi", "Є": "Ye", "Ґ": "G", "Ў": "U",
      "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
      "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
      "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
      "э": "e", "ю": "yu", "я": "ya", "і": "i", "ї": "yi", "є": "ye", "ґ": "g", "ў": "u"
    },
    GREEK_MAP: {
      "Α": "A", "Β": "V", "Γ": "G", "Δ": "D", "Ε": "E", "Ζ": "Z", "Η": "I", "Θ": "Th", "Ι": "I", "Κ": "K",
      "Λ": "L", "Μ": "M", "Ν": "N", "Ξ": "X", "Ο": "O", "Π": "P", "Ρ": "R", "Σ": "S", "Τ": "T", "Υ": "Y",
      "Φ": "F", "Χ": "Ch", "Ψ": "Ps", "Ω": "O",
      "α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i", "θ": "th", "ι": "i", "κ": "k",
      "λ": "l", "μ": "m", "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t",
      "υ": "y", "φ": "f", "χ": "ch", "ψ": "ps", "ω": "o"
    },
    NON_LATIN_RE: /[\u0370-\u03FF\u0400-\u04FF\u0530-\u058F\u0590-\u05FF\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u10A0-\u10FF\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]/,
    USER_AGENT: "SVEA-Viscount-Pass2-Toponymy/3.0 (https://confoederatio.org; zero-llm-whg-geohack)",

    /**
     * Cleans and transliterates a candidate string into English-language Latin script without corruptions.
     * @alias residual_toponymy_resolver.cleanToLatin
     *
     * @param {string} arg0_raw
     *
     * @returns {string}
     */
    cleanToLatin (arg0_raw) {
      //Convert from parameters
      let raw = String(arg0_raw || "").trim();

      //Guard clauses
      if (!raw) return "";

      //Function body
      let s = raw.replace(/\s*\([^)]*\)/g, "").replace(/`/g, "").trim();
      let inv = s.match(this.ARTICLE_INVERT_RE);
      if (inv) {
        let base = inv[1].trim();
        let art = inv[2].trim();
        let art_low = art.toLowerCase();
        if (art_low === "al" || art_low === "el" || art_low === "as" || art_low === "ash" ||
            art_low === "ar" || art_low === "az" || art_low === "ad" || art_low === "an" || art_low === "at") {
          s = `${art}-${base}`;
        } else if (art_low === "l'") {
          s = `L'${base}`;
        } else {
          s = `${art} ${base}`;
        }
      }

      if (/[\u0400-\u04FF]/.test(s)) {
        let out = "";
        for (let i = 0; i < s.length; i++)
          out += (this.CYRILLIC_MAP[s[i]] !== undefined) ? this.CYRILLIC_MAP[s[i]] : s[i];
        s = out;
      }
      if (/[\u0370-\u03FF]/.test(s)) {
        let norm_g = s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        let out = "";
        for (let i = 0; i < norm_g.length; i++)
          out += (this.GREEK_MAP[norm_g[i]] !== undefined) ? this.GREEK_MAP[norm_g[i]] : norm_g[i];
        s = out;
      }

      s = s.replace(/\s+/g, " ").trim();
      if (!s || this.NON_LATIN_RE.test(s) || s.includes("?") || s.includes("\uFFFD"))
        return "";

      //Return statement
      return s;
    },

    /**
     * Performs a polite HTTPS GET returning parsed JSON or null on transient failure.
     * @alias residual_toponymy_resolver.fetchJson
     *
     * @param {string} arg0_url
     * @param {number} [arg1_timeout_ms=10000]
     *
     * @returns {Promise<Object|null>}
     */
    fetchJson (arg0_url, arg1_timeout_ms) {
      //Convert from parameters
      let timeout_ms = Number(arg1_timeout_ms) || 10000;
      let url = arg0_url;
      let ua = this.USER_AGENT;

      //Return statement
      return new Promise(function (arg0_resolve) {
        let req = https.get(url, { headers: { "Accept": "application/json", "User-Agent": ua }, timeout: timeout_ms }, function (arg0_res) {
          if (arg0_res.statusCode && arg0_res.statusCode >= 300 && arg0_res.statusCode < 400 && arg0_res.headers.location) {
            arg0_res.resume();
            arg0_resolve(null);
            return;
          }
          if (!arg0_res.statusCode || arg0_res.statusCode >= 400) {
            arg0_res.resume();
            arg0_resolve(null);
            return;
          }
          let chunks = [];
          arg0_res.on("data", function (arg0_c) { chunks.push(arg0_c); });
          arg0_res.on("end", function () {
            try {
              arg0_resolve(JSON.parse(Buffer.concat(chunks).toString("utf8")));
            } catch (e) {
              arg0_resolve(null);
            }
          });
        });
        req.on("timeout", function () {
          req.destroy();
          arg0_resolve(null);
        });
        req.on("error", function () {
          arg0_resolve(null);
        });
      });
    },

    /**
     * Infers preferred de facto ruling-authority language hints at `[lng, lat]` for a given year using `states.json`.
     * @alias residual_toponymy_resolver.inferAuthorityLanguagesAtCoord
     *
     * @param {number} arg0_lng
     * @param {number} arg1_lat
     * @param {number} arg2_year
     * @param {Array<Object>} arg3_states_index
     *
     * @returns {Array<string>}
     */
    inferAuthorityLanguagesAtCoord (arg0_lng, arg1_lat, arg2_year, arg3_states_index) {
      //Convert from parameters
      let lat = Number(arg1_lat);
      let lng = Number(arg0_lng);
      let states = Array.isArray(arg3_states_index) ? arg3_states_index : [];
      let yr = Number(arg2_year);

      //Declare local instance variables
      let langs = [];
      let matches = [];

      //Function body
      for (let i = 0; i < states.length; i++) {
        let st = states[i];
        if (yr < st.start_year || yr > st.stop_year) continue;
        let bb = st.bbox;
        if (lng >= bb[0] && lng <= bb[2] && lat >= bb[1] && lat <= bb[3])
          matches.push(st);
      }

      // Smallest enclosing bbox is most specific de facto polity
      matches.sort(function (arg0_a, arg1_b) { return arg0_a.area - arg1_b.area; });
      let top_name = matches.length > 0 ? matches[0].name_low : "";
      if (top_name) {
        if (/\b(?:russian|soviet|ussr|muscovy)\b/.test(top_name)) langs.push("ru");
        else if (/\b(?:german|prussia|austria|habsburg|holy roman|saxony|bavaria)\b/.test(top_name)) langs.push("de");
        else if (/\b(?:japan|chosen|tokugawa|meiji)\b/.test(top_name)) langs.push("ja");
        else if (/\b(?:ottoman|turkey|turkish)\b/.test(top_name)) langs.push("tr");
        else if (/\b(?:polish|poland|lithuania)\b/.test(top_name)) langs.push("pl");
        else if (/\b(?:spain|spanish|castile|new spain|peru|new granada|rio de la plata)\b/.test(top_name)) langs.push("es");
        else if (/\b(?:portugal|portuguese|brazil)\b/.test(top_name)) langs.push("pt");
        else if (/\b(?:france|french|gaul)\b/.test(top_name)) langs.push("fr");
        else if (/\b(?:dutch|netherlands|east indies)\b/.test(top_name)) langs.push("nl");
        else if (/\b(?:denmark|danish)\b/.test(top_name)) langs.push("da");
        else if (/\b(?:china|qing|ming|yuan|song|tang|han|prc)\b/.test(top_name)) langs.push("zh");
        else if (/\b(?:british|united kingdom|england|india|australia|canada|united states)\b/.test(top_name)) langs.push("en");
      }
      if (!langs.includes("en")) langs.push("en");

      //Return statement
      return langs;
    },

    /**
     * Loads lightweight state bbox records from Dataview `data/atlas/temp/states.json` for de facto authority matching.
     * @alias residual_toponymy_resolver.loadStatesIndex
     *
     * @param {string} arg0_dataview_root
     *
     * @returns {Array<Object>}
     */
    loadStatesIndex (arg0_dataview_root) {
      //Convert from parameters
      let states_path = path.join(arg0_dataview_root, "data/atlas/temp/states.json");

      //Declare local instance variables
      let out = [];

      //Guard clauses
      if (!fs.existsSync(states_path)) return out;

      //Function body
      try {
        let raw = JSON.parse(fs.readFileSync(states_path, "utf8"));
        if (!Array.isArray(raw)) return out;
        for (let i = 0; i < raw.length; i++) {
          let s = raw[i];
          if (!s || !Array.isArray(s.bbox) || s.bbox.length < 4) continue;
          let area = Math.max(0.01, (Number(s.bbox[2]) - Number(s.bbox[0]))*(Number(s.bbox[3]) - Number(s.bbox[1])));
          out.push({
            area: area,
            bbox: [Number(s.bbox[0]), Number(s.bbox[1]), Number(s.bbox[2]), Number(s.bbox[3])],
            name_low: String(s.name || "").toLowerCase(),
            start_year: Number.isFinite(Number(s.start_year)) ? Number(s.start_year) : -10000,
            stop_year: Number.isFinite(Number(s.stop_year)) ? Number(s.stop_year) : 2026
          });
        }
      } catch (e) {}

      //Return statement
      return out;
    },

    /**
     * Parses CLI flags for `resolve_residual_toponymy_whg_geohack.js`.
     * @alias residual_toponymy_resolver.parseCliArgs
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
        dataview_root: "",
        in_file: "",
        limit: 0,
        max_workers: 4,
        offline: false,
        out_file: "",
        project: "",
        svea_root: ""
      };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok.startsWith("--project=")) args.project = tok.slice(10).trim().toUpperCase();
        else if (tok === "--project" && i + 1 < argv.length) args.project = argv[++i].trim().toUpperCase();
        else if (tok.startsWith("--in-file=")) args.in_file = tok.slice(10).trim();
        else if (tok.startsWith("--out-file=")) args.out_file = tok.slice(11).trim();
        else if (tok.startsWith("--svea-root=")) args.svea_root = tok.slice(12).trim();
        else if (tok.startsWith("--dataview-root=")) args.dataview_root = tok.slice(16).trim();
        else if (tok.startsWith("--limit=")) args.limit = Math.max(0, Number(tok.slice(8)) || 0);
        else if (tok.startsWith("--max-workers=")) args.max_workers = Math.max(1, Math.min(4, Number(tok.slice(14)) || 4));
        else if (tok === "--offline") args.offline = true;
      }

      //Return statement
      return args;
    },

    /**
     * Queries GeoHack-aligned MediaWiki GeoSearch + Wikidata `P1448` official historical names near `[lng, lat]`.
     * @alias residual_toponymy_resolver.queryGeoHackWikidata
     *
     * @param {Object} arg0_item
     * @param {number} arg1_max_dist_km
     * @param {Array<Object>} arg2_states_index
     *
     * @returns {Promise<Object>}
     */
    async queryGeoHackWikidata (arg0_item, arg1_max_dist_km, arg2_states_index) {
      //Convert from parameters
      let item = arg0_item;
      let max_dist_km = Number(arg1_max_dist_km) || 8.0;
      let states_index = arg2_states_index;

      //Declare local instance variables
      let lat = Number(item.coords[1]);
      let lng = Number(item.coords[0]);
      let radius_m = Math.min(10000, Math.round(max_dist_km*1000));
      let target_stem = viscount_entity_audit.normaliseEntityStem(item.name || "");
      let timeline = {};

      //Function body
      let geo_url = `https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord=${lat}|${lng}&gsradius=${radius_m}&gslimit=8&format=json`;
      let geo_res = await this.fetchJson(geo_url, 8000);
      let hits = (geo_res && geo_res.query && Array.isArray(geo_res.query.geosearch)) ? geo_res.query.geosearch : [];
      if (hits.length === 0) return { hit: false, names: timeline };

      let matched_title = "";
      for (let i = 0; i < hits.length; i++) {
        let h_stem = viscount_entity_audit.normaliseEntityStem(hits[i].title || "");
        if (target_stem && h_stem && (h_stem === target_stem || h_stem.includes(target_stem) || target_stem.includes(h_stem))) {
          matched_title = hits[i].title;
          break;
        }
      }
      if (!matched_title) return { hit: false, names: timeline };

      let pp_url = `https://en.wikipedia.org/w/api.php?action=query&prop=pageprops&ppprop=wikibase_item&titles=${encodeURIComponent(matched_title)}&format=json`;
      let pp_res = await this.fetchJson(pp_url, 8000);
      let pages = (pp_res && pp_res.query && pp_res.query.pages) ? Object.values(pp_res.query.pages) : [];
      let qid = (pages.length > 0 && pages[0] && pages[0].pageprops && pages[0].pageprops.wikibase_item) ?
        String(pages[0].pageprops.wikibase_item) : "";

      if (qid) {
        let wd_url = `https://www.wikidata.org/w/api.php?action=wbgetentities&ids=${encodeURIComponent(qid)}&props=labels|claims&format=json`;
        let wd_res = await this.fetchJson(wd_url, 8000);
        let ent = (wd_res && wd_res.entities && wd_res.entities[qid]) ? wd_res.entities[qid] : null;
        if (ent && ent.claims && Array.isArray(ent.claims.P1448)) {
          let p1448 = ent.claims.P1448;
          for (let i = 0; i < p1448.length; i++) {
            let cl = p1448[i];
            let val = cl && cl.mainsnak && cl.mainsnak.datavalue && cl.mainsnak.datavalue.value;
            if (!val || !val.text) continue;
            let start_q = cl.qualifiers && Array.isArray(cl.qualifiers.P580) ? cl.qualifiers.P580[0] : null;
            let t_str = start_q && start_q.datavalue && start_q.datavalue.value && start_q.datavalue.value.time;
            if (!t_str) continue;
            let m = String(t_str).match(/^([+-])(\d+)-(\d{2})-(\d{2})/);
            if (!m) continue;
            let yr = Number(m[2])*(m[1] === "-" ? -1 : 1);
            let mo = Math.max(1, Number(m[3]) || 1);
            let dy = Math.max(1, Number(m[4]) || 1);
            if (yr === 0 || yr < -10000 || yr > 2026) continue;
            let auth_langs = this.inferAuthorityLanguagesAtCoord(lng, lat, yr, states_index);
            if (val.language && !auth_langs.includes(val.language) && val.language !== "en") continue;
            let clean_nm = this.cleanToLatin(val.text);
            if (clean_nm) timeline[`${yr}.${mo}.${dy}`] = clean_nm;
          }
        }
        if (Object.keys(timeline).length === 0 && ent && ent.labels && ent.labels.en && ent.labels.en.value) {
          let en_clean = this.cleanToLatin(ent.labels.en.value);
          if (en_clean) {
            let ey = Number.isFinite(Number(item.earliest_year)) ? Number(item.earliest_year) : 1900;
            if (ey === 0) ey = -1;
            timeline[`${ey}.1.1`] = en_clean;
          }
        }
      }

      if (Object.keys(timeline).length === 0) {
        let title_clean = this.cleanToLatin(matched_title);
        if (title_clean) {
          let ey = Number.isFinite(Number(item.earliest_year)) ? Number(item.earliest_year) : 1900;
          if (ey === 0) ey = -1;
          timeline[`${ey}.1.1`] = title_clean;
        }
      }

      //Return statement
      return { hit: Object.keys(timeline).length > 0, names: timeline };
    },

    /**
     * Queries World Historical Gazetteer (WHG) API for historical names + timespans near `[lng, lat]`.
     * @alias residual_toponymy_resolver.queryWhg
     *
     * @param {Object} arg0_item
     * @param {number} arg1_max_dist_km
     *
     * @returns {Promise<Object>}
     */
    async queryWhg (arg0_item, arg1_max_dist_km) {
      //Convert from parameters
      let item = arg0_item;
      let max_dist_km = Number(arg1_max_dist_km) || 10.0;

      //Declare local instance variables
      let lat = Number(item.coords[1]);
      let lng = Number(item.coords[0]);
      let target_stem = viscount_entity_audit.normaliseEntityStem(item.name || "");
      let timeline = {};

      //Function body
      let url = `https://whgazetteer.org/api/index/?name=${encodeURIComponent(item.name || "")}`;
      let res = await this.fetchJson(url, 8000);
      let feats = (res && Array.isArray(res.features)) ? res.features :
        (res && Array.isArray(res.results) ? res.results : []);
      if (feats.length === 0) return { hit: false, names: timeline };

      for (let i = 0; i < feats.length; i++) {
        let feat = feats[i];
        let rep = null;
        if (feat && Array.isArray(feat.reprPoint) && feat.reprPoint.length >= 2) {
          rep = [Number(feat.reprPoint[0]), Number(feat.reprPoint[1])];
        } else if (feat && feat.geometry && feat.geometry.type === "Point" && Array.isArray(feat.geometry.coordinates)) {
          rep = [Number(feat.geometry.coordinates[0]), Number(feat.geometry.coordinates[1])];
        }
        if (!rep || !Number.isFinite(rep[0]) || !Number.isFinite(rep[1])) continue;
        let d_km = viscount_audit_utils.haversineKm(lat, lng, rep[1], rep[0]);
        if (d_km > max_dist_km) continue;

        let props = feat.properties || feat;
        let title_stem = viscount_entity_audit.normaliseEntityStem(props.title || "");
        if (target_stem && title_stem && title_stem !== target_stem && !title_stem.includes(target_stem)) continue;

        let names_arr = Array.isArray(feat.names) ? feat.names : (Array.isArray(props.names) ? props.names : []);
        for (let x = 0; x < names_arr.length; x++) {
          let nm_obj = names_arr[x];
          let top_str = this.cleanToLatin(typeof nm_obj === "string" ? nm_obj : (nm_obj.toponym || nm_obj.name || ""));
          if (!top_str) continue;
          let spans = (nm_obj && nm_obj.when && Array.isArray(nm_obj.when.timespans)) ? nm_obj.when.timespans : [];
          if (spans.length > 0) {
            for (let s_i = 0; s_i < spans.length; s_i++) {
              let start_obj = spans[s_i].start || {};
              let sy = Number(start_obj.in !== undefined ? start_obj.in : start_obj.earliest);
              if (Number.isFinite(sy) && sy !== 0 && sy >= -10000 && sy <= 2026)
                timeline[`${Math.trunc(sy)}.1.1`] = top_str;
            }
          }
        }
      }

      //Return statement
      return { hit: Object.keys(timeline).length > 0, names: timeline };
    },

    /**
     * Resolves Pass-2 residual settlements (`max_pop <= 10k`, non-capital) via bounded WHG + GeoHack + de facto authority
     * heuristics (ZERO LLM agents) and writes compact `[lng, lat]` + `date: string` output.
     * @alias residual_toponymy_resolver.runPass2
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Promise<Object>}
     */
    async runPass2 (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let svea_root = (options.svea_root) ? path.resolve(options.svea_root) :
        (viscount_audit_utils.findSveaRoot(__dirname) || path.resolve(__dirname, "../../../.."));
      let dataview_root = (options.dataview_root) ? path.resolve(options.dataview_root) :
        (process.env.DATAVIEW_ROOT ? path.resolve(process.env.DATAVIEW_ROOT) : path.resolve(svea_root, "../Project 1436 - Dataview"));
      let profiles = viscount_entity_audit.loadSkillProfiles(svea_root);
      let topo_policy = (profiles && profiles.toponymy_pipeline_policy) ? profiles.toponymy_pipeline_policy : {};
      let max_workers = Math.max(1, Math.min(4, Number(options.max_workers || topo_policy.pass2_max_http_workers) || 4));
      let whg_max_km = Number(topo_policy.pass2_whg_max_dist_km) || 10.0;
      let geohack_max_km = Number(topo_policy.pass2_geohack_max_dist_km) || 8.0;
      let project_slug = options.project ? options.project.toLowerCase() : "all_projects";
      let in_file = (options.in_file) ? path.resolve(options.in_file) :
        path.join(svea_root, "tests/toponymy_batches", project_slug, "pass2", "residuals.json");
      let out_file = (options.out_file) ? path.resolve(options.out_file) :
        path.join(path.dirname(in_file), "resolved_pass2_whg_geohack.json");
      let cache_path = path.join(svea_root, "histmap/1.data_raw/population_regional/_shared/_gis_cache/whg_geohack_cache.json");

      //Guard clauses
      if (!fs.existsSync(in_file)) {
        console.error(`[resolve_residual_toponymy_whg_geohack] Pass-2 residuals file not found: ${in_file}`);
        return { success: false };
      }

      //Function body
      let raw = JSON.parse(fs.readFileSync(in_file, "utf8"));
      let all_items = Array.isArray(raw.settlements) ? raw.settlements : (Array.isArray(raw) ? raw : []);
      let items = (options.limit > 0) ? all_items.slice(0, options.limit) : all_items;
      let states_index = this.loadStatesIndex(dataview_root);

      let cache = {};
      if (fs.existsSync(cache_path)) {
        try { cache = JSON.parse(fs.readFileSync(cache_path, "utf8")); } catch (e) { cache = {}; }
      }

      let stats = {
        cache_hits: 0,
        deterministic_fallback: 0,
        geohack_wikidata_hits: 0,
        llm_agents_used: 0,
        total_processed: 0,
        whg_hits: 0
      };
      let cities_out = new Array(items.length);
      let cursor = 0;
      let that = this;

      let runWorker = async function () {
        for (let step = 0; step < items.length; step++) {
          let idx = cursor++;
          if (idx >= items.length) break;
          let it = items[idx];
          if (!it || !Array.isArray(it.coords) || it.coords.length < 2) continue;

          // Safety guard: Pass 2 must never process Pass-1 (>10k or capital) records
          if (it.is_capital || Number(it.max_pop || 0) > (Number(topo_policy.pass1_min_peak_pop) || 10000))
            continue;

          let ckey = `${Number(it.coords[0]).toFixed(5)},${Number(it.coords[1]).toFixed(5)}|${String(it.name || "").toLowerCase()}`;
          let resolved_names = null;

          if (cache[ckey] && cache[ckey].names && Object.keys(cache[ckey].names).length > 0) {
            resolved_names = Object.assign({}, cache[ckey].names);
            stats.cache_hits++;
          } else if (!options.offline) {
            let combined = {};
            let whg_r = await that.queryWhg(it, whg_max_km);
            if (whg_r.hit) {
              Object.assign(combined, whg_r.names);
              stats.whg_hits++;
            }
            let gh_r = await that.queryGeoHackWikidata(it, geohack_max_km, states_index);
            if (gh_r.hit) {
              let gkeys = Object.keys(gh_r.names);
              for (let g = 0; g < gkeys.length; g++) {
                if (!combined[gkeys[g]]) combined[gkeys[g]] = gh_r.names[gkeys[g]];
              }
              stats.geohack_wikidata_hits++;
            }
            if (Object.keys(combined).length > 0) {
              resolved_names = combined;
              cache[ckey] = { names: combined, source: whg_r.hit ? "whg" : "geohack_wikidata" };
            }
          }

          if (!resolved_names || Object.keys(resolved_names).length === 0) {
            let fallback_map = {};
            if (it.names && typeof it.names === "object") {
              let nkeys = Object.keys(it.names);
              for (let n_i = 0; n_i < nkeys.length; n_i++) {
                let cn = that.cleanToLatin(it.names[nkeys[n_i]]);
                if (cn && viscount_entity_audit.isValidCalendarDate(nkeys[n_i]))
                  fallback_map[nkeys[n_i]] = cn;
              }
            }
            if (Object.keys(fallback_map).length === 0) {
              let clean_nm = that.cleanToLatin(it.name || it.key || "");
              if (clean_nm) {
                let ey = Number.isFinite(Number(it.earliest_year)) ? Number(it.earliest_year) : 1900;
                if (ey === 0) ey = -1;
                if (ey < -10000) ey = -10000;
                if (ey > 2026) ey = 2026;
                fallback_map[`${ey}.1.1`] = clean_nm;
              }
            }
            resolved_names = fallback_map;
            stats.deterministic_fallback++;
          }

          // Sort ascending and collapse consecutive case-insensitive duplicates
          let sorted_keys = Object.keys(resolved_names).filter(function (arg0_k) {
            return viscount_entity_audit.isValidCalendarDate(arg0_k);
          }).sort(function (arg0_a, arg1_b) {
            let pa = arg0_a.split(".").map(Number);
            let pb = arg1_b.split(".").map(Number);
            if (pa[0] !== pb[0]) return pa[0] - pb[0];
            if (pa[1] !== pb[1]) return pa[1] - pb[1];
            return pa[2] - pb[2];
          });
          let clean_names = {};
          let prev_low = "";
          for (let k_i = 0; k_i < sorted_keys.length; k_i++) {
            let dk = sorted_keys[k_i];
            let nv = that.cleanToLatin(resolved_names[dk]);
            if (!nv || nv.toLowerCase() === prev_low) continue;
            clean_names[dk] = nv;
            prev_low = nv.toLowerCase();
          }

          if (Object.keys(clean_names).length > 0) {
            cities_out[idx] = {
              coords: [Number(Number(it.coords[0]).toFixed(5)), Number(Number(it.coords[1]).toFixed(5))],
              names: clean_names
            };
            stats.total_processed++;
          }
        }
      };

      let workers = [];
      for (let w = 0; w < max_workers; w++)
        workers.push(runWorker());
      await Promise.all(workers);

      let final_cities = cities_out.filter(Boolean);
      fs.mkdirSync(path.dirname(out_file), { recursive: true });
      fs.writeFileSync(out_file, JSON.stringify({
        cities: final_cities,
        count: final_cities.length,
        generated_at_gmt0: new Date().toISOString(),
        pass: 2,
        pass_tier: "pass2_whg_geohack",
        project: options.project || raw.project || "ALL",
        schema_version: "3.0_compact_coord_map"
      }), "utf8");

      let report = {
        approved: true,
        generated_at_gmt0: new Date().toISOString(),
        mode: options.offline ? "whg_geohack_offline_cache" : "whg_geohack_deterministic",
        out_file: out_file,
        pass: 2,
        project: options.project || raw.project || "ALL",
        stats: stats
      };
      let report_path = path.join(path.dirname(out_file), "pass2_whg_geohack_report.json");
      fs.writeFileSync(report_path, JSON.stringify(report, null, 2), "utf8");

      fs.mkdirSync(path.dirname(cache_path), { recursive: true });
      fs.writeFileSync(cache_path, JSON.stringify(cache), "utf8");

      console.log(
        `[resolve_residual_toponymy_whg_geohack] Resolved ${final_cities.length} Pass-2 residual(s) ` +
        `(whg=${stats.whg_hits}, geohack_wd=${stats.geohack_wikidata_hits}, cache=${stats.cache_hits}, fallback=${stats.deterministic_fallback}, llm_agents=0) -> ${out_file}`
      );

      //Return statement
      return { out_file: out_file, report: report, success: true };
    }
  };

  if (require.main === module) {
    let cli = residual_toponymy_resolver.parseCliArgs(process.argv.slice(2));
    residual_toponymy_resolver.runPass2(cli).then(function (arg0_res) {
      process.exit(arg0_res && arg0_res.success ? 0 : 1);
    });
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { residual_toponymy_resolver: residual_toponymy_resolver };
  }
}
