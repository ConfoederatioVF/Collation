if (!global.Blacktraffic) global.Blacktraffic = {};
Blacktraffic.AgentBrowserPuppeteer = class {
	static instances = [];
	
	constructor (arg0_key, arg1_options) {
		//Convert from parameters
		let key = (arg0_key) ? arg0_key : Class.generateRandomID(Blacktraffic.AgentBrowserPuppeteer);
		let options = (arg1_options) ? arg1_options : {};
		
		//Declare local instance variables
	}
};