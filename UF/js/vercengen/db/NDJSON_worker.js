//[VERCENGEN]

//Import libraries
let fs = require("node:fs");
let path = require("node:path");
let readline = require("node:readline");
let { parentPort, workerData } = require("node:worker_threads");

if (!global?.NDJSON) global.NDJSON = {};
if (!global.ve) global.ve = {};

require("../db_shared/NDJSON_history.js");

//Declare variables
let current_file_path = null;
let partition_cache = new Map();
let processing = false;
let queue = [];

//Internal helper functions
{
	/**
	 * Returns the cache partition directory in saves/.cache.
	 *
	 * @param {string} [arg0_file_path]
	 *
	 * @returns {string}
	 */
	NDJSON.getCacheDirectory = function (arg0_file_path) {
		let file_path = (arg0_file_path) ? arg0_file_path : "";
		let base_name = (file_path) ? path.basename(file_path, path.extname(file_path)) : "current";
		return path.resolve(process.cwd(), "saves/.cache", base_name);
	};
	NDJSON.getTempDirectory = NDJSON.getCacheDirectory;
	
	Object.getValue = function (arg0_object, arg1_variable_string) {
		//Convert from parameters
		let object = arg0_object;
		let variable_string = (arg1_variable_string) ? arg1_variable_string : "";
		
		//Return statement
		return variable_string.split(".")
			.reduce((local_object, local_key) => local_object?.[local_key], object);
	};
}

let extractCoordinates = function (obj, coords_acc) {
	if (!obj) return;
	
	if (Array.isArray(obj)) {
		if (obj.length >= 2 && typeof obj[0] === "number" && typeof obj[1] === "number") {
			coords_acc.push(obj[0], obj[1]);
		} else {
			for (let i = 0; i < obj.length; i++) extractCoordinates(obj[i], coords_acc);
		}
	} else if (typeof obj === "object") {
		if (obj.coordinates) {
			extractCoordinates(obj.coordinates, coords_acc);
		} else if (obj.geometry) {
			extractCoordinates(obj.geometry, coords_acc);
		} else if (obj.feature) {
			extractCoordinates(obj.feature, coords_acc);
		} else {
			for (let k in obj) {
				if (typeof obj[k] === "object") extractCoordinates(obj[k], coords_acc);
			}
		}
	}
};

let calculateBBox = function (raw_keyframes, entity) {
	let coords = [];
	
	if (raw_keyframes && typeof raw_keyframes === "object") {
		let ts = History.getTimestamps(raw_keyframes);
		for (let i = 0; i < ts.length; i++) {
			let kf = raw_keyframes[ts[i]];
			extractCoordinates(kf, coords);
			if (coords.length > 0) break;
		}
	}
	
	if (coords.length === 0 && entity?.value) {
		extractCoordinates(entity.value, coords);
	}
	
	if (coords.length === 0) return null;
	
	let max_x = -Infinity;
	let max_y = -Infinity;
	let min_x = Infinity;
	let min_y = Infinity;
	
	for (let i = 0; i < coords.length; i += 2) {
		let x = coords[i];
		let y = coords[i + 1];
		if (x < min_x) min_x = x;
		if (x > max_x) max_x = x;
		if (y < min_y) min_y = y;
		if (y > max_y) max_y = y;
	}
	
	//Return statement
	return [min_x, min_y, max_x, max_y];
};

let resolveHistory = function (data, timestamp, options) {
	if (!data) return null;
	
	let history_obj = typeof data.history === "string" ? JSON.parse(data.history) : data.history;
	if (!history_obj) return null;
	
	let raw_keyframes = (history_obj && history_obj.keyframes) ? history_obj.keyframes : history_obj;
	
	if (typeof raw_keyframes === "object" && raw_keyframes !== null) {
		if (options?.type === "get_keyframes")
			return History.getKeyframes(raw_keyframes);
		return History.getKeyframe(raw_keyframes, timestamp);
	}
	
	//Return statement
	return null;
};

let loadPartition = async function (page_file) {
	partition_cache.clear();
	
	if (!fs.existsSync(page_file)) return;
	
	let rs = fs.createReadStream(page_file);
	let rl = readline.createInterface({ input: rs });
	
	try {
		for await (let line of rl) {
			let clean = line.trim();
			if (clean.length === 0) continue;
			
			let match = clean.match(/^"([^"]+)"\s*:\s*(.*)$/);
			if (!match) continue;
			
			let key = match[1];
			let val_str = match[2];
			if (val_str.endsWith(",")) val_str = val_str.slice(0, -1);
			
			try {
				let entity = JSON.parse(val_str);
				let history_obj = typeof entity.history === "string" ? JSON.parse(entity.history) : entity.history;
				if (typeof entity.history === "string")
					entity.history = history_obj;
				let raw_keyframes = (history_obj && history_obj.keyframes) ? history_obj.keyframes : history_obj;
				let timestamps = (raw_keyframes && typeof raw_keyframes === "object") ? History.getTimestamps(raw_keyframes) : [];
				let bbox = calculateBBox(raw_keyframes, entity);
				
				partition_cache.set(key, {
					bbox: bbox,
					class_name: entity.class_name,
					entity: entity,
					id: key,
					metadata: entity.metadata,
					raw_keyframes: raw_keyframes,
					timestamps: timestamps,
					type: entity.type,
					value: entity.value
				});
			} catch (e) {}
		}
	} finally {
		rl.close();
		rs.destroy();
	}
};

let updateNDJSON = async function (page_file, getUpdatedValue) {
	let tmp_file = `${page_file}.tmp_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
	let updated = false;
	
	let dir = path.dirname(page_file);
	if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
	
	let ws = fs.createWriteStream(tmp_file);
	
	if (fs.existsSync(page_file)) {
		let rs = fs.createReadStream(page_file);
		let rl = readline.createInterface({ input: rs });
		
		try {
			for await (let line of rl) {
				let clean = line.trim();
				if (clean.length === 0) continue;
				let match = clean.match(/^"([^"]+)"\s*:\s*(.*)$/);
				
				if (match) {
					let key = match[1];
					let val_str = match[2];
					if (val_str.endsWith(",")) val_str = val_str.slice(0, -1);
					
					let newValue = getUpdatedValue(key, val_str);
					if (newValue !== undefined) {
						if (newValue !== null) ws.write(`"${key}":${JSON.stringify(newValue)}\n`);
						updated = true;
					} else {
						ws.write(clean + "\n");
					}
				} else {
					ws.write(clean + "\n");
				}
			}
		} finally {
			rl.close();
			rs.destroy();
		}
	}
	
	let extra_appends = getUpdatedValue(null, null, updated);
	if (extra_appends) {
		for (let [k, val] of Object.entries(extra_appends))
			if (val !== null) ws.write(`"${k}":${JSON.stringify(val)}\n`);
	}
	
	ws.end();
	await new Promise((r) => ws.on("finish", r));
	
	let attempts = 0;
	let renamed = false;
	while (!renamed && attempts < 10)
		try {
			fs.renameSync(tmp_file, page_file);
			renamed = true;
		} catch (e) {
			attempts++;
			if (attempts >= 10) throw e;
			await new Promise((r) => setTimeout(r, 50));
		}
};

parentPort.on("message", (task) => {
	if (task.type === "get_diagnostics") {
		let memory = process.memoryUsage();
		let v8_stats = require("node:v8").getHeapStatistics();
		
		return parentPort.postMessage({
			results: {
				cached_entities: partition_cache.size,
				heapLimit: v8_stats.heap_size_limit,
				heapTotal: memory.heapTotal,
				heapUsed: memory.heapUsed,
				percentage: parseFloat(((memory.heapUsed / v8_stats.heap_size_limit) * 100).toFixed(2)),
				rss: memory.rss,
				worker_id: workerData.worker_id
			},
			task_id: task.task_id
		});
	}
	
	queue.push(task);
	if (!processing) processQueue();
});

async function handleTask (arg0_task) {
	//Convert from parameters
	let task = arg0_task;
	
	//Declare local instance variables
	let {
		bbox,
		file_path,
		id,
		keyframes,
		limit_end,
		query,
		task_id,
		timestamp,
		type,
		update_map,
		zoom
	} = task;
	
	let base_path = file_path ? file_path.replace(/\.ndjson$/, "") : "";
	let folder_path = (NDJSON.getCacheDirectory) ?
		NDJSON.getCacheDirectory(base_path) :
		NDJSON.getTempDirectory(base_path);
	let page_file = path.join(folder_path, `partition_${workerData.worker_id}.ndjson`);
	if (!fs.existsSync(page_file)) {
		let legacy_file = path.join(folder_path, `${workerData.worker_id}.ndjson`);
		if (fs.existsSync(legacy_file)) {
			page_file = legacy_file;
		} else {
			let legacy_temp_dir = path.resolve(process.cwd(), "saves/.temp", path.basename(base_path, path.extname(base_path)));
			let legacy_temp_file = path.join(legacy_temp_dir, `partition_${workerData.worker_id}.ndjson`);
			if (fs.existsSync(legacy_temp_file))
				page_file = legacy_temp_file;
		}
	}
	
	//Ensure partition loaded in memory
	if (type === "init_partition" || current_file_path !== base_path || partition_cache.size === 0) {
		await loadPartition(page_file);
		current_file_path = base_path;
		if (type === "init_partition")
			return parentPort.postMessage({ results: true, task_id });
	}
	
	if (type === "diff") {
		let cached = partition_cache.get(id);
		let found = null;
		
		if (cached) {
			let state_val = resolveHistory(cached.entity, timestamp);
			found = {
				class_name: cached.class_name,
				id: id,
				key: id,
				value: (state_val !== null) ? state_val : cached.value
			};
		}
		
		return parentPort.postMessage({ results: found, task_id });
	}
	
	if (type === "diff_all") {
		let list = [];
		
		for (let [key, cached] of partition_cache) {
			let state_val = resolveHistory(cached.entity, timestamp);
			if (state_val !== null && state_val !== undefined) {
				list.push({
					class_name: cached.class_name,
					id: key,
					key: key,
					value: state_val
				});
			} else {
				list.push({
					class_name: cached.class_name,
					id: key,
					key: key,
					value: cached.value
				});
			}
		}
		
		return parentPort.postMessage({ results: list, task_id });
	}
	
	if (type === "diff_bbox") {
		let list = [];
		let q_min_x = -180;
		let q_min_y = -90;
		let q_max_x = 180;
		let q_max_y = 90;
		
		if (Array.isArray(bbox) && bbox.length >= 4) {
			q_min_x = bbox[0];
			q_min_y = bbox[1];
			q_max_x = bbox[2];
			q_max_y = bbox[3];
		}
		
		for (let [key, cached] of partition_cache) {
			if (cached.bbox) {
				let e_min_x = cached.bbox[0];
				let e_min_y = cached.bbox[1];
				let e_max_x = cached.bbox[2];
				let e_max_y = cached.bbox[3];
				
				if (e_max_x < q_min_x || e_min_x > q_max_x || e_max_y < q_min_y || e_min_y > q_max_y) {
					continue;
				}
			}
			
			let has_history = (cached.timestamps && cached.timestamps.length > 0);
			let resolved_value;
			
			if (has_history) {
				if (!cached.timestamps.some(ts => timestamp >= ts))
					continue;
				
				let state_val = resolveHistory(cached.entity, timestamp);
				if (!state_val || state_val[0] === null || state_val[0] === undefined)
					continue;
				
				resolved_value = state_val;
			} else {
				resolved_value = cached.value;
			}
			
			if (resolved_value && resolved_value[0] !== null && resolved_value[0] !== undefined) {
				list.push({
					class_name: cached.class_name,
					id: key,
					key: key,
					value: resolved_value
				});
			}
		}
		
		return parentPort.postMessage({ results: list, task_id });
	}
	
	if (type === "get_diffs") {
		let found = {};
		let target_ids = Array.isArray(task.ids) ? task.ids : [];
		
		for (let i = 0; i < target_ids.length; i++) {
			let tid = target_ids[i];
			let cached = partition_cache.get(tid);
			if (cached) {
				let state_val = resolveHistory(cached.entity, timestamp);
				found[tid] = {
					class_name: cached.class_name,
					key: tid,
					value: (state_val !== null) ? state_val : cached.value
				};
			}
		}
		
		return parentPort.postMessage({ results: found, task_id });
	}
	
	if (type === "get_hierarchy_values") {
		let list = [];
		
		for (let [key, cached] of partition_cache) {
			let entity_obj = cached.entity;
			let is_feature = (cached.type === "feature" || cached.class_name?.startsWith("Feature"));
			let resolved_name;
			
			if (!is_feature) {
				let state_val = resolveHistory(entity_obj, timestamp);
				if (state_val?.[2]?.name) {
					resolved_name = state_val[2].name;
				} else {
					let history_obj = typeof entity_obj?.history === "string" ?
						JSON.parse(entity_obj.history) : entity_obj?.history;
					let raw_keyframes = (history_obj && history_obj.keyframes) ?
						history_obj.keyframes : history_obj;
					if (raw_keyframes && typeof raw_keyframes === "object")
						resolved_name = History.getName(raw_keyframes);
				}
			}
			
			let name = entity_obj?.metadata?.name || entity_obj?.name || resolved_name || entity_obj?.id || key;
			
			list.push({
				class_name: cached.class_name,
				key: key,
				metadata: entity_obj?.metadata,
				name: name,
				type: cached.type,
				value: is_feature ? (typeof entity_obj?.value === "string" ? JSON.parse(entity_obj.value) : entity_obj?.value) : undefined
			});
		}
		
		return parentPort.postMessage({ results: list, task_id });
	}
	
	if (type === "get_keyframes") {
		let cached = partition_cache.get(id);
		let found = null;
		
		if (cached) {
			let state_val = resolveHistory(cached.entity, undefined, { type: "get_keyframes" });
			if (state_val !== null) found = { key: id, value: state_val };
		}
		
		return parentPort.postMessage({ results: found, task_id });
	}
	
	if (type === "get_value") {
		let cached = partition_cache.get(id);
		return parentPort.postMessage({ results: cached ? cached.entity : null, task_id });
	}
	
	if (type === "get_values") {
		let found = {};
		let target_ids = Array.isArray(task.ids) ? task.ids : [];
		
		for (let i = 0; i < target_ids.length; i++) {
			let tid = target_ids[i];
			let cached = partition_cache.get(tid);
			if (cached) found[tid] = cached.entity;
		}
		
		return parentPort.postMessage({ results: found, task_id });
	}
	
	if (type === "query") {
		let list = [];
		
		for (let [key, cached] of partition_cache) {
			if (limit_end !== undefined && list.length >= limit_end) break;
			
			let obj = cached.entity;
			let matches = true;
			
			for (let query_key in query) {
				if (Object.getValue(obj, query_key) !== query[query_key]) {
					matches = false;
					break;
				}
			}
			
			if (matches) {
				let result_obj = structuredClone(obj);
				result_obj._id = key;
				list.push(result_obj);
			}
		}
		
		return parentPort.postMessage({ results: list, task_id });
	}
	
	if (type === "set_keyframes") {
		let cached = partition_cache.get(id);
		if (cached) {
			let history_obj = typeof cached.entity.history === "string" ? JSON.parse(cached.entity.history) : cached.entity.history;
			if (!history_obj) history_obj = {};
			history_obj.keyframes = keyframes;
			cached.entity.history = history_obj;
			cached.raw_keyframes = keyframes;
			cached.timestamps = History.getTimestamps(keyframes);
			cached.bbox = calculateBBox(keyframes, cached.entity);
		}
		
		await updateNDJSON(page_file, (key, val_str, updated) => {
			if (key === null) return updated ? null : { [id]: { history: { keyframes } } };
			if (key === id) {
				try {
					let obj = JSON.parse(val_str);
					let is_history_string = typeof obj.history === "string";
					let history_obj = is_history_string ? JSON.parse(obj.history) : obj.history;
					if (!history_obj) history_obj = {};
					history_obj.keyframes = keyframes;
					obj.history = is_history_string ? JSON.stringify(history_obj) : history_obj;
					return obj;
				} catch (e) {
					return undefined;
				}
			}
			return undefined;
		});
		
		return parentPort.postMessage({ results: true, task_id });
	}
	
	if (type === "set_values") {
		for (let k in update_map) {
			let val = update_map[k];
			if (val === null) {
				partition_cache.delete(k);
			} else {
				let history_obj = typeof val.history === "string" ? JSON.parse(val.history) : val.history;
				let raw_keyframes = (history_obj && history_obj.keyframes) ? history_obj.keyframes : history_obj;
				let timestamps = (raw_keyframes && typeof raw_keyframes === "object") ? History.getTimestamps(raw_keyframes) : [];
				let bbox = calculateBBox(raw_keyframes, val);
				
				partition_cache.set(k, {
					bbox: bbox,
					class_name: val.class_name,
					entity: val,
					id: k,
					metadata: val.metadata,
					raw_keyframes: raw_keyframes,
					timestamps: timestamps,
					type: val.type,
					value: val.value
				});
			}
		}
		
		let updated_keys = new Set();
		await updateNDJSON(page_file, (key, val_str) => {
			if (key === null) {
				let rem = {};
				for (let k in update_map)
					if (!updated_keys.has(k)) rem[k] = update_map[k];
				return rem;
			}
			if (update_map.hasOwnProperty(key)) {
				updated_keys.add(key);
				return update_map[key];
			}
			return undefined;
		});
		
		return parentPort.postMessage({ results: true, task_id });
	}
}

async function processQueue () {
	processing = true;
	while (queue.length > 0) {
		let task = queue.shift();
		await handleTask(task);
	}
	processing = false;
}