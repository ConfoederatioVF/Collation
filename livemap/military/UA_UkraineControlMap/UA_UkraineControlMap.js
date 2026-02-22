global.UA_UkraineControlMap = class {
	static bf = `${l2}UA_UkraineControlMap/`;
	
	constructor (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		this.static = UA_UkraineControlMap;
		this.initLeafletMap();
	}
	
	initLeafletMap () {
		this.geokmz = new Geospatiale.maptalks_GeoKMZ(`${this.static.bf}Ukraine Control Map v2.kmz`);
		this.geokmz.addTo(map);
	}
};