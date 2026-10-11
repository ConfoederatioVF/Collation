if (!global.proc) global.proc = {};
if (!proc.actions) proc.actions = {};

//Initialise attribute action functions
{
  /**
   * Adds a column of [timestamp, value] pairs to an entity.
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.entity_id
   *  @param {string} arg0_payload.key
   *  @param {Array<Array<number|string, any>>} arg0_payload.values
   *
   * @returns {Promise<Object>}
   */
  proc.actions.addColumn = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let entity_id = payload.entity_id;
    let key = payload.key;
    let values = payload.values || [];

    if (!entity_id || !key || !global.db?.getValue)
      return { success: false, error: "Missing parameters or db" };

    let entity = await db.getValue(entity_id);
    if (!entity) return { success: false, error: "Entity not found" };

    if (!entity.metadata) entity.metadata = {};
    if (!entity.metadata.variables) entity.metadata.variables = {};
    if (!entity.metadata.variables[key]) entity.metadata.variables[key] = {};

    for (let i = 0; i < values.length; i++) {
      let ts = String(values[i][0]);
      let val = values[i][1];
      entity.metadata.variables[key][ts] = val;
    }

    if (global.db?.setValue)
      await db.setValue(entity_id, entity);

    //Return statement
    return {
      entity_id: entity_id,
      key: key,
      success: true
    };
  };


  /**
   * Adds or updates a variable on an entity.
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.entity_id
   *  @param {string} arg0_payload.key
   *  @param {any} arg0_payload.value
   *  @param {number|string} [arg0_payload.date]
   *
   * @returns {Promise<Object>}
   */
  proc.actions.addVariable = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let date = (payload.date !== undefined) ? String(payload.date) : undefined;
    let entity_id = payload.entity_id;
    let key = payload.key;
    let value = payload.value;

    if (!entity_id || !key || !global.db?.getValue)
      return { success: false, error: "Missing parameters or db" };

    let entity = await db.getValue(entity_id);
    if (!entity) return { success: false, error: "Entity not found" };

    if (!entity.metadata) entity.metadata = {};
    if (!entity.metadata.variables) entity.metadata.variables = {};

    if (date !== undefined) {
      if (!entity.metadata.variables[key] || typeof entity.metadata.variables[key] !== "object")
        entity.metadata.variables[key] = {};
      entity.metadata.variables[key][date] = value;
    } else {
      entity.metadata.variables[key] = value;
    }

    if (global.db?.setValue)
      await db.setValue(entity_id, entity);

    //Return statement
    return {
      entity_id: entity_id,
      key: key,
      success: true,
      value: value
    };
  };


  /**
   * Evaluates a mathematical or logical expression across variables for an entity.
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.entity_id
   *  @param {string} arg0_payload.target_key
   *  @param {string} arg0_payload.expression
   *  @param {number|string} [arg0_payload.date]
   *
   * @returns {Promise<Object>}
   */
  proc.actions.calculateField = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let date = (payload.date !== undefined) ? String(payload.date) : undefined;
    let entity_id = payload.entity_id;
    let expression = payload.expression;
    let target_key = payload.target_key;

    if (!entity_id || !target_key || !expression || !global.db?.getValue)
      return { success: false, error: "Missing parameters or db" };

    let entity = await db.getValue(entity_id);
    if (!entity) return { success: false, error: "Entity not found" };

    let vars = entity.metadata?.variables || {};
    let scope = {};

    let var_keys = Object.keys(vars);
    for (let i = 0; i < var_keys.length; i++) {
      let vk = var_keys[i];
      let val = vars[vk];
      if (typeof val === "object" && val !== null && date !== undefined) {
        scope[vk] = (val[date] !== undefined) ? val[date] : 0;
      } else {
        scope[vk] = (typeof val === "number") ? val : parseFloat(val) || 0;
      }
    }

    let calculated_val = 0;
    try {
      let func = new Function(...Object.keys(scope), `return (${expression});`);
      calculated_val = func(...Object.values(scope));
    } catch (e) {
      console.error("[proc] calculateField evaluation error:", e);
      return { success: false, error: e.message };
    }

    return await proc.actions.addVariable({
      date: date,
      entity_id: entity_id,
      key: target_key,
      value: calculated_val
    });
  };


  /**
   * Removes a column from an entity.
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.entity_id
   *  @param {string} arg0_payload.key
   *
   * @returns {Promise<Object>}
   */
  proc.actions.removeColumn = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let entity_id = payload.entity_id;
    let key = payload.key;

    if (!entity_id || !key || !global.db?.getValue)
      return { success: false, error: "Missing parameters or db" };

    let entity = await db.getValue(entity_id);
    if (!entity) return { success: false, error: "Entity not found" };

    if (entity.metadata?.variables?.[key]) {
      delete entity.metadata.variables[key];
      if (global.db?.setValue)
        await db.setValue(entity_id, entity);
    }

    //Return statement
    return {
      entity_id: entity_id,
      key: key,
      success: true
    };
  };


  /**
   * Removes a property key from entity properties or metadata.
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.entity_id
   *  @param {string} arg0_payload.key
   *
   * @returns {Promise<Object>}
   */
  proc.actions.removeProperty = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let entity_id = payload.entity_id;
    let key = payload.key;

    if (!entity_id || !key || !global.db?.getValue)
      return { success: false, error: "Missing parameters or db" };

    let entity = await db.getValue(entity_id);
    if (!entity) return { success: false, error: "Entity not found" };

    if (entity.metadata?.[key] !== undefined) {
      delete entity.metadata[key];
      if (global.db?.setValue)
        await db.setValue(entity_id, entity);
    }

    //Return statement
    return {
      entity_id: entity_id,
      key: key,
      success: true
    };
  };


  /**
   * Removes a variable from an entity.
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.entity_id
   *  @param {string} arg0_payload.key
   *  @param {number|string} [arg0_payload.date]
   *
   * @returns {Promise<Object>}
   */
  proc.actions.removeVariable = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let date = (payload.date !== undefined) ? String(payload.date) : undefined;
    let entity_id = payload.entity_id;
    let key = payload.key;

    if (!entity_id || !key || !global.db?.getValue)
      return { success: false, error: "Missing parameters or db" };

    let entity = await db.getValue(entity_id);
    if (!entity) return { success: false, error: "Entity not found" };

    if (entity.metadata?.variables?.[key]) {
      if (date !== undefined && typeof entity.metadata.variables[key] === "object") {
        delete entity.metadata.variables[key][date];
      } else {
        delete entity.metadata.variables[key];
      }

      if (global.db?.setValue)
        await db.setValue(entity_id, entity);
    }

    //Return statement
    return {
      entity_id: entity_id,
      key: key,
      success: true
    };
  };


  /**
   * Sets or updates properties on an entity's metadata.
   *
   * @param {Object} arg0_payload
   *  @param {string} arg0_payload.entity_id
   *  @param {Object} arg0_payload.properties
   *
   * @returns {Promise<Object>}
   */
  proc.actions.setProperties = async function (arg0_payload) {
    //Convert from parameters
    let payload = (arg0_payload) ? arg0_payload : {};

    //Declare local instance variables
    let entity_id = payload.entity_id;
    let properties = payload.properties || {};

    if (!entity_id || !global.db?.getValue)
      return { success: false, error: "Missing entity ID or db" };

    let entity = await db.getValue(entity_id);
    if (!entity) return { success: false, error: "Entity not found" };

    if (!entity.metadata) entity.metadata = {};
    Object.assign(entity.metadata, properties);

    if (global.db?.setValue)
      await db.setValue(entity_id, entity);

    //Return statement
    return {
      entity_id: entity_id,
      properties: properties,
      success: true
    };
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = proc.actions;
