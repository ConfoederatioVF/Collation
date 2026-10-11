if (!global.proc) global.proc = {};
if (!proc.actions) proc.actions = {};

//Initialise temporal action functions
{
  /**
   * Moves a keyframe from an old timestamp to a new timestamp.
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.entity_id
   *  @param {number|string} arg0_payload.old_date
   *  @param {number|string} arg0_payload.new_date
   *
   * @returns {Promise<Object>}
   */
  proc.actions.moveKeyframe = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let entity_id = payload.entity_id;
    let new_date = (payload.new_date !== undefined) ? String(payload.new_date) : undefined;
    let old_date = (payload.old_date !== undefined) ? String(payload.old_date) : undefined;

    if (!entity_id || old_date === undefined || new_date === undefined || !global.db?.getValue)
      return { success: false, error: "Missing parameters or db" };

    let entity = await db.getValue(entity_id);
    if (!entity) return { success: false, error: "Entity not found" };

    let hist = (typeof entity.history === "string") ? JSON.parse(entity.history) : (entity.history || {});
    let keyframes = hist.keyframes || hist;

    if (keyframes[old_date] !== undefined) {
      keyframes[new_date] = keyframes[old_date];
      delete keyframes[old_date];

      if (global.db?.setKeyframes)
        await db.setKeyframes(entity_id, keyframes);
    }

    //Return statement
    return {
      entity_id: entity_id,
      new_date: new_date,
      old_date: old_date,
      success: true
    };
  };


  /**
   * Removes a keyframe from an entity at a given timestamp.
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.entity_id
   *  @param {number|string} arg0_payload.date
   *
   * @returns {Promise<Object>}
   */
  proc.actions.removeKeyframe = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let date = (payload.date !== undefined) ? String(payload.date) : undefined;
    let entity_id = payload.entity_id;

    if (!entity_id || date === undefined || !global.db?.getValue)
      return { success: false, error: "Missing parameters or db" };

    let entity = await db.getValue(entity_id);
    if (!entity) return { success: false, error: "Entity not found" };

    let hist = (typeof entity.history === "string") ? JSON.parse(entity.history) : (entity.history || {});
    let keyframes = hist.keyframes || hist;

    if (keyframes[date] !== undefined) {
      delete keyframes[date];

      if (global.db?.setKeyframes)
        await db.setKeyframes(entity_id, keyframes);
    }

    //Return statement
    return {
      date: date,
      entity_id: entity_id,
      success: true
    };
  };


  /**
   * Sets the full history object on an entity.
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.entity_id
   *  @param {Object|string} arg0_payload.history
   *
   * @returns {Promise<Object>}
   */
  proc.actions.setHistory = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let entity_id = payload.entity_id;
    let history = payload.history;

    if (!entity_id || history === undefined || !global.db?.getValue)
      return { success: false, error: "Missing parameters or db" };

    let parsed_history = (typeof history === "string") ? JSON.parse(history) : history;
    let keyframes = parsed_history.keyframes || parsed_history;

    if (global.db?.setKeyframes)
      await db.setKeyframes(entity_id, keyframes);

    //Return statement
    return {
      entity_id: entity_id,
      success: true
    };
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = proc.actions;
