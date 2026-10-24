(function () {
  if (!global.ve) global.ve = { registry: { settings: {} } };
  let fs = (typeof require !== "undefined") ? require("fs") : global.fs;
  let json5 = (typeof require !== "undefined") ? require("json5") : (global.JSON5 || global.json5);
  let path = (typeof require !== "undefined") ? require("path") : global.path;
  let turf = global.turf || ((typeof require !== "undefined") ? require(path.resolve(process.cwd(), "UF/js/geospatiale/turf.min.js")) : null);

  if (typeof require !== "undefined") {
    try { require(path.resolve(process.cwd(), "UF/js/date/date_basic.js")); } catch (e) {}
    try { require(path.resolve(process.cwd(), "UF/js/date/date_conversion.js")); } catch (e) {}
  }


  /**
   * PolitiesAtlasJoin executes a spatio-temporal join and topological simplification
   * between atlas.naissance and Cliopatria, generating atlas_simplified.naissance.
   *
   * It maps Atlas entities down to canonical Seshat polities driven by the curated correlation
   * map, buffers joins by 1km to prevent degenerate topology, keeps parenthetical IDs intact
   * without improper merges, identifies metropoles by sovereignty rather than spurious area,
   * eliminates premature country termination, and produces sparse keyframes.
   *
   * @class PolitiesAtlasJoin
   */
  global.PolitiesAtlasJoin = class {
    static config_path = "histmap/2.data_cleaning/polities_atlas_join/polities_atlas_join.json5";



    /**
     * Cleans and validates polygon rings, ensuring closure and filtering out degenerate sliver holes.
     *
     * @param {Array<Array<number[]>>} arg0_rings
     *
     * @returns {Array<Array<number[]>>|null}
     */
    static cleanPolygonRings (arg0_rings) {
      //Convert from parameters
      let rings = arg0_rings;

      //Guard clause
      if (!rings || !rings[0] || rings[0].length < 3) return null;

      //Declare local instance variables
      let first;
      let last;
      let outer;
      let valid_rings;

      outer = rings[0].slice();
      first = outer[0];
      last = outer[outer.length - 1];
      if (first[0] !== last[0] || first[1] !== last[1]) outer.push([first[0], first[1]]);
      if (outer.length < 4) return null;

      valid_rings = [outer];
      for (let i = 1; i < rings.length; i++) {
        let r = rings[i];
        if (r && r.length >= 3) {
          let r_closed = r.slice();
          let rf = r_closed[0];
          let rl = r_closed[r_closed.length - 1];
          if (rf[0] !== rl[0] || rf[1] !== rl[1]) r_closed.push([rf[0], rf[1]]);
          if (r_closed.length >= 4) valid_rings.push(r_closed);
        }
      }

      //Return statement
      return valid_rings;
    }


    /**
     * Resolves the active state of an Atlas entity at a target timestamp.
     *
     * @param {Object} arg0_entity
     * @param {number} arg1_target_ts
     *
     * @returns {Object|null}
     */
    static getEntityStateAtTimestamp (arg0_entity, arg1_target_ts) {
      //Convert from parameters
      let entity = arg0_entity;
      let target_ts = arg1_target_ts;

      //Guard clause
      if (!entity || !entity.history) return null;

      //Declare local instance variables
      let active_geom = null;
      let active_props = {};
      let active_symbol = null;
      let is_hidden = false;
      let timestamps;

      timestamps = Object.keys(entity.history).map(Number).sort((a, b) => a - b);
      if (timestamps.length === 0 || target_ts < timestamps[0]) return null;

      for (let i = 0; i < timestamps.length; i++) {
        let ts = timestamps[i];
        if (ts > target_ts) break;

        let kf = entity.history[String(ts)];
        if (!kf) continue;

        if (kf[0] !== undefined && kf[0] !== "undefined") {
          if (kf[0] === null) {
            active_geom = null;
          } else if (kf[0].feature) {
            active_geom = kf[0].feature;
            is_hidden = false;
          }
        }

        if (kf[1] !== undefined && kf[1] !== null && kf[1] !== "undefined")
          active_symbol = Object.assign({}, active_symbol, kf[1]);

        if (kf[2] !== undefined && kf[2] !== null && kf[2] !== "undefined") {
          active_props = Object.assign({}, active_props, kf[2]);
          if (kf[2].hidden === true) {
            is_hidden = true;
            active_geom = null;
          }
        }
      }

      if (is_hidden || !active_geom || !active_geom.geometry) return null;

      //Ancient entity lifespan limit (only for raw atlas entities ceasing recording prior to modern era)
      let is_simplified = entity.metadata && entity.metadata.description && entity.metadata.description.includes("Simplified Polity");
      if (!is_simplified) {
        let last_entity_ts = timestamps[timestamps.length - 1];
        if (target_ts > last_entity_ts) {
          let last_kf = entity.history[String(last_entity_ts)];
          if (last_kf && (last_kf[0] === null || (last_kf[2] && last_kf[2].hidden === true)))
            return null;

          let last_date = (Date.convertTimestampToDate) ? Date.convertTimestampToDate(last_entity_ts) : null;
          let last_year = (last_date) ? last_date.year : Math.round(last_entity_ts / 8766);
          let target_date = (Date.convertTimestampToDate) ? Date.convertTimestampToDate(target_ts) : null;
          let target_year = (target_date) ? target_date.year : Math.round(target_ts / 8766);

          if (last_year < 1750 && target_year > last_year + 5) return null;
        }
      }

      //Return statement
      return {
        geometry: active_geom.geometry,
        properties: active_props,
        symbol: active_symbol
      };
    }


    /**
     * Produces a deterministic 11-digit snowflake ID from an input string.
     *
     * @param {string} arg0_str
     *
     * @returns {string}
     */
    static hashToSnowflakeId (arg0_str) {
      //Convert from parameters
      let str = String(arg0_str || "");

      //Declare local instance variables
      let abs_hash1;
      let abs_hash2;
      let hash = 5381;
      let hash2 = 0;
      let id_num;

      for (let i = 0; i < str.length; i++) {
        let char = str.charCodeAt(i);
        hash = ((hash << 5) + hash) + char;
        hash = hash & hash;
        hash2 = (hash2 * 33) ^ char;
      }

      abs_hash1 = Math.abs(hash) % 90000;
      abs_hash2 = Math.abs(hash2) % 1000000;
      id_num = (10000 + abs_hash1)*1000000 + abs_hash2;

      //Return statement
      return String(id_num);
    }


    /**
     * Semantic defence check determining whether an Atlas constituent is a subordinate dependency,
     * mandate, or distinct sub-kingdom that must NOT be merged into the sovereign metropole polygon.
     * Genuine peer constituents sharing regional grouping IDs (e.g. Shan States of Burma, Indian Princely States)
     * pass the check and are allowed to merge.
     *
     * @param {string} arg0_name
     * @param {string} arg1_seshat_id
     *
     * @returns {boolean} True if entity is a distinct dependency/mandate
     */
    static isSeparateDependency (arg0_name, arg1_seshat_id) {
      //Convert from parameters
      let name = String(arg0_name || "").trim();
      let seshat_id = String(arg1_seshat_id || "").trim();

      //Guard clause: regional parenthetical peer groups merge together (e.g. (Burma), (British Raj))
      if (seshat_id.startsWith("(") && seshat_id.endsWith(")")) return false;

      //Declare local instance variables
      let canon_lower;
      let canon_words;
      let canonical;
      let clio_entry;
      let dependency_terms;
      let has_core_match;
      let name_lower = name.toLowerCase();
      let name_words;
      let sub_titles;

      canonical = (this.cliopatria_canonicals) ? this.cliopatria_canonicals.get(seshat_id) : null;
      if (!canonical) {
        dependency_terms = ["administration", "colony", "condominium", "concession", "dependency", "dominion", "mandate", "occupied", "presidency", "protectorate", "regency of", "territory of", "viceroyalty"];
        for (let i = 0; i < dependency_terms.length; i++)
          if (name_lower.includes(dependency_terms[i])) return true;
        return false;
      }

      canon_lower = canonical.toLowerCase();
      if (name_lower === canon_lower) return false;

      //1. Cliopatria explicit member-of check
      clio_entry = (this.cliopatria_members) ? this.cliopatria_members.get(name_lower) : null;
      if (clio_entry && clio_entry.member_of) return true;

      //2. Dependency and mandate status terms
      dependency_terms = ["administration", "colony", "condominium", "concession", "dependency", "dominion", "mandate", "occupied", "presidency", "protectorate", "regency of", "territory of", "viceroyalty"];
      for (let i = 0; i < dependency_terms.length; i++)
        if (name_lower.includes(dependency_terms[i])) return true;

      //3. Sub-kingdom or feudal title divergence under an imperial metropole
      if (canon_lower.includes("empire") || canon_lower.includes("republic") || canon_lower.includes("confederation") || canon_lower.includes("union")) {
        sub_titles = ["county of ", "duchy of ", "kingdom of ", "landgraviate of ", "margraviate of ", "principality of "];
        for (let i = 0; i < sub_titles.length; i++)
          if (name_lower.startsWith(sub_titles[i]) && !name_lower.includes(canon_lower)) return true;
      }

      //4. Semantic geographic divergence from imperial metropole
      canon_words = canon_lower.split(/[^a-z]+/).filter((w) => w.length > 3);
      name_words = name_lower.split(/[^a-z]+/).filter((w) => w.length > 3);
      has_core_match = canon_words.some((cw) => name_words.some((nw) => nw.includes(cw) || cw.includes(nw)));

      if (!has_core_match && !name_lower.includes(canon_lower)) return true;

      //Return statement
      return false;
    }


    /**
     * Scores how closely an Atlas constituent represents the sovereign metropole of a Seshat ID.
     * Used to systematically anchor names, metadata, and symbology to the true metropole.
     *
     * @param {string} arg0_name
     * @param {string} arg1_seshat_id
     *
     * @returns {number} Metropolitan affinity score
     */
    static getMetropolitanScore (arg0_name, arg1_seshat_id) {
      //Convert from parameters
      let name = String(arg0_name || "").trim();
      let seshat_id = String(arg1_seshat_id || "").trim();

      //Declare local instance variables
      let canon_lower;
      let canon_words;
      let canonical;
      let match_count = 0;
      let name_lower = name.toLowerCase();
      let name_words;
      let score = 0;

      canonical = (this.cliopatria_canonicals) ? this.cliopatria_canonicals.get(seshat_id) : null;
      if (canonical) {
        canon_lower = canonical.toLowerCase();
        if (name_lower === canon_lower) return 100;
        if (name_lower.includes(canon_lower) || canon_lower.includes(name_lower)) score += 60;

        canon_words = canon_lower.split(/[^a-z]+/).filter((w) => w.length > 3);
        name_words = name_lower.split(/[^a-z]+/).filter((w) => w.length > 3);
        for (let i = 0; i < canon_words.length; i++) {
          if (name_words.includes(canon_words[i])) match_count++;
        }
        score += match_count * 15;
      }

      if (this.isSeparateDependency(name, seshat_id)) score -= 50;

      //Return statement
      return score;
    }


    /**
     * Resolves the canonical polity identity for an Atlas entity at a specific year.
     * Evaluates exact correlation map matches, preceding continuations, succeeding fallbacks,
     * and native Atlas properties, guaranteeing complete historical coverage.
     *
     * @param {string} arg0_entity_id
     * @param {number} arg1_year
     * @param {Object} arg2_active_state
     * @param {Object} arg3_map_entries
     *
     * @returns {Object} Resolved identity object
     */
    static resolveEntityIdentityAtYear (arg0_entity_id, arg1_year, arg2_active_state, arg3_map_entries) {
      //Convert from parameters
      let entity_id = arg0_entity_id;
      let year = arg1_year;
      let active_state = arg2_active_state;
      let map_entries = arg3_map_entries || {};

      //Declare local instance variables
      let entries = map_entries[entity_id] || [];
      let fallback_name;
      let is_parenthetical;
      let m;
      let matches;
      let p;
      let preceding;
      let s;
      let state_name;
      let succeeding;

      //1. Exact match in correlation map
      matches = entries.filter((e) => year >= e.from && year <= e.to);
      if (matches.length > 0) {
        matches.sort((a, b) => (a.span - b.span) || (b.line_num - a.line_num));
        m = matches[0];
        is_parenthetical = m.raw_seshat_id.startsWith("(") && m.raw_seshat_id.endsWith(")");
        //Return statement
        return {
          is_parenthetical: is_parenthetical,
          name: m.name,
          raw_seshat_id: m.raw_seshat_id,
          seshat_id: m.raw_seshat_id
        };
      }

      //2. Preceding entry continuation (for premature map ends, e.g. Bolivia, Paraguay, Chile, Norway)
      preceding = entries.filter((e) => e.to < year).sort((a, b) => b.to - a.to);
      if (preceding.length > 0) {
        p = preceding[0];
        state_name = (active_state && active_state.properties && active_state.properties.name) || p.name;
        is_parenthetical = p.raw_seshat_id.startsWith("(") && p.raw_seshat_id.endsWith(")");
        //Return statement
        return {
          is_parenthetical: is_parenthetical,
          name: state_name,
          raw_seshat_id: p.raw_seshat_id,
          seshat_id: p.raw_seshat_id
        };
      }

      //3. Succeeding entry fallback
      succeeding = entries.filter((e) => e.from > year).sort((a, b) => a.from - b.from);
      if (succeeding.length > 0) {
        s = succeeding[0];
        state_name = (active_state && active_state.properties && active_state.properties.name) || s.name;
        is_parenthetical = s.raw_seshat_id.startsWith("(") && s.raw_seshat_id.endsWith(")");
        //Return statement
        return {
          is_parenthetical: is_parenthetical,
          name: state_name,
          raw_seshat_id: s.raw_seshat_id,
          seshat_id: s.raw_seshat_id
        };
      }

      //4. Native Atlas property fallback
      fallback_name = (active_state && active_state.properties && active_state.properties.name) || `Polity ${entity_id}`;
      //Return statement
      return {
        is_parenthetical: true,
        name: fallback_name,
        raw_seshat_id: `(${fallback_name})`,
        seshat_id: `(${fallback_name})`
      };
    }


    /**
     * Performs topological union over an array of polygon coordinate arrays with 1km buffering.
     * Buffering eliminates slivers and degenerate topology on shared constituent boundaries.
     *
     * @param {Array} arg0_polygons
     *
     * @returns {Object|null} Unified GeoJSON geometry
     */
    static unionPolygonsBuffered (arg0_polygons) {
      //Convert from parameters
      let polygons = arg0_polygons || [];

      //Declare local instance variables
      let cleaned_polys = [];
      let clusters = [];
      let features = [];
      let result_parts = [];
      let visited = new Set();

      for (let i = 0; i < polygons.length; i++) {
        let cl = this.cleanPolygonRings(polygons[i]);
        if (cl) cleaned_polys.push(cl);
      }

      //Guard clauses
      if (cleaned_polys.length === 0) return null;
      if (cleaned_polys.length === 1) {
        return {
          coordinates: cleaned_polys[0],
          type: "Polygon"
        };
      }

      for (let i = 0; i < cleaned_polys.length; i++) {
        try {
          let f = turf.polygon(cleaned_polys[i]);
          features.push({ bbox: turf.bbox(f), feat: f, poly: cleaned_polys[i] });
        } catch (e) {
          result_parts.push(cleaned_polys[i]);
        }
      }

      //Cluster touching or overlapping constituents
      for (let i = 0; i < features.length; i++) {
        if (visited.has(i)) continue;
        let cluster = [i];
        let queue = [i];
        visited.add(i);

        while (queue.length > 0) {
          let curr = queue.shift();
          let curr_f = features[curr];

          for (let j = 0; j < features.length; j++) {
            if (visited.has(j)) continue;
            let other_f = features[j];

            if (curr_f.bbox[0] <= other_f.bbox[2] && curr_f.bbox[2] >= other_f.bbox[0] &&
                curr_f.bbox[1] <= other_f.bbox[3] && curr_f.bbox[3] >= other_f.bbox[1]) {
              try {
                if (turf.booleanIntersects(curr_f.feat, other_f.feat)) {
                  visited.add(j);
                  cluster.push(j);
                  queue.push(j);
                }
              } catch (err) {}
            }
          }
        }
        clusters.push(cluster);
      }

      //Union touching clusters with 1km buffer
      for (let c = 0; c < clusters.length; c++) {
        let clist = clusters[c];
        if (clist.length === 1) {
          result_parts.push(features[clist[0]].poly);
        } else {
          try {
            let bufs = [];
            for (let idx of clist) {
              let b = turf.buffer(features[idx].feat, 1, { units: "kilometers" });
              bufs.push(b || features[idx].feat);
            }
            let u = turf.union(turf.featureCollection(bufs));
            if (u && u.geometry) {
              if (u.geometry.type === "Polygon") {
                result_parts.push(u.geometry.coordinates);
              } else if (u.geometry.type === "MultiPolygon") {
                for (let part of u.geometry.coordinates) result_parts.push(part);
              }
            } else {
              for (let idx of clist) result_parts.push(features[idx].poly);
            }
          } catch (e) {
            for (let idx of clist) result_parts.push(features[idx].poly);
          }
        }
      }

      if (result_parts.length === 1) {
        return {
          coordinates: result_parts[0],
          type: "Polygon"
        };
      }

      //Return statement
      return {
        coordinates: result_parts,
        type: "MultiPolygon"
      };
    }


    /**
     * Loads configuration, atlas.naissance, and correlation map datasets.
     *
     * @param {Object} [arg0_options]
     * @param {string} [arg0_options.config_path]
     *
     * @returns {Object} Loaded datasets and configuration
     */
    static A_loadData (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let atlas_data;
      let config;
      let config_file_path;
      let map_content;
      let map_entries = {};
      let map_lines;

      config_file_path = options.config_path || this.config_path;
      console.log(`[PolitiesAtlasJoin] Loading configuration from: ${config_file_path}...`);
      config = json5.parse(fs.readFileSync(config_file_path, "utf8"));

      console.log(`[PolitiesAtlasJoin] Loading Atlas savefile from: ${config.input_atlas_path}...`);
      atlas_data = JSON.parse(fs.readFileSync(config.input_atlas_path, "utf8"));

      console.log(`[PolitiesAtlasJoin] Loading correlation map from: ${config.correlation_map_path}...`);
      map_content = fs.readFileSync(config.correlation_map_path, "utf8");

      map_lines = map_content.split("\n").filter((l) => l.trim() && !l.startsWith("#"));
      for (let i = 0; i < map_lines.length; i++) {
        let parts = map_lines[i].split("|").map((s) => s.trim());
        let aid = parts[0];
        if (!map_entries[aid]) map_entries[aid] = [];
        map_entries[aid].push({
          from: Number(parts[1]),
          line_num: i + 1,
          name: parts[3],
          raw_seshat_id: parts[4],
          span: Number(parts[2]) - Number(parts[1]),
          to: Number(parts[2])
        });
      }

      //Load Cliopatria semantic hierarchy
      let clio_dump_path = path.resolve(path.dirname(config_file_path), "cliopatria_polities_dump.txt");
      if (fs.existsSync(clio_dump_path)) {
        let clio_lines = fs.readFileSync(clio_dump_path, "utf8").split("\n");
        this.cliopatria_canonicals = new Map();
        this.cliopatria_members = new Map();
        for (let i = 1; i < clio_lines.length; i++) {
          let parts = clio_lines[i].split("|").map((s) => s.trim());
          if (parts.length >= 2 && parts[1]) {
            let p_name = parts[0];
            let s_id = parts[1];
            let m_of = parts[2] || "";
            if (p_name.startsWith("(") && p_name.endsWith(")")) {
              let clean = p_name.slice(1, -1);
              if (!this.cliopatria_canonicals.has(s_id)) this.cliopatria_canonicals.set(s_id, clean);
            }
            this.cliopatria_members.set(p_name.toLowerCase(), { member_of: m_of, name: p_name, seshat_id: s_id });
          }
        }
      }

      //Return statement
      return {
        atlas_data: atlas_data,
        config: config,
        map_entries: map_entries
      };
    }


    /**
     * Iterates through all discrete timestamps, resolving entity identities, unioning
     * contemporaneous constituents with 1km buffering, and emitting sparse diff keyframes.
     *
     * @param {Object} arg0_atlas_data
     * @param {Object} arg1_map_entries
     *
     * @returns {Map<string, Object>} Unified polities with sparse keyframes
     */
    static B_processTimestamps (arg0_atlas_data, arg1_map_entries) {
      //Convert from parameters
      let atlas_data = arg0_atlas_data || {};
      let map_entries = arg1_map_entries || {};

      //Declare local instance variables
      let atlas_ids = Object.keys(atlas_data).filter((k) => atlas_data[k].class_name === "GeometryPolygon" && atlas_data[k].history);
      let kf_stats = { 1: 0, 2: 0, 3: 0, nulls: 0 };
      let last_log_time = Date.now();
      let sorted_ts;
      let total_keyframes = 0;
      let ts_set = new Set();
      let unified_polities = new Map();

      for (let i = 0; i < atlas_ids.length; i++) {
        let ent = atlas_data[atlas_ids[i]];
        for (let t in ent.history) ts_set.add(parseInt(t));
      }
      sorted_ts = Array.from(ts_set).sort((a, b) => a - b);
      console.log(`[PolitiesAtlasJoin] Processing ${sorted_ts.length} timestamps across ${atlas_ids.length} Atlas polygons...`);

      for (let t_idx = 0; t_idx < sorted_ts.length; t_idx++) {
        let t = sorted_ts[t_idx];
        let date = Date.convertTimestampToDate(t);
        let y = (date) ? date.year : Math.round(t / 8766);

        let active_groups = new Map();

        for (let i = 0; i < atlas_ids.length; i++) {
          let id = atlas_ids[i];
          let ent = atlas_data[id];
          let state = this.getEntityStateAtTimestamp(ent, t);
          if (!state || !state.geometry) continue;

          let poly_arr = (state.geometry.type === "Polygon") ? [state.geometry.coordinates] : state.geometry.coordinates;
          let cleaned_rings = [];
          for (let p = 0; p < poly_arr.length; p++) {
            let cl = this.cleanPolygonRings(poly_arr[p]);
            if (cl) cleaned_rings.push(cl);
          }
          if (cleaned_rings.length === 0) continue;

          let ident = this.resolveEntityIdentityAtYear(id, y, state, map_entries);
          let name = (state.properties && state.properties.name) || ident.name;

          //Semantic Defence Check: keep dependencies and mandates separate
          let is_dep = this.isSeparateDependency(name, ident.seshat_id);
          let group_key = (is_dep) ? `${name}_${ident.seshat_id}` : ident.seshat_id;

          let score = this.getMetropolitanScore(name, ident.seshat_id);

          if (!active_groups.has(group_key)) {
            active_groups.set(group_key, {
              highest_score: score,
              ident: ident,
              polygons: [],
              primary_entity_id: id,
              primary_state: state
            });
          }

          let grp = active_groups.get(group_key);
          for (let c = 0; c < cleaned_rings.length; c++) grp.polygons.push(cleaned_rings[c]);

          if (score > grp.highest_score) {
            grp.highest_score = score;
            grp.primary_state = state;
            grp.primary_entity_id = id;
          }
        }

        //Update active polities
        active_groups.forEach((grp, g_key) => {
          if (!unified_polities.has(g_key)) {
            unified_polities.set(g_key, {
              canonical_name: (grp.primary_state && grp.primary_state.properties && grp.primary_state.properties.name) || grp.ident.name,
              highest_score: grp.highest_score,
              ident: grp.ident,
              is_active: false,
              keyframes: {},
              last_geom: null,
              last_geom_sig: null,
              last_props: null,
              last_symbol: null,
              primary_atlas_id: grp.primary_entity_id
            });
          }

          let pol = unified_polities.get(g_key);
          if (grp.highest_score > pol.highest_score) {
            pol.highest_score = grp.highest_score;
            pol.canonical_name = (grp.primary_state && grp.primary_state.properties && grp.primary_state.properties.name) || grp.ident.name;
            pol.primary_atlas_id = grp.primary_entity_id;
          }

          let coord_count = 0;
          let coord_sum_x = 0;
          let coord_sum_y = 0;
          for (let p = 0; p < grp.polygons.length; p++) {
            let poly = grp.polygons[p];
            for (let r = 0; r < poly.length; r++) {
              let ring = poly[r];
              coord_count += ring.length;
              if (ring.length > 0) {
                coord_sum_x += ring[0][0] + ring[ring.length - 1][0];
                coord_sum_y += ring[0][1] + ring[ring.length - 1][1];
                let mid = Math.floor(ring.length / 2);
                coord_sum_x += ring[mid][0];
                coord_sum_y += ring[mid][1];
              }
            }
          }

          let geom_sig = `${grp.polygons.length}|${coord_count}|${coord_sum_x.toFixed(3)}|${coord_sum_y.toFixed(3)}`;
          let geom_changed = (geom_sig !== pol.last_geom_sig);
          let merged_geom = (geom_changed || !pol.last_geom) ? this.unionPolygonsBuffered(grp.polygons) : pol.last_geom;
          if (!merged_geom) return;
          pol.last_geom = merged_geom;
          pol.last_geom_sig = geom_sig;

          let fill = (grp.primary_state && grp.primary_state.symbol && grp.primary_state.symbol.polygonFill)
            ? grp.primary_state.symbol.polygonFill
            : ((pol.last_symbol) ? pol.last_symbol.polygonFill : "#7289da");
          let current_symbol = {
            polygonFill: fill,
            textSize: (grp.primary_state && grp.primary_state.symbol && grp.primary_state.symbol.textSize) || 14
          };
          let current_props = {
            name: (grp.primary_state && grp.primary_state.properties && grp.primary_state.properties.name) || grp.ident.name,
            seshat_id: grp.ident.seshat_id
          };

          //Strict Diff Pattern
          if (!pol.is_active || !pol.last_props) {
            pol.keyframes[String(t)] = [
              { feature: { geometry: merged_geom, properties: {}, type: "Feature" } },
              current_symbol,
              current_props
            ];
            kf_stats[3]++;
            total_keyframes++;
            pol.last_symbol = current_symbol;
            pol.last_props = current_props;
            pol.is_active = true;
          } else {
            let symbol_changed = (current_symbol.polygonFill !== pol.last_symbol.polygonFill || current_symbol.textSize !== pol.last_symbol.textSize);
            let name_changed = (current_props.name !== pol.last_props.name);
            let seshat_changed = (current_props.seshat_id !== pol.last_props.seshat_id);
            let props_changed = (name_changed || seshat_changed);

            if (!geom_changed && !symbol_changed && !props_changed) return;

            if (props_changed) {
              let prop_diff = {};
              if (name_changed) prop_diff.name = current_props.name;
              if (seshat_changed) prop_diff.seshat_id = current_props.seshat_id;
              pol.keyframes[String(t)] = [
                { feature: { geometry: merged_geom, properties: {}, type: "Feature" } },
                (symbol_changed ? current_symbol : null),
                prop_diff
              ];
              kf_stats[3]++;
              total_keyframes++;
              pol.last_props = Object.assign({}, pol.last_props, prop_diff);
              if (symbol_changed) pol.last_symbol = current_symbol;
            } else if (symbol_changed) {
              pol.keyframes[String(t)] = [
                { feature: { geometry: merged_geom, properties: {}, type: "Feature" } },
                current_symbol
              ];
              kf_stats[2]++;
              total_keyframes++;
              pol.last_symbol = current_symbol;
            } else {
              //Sparse keyframe: ONLY boundary geometry changed
              pol.keyframes[String(t)] = [
                { feature: { geometry: merged_geom, properties: {}, type: "Feature" } }
              ];
              kf_stats[1]++;
              total_keyframes++;
            }
          }
        });

        //Deactivate ceased polities
        unified_polities.forEach((pol, g_key) => {
          if (!active_groups.has(g_key) && pol.is_active) {
            pol.keyframes[String(t)] = [null];
            kf_stats.nulls++;
            total_keyframes++;
            pol.is_active = false;
            pol.last_geom = null;
            pol.last_geom_sig = null;
          }
        });

        if (Date.now() - last_log_time > 5000 || t_idx === sorted_ts.length - 1) {
          let pct = Math.round(((t_idx + 1) / sorted_ts.length) * 100);
          console.log(`[PolitiesAtlasJoin] Progress: ${pct}% (TS ${t_idx + 1}/${sorted_ts.length}, Year ${y}, KFs: ${total_keyframes})`);
          last_log_time = Date.now();
        }
      }

      console.log(`[PolitiesAtlasJoin] Finished timestamp processing. Generated ${unified_polities.size} polities with ${total_keyframes} keyframes.`);

      //Return statement
      return unified_polities;
    }


    /**
     * Reassembles the final savefile containing consolidated polities, FeatureGroups, and layers.
     *
     * @param {Map<string, Object>} arg0_unified_polities
     * @param {Object} arg1_atlas_data
     * @param {Object} [arg2_config]
     *
     * @returns {Object} Complete savefile object
     */
    static C_assembleSavefile (arg0_unified_polities, arg1_atlas_data, arg2_config) {
      //Convert from parameters
      let unified_polities = arg0_unified_polities;
      let atlas_data = arg1_atlas_data || {};
      let config = arg2_config || {};

      //Declare local instance variables
      let final_savefile = {};
      let group_entities_map = new Map();
      let original_entity_to_group = new Map();
      let pol_keys = Array.from(unified_polities.keys());
      let used_ids = new Set();

      console.log(`[PolitiesAtlasJoin] Assembling savefile structure...`);

      //1. Preserve map_settings
      if (atlas_data.map_settings) final_savefile.map_settings = atlas_data.map_settings;

      //2. Map original entity IDs to FeatureGroups
      for (let k in atlas_data) {
        if (atlas_data[k].class_name === "FeatureGroup") {
          let fg_val = (typeof atlas_data[k].value === "string") ?
            JSON.parse(atlas_data[k].value) : atlas_data[k].value;

          if (fg_val && fg_val.entities) {
            for (let i = 0; i < fg_val.entities.length; i++) {
              original_entity_to_group.set(fg_val.entities[i].id, k);
            }
          }
          group_entities_map.set(k, []);
        }
      }

      //3. Reconstruct GeometryPolygon entities
      for (let i = 0; i < pol_keys.length; i++) {
        let g_key = pol_keys[i];
        let pol = unified_polities.get(g_key);

        let entity_id = pol.primary_atlas_id;
        if (!entity_id || used_ids.has(entity_id)) {
          entity_id = this.hashToSnowflakeId(g_key);
          if (used_ids.has(entity_id)) {
            let offset = 1;
            while (used_ids.has(`${entity_id}_${offset}`)) offset++;
            entity_id = `${entity_id}_${offset}`;
          }
        }
        used_ids.add(entity_id);

        let new_entity = {
          class_name: "GeometryPolygon",
          history: pol.keyframes,
          id: entity_id,
          metadata: {
            description: `Simplified Polity: ${pol.canonical_name}\nSeshatID: ${pol.ident.seshat_id}\nBase Source: Cliopatria`,
            tags: ["Polities"]
          },
          type: "geometry"
        };

        final_savefile[entity_id] = new_entity;

        //Anchor into regional FeatureGroup
        let assigned_group = original_entity_to_group.get(pol.primary_atlas_id);
        if (!assigned_group) {
          let s_id = pol.ident.seshat_id || "";
          let prefix = s_id.replace(/^\(/, "").split("_")[0];
          let region_prefix_map = {
            ar: "70026347630", au: "45066516298", bd: "19853446951", bo: "70026347630",
            br: "70026347630", ca: "55812148848", cl: "70026347630", cn: "96891234970",
            co: "70026347630", dz: "6066323292", eg: "6066323292", et: "25715763203",
            gl: "55812148848", in: "19853446951", iq: "35194181118", ir: "35194181118",
            jp: "96891234970", kr: "96891234970", lk: "19853446951", ly: "6066323292",
            ma: "6066323292", mn: "96891234970", mx: "70026347630", no: "94350264119",
            nz: "45066516298", pe: "70026347630", pk: "19853446951", py: "70026347630",
            ru: "34506973799", sa: "35194181118", sy: "35194181118", tn: "6066323292",
            tr: "35194181118", us: "55812148848", ve: "70026347630"
          };
          assigned_group = region_prefix_map[prefix] || "94350264119";
        }

        if (group_entities_map.has(assigned_group)) {
          group_entities_map.get(assigned_group).push({
            class_name: "GeometryPolygon",
            id: entity_id
          });
        }
      }

      //4. Reconstruct FeatureGroups and other non-polygon entities
      for (let k in atlas_data) {
        let orig = atlas_data[k];
        if (orig.class_name === "FeatureGroup") {
          let fg_val = (typeof orig.value === "string") ? JSON.parse(orig.value) : orig.value;

          if (group_entities_map.has(k) && fg_val && fg_val.name !== "Atlas") {
            fg_val.entities = group_entities_map.get(k);
            orig.value = JSON.stringify(fg_val);
          }
          final_savefile[k] = orig;
        } else if (orig.class_name !== "GeometryPolygon" && k !== "map_settings") {
          final_savefile[k] = orig;
        }
      }

      console.log(`[PolitiesAtlasJoin] Assembled savefile with ${Object.keys(final_savefile).length} top-level entities.`);

      //Return statement
      return final_savefile;
    }


    /**
     * Main pipeline execution entry point.
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Promise<void>}
     */
    static async run (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let assembled_savefile;
      let keys;
      let loaded_data;
      let out_stream;
      let output_path;
      let stat;
      let unified_polities;

      loaded_data = this.A_loadData(options);
      unified_polities = this.B_processTimestamps(loaded_data.atlas_data, loaded_data.map_entries);
      assembled_savefile = this.C_assembleSavefile(unified_polities, loaded_data.atlas_data, loaded_data.config);

      output_path = loaded_data.config.output_atlas_path;
      console.log(`[PolitiesAtlasJoin] Writing output to: ${output_path}...`);

      out_stream = fs.createWriteStream(output_path, { encoding: "utf8" });
      out_stream.write("{\n");
      keys = Object.keys(assembled_savefile);
      for (let i = 0; i < keys.length; i++) {
        let k = keys[i];
        let val_str = JSON.stringify(assembled_savefile[k]);
        let comma = (i < keys.length - 1) ? "," : "";
        out_stream.write(`  ${JSON.stringify(k)}: ${val_str}${comma}\n`);
      }
      out_stream.write("}\n");
      out_stream.end();

      await new Promise((resolve) => out_stream.on("finish", resolve));
      stat = fs.statSync(output_path);
      console.log(`[PolitiesAtlasJoin] Finished successfully! Saved ${(stat.size / 1024 / 1024).toFixed(2)} MB to ${output_path}`);
    }
  };

  //Auto-execute if executed directly via Node CLI
  if (typeof require !== "undefined" && typeof module !== "undefined" && require.main === module) {
    global.PolitiesAtlasJoin.run()
      .then(() => process.exit(0))
      .catch((err) => {
        console.error("[PolitiesAtlasJoin] Fatal error:", err);
        process.exit(1);
      });
  }
})();
