//Import libraries
let path = require("node:path");
let v8 = require("node:v8");
let { parentPort, workerData } = require("node:worker_threads");

//Import headless dependencies
if (!global.turf)
  global.turf = require(path.resolve(__dirname, "../../../UF/js/geospatiale/turf.min.js"));

if (!global.Blacktraffic)
  require(path.resolve(__dirname, "../../../UF/js/blacktraffic/blacktraffic_basic.js"));

if (!global.db)
  require(path.resolve(__dirname, "../../db/db.js"));

if (!global.proc) global.proc = {};
if (!proc.actions) proc.actions = {};

//Import action definitions
require(path.resolve(__dirname, "../actions/spatial_actions.js"));
require(path.resolve(__dirname, "../actions/batch_feature_actions.js"));
require(path.resolve(__dirname, "../actions/attribute_actions.js"));
require(path.resolve(__dirname, "../actions/temporal_actions.js"));

//Declare local state variables
let is_ready = true;
let processing = false;
let queue = [];

//Initialise worker task handler
{
  /**
   * Executes a task passed into the worker.
   *
   * @param {Object} arg0_task
   */
  async function handleTask (arg0_task) {
    //Convert from parameters
    let task = arg0_task;

    let task_id = task.task_id;
    let type = task.type || task.action_key;

    if (!type && !task.action) {
      console.error("[proc_worker] Requires a type/action to process task:", task_id);
      return parentPort.postMessage({ error: "Missing type", task_id: task_id });
    }

    try {
      let results;
      let action_handler = proc.actions[type] || proc.actions[task.action] || proc[type];

      if (typeof action_handler === "function") {
        let payload = (task.payload !== undefined) ? task.payload : (task.value !== undefined ? task.value : task);
        results = await action_handler(payload);
      } else {
        console.error(`[proc_worker] Unknown action type "${type}" for task ${task_id}`);
        return parentPort.postMessage({ error: `Unknown action: ${type}`, task_id: task_id });
      }

      //Return statement
      return parentPort.postMessage({ results: results, task_id: task_id });
    } catch (e) {
      console.error(`[proc_worker] Error processing task ${task_id}:`, e);
      return parentPort.postMessage({ error: e.message || String(e), task_id: task_id });
    }
  }


  /**
   * Drains the queue sequentially.
   */
  async function processQueue () {
    processing = true;
    for (let i = 0; i < queue.length; i++) {
      let task = queue[i];
      await handleTask(task);
    }
    queue = [];
    processing = false;
  }


  if (parentPort) {
    parentPort.on("message", (task) => {
      if (task.type === "worker_ipc_ready") return;

      if (task.type === "get_diagnostics") {
        let memory = process.memoryUsage();
        let v8_stats = v8.getHeapStatistics();

        return parentPort.postMessage({
          results: {
            heapLimit: v8_stats.heap_size_limit,
            heapTotal: memory.heapTotal,
            heapUsed: memory.heapUsed,
            percentage: parseFloat(((memory.heapUsed / v8_stats.heap_size_limit) * 100).toFixed(2)),
            rss: memory.rss,
            worker_id: workerData?.worker_id || 0
          },
          task_id: task.task_id
        });
      }

      queue.push(task);
      if (!processing && is_ready) processQueue();
    });
  }
}
