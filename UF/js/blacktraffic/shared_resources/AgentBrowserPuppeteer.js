if (!global.Blacktraffic) global.Blacktraffic = {};

/**
 * Creates a new Puppeteer browser agent used for scraping tasks and purposes.
 * 
 * ##### Constructor:
 * - `arg0_key=Class.generateRandomID(Blacktraffic.AgentBrowserPuppeteer)`: {@link string} - The key to use for the given browser agent. Used for ID.
 * - `arg1_options`: {@link Object}
 *   - `.chrome_binary_path`: {@link string}
 *   - `.debug_console=false`: {@link boolean}
 *   - `.debugging_port=0`: {@link number}
 *   - `.headless=false`: {@link boolean}
 *   - `.onload`: {@link function}
 *   - `.user_data_folder`: {@link string} - Refers to a Chrome profile necessary for spoofing.
 *   - 
 *   - `.connection_attempts_threshold=3`: {@link number} - The number of connection attempts to use when opening the browser.
 *   - `.log_channel="console"`: {@link string}
 * 
 * @type {Blacktraffic.AgentBrowserPuppeteer}
 */
Blacktraffic.AgentBrowserPuppeteer = class {
	static instances = [];
	
	constructor (arg0_key, arg1_options) {
		//Convert from parameters
		let key = (arg0_key) ? arg0_key : Class.generateRandomID(Blacktraffic.AgentBrowserPuppeteer);
		let options = (arg1_options) ? arg1_options : {};
		
		//Initialise options
		if (options.debug_console === undefined) options.debug_console = false;
		if (options.headless === undefined) options.headless = false;
		
		options.connection_attempts_threshold = Math.returnSafeNumber(options.connection_attempts_threshold, 3);
		
		//Declare local instance variables
		this.updateLogChannel(options.log_channel);
		this.key = key;
		this.options = options;
		this.tab_obj = {};
		
		//Initialise and push to instances
		this.open().then(() => {
			if (this.options.onload)
				this.options.onload.call(this);
		});
		Blacktraffic.AgentBrowserPuppeteer.instances.push(this);
	}
	
	async captureConsoleToChannel (arg0_tab_key, arg1_channel_key) {
		//Convert from parameters
		let tab = this.getTab(arg0_tab_key);
		let channel_key = arg1_channel_key;
		
		//Declare local instance variables
		let log_obj = log.getLoggingFunctions(channel_key);
		
		//Set listener on tab page if possible
		tab.on("console", async (message) => {
			let args = await Promise.all(message.args().map((local_arg) => local_arg.jsonValue()));
			let type = message.type();
			
			log_obj.log_fn(`${tab.url()} [${type.toUpperCase()}]:`, ...args);
		});
	}
	
	/**
	 * Closes the browser currently mounted to the AgentBrowser.
	 * 
	 * @returns {Promise<Blacktraffic.AgentBrowserPuppeteer>}
	 */
	async close () {
		//Close browser first
		if (this.browser) await this.browser.close();
		this.browser = undefined;
		
		//Return statement
		return this;
	}
	
	/**
	 * Closes the tab specified.
	 * 
	 * @param {Object|string} arg0_tab_key
	 * 
	 * @returns {Promise<Blacktraffic.AgentBrowserPuppeteer>}
	 */
	async closeTab (arg0_tab_key) {
		//Convert from parameters
		let tab_obj = this.getTab(arg0_tab_key);
		
		//Attempt to close the tab if found
		if (tab_obj) {
			await tab_obj.close();
			if (this.browser && !this.browser.isConnected())
				this.browser = undefined;
		}
		
		//Return statement
		return this;
	}
	
	/**
	 * Closes all user tabs from the current browser.
	 * 
	 * @returns {Promise<Blacktraffic.AgentBrowserPuppeteer>}
	 */
	async closeUserTabs () {
		//Declare local instance variables
		let all_tab_keys = Object.keys(this.tab_obj);
		
		//Iterate over all_tab_keys and determine which tabs do not have a _blacktraffic_key, then close them
		for (let i = 0; i < all_tab_keys.length; i++) {
			let local_tab = this.tab_obj[all_tab_keys[i]];
			
			if (!local_tab._blacktraffic_key)
				await this.closeTab(local_tab);
		}
		
		//Return statement
		return this;
	}
	
	/**
	 * Returns a tab object based on its key.
	 * 
	 * @param {Object|string} arg0_tab_key
	 * 
	 * @returns {Object}
	 */
	getTab (arg0_tab_key) {
		//Convert from parameters
		let tab_key = arg0_tab_key;
		
		if (typeof tab_key === "object") return tab_key; //Internal guard clause if tab_key is already a tab object
		
		//Return statement
		return this.tab_obj[tab_key];
	}
	
	/**
	 * Focuses the specified tab.
	 * 
	 * @param {Object|string} arg0_tab_key
	 * 
	 * @returns {Promise<Object|undefined>}
	 */
	async focusTab (arg0_tab_key) {
		//Convert from parameters
		let tab_obj = this.getTab(arg0_tab_key);
		
		//Focus the current tab
		if (tab_obj) {
			await tab_obj.bringToFront();
		} else {
			this.warn_fn(`Blacktraffic.AgentBrowserPuppeteer: Could not focus ${tab_key}, as it doesn't exist.`)
		}
		
		//Return statement
		return tab_obj;
	}
	
	/**
	 * Initialises a Chrome instance and connects Puppeteer.
	 * 
	 * @returns {Promise<Blacktraffic.AgentBrowserPuppeteer>}
	 */
	async open () {
		//Declare local instance variables
		let attempts = 0;
		
		//Iterate over all attempts until threshold or the for loop exits
		for (let i = 0; i < this.options.connection_attempts_threshold.length; i++)
			try {
				let target_port = await Blacktraffic.getFreePort();
				
				//1. Run launch command
				this.launch_cmd = `"${Blacktraffic.getChromeBinaryPath()}" --remote-debugging-port=${Math.returnSafeNumber(this.options.debugging_port, target_port)}${(this.options.user_data_folder) ? ` --user-data-dir="${this.options.user_data_folder}"` : ""}`;
				exec(this.launch_cmd);
				
				//2. Connect to browser instance
				await Blacktraffic.sleep(1500);
				this.browser = await puppeteer.connect({
					browserURL: `http://localhost:${target_port}`,
					defaultViewport: null
				});
				this.log_fn(`Blacktraffic.AgentBrowserPuppeteer: ${this.key} connected to port ${target_port}.`);
				break;
			} catch (e) {
				attempts++;
				this.warn_fn(`Port collision or launch failure, retrying .. ${attempts}/${this.options.connection_attempts_threshold}`);
				await Blacktraffic.sleep(500);
			}
		
		if (!this.browser) this.error_fn(`Blacktraffic.AgentBrowserPuppeteer: ${this.key} failed to connect to a browser.`);
		
		//Return statement
		return this;
	}
	
	/**
	 * Opens a tab at the corresponding URL. Corresponding URLs are optional.
	 * 
	 * @param {string} [arg0_tab_key=Object.generateRandomID(this.tab_obj)]
	 * @param {string} arg1_url
	 * 
	 * @returns {Promise<Object>}
	 */
	async openTab (arg0_tab_key, arg1_url) {
		//Convert from parameters
		let tab_key = (arg0_tab_key) ? arg0_tab_key : Object.generateRandomID(this.tab_obj);
		let url = arg1_url;
		
		//Open tab first
		if (!this.browser) await this.open();
		this.tab_obj[tab_key] = await this.browser.newPage();
			this.tab_obj[tab_key][`_blacktraffic_key`] = tab_key;
		let tab_obj = this.tab_obj[tab_key];
		
		if (url) await tab_obj.goto(url, { waitUntil: "networkidle2" });
		
		//Return statement
		return this.tab_obj[tab_key];
	}
	
	/**
	 * Updates the default logging channel for the current agent.
	 * 
	 * @param {string} arg0_channel_key
	 */
	updateLogChannel (arg0_channel_key) {
		//Convert from parameters
		let channel_key = arg0_channel_key;
		
		this.log_obj = log.getLoggingFunctions(channel_key);
			this.error_fn = this.log_obj.error_fn;
			this.log_fn = this.log_obj.log_fn;
			this.warn_fn = this.log_obj.warn_fn;
	}
};

/**
 * Attempts to return the Chrome binary path.
 * 
 * @returns {string}
 */
Blacktraffic.getChromeBinaryPath = function () {
	//Declare local instance variables
	let os_platform = Blacktraffic.getOS();
	
	//Handle Windows
	if (os_platform === "win") {
		let suffix = "/Google/Chrome/Application/chrome.exe";
		let prefixes = [process.env.LOCALAPPDATA, process.env.ProgramFiles, process.env["PROGRAMFILES(X86)"]];
		
		for (let local_prefix of prefixes)
			if (local_prefix) {
				let chrome_path = path.join(local_prefix, suffix);
				if (fs.existsSync(chrome_path)) return chrome_path;
			}
	} else if (os_platform === "lin") {
		let chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
		if (fs.existsSync(chrome_path)) return chrome_path;
	} else {
		let binaries = ["google-chrome", "google-chrome-stable", "chromium"];
		
		for (let local_binary of binaries)
			try {
				let chrome_path = child_process.execSync(`which ${local_binary}`, { stdio: "pipe" })
					.toString().trim();
				if (chrome_path && fs.existsSync(chrome_path)) return chrome_path;
			} catch (e) {} //Which returns non-zero exit code if not found
	}
};