//Initialise functions
{
  let BACKTICK_HACEK_MAP = {
    "`C": "Č", "`c": "č", "`D": "Ď", "`d": "ď",
    "`E": "Ě", "`e": "ě", "`N": "Ň", "`n": "ň",
    "`R": "Ř", "`r": "ř", "`S": "Š", "`s": "š",
    "`T": "Ť", "`t": "ť", "`U": "Ů", "`u": "ů",
    "`Z": "Ž", "`z": "ž"
  };

  let COUNTRY_ALIASES = {
    "czech rep.": "czechia",
    "czech republic": "czechia",
    "england and wales": "united kingdom",
    "great britain": "united kingdom",
    "korea": "south korea",
    "macedonia": "north macedonia",
    "people's republic of china": "china",
    "prc": "china",
    "republic of korea": "south korea",
    "russian federation": "russia",
    "scotland": "united kingdom",
    "skorea": "south korea",
    "the netherlands": "netherlands",
    "turkiye": "turkey",
    "uk": "united kingdom",
    "united states": "united states of america",
    "uniteds": "united states of america",
    "usa": "united states of america",
    "viet nam": "vietnam"
  };

  let HACEK_APOSTROPHE_COUNTRIES = new Set([
    "belarus", "bosnia and herzegovina", "bulgaria", "croatia", "czechia",
    "czech republic", "estonia", "kazakhstan", "kosovo", "latvia",
    "lithuania", "moldova", "mongolia", "montenegro", "north macedonia",
    "poland", "russia", "serbia", "slovakia", "slovenia", "ukraine", "ussr"
  ]);

  let LITHUANIA_SAVIVALDYBE_MAP = {
    "akmenes rajono savivaldybe": "Naujoji Akmenė",
    "alytus miesto savivaldybe": "Alytus",
    "alytus rajono savivaldybe": "Alytus",
    "anyksciu rajono savivaldybe": "Anykščiai",
    "birstono savivaldybe": "Birštonas",
    "birzu rajono savivaldybe": "Biržai",
    "druskininku savivaldybe": "Druskininkai",
    "elektrenu savivaldybe": "Elektrėnai",
    "ignalinos rajono savivaldybe": "Ignalina",
    "jonavos rajono savivaldybe": "Jonava",
    "joniskio rajono savivaldybe": "Joniškis",
    "jurbarko rajono savivaldybe": "Jurbarkas",
    "kaisiadoriu rajono savivaldybe": "Kaišiadorys",
    "kalvarijos savivaldybe": "Kalvarija",
    "kauno miesto savivaldybe": "Kaunas",
    "kauno rajono savivaldybe": "Kaunas",
    "kazlu rudos savivaldybe": "Kazlų Rūda",
    "kedainiu rajono savivaldybe": "Kėdainiai",
    "kelmes rajono savivaldybe": "Kelmė",
    "klaipedos miesto savivaldybe": "Klaipėda",
    "klaipedos rajono savivaldybe": "Gargždai",
    "kretingos rajono savivaldybe": "Kretinga",
    "kupiskio rajono savivaldybe": "Kupiškis",
    "lazdiju rajono savivaldybe": "Lazdijai",
    "marijampoles savivaldybe": "Marijampolė",
    "mazeikiu rajono savivaldybe": "Mažeikiai",
    "moletu rajono savivaldybe": "Molėtai",
    "neringos savivaldybe": "Nida",
    "pagegiu savivaldybe": "Pagėgiai",
    "pakruojo rajono savivaldybe": "Pakruojis",
    "palangos miesto savivaldybe": "Palanga",
    "panevezio miesto savivaldybe": "Panevėžys",
    "panevezio rajono savivaldybe": "Panevėžys",
    "pasvalio rajono savivaldybe": "Pasvalys",
    "plunges rajono savivaldybe": "Plungė",
    "prienu rajono savivaldybe": "Prienai",
    "radviliskio rajono savivaldybe": "Radviliškis",
    "raseiniu rajono savivaldybe": "Raseiniai",
    "rietavo savivaldybe": "Rietavas",
    "rokiskio rajono savivaldybe": "Rokiškis",
    "sakiu rajono savivaldybe": "Šakiai",
    "salcininku rajono savivaldybe": "Šalčininkai",
    "siauliu miesto savivaldybe": "Šiauliai",
    "siauliu rajono savivaldybe": "Šiauliai",
    "silales rajono savivaldybe": "Šilalė",
    "silutes rajono savivaldybe": "Šilutė",
    "sirvintu rajono savivaldybe": "Širvintos",
    "skuodo rajono savivaldybe": "Skuodas",
    "svencioniu rajono savivaldybe": "Švenčionys",
    "taurages rajono savivaldybe": "Tauragė",
    "telsiu rajono savivaldybe": "Telšiai",
    "traku rajono savivaldybe": "Trakai",
    "ukmerges rajono savivaldybe": "Ukmergė",
    "utenos rajono savivaldybe": "Utena",
    "varenos rajono savivaldybe": "Varėna",
    "vilkaviskio rajono savivaldybe": "Vilkaviškis",
    "vilniaus miesto savivaldybe": "Vilnius",
    "vilniaus rajono savivaldybe": "Vilnius",
    "visagino savivaldybe": "Visaginas",
    "zarasu rajono savivaldybe": "Zarasai"
  };

  let LOWERCASE_PARTICLES = new Set([
    "al", "am", "an", "and", "auf", "bei", "bin", "da", "das", "de", "del",
    "den", "der", "des", "di", "do", "dos", "du", "e", "el", "en", "ibn",
    "il", "im", "in", "la", "las", "le", "les", "los", "of", "on", "sous",
    "sur", "the", "van", "von", "y"
  ]);

  let ROMAN_NUMERALS_RE = /^(?:I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)$/;

  let stadester_name_normaliser = {
    _cached_amalg_cfg: undefined,
    _cached_boundary_manifest: undefined,
    _cached_boundary_shards: {},
    _cached_metro_cfg: undefined,
    _cached_non_hab_res: undefined,

    /**
     * Removes statistical/administrative boundary prefixes and suffixes across all 14 global macro-regions.
     * @alias stadester_name_normaliser.cleanStatisticalWrapper
     *
     * @param {string} arg0_name
     * @param {string} [arg1_country]
     *
     * @returns {string}
     */
    cleanStatisticalWrapper (arg0_name, arg1_country) {
      //Convert from parameters
      let country_low = this.normaliseCountryName(arg1_country);
      let s = String(arg0_name || "").trim();

      //Guard clauses
      if (!s) return "";

      //Function body
      let fold = this.foldAscii(s);
      if (country_low === "lithuania" || fold.endsWith("savivaldybe")) {
        let lt_hit = LITHUANIA_SAVIVALDYBE_MAP[fold];
        if (lt_hit) return lt_hit;
        s = s.replace(/\s+(?:rajono|miesto)?\s*savivaldyb[eė]$/i, "").trim();
      }
      if (country_low === "estonia")
        s = s.replace(/\s+(?:linn|vald|alev|alevik)$/i, "").trim();
      if (country_low === "romania" || country_low === "moldova")
        s = s.replace(/^(?:Municipiul|Ora[şș](?:ul)?|Oras|Comuna)\s+/i, "").trim();
      if (country_low === "bulgaria") {
        if (/^stolichna$/i.test(fold)) return "Sofia";
        s = s.replace(/^(?:Obshtina|Община)\s+/i, "").trim();
      }
      if (country_low === "albania")
        s = s.replace(/^Bashkia\s+/i, "").trim();
      if (country_low === "greece")
        s = s.replace(/^(?:Dimos|Koinotita|Δήμος|Κοινότητα)\s+/i, "").trim();
      if (country_low === "croatia")
        s = s.replace(/^(?:Grad|Općina)\s+/i, "").trim();
      if (country_low === "indonesia")
        s = s.replace(/^(?:Kota\s+Administrasi|Kabupaten|Kota)\s+/i, "").trim();
      if (country_low === "ukraine")
        s = s.replace(/\s+(?:miska|selyshchna|silska)\s+hromada$/i, "").trim();
      if (country_low === "russia" || country_low === "belarus" || country_low === "kazakhstan")
        s = s.replace(/^(?:Gorodskoy\s+okrug|Gorod|PGT)\s+/i, "").trim();

      s = s.replace(/^Greater\s+(?=[A-Z])/i, "");
      s = s.replace(/\s*\((?:CDP|CCD|MSA|UA|OG|LGA|UCL|SUA|CSD|CMA|balance|urban area|agglomeration|municipality|commune|district|greater city)\)\s*$/i, "").trim();
      s = s.replace(/\s+(?:Central Business District|Metropolitan Borough|District Municipality|Metropolitan Municipality|Local Municipality|Municipal Corporation|Census Town|Nagar Panchayat|Cantonment Board|Urban Area|Unincorporated|CDP|CCD)$/i, "").trim();

      //Return statement
      return s;
    },

    /**
     * Decodes Populstat backtick and Slavic apostrophe haceks, fixes unbalanced parentheses, and trims stray quotes.
     * @alias stadester_name_normaliser.decodeHaceksAndQuotes
     *
     * @param {string} arg0_name
     * @param {string} [arg1_country]
     *
     * @returns {string}
     */
    decodeHaceksAndQuotes (arg0_name, arg1_country) {
      //Convert from parameters
      let country_low = this.normaliseCountryName(arg1_country);
      let s = String(arg0_name || "").trim();

      //Guard clauses
      if (!s) return "";

      //Function body
      let keys = Object.keys(BACKTICK_HACEK_MAP);
      for (let i = 0; i < keys.length; i++) {
        if (s.includes(keys[i]))
          s = s.split(keys[i]).join(BACKTICK_HACEK_MAP[keys[i]]);
      }

      if (country_low === "united kingdom" || country_low === "ireland")
        s = s.replace(/^'+([A-Z])/, "$1");

      let is_slavic_hacek = (!country_low || HACEK_APOSTROPHE_COUNTRIES.has(country_low));
      if (is_slavic_hacek) {
        s = s
          .replace(/(^|[\s\-])'C([a-z])/g, "$1Č$2")
          .replace(/(^|[\s\-])'S([a-z])/g, "$1Š$2")
          .replace(/(^|[\s\-])'Z([a-z])/g, "$1Ž$2")
          .replace(/(^|[\s\-])'R([a-z])/g, "$1Ř$2")
          .replace(/([A-Za-z])'c(?=[a-z]|$)/g, "$1č")
          .replace(/([A-Za-z])'s(?=[a-z]|$)/g, "$1š")
          .replace(/([A-Za-z])'z(?=[a-z]|$)/g, "$1ž")
          .replace(/([A-Za-z])'r(?=[a-z]|$)/g, "$1ř");
        if (country_low === "ukraine" || country_low === "russia" || country_low === "belarus" || country_low === "ussr") {
          s = s
            .replace(/s'k\b/gi, "sk")
            .replace(/s'kyj\b/gi, "skyi")
            .replace(/l's'k/gi, "lsk")
            .replace(/n's'k/gi, "nsk")
            .replace(/([bcdfghjklmnpqrstvwxyz])'([bcdfghjklmnpqrstvwxyz])/gi, "$1$2")
            .replace(/l'\b/gi, "l");
        }
      }

      if (s.includes("(") && !s.includes(")"))
        s = s.replace(/\s*\([^)]*$/, "").trim();

      s = s.replace(/`/g, "").replace(/\s+/g, " ").trim();

      //Return statement
      return s;
    },

    /**
     * Folds Unicode string into lowercase ASCII for deterministic table lookups.
     * @alias stadester_name_normaliser.foldAscii
     *
     * @param {string} arg0_str
     *
     * @returns {string}
     */
    foldAscii (arg0_str) {
      //Convert from parameters
      let raw = String(arg0_str || "").trim().toLowerCase();

      //Return statement
      return raw
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/ł/g, "l")
        .replace(/đ/g, "d")
        .replace(/ø/g, "o")
        .replace(/ß/g, "ss")
        .replace(/ı/g, "i")
        .replace(/ğ/g, "g")
        .replace(/ş/g, "s")
        .replace(/ç/g, "c")
        .replace(/ö/g, "o")
        .replace(/ü/g, "u")
        .replace(/\s+/g, " ")
        .trim();
    },

    /**
     * Computes Haversine distance in kilometres between two `[lat, lng]` coordinate pairs.
     * @alias stadester_name_normaliser.haversineKm
     *
     * @param {Array<number>} arg0_a
     * @param {Array<number>} arg1_b
     *
     * @returns {number}
     */
    haversineKm (arg0_a, arg1_b) {
      //Convert from parameters
      let a = arg0_a;
      let b = arg1_b;

      //Guard clauses
      if (!Array.isArray(a) || !Array.isArray(b) || a.length < 2 || b.length < 2) return Infinity;

      //Declare local instance variables
      let d_lat = (Number(b[0]) - Number(a[0]))*Math.PI/180;
      let d_lng = (Number(b[1]) - Number(a[1]))*Math.PI/180;
      let la1 = Number(a[0])*Math.PI/180;
      let la2 = Number(b[0])*Math.PI/180;
      let h = Math.sin(d_lat*0.5)*Math.sin(d_lat*0.5) +
        Math.cos(la1)*Math.cos(la2)*Math.sin(d_lng*0.5)*Math.sin(d_lng*0.5);

      //Return statement
      return 12742*Math.asin(Math.min(1, Math.sqrt(h)));
    },

    /**
     * Returns true when a settlement label is a non-habitation test string, cave, hypogeum, quarry, kurgan, or survey code.
     * @alias stadester_name_normaliser.isJunkOrSurveyCode
     *
     * @param {string} arg0_name
     *
     * @returns {boolean}
     */
    isJunkOrSurveyCode (arg0_name) {
      //Convert from parameters
      let s = String(arg0_name || "").trim();

      //Guard clauses
      if (!s) return true;

      //Function body
      let low = s.toLowerCase();
      if (/^(?:teste\d*|unknown|unnamed|vanished|none|null|petroglyph|rock_painting|geoglifo(?:\s+\d+)?|greater valletta)$/i.test(low))
        return true;
      if (/^(?:[A-Z]{1,4}[- ]?\d{2,4}(?:[-/]\d+)?|\d{1,3}[A-Z]{1,3}[- ]?\d*|[A-Z]\.\d+\.\d+|[A-Z]-\w{1,4})$/.test(s))
        return true;
      if (/^[A-Z]\.[A-Z]\.\d+/.test(s))
        return true;

      if (this._cached_non_hab_res === undefined) {
        let cfg = this.loadMetroSubdivisions();
        let pats = (cfg && Array.isArray(cfg.non_habitation_regexes)) ? cfg.non_habitation_regexes : [];
        this._cached_non_hab_res = pats.map(function (arg0_p) { return new RegExp(arg0_p, "i"); });
      }
      for (let i = 0; i < this._cached_non_hab_res.length; i++) {
        if (this._cached_non_hab_res[i].test(s) || this._cached_non_hab_res[i].test(this.foldAscii(s)))
          return true;
      }

      //Return statement
      return false;
    },

    /**
     * Alias of `isJunkOrSurveyCode` for explicit non-habitation filtering.
     * @alias stadester_name_normaliser.isNonHabitationFeature
     *
     * @param {string} arg0_name
     *
     * @returns {boolean}
     */
    isNonHabitationFeature (arg0_name) {
      //Return statement
      return this.isJunkOrSurveyCode(arg0_name);
    },

    /**
     * Returns true when two settlement names form a protected distinct-municipality neighbour pair.
     * @alias stadester_name_normaliser.isProtectedDistinctPair
     *
     * @param {string} arg0_name_a
     * @param {string} arg1_name_b
     *
     * @returns {boolean}
     */
    isProtectedDistinctPair (arg0_name_a, arg1_name_b) {
      //Convert from parameters
      let a = this.foldAscii(arg0_name_a);
      let b = this.foldAscii(arg1_name_b);

      //Guard clauses
      if (!a || !b || a === b) return false;

      //Function body
      let cfg = this.loadMetroSubdivisions();
      let pairs = (cfg && Array.isArray(cfg.protected_distinct_neighbours)) ? cfg.protected_distinct_neighbours : [];
      for (let i = 0; i < pairs.length; i++) {
        let p0 = pairs[i][0];
        let p1 = pairs[i][1];
        if ((a === p0 && b === p1) || (a === p1 && b === p0))
          return true;
      }

      //Return statement
      return false;
    },

    /**
     * Lazily loads `config/municipal_boundaries_global/manifest.json`.
     * @alias stadester_name_normaliser.loadGlobalBoundaryManifest
     *
     * @returns {Object|null}
     */
    loadGlobalBoundaryManifest () {
      //Function body
      if (this._cached_boundary_manifest !== undefined)
        return this._cached_boundary_manifest;

      let mf_path = (typeof __dirname !== "undefined") ?
        require("path").join(__dirname, "config", "municipal_boundaries_global", "manifest.json") : "";
      try {
        let fs_mod = require("fs");
        if (mf_path && fs_mod.existsSync(mf_path)) {
          this._cached_boundary_manifest = JSON.parse(fs_mod.readFileSync(mf_path, "utf8"));
        } else {
          this._cached_boundary_manifest = null;
        }
      } catch (e) {
        console.error("[stadester_name_normaliser] Failed to load global boundary manifest:", e);
        this._cached_boundary_manifest = null;
      }

      //Return statement
      return this._cached_boundary_manifest;
    },

    /**
     * Lazily loads a specific regional boundary shard from `config/municipal_boundaries_global/`.
     * @alias stadester_name_normaliser.loadGlobalBoundaryShard
     *
     * @param {string} arg0_file
     *
     * @returns {Object|null}
     */
    loadGlobalBoundaryShard (arg0_file) {
      //Convert from parameters
      let file_name = String(arg0_file || "");

      //Guard clauses
      if (!file_name) return null;
      if (this._cached_boundary_shards[file_name] !== undefined)
        return this._cached_boundary_shards[file_name];

      //Function body
      let sp = (typeof __dirname !== "undefined") ?
        require("path").join(__dirname, "config", "municipal_boundaries_global", file_name) : "";
      try {
        let fs_mod = require("fs");
        if (sp && fs_mod.existsSync(sp)) {
          this._cached_boundary_shards[file_name] = JSON.parse(fs_mod.readFileSync(sp, "utf8"));
        } else {
          this._cached_boundary_shards[file_name] = null;
        }
      } catch (e) {
        console.error(`[stadester_name_normaliser] Failed to load boundary shard ${file_name}:`, e);
        this._cached_boundary_shards[file_name] = null;
      }

      //Return statement
      return this._cached_boundary_shards[file_name];
    },

    /**
     * Lazily loads `config/historical_municipal_amalgamations.json5`.
     * @alias stadester_name_normaliser.loadHistoricalAmalgamations
     *
     * @returns {Object|null}
     */
    loadHistoricalAmalgamations () {
      //Function body
      if (this._cached_amalg_cfg !== undefined)
        return this._cached_amalg_cfg;

      let cfg_path = (typeof __dirname !== "undefined") ?
        require("path").join(__dirname, "config", "historical_municipal_amalgamations.json5") : "";
      try {
        let fs_mod = require("fs");
        let j5_mod = global.JSON5 || require("json5");
        if (cfg_path && fs_mod.existsSync(cfg_path)) {
          this._cached_amalg_cfg = j5_mod.parse(fs_mod.readFileSync(cfg_path, "utf8"));
        } else {
          this._cached_amalg_cfg = null;
        }
      } catch (e) {
        console.error("[stadester_name_normaliser] Failed to load historical_municipal_amalgamations.json5:", e);
        this._cached_amalg_cfg = null;
      }

      //Return statement
      return this._cached_amalg_cfg;
    },

    /**
     * Lazily loads `config/metropolitan_subdivisions.json5`.
     * @alias stadester_name_normaliser.loadMetroSubdivisions
     *
     * @returns {Object|null}
     */
    loadMetroSubdivisions () {
      //Function body
      if (this._cached_metro_cfg !== undefined)
        return this._cached_metro_cfg;

      let cfg_path = (typeof __dirname !== "undefined") ?
        require("path").join(__dirname, "config", "metropolitan_subdivisions.json5") : "";
      try {
        let fs_mod = require("fs");
        let j5_mod = global.JSON5 || require("json5");
        if (cfg_path && fs_mod.existsSync(cfg_path)) {
          this._cached_metro_cfg = j5_mod.parse(fs_mod.readFileSync(cfg_path, "utf8"));
        } else {
          this._cached_metro_cfg = null;
        }
      } catch (e) {
        console.error("[stadester_name_normaliser] Failed to load metropolitan_subdivisions.json5:", e);
        this._cached_metro_cfg = null;
      }

      //Return statement
      return this._cached_metro_cfg;
    },

    /**
     * Full deterministic name sanitisation: splits comma-joined alias lists, decodes haceks, strips statistical wrappers, and applies locale Title Case.
     * @alias stadester_name_normaliser.normaliseCityName
     *
     * @param {string} arg0_name
     * @param {string} [arg1_country]
     *
     * @returns {{ extra_aliases: Array<string>, name: string }}
     */
    normaliseCityName (arg0_name, arg1_country) {
      //Convert from parameters
      let country = String(arg1_country || "").trim();
      let raw = String(arg0_name || "").trim();

      //Guard clauses
      if (!raw) return { extra_aliases: [], name: "" };

      //Declare local instance variables
      let extra_aliases = [];
      let working = raw;

      //Function body
      if (working.includes(",") && !/,\s*(?:Al|El|As|Ash|Ar|Az|Ad|An|At|Le|La|Les|L'|Los|Las|Il|Lo|De|Den|Het|Der|Die|Das|The)$/i.test(working)) {
        let parts = working.split(",").map(function (arg0_p) { return arg0_p.trim(); }).filter(Boolean);
        if (parts.length >= 2 && parts[0].length >= 2) {
          working = parts[0];
          for (let i = 1; i < parts.length; i++)
            if (parts[i].length >= 2) extra_aliases.push(parts[i]);
        }
      }

      working = working.replace(/\s*\(mod_[a-z0-9_]+\)\s*/gi, " ").trim();
      working = this.decodeHaceksAndQuotes(working, country);
      working = this.cleanStatisticalWrapper(working, country);
      working = this.toLocaleTitleCase(working);

      //Return statement
      return { extra_aliases: extra_aliases, name: working };
    },

    /**
     * Normalises country strings to canonical lowercase names for boundary/subdivision matching.
     * @alias stadester_name_normaliser.normaliseCountryName
     *
     * @param {string} arg0_country
     *
     * @returns {string}
     */
    normaliseCountryName (arg0_country) {
      //Convert from parameters
      let c = this.foldAscii(arg0_country);

      //Return statement
      return COUNTRY_ALIASES[c] || c;
    },

    /**
     * Resolves a Class 3 historically independent municipality later annexed at a documented `annexation_year`.
     * @alias stadester_name_normaliser.resolveHistoricalAmalgamation
     *
     * @param {string} arg0_name
     * @param {string} [arg1_country]
     * @param {Array<number>} [arg2_coords]
     *
     * @returns {{ annexation_year: number, parent_coords: Array<number>|null, parent_is_capital: boolean, parent_name: string }|null}
     */
    resolveHistoricalAmalgamation (arg0_name, arg1_country, arg2_coords) {
      //Convert from parameters
      let coords = Array.isArray(arg2_coords) ? arg2_coords : [];
      let country_low = this.normaliseCountryName(arg1_country);
      let lat = Number(coords[0]);
      let lng = Number(coords[1]);
      let raw = String(arg0_name || "").trim();

      //Guard clauses
      if (!raw) return null;

      //Function body
      let fold = this.foldAscii(raw.replace(/\s*\(mod_[a-z0-9_]+\)\s*/gi, " ").trim());
      let cfg = this.loadHistoricalAmalgamations();
      let list = (cfg && Array.isArray(cfg.amalgamations)) ? cfg.amalgamations : [];

      for (let i = 0; i < list.length; i++) {
        let item = list[i];
        if (!item) continue;
        if (country_low && this.normaliseCountryName(item.country) !== country_low) continue;
        let formers = Array.isArray(item.former_municipalities) ? item.former_municipalities : [];
        if (!formers.includes(fold)) continue;
        if (Number.isFinite(lat) && Number.isFinite(lng) && Array.isArray(item.parent_coords) && Number.isFinite(item.max_radius_km)) {
          if (this.haversineKm([lat, lng], item.parent_coords) > item.max_radius_km)
            continue;
        }
        return {
          annexation_year: Number(item.annexation_year),
          parent_coords: Array.isArray(item.parent_coords) ? item.parent_coords.slice() : null,
          parent_is_capital: Boolean(item.parent_is_capital),
          parent_name: item.parent_name
        };
      }

      //Return statement
      return null;
    },

    /**
     * Resolves `[lat, lng]` globally to its municipal polygon across all regional shards in `municipal_boundaries_global/`.
     * @alias stadester_name_normaliser.resolveMunicipalBoundary
     *
     * @param {number} arg0_lat
     * @param {number} arg1_lng
     * @param {string} [arg2_country]
     *
     * @returns {{ area_km2: number, boundary_scope: string, centroid: Array<number>, id: string, is_capital: boolean, name: string }|null}
     */
    resolveMunicipalBoundary (arg0_lat, arg1_lng, arg2_country) {
      //Convert from parameters
      let country_norm = this.normaliseCountryName(arg2_country);
      let lat = Number(arg0_lat);
      let lng = Number(arg1_lng);

      //Guard clauses
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
      if (lat < -90.0 || lat > 90.0 || lng < -180.0 || lng > 180.0) return null;

      //Function body
      let mf = this.loadGlobalBoundaryManifest();
      if (!mf || !Array.isArray(mf.shards)) return null;

      let pointInRing = function (arg0_x, arg1_y, arg2_ring) {
        let inside = false;
        for (let i = 0, j = arg2_ring.length - 1; i < arg2_ring.length; j = i++) {
          let xi = arg2_ring[i][0];
          let yi = arg2_ring[i][1];
          let xj = arg2_ring[j][0];
          let yj = arg2_ring[j][1];
          let inter = ((yi > arg1_y) !== (yj > arg1_y)) &&
            (arg0_x < (xj - xi)*(arg1_y - yi)/((yj - yi) || 1e-12) + xi);
          if (inter) inside = !inside;
        }
        return inside;
      };

      for (let s = 0; s < mf.shards.length; s++) {
        let sh_meta = mf.shards[s];
        let bb = sh_meta.bbox;
        if (Array.isArray(bb) && bb.length >= 4) {
          if (lat < bb[0] || lat > bb[2] || lng < bb[1] || lng > bb[3]) continue;
        }
        let idx_obj = this.loadGlobalBoundaryShard(sh_meta.file);
        if (!idx_obj || !Array.isArray(idx_obj.municipalities) || !idx_obj.grid) continue;

        let step = idx_obj.grid_step || 0.25;
        let gy = Math.floor(lat/step);
        let gx = Math.floor(lng/step);
        let cand_indices = idx_obj.grid[`${gy},${gx}`];
        if (!Array.isArray(cand_indices) || cand_indices.length === 0) continue;

        for (let c = 0; c < cand_indices.length; c++) {
          let m = idx_obj.municipalities[cand_indices[c]];
          if (!m || !m.bbox) continue;
          if (country_norm && this.normaliseCountryName(m.country) !== country_norm) continue;
          if (lng < m.bbox[0] || lng > m.bbox[2] || lat < m.bbox[1] || lat > m.bbox[3]) continue;
          for (let p = 0; p < m.rings.length; p++) {
            let outer = m.rings[p][0];
            if (outer && outer.length >= 3 && pointInRing(lng, lat, outer)) {
              return {
                area_km2: Number(m.area_km2 || 0),
                boundary_scope: m.boundary_scope || "urban_city_proper",
                centroid: m.centroid,
                id: m.id,
                is_capital: Boolean(m.is_capital),
                name: m.name
              };
            }
          }
        }
      }

      //Return statement
      return null;
    },

    /**
     * Resolves a Class 2 pure intra-municipal subdivision to its canonical parent municipality.
     * @alias stadester_name_normaliser.resolveParentMunicipality
     *
     * @param {string} arg0_name
     * @param {string} [arg1_country]
     * @param {Array<number>} [arg2_coords]
     *
     * @returns {{ effective_from_year: number|null, is_capital_override: boolean, parent_coords: Array<number>|null, parent_name: string }|null}
     */
    resolveParentMunicipality (arg0_name, arg1_country, arg2_coords) {
      //Convert from parameters
      let coords = Array.isArray(arg2_coords) ? arg2_coords : [];
      let country_low = this.normaliseCountryName(arg1_country);
      let lat = Number(coords[0]);
      let lng = Number(coords[1]);
      let raw = String(arg0_name || "").trim();

      //Guard clauses
      if (!raw) return null;

      //Function body
      let fold = this.foldAscii(raw.replace(/\s*\(mod_[a-z0-9_]+\)\s*/gi, " ").trim());
      let cfg = this.loadMetroSubdivisions();
      let parents_map = (cfg && cfg.intra_municipal_parents) ? cfg.intra_municipal_parents : {};
      let c_parents = parents_map[country_low];

      if (c_parents) {
        let p_keys = Object.keys(c_parents);
        for (let i = 0; i < p_keys.length; i++) {
          let p_obj = c_parents[p_keys[i]];
          let dists = Array.isArray(p_obj.districts) ? p_obj.districts : [];
          let matched_dist = dists.includes(fold) ||
            (country_low === "north macedonia" && fold.startsWith("skopje - ")) ||
            (country_low === "france" && /^paris\s+\d{1,2}\b/i.test(fold)) ||
            (country_low === "france" && /^lyon\s+\d{1,2}\b/i.test(fold)) ||
            (country_low === "france" && /^marseille\s+\d{1,2}\b/i.test(fold));

          if (!matched_dist) continue;
          if (Number.isFinite(lat) && Number.isFinite(lng) && Array.isArray(p_obj.coords) && Number.isFinite(p_obj.max_radius_km)) {
            if (this.haversineKm([lat, lng], p_obj.coords) > p_obj.max_radius_km)
              continue;
          }
          return {
            effective_from_year: Number.isFinite(Number(p_obj.effective_from_year)) ? Number(p_obj.effective_from_year) : null,
            is_capital_override: Boolean(p_obj.is_capital),
            parent_coords: Array.isArray(p_obj.coords) ? p_obj.coords.slice() : null,
            parent_name: p_obj.canonical_name
          };
        }
      }

      //Return statement
      return null;
    },

    /**
     * Converts ALL-UPPERCASE or all-lowercase names into locale-aware Title Case, preserving Roman numerals and particles.
     * @alias stadester_name_normaliser.toLocaleTitleCase
     *
     * @param {string} arg0_name
     *
     * @returns {string}
     */
    toLocaleTitleCase (arg0_name) {
      //Convert from parameters
      let s = String(arg0_name || "").trim();

      //Guard clauses
      if (!s) return "";

      //Function body
      let letters = s.replace(/[^A-Za-zÀ-ÖØ-öø-žĀ-ɏ]/g, "");
      if (letters.length < 3) return s;

      let is_all_upper = (letters === letters.toLocaleUpperCase("en-GB") && letters !== letters.toLocaleLowerCase("en-GB"));
      let is_all_lower = (letters === letters.toLocaleLowerCase("en-GB") && letters !== letters.toLocaleUpperCase("en-GB"));
      if (!is_all_upper && !is_all_lower) return s;

      if (is_all_upper && ROMAN_NUMERALS_RE.test(s)) return s;

      let low_special = this.foldAscii(s);
      if (low_special === "karadeniz eregli") return "Karadeniz Ereğli";
      if (low_special === "katerini") return "Kateríni";

      let tokens = s.split(/(\s+|-)/);
      let word_idx = 0;
      let out = [];

      for (let i = 0; i < tokens.length; i++) {
        let tok = tokens[i];
        if (!tok || /^\s+$/.test(tok) || tok === "-") {
          out.push(tok);
          continue;
        }
        if (is_all_upper && ROMAN_NUMERALS_RE.test(tok) && word_idx > 0) {
          out.push(tok);
          word_idx++;
          continue;
        }
        let low_tok = tok.toLocaleLowerCase("en-GB");
        if (word_idx > 0 && LOWERCASE_PARTICLES.has(low_tok)) {
          out.push(low_tok);
        } else {
          let first_char = low_tok.charAt(0).toLocaleUpperCase("en-GB");
          out.push(first_char + low_tok.slice(1));
        }
        word_idx++;
      }

      //Return statement
      return out.join("");
    }
  };

  if (typeof global !== "undefined")
    global.stadester_name_normaliser = stadester_name_normaliser;
  if (typeof module !== "undefined" && module.exports)
    module.exports = { stadester_name_normaliser: stadester_name_normaliser };
}
