/**
 * System Manager component for real-time DB and Process worker diagnostics and concurrency control.
 *
 * @type {UI_SystemManager}
 */
global.UI_SystemManager = class extends ve.Component {
  constructor (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};
    super(options);

    //Declare local instance variables
    this.auto_refresh = true;
    this.db_diagnostics = [];
    this.db_target_threads = (global.ve?.ndjson_worker_pool?.length) ?
      global.ve.ndjson_worker_pool.length : Math.max(1, (os?.cpus?.()?.length || 4) - 1);
    this.is_updating_db = false;
    this.is_updating_proc = false;
    this.options = options;
    this.proc_diagnostics = [];
    this.proc_target_threads = (global.proc?.worker_pool?.length) ?
      global.proc.worker_pool.length : Math.max(1, Math.min(4, Math.ceil(((os?.cpus?.()?.length || 4) - 1) / 4)));

    //Build container element
    this.element = document.createElement("div");
    this.element.setAttribute("component", "ui-system-manager");
    this.element.style.cssText = `
      display: flex;
      flex-direction: column;
      height: 100%;
      width: 100%;
      overflow-y: auto;
      background: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #0f172a 100%);
      color: #f1f5f9;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      padding: 1.5rem;
      box-sizing: border-box;
      gap: 1.5rem;
    `;

    //Initial draw & start live polling
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
   * Builds the initial DOM layout skeleton.
   */
  render () {
    let os_module = (typeof os !== "undefined") ? os : require("node:os");
    let cpu_count = os_module.cpus ? os_module.cpus().length : 4;
    let total_ram = os_module.totalmem ? this.formatBytes(os_module.totalmem()) : "N/A";
    let free_ram = os_module.freemem ? this.formatBytes(os_module.freemem()) : "N/A";

    this.element.innerHTML = `
      <style>
        .sm-card {
          background: rgba(30, 41, 59, 0.6);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          backdrop-filter: blur(16px);
          padding: 1.25rem;
          box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.3);
          transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .sm-card:hover {
          border-color: rgba(99, 102, 241, 0.3);
        }
        .sm-btn {
          background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%);
          border: none;
          color: #ffffff;
          padding: 0.5rem 1rem;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          font-size: 0.875rem;
          transition: opacity 0.2s ease, transform 0.1s ease;
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
        }
        .sm-btn:hover {
          opacity: 0.9;
          transform: translateY(-1px);
        }
        .sm-btn:active {
          transform: translateY(0);
        }
        .sm-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .sm-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.25rem 0.65rem;
          border-radius: 9999px;
          font-size: 0.75rem;
          font-weight: 600;
          letter-spacing: 0.025em;
        }
        .sm-badge-online {
          background: rgba(16, 185, 129, 0.15);
          color: #34d399;
          border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .sm-badge-proc {
          background: rgba(59, 130, 246, 0.15);
          color: #60a5fa;
          border: 1px solid rgba(59, 130, 246, 0.3);
        }
        .sm-dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background: currentColor;
          box-shadow: 0 0 8px currentColor;
        }
        .sm-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 1rem;
        }
        .sm-progress-track {
          width: 100%;
          height: 8px;
          background: rgba(255, 255, 255, 0.06);
          border-radius: 9999px;
          overflow: hidden;
          margin-top: 0.5rem;
        }
        .sm-progress-fill {
          height: 100%;
          border-radius: 9999px;
          transition: width 0.4s ease, background 0.4s ease;
        }
        .sm-input {
          background: rgba(15, 23, 42, 0.8);
          border: 1px solid rgba(255, 255, 255, 0.15);
          border-radius: 6px;
          color: #f8fafc;
          padding: 0.4rem 0.75rem;
          font-size: 0.9rem;
          outline: none;
          width: 70px;
        }
        .sm-input:focus {
          border-color: #6366f1;
        }
      </style>

      <!-- Header Section -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem;">
        <div>
          <h2 style="margin: 0; font-size: 1.5rem; font-weight: 700; background: linear-gradient(90deg, #f8fafc, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            System & Multithreading Manager
          </h2>
          <div style="color: #94a3b8; font-size: 0.875rem; margin-top: 0.25rem;">
            Real-time diagnostics and concurrent thread pool orchestration
          </div>
        </div>

        <div style="display: flex; align-items: center; gap: 1rem;">
          <label style="display: inline-flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: #cbd5e1; cursor: pointer;">
            <input type="checkbox" id="sm-auto-refresh" checked style="cursor: pointer;" />
            Auto-refresh (1,5s)
          </label>
          <button class="sm-btn" id="sm-refresh-btn" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15);">
            🔄 Refresh Now
          </button>
        </div>
      </div>

      <!-- System Overview Banner -->
      <div class="sm-card" style="display: flex; flex-wrap: wrap; gap: 2rem; justify-content: space-around; background: rgba(15, 23, 42, 0.75);">
        <div>
          <div style="font-size: 0.75rem; text-transform: uppercase; color: #64748b; font-weight: 700; letter-spacing: 0.05em;">CPU Logical Cores</div>
          <div style="font-size: 1.4rem; font-weight: 700; color: #38bdf8; margin-top: 0.2rem;">${cpu_count} Threads</div>
        </div>
        <div>
          <div style="font-size: 0.75rem; text-transform: uppercase; color: #64748b; font-weight: 700; letter-spacing: 0.05em;">System RAM Available</div>
          <div style="font-size: 1.4rem; font-weight: 700; color: #34d399; margin-top: 0.2rem;">${free_ram} <span style="font-size: 0.85rem; color: #64748b;">/ ${total_ram}</span></div>
        </div>
        <div>
          <div style="font-size: 0.75rem; text-transform: uppercase; color: #64748b; font-weight: 700; letter-spacing: 0.05em;">Total Cached Geometries</div>
          <div id="sm-summary-entities" style="font-size: 1.4rem; font-weight: 700; color: #f59e0b; margin-top: 0.2rem;">0</div>
        </div>
        <div>
          <div style="font-size: 0.75rem; text-transform: uppercase; color: #64748b; font-weight: 700; letter-spacing: 0.05em;">Worker Memory Footprint</div>
          <div id="sm-summary-ram" style="font-size: 1.4rem; font-weight: 700; color: #c084fc; margin-top: 0.2rem;">0 MB</div>
        </div>
      </div>

      <!-- Database (DB) Workers Section -->
      <div class="sm-card">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 0.75rem;">
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #f8fafc;">Database (DB) Worker Pool</div>
            <span class="sm-badge sm-badge-online"><span class="sm-dot"></span> <span id="sm-db-count">0</span> Active</span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span style="font-size: 0.85rem; color: #94a3b8;">Concurrent Threads:</span>
            <input type="number" id="sm-db-threads-input" class="sm-input" min="1" max="32" value="${this.db_target_threads}" />
            <button class="sm-btn" id="sm-db-apply-btn">Apply DB Threads</button>
          </div>
        </div>
        <div id="sm-db-grid" class="sm-grid">
          <div style="color: #64748b; font-size: 0.9rem; padding: 1rem;">No DB workers active or file not yet loaded.</div>
        </div>
      </div>

      <!-- Process (Proc) Workers Section -->
      <div class="sm-card">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 0.75rem;">
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #f8fafc;">Process (Compute) Worker Pool</div>
            <span class="sm-badge sm-badge-proc"><span class="sm-dot"></span> <span id="sm-proc-count">0</span> Active</span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span style="font-size: 0.85rem; color: #94a3b8;">Concurrent Threads:</span>
            <input type="number" id="sm-proc-threads-input" class="sm-input" min="1" max="32" value="${this.proc_target_threads}" />
            <button class="sm-btn" id="sm-proc-apply-btn" style="background: linear-gradient(135deg, #2563eb 0%, #06b6d4 100%);">Apply Proc Threads</button>
          </div>
        </div>
        <div id="sm-proc-grid" class="sm-grid">
          <div style="color: #64748b; font-size: 0.9rem; padding: 1rem;">Process workers idle or initializing.</div>
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
            db_apply_btn.textContent = "Apply DB Threads";
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
            proc_apply_btn.textContent = "Apply Proc Threads";
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
        db_grid.innerHTML = `<div style="color: #64748b; font-size: 0.9rem; padding: 1rem;">No DB workers active or file not yet loaded.</div>`;
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

          let color = "#10b981";
          if (percentage > 80) color = "#ef4444";
          else if (percentage > 60) color = "#f59e0b";

          db_html += `
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 1rem;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <div style="font-weight: 600; color: #e2e8f0; font-size: 0.95rem;">Partition Shard #${wid}</div>
                <span class="sm-badge sm-badge-online"><span class="sm-dot"></span> Online</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.825rem; color: #94a3b8; margin-top: 0.4rem;">
                <span>Cached Entities:</span>
                <span style="font-weight: 600; color: #f8fafc;">${this.formatNumber(entities)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.825rem; color: #94a3b8; margin-top: 0.25rem;">
                <span>RSS Memory:</span>
                <span style="font-weight: 600; color: #38bdf8;">${this.formatBytes(rss)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.825rem; color: #94a3b8; margin-top: 0.25rem;">
                <span>Heap Allocated:</span>
                <span style="color: #cbd5e1;">${this.formatBytes(heap_used)} / ${this.formatBytes(heap_limit)}</span>
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
        proc_grid.innerHTML = `<div style="color: #64748b; font-size: 0.9rem; padding: 1rem;">Process workers idle or initializing.</div>`;
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

          let color = "#3b82f6";
          if (percentage > 80) color = "#ef4444";
          else if (percentage > 60) color = "#f59e0b";

          proc_html += `
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 1rem;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <div style="font-weight: 600; color: #e2e8f0; font-size: 0.95rem;">Compute Worker #${wid}</div>
                <span class="sm-badge sm-badge-proc"><span class="sm-dot"></span> Ready</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.825rem; color: #94a3b8; margin-top: 0.4rem;">
                <span>Active Tasks:</span>
                <span style="font-weight: 600; color: ${active_tasks > 0 ? '#38bdf8' : '#64748b'};">${active_tasks}</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.825rem; color: #94a3b8; margin-top: 0.25rem;">
                <span>RSS Memory:</span>
                <span style="font-weight: 600; color: #60a5fa;">${this.formatBytes(rss)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.825rem; color: #94a3b8; margin-top: 0.25rem;">
                <span>Heap Allocated:</span>
                <span style="color: #cbd5e1;">${this.formatBytes(heap_used)} / ${this.formatBytes(heap_limit)}</span>
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
