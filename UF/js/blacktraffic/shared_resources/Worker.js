if (!global.Blacktraffic) global.Blacktraffic = {};

/**
 * Represents a Blacktraffic.Worker type that can be repeatedly called to execute browser automation or other tasks. A tab is currently provided by default per task, regardless of whether it actually needs a browser context to execute.
 * 
 * ##### Constructor:
 * - `arg0_type`: {@link string} - The worker type to identify with.
 * - `arg1_options`: {@link Object}
 *   - `.config_file_path`: {@link string} - The config JSON5 file to load. Accessible at `.config`.
 *   - `.do_not_close_tab`: {@link boolean}
 *   - `.log_channel="${worker}_type"`: {@link string}
 *   - `.special_function`: {@link function}(arg0_tab_obj:{@link Object}, arg1_instance:this) | {@link Array}<{@link Ontology}>
 *   - `.tags=[]`: {@link Array}<{@link string}>
 *   - 
 *   - `.console_persistence=false`: {@link boolean} - Whether console outputs should persist between worker jobs.
 * 
 * @type {Blacktraffic.Worker}
 */
Blacktraffic.Worker = class {
	//[WIP] - Should be refactored in future to work with multiple browsers. Requires multiple copychecks and passes to ensure the contract is fulfilled. Need to add job interval to contract.
	//[WIP] - Should probably use a dual-channel logging system: a temporary log just for the worker, and a permanent log for all workers of the same type. This needs a wrapper to function, [REVISIT].
	
	/**
	 * @type {Blacktraffic.AgentBrowserPuppeteer}
	 */
	static browser_obj;
	
	/**
	 * @type {string}
	 */
	static input_chrome_profile = Blacktraffic.getChromeDefaultProfilePath();
	
	/**
	 * [WIP] - Should probably really be set to a default like ./settings/Blacktraffic/workers.
	 * @type {string}
	 */
	static saves_folder = `./livemap/1.workers/dashboard/`;
	
	/**
	 * @type {{ "<worker_type_key>": number }}
	 */
	static workers_id_obj = {};
	
	/**
	 * @type {{ "<worker_type_key>": Object[] }}
	 */
	static workers_obj = {};
	
	constructor (arg0_type, arg1_options) {
		//Convert from parameters
		let type = arg0_type;
		let options = (arg1_options) ? arg1_options : {};
		
		//Initialise options
		if (options.console_persistence === undefined) options.console_persistence = false;
		if (options.do_not_close_tab === undefined) options.do_not_close_tab = false;
		options.log_channel = (options.log_channel) ? options.log_channel : `worker_${type}`;
		options.tags = (options.tags) ? options.tags : [];
		
		//Declare local instance variables
		this.config = (options.config_file_path && fs.existsSync(options.config_file_path)) ? 
			JSON5.parse(fs.readFileSync(options.config_file_path)) : {};
		this.console = (!log[options.log_channel]) ?
			new log.Channel(options.log_channel) : log[`${options.log_channel}_instance`];
		this.is_enabled = true;
		this.options = options;
		this.static = Blacktraffic.Worker;
		this.type = type;
		
		this.current_job_status = "idle";
		this.jobs = []; //Internal job history
		
		//Append to workers_obj
		Object.modifyValue(this.static.workers_id_obj, type, 1); //Ensure unique ID
		
		if (!this.static.workers_obj[type]) this.static.workers_obj[type] = [];
			let worker_array = this.static.workers_obj[type];
			worker_array.push(this);
			this.worker_id = structuredClone(this.static.workers_id_obj[type]);
		this.name = `${type} ${this.worker_id}`;
	}
	
	async disable () {
		//Declare local instance variables
		let current_tab = await this.getTab();
		this.is_enabled = false;
		
		//Close any currently open tasks
		if (current_tab) await current_tab.close();
		if (this.console) this.console.log(`${this.name} disabled.`);
	}
	
	async enable () {
		this.is_enabled = true;
		if (this.console) this.console.log(`${this.name} enabled.`);
	}
	
	async getBrowser () {
		//Ensure a browser context is accessible
		if (!this.static.browser_obj?.browser) 
			this.static.browser_obj = await new Promise((resolve) => {
				let browser = new Blacktraffic.AgentBrowserPuppeteer(undefined, {
					onload: () => resolve(browser),
					user_data_folder: this.static.input_chrome_profile
				});
			}); 
		this._browser = this.static.browser_obj;
		
		//Return statement
		return this._browser;
	}
	
	getCurrentStatus () { return this.current_job_status; }
	
	getCurrentStatusElement () {
		//Declare local instance variables
		let last_job = this.jobs[this.jobs.length - 1];
		let status = this.getCurrentStatus();
		let status_el = document.createElement("span");
		
		//Set innerText and colour based off status
		if (status === "done") {
			status_el.innerText = "Done";
			status_el.style.color = "lime";
		} else if (status === "failed") {
			status_el.innerText = "Failed";
			status_el.style.color = "red";
		} else if (status === "idle") {
			status_el.innerText = "Idle";
			status_el.style.color = "lightgrey";
		} else if (status === "partially_failed") {
			status_el.innerText = "Partially Failed";
			status_el.style.color = "orange";
		} else if (status === "running") {
			let time_string = (last_job) ? new Date(last_job.timestamp).toLocaleTimeString() : ' ..'; //[WIP] - Add time elapsed later
			status_el.innerText = `Running (Time Elapsed) - Started [${time_string}]`;
			status_el.style.color = "cyan";
		}
		status_el.classList.add(`data-status-${status}`);
		
		//Return statement
		return status_el;
	}
	
	getCurrentTimeStatus () {
		//Declare local instance variables
		let current_status;
			if (this.jobs.length === 0) {
				current_status = "idle";
			} else {
				current_status = (this.current_job_status === "running") ? "running" : "done";
			}
		let last_job = this.jobs[this.jobs.length - 1];
		
		//Return statement
		return {
			status: current_status,
			timestamp: (last_job) ? last_job.timestamp : Date.now()
		};
	}
	
	getJobList () { return this.jobs; }
	
	getLastSuccessfulJob () {
		//Return statement
		for (let i = this.jobs.length - 1; i >= 0; i--)
			if (this.jobs[i].status === "done") return new Date(this.jobs[i].timestamp);
	}
	
	async getTab () {
		//Ensure a tab context is accessible
		if (!this._browser) await this.getBrowser();
		
		//Declare local instance variables
		let current_tab = this._browser.getTab(this.getTabID());
		
		//Return statement
		if (!current_tab) {
			return this._browser.openTab(this.getTabID());
		} else {
			//Return statement
			return current_tab;
		}
	}
	
	getTabID () { return `${this.type}_${this.worker_id}`; }
	
	remove () {
		//Declare local instance variables
		let worker_array = this.static.workers_obj[this.type];
		
		if (worker_array) {
			let index = worker_array.indexOf(this);
			if (index > -1) worker_array.splice(index, 1);
		}
	}
	
	async run () {
		if (!this.is_enabled) return []; //Internal guard clause if disabled
		
		//Declare local instance variables
		let log_folder = path.join(this.static.saves_folder, "logs", this.type);
			if (!fs.existsSync(log_folder)) fs.mkdirSync(log_folder, { recursive: true });
		let start_time = Date.now();
		
		let log_file_name = `${this.name}_${start_time}.log`;
		let log_path = path.join(log_folder, log_file_name);
		
		this.current_job_status = "running";
		let job_obj = {
			log_file_path: log_path,
			status: "running",
			time_elapsed: 0,
			timestamp: start_time
		};
		
		//Initialise job; begin logging to console
		if (this.console && !this.options.console_persistence) this.console.clear();
		this.jobs.push(job_obj);
		this.console.log(`[${this.name}] Executing run() at ${new Date(start_time).toISOString()}.`);
		
		try {
			let ontologies = [];
			let tab_obj = await this.getTab();
			
			//Execute worker logic
			if (typeof this.options.special_function === "function") {
				ontologies = await this.options.special_function(tab_obj, this);
			} else if (Array.isArray(this.options.special_function)) {
				ontologies = this.options.special_function;
			}
			
			//Job is only successful if it returns Ontology[]
			if (!Array.isArray(ontologies)) {
				this.console.warn(`[${this.name}] Worker failed to return Ontology[], returned:`, ontologies);
				job_obj.status = "partially_failed";
				this.current_job_status = "partially_failed";
			} else {
				job_obj.status = "done";
				this.current_job_status = "done";
			}
			
			if (!this.options.do_not_close_tab) await tab_obj.close();
			
			//Return statement
			return ontologies;
		} catch (e) {
			this.console.error(`[${this.name}] Worker failed to execute properly:`, (e.stack || e));
			job_obj.status = "failed";
			this.current_job_status = "failed";
		} finally {
			job_obj.time_elapsed = Date.now() - start_time;
			this.console.log(`[${this.name}] Worker finished in ${job_obj.time_elapsed}ms`);
			
			try {
				this.console.save(log_path, { format: "plaintext" }); //Save the console in plaintext form
			} catch (e) {
				this.console.error(`[${this.name}] Failed to write worker log to ${log_path}:`, (e.stack || e));
			}
		}
	}
};