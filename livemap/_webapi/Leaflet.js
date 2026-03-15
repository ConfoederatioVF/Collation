Blacktraffic.AgentBrowser.webapi.Leaflet = {
	captureMaps: function () {
		// This array will hold all map instances found on the page
		window.captured_maps = [];
		
		let leafletBackend;
		
		// We define a getter/setter on window.L to catch the moment Leaflet loads
		Object.defineProperty(window, "L", {
			get: function () {
				return leafletBackend;
			},
			set: function (newLeaflet) {
				leafletBackend = newLeaflet;
				
				// Ensure we have the Map object and haven't hooked it yet
				if (leafletBackend && leafletBackend.Map && !leafletBackend._hooked) {
					leafletBackend._hooked = true;
					
					console.log("Leaflet detected! Injecting initialization hook...");
					
					leafletBackend.Map.addInitHook(function () {
						window.captured_maps.push(this);
						console.log("New Leaflet map instance captured:", this);
					});
				}
			},
			configurable: true,
		});
		
		// Optional: Expose a helper function to the console to interact with maps
		window.getMaps = () => window.captured_maps;
	},
	
	getGeometryType: function (geometry) {
		if (geometry instanceof L.Polygon) {
			return "polygon";
		} else if (geometry instanceof L.Polyline) {
			return "line";
		} else if (geometry instanceof L.Marker || geometry instanceof L.CircleMarker) {
			return "point";
		}
	}
};