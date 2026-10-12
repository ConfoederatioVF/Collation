config.actions.geometry_media = {
	create_media: {
		name: "Create Media",
		scope: ["GeometryMedia"],
		
		special_function: async function (json)  {
			if (json.create_media.id) {
				let new_media = new naissance.GeometryMedia();
				new_media.setID(json.create_media.id);
				
				//Refresh leftbar on creation
				UI_Leftbar.refresh();
			}
		}
	},
	update_keyframe: {
		name: "Update Keyframe",
		scope: ["GeometryMedia"],
		
		special_function: async function (json) {
			let media_obj = json.naissance_obj || (json.geometry_obj ? naissance.Geometry.instances[json.geometry_obj] : null);
			if (!media_obj) return;
			
			if (json.update_keyframe) {
				//Declare local instance variables
				let update_keyframe_date = (json.update_keyframe.date !== undefined) ? 
					json.update_keyframe.date : main.date;
				let marker_coord = (media_obj.geometry?.getCoordinates) ?
					media_obj.geometry.getCoordinates() :
					(map?.getCenter ? map.getCenter() : { x: 0, y: 0 });
				let symbol_obj = (json.update_keyframe.symbol_obj !== undefined) ?
					json.update_keyframe.symbol_obj :
					(media_obj.value?.[1] || {});
				
				let geometry_obj = {
					center: [marker_coord.x, marker_coord.y],
					mesh_points: JSON.parse(JSON.stringify(media_obj.mesh_points)),
					initial_zoom: media_obj.initial_zoom
				};
				
				//Add keyframes; draw call
				media_obj.history.addKeyframe(update_keyframe_date, geometry_obj, symbol_obj);
				if (global.db?.setKeyframes && media_obj.id) {
					try {
						await db.setKeyframes(media_obj.id, media_obj.history.keyframes);
					} catch (e) {}
				}
				media_obj.draw();
			}
		}
	}
};
config.actions.geometry_media.update_media_keyframe = config.actions.geometry_media.update_keyframe;