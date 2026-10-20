if (!global.naissance) global.naissance = {};
naissance.History = class {
	static draw_keyframe_function (arg0_history, arg1_options) {
		//Convert from parameters
		let history_obj = arg0_history;
		let options = (arg1_options) ? arg1_options : {};
		
		//Declare local instance variables
		let components_obj = options.components_obj;
		let local_key = options.key;
		let local_value = options.value;
		let kf_localisation = (typeof local_value?.localisation === "string") ? local_value.localisation : "";
		let kf_ts = (local_value && typeof local_value.timestamp === "number") ? local_value.timestamp : parseInt(local_key);
		
		//Set components_obj
		components_obj[`t_${local_key}`] = new ve.Interface({
			date_info: new ve.HTML(String.formatDate(parseInt(local_key)), {
				tooltip: `Timestamp: ${kf_ts}`,
				x: 0, y: 0
			}),
			localisation: veHTML(() => kf_localisation, { x: 1, y: 0 }),
			actions_bar: veRawInterface({
				jump_to_date: veButton((e) => {
					let cur_kf = history_obj.keyframes?.[local_key];
					let cur_val = cur_kf?.value || cur_kf;
					let is_geom_removed = false;
					let target_key = parseInt(local_key);
					
					if (Array.isArray(cur_val)) {
						is_geom_removed = (cur_val[0] === null || cur_val[0] === "null" || cur_val[2]?.hidden === true);
					} else if (cur_val && Array.isArray(cur_val.value)) {
						is_geom_removed = (cur_val.value[0] === null || cur_val.value[0] === "null" || cur_val.value[2]?.hidden === true);
					}
					
					if (is_geom_removed) {
						let all_timestamps = (history_obj.getTimestamps) ? history_obj.getTimestamps() : [];
						let first_ts = (all_timestamps.length > 0) ? parseInt(all_timestamps[0]) : 0;
						target_key = Math.max(first_ts, target_key - 1);
					}
					
					DALS.Timeline.parseAction("load_date", [
						{ set_date: Date.convertTimestampToDate(target_key) },
						{ refresh_date: true }
					]);
				}, {
					name: "<icon>arrow_forward</icon>",
					tooltip: "Jump to Date"
				}),
				move_keyframe: veButton(() => {
					let cur_kf = history_obj.keyframes?.[local_key];
					let move_ts = cur_kf?.timestamp || kf_ts;
					let move_keyframe_window = veWindow({
						new_date: veDate(move_ts, { name: "New Date" }),
						confirm: veButton(() => {
							DALS.Timeline.parseAction("move_keyframe", [{
								geometry_obj: history_obj.options._id(),
								move_keyframe: {
									date: move_ts,
									ot_date: move_keyframe_window.new_date.v
								}
							}]);
							move_keyframe_window.close();
						})
					}, {
						can_rename: false,
						name: "Move Keyframe"
					});
				}, {
					name: "<icon>height</icon>",
					tooltip: "Move Keyframe to Date"
				}),
				remove_keyframe: veButton((e) => {
					DALS.Timeline.parseAction("delete_keyframe", [
						{ geometry_obj: history_obj.options._id(), remove_keyframe: local_key },
						{ refresh_date: true }
					]);
				}, {
					name: "<icon>delete</icon>",
					tooltip: "Delete Keyframe"
				})
			}, {
				attributes: { class: "actions-bar" },
				x: 2, y: 0
			})
		}, {
			attributes: { "naissance-ui": "HistoryKeyframes" },
			gc: true,
			is_folder: false
		});
		
		let local_keyframe_ui = components_obj[`t_${local_key}`];
		local_keyframe_ui.element.addEventListener("contextmenu", (e) => {
			if (history_obj.keyframe_context_menu) history_obj.keyframe_context_menu.close();
			let cur_kf = history_obj.keyframes?.[local_key];
			
			history_obj.keyframe_context_menu = veContextMenu({
				copy_timestamp: veButton(() => {
					navigator.clipboard.writeText(local_key);
					veToast(`Copied timestamp to keyboard.`);
				}, { name: "Copy Timestamp" }),
				copy_geometry_to_date: veButton(() => {
					let geom_to_copy = cur_kf?.value?.[0];
					if (geom_to_copy !== undefined) {
						history_obj.addKeyframe(main.timestamp, geom_to_copy);
						veToast(`Copied geometry keyframe to present date.`);
					}
				}, { name: "Copy Geometry To Date" }),
				
				//Edit Symbol, Edit Properties
				edit_symbol_button: veButton(() => {
					if (history_obj.edit_symbol_object_window) history_obj.edit_symbol_object_window.close();
					let sym_val = cur_kf?.value?.[1];
					history_obj.edit_symbol_object_window = veWindow({
						symbol_obj: veObjectEditor(sym_val, {
							onuserchange: (v) => history_obj.edit_symbol_object = v
						}),
						confirm: veButton(() => {
							if (history_obj.edit_symbol_object)
								if (Object.keys(history_obj.edit_symbol_object).length > 0) {
									history_obj.addKeyframe(local_key, undefined, history_obj.edit_symbol_object);
									veToast(`Edited symbol at timestamp.`);
								} else {
									if (cur_kf?.value) cur_kf.value[1] = undefined;
									veToast(`Deleted symbol at timestamp.`);
								}
							history_obj.getKeyframe({ refresh_localisation: true });
						}, { name: "Confirm" })
					}, { name: "Edit Symbol", can_rename: false, width: "20rem" })
				}, { name: "Edit Symbol" }),
				edit_properties_button: veButton(() => {
					if (history_obj.edit_properties_object_window) history_obj.edit_properties_object_window.close();
					let prop_val = cur_kf?.value?.[2];
					history_obj.edit_properties_object_window = veWindow({
						symbol_obj: veObjectEditor(prop_val, {
							onuserchange: (v) => history_obj.edit_properties_object = v
						}),
						confirm: veButton(() => {
							if (history_obj.edit_properties_object)
								if (Object.keys(history_obj.edit_properties_object).length > 0) {
									history_obj.addKeyframe(local_key, undefined, undefined, history_obj.edit_properties_object);
									veToast(`Edited properties at timestamp.`);
								} else {
									if (cur_kf?.value) cur_kf.value[2] = undefined;
									veToast(`Deleted properties at timestamp.`);
								}
							history_obj.getKeyframe({ refresh_localisation: true });
						}, { name: "Confirm" })
					}, { name: "Edit Properties", can_rename: false, width: "20rem" });
				}, { name: "Edit Properties" })
			}, { id: "ui_keyframe_context_menu" });
		});
	}
};