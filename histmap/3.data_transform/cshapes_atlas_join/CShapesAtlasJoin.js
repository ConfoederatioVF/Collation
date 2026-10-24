(function () {
  if (!global.ve) global.ve = { registry: { settings: {} } };
  let fs = (typeof require !== "undefined") ? require("fs") : global.fs;
  let path = (typeof require !== "undefined") ? require("path") : global.path;
  let turf = global.turf || ((typeof require !== "undefined") ? require(path.resolve(process.cwd(), "UF/js/geospatiale/turf.min.js")) : null);

  if (typeof require !== "undefined") {
    try { require(path.resolve(process.cwd(), "UF/js/date/date_basic.js")); } catch (e) {}
    try { require(path.resolve(process.cwd(), "UF/js/date/date_conversion.js")); } catch (e) {}
  }

  /**
   * CShapesAtlasJoin spatiotemporally joins CShapes-Europe (1816-1886) and CShapes-2.0 (1886+)
   * into atlas_simplified.naissance, assigning canonical Seshat IDs and Correlates of War (COW)
   * codes, inheriting polygon colours via pole of inaccessibility, and enforcing strict topology.
   *
   * @class CShapesAtlasJoin
   */
  global.CShapesAtlasJoin = class {
    static c2_path = "saves/CShapes-2.0.geojson";
    static c2_txt_path = "histmap/2.data_cleaning/cshapes_join/cshapes_2_polities.txt";
    static eu_path = "saves/CShapes-Europe.geojson";
    static eu_txt_path = "histmap/2.data_cleaning/cshapes_join/cshapes_europe_polities.txt";
    static europe_bbox = [-25.0, 34.0, 60.0, 72.0];
    static out_atlas_path = "saves/atlas_simplified.naissance";
    static raw_atlas_path = "saves/atlas.naissance";
    static simp_atlas_path = (typeof fs !== "undefined" && fs.existsSync("saves/atlas_simplified.naissance.bak")) ? "saves/atlas_simplified.naissance.bak" : "saves/atlas_simplified.naissance";

    /**
     * Builds a fast spatial bounding-box index of active Atlas polygons at a target timestamp.
     *
     * @param {Object} arg0_atlas_data
     * @param {number} arg1_target_ts
     *
     * @returns {Array<Object>} List of indexed active features with bounding boxes
     */
    static buildSpatialIndex (arg0_atlas_data, arg1_target_ts) {
      //Convert from parameters
      let atlas_data = arg0_atlas_data;
      let target_ts = arg1_target_ts;

      //Declare local instance variables
      let bbox;
      let ent;
      let feat;
      let indexed = [];
      let keys;
      let state;

      keys = Object.keys(atlas_data);
      for (let i = 0; i < keys.length; i++) {
        ent = atlas_data[keys[i]];
        if (ent.class_name !== "GeometryPolygon" || !ent.history) continue;

        state = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, target_ts);
        if (!state || !state.geometry) continue;

        try {
          feat = turf.feature(state.geometry);
          bbox = turf.bbox(feat);
          indexed.push({
            bbox: bbox,
            feature: feat,
            id: ent.id,
            symbol: state.symbol
          });
        } catch (e) {}
      }

      //Return statement
      return indexed;
    }

    /**
     * Computes a fast string signature of geometry rings and coordinate sums to detect topological changes.
     *
     * @param {Object} arg0_geom
     *
     * @returns {string} Deterministic geometry signature
     */
    static computeGeomSignature (arg0_geom) {
      //Convert from parameters
      let geom = arg0_geom;

      //Guard clause
      if (!geom) return "null";

      //Declare local instance variables
      let count = 0;
      let polys = (geom.type === "MultiPolygon") ? geom.coordinates : [geom.coordinates];
      let ring;
      let sum_x = 0;
      let sum_y = 0;

      for (let p = 0; p < polys.length; p++) {
        for (let r = 0; r < polys[p].length; r++) {
          ring = polys[p][r];
          count += ring.length;
          if (ring.length > 0) {
            sum_x += ring[0][0] + ring[ring.length - 1][0];
            sum_y += ring[0][1] + ring[ring.length - 1][1];
          }
        }
      }

      //Return statement
      return polys.length + "|" + count + "|" + sum_x.toFixed(2) + "|" + sum_y.toFixed(2);
    }

    /**
     * Deactivates an active entity, appending a null keyframe.
     *
     * @param {string} arg0_id
     * @param {number} arg1_ts
     * @param {Map<string, Object>} arg2_history_map
     * @param {Map<string, Object>} arg3_state_tracker
     */
    static deactivateEntity (arg0_id, arg1_ts, arg2_history_map, arg3_state_tracker) {
      //Convert from parameters
      let history_map = arg2_history_map;
      let id = arg0_id;
      let state_tracker = arg3_state_tracker;
      let ts = String(arg1_ts);

      //Declare local instance variables
      let prev = state_tracker.get(id);

      if (prev && prev.is_active) {
        if (!history_map.has(id)) history_map.set(id, {});
        history_map.get(id)[ts] = [null];
        prev.is_active = false;
        prev.last_geom = null;
        prev.last_geom_sig = null;
      }
    }

    /**
     * Emits a sparse diff keyframe, omitting unchanged properties/symbols to prevent duplication.
     *
     * @param {string} arg0_id
     * @param {number} arg1_ts
     * @param {Object} arg2_geom
     * @param {Object} arg3_symbol
     * @param {Object} arg4_props
     * @param {Map<string, Object>} arg5_history_map
     * @param {Map<string, Object>} arg6_state_tracker
     */
    static emitKeyframe (arg0_id, arg1_ts, arg2_geom, arg3_symbol, arg4_props, arg5_history_map, arg6_state_tracker) {
      //Convert from parameters
      let geom = arg2_geom;
      let history_map = arg5_history_map;
      let id = arg0_id;
      let props = arg4_props;
      let state_tracker = arg6_state_tracker;
      let symbol = arg3_symbol;
      let ts = String(arg1_ts);

      //Declare local instance variables
      let diff_props = {};
      let feat_obj = { feature: { geometry: geom, properties: {}, type: "Feature" } };
      let geom_changed = false;
      let prev = state_tracker.get(id);
      let props_changed = false;
      let sig = this.computeGeomSignature(geom);
      let symbol_changed = false;

      if (!history_map.has(id)) history_map.set(id, {});

      if (!prev || !prev.is_active) {
        //Activation keyframe: emit full geometry, symbol, and properties
        history_map.get(id)[ts] = [feat_obj, symbol, props];
        state_tracker.set(id, {
          is_active: true,
          last_geom: geom,
          last_geom_sig: sig,
          last_props: Object.assign({}, props),
          last_symbol: Object.assign({}, symbol)
        });
        return;
      }

      geom_changed = (sig !== prev.last_geom_sig);
      symbol_changed = (symbol && prev.last_symbol && symbol.polygonFill !== prev.last_symbol.polygonFill);

      for (let p in props) {
        if (props[p] !== prev.last_props[p]) {
          props_changed = true;
          diff_props[p] = props[p];
        }
      }

      //Sparse check: if nothing changed, do not emit redundant keyframe
      if (!geom_changed && !symbol_changed && !props_changed) return;

      if (props_changed) {
        history_map.get(id)[ts] = [feat_obj, (symbol_changed ? symbol : null), diff_props];
        prev.last_props = Object.assign({}, prev.last_props, diff_props);
        if (symbol_changed) prev.last_symbol = Object.assign({}, symbol);
        prev.last_geom_sig = sig;
      } else if (symbol_changed) {
        history_map.get(id)[ts] = [feat_obj, symbol];
        prev.last_symbol = Object.assign({}, symbol);
        prev.last_geom_sig = sig;
      } else {
        //Sparse keyframe: boundary geometry only
        history_map.get(id)[ts] = [feat_obj];
        prev.last_geom_sig = sig;
      }
    }

    /**
     * Computes the pole of inaccessibility of a feature and samples colour from the Atlas spatial index.
     *
     * @param {Object} arg0_feature
     * @param {Array<Object>} arg1_spatial_index
     * @param {string} [arg2_default_color]
     *
     * @returns {string} Inherited hex colour string
     */
    static inheritColorViaPOI (arg0_feature, arg1_spatial_index, arg2_default_color) {
      //Convert from parameters
      let default_color = arg2_default_color || "#7289da";
      let feature = arg0_feature;
      let spatial_index = arg1_spatial_index;

      //Guard clause
      if (!feature || !spatial_index) return default_color;

      //Declare local instance variables
      let b;
      let c;
      let item;
      let pt;

      try {
        pt = turf.pointOnFeature(feature);
        c = pt.geometry.coordinates;

        for (let i = 0; i < spatial_index.length; i++) {
          item = spatial_index[i];
          b = item.bbox;
          if (c[0] >= b[0] && c[0] <= b[2] && c[1] >= b[1] && c[1] <= b[3]) {
            if (turf.booleanPointInPolygon(pt, item.feature)) {
              if (item.symbol && item.symbol.polygonFill)
                //Return statement
                return item.symbol.polygonFill;
            }
          }
        }
      } catch (e) {}

      //Return statement
      return default_color;
    }

    /**
     * Determines whether a polygon coordinate ring is located inside the European bounding envelope.
     *
     * @param {Array<Array<number>>} arg0_ring
     *
     * @returns {boolean} True if ring centroid is within European bounds
     */
    static isRingInEurope (arg0_ring) {
      //Convert from parameters
      let ring = arg0_ring;

      //Guard clause
      if (!ring || ring.length < 3) return false;

      //Declare local instance variables
      let bb = CShapesAtlasJoin.europe_bbox;
      let sum_x = 0;
      let sum_y = 0;
      let x;
      let y;

      for (let i = 0; i < ring.length; i++) {
        sum_x += ring[i][0];
        sum_y += ring[i][1];
      }
      x = sum_x / ring.length;
      y = sum_y / ring.length;

      //Return statement
      return (x >= bb[0] && x <= bb[2] && y >= bb[1] && y <= bb[3]);
    }

    /**
     * Parses the CShapes metadata text file mapping names and codes to Seshat IDs and COW codes.
     *
     * @param {string} arg0_file_path
     *
     * @returns {Map<string, Object>} Map keyed by code/name to metadata object
     */
    static loadMetadataTable (arg0_file_path) {
      //Convert from parameters
      let file_path = arg0_file_path;

      //Declare local instance variables
      let cow;
      let from;
      let lines;
      let name;
      let parts;
      let raw;
      let seshat;
      let table = new Map();
      let to;

      raw = fs.readFileSync(file_path, "utf8");
      lines = raw.trim().split("\n");

      for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        if (line.startsWith("#") || !line) continue;

        parts = line.split(" | ");
        if (parts.length >= 6) {
          let code = parts[0].trim();
          name = parts[1].trim();
          from = parseInt(parts[2].trim());
          to = parseInt(parts[3].trim());
          seshat = parts[4].trim();
          cow = parseInt(parts[5].trim()) || null;

          let entry = {
            code: code,
            cow: cow,
            cow_code: cow,
            from: from,
            name: name,
            seshat_id: seshat,
            to: to
          };

          table.set(code + "|" + name, entry);
          table.set(name.toLowerCase(), entry);
          if (!table.has(code)) table.set(code, entry);
        }
      }

      //Return statement
      return table;
    }

    /**
     * Loads all source savefiles, GeoJSON layers, and metadata correlation mappings.
     *
     * @returns {Object} Loaded datasets
     */
    static loadSources () {
      //Declare local instance variables
      let atlas_data;
      let c2_geo;
      let c2_meta;
      let eu_geo;
      let eu_meta;
      let simp_data;

      console.log("[CShapesAtlasJoin] Loading source datasets...");
      simp_data = JSON.parse(fs.readFileSync(this.simp_atlas_path, "utf8"));
      atlas_data = JSON.parse(fs.readFileSync(this.raw_atlas_path, "utf8"));
      eu_geo = JSON.parse(fs.readFileSync(this.eu_path, "utf8"));
      c2_geo = JSON.parse(fs.readFileSync(this.c2_path, "utf8"));
      eu_meta = this.loadMetadataTable(this.eu_txt_path);
      c2_meta = this.loadMetadataTable(this.c2_txt_path);

      console.log(`[CShapesAtlasJoin] Loaded ${eu_geo.features.length} EU features, ${c2_geo.features.length} C2 features.`);

      //Return statement
      return {
        atlas_data: atlas_data,
        c2_geo: c2_geo,
        c2_meta: c2_meta,
        eu_geo: eu_geo,
        eu_meta: eu_meta,
        simp_data: simp_data
      };
    }

    /**
     * Main execution routine: spatiotemporally joins CShapes-Europe (1816-1886) and CShapes-2.0 (1886+),
     * inherits pole-of-inaccessibility colours, and outputs compliant sparse keyframes.
     *
     * @returns {Promise<void>}
     */
    static async run () {
      //Declare local instance variables
      let active_c2;
      let active_eu;
      let all_timestamps = new Set();
      let c2_by_polity;
      let entity_history_map = new Map();
      let entity_meta_map = new Map();
      let entity_name_map = new Map();
      let entity_state_tracker = new Map();
      let eu_by_polity;
      let last_log = Date.now();
      let out_stream;
      let polities_join = require(path.resolve(process.cwd(), "histmap/3.data_transform/polities_atlas_join/polities_atlas_join.js"));
      let seshat_to_entity_id = new Map();
      let sources = this.loadSources();
      let ts_keys;

      //1. Index all continuous polities and their immutable canonical names in existing atlas_simplified
      for (let k in sources.simp_data) {
        let ent = sources.simp_data[k];
        if (ent.class_name === "GeometryPolygon" && ent.history) {
          entity_meta_map.set(k, {
            class_name: "GeometryPolygon",
            id: ent.id,
            metadata: ent.metadata,
            type: "geometry"
          });
          entity_history_map.set(k, {});

          //Establish immutable canonical name to prevent mutations
          let init_name = null;
          let init_seshat = null;
          let ts_arr = Object.keys(ent.history).sort((a, b) => Number(a) - Number(b));
          for (let i = 0; i < ts_arr.length; i++) {
            let kf = ent.history[ts_arr[i]];
            if (kf && kf[2] && kf[2].name) {
              init_name = kf[2].name;
              init_seshat = kf[2].seshat_id;
              break;
            }
          }

          if (init_name) entity_name_map.set(k, init_name);
          if (init_seshat && !seshat_to_entity_id.has(init_seshat)) {
            let is_dep = init_name.toLowerCase().includes("guiana") || init_name.toLowerCase().includes("north america") || init_name.toLowerCase().includes("syria");
            if (!is_dep) seshat_to_entity_id.set(init_seshat, k);
          }

          let desc = (ent.metadata && ent.metadata.description) || "";
          let match = desc.match(/SeshatID:\s*([^\n]+)/);
          if (match) {
            let s_id = match[1].trim();
            if (!seshat_to_entity_id.has(s_id)) seshat_to_entity_id.set(s_id, k);
          }

          for (let ts in ent.history) all_timestamps.add(Number(ts));
        }
      }

      //Explicit canonical metropole and historical mappings
      seshat_to_entity_id.set("gb_british_emp_1", "87693477140");
      seshat_to_entity_id.set("gb_british_emp_2", "87692477137");
      seshat_to_entity_id.set("us_antebellum", "999152906");
      seshat_to_entity_id.set("fr_france_modern_1", "82079236664");
      seshat_to_entity_id.set("ru_romanov_dyn_2", "10264500703");
      seshat_to_entity_id.set("ru_soviet_union", "10264500703");
      seshat_to_entity_id.set("ru_russian_federation", "10264500703");
      seshat_to_entity_id.set("(Burma)", "79315678680");
      seshat_to_entity_id.set("(British Raj)", "562205920");
      seshat_to_entity_id.set("de_ns_germany", "27376636343");

      ts_keys = Array.from(all_timestamps).sort((a, b) => a - b);
      console.log(`[CShapesAtlasJoin] Processing ${ts_keys.length} discrete historical timestamps...`);

      //2. Iterate through all timestamps
      for (let t_idx = 0; t_idx < ts_keys.length; t_idx++) {
        let ts = ts_keys[t_idx];
        let date = (Date.convertTimestampToDate) ? Date.convertTimestampToDate(ts) : null;
        let year = (date) ? date.year : Math.round(ts / 8766);
        let spatial_index = null;

        if (year >= 1816) {
          spatial_index = this.buildSpatialIndex(sources.atlas_data, ts);
        }

        //Epoch A: Pre-1816 (Keep original simplified entities unmodified)
        if (year < 1816) {
          for (let id of entity_meta_map.keys()) {
            let orig = sources.simp_data[id];
            if (orig && orig.history && orig.history[String(ts)]) {
              entity_history_map.get(id)[String(ts)] = orig.history[String(ts)];
              let kf = orig.history[String(ts)];
              if (kf && kf[0] !== null) {
                let geom = kf[0].feature ? kf[0].feature.geometry : null;
                entity_state_tracker.set(id, {
                  is_active: true,
                  last_geom: geom,
                  last_geom_sig: this.computeGeomSignature(geom),
                  last_props: kf[2] || {},
                  last_symbol: kf[1] || {}
                });
              } else if (kf && kf[0] === null) {
                entity_state_tracker.set(id, { is_active: false, last_geom: null, last_geom_sig: null });
              }
            }
          }
        } else if (year >= 1816 && year <= 1886) {
          //Epoch B: 1816-1886 (Spatiotemporally merge CShapes-Europe + preserve overseas polities)
          active_eu = sources.eu_geo.features.filter((f) => f.properties.From <= year && f.properties.To >= year);

          //B1. Map CShapes-Europe features by Seshat ID
          eu_by_polity = new Map();
          for (let i = 0; i < active_eu.length; i++) {
            let feat = active_eu[i];
            let p = feat.properties;
            let meta = sources.eu_meta.get(p.Id + "|" + p.Name) || sources.eu_meta.get(p.Name.toLowerCase()) || {
              cow: p.Id, cow_code: p.Id, name: p.Name, seshat_id: `(${p.Name})`
            };

            let s_key = meta.seshat_id;
            if (!eu_by_polity.has(s_key)) {
              eu_by_polity.set(s_key, {
                features: [],
                meta: meta,
                name: p.Name
              });
            }
            eu_by_polity.get(s_key).features.push(feat);
          }

          //B2. Process simplified polities: retain overseas polygons, merge European CShapes
          let handled_seshat_ids = new Set();

          for (let id of entity_meta_map.keys()) {
            let ent = sources.simp_data[id];
            if (!ent || !ent.history) continue;

            let st = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, ts);
            let s_id = st && st.properties && st.properties.seshat_id;

            //Metropole check
            let is_uk = (id === "87693477140" || id === "87692477137");
            let is_russia = (id === "10264500703");
            let is_france = (id === "82079236664");

            let eu_grp = null;
            if (is_uk) {
              eu_grp = (year <= 1852) ? eu_by_polity.get("gb_british_emp_1") : eu_by_polity.get("gb_british_emp_2");
              if (!eu_grp) eu_grp = eu_by_polity.get("gb_british_emp_1") || eu_by_polity.get("gb_british_emp_2");
            } else if (is_russia) eu_grp = eu_by_polity.get("ru_romanov_dyn_2");
            else if (is_france) eu_grp = eu_by_polity.get("fr_france_modern_1");
            else if (s_id && !s_id.startsWith("(") && id !== "84316578489" /* Guiana */ && id !== "21580921075" /* BNA */) {
              eu_grp = eu_by_polity.get(s_id);
            }

            if (!st || !st.geometry) {
              if (eu_grp) {
                handled_seshat_ids.add(eu_grp.meta.seshat_id);
                this.emitCShapesPolity(id, ts, eu_grp, spatial_index, entity_meta_map, entity_history_map, entity_state_tracker, entity_name_map);
              } else {
                this.deactivateEntity(id, ts, entity_history_map, entity_state_tracker);
              }
              continue;
            }

            let orig_geom = st.geometry;
            let polys = (orig_geom.type === "MultiPolygon") ? orig_geom.coordinates : [orig_geom.coordinates];
            let overseas_polys = [];

            for (let p = 0; p < polys.length; p++) {
              let r = polys[p][0];
              if (!this.isRingInEurope(r)) overseas_polys.push(polys[p]);
            }

            if (eu_grp) {
              //Metropole polity: combines European CShapes territory with Siberian/overseas territory
              handled_seshat_ids.add(eu_grp.meta.seshat_id);
              for (let f = 0; f < eu_grp.features.length; f++) {
                let g = eu_grp.features[f].geometry;
                if (g.type === "Polygon") overseas_polys.push(g.coordinates);
                else if (g.type === "MultiPolygon") {
                  for (let m = 0; m < g.coordinates.length; m++) overseas_polys.push(g.coordinates[m]);
                }
              }

              let combined_geom = (overseas_polys.length === 1)
                ? { coordinates: overseas_polys[0], type: "Polygon" }
                : { coordinates: overseas_polys, type: "MultiPolygon" };

              let color = this.inheritColorViaPOI(eu_grp.features[0], spatial_index, st.symbol ? st.symbol.polygonFill : "#7289da");
              let sym = { polygonFill: color, textSize: 14 };
              let canon_name = entity_name_map.get(id) || eu_grp.meta.name;
              let props = {
                cow: eu_grp.meta.cow || eu_grp.meta.cow_code,
                cow_code: eu_grp.meta.cow_code || eu_grp.meta.cow,
                name: canon_name,
                seshat_id: eu_grp.meta.seshat_id
              };

              this.emitKeyframe(id, ts, combined_geom, sym, props, entity_history_map, entity_state_tracker);
            } else if (overseas_polys.length > 0) {
              //Polity is purely overseas or colony (USA, Canada, Brazil, China, British Guiana)
              let retained_geom = (overseas_polys.length === 1)
                ? { coordinates: overseas_polys[0], type: "Polygon" }
                : { coordinates: overseas_polys, type: "MultiPolygon" };

              let s_props = Object.assign({}, st.properties);
              let s_sym = Object.assign({}, st.symbol);

              let meta = sources.eu_meta.get((s_props.name || "").toLowerCase()) || sources.c2_meta.get((s_props.name || "").toLowerCase());
              if (meta && meta.cow) {
                s_props.cow = meta.cow;
                s_props.cow_code = meta.cow;
              }
              if (entity_name_map.has(id)) s_props.name = entity_name_map.get(id);

              this.emitKeyframe(id, ts, retained_geom, s_sym, s_props, entity_history_map, entity_state_tracker);
            } else {
              //Stray European polygon replaced by CShapes-Europe; deactivate cleanly
              this.deactivateEntity(id, ts, entity_history_map, entity_state_tracker);
            }
          }

          //B3. Emit any remaining CShapes-Europe polities
          for (let s_key of eu_by_polity.keys()) {
            if (handled_seshat_ids.has(s_key)) continue;

            let grp = eu_by_polity.get(s_key);
            let target_id = seshat_to_entity_id.get(s_key) || global.PolitiesAtlasJoin.hashToSnowflakeId("cshapes_eu_" + s_key);
            this.emitCShapesPolity(target_id, ts, grp, spatial_index, entity_meta_map, entity_history_map, entity_state_tracker, entity_name_map);
          }
        } else {
          //Epoch C: Post-1886 (Polities switch directly to CShapes-2.0, non-state dependencies preserved)
          let curr_date_num = (date) ? (date.year * 10000 + (date.month || 1) * 100 + (date.day || 1)) : (year * 10000 + 101);
          active_c2 = sources.c2_geo.features.filter((f) => {
            let p = f.properties;
            let s = p.gwsyear * 10000 + p.gwsmonth * 100 + p.gwsday;
            let e = p.gweyear * 10000 + p.gwemonth * 100 + p.gweday;
            return curr_date_num >= s && curr_date_num <= e;
          });

          //C1. Group active CShapes-2.0 features by Seshat ID / polity
          c2_by_polity = new Map();
          for (let i = 0; i < active_c2.length; i++) {
            let feat = active_c2[i];
            let p = feat.properties;
            let meta = sources.c2_meta.get(p.gwcode + "|" + p.cntry_name) || sources.c2_meta.get(p.cntry_name.toLowerCase()) || {
              cow: p.gwcode, cow_code: p.gwcode, name: p.cntry_name, seshat_id: `(${p.cntry_name})`
            };

            //Special historical grouping for Burma and British Raj
            let s_key = meta.seshat_id;
            if (p.cntry_name.includes("Burma") || p.cntry_name.includes("Myanmar")) s_key = "(Burma)";
            if (p.cntry_name === "India" && year < 1947) s_key = "(British Raj)";

            if (!c2_by_polity.has(s_key)) {
              c2_by_polity.set(s_key, {
                features: [],
                meta: meta,
                name: p.cntry_name
              });
            }
            c2_by_polity.get(s_key).features.push(feat);
          }

          let c2_active_ids = new Set();

          //C2. Emit CShapes-2.0 polities
          for (let s_key of c2_by_polity.keys()) {
            let grp = c2_by_polity.get(s_key);
            let target_id = seshat_to_entity_id.get(s_key) || global.PolitiesAtlasJoin.hashToSnowflakeId("cshapes_c2_" + s_key);
            c2_active_ids.add(target_id);

            //Special case: WWII Germany Berlin coverage
            if (year >= 1933 && year <= 1945 && (grp.name.includes("Germany") || s_key.includes("germany"))) {
              target_id = "27376636343";
              c2_active_ids.add(target_id);
            }

            this.emitCShapesPolity(target_id, ts, grp, spatial_index, entity_meta_map, entity_history_map, entity_state_tracker, entity_name_map);
          }

          //C3. Preserve unmapped non-state territories from simplified (like Greenland, Svalbard, etc.)
          for (let id of entity_meta_map.keys()) {
            if (c2_active_ids.has(id)) continue;

            let ent = sources.simp_data[id];
            if (!ent || !ent.history) continue;

            let st = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, ts);
            if (st && st.geometry) {
              let name = st.properties && st.properties.name;
              let is_preserved_dep = name && (name.includes("Greenland") || name.includes("Svalbard") || id === "58904326755");
              if (is_preserved_dep) {
                let s_props = Object.assign({}, st.properties);
                if (entity_name_map.has(id)) s_props.name = entity_name_map.get(id);
                this.emitKeyframe(id, ts, st.geometry, st.symbol, s_props, entity_history_map, entity_state_tracker);
                continue;
              }
            }

            this.deactivateEntity(id, ts, entity_history_map, entity_state_tracker);
          }
        }

        if (Date.now() - last_log > 5000 || t_idx === ts_keys.length - 1) {
          let pct = Math.round(((t_idx + 1) / ts_keys.length) * 100);
          console.log(`[CShapesAtlasJoin] Progress: ${pct}% (TS ${t_idx + 1}/${ts_keys.length}, Year ${year})`);
          last_log = Date.now();
        }
      }

      //3. Reassemble finalized savefile
      console.log(`[CShapesAtlasJoin] Assembling finalized atlas_simplified.naissance savefile...`);
      let final_savefile = {};
      if (sources.simp_data.map_settings) final_savefile.map_settings = sources.simp_data.map_settings;

      //Preserve FeatureGroups and metadata
      for (let k in sources.simp_data) {
        let orig = sources.simp_data[k];
        if (orig.class_name !== "GeometryPolygon" && k !== "map_settings") {
          final_savefile[k] = orig;
        }
      }

      //Attach all GeometryPolygons
      for (let id of entity_meta_map.keys()) {
        let hist = entity_history_map.get(id);
        if (hist && Object.keys(hist).length > 0) {
          let ent_meta = entity_meta_map.get(id);
          final_savefile[id] = {
            class_name: "GeometryPolygon",
            history: hist,
            id: id,
            metadata: ent_meta.metadata || { description: "Simplified Polity", tags: ["Polities"] },
            type: "geometry"
          };
        }
      }

      console.log(`[CShapesAtlasJoin] Writing output to ${this.out_atlas_path}...`);
      out_stream = fs.createWriteStream(this.out_atlas_path, { encoding: "utf8" });
      out_stream.write("{\n");
      let all_keys = Object.keys(final_savefile);
      for (let i = 0; i < all_keys.length; i++) {
        let k = all_keys[i];
        let val_str = JSON.stringify(final_savefile[k]);
        let comma = (i < all_keys.length - 1) ? "," : "";
        out_stream.write(`  ${JSON.stringify(k)}: ${val_str}${comma}\n`);
      }
      out_stream.write("}\n");
      out_stream.end();

      await new Promise((resolve) => out_stream.on("finish", resolve));
      let stat = fs.statSync(this.out_atlas_path);
      console.log(`[CShapesAtlasJoin] Finished successfully! Written ${(stat.size / 1024 / 1024).toFixed(2)} MB to ${this.out_atlas_path}`);
    }

    /**
     * Helper to assemble and emit a CShapes polity feature group into the savefile.
     */
    static emitCShapesPolity (arg0_target_id, arg1_ts, arg2_grp, arg3_spatial_index, arg4_meta_map, arg5_history_map, arg6_state_tracker, arg7_name_map) {
      let grp = arg2_grp;
      let history_map = arg5_history_map;
      let meta_map = arg4_meta_map;
      let name_map = arg7_name_map;
      let spatial_index = arg3_spatial_index;
      let state_tracker = arg6_state_tracker;
      let target_id = arg0_target_id;
      let ts = arg1_ts;

      let combined_polys = [];
      for (let f = 0; f < grp.features.length; f++) {
        let g = grp.features[f].geometry;
        if (g.type === "Polygon") combined_polys.push(g.coordinates);
        else if (g.type === "MultiPolygon") {
          for (let m = 0; m < g.coordinates.length; m++) combined_polys.push(g.coordinates[m]);
        }
      }

      let merged_geom = (combined_polys.length === 1)
        ? { coordinates: combined_polys[0], type: "Polygon" }
        : { coordinates: combined_polys, type: "MultiPolygon" };

      let color = this.inheritColorViaPOI(grp.features[0], spatial_index, "#7289da");
      let sym = { polygonFill: color, textSize: 14 };

      //Prevent name mutations across keyframes by preserving existing canonical name
      let canon_name = (name_map && name_map.has(target_id)) ? name_map.get(target_id) : (grp.meta.name || grp.name);
      if (name_map && !name_map.has(target_id)) name_map.set(target_id, canon_name);

      let props = {
        cow: grp.meta.cow || grp.meta.cow_code,
        cow_code: grp.meta.cow_code || grp.meta.cow,
        name: canon_name,
        seshat_id: grp.meta.seshat_id
      };

      if (!meta_map.has(target_id)) {
        meta_map.set(target_id, {
          class_name: "GeometryPolygon",
          id: target_id,
          metadata: {
            description: `Simplified Polity: ${props.name}\nSeshatID: ${props.seshat_id}\nCOW: ${props.cow_code}\nBase Source: CShapes`,
            tags: ["Polities"]
          },
          type: "geometry"
        });
      }

      this.emitKeyframe(target_id, ts, merged_geom, sym, props, history_map, state_tracker);
    }
  };

  //Auto-execute if executed directly via Node CLI
  if (typeof require !== "undefined" && typeof module !== "undefined" && require.main === module) {
    global.CShapesAtlasJoin.run()
      .then(() => process.exit(0))
      .catch((err) => {
        console.error("[CShapesAtlasJoin] Fatal error:", err);
        process.exit(1);
      });
  }
})();
