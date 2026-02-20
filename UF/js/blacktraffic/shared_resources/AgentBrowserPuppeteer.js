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
	 * Returns all tabs in the current browser.
	 * 
	 * @returns {Promise<Object[]>}
	 */
	async getTabs () {
		//Return statement
		if (this.browser)
			return await this.browser.pages();
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
		let tab_key = arg0_tab_key;
		
		//Declare local instance variables
		let tab_obj = this.getTab(tab_key);
		
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
	 * Injects a script within the current tab. 
	 * **Note.** Contexts are fully isolated when passing a function.
	 * 
	 * @param {string} arg0_tab_key
	 * @param {function} arg1_function
	 *  @param {Object} [arg2_options]
	 *  	@param {Object} [arg2_options.options] - Any options to pass down to the local function.
	 * 
	 * @returns {Promise<Object>}
	 */
	async injectScript (arg0_tab_key, arg1_function, arg2_options) {
		//Convert from parameters
		let tab_obj = this.getTab(arg0_tab_key);
		let local_function = arg1_function;
		let options = (arg2_options) ? arg2_options : {};
		
		//Inject script if possible
		if (tab_obj && local_function)
			await tab_obj.evaluate(local_function, (options.options) ? options.options : {});
		
		//Return statement
		return tab_obj;
	}
	
	/**
	 * Registers an onload script for future page visits using the mounted tab. 
	 * **Note.** Contexts are fully isolated when passing a function.
	 * 
	 * @param {string} arg0_tab_key
	 * @param {function} arg1_function
	 * @param {Object} [arg2_options]
	 *  @param {Object} [arg2_options.options] - Any options to pass down to the local function.
	 *  @param {string} [arg2_options.url]
	 * 
	 * @returns {Promise<Object>}
	 */
	async injectScriptOnload (arg0_tab_key, arg1_function, arg2_options) {
		//Convert from parameters
		let tab_obj = this.getTab(arg0_tab_key);
		let local_function = arg1_function;
		let options = (arg2_options) ? arg2_options : {};
		
		//Inject script at document start if possible
		if (tab_obj && local_function) {
			await tab_obj.evaluateOnNewDocument(local_function, (options.options) ? options.options : {});
			if (options.url) await tab_obj.goto(options.url, { waitUntil: "networkidle2" });
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
		for (let i = 0; i < this.options.connection_attempts_threshold; i++)
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
	 * Reloads the given tab.
	 * 
	 * @param {string} arg0_tab_key
	 * 
	 * @returns {Promise<Object>}
	 */
	async reloadTab (arg0_tab_key) {
		//Convert from parameters
		let tab_obj = this.getTab(arg0_tab_key);
		
		//Reload the current tab
		await tab.reload({ waitUntil: "networkidle2" });
		
		//Return statement
		return tab_obj;
	}
	
	/**
	 * Checks if a given tab exists.
	 * 
	 * @param {Object|string} arg0_tab_key
	 * @param {Object} [arg1_options]
	 *  @param {boolean} [arg1_options.strict=false] - Whether to also ensure the current tab is connected.
	 *  
	 * @returns {Promise<boolean>}
	 */
	async tabExists (arg0_tab_key, arg1_options) {
		//Convert from parameters
		let tab_obj = this.getTab(arg0_tab_key);
		let options = (arg1_options) ? arg1_options : {};
		
		//Declare local instance variables
		let is_connected = false;
		
		//options.strict handler
		if (tab_obj && options.strict)
			try {
				await tab_obj.title();
				is_connected = true;
			} catch (e) {}
		
		//Return statement
		if (!options.strict && tab_obj) return true;
		if (options.strict && is_connected) return true;
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
	
	/**
	 * Waits for content to stop changing within a selector.
	 *
	 * @param {Object|string} arg0_tab_key - The given tab key.
	 * @param {string} arg1_selector
	 * @param {number} [arg2_interval=3000]
	 */
	async waitForStableContent (arg0_tab_key, arg1_selector, arg2_interval) {
		//Convert from parameters
		let tab_obj = this.getTab(arg0_tab_key);
		let selector = arg1_selector;
		let interval = Math.returnSafeNumber(arg2_interval, 3000);
		
		//Wait for function inside of tab should it exist
		if (tab_obj) {
			let state_key = `_Blacktraffic_stable_${selector.replace(/[^a-z]/gi, "")}`;
			
			await tab_obj.waitForFunction((selector, state_key) => {
				let local_els = document.querySelectorAll(selector);
				if (local_els.length === 0) return false;
				
				let last_el = local_els[local_els.length - 1];
				
				//Check if HTML has changed
				if (!window[state_key]) {
					window[state_key] = last_el.innerHTML;
					return false;
				}
				
				let current_html = last_el.innerHTML;
				if (current_html === window[state_key]) {
					return true;
				} else {
					window[state_key] = current_html;
					return false;
				}
			}, { polling: interval, timeout: 0 }, selector, state_key);
		}
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