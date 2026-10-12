global.UI_AdvancedToolsWindow = class {
	static instance;
	
	constructor () {
		if (UI_AdvancedToolsWindow.instance) UI_AdvancedToolsWindow.instance.close();
		UI_AdvancedToolsWindow.instance = vePageMenuWindow({
			datavis_suite: {
				name: "Datavis Suite",
				components_obj: {
					datavis_suite: veDatavisSuite()
				}
			},
			system_manager: {
				name: "System Manager",
				components_obj: {
					system_manager: veSystemManager()
				}
			},
			script_manager: {
				name: "Script Manager (IDE)",
				components_obj: {
					script_manager: veScriptManager()
				}
			}
		}, {
			can_rename: false,
			name: "Advanced Tools",
			height: "80dvh",
			width: "80dvw",
			onuserchange: (v, e) => {
				if (v.close) window.discordRPC.updateActivity({ state: "Working" });
			},
			
			page_menu_options: {
				retain: true,
				starting_page: "script_manager",
				style: {
					display: "flex",
					height: "100%",
					flexDirection: "column",
					
					"#component-body": { 
						flexGrow: 1,
						"[component='ve-interface']": { padding: 0 },
						"td[id='0-0']": { padding: 0 }
					}
				}
			}
		});
		window.discordRPC.updateActivity("advanced_tools_activity");
	}
};