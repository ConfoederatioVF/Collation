/**
 * HANDBOOK-scoped Stadestér 2.0 Partitioned Shard Synchroniser.
 *
 * Loads ONLY Project HANDBOOK's 27 verified settlement gazetteers via ViscountGazetteerLoader,
 * runs the exact Stadestér UUD interpolation, metro-flattening, error-fixing, area/Angel-density/Clark
 * centre-density, and radial-buffer pipeline on HANDBOOK's entries, writes partitioned `09_handbook_1..N.json`
 * shards (<= 200 MB each) + updates ONLY HANDBOOK's block in `stadester_manifest.json` across:
 *   1. histmap/3.data_transform/population_Stadester.transform/stadester/
 *   2. histmap/5.data_visualisation/stadester/stadester_2.0/
 *   3. F:/Active Projects/Project 1436 - Dataview/data/stadester/stadester_2.0/
 * and synchronises Dataview's `all_cities_coords.json` without disturbing any sibling Viscount macro-region.
 *
 * Usage:
 *   node --max-old-space-size=12288 histmap/1.data_raw/population_regional/HANDBOOK/_shared/scripts/sync_handbook_to_dataview.js
 */
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");
let pngjs = require("pngjs");

global.fs = fs;
global.JSON5 = JSON5;
global.path = path;
global.pngjs = pngjs;

let svea_root = path.resolve(__dirname, "../../../../../..");
process.chdir(svea_root);

global.h1 = path.join(svea_root, "histmap", "1.data_raw");
global.h2 = path.join(svea_root, "histmap", "2.data_cleaning");
global.h3 = path.join(svea_root, "histmap", "3.data_transform");
global.h5 = path.join(svea_root, "histmap", "5.data_visualisation");

let st_dir = path.join(global.h2, "population_Stadester");
let audit_mod = require(path.join(svea_root, ".agents", "skills", "population-regional-study", "scripts", "viscount_entity_and_continuity_audit.js"));
let viscount_entity_audit = audit_mod.viscount_entity_audit;
require(path.join(st_dir, "config", "stadester_config.js"));
require(path.join(st_dir, "StadesterPartitionIO.js"));
require(path.join(st_dir, "ViscountGazetteerLoader.js"));
require(path.join(st_dir, "stadester_uud_sources.js"));
require(path.join(st_dir, "stadester_uud.js"));
require(path.join(st_dir, "stadester_uud_fixes.js"));
require(path.join(st_dir, "stadester_ghs_pop.js"));
require(path.join(st_dir, "stadester_density.js"));
require(path.join(st_dir, "population_Stadester.js"));

//Initialise functions
{
  let handbook_dataview_sync = {
    /**
     * Replaces ONLY HANDBOOK's `09_handbook*.json` shard files and updates HANDBOOK's entry
     * in `stadester_manifest.json` inside `arg0_target_dir`, leaving all 13 sibling regions untouched.
     * @alias handbook_dataview_sync.updateHandbookShardsInDir
     *
     * @param {string} arg0_target_dir
     * @param {Array<Array>} arg1_entries
     * @param {number} arg2_max_bytes
     *
     * @returns {Object}
     */
    updateHandbookShardsInDir (arg0_target_dir, arg1_entries, arg2_max_bytes) {
      //Convert from parameters
      let entries = arg1_entries;
      let max_bytes = Number(arg2_max_bytes) || 209715200;
      let target_dir = path.resolve(arg0_target_dir);

      //Declare local instance variables
      let existing_files;
      let manifest_obj;
      let manifest_path = path.join(target_dir, "stadester_manifest.json");
      let shard_res;

      //Guard clauses
      if (!fs.existsSync(target_dir)) {
        console.error(`[HandbookDataviewSync] Target directory missing: ${target_dir}`);
        return null;
      }

      //Function body
      //Remove old 09_handbook*.json files ONLY
      existing_files = fs.readdirSync(target_dir);
      for (let i = 0; i < existing_files.length; i++) {
        let f_name = existing_files[i];
        if (/^09_handbook(?:_\d+)?\.json$/i.test(f_name)) {
          try {
            fs.unlinkSync(path.join(target_dir, f_name));
          } catch (e) {}
        }
      }

      shard_res = StadesterPartitionIO.streamWriteJsonShard(target_dir, "09_handbook", entries, max_bytes);

      if (fs.existsSync(manifest_path)) {
        manifest_obj = JSON.parse(fs.readFileSync(manifest_path, "utf8"));
        let regions = Array.isArray(manifest_obj.regions) ? manifest_obj.regions : [];
        let found = false;
        let total_entries = 0;

        for (let i = 0; i < regions.length; i++) {
          if (regions[i].key === "HANDBOOK") {
            regions[i].bytes = shard_res.bytes;
            regions[i].count = entries.length;
            regions[i].files = shard_res.files;
            found = true;
          }
          total_entries += Number(regions[i].count) || 0;
        }
        if (!found) {
          regions.push({
            bytes: shard_res.bytes,
            count: entries.length,
            files: shard_res.files,
            key: "HANDBOOK",
            order: 9,
            slug: "handbook",
            z_priority: 9
          });
          total_entries += entries.length;
        }
        manifest_obj.generated_at = new Date().toISOString();
        manifest_obj.total_entries = total_entries;
        fs.writeFileSync(manifest_path, JSON.stringify(manifest_obj, null, 2), "utf8");
      }

      console.log(`- Synced HANDBOOK -> ${target_dir}: ${entries.length} settlements across ${shard_res.files.length} shard(s) (${(shard_res.bytes/(1024*1024)).toFixed(2)} MB): [${shard_res.files.join(", ")}]`);

      //Return statement
      return shard_res;
    },

    /**
     * Cross-chapter deduplication eliminating variant-spelling/exonym pairs (<= 25.5 km) and
     * same-country modern twins (<= 1.65 km) across all 27 merged HANDBOOK chapters before
     * Stadestér UUD interpolation so every 09_handbook_1..N.json shard passes Gatekeeper A cleanly.
     * @alias handbook_dataview_sync.dedupCrossChapter
     *
     * @param {Object} arg0_uud_obj
     *
     * @returns {Object}
     */
    dedupCrossChapter (arg0_uud_obj) {
      //Convert from parameters
      let uud_obj = arg0_uud_obj;

      //Declare local instance variables
      let grid_tight = new Map();
      let grid_wide = new Map();
      let items = [];
      let kept_obj = {};
      let keys = Object.keys(uud_obj);
      let merged_count = 0;
      let profiles = viscount_entity_audit.loadSkillProfiles(svea_root);

      //Function body
      for (let i = 0; i < keys.length; i++) {
        let k = keys[i];
        let rec = uud_obj[k];
        if (!rec || !Array.isArray(rec.coords) || rec.coords.length < 2 || !rec.population) continue;
        let la = Number(rec.coords[0]);
        let lo = Number(rec.coords[1]);
        if (!Number.isFinite(la) || !Number.isFinite(lo)) continue;
        let pop_ks = Object.keys(rec.population);
        let max_y = -99999;
        let peak_v = 0;
        for (let x = 0; x < pop_ks.length; x++) {
          let yi = Number(pop_ks[x]);
          let pv = Number(rec.population[pop_ks[x]]) || 0;
          if (pv > 0) {
            if (yi > max_y) max_y = yi;
            if (pv > peak_v) peak_v = pv;
          }
        }
        let nm = String(rec.name || "").trim();
        let ctry = String(rec.country || "").trim();
        let stem = viscount_entity_audit.normaliseEntityStem(nm);
        items.push({ ctry: ctry, is_mod: max_y >= 1950, k: k, la: la, lo: lo, max_y: max_y, nm: nm, peak_v: peak_v, rec: rec, stem: stem });
      }

      //Sort descending by modern status, clean canonical naming (no unclosed parentheticals), then peak population
      items.sort(function (arg0_a, arg1_b) {
        if (arg0_a.is_mod !== arg1_b.is_mod) return arg1_b.is_mod ? 1 : -1;
        let a_unclosed = arg0_a.nm.includes("(") && !arg0_a.nm.includes(")");
        let b_unclosed = arg1_b.nm.includes("(") && !arg1_b.nm.includes(")");
        if (a_unclosed !== b_unclosed) return a_unclosed ? 1 : -1;
        return arg1_b.peak_v - arg0_a.peak_v;
      });

      let havKm = function (arg0_la1, arg1_lo1, arg2_la2, arg3_lo2) {
        let d_la = (arg2_la2 - arg0_la1)*Math.PI/180;
        let d_lo = (arg3_lo2 - arg1_lo1)*Math.PI/180;
        let r1 = arg0_la1*Math.PI/180;
        let r2 = arg2_la2*Math.PI/180;
        let a = Math.sin(d_la/2)*Math.sin(d_la/2) + Math.cos(r1)*Math.cos(r2)*Math.sin(d_lo/2)*Math.sin(d_lo/2);
        return 6371*2*Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      };

      for (let i = 0; i < items.length; i++) {
        let it = items[i];
        let tx = Math.floor(it.la*16);
        let ty = Math.floor(it.lo*16);
        let gx = Math.floor(it.la*2);
        let gy = Math.floor(it.lo*2);
        let target = null;

        //1. Tight check (<= 1.65 km same-country modern twins)
        if (it.is_mod) {
          for (let dx = -1; dx <= 1 && !target; dx++) {
            for (let dy = -1; dy <= 1 && !target; dy++) {
              let bucket = grid_tight.get(`${it.ctry}|${tx + dx}|${ty + dy}`);
              if (!bucket) continue;
              for (let x = 0; x < bucket.length; x++) {
                let prev = bucket[x];
                if (!prev.is_mod) continue;
                if (Math.abs(it.la - prev.la) > 0.025 || Math.abs(it.lo - prev.lo) > 0.032) continue;
                if (havKm(it.la, it.lo, prev.la, prev.lo) <= 1.65) {
                  target = prev;
                  break;
                }
              }
            }
          }
        }

        //2. Wide check (<= 25.5 km country-agnostic variant-spelling/exonym duplicates on 0.50 deg grid)
        if (!target) {
          for (let dx = -1; dx <= 1 && !target; dx++) {
            for (let dy = -1; dy <= 1 && !target; dy++) {
              let bucket = grid_wide.get(`${gx + dx}|${gy + dy}`);
              if (!bucket) continue;
              for (let x = 0; x < bucket.length; x++) {
                let prev = bucket[x];
                if (Math.abs(it.la - prev.la) > 0.25 || Math.abs(it.lo - prev.lo) > 0.45) continue;
                let dkm = havKm(it.la, it.lo, prev.la, prev.lo);
                if (dkm > 25.5) continue;
                let same_stem_or_exo = (
                  (it.stem && prev.stem && it.stem === prev.stem) ||
                  viscount_entity_audit.areEquivalentExonyms(it.nm, prev.nm, profiles)
                );
                let is_dup = same_stem_or_exo && (it.nm.toLowerCase() !== prev.nm.toLowerCase() || dkm <= 5.5);
                if (is_dup) {
                  target = prev;
                  break;
                }
              }
            }
          }
        }

        if (target) {
          //Merge uncovered population years & alternate names into canonical target
          let p_keys = Object.keys(it.rec.population);
          for (let x = 0; x < p_keys.length; x++) {
            let yk = p_keys[x];
            if (target.rec.population[yk] === undefined) {
              if (!target.rec.foundation_year || Number(yk) >= Number(target.rec.foundation_year))
                target.rec.population[yk] = it.rec.population[yk];
            }
          }
          if (!Array.isArray(target.rec.other_names)) target.rec.other_names = [];
          if (it.nm && it.nm !== target.nm && !target.rec.other_names.includes(it.nm))
            target.rec.other_names.push(it.nm);
          merged_count++;
        } else {
          kept_obj[it.k] = it.rec;
          let tk = `${it.ctry}|${tx}|${ty}`;
          let wk = `${gx}|${gy}`;
          if (!grid_tight.has(tk)) grid_tight.set(tk, []);
          grid_tight.get(tk).push(it);
          if (!grid_wide.has(wk)) grid_wide.set(wk, []);
          grid_wide.get(wk).push(it);
        }
      }

      console.log(`- Cross-chapter deduplication merged ${merged_count} variant/twin duplicate(s) -> ${Object.keys(kept_obj).length} clean HANDBOOK settlements.`);

      //Return statement
      return kept_obj;
    },

    /**
     * Sanitises Dataview's partitioned `city_metadata/09_handbook.json` (and HANDBOOK entries in
     * `00_capitals.json`) against orphaned keys, near-duplicate records (<= 1.55 km or <= 15.5 km
     * same-stem/exonym), suspicious monument names, and Signature B defunct-annex hijacking.
     * @alias handbook_dataview_sync.cleanHandbookCityMetadata
     *
     * @param {string} arg0_dv_dir
     * @param {Object} arg1_stadester_obj
     */
    cleanHandbookCityMetadata (arg0_dv_dir, arg1_stadester_obj) {
      //Convert from parameters
      let dv_dir = arg0_dv_dir;
      let stadester_obj = arg1_stadester_obj;

      //Declare local instance variables
      let caps_changed = false;
      let caps_path = path.join(dv_dir, "stadester_2.0", "city_metadata", "00_capitals.json");
      let hb_meta_path = path.join(dv_dir, "stadester_2.0", "city_metadata", "09_handbook.json");
      let man_path = path.join(dv_dir, "stadester_2.0", "city_metadata", "city_metadata_manifest.json");
      let monument_re = /\b(?:mastaba|de morgan'?s|pyramid of|tomb of|temple of|shrine of)\b/i;
      let profiles = viscount_entity_audit.loadSkillProfiles(svea_root);
      let shard_keys = new Set(Object.keys(stadester_obj));
      let unas_path = path.join(dv_dir, "stadester_2.0", "city_metadata", "15_unassigned.json");

      //Guard clauses
      if (!fs.existsSync(hb_meta_path) || !fs.existsSync(man_path)) return;

      //Function body
      let prec_path = path.join(svea_root, "histmap", "2.data_cleaning", "population_Stadester", "config", "viscount_precedence.json5");
      let prec_obj = JSON5.parse(fs.readFileSync(prec_path, "utf8"));
      let hb_proj = prec_obj.projects.find(function (arg0_p) { return String(arg0_p.key || "").toUpperCase() === "HANDBOOK"; });
      let hb_countries = new Set((hb_proj && Array.isArray(hb_proj.countries) ? hb_proj.countries : []).map(function (arg0_c) {
        return String(arg0_c || "").trim().toLowerCase();
      }));

      //Index modern active HANDBOOK settlements by spatial grid for canonical alignment
      let shard_grid = new Map();
      let all_sk = Object.keys(stadester_obj);
      for (let i = 0; i < all_sk.length; i++) {
        let sk = all_sk[i];
        let c = stadester_obj[sk];
        if (!c || !Array.isArray(c.coords) || c.coords.length < 2) continue;
        let lat = Number(c.coords[0]);
        let lng = Number(c.coords[1]);
        let pop = c.population || {};
        let y_list = Object.keys(pop).map(Number).filter(function (arg0_y) { return Number.isFinite(arg0_y) && Number(pop[arg0_y]) > 0; });
        let max_yr = y_list.length > 0 ? Math.max.apply(null, y_list) : -99999;
        let gk = `${Math.round(lat*2)},${Math.round(lng*2)}`;
        if (!shard_grid.has(gk)) shard_grid.set(gk, []);
        shard_grid.get(gk).push({
          key: sk,
          lat: lat,
          lng: lng,
          max_yr: max_yr,
          name: String(c.name || ""),
          stem: viscount_entity_audit.normaliseEntityStem(c.name || sk)
        });
      }

      let hasNearbyModernMatch = function (arg0_lat, arg1_lng, arg2_name, arg3_stem) {
        let gx = Math.round(arg0_lat*2);
        let gy = Math.round(arg1_lng*2);
        for (let dx = -1; dx <= 1; dx++) {
          for (let dy = -1; dy <= 1; dy++) {
            let b = shard_grid.get(`${gx + dx},${gy + dy}`);
            if (!b) continue;
            for (let z = 0; z < b.length; z++) {
              let cand = b[z];
              let d = viscount_entity_audit.haversineKm(arg0_lat, arg1_lng, cand.lat, cand.lng);
              if (d <= 25.0 && cand.max_yr >= 1950 && (cand.stem === arg3_stem || viscount_entity_audit.areEquivalentExonyms(arg2_name, cand.name, profiles)))
                return true;
            }
          }
        }
        return false;
      };

      let sanitiseHistoricalNames = function (arg0_rec) {
        let rec = arg0_rec;
        let hn = Array.isArray(rec.historical_names) ? rec.historical_names : [];
        let rec_name = String(rec.name || "").trim();
        let rec_stem = viscount_entity_audit.normaliseEntityStem(rec_name);
        if (!rec_name || hn.length === 0) return false;

        let changed = false;
        let cleaned = [];
        for (let x = 0; x < hn.length; x++) {
          let item = hn[x];
          if (!item || !item.name || !viscount_entity_audit.isValidCalendarDate(item.date)) {
            changed = true;
            continue;
          }
          let nm = String(item.name).trim();
          if (monument_re.test(nm) && !rec.verified_settlement) {
            changed = true;
            continue;
          }
          if (viscount_entity_audit.isSuspiciousToponym(nm, profiles) && !rec.verified_settlement) {
            changed = true;
            continue;
          }
          let yr = Number(String(item.date).split(".")[0]);
          cleaned.push({ date: item.date, name: nm, yr: yr });
        }

        cleaned.sort(function (arg0_a, arg1_b) { return arg0_a.yr - arg1_b.yr; });

        //Collapse consecutive identical-stem entries
        let deduped = [];
        let prev_stem = "";
        for (let x = 0; x < cleaned.length; x++) {
          let st = viscount_entity_audit.normaliseEntityStem(cleaned[x].name);
          if (prev_stem && st && st === prev_stem) {
            changed = true;
            continue;
          }
          deduped.push({ date: cleaned[x].date, name: cleaned[x].name, yr: cleaned[x].yr });
          prev_stem = st;
        }

        //Fix Signature B: if terminal historical name is < 1920 and differs from canonical modern rec.name,
        //and either rec.name appeared earlier OR a modern active (>=1950) HANDBOOK settlement matches rec.name,
        //append { date: "1920.1.1", name: rec_name } so modern settlements are never renamed to defunct mediaeval annexes.
        if (deduped.length > 0 && rec_stem) {
          let last = deduped[deduped.length - 1];
          let last_stem = viscount_entity_audit.normaliseEntityStem(last.name);
          let last_matches_rec = (last_stem === rec_stem) || viscount_entity_audit.areEquivalentExonyms(last.name, rec_name, profiles);
          if (last.yr < 1920 && !last_matches_rec) {
            let earlier_matches_rec = false;
            for (let x = 0; x < deduped.length - 1; x++) {
              let xs = viscount_entity_audit.normaliseEntityStem(deduped[x].name);
              if (xs === rec_stem || viscount_entity_audit.areEquivalentExonyms(deduped[x].name, rec_name, profiles)) {
                earlier_matches_rec = true;
                break;
              }
            }
            let lat = Array.isArray(rec.coords) ? Number(rec.coords[1]) : NaN;
            let lng = Array.isArray(rec.coords) ? Number(rec.coords[0]) : NaN;
            let is_mod_city = Number.isFinite(lat) && Number.isFinite(lng) && hasNearbyModernMatch(lat, lng, rec_name, rec_stem);
            if (earlier_matches_rec || is_mod_city) {
              deduped.push({ date: "1920.1.1", name: rec_name, yr: 1920 });
              changed = true;
            }
          }
        }

        if (deduped.length === 0) {
          deduped.push({ date: "1920.1.1", name: rec_name, yr: 1920 });
          changed = true;
        }

        if (changed) {
          rec.historical_names = deduped.map(function (arg0_e) { return { date: arg0_e.date, name: arg0_e.name }; });
        }
        return changed;
      };

      //1. Clean surgical HANDBOOK bugs in 00_capitals.json & build anchor grid
      let anchor_grid = new Map();
      let caps_arr = fs.existsSync(caps_path) ? JSON.parse(fs.readFileSync(caps_path, "utf8")) : [];
      let sigb_fixed_caps = 0;
      for (let i = 0; i < caps_arr.length; i++) {
        let r = caps_arr[i];
        if (!r || !Array.isArray(r.coords) || r.coords.length < 2) continue;
        //Fix Cherokee Nation capital New Echota (Georgia, USA at lng -84.9) mistagged as country:"Georgia"
        if (r.key === "New Echota-Georgia" && Number(r.coords[0]) < -30 && String(r.country || "").toLowerCase() === "georgia") {
          r.country = "United States";
          caps_changed = true;
        }
        let c_low = String(r.country || "").trim().toLowerCase();
        let is_hb_cap = (String(r.region_shard || "").toUpperCase() === "HANDBOOK") || (hb_countries.has(c_low) && Number(r.coords[0]) > -25);
        if (is_hb_cap) {
          if (sanitiseHistoricalNames(r)) {
            caps_changed = true;
            sigb_fixed_caps++;
          }
        }
        let lat = Number(r.coords[1]);
        let lng = Number(r.coords[0]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
        let gk = `${Math.round(lat*2)},${Math.round(lng*2)}`;
        if (!anchor_grid.has(gk)) anchor_grid.set(gk, []);
        anchor_grid.get(gk).push({ lat: lat, lng: lng, rec: r, stem: viscount_entity_audit.normaliseEntityStem(r.name) });
      }
      if (fs.existsSync(unas_path)) {
        let unas_arr = JSON.parse(fs.readFileSync(unas_path, "utf8"));
        for (let i = 0; i < unas_arr.length; i++) {
          let r = unas_arr[i];
          if (!r || !Array.isArray(r.coords) || r.coords.length < 2) continue;
          let lat = Number(r.coords[1]);
          let lng = Number(r.coords[0]);
          if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
          let gk = `${Math.round(lat*2)},${Math.round(lng*2)}`;
          if (!anchor_grid.has(gk)) anchor_grid.set(gk, []);
          anchor_grid.get(gk).push({ lat: lat, lng: lng, rec: r, stem: viscount_entity_audit.normaliseEntityStem(r.name) });
        }
      }

      //2. Clean & deduplicate 09_handbook.json
      let hb_arr = JSON.parse(fs.readFileSync(hb_meta_path, "utf8"));
      let dropped_orphans = 0;
      let dropped_susp = 0;
      let dropped_near_dups = 0;
      let sigb_fixed_hb = 0;
      let candidates = [];

      for (let i = 0; i < hb_arr.length; i++) {
        let r = hb_arr[i];
        if (!r || !Array.isArray(r.coords) || r.coords.length < 2) continue;
        let nm = String(r.name || "").trim();
        if (!nm || nm.includes("\uFFFD")) continue;
        let k_str = String(r.key || "");
        if (k_str && !shard_keys.has(k_str)) {
          dropped_orphans++;
          continue;
        }
        if ((monument_re.test(nm) || viscount_entity_audit.isSuspiciousToponym(nm, profiles)) && !r.verified_settlement) {
          dropped_susp++;
          continue;
        }
        if (sanitiseHistoricalNames(r)) sigb_fixed_hb++;
        let lat = Number(r.coords[1]);
        let lng = Number(r.coords[0]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
        let stem = viscount_entity_audit.normaliseEntityStem(nm);
        let mod_hit = hasNearbyModernMatch(lat, lng, nm, stem) ? 1 : 0;
        let clean_nm = (nm.includes("(") && !nm.includes(")")) ? 0 : 1;
        let score = mod_hit*1000 + clean_nm*100 + (Array.isArray(r.historical_names) ? r.historical_names.length*10 : 0) + (Array.isArray(r.other_names) ? r.other_names.length : 0);
        candidates.push({ lat: lat, lng: lng, rec: r, score: score, stem: stem });
      }

      candidates.sort(function (arg0_a, arg1_b) { return arg1_b.score - arg0_a.score; });

      let kept_hb = [];
      let kept_grid = new Map();
      let isNearDup = function (arg0_a, arg1_b) {
        if (Math.abs(arg0_a.lat - arg1_b.lat) > 0.16 || Math.abs(arg0_a.lng - arg1_b.lng) > 0.25) return false;
        let d_km = viscount_entity_audit.haversineKm(arg0_a.lat, arg0_a.lng, arg1_b.lat, arg1_b.lng);
        if (d_km <= 1.55) return true;
        if (d_km <= 15.5 && arg0_a.stem && arg1_b.stem && (arg0_a.stem === arg1_b.stem || viscount_entity_audit.areEquivalentExonyms(arg0_a.rec.name, arg1_b.rec.name, profiles)))
          return true;
        return false;
      };

      for (let i = 0; i < candidates.length; i++) {
        let c = candidates[i];
        let gx = Math.round(c.lat*2);
        let gy = Math.round(c.lng*2);
        let dup_target = null;

        //Check against 00_capitals.json / 15_unassigned.json anchors first
        for (let dx = -1; dx <= 1 && !dup_target; dx++) {
          for (let dy = -1; dy <= 1 && !dup_target; dy++) {
            let b = anchor_grid.get(`${gx + dx},${gy + dy}`);
            if (!b) continue;
            for (let z = 0; z < b.length; z++) {
              if (isNearDup(c, b[z])) {
                dup_target = b[z];
                break;
              }
            }
          }
        }
        if (dup_target) {
          dropped_near_dups++;
          continue;
        }

        //Check against already-kept 09_handbook.json records
        for (let dx = -1; dx <= 1 && !dup_target; dx++) {
          for (let dy = -1; dy <= 1 && !dup_target; dy++) {
            let b = kept_grid.get(`${gx + dx},${gy + dy}`);
            if (!b) continue;
            for (let z = 0; z < b.length; z++) {
              if (isNearDup(c, b[z])) {
                dup_target = b[z];
                break;
              }
            }
          }
        }
        if (dup_target) {
          if (!Array.isArray(dup_target.rec.other_names)) dup_target.rec.other_names = [];
          if (c.rec.name && c.rec.name !== dup_target.rec.name && !dup_target.rec.other_names.includes(c.rec.name))
            dup_target.rec.other_names.push(c.rec.name);
          dropped_near_dups++;
        } else {
          kept_hb.push(c.rec);
          let gk = `${gx},${gy}`;
          if (!kept_grid.has(gk)) kept_grid.set(gk, []);
          kept_grid.get(gk).push(c);
        }
      }

      if (caps_changed)
        fs.writeFileSync(caps_path, JSON.stringify(caps_arr), "utf8");
      fs.writeFileSync(hb_meta_path, JSON.stringify(kept_hb), "utf8");

      let man = JSON.parse(fs.readFileSync(man_path, "utf8"));
      let total_meta = 0;
      if (Array.isArray(man.shards)) {
        for (let i = 0; i < man.shards.length; i++) {
          if (man.shards[i].key === "HANDBOOK") man.shards[i].count = kept_hb.length;
          total_meta += Number(man.shards[i].count) || 0;
        }
      }
      man.total_entries = total_meta;
      man.generated_at = new Date().toISOString();
      fs.writeFileSync(man_path, JSON.stringify(man, null, 2), "utf8");

      console.log(
        `- Cleaned city_metadata/09_handbook.json: ${hb_arr.length} -> ${kept_hb.length} records ` +
        `(orphans=${dropped_orphans}, suspicious=${dropped_susp}, near_dups=${dropped_near_dups}, ` +
        `sigB_sanitised=${sigb_fixed_hb}+${sigb_fixed_caps}caps).`
      );
    },

    /**
     * Executes HANDBOOK-only Stadestér 2.0 compilation and synchronises to SVEA + Dataview.
     * @alias handbook_dataview_sync.run
     */
    run () {
      //Declare local instance variables
      let all_keys;
      let entries = [];
      let raw_folder = path.join(global.h1, "population_Stadester") + path.sep;
      let stadester_obj;
      let target_dirs;
      let uud_obj;

      //Function body
      console.log("[1/5] Loading HANDBOOK 27-chapter settlement gazetteers via ViscountGazetteerLoader...");
      uud_obj = ViscountGazetteerLoader.getViscountRegionalObject({
        only_project: "HANDBOOK",
        project_root: svea_root
      });
      console.log(`- Loaded ${Object.keys(uud_obj).length} deduplicated HANDBOOK settlements.`);
      uud_obj = this.dedupCrossChapter(uud_obj);

      console.log("[2/5] Interpolating HYDE benchmark & annual modern population series...");
      uud_obj = population_Stadester_uud.interpolateUUD(uud_obj, {});

      console.log("[3/5] Converting UUD -> Stadestér schema & applying fixes...");
      stadester_obj = population_Stadester_uud.parseUUDToStadester(uud_obj);
      stadester_obj = population_Stadester_uud.fixStadesterErrors(stadester_obj);

      console.log("[4/5] Computing urban areas, Angel densities, Clark centre densities & radial buffers...");
      stadester_obj = population_Stadester_density.processCitiesAreas(stadester_obj, { raw_folder: raw_folder });
      stadester_obj = population_Stadester_density.cacheRadialBuffers(stadester_obj);
      if (typeof population_Stadester_ghs_pop !== "undefined" && typeof population_Stadester_ghs_pop.cleanTransientMetadata === "function")
        population_Stadester_ghs_pop.cleanTransientMetadata(stadester_obj);

      all_keys = Object.keys(stadester_obj).sort();
      for (let i = 0; i < all_keys.length; i++) {
        let k = all_keys[i];
        let obj = stadester_obj[k];
        if (!obj || typeof obj !== "object") continue;
        obj.viscount_project = "HANDBOOK";
        entries.push([k, obj]);
      }

      console.log(`[5/5] Writing partitioned 09_handbook_1..N.json shards (${entries.length} cities)...`);
      target_dirs = [
        path.join(global.h3, "population_Stadester.transform", "stadester"),
        path.join(global.h5, "stadester", "stadester_2.0"),
        "F:/Active Projects/Project 1436 - Dataview/data/stadester/stadester_2.0"
      ];
      for (let i = 0; i < target_dirs.length; i++) {
        if (fs.existsSync(target_dirs[i]))
          this.updateHandbookShardsInDir(target_dirs[i], entries, 209715200);
      }

      //Sync Dataview all_cities_coords.json, clean HANDBOOK city_metadata & invalidate legacy JSON caches
      let dv_dir = "F:/Active Projects/Project 1436 - Dataview/data/stadester";
      if (fs.existsSync(dv_dir)) {
        this.cleanHandbookCityMetadata(dv_dir, stadester_obj);
        population_Stadester.syncDataviewCityCoords(dv_dir, stadester_obj);
        let stale_caches = [
          path.join(dv_dir, "cache", "stadester_2.0_lite.json"),
          path.join(dv_dir, "cache", "stadester_2.0_indexed.json"),
          path.join(dv_dir, "cache", "stadester_city_cache.json")
        ];
        for (let i = 0; i < stale_caches.length; i++) {
          if (fs.existsSync(stale_caches[i])) {
            try { fs.unlinkSync(stale_caches[i]); } catch (e) {}
          }
        }
        console.log("- Synchronised Dataview all_cities_coords.json & cleared legacy JSON caches.");
      }
      console.log("=== HANDBOOK Stadestér 2.0 Dataview Sync COMPLETE ===");
    }
  };

  handbook_dataview_sync.run();
}
