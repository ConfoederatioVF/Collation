if (!global.proc) global.proc = {};
if (!proc.actions) proc.actions = {};

//Initialise batch feature action functions
{
  let turf = (global.turf) ? global.turf : (typeof require !== "undefined" ? require("../../../UF/js/geospatiale/turf.min.js") : null);

  /**
   * Cleans duplicate keyframes and redundant consecutive values.
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.entity_id
   *
   * @returns {Promise<Object>}
   */
  proc.actions.cleanKeyframes = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let entity_id = payload.entity_id;

    if (!entity_id || !global.db?.getValue)
      return { success: false, error: "Missing entity ID or db" };

    let entity = await db.getValue(entity_id);
    if (!entity) return { success: false, error: "Entity not found" };

    let hist = (typeof entity.history === "string") ? JSON.parse(entity.history) : (entity.history || {});
    let keyframes = hist.keyframes || hist;
    let timestamps = Object.keys(keyframes).map(Number).sort((a, b) => a - b);
    let cleaned_keyframes = {};
    let last_str = null;

    for (let i = 0; i < timestamps.length; i++) {
      let ts = String(timestamps[i]);
      let val = keyframes[ts];
      let val_str = JSON.stringify(val);

      if (val_str !== last_str) {
        cleaned_keyframes[ts] = val;
        last_str = val_str;
      }
    }

    if (global.db?.setKeyframes)
      await db.setKeyframes(entity_id, cleaned_keyframes);

    //Return statement
    return {
      cleaned_count: timestamps.length - Object.keys(cleaned_keyframes).length,
      entity_id: entity_id,
      success: true
    };
  };


  /**
   * Runs a spatial operation across all child geometries in a Feature.
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.feature_id
   *  @param {string} arg0_payload.operation_type - 'buffer'|'difference'|'intersect'|'union'|'xor'
   *  @param {string} [arg0_payload.ot_entity_id]
   *  @param {Object} [arg0_payload.options]
   *  @param {number|string} [arg0_payload.date]
   *
   * @returns {Promise<Object>}
   */
  proc.actions.featureOperation = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let date = (payload.date !== undefined) ? String(payload.date) : "0";
    let feature_id = payload.feature_id;
    let operation_type = payload.operation_type || "buffer";
    let options = (payload.options) ? payload.options : {};
    let ot_entity_id = payload.ot_entity_id;

    if (!feature_id || !global.db?.getValue)
      return { success: false, error: "Missing feature ID or db" };

    let feature_ent = await db.getValue(feature_id);
    if (!feature_ent) return { success: false, error: "Feature not found" };

    let raw_val = (typeof feature_ent.value === "string") ? JSON.parse(feature_ent.value) : (feature_ent.value || {});
    let child_ids = raw_val.entities || raw_val._entities || [];

    if (!Array.isArray(child_ids) || child_ids.length === 0)
      return { count: 0, feature_id: feature_id, success: true };

    let results = [];
    for (let i = 0; i < child_ids.length; i++) {
      let child_id = (typeof child_ids[i] === "object") ? child_ids[i].id : child_ids[i];
      if (!child_id) continue;

      let op_res = await proc.actions.geometryOperation({
        date: date,
        entity_id: child_id,
        options: options,
        ot_entity_id: ot_entity_id,
        type: operation_type
      });

      results.push(op_res);
    }

    //Return statement
    return {
      count: results.length,
      feature_id: feature_id,
      results: results,
      success: true
    };
  };


  /**
   * Flattens/unions all child geometries in a feature at a given date into a single combined geometry.
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.feature_id
   *  @param {number|string} [arg0_payload.date]
   *
   * @returns {Promise<Object>}
   */
  proc.actions.flattenGeometries = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let date = (payload.date !== undefined) ? String(payload.date) : "0";
    let feature_id = payload.feature_id;

    if (!feature_id || !global.db?.getValue)
      return { success: false, error: "Missing feature ID or db" };

    let feature_ent = await db.getValue(feature_id);
    if (!feature_ent) return { success: false, error: "Feature not found" };

    let raw_val = (typeof feature_ent.value === "string") ? JSON.parse(feature_ent.value) : (feature_ent.value || {});
    let child_ids = raw_val.entities || raw_val._entities || [];

    if (!Array.isArray(child_ids) || child_ids.length === 0)
      return { geometry: null, success: true };

    let combined_feature = null;

    for (let i = 0; i < child_ids.length; i++) {
      let child_id = (typeof child_ids[i] === "object") ? child_ids[i].id : child_ids[i];
      if (!child_id) continue;

      let child_ent = await db.getValue(child_id);
      if (!child_ent) continue;

      let hist = (typeof child_ent.history === "string") ? JSON.parse(child_ent.history) : (child_ent.history || {});
      let keyframes = hist.keyframes || hist;
      let kf = keyframes[date];
      if (!kf) continue;

      let geom_raw = (kf.value !== undefined) ? kf.value : kf;
      if (Array.isArray(geom_raw) && geom_raw[0]) geom_raw = geom_raw[0];
      let feat = proc.toTurfFeature(geom_raw);

      if (feat) {
        if (!combined_feature) {
          combined_feature = feat;
        } else {
          try {
            combined_feature = turf.union(turf.featureCollection([combined_feature, feat]));
          } catch (e) {}
        }
      }
    }

    //Return statement
    return {
      feature_id: feature_id,
      geometry: (combined_feature) ? (combined_feature.geometry || combined_feature) : null,
      success: true
    };
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = proc.actions;
