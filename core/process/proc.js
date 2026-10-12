{
  let path = (global.path) ? global.path : (typeof require !== "undefined" ? require("node:path") : null);

  if (!global.proc)
    /**
     * The namespace for all Naissance geoprocessing and action multithreading.
     *
     * @namespace proc
     */
    global.proc = {};

  if (!proc.actions) proc.actions = {};

  //Load headless action implementations
  try {
    if (typeof require !== "undefined" && path) {
      require(path.resolve(__dirname, "actions/spatial_actions.js"));
      require(path.resolve(__dirname, "actions/batch_feature_actions.js"));
      require(path.resolve(__dirname, "actions/attribute_actions.js"));
      require(path.resolve(__dirname, "actions/temporal_actions.js"));
    }
  } catch (e) {}
}

//Initialise util functions
{
  /**
   * Handles chained command execution returned from worker tasks.
   *
   * @param {Object} arg0_results_obj
   *
   * @returns {Promise<any[]>}
   */
  proc.handleCommandQueue = async function (arg0_results_obj) {
    //Convert from parameters
    let results_obj = (arg0_results_obj) ? arg0_results_obj : {};

    //Declare local instance variables
    let results = [];

    if (results_obj.cmd_queue)
      for (let i = 0; i < results_obj.cmd_queue.length; i++) {
        let local_cmd = results_obj.cmd_queue[i];
        let local_function = Object.getValue(global, local_cmd.function_key);
        local_cmd.value = (local_cmd.value) ? local_cmd.value : [];

        if (typeof local_function === "function")
          results.push(await local_function(...local_cmd.value));
      }

    //Return statement
    return results;
  };
}

//Initialise primary geoprocessing dispatch functions
{
  /**
   * Executes a geoprocessing action across worker threads or locally with automatic fallback.
   *
   * @param {string} arg0_action_key
   * @param {Object} arg1_payload
   * @param {Object} [arg2_options]
   *
   * @returns {Promise<any>}
   */
  proc.executeAction = async function (arg0_action_key, arg1_payload, arg2_options) {
    //Convert from parameters
    let action_key = arg0_action_key;
    let options = (arg2_options) ? arg2_options : {};
    let payload = (arg1_payload) ? arg1_payload : {};

    //1. Attempt dispatch via process worker pool
    if (global.proc?.IPC_task) {
      try {
        let res = await proc.IPC_task({
          action_key: action_key,
          payload: payload,
          type: action_key
        });
        //Return statement
        return res;
      } catch (err) {
        console.error(`[proc] Worker thread execution failed for ${action_key}:`, err);
      }
    }

    //2. Attempt dispatch via Blacktraffic IPC (Renderer to Main Process)
    if (global.Blacktraffic?.task) {
      try {
        let res = await proc.send({
          action_key: action_key,
          payload: payload,
          type: action_key
        });
        if (res && res.cmd_queue)
          res.results = await proc.handleCommandQueue(res.cmd_queue);
        //Return statement
        return res;
      } catch (err) {
        console.error(`[proc] Blacktraffic dispatch failed for ${action_key}:`, err);
      }
    }

    //3. Fallback to direct local execution in current thread
    let local_action = proc.actions[action_key];
    if (typeof local_action === "function") {
      //Return statement
      return await local_action(payload);
    }

    console.error(`[proc] Action "${action_key}" is not registered in proc.actions.`);
    //Return statement
    return { error: `Action ${action_key} not found`, success: false };
  };


  /**
   * Executes an action targeted at a Feature.
   *
   * @param {Object|string} arg0_feature_obj
   * @param {Object} arg1_json
   *
   * @returns {Promise<any>}
   */
  proc.feature = async function (arg0_feature_obj, arg1_json) {
    //Convert from parameters
    let feature_obj = arg0_feature_obj;
    let json = (arg1_json) ? arg1_json : {};

    //Declare local instance variables
    json.feature_obj = (typeof feature_obj === "string" && global.db?.getValue) ?
      await db.getValue(feature_obj) : feature_obj;
    json.type = json.type || "FeatureAction";

    //Return statement
    return await proc.executeAction(json.type, json);
  };


  /**
   * Executes an action targeted at a Geometry.
   *
   * @param {Object|string} arg0_geometry_obj
   * @param {Object} arg1_json
   *
   * @returns {Promise<any>}
   */
  proc.geometry = async function (arg0_geometry_obj, arg1_json) {
    //Convert from parameters
    let geometry_obj = arg0_geometry_obj;
    let json = (arg1_json) ? arg1_json : {};

    //Declare local instance variables
    json.geometry_obj = (typeof geometry_obj === "string" && global.db?.getValue) ?
      await db.getValue(geometry_obj) : geometry_obj;
    json.type = json.type || "GeometryAction";

    //Return statement
    return await proc.executeAction(json.type, json);
  };


  /**
   * Sends an action packet to Blacktraffic IPC for worker processing.
   *
   * @param {Object} arg0_json
   *
   * @returns {Promise<any>}
   */
  proc.send = async function (arg0_json) {
    //Convert from parameters
    let json = (arg0_json) ? arg0_json : {};

    if (global.Blacktraffic?.task) {
      //Return statement
      return await Blacktraffic.task("process", {
        args: [json]
      });
    }

    if (global.proc?.IPC_task) {
      //Return statement
      return await proc.IPC_task(json);
    }

    console.error("[proc] No IPC pipeline available for proc.send");
    //Return statement
    return null;
  };


  /**
   * Shuts down active worker pools.
   *
   * @returns {Promise<void>}
   */
  proc.terminate = async function () {
    if (global.proc?.IPC_terminate)
      await proc.IPC_terminate();
  };


  /**
   * Returns resource diagnostics from all process workers in the pool.
   *
   * @returns {Promise<Array<Object>>}
   */
  proc.getDiagnostics = async function () {
    if (global.proc?.IPC_getDiagnostics)
      return await proc.IPC_getDiagnostics();
    return [];
  };


  /**
   * Sets the concurrent thread pool size for process workers.
   *
   * @param {number} arg0_count
   *
   * @returns {Promise<number>}
   */
  proc.setWorkerPoolSize = async function (arg0_count) {
    if (global.proc?.IPC_setWorkerPoolSize)
      return await proc.IPC_setWorkerPoolSize(arg0_count);
    return 1;
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = proc;
