//Import libraries
let NodeWorker = require("node:worker_threads").Worker;
let os = require("node:os");
let path = require("node:path");

if (!global.proc) global.proc = {};

//Initialise worker pool and IPC management functions
{
  /**
   * Resolves active RAM diagnostic percentage statistics from every process worker in the pool.
   *
   * @returns {Promise<Array<{worker_id: number, rss: number, heapUsed: number, heapTotal: number, heapLimit: number, percentage: number}>>}
   */
  proc.IPC_getDiagnostics = async function () {
    //Declare local instance variables
    let pool = proc.IPC_getWorkerPool();
    let promises = [];

    for (let i = 0; i < pool.length; i++) {
      let task_id = proc.task_id_counter++;

      promises.push(new Promise((resolve) => {
        proc.pending_tasks.set(task_id, resolve);
        pool[i].postMessage({
          task_id: task_id,
          type: "get_diagnostics"
        });
      }));
    }

    //Return statement
    return await Promise.all(promises);
  };


  /**
   * Creates or returns the pool of workers to handle geoprocessing tasks.
   *
   * @param {number} [arg0_max_workers]
   *
   * @returns {NodeWorker[]}
   */
  proc.IPC_getWorkerPool = function (arg0_max_workers) {
    //Convert from parameters
    let default_workers = Math.max(1, Math.min(4, Math.ceil((os.cpus().length - 1) / 4)));
    let max_workers = (arg0_max_workers && arg0_max_workers > 0) ? arg0_max_workers : default_workers;

    if (proc.pending_tasks === undefined) proc.pending_tasks = new Map();
    if (proc.task_id_counter === undefined) proc.task_id_counter = 0;
    if (proc.worker_pool === undefined) proc.worker_pool = [];

    if (proc.worker_pool.length === 0) {
      let worker_script = path.resolve(__dirname, "process_worker.js");
      let electron_ipc = null;

      try {
        let electron = require("electron");
        electron_ipc = electron.ipcMain;
      } catch (e) {}

      for (let i = 0; i < max_workers; i++) {
        let worker = new NodeWorker(worker_script, {
          workerData: { worker_id: i }
        });

        worker.active_tasks = 0;

        worker.on("message", (response) => {
          //1. Handle proxy/bridge requests from worker to main thread
          if (response.type === "worker_ipc_request") {
            let args = response.args || [];
            let channel = response.channel;
            let task_id = response.task_id;

            if (electron_ipc) {
              let mock_event = {
                sender: {
                  send: (response_channel, results) => {
                    worker.postMessage({
                      results: results,
                      task_id: task_id,
                      type: "worker_ipc_ready"
                    });
                  }
                }
              };

              electron_ipc.emit(channel, mock_event, ...args);
            } else if (global.NDJSON && channel === "ndjson") {
              let func_key = args[0];
              let func_args = args.slice(1);
              if (typeof NDJSON[func_key] === "function") {
                Promise.resolve(NDJSON[func_key](...func_args)).then((res) => {
                  worker.postMessage({
                    results: res,
                    task_id: task_id,
                    type: "worker_ipc_ready"
                  });
                });
              }
            }
            return;
          }

          //2. Handle standard task/diagnostic responses
          let callback = proc.pending_tasks.get(response.task_id);
          if (callback) {
            callback(response.results !== undefined ? response.results : response);
            proc.pending_tasks.delete(response.task_id);
          }
        });

        worker.on("error", (err) => {
          console.error(`[proc_main] Worker ${i} encountered error:`, err);
        });

        proc.worker_pool.push(worker);
      }
    }

    //Return statement
    return proc.worker_pool;
  };


  /**
   * Sends a geoprocessing task to subordinate workers.
   *
   * @param {Object} arg0_json
   *
   * @returns {Promise<any>}
   */
  proc.IPC_task = async function (arg0_json) {
    //Convert from parameters
    let json = (arg0_json) ? arg0_json : {};

    //Declare local instance variables
    let pool = proc.IPC_getWorkerPool();
    let selected_worker = pool[0];
    let min_tasks = selected_worker.active_tasks || 0;

    for (let i = 1; i < pool.length; i++) {
      let active_tasks = pool[i].active_tasks || 0;
      if (active_tasks < min_tasks) {
        min_tasks = active_tasks;
        selected_worker = pool[i];
      }
    }

    if (selected_worker.active_tasks === undefined) selected_worker.active_tasks = 0;
    selected_worker.active_tasks++;

    let task_id = proc.task_id_counter++;

    //Return statement
    return new Promise((resolve) => {
      proc.pending_tasks.set(task_id, (result) => {
        selected_worker.active_tasks = Math.max(0, (selected_worker.active_tasks || 1) - 1);
        resolve(result);
      });

      selected_worker.postMessage({
        action: json.action || json.type,
        action_key: json.action_key || json.type,
        payload: json.payload || json.value || json,
        task_id: task_id,
        type: json.type || json.action_key
      });
    });
  };


  /**
   * Cleanly terminates all process workers in the pool.
   *
   * @returns {Promise<void>}
   */
  proc.IPC_terminate = async function () {
    if (proc.worker_pool) {
      for (let i = 0; i < proc.worker_pool.length; i++) {
        try {
          await proc.worker_pool[i].terminate();
        } catch (e) {}
      }
      proc.worker_pool = [];
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = proc;
