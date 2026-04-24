global.UI_Mapmodes = class extends ve.Class {
	constructor () {
		super();
		
		//Declare local instance variables
		this.interface = new ve.Interface({
			mapmode_selection: new ve.SearchSelect({}, {
				header_components_obj: {
					add_new_mapmode: veButton(() => {
						this.openAddMapmodesWindow();
					}, {
						name: "<icon>add_circle</icon>",
						tooltip: "Add New Mapmode",
						style: { marginLeft: "var(--cell-padding)" }
					}),
					mapmode_settings: veButton(() => {
						if (main.interfaces.mapmodes_ui_settings) main.interfaces.mapmodes_ui_settings.close("instance");
						main.interfaces.mapmodes_ui_settings = new UI_Mapmodes_Settings();
					}, {
						name: "<icon>settings</icon>",
						tooltip: "Mapmode Settings",
						style: { marginLeft: "var(--cell-padding)" }
					})
				},
				filter_names: {
					"data-default": "Default"
				},
				searchbar_style: {
					marginBottom: "calc(var(--padding))"
				},
			})
		}, {
			is_folder: false,
			style: {
				'[component="ve-button"]': {
					position: "relative"
				},
				'[component="ve-button"] .priority-element': {
					alignItems: "center",
					backgroundColor: "var(--bg-secondary-colour)",
					border: "1px solid var(--hover-colour)",
					borderRadius: "50%",
					display: "flex",
					height: "var(--body-font-size)",
					justifyContent: "center",
					padding: "calc(var(--cell-padding)*0.5)",
					position: "absolute",
					top: 0,
					right: 0,
					transform: `translate(
						calc(100% - var(--padding) - 2px - var(--cell-padding)), 
						calc(-100% + var(--cell-padding))
					)`,
					width: "var(--body-font-size)",
					zIndex: 1
				},
				'[data-selected-mapmode="true"] button': {
					backgroundColor: `var(--accent-secondary-colour)`
				},
				padding: 0
			}
		});
		setTimeout(() => {
			naissance.Mapmode.loadConfig();
			this.draw();
		}, 100);
		
		//Open window
		super.open("instance", {
			anchor: "bottom_right",
			mode: "static_window",
			name: "Mapmodes",
			width: "26rem",
			x: 8,
			y: () => main.brush.instance_window.element.offsetHeight + 16
		});
	}
	
	/**
	 * Draws all mapmode icons from {@link naissance.Mapmode|naissance.Mapmode.instances}.
	 */
	draw () {
		//Declare local instance variables
		let components_obj = {};
		let map_settings = main.map.settings;
		
		//Iterate over all naissance.Mapmode.instances
		for (let i = 0; i < naissance.Mapmode.instances.length; i++) {
			let local_mapmode = naissance.Mapmode.instances[i];
			if (!(map_settings.enabled_mapmodes && map_settings.enabled_mapmodes.includes(local_mapmode.id)))
				continue; //Internal guard clause if map settings does not have this mapmode enabled
				
			components_obj[local_mapmode.id] = local_mapmode.drawHierarchyDatatype();
			
			let local_component_obj = components_obj[local_mapmode.id];
			
			//Set local_component_obj top right numeric element if enabled
			if (local_mapmode.is_enabled) {
				let local_priority_el = document.createElement("div");
					local_priority_el.classList.add("priority-element");
					local_priority_el.innerHTML = (main.user.mapmodes.indexOf(local_mapmode.id) + 1).toString();
				local_component_obj.element.appendChild(local_priority_el);
			}
		}
		
		//Set new mapmode_selection value
		this.interface.mapmode_selection.v = components_obj;
	}
	
	openAddMapmodesWindow () {
		if (this.add_mapmodes_window) this.add_mapmodes_window.close(); //Close add_mapmodes_window if already open
		
		//Declare local instance variables
		let components_obj = {};
		let map_settings = main.map.settings;
		
		if (!map_settings.enabled_mapmodes) map_settings.enabled_mapmodes = [];
		
		//Iterate over all naissance.Mapmode.instances and determine which are already in the local savefile
		for (let i = 0; i < naissance.Mapmode.instances.length; i++) {
			let local_mapmode = naissance.Mapmode.instances[i];
			
			let local_mapmode_button = veButton((v, e) => {
				let mapmode_index = map_settings.enabled_mapmodes.indexOf(local_mapmode.id);
				
				//Toggle map_settings.enabled_mapmodes
				(mapmode_index !== -1) ?
					map_settings.enabled_mapmodes.splice(mapmode_index, 1) :
					map_settings.enabled_mapmodes.push(local_mapmode.id);
				
				//Update attribute; save map settings
				e.element.setAttribute("data-is-enabled", map_settings.enabled_mapmodes.includes(local_mapmode.id));
				this.draw();
			}, {
				name: `${(local_mapmode.options.icon) ? `<icon>${local_mapmode.options.icon}</icon>&nbsp;&nbsp;` : ""}${local_mapmode.options.name}`,
				attributes: {
					"data-is-enabled": map_settings.enabled_mapmodes.includes(local_mapmode.id)
				}
			});
			
			components_obj[local_mapmode.id] = local_mapmode_button;
		}
		
		this.add_mapmodes_window = veWindow({
			mapmodes_search: veSearchSelect(components_obj, {
				display: "inline",
				placeholder: "Search for mapmode ...",
				searchbar_style: {
					width: `calc(100% - var(--padding))`
				},
				style: {
					"> [component='ve-button']": {
						display: "inline",
						padding: 0
					},
					"[data-is-enabled='true'] button": {
						backgroundColor: `var(--accent-primary-colour)`
					}
				},
			})
		}, {
			name: "Add Mapmodes",
			can_rename: false,
			width: "30rem",
			x: "50dvw - 30rem/2",
			y: "50dvh"
		});
	}
};