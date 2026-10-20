/**
 * - #### Internal Commands:
 * - `.clean_keyframes`: {@link Array}<{@link string}> - Arguments: ["symbol"]. Whether to clean keyframes, including the default `main.brush.getBrushSymbol()` (if symbol is enabled), as well as any duplicates.
 * - `.delete_geometry`: {@link boolean}
 * - `.geometry_operation`: {@link Object}
 *   - `.type`: {@link string} - Either 'buffer'/'difference'/'intersect'/'union'/'xor'.
 *   -
 *   - `.feature_id`: {@link string}
 *   - `.geometry_id`: {@link string}
 *
 *   - Special options ('buffer')
 *     - `.distance`: {@link number} - The number of kilometres to buffer by.
 * - `.merge_geometry`: {@link string} - Merges a geometry with the target geometry ID.
 * - `.move_keyframe`: {@link number}
 *   - `.date`: {@link Object} - The date of the keyframe to move.
 *   - `.ot_date`: {@link Object} - The date to move the keyframe to.
 * - `.remove_keyframe`: {@link number} - The timestamp of the removed keyframe.
 * - `.remove_property`: {@link Object}
 *   - `.date`: {@link number}|{@link Object} - Optional.
 *   - `.key`: {@link string}
 * - `.set_history`: {@link string} - The JSON `.history` string to set for the target Geometry.
 * - `.set_label_symbol`: {@link Object}
 * - `.set_name`: {@link string}
 * - `.set_polygon`: {@link string} - The JSON to set the polygon geometry to.
 * - `.set_properties`: {@link Object}
 *   - `<data_key>`: {@link any}
 * - `.set_tags`: {@link Array}<{@link string}>
 * - `.set_symbol`: {@link Object}
 *   - `<symbol_key>`: {@link any}
 * - `.set_zoom`: {@link Object}
 *   - `.is_start_keyframe=false`: {@link boolean}
 *   - `.max_zoom`: {@link number}|{@link string} - 'delete' if a number.
 *   - `.min_zoom`: {@link number}|{@link string} - 'delete' if a number.
 *
 * - Variables:
 * - `.add_column`: {@link Object}
 *   - `.key`: {@link string}
 *   - `.values`: {@link Array}<{@link Array}<{@link Object}|{@link number}, {@link any}, ...>> - [date, value] map.
 * - `.add_variable`: {@link Object}
 *   - `.date`: {@link Object}|{@link number}|{@link string} - If string, either 'start'/'end'.
 *   - `.key`: {@link string}
 *   - `.value`: {@link any}
 * - `.remove_column`: {@link string}
 * - `.remove_variable`: {@link Object}
 *   - `.date`: {@link Object}|{@link number}|{@link string} - If string, either 'start'/'end'.
 *   - `.key`: {@link string}
 */
//Debounced synchronization tracker to persist keyframes differentially to DB workers without blocking renderer
let db_sync_timeouts = new Map();
let db_pending_diffs = new Map();

let syncKeyframeToDB = function (arg0_id, arg1_date, arg2_keyframe) {
	let id = arg0_id;
	let date = arg1_date;
	let keyframe = arg2_keyframe;
	if (!id || (!global.db?.setKeyframe && !global.db?.setKeyframes)) return;
	
	let ts_key = (typeof date === "object") ? Date.getTimestamp(date) : date;
	ts_key = String(ts_key);
	
	if (!db_pending_diffs.has(id))
		db_pending_diffs.set(id, {});
	db_pending_diffs.get(id)[ts_key] = keyframe;
	
	if (db_sync_timeouts.has(id))
		clearTimeout(db_sync_timeouts.get(id));
	
	let timeout = setTimeout(() => {
		db_sync_timeouts.delete(id);
		let diff = db_pending_diffs.get(id);
		db_pending_diffs.delete(id);
		
		if (diff && Object.keys(diff).length > 0) {
			if (global.db?.setKeyframesDiff) {
				global.db.setKeyframesDiff(id, diff).catch(() => {});
			} else if (global.db?.setKeyframe && Object.keys(diff).length === 1) {
				let single_ts = Object.keys(diff)[0];
				global.db.setKeyframe(id, single_ts, diff[single_ts]).catch(() => {});
			}
		}
	}, 200);
	db_sync_timeouts.set(id, timeout);
};

let syncGeometryToDB = function (arg0_id, arg1_keyframes) {
	let id = arg0_id;
	let keyframes = arg1_keyframes;
	if (!id || !global.db?.setKeyframes) return;
	
	if (db_sync_timeouts.has(id))
		clearTimeout(db_sync_timeouts.get(id));
	
	let timeout = setTimeout(() => {
		db_sync_timeouts.delete(id);
		db_pending_diffs.delete(id);
		global.db.setKeyframes(id, keyframes).catch(() => {});
	}, 200);
	db_sync_timeouts.set(id, timeout);
};

config.actions.geometry_polygon = {
	create_polygon: {
		name: "Create Polygon",
		scope: ["GeometryPolygon"],
		
		special_function: async function (json) {
			//Create new polygon
			if (json.create_polygon.id) {
				let new_polygon = new naissance.GeometryPolygon();
				new_polygon.setID(json.create_polygon.id);
				if (json.create_polygon.name) {
					new_polygon.fire_action_silently = true;
					new_polygon.name = json.create_polygon.name;
					delete new_polygon.fire_action_silently;
				}
				if (main.brush.selected_feature)
					if (!json.create_polygon.do_not_refresh)
						UI_Leftbar.refresh();
			}
		}
	},
	
	add_to_polygon: {
		name: "Add to Polygon",
		scope: ["GeometryPolygon"],
		
		special_function: async function (json) {
			//Declare local instance variables
			let polygon_obj = json.naissance_obj;
			if (!polygon_obj && json.geometry_obj)
				polygon_obj = naissance.Geometry.instances[json.geometry_obj];
			
			if (polygon_obj && typeof polygon_obj.loadHistory === "function")
				if (!polygon_obj.history?.keyframes || Object.keys(polygon_obj.history.keyframes).length === 0)
					await polygon_obj.loadHistory();
			
			//Date range handling
			if (json.add_to_polygon.date_range && polygon_obj?.history) {
				await polygon_obj.history.callFunctionInDateRange(json.add_to_polygon.date_range, async (local_keyframe) => {
					await DALS.Timeline.parseAction("add_to_polygon", [{
						geometry_obj: polygon_obj.id,
						add_to_polygon: {
							date: local_keyframe,
							do_not_draw: true,
							geometry: json.add_to_polygon.geometry
						}
					}], true);
				});
				if (polygon_obj.draw) polygon_obj.draw();
				return;
			}

			let date = (json.add_to_polygon.date !== undefined) ? json.add_to_polygon.date : main.date;
			let has_history = Boolean(polygon_obj?.history && polygon_obj.history.getTimestamps().length > 0);
			let is_alive = true;
			if (has_history) {
				let ts = Date.getTimestamp(date);
				if (polygon_obj.history._hasTimestampAfter && !polygon_obj.history._hasTimestampAfter(ts))
					is_alive = false;
				let kf = polygon_obj.history.getKeyframe({ date: date });
				if (!kf?.value || kf.value[0] === null || kf.value[0] === undefined || kf.value[0] === "null" || kf.value[2]?.hidden)
					is_alive = false;
			}

			//Guard clause: do not create phantom geometries outside entity lifespan
			if (has_history && !is_alive) return;

			let geometry = (polygon_obj) ? polygon_obj.getGeometryKeyframeAtDate(date) : null;
			if (!geometry && !has_history)
				geometry = polygon_obj?.geometry || polygon_obj?.value?.[0];
			let ot_geometry = json.add_to_polygon.geometry;

			//Immediate in-memory calculation for active rendering geometry (0ms lag brushing)
			if (polygon_obj && polygon_obj.history && (geometry || ot_geometry)) {
					try {
						let turf_geom = (geometry) ? Geospatiale.convertMaptalksToTurf(geometry) : null;
						let turf_ot = (ot_geometry) ? Geospatiale.convertMaptalksToTurf(ot_geometry) : null;
						let target_json = null;
						
						if (turf_geom && turf_ot) {
							let union_res = null;
							try {
								union_res = (Geospatiale.unionComponentWise) ?
									Geospatiale.unionComponentWise(turf_geom, turf_ot) :
									turf.union(turf.featureCollection([turf_geom, turf_ot]));
							} catch (e) {
								console.error("[add_to_polygon] union error:", e);
								union_res = turf_ot || turf_geom;
							}

							if (union_res && union_res.geometry?.type === "GeometryCollection") {
								let poly_geoms = union_res.geometry.geometries.filter(
									g => g.type === "Polygon" || g.type === "MultiPolygon"
								);
								if (poly_geoms.length === 1) union_res = turf.feature(poly_geoms[0]);
								else if (poly_geoms.length > 1) union_res = turf.multiPolygon(poly_geoms.flatMap(g => (g.type === "Polygon") ? [g.coordinates] : g.coordinates));
							}
							if (union_res) {
								let m_obj = Geospatiale.convertTurfToMaptalks(union_res);
								target_json = (m_obj && typeof m_obj.toJSON === "function") ?
									m_obj.toJSON() : (union_res.feature || union_res);
							}
						} else if (turf_geom && !turf_ot) {
							let m_obj = Geospatiale.convertTurfToMaptalks(turf_geom);
							target_json = (m_obj && typeof m_obj.toJSON === "function") ?
								m_obj.toJSON() : (turf_geom.feature || turf_geom);
						} else if (!turf_geom && turf_ot) {
							let m_obj = Geospatiale.convertTurfToMaptalks(turf_ot);
							target_json = (m_obj && typeof m_obj.toJSON === "function") ?
								m_obj.toJSON() : (turf_ot.feature || turf_ot);
						}
						
						if (target_json !== null) {
							polygon_obj.addKeyframe(date, target_json);
							syncKeyframeToDB(polygon_obj.id, date, target_json);
							if (!json.add_to_polygon?.do_not_draw && polygon_obj.draw) polygon_obj.draw();
						}
						return;
					} catch (e) {
						console.error(e);
					}
				}
				
				//Offload to background worker for uninstantiated/batch entities
				if (global.proc?.executeAction) {
					let res = await proc.executeAction("addToPolygon", {
						date: date,
						entity_id: polygon_obj ? polygon_obj.id : (json.geometry_obj || json.entity_id),
						geometry: json.add_to_polygon.geometry
					});
					if (res && res.geometry && polygon_obj) {
						let m_obj = Geospatiale.convertTurfToMaptalks(res.geometry);
						let kf_val = (m_obj && typeof m_obj.toJSON === "function") ?
							m_obj.toJSON() : (res.geometry.feature || res.geometry);
						polygon_obj.addKeyframe(date, kf_val);
						if (polygon_obj.draw) polygon_obj.draw();
						return;
					}
				}
		}
	},
	geometry_operation: {
		name: "Geometry Operation",
		feature_name: "Operate on Geometries",
		scope: ["GeometryPolygon"],
		
		draw_function: function () {
			//Declare local instance variables
			let operation_names = {
				buffer: { name: "Buffer" },
				difference: { name: "Difference" },
				intersect: { name: "Intersect" },
				union: { name: "Union" },
				xor: { name: "XOR" }
			};
			let operation_target = () => (this.ui.geometry_operation_target || "geometry");
			let operation_type = () => (this.ui.geometry_operation_type || "union");
			
			//Return statement
			return {
				geometry_operation_target: veSelect({
					feature: { name: "Feature" },
					geometry: { name: "Geometry" }
				}, {
					name: "Merge With Entity Type",
					selected: operation_target(),
					onuserchange: (v) => this.ui.geometry_operation_target = v
				}),
				geometry_operation_geometry: new UI_GeometryDatalist(this.ui.geometry_operation_geometry, {
					name: "Geometry",
					filter_types: ["GeometryPolygon"],
					limit: () => {
						let target = operation_target();
						if (target === "geometry") return true;
						return false;
					},
					onuserchange: (v) => this.ui.geometry_operation_geometry = v
				}),
				geometry_operation_feature: new UI_FeatureDatalist(this.ui.geometry_operation_feature, {
					name: "Feature",
					filter_types: ["FeatureGroup", "FeatureLayer"],
					limit: () => {
						let target = operation_target();
						if (target === "feature") return true;
						return false;
					},
					onuserchange: (v) => this.ui.geometry_operation_feature = v
				}),
				operation_type: veSelect(operation_names, {
					name: "Operation Type",
					selected: operation_type(),
					onuserchange: (v) => this.ui.geometry_operation_type = v
				}),
				
				buffer_distance: veNumber(this.ui.geometry_operation_buffer_distance, {
					name: "Buffer Distance",
					limit: () => operation_type() === "buffer",
					onuserchange: (v) => this.ui.geometry_operation_buffer_distance = v
				}),
				
				confirm: veButton(() => {
					//Declare local instance variables
					let geometry_operation_type = operation_type();
					let options = {};
					let target = operation_target();
					let target_geometry_id = (target === "geometry") ? this.ui.geometry_operation_geometry : undefined;
					let target_feature_id = (target === "feature") ? this.ui.geometry_operation_feature : undefined;
					
					//Buffer handling
					let buffer_distance = Math.returnSafeNumber(this.ui.geometry_operation_buffer_distance, 0);
					if (geometry_operation_type === "buffer") {
						if (buffer_distance === 0) {
							veToast(`<icon>warning</icon> Buffer distance must not be 0.`);
							return;
						}
						
						options.distance = buffer_distance;
					}
					
					//Run feature operation
					DALS.Timeline.parseAction("geometry_operation", {
						[this.getDALSKey()]: this.id,
						geometry_operation: {
							type: geometry_operation_type,
							feature_id: target_feature_id,
							geometry_id: target_geometry_id,
							options: options
						}
					});
					
					let operation_name = operation_names[geometry_operation_type].name;
					let ot_name;
					if (target_geometry_id) ot_name = naissance.Geometry.instances[target_geometry_id]?.name;
					if (target_feature_id) ot_name = naissance.Feature.instances[target_feature_id]?.name;
					
					if (this instanceof naissance.Geometry) {
						veToast(`Performed ${operation_name} on ${this.name} using ${ot_name}.`);
					} else {
						let all_geometries = this.getAllGeometries();
						
						veToast(`Performed ${operation_name} on ${String.formatNumber(all_geometries.length)} geometries using ${ot_name}.`);
					}
				}, { name: "Confirm" })
			};
		},
		special_function: async function (json) {
			//Declare local instance variables
			let geometry_obj = json.naissance_obj;
			
			//Immediate in-memory execution for active rendering entity (0ms latency)
			if (geometry_obj && geometry_obj.history && typeof naissance?.Geometry?.operate === "function") {
				let maptalks_geometry = naissance.Geometry.operate.call(geometry_obj,
					json.geometry_operation.type,
					(json.geometry_operation.feature_id) ? json.geometry_operation.feature_id : json.geometry_operation.geometry_id,
					json.geometry_operation.options);
				maptalks_geometry = (maptalks_geometry === null) ? null : maptalks_geometry.toJSON();
				geometry_obj.history.addKeyframe(main.date, maptalks_geometry);
				if (geometry_obj.draw) geometry_obj.draw();
				syncKeyframeToDB(geometry_obj.id, main.date, maptalks_geometry);
				return;
			}
			
			if (global.proc?.executeAction) {
				let res = await proc.executeAction("geometryOperation", {
					date: main.date,
					entity_id: geometry_obj ? geometry_obj.id : (json.geometry_obj || json.entity_id),
					options: json.geometry_operation.options,
					ot_entity_id: (json.geometry_operation.feature_id) ? json.geometry_operation.feature_id : json.geometry_operation.geometry_id,
					type: json.geometry_operation.type
				});
				if (res && res.geometry !== undefined && geometry_obj) {
					let maptalks_geometry = (res.geometry) ? Geospatiale.convertTurfToMaptalks(res.geometry).toJSON() : null;
					geometry_obj.history.addKeyframe(main.date, maptalks_geometry);
					if (geometry_obj.draw) geometry_obj.draw();
					return;
				}
			}
		}
	},
	remove_from_polygon: {
		name: "Remove from Polygon",
		scope: ["GeometryPolygon"],
		
		special_function: async function (json) {
			//Declare local instance variables
			let polygon_obj = json.naissance_obj;
			if (!polygon_obj && json.geometry_obj)
				polygon_obj = naissance.Geometry.instances[json.geometry_obj];
			
			if (polygon_obj && typeof polygon_obj.loadHistory === "function")
				if (!polygon_obj.history?.keyframes || Object.keys(polygon_obj.history.keyframes).length === 0)
					await polygon_obj.loadHistory();
			
			if (json.remove_from_polygon) {
				//Date range handling
				if (json.remove_from_polygon.date_range && polygon_obj?.history) {
					await polygon_obj.history.callFunctionInDateRange(json.remove_from_polygon.date_range, async (local_keyframe) => {
						await DALS.Timeline.parseAction("remove_from_polygon", [{
							geometry_obj: polygon_obj.id,
							remove_from_polygon: {
								date: local_keyframe,
								do_not_draw: true,
								geometry: json.remove_from_polygon.geometry
							}
						}], true);
					});
					if (polygon_obj.draw) polygon_obj.draw();
					return;
				}

				let date = (json.remove_from_polygon.date !== undefined) ? json.remove_from_polygon.date : main.date;
				let has_history = Boolean(polygon_obj?.history && polygon_obj.history.getTimestamps().length > 0);
				let is_alive = true;
				if (has_history) {
					let ts = Date.getTimestamp(date);
					if (polygon_obj.history._hasTimestampAfter && !polygon_obj.history._hasTimestampAfter(ts))
						is_alive = false;
					let kf = polygon_obj.history.getKeyframe({ date: date });
					if (!kf?.value || kf.value[0] === null || kf.value[0] === undefined || kf.value[0] === "null" || kf.value[2]?.hidden)
						is_alive = false;
				}

				//Guard clause: do not subtract from a geometry that does not exist at this date
				if (!is_alive) return;

				let geometry = (polygon_obj) ? polygon_obj.getGeometryKeyframeAtDate(date) : null;
				if (!geometry) return;
				let ot_geometry = json.remove_from_polygon.geometry;

				//Immediate in-memory difference for active rendering geometry (0ms lag brushing)
				if (polygon_obj && polygon_obj.history && geometry) {
						try {
							let diff_succeeded = false;
							let turf_difference = null;
							let turf_existing = Geospatiale.convertMaptalksToTurf(geometry);
							let turf_remove = Geospatiale.convertMaptalksToTurf(ot_geometry);
							
							if (turf_existing && turf_remove) {
								let bbox_existing = turf.bbox(turf_existing);
								let bbox_remove = turf.bbox(turf_remove);
								let overlaps = !(
									bbox_existing[0] > bbox_remove[2] ||
									bbox_existing[2] < bbox_remove[0] ||
									bbox_existing[1] > bbox_remove[3] ||
									bbox_existing[3] < bbox_remove[1]
								);
								if (!overlaps) return;
								
								try {
									turf_difference = (Geospatiale.diffComponentWise) ?
										Geospatiale.diffComponentWise(turf_existing, turf_remove) :
										turf.difference(turf.featureCollection([turf_existing, turf_remove]));
									diff_succeeded = true;
								} catch (e) {
									console.error("[remove_from_polygon] diff error:", e);
								}
								
								//Clean up GeometryCollection if points/lines mixed in
								if (turf_difference && turf_difference.geometry?.type === "GeometryCollection") {
									let poly_geoms = turf_difference.geometry.geometries.filter(
										g => g.type === "Polygon" || g.type === "MultiPolygon"
									);
									if (poly_geoms.length === 0) {
										turf_difference = null;
									} else if (poly_geoms.length === 1) {
										turf_difference = turf.feature(poly_geoms[0]);
									} else {
										turf_difference = turf.multiPolygon(poly_geoms.flatMap(g => (g.type === "Polygon") ? [g.coordinates] : g.coordinates));
									}
								}
								
								if (diff_succeeded) {
									//Only erase polygon completely if subtractor legitimately covers the existing polygon
									let is_fully_covered = false;
									if (!turf_difference) {
										try {
											let existing_area = turf.area(turf_existing);
											let inter = turf.intersect(turf.featureCollection([turf_existing, turf_remove]));
											let inter_area = inter ? turf.area(inter) : 0;
											if (existing_area > 0 && inter_area >= existing_area * 0.999)
												is_fully_covered = true;
										} catch (cov_err) {}
									}
									
									if (turf_difference || is_fully_covered) {
										let diff_json = null;
										if (turf_difference) {
											let m_obj = Geospatiale.convertTurfToMaptalks(turf_difference);
											diff_json = (m_obj && typeof m_obj.toJSON === "function") ?
												m_obj.toJSON() : (turf_difference.feature || turf_difference);
										}
										polygon_obj.addKeyframe(date, diff_json);
										syncKeyframeToDB(polygon_obj.id, date, diff_json);
										if (!json.remove_from_polygon?.do_not_draw && polygon_obj.draw) polygon_obj.draw();
									}
								}
								return;
							}
						} catch (e) {
							console.error(e);
						}
					}
					
					//Offload to background worker for uninstantiated/batch entities
					if (global.proc?.executeAction) {
						let res = await proc.executeAction("removeFromPolygon", {
							date: date,
							entity_id: polygon_obj ? polygon_obj.id : (json.geometry_obj || json.entity_id),
							geometry: json.remove_from_polygon.geometry
						});
						if (res && res.geometry !== undefined && polygon_obj) {
							let maptalks_geom = (res.geometry) ? Geospatiale.convertTurfToMaptalks(res.geometry)?.toJSON() : null;
							if (!maptalks_geom && res.geometry) maptalks_geom = res.geometry.feature || res.geometry;
							polygon_obj.addKeyframe(date, maptalks_geom);
							if (polygon_obj.draw) polygon_obj.draw();
							return;
						}
					}
				}
		}
	},
	set_polygon: {
		name: "Set Polygon",
		scope: ["GeometryPolygon"],
		
		special_function: async function (json) {
			//Declare local instance variables
			let polygon_obj = json.naissance_obj;
			
			if (json.set_polygon && json.set_polygon.geometry) {
				let new_geometry = json.set_polygon.geometry;
				
				if (typeof new_geometry === "string")
					new_geometry = JSON.parse(new_geometry);
				polygon_obj.addKeyframe(main.date, new_geometry);
			}
		}
	},
	simplify_polygon: {
		name: "Simplify Polygon",
		feature_name: "Simplify All Polygons",
		scope: ["GeometryPolygon"],
		
		special_function: async function (json) {
			//Declare local instance variables
			let polygon_obj = json.naissance_obj;
			
			if (typeof json.simplify_polygon === "number") {
				let geometry = polygon_obj.geometry;
				let turf_simplify = turf.simplify(Geospatiale.convertMaptalksToTurf(geometry), { tolerance: json.simplify_polygon });
				
				polygon_obj.addKeyframe(main.date, (turf_simplify) ?
					Geospatiale.convertTurfToMaptalks(turf_simplify).toJSON() : null);
			} else if (typeof json.simplify_polygon === "object") {
				let tolerance = Math.returnSafeNumber(json.simplify_polygon.tolerance);
				
				if (tolerance) {
					let date = (json.simplify_polygon.date) ? json.simplify_polygon.date : main.date;
					
					if (json.simplify_polygon.date_range) {
						polygon_obj.history.callFunctionInDateRange(json.simplify_polygon.date_range, (local_keyframe) => {
							let local_simplify_options = json.simplify_polygon;
							delete local_simplify_options.date_range;
							
							DALS.Timeline.parseAction("simplify_polygon", [{
								geometry_obj: polygon_obj.id,
								simplify_polygon: {
									date: local_keyframe,
									tolerance: tolerance,
									...local_simplify_options
								}
							}], true);
						});
					} else {
						let geometry = (json.simplify_polygon.date) ?
							polygon_obj.getGeometryKeyframeAtDate(date) : polygon_obj.geometry;
						
						if (geometry) try {
							let turf_simplify = turf.simplify(Geospatiale.convertMaptalksToTurf(geometry), { tolerance: tolerance });
							if (json.simplify_polygon.truncate > 0)
								turf_simplify = turf.truncate(turf_simplify, { precision: json.simplify_polygon.truncate });
							
							polygon_obj.addKeyframe(date, (turf_simplify) ?
								Geospatiale.convertTurfToMaptalks(turf_simplify).toJSON() : null);
						} catch (e) {
							console.error(`Turf simplify:`, Geospatiale.convertMaptalksToTurf(geometry), geometry, e);
						}
					}
				}
			}
		}
	},
	simplify_polygon_for_all_keyframes: {
		name: "Simplify Polygon for All Keyframes",
		feature_name: "Simplify All Polygon Keyframes",
		scope: ["GeometryPolygon"],
		
		draw_function: function () {
			//Return statement
			return {
				simplify_threshold: veRange(Math.returnSafeNumber(this.ui.simplify_threshold, 0.01), {
					name: `Simplify Threshold`,
					onuserchange: (v) => this.ui.simplify_threshold = v
				}),
				truncate_coordinates: veNumber(Math.returnSafeNumber(this.ui.truncate_threshold, -1), {
					name: "Truncate Coordinates",
					onuserchange: (v) => this.ui.truncate_threshold = v
				}),
				confirm: veButton(() => {
					//Declare local instance variables
					let simplify_threshold = Math.returnSafeNumber(this.ui.simplify_threshold, 0.01);
					
					try {
						DALS.Timeline.parseAction(`simplify_polygon_for_all_keyframes`, [{
							[this.getDALSKey()]: this.id,
							simplify_polygon_for_all_keyframes: {
								tolerance: simplify_threshold,
								truncate: this.ui.truncate_threshold
							}
						}]);
						
						//Declare formatting strings
						let simplify_string = String.formatNumber(simplify_threshold, 2);
						
						if (this instanceof naissance.Feature) {
							veToast(`Simplified all geometries by ${simplify_string}.`);
						} else {
							veToast(`Simplified all keyframes in polygon by ${simplify_string}.`);
						}
					} catch (e) { console.error(e); }
				}, { name: "Confirm" })
			};
		},
		special_function: async function (json) {
			//Declare local instance variables
			let polygon_obj = json.naissance_obj;
			
			Object.iterate(polygon_obj.history.keyframes, (local_key, local_value) => {
				let local_geometry = local_value.value[0];
				
				if (local_geometry && local_geometry !== "undefined") {
					let geometry = maptalks.Geometry.fromJSON(local_geometry);
					
					if (geometry) try {
						let turf_simplify = turf.simplify(Geospatiale.convertMaptalksToTurf(geometry), {
							tolerance: json.simplify_polygon_for_all_keyframes.tolerance
						});
						if (json.simplify_polygon_for_all_keyframes.truncate > 0)
							turf_simplify = turf.truncate(turf_simplify, {
								precision: json.simplify_polygon_for_all_keyframes.truncate
							});
						
						local_value.value[0] = Geospatiale.convertTurfToMaptalks(turf_simplify).toJSON();
					} catch (e) { console.error(`Error simplifying ${polygon_obj.name}:`, local_value, e); }
				}
			});
		}
	}
};