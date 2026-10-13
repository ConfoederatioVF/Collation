if (!global.proc) global.proc = {};
if (!proc.actions) proc.actions = {};

//Initialise spatial helper functions
{
  let turf = (global.turf) ? global.turf : (typeof require !== "undefined" ? require("../../../UF/js/geospatiale/turf.min.js") : null);
  /**
   * Cleans rings within a GeoJSON geometry/feature.
   *
   * @param {Object} arg0_geometry
   *
   * @returns {Object|null}
   */
  proc.cleanRings = function (arg0_geometry) {
    //Convert from parameters
    let geometry = arg0_geometry;

    if (!geometry) return null;

    let target_geom = (geometry.type === "Feature") ? geometry.geometry : geometry;
    if (!target_geom || !target_geom.coordinates) return geometry;

    if (target_geom.type === "Polygon") {
      let valid_rings = [];

      for (let i = 0; i < target_geom.coordinates.length; i++) {
        let clean_ring = [];
        let local_ring = target_geom.coordinates[i];

        if (local_ring)
          for (let x = 0; x < local_ring.length; x++) {
            let point_a = local_ring[x];
            let point_b = clean_ring[clean_ring.length - 1];
            let is_duplicate = (point_b) ? (point_a[0] === point_b[0] && point_a[1] === point_b[1]) : false;

            if (!is_duplicate) clean_ring.push(point_a);
          }

        if (clean_ring.length >= 4) {
          valid_rings.push(clean_ring);
        } else {
          if (i === 0) return null;
        }
      }

      target_geom.coordinates = valid_rings;
      //Return statement
      return (valid_rings.length > 0) ? geometry : null;
    } else if (target_geom.type === "MultiPolygon") {
      let valid_polygons = [];

      for (let i = 0; i < target_geom.coordinates.length; i++) {
        let is_poly_valid = true;
        let local_polygon = target_geom.coordinates[i];
        let valid_rings = [];

        for (let x = 0; x < local_polygon.length; x++) {
          let clean_ring = [];
          let local_ring = local_polygon[x];

          if (local_ring)
            for (let y = 0; y < local_ring.length; y++) {
              let point_a = local_ring[y];
              let point_b = clean_ring[clean_ring.length - 1];
              let is_duplicate = (point_b) ? (point_a[0] === point_b[0] && point_a[1] === point_b[1]) : false;

              if (!is_duplicate) clean_ring.push(point_a);
            }

          if (clean_ring.length >= 4) {
            valid_rings.push(clean_ring);
          } else {
            if (x === 0) {
              is_poly_valid = false;
              break;
            }
          }
        }

        if (is_poly_valid && valid_rings.length > 0) valid_polygons.push(valid_rings);
      }

      target_geom.coordinates = valid_polygons;
      //Return statement
      return (valid_polygons.length > 0) ? geometry : null;
    }

    //Return statement
    return geometry;
  };


  /**
   * Normalises an input geometry or feature into a valid Turf.js Feature.
   *
   * @param {Object} arg0_geometry
   *
   * @returns {Object|null}
   */
  proc.toTurfFeature = function (arg0_geometry) {
    //Convert from parameters
    let geometry = arg0_geometry;

    if (!geometry) return null;

    if (geometry.type === "Feature") {
      let cleaned = proc.cleanRings(geometry);
      //Return statement
      return cleaned;
    }

    if (geometry.geometry && geometry.geometry.type) {
      let feature = turf.feature(geometry.geometry, geometry.properties || {});
      //Return statement
      return proc.cleanRings(feature);
    }

    if (["GeometryCollection", "LineString", "MultiLineString", "MultiPoint", "MultiPolygon", "Point", "Polygon"].includes(geometry.type)) {
      let feature = turf.feature(geometry);
      //Return statement
      return proc.cleanRings(feature);
    }

    //Return statement
    return null;
  };
}

//Initialise spatial action functions
{
  let turf = (global.turf) ? global.turf : (typeof require !== "undefined" ? require("../../../UF/js/geospatiale/turf.min.js") : null);

  /**
   * Adds/unions a geometry into a target entity at a given timestamp.
   *
   * @param {Object} arg0_payload
   *  @param {string} [arg0_payload.entity_id]
   *  @param {Object} [arg0_payload.entity_obj]
   *  @param {number|string} [arg0_payload.date]
   *  @param {Object} arg0_payload.geometry
   *
   * @returns {Promise<Object>}
   */
  proc.actions.addToPolygon = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let date = (payload.date !== undefined) ? String(payload.date) : "0";
    let entity_id = payload.entity_id;
    let entity_obj = payload.entity_obj;
    let incoming_geom = proc.toTurfFeature(payload.geometry);

    if (!entity_obj && entity_id && global.db?.getValue)
      entity_obj = await db.getValue(entity_id);

    if (!entity_obj) {
      console.error("[proc] addToPolygon: entity not found:", entity_id);
      return { success: false, error: "Entity not found" };
    }

    let existing_geom = null;
    let keyframes = {};

    if (entity_obj.history) {
      if (typeof entity_obj.history === "string") {
        try {
          let parsed_history = JSON.parse(entity_obj.history);
          keyframes = parsed_history.keyframes || parsed_history;
        } catch (e) {}
      } else if (typeof entity_obj.history === "object") {
        keyframes = entity_obj.history.keyframes || entity_obj.history;
      }
    }

    let target_ts = (date !== undefined) ? parseInt(date) : 0;
    let all_kf_ts = Object.keys(keyframes).map(k => parseInt(k)).filter(n => !isNaN(n)).sort((a, b) => a - b);
    let best_kf_ts = null;
    for (let i = 0; i < all_kf_ts.length; i++) {
      if (all_kf_ts[i] <= target_ts) best_kf_ts = all_kf_ts[i];
    }

    //If entity has history and target_ts is before its first keyframe, do not create phantom keyframe before birth
    if (all_kf_ts.length > 0 && best_kf_ts === null)
      return { entity_id: entity_id, success: false, error: "Cannot add before entity start date" };

    let keyframe_entry = (best_kf_ts !== null) ? keyframes[String(best_kf_ts)] : keyframes[date];
    if (keyframe_entry) {
      let raw_val = (keyframe_entry.value !== undefined) ? keyframe_entry.value : keyframe_entry;
      if (Array.isArray(raw_val) && raw_val[0]) raw_val = raw_val[0];
      //If entity has ended (value[0] is null), do not resurrect after end date
      if (all_kf_ts.length > 0 && (raw_val === null || raw_val === "null"))
        return { entity_id: entity_id, success: false, error: "Cannot add after entity end date" };
      if (raw_val) existing_geom = proc.toTurfFeature(raw_val);
    }

    let result_geom;
    if (existing_geom && incoming_geom) {
      try {
        let clean_existing = existing_geom;
        let clean_incoming = incoming_geom;

        try {
          let tr_ex = turf.truncate(existing_geom, { precision: 6, coordinates: 2, mutate: false });
          clean_existing = turf.buffer(tr_ex, 0) || existing_geom;
        } catch (e) {}

        try {
          let tr_in = turf.truncate(incoming_geom, { precision: 6, coordinates: 2, mutate: false });
          clean_incoming = turf.buffer(tr_in, 0) || incoming_geom;
        } catch (e) {}

        result_geom = turf.union(turf.featureCollection([clean_existing, clean_incoming]));
      } catch (e) {
        result_geom = incoming_geom || existing_geom;
      }

      if (result_geom && result_geom.geometry?.type === "GeometryCollection") {
        let poly_geoms = result_geom.geometry.geometries.filter(
          g => g.type === "Polygon" || g.type === "MultiPolygon"
        );
        if (poly_geoms.length === 1) {
          result_geom = turf.feature(poly_geoms[0]);
        } else if (poly_geoms.length > 1) {
          result_geom = turf.multiPolygon(poly_geoms.flatMap(g => (g.type === "Polygon") ? [g.coordinates] : g.coordinates));
        }
      }
    } else {
      result_geom = incoming_geom || existing_geom;
    }

    let serialised_geom = (result_geom) ? (result_geom.geometry || result_geom) : null;
    if (keyframes[date] && keyframes[date].value !== undefined) {
      keyframes[date].value = [serialised_geom];
    } else {
      keyframes[date] = [serialised_geom];
    }

    if (global.db?.setKeyframes && entity_id)
      await db.setKeyframes(entity_id, keyframes);

    //Return statement
    return {
      entity_id: entity_id,
      geometry: serialised_geom,
      success: true,
      timestamp: date
    };
  };


  /**
   * Buffers a geometry by distance in kilometres.
   *
   * @param {Object} arg0_payload
   *  @param {Object} arg0_payload.geometry
   *  @param {number} arg0_payload.distance
   *  @param {Object} [arg0_payload.options]
   *
   * @returns {Promise<Object>}
   */
  proc.actions.buffer = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let distance = (payload.distance !== undefined) ? payload.distance : 0;
    let options = (payload.options) ? payload.options : {};
    let turf_feature = proc.toTurfFeature(payload.geometry);

    if (!turf_feature) return { success: false, error: "Invalid geometry" };

    let buffered = turf.buffer(turf_feature, distance, {
      steps: options.steps || 8,
      units: options.units || "kilometers"
    });

    //Return statement
    return {
      geometry: (buffered) ? (buffered.geometry || buffered) : null,
      success: true
    };
  };


  /**
   * Computes the difference of geometry A minus geometry B.
   *
   * @param {Object} arg0_payload
   *  @param {Object} arg0_payload.geometry_a
   *  @param {Object} arg0_payload.geometry_b
   *
   * @returns {Promise<Object>}
   */
  proc.actions.difference = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let feat_a = proc.toTurfFeature(payload.geometry_a);
    let feat_b = proc.toTurfFeature(payload.geometry_b);

    if (!feat_a) return { geometry: null, success: true };
    if (!feat_b) return { geometry: feat_a.geometry || feat_a, success: true };

    let diff = null;
    try {
      diff = turf.difference(turf.featureCollection([feat_a, feat_b]));
    } catch (e) {
      console.error("[proc] difference error:", e);
    }

    //Return statement
    return {
      geometry: (diff) ? (diff.geometry || diff) : null,
      success: true
    };
  };


  /**
   * Executes a generalised geometry operation (buffer, difference, intersect, union, xor).
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.type - 'buffer'|'difference'|'intersect'|'union'|'xor'
   *  @param {Object} [arg0_payload.geometry_a]
   *  @param {Object} [arg0_payload.geometry_b]
   *  @param {string} [arg0_payload.entity_id]
   *  @param {string} [arg0_payload.ot_entity_id]
   *  @param {Object} [arg0_payload.options]
   *  @param {number|string} [arg0_payload.date]
   *
   * @returns {Promise<Object>}
   */
  proc.actions.geometryOperation = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let date = (payload.date !== undefined) ? String(payload.date) : "0";
    let entity_id = payload.entity_id;
    let geom_a = payload.geometry_a;
    let geom_b = payload.geometry_b;
    let options = (payload.options) ? payload.options : {};
    let ot_entity_id = payload.ot_entity_id;
    let type = (payload.type) ? payload.type : "union";

    if (!geom_a && entity_id && global.db?.getValue) {
      let ent_a = await db.getValue(entity_id);
      if (ent_a) geom_a = ent_a;
    }
    if (!geom_b && ot_entity_id && global.db?.getValue) {
      let ent_b = await db.getValue(ot_entity_id);
      if (ent_b) geom_b = ent_b;
    }

    let feat_a = proc.toTurfFeature(geom_a);
    let feat_b = proc.toTurfFeature(geom_b);
    let result_feat = null;

    if (type === "buffer") {
      let distance = (options.distance !== undefined) ? options.distance : 0;
      if (feat_b) {
        result_feat = turf.buffer(feat_b, distance, { units: options.units || "kilometers" });
      } else if (feat_a) {
        result_feat = turf.buffer(feat_a, distance, { units: options.units || "kilometers" });
      }
    } else if (type === "difference") {
      if (feat_a && feat_b) {
        result_feat = turf.difference(turf.featureCollection([feat_a, feat_b]));
      } else if (feat_a && !feat_b) {
        result_feat = feat_a;
      }
    } else if (type === "intersect") {
      if (feat_a && feat_b) {
        result_feat = turf.intersect(turf.featureCollection([feat_a, feat_b]));
      }
    } else if (type === "union") {
      if (feat_a && feat_b) {
        result_feat = turf.union(turf.featureCollection([feat_a, feat_b]));
      } else {
        result_feat = feat_a || feat_b;
      }
    } else if (type === "xor") {
      if (feat_a && feat_b) {
        let inter = turf.intersect(turf.featureCollection([feat_a, feat_b]));
        if (inter) {
          result_feat = turf.difference(turf.featureCollection([feat_a, inter]));
        } else {
          result_feat = turf.union(turf.featureCollection([feat_a, feat_b]));
        }
      } else {
        result_feat = feat_a || feat_b;
      }
    }

    let output_geometry = (result_feat) ? (result_feat.geometry || result_feat) : null;

    if (entity_id && global.db?.setKeyframes) {
      let ent = await db.getValue(entity_id);
      if (ent) {
        let keyframes = {};
        if (ent.history) {
          let raw_hist = (typeof ent.history === "string") ? JSON.parse(ent.history) : ent.history;
          keyframes = raw_hist.keyframes || raw_hist;
        }
        if (keyframes[date] && keyframes[date].value !== undefined) {
          keyframes[date].value = [output_geometry];
        } else {
          keyframes[date] = [output_geometry];
        }
        await db.setKeyframes(entity_id, keyframes);
      }
    }

    //Return statement
    return {
      entity_id: entity_id,
      geometry: output_geometry,
      success: true,
      type: type
    };
  };


  /**
   * Computes the intersection of geometry A and geometry B.
   *
   * @param {Object} arg0_payload
   *  @param {Object} arg0_payload.geometry_a
   *  @param {Object} arg0_payload.geometry_b
   *
   * @returns {Promise<Object>}
   */
  proc.actions.intersect = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let feat_a = proc.toTurfFeature(payload.geometry_a);
    let feat_b = proc.toTurfFeature(payload.geometry_b);

    if (!feat_a || !feat_b) return { geometry: null, success: true };

    let inter = null;
    try {
      inter = turf.intersect(turf.featureCollection([feat_a, feat_b]));
    } catch (e) {
      console.error("[proc] intersect error:", e);
    }

    //Return statement
    return {
      geometry: (inter) ? (inter.geometry || inter) : null,
      success: true
    };
  };


  /**
   * Merges a target geometry entity into a source geometry entity.
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.source_id
   *  @param {string} arg0_payload.target_id
   *  @param {number|string} [arg0_payload.date]
   *
   * @returns {Promise<Object>}
   */
  proc.actions.mergeGeometry = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let date = (payload.date !== undefined) ? String(payload.date) : undefined;
    let source_id = payload.source_id;
    let target_id = payload.target_id;

    if (!source_id || !target_id) return { success: false, error: "Missing source or target ID" };

    let source_ent = (global.db?.getValue) ? await db.getValue(source_id) : null;
    let target_ent = (global.db?.getValue) ? await db.getValue(target_id) : null;

    if (!source_ent || !target_ent) return { success: false, error: "Entities not found" };

    let source_hist = (typeof source_ent.history === "string") ? JSON.parse(source_ent.history) : (source_ent.history || {});
    let target_hist = (typeof target_ent.history === "string") ? JSON.parse(target_ent.history) : (target_ent.history || {});

    let source_keyframes = source_hist.keyframes || source_hist;
    let target_keyframes = target_hist.keyframes || target_hist;

    let target_dates = (date !== undefined) ? [date] : Object.keys(target_keyframes);

    for (let i = 0; i < target_dates.length; i++) {
      let local_date = target_dates[i];
      let tgt_val = target_keyframes[local_date];
      if (!tgt_val) continue;

      let tgt_raw = (tgt_val.value !== undefined) ? tgt_val.value : tgt_val;
      if (Array.isArray(tgt_raw) && tgt_raw[0]) tgt_raw = tgt_raw[0];
      let tgt_feat = proc.toTurfFeature(tgt_raw);
      if (!tgt_feat) continue;

      let src_val = source_keyframes[local_date];
      let src_raw = (src_val) ? ((src_val.value !== undefined) ? src_val.value : src_val) : null;
      if (Array.isArray(src_raw) && src_raw[0]) src_raw = src_raw[0];
      let src_feat = (src_raw) ? proc.toTurfFeature(src_raw) : null;

      let merged_feat;
      if (src_feat && tgt_feat) {
        try {
          merged_feat = turf.union(turf.featureCollection([src_feat, tgt_feat]));
        } catch (e) {
          merged_feat = tgt_feat;
        }
      } else {
        merged_feat = tgt_feat || src_feat;
      }

      let serialised = (merged_feat) ? (merged_feat.geometry || merged_feat) : null;
      if (source_keyframes[local_date] && source_keyframes[local_date].value !== undefined) {
        source_keyframes[local_date].value = [serialised];
      } else {
        source_keyframes[local_date] = [serialised];
      }
    }

    if (global.db?.setKeyframes)
      await db.setKeyframes(source_id, source_keyframes);

    //Return statement
    return {
      source_id: source_id,
      success: true,
      target_id: target_id
    };
  };


  /**
   * Subtracts/differences a geometry from a target polygon entity at a given timestamp.
   *
   * @param {Object} arg0_payload
   *  @param {string} [arg0_payload.entity_id]
   *  @param {Object} [arg0_payload.entity_obj]
   *  @param {number|string} [arg0_payload.date]
   *  @param {Object} arg0_payload.geometry
   *
   * @returns {Promise<Object>}
   */
  proc.actions.removeFromPolygon = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let date = (payload.date !== undefined) ? String(payload.date) : "0";
    let entity_id = payload.entity_id;
    let entity_obj = payload.entity_obj;
    let incoming_geom = proc.toTurfFeature(payload.geometry);

    if (!entity_obj && entity_id && global.db?.getValue)
      entity_obj = await db.getValue(entity_id);

    if (!entity_obj) return { success: false, error: "Entity not found" };

    let existing_geom = null;
    let keyframes = {};

    if (entity_obj.history) {
      if (typeof entity_obj.history === "string") {
        try {
          let parsed_history = JSON.parse(entity_obj.history);
          keyframes = parsed_history.keyframes || parsed_history;
        } catch (e) {}
      } else if (typeof entity_obj.history === "object") {
        keyframes = entity_obj.history.keyframes || entity_obj.history;
      }
    }

    let target_ts = (date !== undefined) ? parseInt(date) : 0;
    let best_kf_ts = null;
    let all_kf_ts = Object.keys(keyframes).map(k => parseInt(k)).filter(n => !isNaN(n)).sort((a, b) => a - b);
    for (let i = 0; i < all_kf_ts.length; i++) {
      if (all_kf_ts[i] <= target_ts) best_kf_ts = all_kf_ts[i];
    }

    //If entity has history and target_ts is before its first keyframe, do not modify
    if (all_kf_ts.length > 0 && best_kf_ts === null)
      return { entity_id: entity_id, success: false, error: "Cannot remove before entity start date" };

    let keyframe_entry = (best_kf_ts !== null) ? keyframes[String(best_kf_ts)] : keyframes[date];
    if (keyframe_entry) {
      let raw_val = (keyframe_entry.value !== undefined) ? keyframe_entry.value : keyframe_entry;
      if (Array.isArray(raw_val) && raw_val[0]) raw_val = raw_val[0];
      //If entity has ended (value[0] is null), do not resurrect after end date
      if (all_kf_ts.length > 0 && (raw_val === null || raw_val === "null"))
        return { entity_id: entity_id, success: false, error: "Cannot remove after entity end date" };
      if (raw_val) existing_geom = proc.toTurfFeature(raw_val);
    }

    let result_geom = null;
    if (existing_geom && incoming_geom) {
      let clean_existing = existing_geom;
      let clean_incoming = incoming_geom;

      try {
        let tr_ex = turf.truncate(existing_geom, { precision: 6, coordinates: 2, mutate: false });
        clean_existing = turf.buffer(tr_ex, 0) || existing_geom;
      } catch (e) {}

      try {
        let tr_in = turf.truncate(incoming_geom, { precision: 6, coordinates: 2, mutate: false });
        clean_incoming = turf.buffer(tr_in, 0) || incoming_geom;
      } catch (e) {}

      try {
        result_geom = turf.difference(turf.featureCollection([clean_existing, clean_incoming]));
      } catch (e) {
        console.error("[proc] removeFromPolygon error:", e);
      }

      if (result_geom && result_geom.geometry?.type === "GeometryCollection") {
        let poly_geoms = result_geom.geometry.geometries.filter(
          g => g.type === "Polygon" || g.type === "MultiPolygon"
        );
        if (poly_geoms.length === 0) {
          result_geom = null;
        } else if (poly_geoms.length === 1) {
          result_geom = turf.feature(poly_geoms[0]);
        } else {
          result_geom = turf.multiPolygon(poly_geoms.flatMap(g => (g.type === "Polygon") ? [g.coordinates] : g.coordinates));
        }
      }

      //Protect against accidental deletion: only allow result_geom to be null if incoming_geom legitimately covers existing_geom
      if (!result_geom) {
        let is_fully_covered = false;
        try {
          let ex_area = turf.area(existing_geom);
          let inter = turf.intersect(turf.featureCollection([existing_geom, incoming_geom]));
          let in_area = inter ? turf.area(inter) : 0;
          if (ex_area > 0 && in_area >= ex_area * 0.999)
            is_fully_covered = true;
        } catch (cov_e) {}

        if (!is_fully_covered)
          result_geom = existing_geom;
      }
    } else if (existing_geom && !incoming_geom) {
      result_geom = existing_geom;
    }

    let serialised_geom = (result_geom) ? (result_geom.geometry || result_geom) : null;
    if (keyframes[date] && keyframes[date].value !== undefined) {
      keyframes[date].value = [serialised_geom];
    } else {
      keyframes[date] = [serialised_geom];
    }

    if (global.db?.setKeyframes && entity_id)
      await db.setKeyframes(entity_id, keyframes);

    //Return statement
    return {
      entity_id: entity_id,
      geometry: serialised_geom,
      success: true,
      timestamp: date
    };
  };


  /**
   * Simplifies polygon coordinates using Douglas-Peucker algorithm.
   *
   * @param {Object} arg0_payload
   *  @param {Object} arg0_payload.geometry
   *  @param {number} [arg0_payload.tolerance=0.01]
   *  @param {boolean} [arg0_payload.highQuality=true]
   *
   * @returns {Promise<Object>}
   */
  proc.actions.simplifyPolygon = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let highQuality = (payload.highQuality !== undefined) ? payload.highQuality : true;
    let tolerance = (payload.tolerance !== undefined) ? payload.tolerance : 0.01;
    let turf_feature = proc.toTurfFeature(payload.geometry);

    if (!turf_feature) return { geometry: null, success: false, error: "Invalid geometry" };

    let simplified = turf.simplify(turf_feature, {
      highQuality: highQuality,
      tolerance: tolerance
    });

    //Return statement
    return {
      geometry: (simplified) ? (simplified.geometry || simplified) : null,
      success: true
    };
  };


  /**
   * Computes the union of geometry A and geometry B.
   *
   * @param {Object} arg0_payload
   *  @param {Object} arg0_payload.geometry_a
   *  @param {Object} arg0_payload.geometry_b
   *
   * @returns {Promise<Object>}
   */
  proc.actions.union = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let feat_a = proc.toTurfFeature(payload.geometry_a);
    let feat_b = proc.toTurfFeature(payload.geometry_b);

    if (!feat_a && !feat_b) return { geometry: null, success: true };
    if (!feat_a) return { geometry: feat_b.geometry || feat_b, success: true };
    if (!feat_b) return { geometry: feat_a.geometry || feat_a, success: true };

    let un = null;
    try {
      un = turf.union(turf.featureCollection([feat_a, feat_b]));
    } catch (e) {
      console.error("[proc] union error:", e);
      un = feat_a;
    }

    //Return statement
    return {
      geometry: (un) ? (un.geometry || un) : null,
      success: true
    };
  };


  /**
   * Computes symmetric difference (XOR) of geometry A and geometry B.
   *
   * @param {Object} arg0_payload
   *  @param {Object} arg0_payload.geometry_a
   *  @param {Object} arg0_payload.geometry_b
   *
   * @returns {Promise<Object>}
   */
  proc.actions.xor = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let feat_a = proc.toTurfFeature(payload.geometry_a);
    let feat_b = proc.toTurfFeature(payload.geometry_b);

    if (!feat_a && !feat_b) return { geometry: null, success: true };
    if (!feat_a) return { geometry: feat_b.geometry || feat_b, success: true };
    if (!feat_b) return { geometry: feat_a.geometry || feat_a, success: true };

    let xor_result = null;
    try {
      let inter = turf.intersect(turf.featureCollection([feat_a, feat_b]));
      if (inter) {
        xor_result = turf.difference(turf.featureCollection([feat_a, inter]));
      } else {
        xor_result = turf.union(turf.featureCollection([feat_a, feat_b]));
      }
    } catch (e) {
      console.error("[proc] xor error:", e);
    }

    //Return statement
    return {
      geometry: (xor_result) ? (xor_result.geometry || xor_result) : null,
      success: true
    };
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = proc.actions;
