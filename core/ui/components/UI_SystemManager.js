/**
 * System Manager component for real-time DB and Process worker diagnostics and concurrency control.
 * Restyled to adhere natively to Vercengen's core design system and typography.
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
   * Cleans up running intervals when the component is removed.
   */
  destroy () {
    if (this.poll_interval) {
      clearInterval(this.poll_interval);
      this.poll_interval = null;
    }
  }


  /**
   * Fetches latest metrics from DB and Process worker pools and updates UI.
   */
  async refreshDiagnostics () {
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
   * Builds the initial DOM layout skeleton conforming strictly to Vercengen UI conventions.
   */
  render () {
    let os_module = (typeof os !== "undefined") ? os : ((typeof require === "function") ? require("node:os") : null);
    let cpu_count = os_module?.cpus ? os_module.cpus().length : 4;
    let total_ram = os_module?.totalmem ? this.formatBytes(os_module.totalmem()) : "N/A";
    let free_ram = os_module?.freemem ? this.formatBytes(os_module.freemem()) : "N/A";

    this.element.innerHTML = `
      <style>
        .sm-panel {
          background: rgba(255, 255, 255, 0.03);
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: calc(var(--padding, 0.5rem)*0.5);
          padding: calc(var(--padding, 0.5rem)*1.25);
        }
        .sm-btn {
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
        .sm-btn:hover {
          background-color: var(--accent-primary-colour, rgba(200, 40, 40));
          border-color: var(--accent-secondary-colour, rgba(240, 60, 60));
          cursor: pointer;
        }
        .sm-btn:active {
          opacity: 0.85;
        }
        .sm-btn:disabled {
          opacity: 0.4;
          cursor: not-allowed;
          background-color: rgba(255, 255, 255, 0.03) !important;
        }
        .sm-badge {
          display: inline-flex;
          align-items: center;
          padding: 0.12rem 0.5rem;
          border-radius: 2px;
          font-size: 0.7rem;
          font-weight: 400;
          letter-spacing: 0.04em;
          text-transform: uppercase;
        }
        .sm-badge-online {
          background: rgba(34, 197, 94, 0.08);
          color: #4ade80;
          border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .sm-badge-proc {
          background: rgba(56, 189, 248, 0.08);
          color: #38bdf8;
          border: 1px solid rgba(56, 189, 248, 0.3);
        }
        .sm-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
          gap: 0.6rem;
        }
        .sm-tile {
          background: rgba(255, 255, 255, 0.02);
          backdrop-filter: blur(4px);
          -webkit-backdrop-filter: blur(4px);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: calc(var(--padding, 0.5rem)*0.5);
          padding: 0.65rem 0.85rem;
          transition: border-color 0.2s ease, background 0.2s ease;
        }
        .sm-tile:hover {
          background: rgba(255, 255, 255, 0.04);
          border-color: rgba(255, 255, 255, 0.16);
        }
        .sm-progress-track {
          width: 100%;
          height: 3px;
          background: rgba(255, 255, 255, 0.06);
          border-radius: 1.5px;
          overflow: hidden;
          margin-top: 0.45rem;
        }
        .sm-progress-fill {
          height: 100%;
          border-radius: 1.5px;
          transition: width 0.3s ease, background 0.3s ease;
        }
        .sm-input {
          background: transparent;
          border: none;
          border-bottom: 1px solid rgba(255, 255, 255, 0.25);
          color: var(--body-colour, #ffffff);
          font-family: var(--body-font-family, "Karla", sans-serif);
          font-size: var(--body-font-size, 0.85rem);
          font-weight: 400;
          padding: 0.15rem 0.3rem;
          outline: none;
          width: 44px;
          text-align: center;
          transition: border-bottom-color 0.2s ease;
        }
        .sm-input:focus {
          border-bottom-color: var(--accent-primary-colour, rgba(200, 40, 40));
        }
      </style>

      <!-- Header Section -->
      <div style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 0.75rem; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 0.75rem;">
        <div>
          <h2 style="margin: 0; font-family: var(--header-font-family, 'Karla', sans-serif); font-size: 1.2rem; font-weight: 500; color: var(--header-colour, #ffffff); letter-spacing: 0.01em;">
            Current Resources
          </h2>
        </div>

        <div style="display: flex; align-items: center; gap: 0.75rem;">
          <label style="display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.8rem; color: rgba(255, 255, 255, 0.7); font-weight: 300; cursor: pointer;">
            <input type="checkbox" id="sm-auto-refresh" checked style="cursor: pointer; accent-color: var(--accent-primary-colour, #c82828);" />
            Auto-refresh (1,5s)
          </label>
          <button class="sm-btn" id="sm-refresh-btn">
            Refresh
          </button>
        </div>
      </div>

      <!-- System Overview Metrics Bar -->
      <div class="sm-panel" style="display: flex; flex-wrap: wrap; gap: 1.5rem; justify-content: space-around; align-items: center;">
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
      </div>

      <!-- Database (DB) Workers Section -->
      <div class="sm-panel">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 0.75rem; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 0.5rem;">
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <span style="font-family: var(--body-font-family, 'Karla', sans-serif); font-size: 0.95rem; font-weight: 500; color: var(--header-colour, #ffffff);">
              Database (DB) Worker Pool
            </span>
            <span class="sm-badge sm-badge-online"><span id="sm-db-count">0</span> Active</span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 0.8rem; color: rgba(255, 255, 255, 0.6); font-weight: 300;">Concurrent Threads:</span>
            <input type="number" id="sm-db-threads-input" class="sm-input" min="1" max="32" value="${this.db_target_threads}" />
            <button class="sm-btn" id="sm-db-apply-btn">Apply Concurrency</button>
          </div>
        </div>
        <div id="sm-db-grid" class="sm-grid">
          <div style="color: rgba(255, 255, 255, 0.5); font-size: 0.85rem; padding: 0.5rem 0; font-weight: 300;">No active DB worker pool detected or savefile not yet loaded.</div>
        </div>
      </div>

      <!-- Process (Compute) Workers Section -->
      <div class="sm-panel">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 0.75rem; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 0.5rem;">
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <span style="font-family: var(--body-font-family, 'Karla', sans-serif); font-size: 0.95rem; font-weight: 500; color: var(--header-colour, #ffffff);">
              Process (Compute) Worker Pool
            </span>
            <span class="sm-badge sm-badge-proc"><span id="sm-proc-count">0</span> Active</span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 0.8rem; color: rgba(255, 255, 255, 0.6); font-weight: 300;">Concurrent Threads:</span>
            <input type="number" id="sm-proc-threads-input" class="sm-input" min="1" max="32" value="${this.proc_target_threads}" />
            <button class="sm-btn" id="sm-proc-apply-btn">Apply Concurrency</button>
          </div>
        </div>
        <div id="sm-proc-grid" class="sm-grid">
          <div style="color: rgba(255, 255, 255, 0.5); font-size: 0.85rem; padding: 0.5rem 0; font-weight: 300;">Process worker pool idle or standby.</div>
        </div>
      </div>
    `;

    //Bind event listeners
    let auto_refresh_cb = this.element.querySelector("#sm-auto-refresh");
    if (auto_refresh_cb) {
      auto_refresh_cb.addEventListener("change", (e) => {
        this.auto_refresh = e.target.checked;
      });
    }

    let refresh_btn = this.element.querySelector("#sm-refresh-btn");
    if (refresh_btn) {
      refresh_btn.addEventListener("click", () => {
        this.refreshDiagnostics();
      });
    }

    let db_apply_btn = this.element.querySelector("#sm-db-apply-btn");
    let db_input = this.element.querySelector("#sm-db-threads-input");
    if (db_apply_btn && db_input) {
      db_apply_btn.addEventListener("click", async () => {
        let count = parseInt(db_input.value);
        if (count > 0 && !this.is_updating_db) {
          this.is_updating_db = true;
          db_apply_btn.disabled = true;
          db_apply_btn.textContent = "Updating...";
          try {
            if (global.db?.setWorkerPoolSize) {
              await db.setWorkerPoolSize(count);
            }
            await this.refreshDiagnostics();
          } finally {
            this.is_updating_db = false;
            db_apply_btn.disabled = false;
            db_apply_btn.textContent = "Apply Concurrency";
          }
        }
      });
    }

    let proc_apply_btn = this.element.querySelector("#sm-proc-apply-btn");
    let proc_input = this.element.querySelector("#sm-proc-threads-input");
    if (proc_apply_btn && proc_input) {
      proc_apply_btn.addEventListener("click", async () => {
        let count = parseInt(proc_input.value);
        if (count > 0 && !this.is_updating_proc) {
          this.is_updating_proc = true;
          proc_apply_btn.disabled = true;
          proc_apply_btn.textContent = "Updating...";
          try {
            if (global.proc?.setWorkerPoolSize) {
              await proc.setWorkerPoolSize(count);
            }
            await this.refreshDiagnostics();
          } finally {
            this.is_updating_proc = false;
            proc_apply_btn.disabled = false;
            proc_apply_btn.textContent = "Apply Concurrency";
          }
        }
      });
    }
  }


  /**
   * Updates dynamic DOM metrics without reconstructing entire markup.
   */
  updateView () {
    let total_entities = 0;
    let total_rss = 0;

    //Update DB workers
    let db_grid = this.element.querySelector("#sm-db-grid");
    let db_count = this.element.querySelector("#sm-db-count");
    if (db_count) db_count.textContent = String(this.db_diagnostics.length);

    if (db_grid) {
      if (this.db_diagnostics.length === 0) {
        db_grid.innerHTML = `<div style="color: rgba(255, 255, 255, 0.5); font-size: 0.85rem; padding: 0.5rem 0;">No active DB worker pool detected or savefile not yet loaded.</div>`;
      } else {
        let db_html = "";
        for (let i = 0; i < this.db_diagnostics.length; i++) {
          let diag = this.db_diagnostics[i] || {};
          let wid = diag.worker_id !== undefined ? diag.worker_id : i;
          let entities = diag.cached_entities || 0;
          let rss = diag.rss || 0;
          let heap_used = diag.heapUsed || 0;
          let heap_limit = diag.heapLimit || 1;
          let percentage = Math.min(100, Math.max(0, diag.percentage || (heap_used / heap_limit) * 100));

          total_entities += entities;
          total_rss += rss;

          let color = "#4ade80";
          if (percentage > 85) color = "var(--accent-secondary-colour, #f03c3c)";
          else if (percentage > 65) color = "#f59e0b";

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
        db_grid.innerHTML = db_html;
      }
    }

    //Update Process workers
    let proc_grid = this.element.querySelector("#sm-proc-grid");
    let proc_count = this.element.querySelector("#sm-proc-count");
    if (proc_count) proc_count.textContent = String(this.proc_diagnostics.length);

    if (proc_grid) {
      if (this.proc_diagnostics.length === 0) {
        proc_grid.innerHTML = `<div style="color: rgba(255, 255, 255, 0.5); font-size: 0.85rem; padding: 0.5rem 0;">Process worker pool idle or standby.</div>`;
      } else {
        let proc_html = "";
        for (let i = 0; i < this.proc_diagnostics.length; i++) {
          let diag = this.proc_diagnostics[i] || {};
          let wid = diag.worker_id !== undefined ? diag.worker_id : i;
          let active_tasks = diag.active_tasks || 0;
          let rss = diag.rss || 0;
          let heap_used = diag.heapUsed || 0;
          let heap_limit = diag.heapLimit || 1;
          let percentage = Math.min(100, Math.max(0, diag.percentage || (heap_used / heap_limit) * 100));

          total_rss += rss;

          let color = "#38bdf8";
          if (percentage > 85) color = "var(--accent-secondary-colour, #f03c3c)";
          else if (percentage > 65) color = "#f59e0b";

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
        proc_grid.innerHTML = proc_html;
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
