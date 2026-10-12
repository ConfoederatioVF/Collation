/**
 * System Manager component for real-time DB and Process worker diagnostics and concurrency control.
 * Restyled to adhere natively to Vercengen's core design system and composable component architecture.
 *
 * @type {UI_SystemManager}
 */
global.UI_SystemManager = class extends ve.Component {
  constructor (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};
    super(options);

    //Declare local instance variables
    let os_module = (typeof os !== "undefined") ? os : ((typeof require === "function") ? require("node:os") : null);
    let cpu_cores = os_module?.cpus ? os_module.cpus().length : 4;

    this.auto_refresh = true;
    this.db_diagnostics = [];
    this.db_target_threads = (global.ve?.ndjson_worker_pool?.length) ?
      global.ve.ndjson_worker_pool.length : Math.max(1, cpu_cores - 1);
    this.is_updating_db = false;
    this.is_updating_proc = false;
    this.options = options;
    this.proc_diagnostics = [];
    this.proc_target_threads = (global.proc?.worker_pool?.length) ?
      global.proc.worker_pool.length : Math.max(1, Math.min(4, Math.ceil((cpu_cores - 1) / 4)));

    //Build container element
    this.element = document.createElement("div");
    this.element.setAttribute("component", "ui-system-manager");
    this.element.style.cssText = `
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      gap: calc(var(--padding, 0.5rem)*1.5);
      height: 100%;
      overflow-y: auto;
      padding: calc(var(--padding, 0.5rem)*1.5);
      width: 100%;
      background: transparent;
      color: var(--body-colour, #ffffff);
      font-family: var(--body-font-family, "Karla", sans-serif);
      font-size: var(--body-font-size, 0.85rem);
    `;

    //Initial draw & live polling
    this.render();
    this.refreshDiagnostics();

    this.poll_interval = setInterval(() => {
      if (this.auto_refresh && document.body.contains(this.element)) {
        this.refreshDiagnostics();
      }
    }, 1500);
  }


  /**
   * Applies the user-requested DB concurrency worker pool size.
   */
  async applyDbConcurrency () {
    let count = parseInt(this.db_threads_input.v);
    if (count > 0 && !this.is_updating_db) {
      this.is_updating_db = true;
      this.db_apply_btn.disabled = true;
      this.db_apply_btn.name = "Updating...";
      try {
        if (global.db?.setWorkerPoolSize) {
          await db.setWorkerPoolSize(count);
        }
        await this.refreshDiagnostics();
      } finally {
        this.is_updating_db = false;
        this.db_apply_btn.disabled = false;
        this.db_apply_btn.name = "Apply Concurrency";
      }
    }
  }


  /**
   * Applies the user-requested Process concurrency worker pool size.
   */
  async applyProcConcurrency () {
    let count = parseInt(this.proc_threads_input.v);
    if (count > 0 && !this.is_updating_proc) {
      this.is_updating_proc = true;
      this.proc_apply_btn.disabled = true;
      this.proc_apply_btn.name = "Updating...";
      try {
        if (global.proc?.setWorkerPoolSize) {
          await proc.setWorkerPoolSize(count);
        }
        await this.refreshDiagnostics();
      } finally {
        this.is_updating_proc = false;
        this.proc_apply_btn.disabled = false;
        this.proc_apply_btn.name = "Apply Concurrency";
      }
    }
  }


  /**
   * Cleans up running intervals and sub-components when the component is removed.
   */
  destroy () {
    if (this.poll_interval) {
      clearInterval(this.poll_interval);
      this.poll_interval = null;
    }
    if (this.header_controls?.destroy) this.header_controls.destroy();
    if (this.db_controls?.destroy) this.db_controls.destroy();
    if (this.proc_controls?.destroy) this.proc_controls.destroy();
  }


  /**
   * Formats a byte number into a legible string with European decimals.
   *
   * @param {number} arg0_bytes
   * @returns {string}
   */
  formatBytes (arg0_bytes) {
    let bytes = Number(arg0_bytes) || 0;
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1).replace(".", ",")} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1).replace(".", ",")} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2).replace(".", ",")} GB`;
  }


  /**
   * Formats an integer with standard thousands separator.
   *
   * @param {number} arg0_num
   * @returns {string}
   */
  formatNumber (arg0_num) {
    let num = Number(arg0_num) || 0;
    return num.toLocaleString("en-GB");
  }


  /**
   * Fetches latest metrics from DB and Process worker pools and updates UI.
   */
  async refreshDiagnostics () {
    if (this.is_updating_db || this.is_updating_proc) return;
    try {
      if (global.db?.getDiagnostics) {
        let db_res = await db.getDiagnostics();
        if (Array.isArray(db_res)) this.db_diagnostics = db_res;
      }
      if (global.proc?.getDiagnostics) {
        let proc_res = await proc.getDiagnostics();
        if (Array.isArray(proc_res)) this.proc_diagnostics = proc_res;
      }
      this.updateView();
    } catch (e) {
      console.error("[UI_SystemManager] Error refreshing diagnostics:", e);
    }
  }


  /**
   * Builds the DOM layout using Vercengen components conforming strictly to UI conventions.
   */
  render () {
    let os_module = (typeof os !== "undefined") ? os : ((typeof require === "function") ? require("node:os") : null);
    let cpu_count = os_module?.cpus ? os_module.cpus().length : 4;
    let total_ram = os_module?.totalmem ? this.formatBytes(os_module.totalmem()) : "N/A";
    let free_ram = os_module?.freemem ? this.formatBytes(os_module.freemem()) : "N/A";

    this.element.innerHTML = "";

    //Style block for System Manager panels and cards
    let style_el = document.createElement("style");
    style_el.textContent = `
      [component="ui-system-manager"] .sm-panel {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: calc(var(--padding, 0.5rem)*0.5);
        padding: calc(var(--padding, 0.5rem)*1.25);
      }
      [component="ui-system-manager"] .sm-btn button {
        background-color: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: calc(var(--padding, 0.5rem)*0.5);
        color: var(--body-colour, #ffffff);
        font-family: var(--body-font-family, "Karla", sans-serif);
        font-size: var(--body-font-size, 0.85rem);
        font-weight: 400;
        padding: calc(var(--padding, 0.5rem)*0.4) calc(var(--padding, 0.5rem)*1.4);
        cursor: pointer;
        transition: all 0.25s ease;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
      }
      [component="ui-system-manager"] .sm-btn button:hover {
        background-color: var(--accent-primary-colour, rgba(200, 40, 40));
        border-color: var(--accent-secondary-colour, rgba(240, 60, 60));
        cursor: pointer;
      }
      [component="ui-system-manager"] .sm-btn button:active {
        opacity: 0.85;
      }
      [component="ui-system-manager"] .sm-btn button:disabled,
      [component="ui-system-manager"] .sm-btn button[disabled="true"] {
        opacity: 0.4;
        cursor: not-allowed;
        background-color: rgba(255, 255, 255, 0.03) !important;
        border-color: rgba(255, 255, 255, 0.08) !important;
      }
      [component="ui-system-manager"] .sm-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.12rem 0.5rem;
        border-radius: 2px;
        font-size: 0.7rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }
      [component="ui-system-manager"] .sm-badge-online {
        background: rgba(34, 197, 94, 0.08);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
      }
      [component="ui-system-manager"] .sm-badge-proc {
        background: rgba(56, 189, 248, 0.08);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
      }
      [component="ui-system-manager"] .sm-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
        gap: 0.6rem;
      }
      [component="ui-system-manager"] .sm-tile {
        background: rgba(255, 255, 255, 0.02);
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: calc(var(--padding, 0.5rem)*0.5);
        padding: 0.65rem 0.85rem;
        transition: border-color 0.2s ease, background 0.2s ease;
      }
      [component="ui-system-manager"] .sm-tile:hover {
        background: rgba(255, 255, 255, 0.04);
        border-color: rgba(255, 255, 255, 0.16);
      }
      [component="ui-system-manager"] .sm-progress-track {
        width: 100%;
        height: 3px;
        background: rgba(255, 255, 255, 0.06);
        border-radius: 1.5px;
        overflow: hidden;
        margin-top: 0.45rem;
      }
      [component="ui-system-manager"] .sm-progress-fill {
        height: 100%;
        border-radius: 1.5px;
        transition: width 0.3s ease, background 0.3s ease;
      }
      [component="ui-system-manager"] .sm-header-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        flex-wrap: wrap;
        gap: 0.75rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding-bottom: 0.75rem;
      }
      [component="ui-system-manager"] .sm-section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.75rem;
        margin-bottom: 0.75rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding-bottom: 0.5rem;
      }
      [component="ui-system-manager"] [component="ve-number"] #name {
        color: rgba(255, 255, 255, 0.6);
        font-size: 0.8rem;
        font-weight: 300;
      }
      [component="ui-system-manager"] [component="ve-checkbox"] label {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.7);
        font-weight: 300;
        cursor: pointer;
      }
      [component="ui-system-manager"] [component="ve-checkbox"] input[type="checkbox"] {
        cursor: pointer;
        accent-color: var(--accent-primary-colour, #c82828);
      }
    `;
    this.element.appendChild(style_el);

    //1. Header Section with Vercengen components
    this.auto_refresh_checkbox = new ve.Checkbox(this.auto_refresh, {
      attributes: {
        style: "display: inline-flex; align-items: center; cursor: pointer;"
      },
      name: "Auto-refresh (1,5s)",
      onchange: (val) => {
        this.auto_refresh = Boolean(val);
      }
    });

    this.refresh_btn = new ve.Button(() => {
      this.refreshDiagnostics();
    }, {
      attributes: {
        class: "sm-btn",
        style: "display: inline-flex; align-items: center;"
      },
      name: "Refresh"
    });

    this.header_controls = new ve.RawInterface({
      auto_refresh: this.auto_refresh_checkbox,
      refresh: this.refresh_btn
    }, {
      attributes: {
        style: "display: inline-flex; align-items: center; gap: 0.75rem;"
      },
      no_name_element: true
    });

    let header_div = document.createElement("div");
    header_div.className = "sm-header-row";
    header_div.innerHTML = `
      <div>
        <h2 style="margin: 0; font-family: var(--header-font-family, 'Karla', sans-serif); font-size: 1.2rem; font-weight: 500; color: var(--header-colour, #ffffff); letter-spacing: 0.01em;">
          Current Resources
        </h2>
      </div>
    `;
    header_div.appendChild(this.header_controls.element);
    this.element.appendChild(header_div);

    //2. Overview Metrics Bar
    let overview_panel = document.createElement("div");
    overview_panel.className = "sm-panel";
    overview_panel.style.cssText = "display: flex; flex-wrap: wrap; gap: 1.5rem; justify-content: space-around; align-items: center;";
    overview_panel.innerHTML = `
      <div style="text-align: center; min-width: 140px;">
        <div style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: rgba(255, 255, 255, 0.5); font-weight: 400;">CPU Logical Cores</div>
        <div style="font-family: var(--body-font-family, 'Karla', sans-serif); font-size: 1.3rem; font-weight: 400; color: var(--header-colour, #ffffff); margin-top: 0.25rem;">
          ${cpu_count} Threads
        </div>
      </div>
      <div style="width: 1px; height: 32px; background: rgba(255, 255, 255, 0.08);"></div>
      <div style="text-align: center; min-width: 140px;">
        <div style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: rgba(255, 255, 255, 0.5); font-weight: 400;">System RAM Available</div>
        <div style="font-family: var(--body-font-family, 'Karla', sans-serif); font-size: 1.3rem; font-weight: 400; color: var(--header-colour, #ffffff); margin-top: 0.25rem;">
          ${free_ram} <span style="font-size: 0.8rem; color: rgba(255, 255, 255, 0.5); font-weight: 300;">/ ${total_ram}</span>
        </div>
      </div>
      <div style="width: 1px; height: 32px; background: rgba(255, 255, 255, 0.08);"></div>
      <div style="text-align: center; min-width: 140px;">
        <div style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: rgba(255, 255, 255, 0.5); font-weight: 400;">Total Cached Geometries</div>
        <div id="sm-summary-entities" style="font-family: var(--body-font-family, 'Karla', sans-serif); font-size: 1.3rem; font-weight: 400; color: var(--header-colour, #ffffff); margin-top: 0.25rem;">
          0
        </div>
      </div>
      <div style="width: 1px; height: 32px; background: rgba(255, 255, 255, 0.08);"></div>
      <div style="text-align: center; min-width: 140px;">
        <div style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: rgba(255, 255, 255, 0.5); font-weight: 400;">Worker Memory Footprint</div>
        <div id="sm-summary-ram" style="font-family: var(--body-font-family, 'Karla', sans-serif); font-size: 1.3rem; font-weight: 400; color: var(--header-colour, #ffffff); margin-top: 0.25rem;">
          0 MB
        </div>
      </div>
    `;
    this.element.appendChild(overview_panel);

    //3. Database (DB) Workers Section
    let db_panel = document.createElement("div");
    db_panel.className = "sm-panel";

    this.db_threads_input = new ve.Number(this.db_target_threads, {
      attributes: {
        class: "sm-input",
        style: "background: transparent; border: none; border-bottom: 1px solid rgba(255, 255, 255, 0.25); color: var(--body-colour, #ffffff); font-family: var(--body-font-family, 'Karla', sans-serif); font-size: var(--body-font-size, 0.85rem); font-weight: 400; padding: 0.15rem 0.3rem; outline: none; width: 44px; text-align: center;"
      },
      element_attributes: {
        style: "display: inline-flex; align-items: center; gap: 0.5rem;"
      },
      max: 32,
      min: 1,
      name: "Concurrent Threads:",
      onchange: (val) => {
        let parsed = parseInt(val);
        if (parsed > 0) this.db_target_threads = parsed;
      }
    });

    this.db_apply_btn = new ve.Button(async () => {
      await this.applyDbConcurrency();
    }, {
      attributes: {
        class: "sm-btn",
        style: "display: inline-flex; align-items: center;"
      },
      name: "Apply Concurrency"
    });

    this.db_controls = new ve.RawInterface({
      threads: this.db_threads_input,
      apply: this.db_apply_btn
    }, {
      attributes: {
        style: "display: inline-flex; align-items: center; gap: 0.5rem;"
      },
      no_name_element: true
    });

    let db_header = document.createElement("div");
    db_header.className = "sm-section-header";
    db_header.innerHTML = `
      <div style="display: flex; align-items: center; gap: 0.6rem;">
        <span style="font-family: var(--body-font-family, 'Karla', sans-serif); font-size: 0.95rem; font-weight: 500; color: var(--header-colour, #ffffff);">
          Database (DB) Worker Pool
        </span>
        <span class="sm-badge sm-badge-online"><span id="sm-db-count">0</span> Active</span>
      </div>
    `;
    db_header.appendChild(this.db_controls.element);
    db_panel.appendChild(db_header);

    this.db_grid = document.createElement("div");
    this.db_grid.className = "sm-grid";
    this.db_grid.innerHTML = `<div style="color: rgba(255, 255, 255, 0.5); font-size: 0.85rem; padding: 0.5rem 0; font-weight: 300;">No active DB worker pool detected or savefile not yet loaded.</div>`;
    db_panel.appendChild(this.db_grid);
    this.element.appendChild(db_panel);

    //4. Process (Compute) Workers Section
    let proc_panel = document.createElement("div");
    proc_panel.className = "sm-panel";

    this.proc_threads_input = new ve.Number(this.proc_target_threads, {
      attributes: {
        class: "sm-input",
        style: "background: transparent; border: none; border-bottom: 1px solid rgba(255, 255, 255, 0.25); color: var(--body-colour, #ffffff); font-family: var(--body-font-family, 'Karla', sans-serif); font-size: var(--body-font-size, 0.85rem); font-weight: 400; padding: 0.15rem 0.3rem; outline: none; width: 44px; text-align: center;"
      },
      element_attributes: {
        style: "display: inline-flex; align-items: center; gap: 0.5rem;"
      },
      max: 32,
      min: 1,
      name: "Concurrent Threads:",
      onchange: (val) => {
        let parsed = parseInt(val);
        if (parsed > 0) this.proc_target_threads = parsed;
      }
    });

    this.proc_apply_btn = new ve.Button(async () => {
      await this.applyProcConcurrency();
    }, {
      attributes: {
        class: "sm-btn",
        style: "display: inline-flex; align-items: center;"
      },
      name: "Apply Concurrency"
    });

    this.proc_controls = new ve.RawInterface({
      threads: this.proc_threads_input,
      apply: this.proc_apply_btn
    }, {
      attributes: {
        style: "display: inline-flex; align-items: center; gap: 0.5rem;"
      },
      no_name_element: true
    });

    let proc_header = document.createElement("div");
    proc_header.className = "sm-section-header";
    proc_header.innerHTML = `
      <div style="display: flex; align-items: center; gap: 0.6rem;">
        <span style="font-family: var(--body-font-family, 'Karla', sans-serif); font-size: 0.95rem; font-weight: 500; color: var(--header-colour, #ffffff);">
          Process (Compute) Worker Pool
        </span>
        <span class="sm-badge sm-badge-proc"><span id="sm-proc-count">0</span> Active</span>
      </div>
    `;
    proc_header.appendChild(this.proc_controls.element);
    proc_panel.appendChild(proc_header);

    this.proc_grid = document.createElement("div");
    this.proc_grid.className = "sm-grid";
    this.proc_grid.innerHTML = `<div style="color: rgba(255, 255, 255, 0.5); font-size: 0.85rem; padding: 0.5rem 0; font-weight: 300;">Process worker pool idle or standby.</div>`;
    proc_panel.appendChild(this.proc_grid);
    this.element.appendChild(proc_panel);
  }


  /**
   * Updates dynamic DOM metrics without reconstructing entire markup.
   */
  updateView () {
    let total_entities = 0;
    let total_rss = 0;

    //Update DB workers count
    let db_count = this.element.querySelector("#sm-db-count");
    if (db_count) db_count.textContent = String(this.db_diagnostics.length);

    //Sync concurrent threads number input with actual active threads if not currently focused by user
    let is_db_input_focused = this.db_threads_input?.element?.contains(document.activeElement);
    if (!is_db_input_focused && this.db_diagnostics.length > 0) {
      if (this.db_threads_input.v !== this.db_diagnostics.length) {
        this.db_threads_input.v = this.db_diagnostics.length;
        this.db_target_threads = this.db_diagnostics.length;
      }
    }

    if (this.db_grid) {
      if (this.db_diagnostics.length === 0) {
        this.db_grid.innerHTML = `<div style="color: rgba(255, 255, 255, 0.5); font-size: 0.85rem; padding: 0.5rem 0;">No active DB worker pool detected or savefile not yet loaded.</div>`;
      } else {
        let db_html = "";
        for (let i = 0; i < this.db_diagnostics.length; i++) {
          let diag = this.db_diagnostics[i] || {};
          let wid = (diag.worker_id !== undefined) ? diag.worker_id : i;
          let entities = diag.cached_entities || 0;
          let rss = diag.rss || 0;
          let heap_used = diag.heapUsed || 0;
          let heap_limit = diag.heapLimit || 1;
          let percentage = Math.min(100, Math.max(0, diag.percentage || (heap_used / heap_limit)*100));

          total_entities += entities;
          total_rss += rss;

          let color = "#4ade80";
          if (percentage > 85) {
            color = "var(--accent-secondary-colour, #f03c3c)";
          } else if (percentage > 65) {
            color = "#f59e0b";
          }

          db_html += `
            <div class="sm-tile">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                <div style="font-family: var(--body-font-family, 'Karla', sans-serif); font-weight: 500; font-size: 0.85rem; color: var(--header-colour, #ffffff);">
                  Partition Shard #${wid}
                </div>
                <span class="sm-badge sm-badge-online">Online</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: rgba(255, 255, 255, 0.6); margin-top: 0.25rem;">
                <span style="font-weight: 300;">Cached Entities:</span>
                <span style="font-family: var(--body-font-family, 'Karla', sans-serif); font-weight: 400; color: var(--body-colour, #ffffff);">${this.formatNumber(entities)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: rgba(255, 255, 255, 0.6); margin-top: 0.2rem;">
                <span style="font-weight: 300;">RSS Memory:</span>
                <span style="font-family: var(--body-font-family, 'Karla', sans-serif); font-weight: 400; color: var(--body-colour, #ffffff);">${this.formatBytes(rss)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: rgba(255, 255, 255, 0.6); margin-top: 0.2rem;">
                <span style="font-weight: 300;">Heap Allocated:</span>
                <span style="font-family: var(--body-font-family, 'Karla', sans-serif); font-weight: 400; color: rgba(255, 255, 255, 0.8);">${this.formatBytes(heap_used)} / ${this.formatBytes(heap_limit)}</span>
              </div>
              <div class="sm-progress-track">
                <div class="sm-progress-fill" style="width: ${percentage}%; background: ${color};"></div>
              </div>
            </div>
          `;
        }
        this.db_grid.innerHTML = db_html;
      }
    }

    //Update Process workers count
    let proc_count = this.element.querySelector("#sm-proc-count");
    if (proc_count) proc_count.textContent = String(this.proc_diagnostics.length);

    let is_proc_input_focused = this.proc_threads_input?.element?.contains(document.activeElement);
    if (!is_proc_input_focused && this.proc_diagnostics.length > 0) {
      if (this.proc_threads_input.v !== this.proc_diagnostics.length) {
        this.proc_threads_input.v = this.proc_diagnostics.length;
        this.proc_target_threads = this.proc_diagnostics.length;
      }
    }

    if (this.proc_grid) {
      if (this.proc_diagnostics.length === 0) {
        this.proc_grid.innerHTML = `<div style="color: rgba(255, 255, 255, 0.5); font-size: 0.85rem; padding: 0.5rem 0;">Process worker pool idle or standby.</div>`;
      } else {
        let proc_html = "";
        for (let i = 0; i < this.proc_diagnostics.length; i++) {
          let diag = this.proc_diagnostics[i] || {};
          let wid = (diag.worker_id !== undefined) ? diag.worker_id : i;
          let active_tasks = diag.active_tasks || 0;
          let rss = diag.rss || 0;
          let heap_used = diag.heapUsed || 0;
          let heap_limit = diag.heapLimit || 1;
          let percentage = Math.min(100, Math.max(0, diag.percentage || (heap_used / heap_limit)*100));

          total_rss += rss;

          let color = "#38bdf8";
          if (percentage > 85) {
            color = "var(--accent-secondary-colour, #f03c3c)";
          } else if (percentage > 65) {
            color = "#f59e0b";
          }

          proc_html += `
            <div class="sm-tile">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                <div style="font-family: var(--body-font-family, 'Karla', sans-serif); font-weight: 500; font-size: 0.85rem; color: var(--header-colour, #ffffff);">
                  Compute Worker #${wid}
                </div>
                <span class="sm-badge sm-badge-proc">Ready</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: rgba(255, 255, 255, 0.6); margin-top: 0.25rem;">
                <span style="font-weight: 300;">Active Tasks:</span>
                <span style="font-family: var(--body-font-family, 'Karla', sans-serif); font-weight: 400; color: ${active_tasks > 0 ? 'var(--accent-secondary-colour, #f03c3c)' : 'var(--body-colour, #ffffff)'};">${active_tasks}</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: rgba(255, 255, 255, 0.6); margin-top: 0.2rem;">
                <span style="font-weight: 300;">RSS Memory:</span>
                <span style="font-family: var(--body-font-family, 'Karla', sans-serif); font-weight: 400; color: var(--body-colour, #ffffff);">${this.formatBytes(rss)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: rgba(255, 255, 255, 0.6); margin-top: 0.2rem;">
                <span style="font-weight: 300;">Heap Allocated:</span>
                <span style="font-family: var(--body-font-family, 'Karla', sans-serif); font-weight: 400; color: rgba(255, 255, 255, 0.8);">${this.formatBytes(heap_used)} / ${this.formatBytes(heap_limit)}</span>
              </div>
              <div class="sm-progress-track">
                <div class="sm-progress-fill" style="width: ${percentage}%; background: ${color};"></div>
              </div>
            </div>
          `;
        }
        this.proc_grid.innerHTML = proc_html;
      }
    }

    //Update Top Banner Summary
    let summary_entities = this.element.querySelector("#sm-summary-entities");
    if (summary_entities) summary_entities.textContent = this.formatNumber(total_entities);

    let summary_ram = this.element.querySelector("#sm-summary-ram");
    if (summary_ram) summary_ram.textContent = this.formatBytes(total_rss);
  }
};

//Functional binding
global.veSystemManager = function (arg0_options) {
  return new UI_SystemManager(arg0_options);
};
