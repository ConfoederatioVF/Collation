global.UA_UkraineControlMap = class {
	static bf = `${l2}UA_UkraineControlMap/`;
	
	constructor (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		this.static = UA_UkraineControlMap;
		
		this.leaflet_html = document.createElement("div");
			this.leaflet_html.classList.add("ve-drag-disabled");
			this.leaflet_html.style.minHeight = "800px";
			this.leaflet_html.style.minWidth = "1400px";
		this.leaflet_window = veWindow({
			map: veHTML(this.leaflet_html),
			window_opacity: veRange(1, {
				name: "Window Opacity",
				onchange: (v) => this.leaflet_window.element.style.opacity = v
			})
		}, {
			height: "800px",
			width: "800px"
		});
		this.initLeafletMap();
	}
	
	initLeafletMap () {
		this.map = L.map(this.leaflet_html);
		this.map.setView(new L.LatLng(43.5978, 12.7059), 5);
		
		let OpenTopoMap = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
			maxZoom: 17,
			attribution: 'Map data: &copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
			opacity: 0.90
		});
		OpenTopoMap.addTo(this.map);
		
		// Instantiate KMZ layer (async)
		window.kmz = L.kmzLayer().addTo(this.map);
		
		kmz.on('load', function(e) {
			control.addOverlay(e.layer, e.name);
			// e.layer.addTo(map);
		});
		
		// Add remote KMZ files as layers (NB if they are 3rd-party servers, they MUST have CORS enabled)
		kmz.load(`${this.static.bf}/Ukraine Control Map v2.kmz`);
		
		let control = L.control.layers(null, null, { collapsed:false }).addTo(this.map);
	}
};