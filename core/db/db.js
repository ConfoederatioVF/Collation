if (!global.db)
	/**
	 * The namespace for Naissance database access and state differencing.
	 *
	 * @namespace db
	 */
	global.db = {};

let is_renderer = Boolean(typeof window !== "undefined" || (typeof process !== "undefined" && process?.type === "renderer"));

//Initialise functions
{
	/**
	 * Returns a diff over `.history.keyframes` for the ID in question.
	 *
	 * @param {string} arg0_id
	 * @param {number|string} arg1_timestamp
	 *
	 * @returns {Promise<Object|null>}
	 */
	db.diff = async function (arg0_id, arg1_timestamp) {
		//Convert from parameters
		let id = arg0_id;
		let timestamp = arg1_timestamp;
		
		//Return statement
		if (!is_renderer && global.NDJSON?.diff) return await NDJSON.diff(id, timestamp);
		return await db.send("diff", id, timestamp);
	};
	
	/**
	 * Diffs all `.history.keyframes` for all entities at a given timestamp.
	 *
	 * @param {number|string} arg0_timestamp
	 *
	 * @returns {Promise<Object[]>}
	 */
	db.diffAll = async function (arg0_timestamp) {
		//Convert from parameters
		let timestamp = arg0_timestamp;
		
		//Return statement
		if (!is_renderer && global.NDJSON?.diffAll) return await NDJSON.diffAll(timestamp);
		return await db.send("diffAll", timestamp);
	};
	
	/**
	 * Returns diffs over `.history.keyframes` for entities intersecting the bounding box at the given timestamp.
	 *
	 * @param {Object} [arg0_options]
	 *  @param {number[]} [arg0_options.bbox] - [min_x, min_y, max_x, max_y]
	 *  @param {number|string} arg0_options.timestamp
	 *  @param {number} [arg0_options.zoom]
	 *
	 * @returns {Promise<Object[]>}
	 */
	db.diffBBox = async function (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Return statement
		if (!is_renderer && global.NDJSON?.diffBBox) return await NDJSON.diffBBox(options);
		return await db.send("diffBBox", options);
	};
	
	/**
	 * Resolves active RAM diagnostic percentage statistics from every worker in the pool.
	 *
	 * @returns {Promise<Array<{worker_id: number, rss: number, heapUsed: number, heapTotal: number, heapLimit: number, percentage: number}>>}
	 */
	db.getDiagnostics = async function () {
		//Return statement
		if (!is_renderer && global.NDJSON?.getDiagnostics) return await NDJSON.getDiagnostics();
		return await db.send("getDiagnostics");
	};
	
	/**
	 * Returns diffs over `.history.keyframes` for multiple IDs in 1-pass.
	 *
	 * @param {string[]} arg0_ids
	 * @param {number|string} arg1_timestamp
	 *
	 * @returns {Promise<Array<Object|null>>}
	 */
	db.getDiffs = async function (arg0_ids, arg1_timestamp) {
		//Convert from parameters
		let ids = arg0_ids;
		let timestamp = arg1_timestamp;
		
		//Return statement
		if (!is_renderer && global.NDJSON?.getDiffs) return await NDJSON.getDiffs(ids, timestamp);
		return await db.send("getDiffs", ids, timestamp);
	};
	
	/**
	 * Returns hierarchy metadata for all entities at a given timestamp.
	 *
	 * @param {number|string} [arg0_timestamp]
	 *
	 * @returns {Promise<Object[]>}
	 */
	db.getHierarchyValues = async function (arg0_timestamp) {
		//Convert from parameters
		let timestamp = (arg0_timestamp !== undefined) ? arg0_timestamp : 0;
		
		//Return statement
		if (!is_renderer && global.NDJSON?.getHierarchyValues) return await NDJSON.getHierarchyValues(timestamp);
		return await db.send("getHierarchyValues", timestamp);
	};
	
	/**
	 * Returns processed `.history.keyframes` for a given entity key.
	 *
	 * @param {string} arg0_id
	 *
	 * @returns {Promise<Object>}
	 */
	db.getKeyframes = async function (arg0_id) {
		//Convert from parameters
		let id = arg0_id;
		
		//Return statement
		if (!is_renderer && global.NDJSON?.getKeyframes) return await NDJSON.getKeyframes(id);
		return await db.send("getKeyframes", id);
	};
	
	/**
	 * Returns the cache partition directory in saves/.cache.
	 *
	 * @param {string} [arg0_file_path]
	 *
	 * @returns {string}
	 */
	db.getCacheDirectory = function (arg0_file_path) {
		//Convert from parameters
		let file_path = (arg0_file_path) ? arg0_file_path : (global.ve?.naissance_file_path || global.ve?.ndjson_file_path);
		let local_path = (global.path) ? global.path : ((typeof require === "function") ? require("node:path") : null);
		let base_name = (file_path && local_path) ? local_path.basename(file_path, local_path.extname(file_path)) : "current";
		
		//Return statement
		return (local_path) ? local_path.resolve(process.cwd(), "saves/.cache", base_name) : `saves/.cache/${base_name}`;
	};
	db.getTempDirectory = db.getCacheDirectory;
	
	/**
	 * Returns all unique global timestamps from all partitions.
	 *
	 * @returns {Promise<number[]>}
	 */
	db.getTimestamps = async function () {
		//Return statement
		if (!is_renderer && global.NDJSON?.getTimestamps) return await NDJSON.getTimestamps();
		return await db.send("getTimestamps");
	};
	
	/**
	 * Returns the Object value of a single ID.
	 *
	 * @param {string} arg0_id
	 *
	 * @returns {Promise<Object|null>}
	 */
	db.getValue = async function (arg0_id) {
		//Convert from parameters
		let id = arg0_id;
		
		//Return statement
		if (!is_renderer && global.NDJSON?.getValue) return await NDJSON.getValue(id);
		return await db.send("getValue", id);
	};
	
	/**
	 * Returns the Object values of multiple IDs in 1-pass.
	 *
	 * @param {string[]} arg0_ids
	 *
	 * @returns {Promise<Array<Object|null>>}
	 */
	db.getValues = async function (arg0_ids) {
		//Convert from parameters
		let ids = arg0_ids;
		
		//Return statement
		if (!is_renderer && global.NDJSON?.getValues) return await NDJSON.getValues(ids);
		return await db.send("getValues", ids);
	};
	
	/**
	 * Initialises the DB API for Naissance.
	 *
	 * @returns {Promise<boolean>}
	 */
	db.initialise = async function () {
		//Return statement
		return true;
	};
	
	/**
	 * Loads a savefile and streams it into partitioned NDJSON shards.
	 *
	 * @param {string} arg0_file_path
	 * @param {Object} [arg1_options]
	 *
	 * @returns {Promise<string>}
	 */
	db.load = async function (arg0_file_path, arg1_options) {
		//Convert from parameters
		let file_path = arg0_file_path;
		let options = (arg1_options) ? arg1_options : {};
		
		//Return statement
		if (!is_renderer && global.NDJSON?.load) return await NDJSON.load(file_path, options);
		return await db.send("load", file_path, options);
	};
	
	/**
	 * Queries entities matching specified criteria.
	 *
	 * @param {Object} [arg0_options]
	 *
	 * @returns {Promise<Object[]>}
	 */
	db.query = async function (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Return statement
		if (!is_renderer && global.NDJSON?.query) return await NDJSON.query(options);
		return await db.send("query", options);
	};
	
	/**
	 * Removes an entity by ID.
	 *
	 * @param {string} arg0_id
	 *
	 * @returns {Promise<boolean>}
	 */
	db.removeValue = async function (arg0_id) {
		//Convert from parameters
		let id = arg0_id;
		
		//Return statement
		if (!is_renderer && global.NDJSON?.removeValue) return await NDJSON.removeValue(id);
		return await db.send("removeValue", id);
	};
	
	/**
	 * Removes multiple entities by ID array.
	 *
	 * @param {string[]} arg0_ids
	 *
	 * @returns {Promise<boolean>}
	 */
	db.removeValues = async function (arg0_ids) {
		//Convert from parameters
		let ids = arg0_ids;
		
		//Return statement
		if (!is_renderer && global.NDJSON?.removeValues) return await NDJSON.removeValues(ids);
		return await db.send("removeValues", ids);
	};
	
	/**
	 * Saves partitioned shards back into a 100% compliant .naissance file.
	 *
	 * @param {string} [arg0_target_path]
	 *
	 * @returns {Promise<string>}
	 */
	db.save = async function (arg0_target_path) {
		//Convert from parameters
		let target_path = arg0_target_path;
		
		//Return statement
		if (!is_renderer && global.NDJSON?.save) return await NDJSON.save(target_path);
		return await db.send("save", target_path);
	};
	
	/**
	 * Internal dispatcher to call NDJSON methods via Blacktraffic or Electron IPC.
	 *
	 * @param {string} arg0_function_key
	 * @param {any[]} argn_arguments
	 *
	 * @returns {Promise<any>}
	 */
	db.send = async function (arg0_function_key, ...argn_arguments) {
		//Convert from parameters
		let function_key = arg0_function_key;
		
		//Renderer IPC
		if (is_renderer) {
			try {
				let electron_mod = (global.electron) ? global.electron : require("electron");
				return await electron_mod.ipcRenderer.invoke("ndjson:invoke", function_key, ...argn_arguments);
			} catch (e) {
				console.error(`[db] Failed to invoke NDJSON.${function_key} via IPC:`, e);
				return null;
			}
		}
		
		//Return statement
		if (global.Blacktraffic?.task) {
			return await Blacktraffic.task("ndjson", {
				args: [function_key, ...argn_arguments]
			});
		}
		
		console.error(`[db] Neither global.NDJSON nor IPC is available to execute ${function_key}`);
		return null;
	};
	
	/**
	 * Sets keyframes for a specific entity ID.
	 *
	 * @param {string} arg0_id
	 * @param {Object} arg1_keyframes
	 *
	 * @returns {Promise<boolean>}
	 */
	db.setKeyframes = async function (arg0_id, arg1_keyframes) {
		//Convert from parameters
		let id = arg0_id;
		let keyframes = arg1_keyframes;
		
		//Return statement
		if (!is_renderer && global.NDJSON?.setKeyframes) return await NDJSON.setKeyframes(id, keyframes);
		return await db.send("setKeyframes", id, keyframes);
	};
	
	/**
	 * Sets the value of a single entity ID.
	 *
	 * @param {string} arg0_id
	 * @param {Object} arg1_value
	 *
	 * @returns {Promise<boolean>}
	 */
	db.setValue = async function (arg0_id, arg1_value) {
		//Convert from parameters
		let id = arg0_id;
		let value = arg1_value;
		
		//Return statement
		if (!is_renderer && global.NDJSON?.setValue) return await NDJSON.setValue(id, value);
		return await db.send("setValue", id, value);
	};
	
	/**
	 * Sets multiple entity values across worker partitions.
	 *
	 * @param {Object} arg0_update_map
	 *
	 * @returns {Promise<boolean>}
	 */
	db.setValues = async function (arg0_update_map) {
		//Convert from parameters
		let update_map = arg0_update_map;
		
		//Return statement
		if (!is_renderer && global.NDJSON?.setValues) return await NDJSON.setValues(update_map);
		return await db.send("setValues", update_map);
	};
	
	/**
	 * Adjusts the concurrent thread pool size for DB workers.
	 *
	 * @param {number} arg0_count
	 *
	 * @returns {Promise<number>}
	 */
	db.setWorkerPoolSize = async function (arg0_count) {
		//Convert from parameters
		let count = arg0_count;
		
		//Return statement
		if (!is_renderer && global.NDJSON?.setWorkerPoolSize) return await NDJSON.setWorkerPoolSize(count);
		if (is_renderer) return await db.send("setWorkerPoolSize", count);
		return 1;
	};
}

if (!global.NDJSON && is_renderer) {
	global.NDJSON = new Proxy({ _is_renderer_proxy: true }, {
		get (target, prop) {
			if (prop === "_is_renderer_proxy") return true;
			if (prop === "getCacheDirectory") return db.getCacheDirectory;
			if (prop === "getTempDirectory") return db.getCacheDirectory;
			return async (...args) => await db.send(prop, ...args);
		}
	});
}
