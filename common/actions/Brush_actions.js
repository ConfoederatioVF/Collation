config.actions.brush = {
	select_feature_id: {
		name: "Select Feature ID",
		scope: ["Brush", "Feature"],
		special_function: async function (json) {
			if (json.select_feature_id !== undefined && json.select_feature_id !== false && json.select_feature_id !== null) {
				let id = String(json.select_feature_id);
				main.brush.selected_feature = naissance.Feature.instances[id];
				if (main.brush.selected_feature?.draw) main.brush.selected_feature.draw();
			} else if (json.select_feature_id === false || json.select_feature_id === null) {
				main.brush.selected_feature = undefined;
			}
		}
	},
	select_geometry_id: {
		name: "Select Geometry ID",
		scope: ["Brush", "Geometry"],
		special_function: async function (json) {

			//Select new geometry
			if (json.select_geometry_id !== undefined && json.select_geometry_id !== false && json.select_geometry_id !== null) {
				let id = String(json.select_geometry_id);
				let target_geom = naissance.Geometry.instances[id];
				if (target_geom && typeof target_geom.loadHistory === "function")
					await target_geom.loadHistory();
				main.brush.selected_geometry = target_geom;
			} else if (json.select_geometry_id === false || json.select_geometry_id === null) {
				main.brush.selected_geometry = undefined;
			}
			
			//Handle brush mode
			main.brush.node_editor.update();
		}
	}
};