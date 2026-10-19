//State mutation functions
{
	if (!DALS.deleted_ids) DALS.deleted_ids = new Set();

	/**
	 * Parses a user action inside Naissance. All user actions must be mapped to a valid JSON schema.
	 * @alias DALS.Timeline.parseAction
	 *
	 * @param {string} [arg0_key] - The key to push to the current DALS timeline.
	 * @param {Object[]} [arg1_json] - If no top-level ID is passed, the action is assumed to be global.
	 * @param {boolean} [arg2_do_not_push_action=false]
	 */
	DALS.Timeline.parseAction = async function (arg0_key, arg1_json, arg2_do_not_push_action) {
		//Convert from parameters
		let key = arg0_key;
		let json = (typeof arg1_json === "string") ? JSON.parse(arg1_json) : arg1_json;
		let do_not_push_action = arg2_do_not_push_action;
		
		//Initialise JSON
		if (json === undefined) json = [];
		
		//Allow callers to pass either a raw MVP array or a full action object
		if (!Array.isArray(json) && json.value !== undefined) {
			if (key === undefined)
				key = json.key || json.options?.key;
			
			json = (typeof json.value === "string") ?
				JSON.parse(json.value) : json.value;
		}
		if (json === undefined) json = [];
		if (!Array.isArray(json)) json = [json];
		
		//Declare local instance variables
		let scope_map = naissance.Action.scope_map;
		
		//Iterate over multi-value packet (MVP) and filter it down to superclass single-value packets (SVPs)
		for (let i = 0; i < json.length; i++) {
			//New handling (Actions Palette)
			if (json[i].feature_obj || json[i].geometry_obj || json[i].type) {
				let feature_obj = naissance.Feature.instances[json[i].feature_obj];
				let geometry_obj = naissance.Geometry.instances[json[i].geometry_obj]; 
				let naissance_obj;
				
				if (feature_obj) naissance_obj = feature_obj;
				if (geometry_obj) naissance_obj = geometry_obj;
				
				//Iterate over all scopes and handle their actions
				let scopes = naissance.Action.getScopes((naissance_obj || json[i].type));
				
				for (let x = 0; x < scopes.length; x++) {
					let local_scope_map = scope_map[scopes[x]];
					if (!local_scope_map) continue;
					
					//Iterate over all_scope_keys
					let all_scope_keys = Object.keys(local_scope_map);
					
					for (let y = 0; y < all_scope_keys.length; y++) {
						let local_action = local_scope_map[all_scope_keys[y]];
						
						if (json[i][local_action.key] !== undefined && typeof local_action.special_function === "function")
							await local_action.special_function({
								naissance_obj,
								...json[i]
							});
					}
				}
			} else {
				if (json[i].load_save || json[i].load_savefile) {
					if (json[i].load_save) {
						DALS.fromJSON(json[i].load_save);
						window.discordRPC.updateActivity("editing_default");
					}
					if (json[i].load_savefile) {
						DALS.load(json[i].load_savefile);
						if (window?.discordRPC?.updateActivity)
							window.discordRPC.updateActivity("editing_savefile", path.basename(json[i].load_savefile));
					}
				}
				if (json[i].set_date) {
					UI_DateMenu.setDate(json[i].set_date);
				} else if (json[i].refresh_date === true) {
					let is_playing = UI_DateMenu.isPlaying();
					let main_obj = (typeof main !== "undefined") ? main : (globalThis.main || global.main);
					
					if (global.ve?.ndjson_file_path) {
						if (main_obj?.renderer?.update)
							main_obj.renderer.update();
						
						Object.iterate(naissance.Geometry.instances, (local_key, local_value) => {
							let has_local_history = (local_value.history?.keyframes && Object.keys(local_value.history.keyframes).length > 0);
							if (has_local_history) {
								local_value.draw();
								local_value.update();
							}
						});
					} else {
						Object.iterate(naissance.Geometry.instances, (local_key, local_value) => {
							local_value.draw();
							local_value.update();
						});
					}
					
					naissance.GeometryMedia.syncToDate();
					naissance.Mapmode.draw();
					if (!is_playing) UI_Leftbar.refresh();
				}
			}
		}
		
		//Save action to current timeline if needed
		if (!do_not_push_action) {
			new DALS.Action({
				options: {
					key: key,
					name: String.formalise(key)
				},
				value: json
			});
			
			//Force all UI_LeftbarHierarchy instances to .refresh()
			UI_Leftbar.refresh();
		}
	};
}

//State save/load functions
{
	DALS.load = async function (arg0_file_path) {
		//Convert from parameters
		let file_path = path.resolve(arg0_file_path);
		let main_obj = (typeof main !== "undefined") ? main : (globalThis.main || global.main);
		
		console.log(`[DALS] Loading savefile via multithreaded DB: ${file_path}`);
		DALS.clearMap();
		
		if (global.db?.load) {
			let shard_folder = await db.load(file_path);
			
			//Load map settings from metadata.json if present
			let folder_path = (global.db?.getCacheDirectory) ?
				db.getCacheDirectory(file_path) :
				((global.NDJSON?.getCacheDirectory) ?
					NDJSON.getCacheDirectory(file_path) :
					path.resolve(process.cwd(), "saves/.cache", path.basename(file_path, path.extname(file_path))));
			let metadata_file = path.join(folder_path, "metadata.json");
			
			if (!global.ve) global.ve = {};
			global.ve.naissance_file_path = file_path;
			global.ve.ndjson_file_path = shard_folder || path.join(folder_path, "partition_0.ndjson");
			
			let metadata_json = {};
			if (fs.existsSync(metadata_file)) {
				try {
					let metadata_raw = fs.readFileSync(metadata_file, "utf8");
					if (metadata_raw.trim().length > 0)
						metadata_json = JSON.parse(metadata_raw);
				} catch (e) {
					console.error(e);
				}
			}
			
			//1. Populate UI Leftbar Hierarchy and instances BEFORE applying map settings and date
			let hierarchy_fn = global.db?.getHierarchyValues || global.NDJSON?.getHierarchyValues;
			if (hierarchy_fn) {
				let timestamp = (main_obj?.timestamp !== undefined) ? main_obj.timestamp :
					(main_obj?.date ? Date.getTimestamp(main_obj.date) : 0);
				let hierarchy_values = await hierarchy_fn(timestamp);
				
				if (Array.isArray(hierarchy_values)) {
					let feature_instances = [];
					
					for (let i = 0; i < hierarchy_values.length; i++) {
						let entry = hierarchy_values[i];
						let id = String(entry.key !== undefined ? entry.key : entry.id);
						let class_name = entry.class_name;
						
						if (class_name && naissance[class_name]) {
							if (class_name.startsWith("Feature")) {
								let feature_obj = new naissance[class_name](undefined, { metadata: entry.metadata });
								feature_obj.setID(id);
								if (entry.value) feature_obj.json = entry.value;
								if (entry.name) feature_obj._name = entry.name;
								feature_instances.push(feature_obj);
							} else if (class_name.startsWith("Geometry")) {
								let geom_obj = new naissance[class_name]({ is_import: true });
								geom_obj.setID(id);
								if (entry.metadata) geom_obj.metadata = entry.metadata;
								if (entry.name) geom_obj._name = entry.name;
							}
						}
					}
					
					//Second pass: deserialise features and attach their entities after all geometries exist
					for (let i = 0; i < feature_instances.length; i++) {
						let feature_obj = feature_instances[i];
						if (feature_obj.json && typeof feature_obj.fromJSON === "function") {
							feature_obj.fromJSON(feature_obj.json);
						}
					}
				}
			}
			
			//2. Load global timestamps for Timeline Chronology
			let global_timestamps = metadata_json?.timestamps;
			
			if (!global_timestamps || !Array.isArray(global_timestamps) || global_timestamps.length === 0) {
				let timestamps_fn = global.db?.getTimestamps || global.NDJSON?.getTimestamps;
				if (timestamps_fn) {
					try {
						global_timestamps = await timestamps_fn();
						if (Array.isArray(global_timestamps) && global_timestamps.length > 0)
							metadata_json.timestamps = global_timestamps;
					} catch (e) {
						console.error("[DALS] Error loading global timestamps:", e);
					}
				}
			}
			
			if (main_obj?.renderer && Array.isArray(global_timestamps))
				main_obj.renderer.timestamps = global_timestamps;
			
			//3. Apply map settings and date from metadata.json now that instances exist
			if (metadata_json && Object.keys(metadata_json).length > 0 && global.UI_MapSettings) {
				UI_MapSettings.fromJSON(metadata_json);
			}
			
			//4. Trigger hierarchy refresh and renderer update
			setTimeout(() => {
				try {
					if (global.UI_Leftbar?.refresh) UI_Leftbar.refresh();
				} catch (e) {
					console.error("[DALS] UI_Leftbar.refresh error:", e);
				}
				try {
					if (global.UI_LeftbarTimeline?.refresh) UI_LeftbarTimeline.refresh();
				} catch (e) {
					console.error("[DALS] UI_LeftbarTimeline.refresh error:", e);
				}
				try {
					if (main_obj?.renderer?.update) main_obj.renderer.update();
				} catch (e) {
					console.error("[DALS] renderer.update error:", e);
				}
			}, 100);
			
			//Reload cursor
			if (main_obj?.layers?.cursor_layer && main_obj?.brush?.cursor)
				main_obj.layers.cursor_layer.addGeometry(main_obj.brush.cursor);
				
			return;
		}
		
		//Fallback for non-db environment
		fs.readFile(file_path, "utf8", (err, data) => {
			if (err) {
				console.error(err);
				return;
			}
			DALS.fromJSON(data);
		});
	};
	
	DALS.clearMap = function () {
		//Clear _layers
		main._layers.province_layers = [];
		if (main._layers.provinces)
			main._layers.provinces.clear();
		if (main?.layers?.entity_layer)
			main.layers.entity_layer.clear();
		if (main?.layers?.selection_layer)
			main.layers.selection_layer.clear();
		if (main?.layers?.label_layer)
			main.layers.label_layer.clear();
		
		//Derender and remove all cached renderer entities
		if (main?.renderer?.rendered_entities) {
			for (let [id, inst] of main.renderer.rendered_entities) {
				if (typeof inst.remove === "function") {
					try { inst.remove(true); } catch (e) {}
				}
				if (main.renderer?.derenderEntity) {
					main.renderer.derenderEntity(inst);
				}
			}
			main.renderer.rendered_entities.clear();
		}
		
		//Clear geometries
		Object.iterate(naissance.Geometry.instances, (local_key, local_geometry) => {
			try { local_geometry.remove(true); } catch (e) {}
		});
		
		//Remove any lingering media canvases attached to the map container
		let map_container = (typeof map !== "undefined" && map?.getContainer) ? map.getContainer() : null;
		if (map_container) {
			let all_media_canvases = map_container.querySelectorAll("canvas.geometry-media-canvas");
			for (let i = 0; i < all_media_canvases.length; i++) {
				if (all_media_canvases[i].parentNode)
					all_media_canvases[i].parentNode.removeChild(all_media_canvases[i]);
			}
		}
		
		//Clear scene
		scene.map_component.clear();
		naissance.Feature.instances = {};
		naissance.Geometry.instances = {};
		if (DALS.deleted_ids) DALS.deleted_ids.clear();
	};
	
	DALS.fromJSON = function (arg0_json) {
		//Convert from parameters
		let json = (arg0_json) ? arg0_json : {};
		if (typeof json === "string") json = JSON.parse(json);
		
		//0. Clear map
		console.log(`DALS.fromJSON called.`);
		DALS.clearMap();
		
		//1. Handle main map
		if (json.map_settings)
			UI_MapSettings.fromJSON(json.map_settings);
		
		//2. Iterate over JSON to load in each class
		Object.iterate(json, (local_key, local_value) => {
			if (local_value.class_name) {
				//2.1. Handle naissance.Geometry classes
				if (local_value.type === "geometry") {
					let geometry_obj = new naissance[local_value.class_name]({ is_import: true });
					
					//ID/History/Metadata deserialisation
					if (local_value.id) geometry_obj.setID(local_value.id);
					geometry_obj.history.fromJSON(local_value.history);
					if (local_value.metadata) geometry_obj.metadata = local_value.metadata;
				}
				//2.2. Handle naissance.Feature classes
				else if (local_value.type === "feature") {
					let feature_obj = new naissance[local_value.class_name](undefined, {
						metadata: local_value.metadata
					});
					
					if (local_value.id) feature_obj.setID(local_value.id);
					if (local_value.is_visible === false) feature_obj._is_visible = false;
					if (local_value.value) feature_obj.json = local_value.value;
				}
			}
		});
		
		//3. Features must be rendered separately
		Object.iterate(naissance.Feature.instances, (local_key, local_feature) => {
			local_feature.fromJSON(local_feature.json);
			try {
				if (local_feature.draw) local_feature.draw();
				if (local_feature._is_visible === false) local_feature.hide();
			} catch (e) { console.warn(e); }
		});
		
		//4. Force all UI_LeftbarHierarchy instances to .refresh()
		setTimeout(() => {
			UI_Leftbar.refresh();
			main.renderer.update(); //Update renderer
		}, 100);
		
		//Reload cursor
		main.layers.cursor_layer.addGeometry(main.brush.cursor);
	};
	
	DALS.toJSON = function () {
		//Declare local instance variables
		let json_obj = {};
		
		//Set json_obj.map_settings
		try {
			if (global.map) json_obj.map_settings = UI_MapSettings.toJSON();
		} catch (e) { console.error(e); }
		
		//Iterate over all naissance.Geometry.instances and serialise them
		Object.iterate(naissance.Geometry.instances, (local_key, local_geometry) => {
			let local_history_json = local_geometry.history.toJSON();
			
			Object.iterate(local_history_json, (local_timestamp, local_value) => {
				if (local_value[0] && typeof local_value[0] === "object") {
					delete local_value[0].options;
					delete local_value[0].symbol;
				}
			});
			
			json_obj[local_geometry.id] = {
				id: local_geometry.id,
				class_name: local_geometry.class_name,
				history: local_history_json,
				metadata: local_geometry.metadata,
				type: "geometry"
			}
			
			//Visibility is handled via keyframes, so the same sort of handling naissance.Feature needs isn't required
		});
		
		//Iterate over all naissance.Feature.instances and serialise them
		Object.iterate(naissance.Feature.instances, (local_key, local_feature) => {
			json_obj[local_feature.id] = {
				id: local_feature.id,
				class_name: local_feature.class_name,
				metadata: local_feature.metadata,
				type: "feature",
				value: local_feature.toJSON()
			};
			
			let local_json = json_obj[local_feature.id];
			if (!local_feature._is_visible)
				local_json.is_visible = false;
		});
		
		//Return statement
		return json_obj;
	};
	
	/**
	 * Saves the current state either directly to disk (in legacy/in-memory mode)
	 * or via the NDJSON partition streaming pipeline (in DB mode).
	 *
	 * @param {string} [arg0_target_path]
	 *
	 * @returns {Promise<string>}
	 */
	DALS.save = async function (arg0_target_path) {
		//Convert from parameters
		let target_path = (arg0_target_path) ?
			path.resolve(arg0_target_path) :
			path.resolve(global.ve?.naissance_file_path || "saves/autosave.naissance");
		
		//DB Mode: Flush in-memory entities and stream shards into .naissance
		if (global.ve?.ndjson_file_path && global.db?.save) {
			let file_path = (global.db?.getFilePath) ? global.db.getFilePath() : global.ve.naissance_file_path;
			let folder_path = (global.NDJSON?.getCacheDirectory) ?
				global.NDJSON.getCacheDirectory(file_path) : null;
			
			//1. Update metadata.json with latest map settings
			if (folder_path && fs.existsSync(folder_path)) {
				let metadata_path = path.join(folder_path, "metadata.json");
				let current_meta = {};
				if (fs.existsSync(metadata_path)) {
					try { current_meta = JSON.parse(fs.readFileSync(metadata_path, "utf8")); } catch (e) {}
				}
				if (global.UI_MapSettings?.toJSON && global.map) {
					try {
						let live_settings = UI_MapSettings.toJSON();
						current_meta = { ...current_meta, ...live_settings };
					} catch (e) {}
				}
				try { fs.writeFileSync(metadata_path, JSON.stringify(current_meta, null, 2)); } catch (e) {}
			}
			
			//1.5. Flush any tracked deleted IDs into the DB
			if (DALS.deleted_ids && DALS.deleted_ids.size > 0 && global.db?.removeValues) {
				await db.removeValues(Array.from(DALS.deleted_ids));
				DALS.deleted_ids.clear();
			}
			
			//2. Flush modified in-memory instances into the DB
			let update_map = {};
			if (naissance.Geometry?.instances) {
				for (let id in naissance.Geometry.instances) {
					let inst = naissance.Geometry.instances[id];
					let kfs = inst.history?.keyframes;
					if (kfs && Object.keys(kfs).length > 0) {
						update_map[id] = {
							class_name: inst.class_name,
							history: inst.history.toJSON(),
							id: id,
							metadata: inst.metadata,
							type: "geometry"
						};
					}
				}
			}
			if (naissance.Feature?.instances) {
				for (let id in naissance.Feature.instances) {
					let feat = naissance.Feature.instances[id];
					update_map[id] = {
						class_name: feat.class_name,
						id: id,
						metadata: feat.metadata,
						type: "feature",
						value: (feat.toJSON ? feat.toJSON() : feat.value)
					};
				}
			}
			if (Object.keys(update_map).length > 0 && global.db?.setValues) {
				await db.setValues(update_map);
			}
			
			//3. Save through NDJSON streaming pipeline
			let saved_path = await db.save(target_path);
			global.ve.naissance_file_path = saved_path;
			
			//Return statement
			return saved_path;
		}
		
		//In-memory mode: Serialise and write directly
		let json_data = DALS.toJSON();
		let json_str = JSON.stringify(json_data, null, 2);
		let target_dir = path.dirname(target_path);
		if (!fs.existsSync(target_dir)) fs.mkdirSync(target_dir, { recursive: true });
		fs.writeFileSync(target_path, json_str, "utf8");
		global.ve.naissance_file_path = target_path;
		
		//Return statement
		return target_path;
	};
}