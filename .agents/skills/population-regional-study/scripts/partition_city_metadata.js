//Import modules
let crypto = require("crypto");
let fs = require("fs");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");
let { viscount_entity_audit } = require("./viscount_entity_and_continuity_audit");

//Initialise functions
{
  let city_metadata_partitioner = {
    ARTICLE_INVERT_RE: /^(.+?),\s*(Al|El|As|Ash|Ar|Az|Ad|An|At|Le|La|Les|L'|Los|Las|El|Il|Lo|De|Den|Het|Der|Die|Das|The)$/i,
    BACKTICK_HACEK_MAP: {
      "`C": "Č", "`c": "č", "`S": "Š", "`s": "š", "`Z": "Ž", "`z": "ž",
      "`R": "Ř", "`r": "ř", "`E": "Ě", "`e": "ě", "`N": "Ň", "`n": "ň",
      "`T": "Ť", "`t": "ť", "`D": "Ď", "`d": "ď", "`U": "Ů", "`u": "ů"
    },
    REGION_SHARD_FILES: [
      { file: "01_centaur.json", key: "CENTAUR" },
      { file: "02_polaris.json", key: "POLARIS" },
      { file: "03_preta.json", key: "PRETA" },
      { file: "04_jade.json", key: "JADE" },
      { file: "05_indus.json", key: "INDUS" },
      { file: "06_castle.json", key: "CASTLE" },
      { file: "07_mandala.json", key: "MANDALA" },
      { file: "08_saray.json", key: "SARAY" },
      { file: "09_handbook.json", key: "HANDBOOK" },
      { file: "10_magnetic.json", key: "MAGNETIC" },
      { file: "11_quipu.json", key: "QUIPU" },
      { file: "12_jaguar.json", key: "JAGUAR" },
      { file: "13_austral.json", key: "AUSTRAL" },
      { file: "14_nicethi.json", key: "NICETHI" }
    ],

    /**
     * Repairs common legacy GeoNames/Stadestér encoding artifacts (backtick haceks, comma-inverted articles, parentheticals).
     * @alias city_metadata_partitioner.cleanLegacyName
     *
     * @param {string} arg0_raw
     *
     * @returns {string}
     */
    cleanLegacyName (arg0_raw) {
      //Convert from parameters
      let s = String(arg0_raw || "").trim();

      //Guard clauses
      if (!s) return "";

      //Function body
      // Fix backtick-encoded Slavic/Turkic haceks (`c -> č, `s -> š, `z -> ž, etc.)
      let keys = Object.keys(this.BACKTICK_HACEK_MAP);
      for (let i = 0; i < keys.length; i++) {
        if (s.includes(keys[i]))
          s = s.split(keys[i]).join(this.BACKTICK_HACEK_MAP[keys[i]]);
      }
      // Fix trailing backticks or standalone stray backticks (e.g. Ker`c -> Kerč / Toshkent)
      s = s.replace(/`/g, "");
      // Strip parentheticals
      s = s.replace(/\s*\([^)]*\)/g, "").trim();

      // Repair comma-inverted articles (`Mans, Le` -> `Le Mans`, `Iskandarîyah, Al` -> `Al-Iskandarîyah`)
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

      //Return statement
      return s.replace(/\s+/g, " ").trim();
    },

    /**
     * Builds a spatial index of all compiled `stadester_2.0` shard cities so every metadata entry
     * maps deterministically to its canonical regional shard (`01_centaur.json`..`14_nicethi.json`).
     * @alias city_metadata_partitioner.loadRegionalSpatialIndex
     *
     * @param {string} arg0_stadester_dir
     *
     * @returns {Map<string, Array<{ lat: number, lng: number, region_key: string, country: string }>>}
     */
    loadRegionalSpatialIndex (arg0_stadester_dir) {
      //Convert from parameters
      let stadester_dir = arg0_stadester_dir;

      //Declare local instance variables
      let grid = new Map();
      let man_path = path.join(stadester_dir, "stadester_manifest.json");

      //Guard clauses
      if (!fs.existsSync(man_path)) return grid;

      //Function body
      let man = JSON.parse(fs.readFileSync(man_path, "utf8"));
      let regions = Array.isArray(man.regions) ? man.regions : [];
      for (let i = 0; i < regions.length; i++) {
        let rkey = String(regions[i].key || "").toUpperCase();
        let files = Array.isArray(regions[i].files) ? regions[i].files : [];
        for (let x = 0; x < files.length; x++) {
          let fp = path.join(stadester_dir, files[x]);
          if (!fs.existsSync(fp)) continue;
          let obj = JSON.parse(fs.readFileSync(fp, "utf8"));
          let vals = Object.values(obj);
          for (let y = 0; y < vals.length; y++) {
            let c = vals[y];
            if (!c || !Array.isArray(c.coords) || c.coords.length < 2) continue;
            let lat = Number(c.coords[0]);
            let lng = Number(c.coords[1]);
            if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
            let gkey = `${Math.round(lat*4)},${Math.round(lng*4)}`;
            if (!grid.has(gkey)) grid.set(gkey, []);
            grid.get(gkey).push({ country: c.country || "", lat: lat, lng: lng, region_key: rkey });
          }
        }
      }

      //Return statement
      return grid;
    },

    /**
     * Parses CLI arguments.
     * @alias city_metadata_partitioner.parseCliArgs
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
        dry_run: false,
        no_backup: false,
        svea_root: ""
      };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok.startsWith("--dataview-root=")) out.dataview_root = tok.slice(16).trim();
        else if (tok.startsWith("--svea-root=")) out.svea_root = tok.slice(12).trim();
        else if (tok.startsWith("--dataset=")) out.dataset = tok.slice(10).trim();
        else if (tok === "--dry-run") out.dry_run = true;
        else if (tok === "--no-backup") out.no_backup = true;
      }

      //Return statement
      return out;
    },

    /**
     * Resolves a coordinate `[lat, lng]` to its Viscount macro-region key via nearest regional shard city (<= 150 km) or fallback bbox.
     * @alias city_metadata_partitioner.resolveRegionForCoords
     *
     * @param {number} arg0_lat
     * @param {number} arg1_lng
     * @param {Map} arg2_grid
     *
     * @returns {{ country: string, region_key: string }}
     */
    resolveRegionForCoords (arg0_lat, arg1_lng, arg2_grid) {
      //Convert from parameters
      let grid = arg2_grid;
      let lat = Number(arg0_lat);
      let lng = Number(arg1_lng);

      //Function body
      let gx = Math.round(lat*4);
      let gy = Math.round(lng*4);
      let best_d = 999999;
      let best_reg = "";
      let best_country = "";

      // Fast path: check exact 0.25-deg cell first
      let center_b = grid.get(`${gx},${gy}`);
      if (center_b) {
        for (let i = 0; i < center_b.length; i++) {
          let d_sq = (lat - center_b[i].lat)*(lat - center_b[i].lat) + (lng - center_b[i].lng)*(lng - center_b[i].lng);
          if (d_sq < best_d) {
            best_d = d_sq;
            best_reg = center_b[i].region_key;
            best_country = center_b[i].country;
            if (d_sq < 0.0025) return { country: best_country, region_key: best_reg };
          }
        }
        if (best_reg) return { country: best_country, region_key: best_reg };
      }

      for (let dx = -2; dx <= 2; dx++) {
        for (let dy = -2; dy <= 2; dy++) {
          if (dx === 0 && dy === 0) continue;
          let b = grid.get(`${gx + dx},${gy + dy}`);
          if (!b) continue;
          for (let i = 0; i < b.length; i++) {
            let d_sq = (lat - b[i].lat)*(lat - b[i].lat) + (lng - b[i].lng)*(lng - b[i].lng);
            if (d_sq < best_d) {
              best_d = d_sq;
              best_reg = b[i].region_key;
              best_country = b[i].country;
            }
          }
        }
      }
      if (best_reg && best_d <= 2.25)
        return { country: best_country, region_key: best_reg };

      // Coarse geographic fallback for remote points not yet in a compiled shard
      if (lng <= -30) {
        if (lat >= 32.5 || (lat >= 18 && lng <= -150)) return { country: "", region_key: "CENTAUR" };
        if (lat >= 7.0) return { country: "", region_key: "JAGUAR" };
        if (lng <= -68.0 || lat <= -34.0) return { country: "", region_key: "QUIPU" };
        return { country: "", region_key: "PRETA" };
      }
      if (lng >= 110 && lat <= 0) return { country: "", region_key: "AUSTRAL" };
      if (lat <= 20 && lng >= -25 && lng <= 55) return { country: "", region_key: "NICETHI" };
      if (lat >= 35 && lng >= -25 && lng <= 28) return { country: "", region_key: "MAGNETIC" };
      if (lat >= 44 && lng > 28 && lng <= 180) return { country: "", region_key: "POLARIS" };

      //Return statement
      return { country: "", region_key: "UNASSIGNED" };
    },

    /**
     * Partitions monolithic `city_metadata.json` + unifies `state_capitals.json` into `city_metadata/`
     * (`city_metadata_manifest.json`, `00_capitals.json`, `01_centaur.json`..`14_nicethi.json`, `15_unassigned.json`).
     * @alias city_metadata_partitioner.runPartition
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Object}
     */
    runPartition (arg0_options) {
      //Convert from parameters
      let opts = (arg0_options) ? arg0_options : {};
      let dataset_id = String(opts.dataset || "stadester_2.0").replace(/\.json$/i, "");
      let svea_root = opts.svea_root ? path.resolve(opts.svea_root) : (viscount_audit_utils.findSveaRoot(__dirname) || path.resolve(__dirname, "../../../.."));
      let dataview_root = opts.dataview_root ? path.resolve(opts.dataview_root) :
        (process.env.DATAVIEW_ROOT ? path.resolve(process.env.DATAVIEW_ROOT) : path.resolve(svea_root, "../Project 1436 - Dataview"));

      //Declare local instance variables
      let stadester_dir = path.join(dataview_root, "data/stadester", dataset_id);
      let mono_path = path.join(stadester_dir, "city_metadata.json");
      let capitals_path = path.join(dataview_root, "data/stadester/state_capitals.json");
      let out_dir = path.join(stadester_dir, "city_metadata");
      let backup_path = path.join(stadester_dir, "city_metadata.legacy_backup.json");

      //Guard clauses
      if (!fs.existsSync(mono_path)) {
        console.error(`[partition_city_metadata] Monolithic city_metadata.json not found: ${mono_path}`);
        return { success: false };
      }

      //Function body
      let raw_meta = JSON.parse(fs.readFileSync(mono_path, "utf8"));
      let raw_capitals = fs.existsSync(capitals_path) ? JSON.parse(fs.readFileSync(capitals_path, "utf8")) : [];
      let reg_grid = this.loadRegionalSpatialIndex(stadester_dir);

      // 1. Clean and deduplicate monolithic metadata entries (merge exact <= 1.5 km same-stem collisions)
      let dedup_grid = new Map();
      let cleaned_entries = [];
      let repaired_names = 0;
      let merged_collisions = 0;
      let dropped_junk = 0;

      for (let i = 0; i < raw_meta.length; i++) {
        let entry = raw_meta[i];
        if (!entry || !Array.isArray(entry.coords) || entry.coords.length < 2) { dropped_junk++; continue; }
        let lng = Number(entry.coords[0]);
        let lat = Number(entry.coords[1]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) { dropped_junk++; continue; }

        let orig_name = String(entry.name || "").trim();
        // Drop street-address junk (`BRDR. Gram, Danmarksgade 16, 6500 Vojens.`)
        if ((orig_name.match(/,/g) || []).length >= 2 && /\d{3,}/.test(orig_name)) { dropped_junk++; continue; }

        let clean_name = this.cleanLegacyName(orig_name);
        if (!clean_name || clean_name === "0" || clean_name === "Unknown" || clean_name === "Settlement" || clean_name.includes("?") || clean_name.includes("\uFFFD")) {
          dropped_junk++;
          continue;
        }
        if (clean_name !== orig_name) repaired_names++;

        let hist = [];
        if (Array.isArray(entry.historical_names)) {
          for (let x = 0; x < entry.historical_names.length; x++) {
            let h = entry.historical_names[x];
            if (!h || typeof h !== "object") continue;
            let hn = this.cleanLegacyName(h.name || "");
            let hd = String(h.date || "").trim();
            if (!hn || !viscount_entity_audit.isValidCalendarDate(hd)) continue;
            hist.push({ date: hd, name: hn });
          }
        }
        if (hist.length === 0)
          hist.push({ date: "1900.1.1", name: clean_name });

        let others = new Set();
        if (Array.isArray(entry.other_names)) {
          for (let x = 0; x < entry.other_names.length; x++) {
            let o = this.cleanLegacyName(entry.other_names[x] || "");
            if (o && o !== clean_name && !o.includes("?") && !o.includes("\uFFFD")) others.add(o);
          }
        }
        if (orig_name !== clean_name && !orig_name.includes("`") && !orig_name.includes("?") && !this.ARTICLE_INVERT_RE.test(orig_name))
          others.add(orig_name);

        let stem = viscount_entity_audit.normaliseEntityStem(clean_name);
        let gkey = `${Math.round(lat*20)},${Math.round(lng*20)}`;
        let merged_into = null;
        for (let dx = -1; dx <= 1 && !merged_into; dx++) {
          for (let dy = -1; dy <= 1 && !merged_into; dy++) {
            let bucket = dedup_grid.get(`${Math.round(lat*20) + dx},${Math.round(lng*20) + dy}`);
            if (!bucket) continue;
            for (let b = 0; b < bucket.length; b++) {
              let cand = bucket[b];
              let d_km = viscount_audit_utils.haversineKm(lat, lng, cand.lat, cand.lng);
              if (d_km <= 1.5 && (cand.stem === stem || d_km <= 0.15)) {
                merged_into = cand;
                break;
              }
            }
          }
        }

        if (merged_into) {
          merged_collisions++;
          if (hist.length > merged_into.rec.historical_names.length)
            merged_into.rec.historical_names = hist;
          if (clean_name !== merged_into.rec.name) merged_into.others.add(clean_name);
          others.forEach(function (arg0_o) { merged_into.others.add(arg0_o); });
          continue;
        }

        let reg_info = this.resolveRegionForCoords(lat, lng, reg_grid);
        let rec = {
          coords: [Number(lng.toFixed(5)), Number(lat.toFixed(5))],
          country: entry.country || reg_info.country || "",
          historical_names: hist,
          name: clean_name,
          region_shard: reg_info.region_key
        };
        if (entry.capital && typeof entry.capital === "object") rec.capital = Object.assign({}, entry.capital);
        if (entry.capitals && typeof entry.capitals === "object" && !rec.capital) rec.capital = Object.assign({}, entry.capitals);
        if (entry.key) rec.key = entry.key;
        if (entry.verified_settlement) rec.verified_settlement = true;

        let item = { lat: lat, lng: lng, others: others, rec: rec, stem: stem };
        cleaned_entries.push(item);
        if (!dedup_grid.has(gkey)) dedup_grid.set(gkey, []);
        dedup_grid.get(gkey).push(item);
      }

      // Finalise other_names arrays
      for (let i = 0; i < cleaned_entries.length; i++) {
        let it = cleaned_entries[i];
        it.others.delete(it.rec.name);
        if (it.others.size > 0) it.rec.other_names = Array.from(it.others);
      }

      // 2. Unify `state_capitals.json` (`Record<state_id, { acapital, timeline: [{ city, key, start, stop }] }>`)
      //    with Priority Tier 0 (`00_capitals.json`) so every state capital groups capital timelines with canonical names
      let capital_indices = new Set();
      let capitals_out = [];
      let capital_by_key_or_name = new Map();

      // Index cleaned_entries by key and normalised stem for fast capital matching
      let cleaned_by_key = new Map();
      let cleaned_by_stem = new Map();
      for (let i = 0; i < cleaned_entries.length; i++) {
        let it = cleaned_entries[i];
        if (it.rec.key) cleaned_by_key.set(String(it.rec.key).toLowerCase(), i);
        if (it.stem) {
          if (!cleaned_by_stem.has(it.stem)) cleaned_by_stem.set(it.stem, []);
          cleaned_by_stem.get(it.stem).push(i);
        }
        // Also capture any existing capital timelines embedded in legacy city_metadata.json
        if ((it.rec.capital && typeof it.rec.capital === "object" && Object.keys(it.rec.capital).length > 0) ||
            (Array.isArray(it.rec.capital_records) && it.rec.capital_records.length > 0)) {
          capital_indices.add(i);
        }
      }

      if (raw_capitals && typeof raw_capitals === "object" && !Array.isArray(raw_capitals)) {
        let state_ids = Object.keys(raw_capitals);
        for (let s = 0; s < state_ids.length; s++) {
          let sid_str = state_ids[s];
          let sc = raw_capitals[sid_str];
          if (!sc || sc.acapital || !Array.isArray(sc.timeline)) continue;
          let sid_num = Number(sid_str);

          for (let t = 0; t < sc.timeline.length; t++) {
            let item = sc.timeline[t];
            if (!item || !item.start) continue;
            let cap_key = String(item.key || "").trim();
            let cap_city = this.cleanLegacyName(item.city || cap_key.split("-")[0] || "");
            let cap_stem = viscount_entity_audit.normaliseEntityStem(cap_city);
            if (!cap_city && !cap_key) continue;

            let matched_idx = -1;
            if (cap_key && cleaned_by_key.has(cap_key.toLowerCase())) {
              matched_idx = cleaned_by_key.get(cap_key.toLowerCase());
            } else if (cap_stem && cleaned_by_stem.has(cap_stem)) {
              let cands = cleaned_by_stem.get(cap_stem);
              matched_idx = cands[0];
              if (cands.length > 1 && cap_key) {
                let key_low = cap_key.toLowerCase();
                for (let c_i = 0; c_i < cands.length; c_i++) {
                  let c_rec = cleaned_entries[cands[c_i]].rec;
                  if (c_rec.country && key_low.includes(String(c_rec.country).toLowerCase())) {
                    matched_idx = cands[c_i];
                    break;
                  }
                }
              }
            }

            if (matched_idx >= 0) {
              capital_indices.add(matched_idx);
              let target = cleaned_entries[matched_idx].rec;
              if (!target.capital || typeof target.capital !== "object") target.capital = {};
              target.capital[String(item.start).trim()] = Number.isFinite(sid_num) ? sid_num : sid_str;
              if (item.stop) {
                let stop_k = String(item.stop).trim();
                if (target.capital[stop_k] === undefined) target.capital[stop_k] = null;
              }
              if (cap_city && cap_city !== target.name) {
                if (!Array.isArray(target.other_names)) target.other_names = [];
                if (!target.other_names.includes(cap_city)) target.other_names.push(cap_city);
              }
            } else {
              let cl_key = (cap_key || cap_stem || cap_city).toLowerCase();
              if (!capital_by_key_or_name.has(cl_key)) {
                capital_by_key_or_name.set(cl_key, {
                  capital: {},
                  key: cap_key || undefined,
                  name: cap_city || cap_key
                });
              }
              let stub = capital_by_key_or_name.get(cl_key);
              stub.capital[String(item.start).trim()] = Number.isFinite(sid_num) ? sid_num : sid_str;
              if (item.stop && stub.capital[String(item.stop).trim()] === undefined)
                stub.capital[String(item.stop).trim()] = null;
            }
          }
        }
      }

      // 3. Bucket records into `00_capitals.json` + 14 regional shards + `15_unassigned.json`
      let shards = {};
      for (let i = 0; i < this.REGION_SHARD_FILES.length; i++)
        shards[this.REGION_SHARD_FILES[i].key] = [];
      shards.UNASSIGNED = [];

      for (let i = 0; i < cleaned_entries.length; i++) {
        let rec = cleaned_entries[i].rec;
        if (capital_indices.has(i)) {
          capitals_out.push(rec);
        } else {
          let rk = rec.region_shard && shards[rec.region_shard] ? rec.region_shard : "UNASSIGNED";
          shards[rk].push(rec);
        }
      }

      // Sort deterministically by name + coords
      let sortFn = function (arg0_a, arg1_b) {
        let na = String(arg0_a.name || "");
        let nb = String(arg1_b.name || "");
        if (na < nb) return -1;
        if (na > nb) return 1;
        return Number(arg0_a.coords[1]) - Number(arg1_b.coords[1]);
      };
      capitals_out.sort(sortFn);
      Object.keys(shards).forEach(function (arg0_k) { shards[arg0_k].sort(sortFn); });

      let manifest_shards = [];
      let writeShard = function (arg0_file, arg1_key, arg2_tier, arg3_arr) {
        let json_str = JSON.stringify(arg3_arr, null, 2);
        let sha = crypto.createHash("sha256").update(json_str).digest("hex");
        if (!opts.dry_run) {
          fs.mkdirSync(out_dir, { recursive: true });
          fs.writeFileSync(path.join(out_dir, arg0_file), json_str, "utf8");
        }
        manifest_shards.push({
          count: arg3_arr.length,
          file: arg0_file,
          key: arg1_key,
          sha256: sha,
          tier: arg2_tier
        });
      };

      if (!opts.dry_run && !opts.no_backup && !fs.existsSync(backup_path))
        fs.copyFileSync(mono_path, backup_path);

      writeShard("00_capitals.json", "CAPITALS", 0, capitals_out);
      for (let i = 0; i < this.REGION_SHARD_FILES.length; i++) {
        let r = this.REGION_SHARD_FILES[i];
        writeShard(r.file, r.key, 1, shards[r.key]);
      }
      writeShard("15_unassigned.json", "UNASSIGNED", 2, shards.UNASSIGNED);

      let manifest = {
        dataset: dataset_id,
        generated_at_gmt0: new Date().toISOString(),
        schema_version: "2.0",
        shards: manifest_shards,
        stats: {
          capitals_count: capitals_out.length,
          dropped_junk: dropped_junk,
          input_count: raw_meta.length,
          merged_collisions: merged_collisions,
          output_count: capitals_out.length + Object.values(shards).reduce(function (arg0_a, arg1_b) { return arg0_a + arg1_b.length; }, 0),
          repaired_names: repaired_names
        }
      };

      if (!opts.dry_run)
        fs.writeFileSync(path.join(out_dir, "city_metadata_manifest.json"), JSON.stringify(manifest, null, 2), "utf8");

      console.log(`[partition_city_metadata] Partitioned ${raw_meta.length} -> ${manifest.stats.output_count} records (${capitals_out.length} capitals in 00_capitals.json, ${merged_collisions} collisions merged, ${repaired_names} names repaired, ${dropped_junk} junk dropped).`);

      //Return statement
      return { manifest: manifest, out_dir: out_dir, success: true };
    }
  };

  if (require.main === module) {
    let cli = city_metadata_partitioner.parseCliArgs(process.argv.slice(2));
    let res = city_metadata_partitioner.runPartition(cli);
    process.exit(res.success ? 0 : 1);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { city_metadata_partitioner: city_metadata_partitioner };
  }
}
