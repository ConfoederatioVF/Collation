let fs = require("node:fs");
let path = require("node:path");
let { Worker } = require("node:worker_threads");

async function runTests() {
  console.log("=== Testing Modular png_worker.js ===");

  let worker_path = path.resolve("./UF/js/geospatiale/files/png/png_worker.js");
  let test_dir = path.resolve("./tests/temp_worker_test/");
  if (!fs.existsSync(test_dir)) fs.mkdirSync(test_dir, { recursive: true });

  let worker = new Worker(worker_path, {
    workerData: {
      root_dir: process.cwd(),
      worker_id: 1
    }
  });

  let task_id_counter = 0;
  let pending_tasks = new Map();

  worker.on("message", (msg) => {
    let resolve = pending_tasks.get(msg.task_id);
    if (resolve) {
      pending_tasks.delete(msg.task_id);
      resolve(msg);
    }
  });

  worker.on("error", (err) => {
    console.error("Worker error:", err);
  });

  function sendTask(task) {
    let task_id = ++task_id_counter;
    task.task_id = task_id;
    return new Promise((resolve) => {
      pending_tasks.set(task_id, resolve);
      worker.postMessage(task);
    });
  }

  try {
    // 1. Test ping
    console.log("1. Testing ping...");
    let ping_res = await sendTask({ type: "ping" });
    if (!ping_res.success || !ping_res.result.pong) {
      throw new Error(`Ping failed: ${JSON.stringify(ping_res)}`);
    }
    console.log("   [PASS] Ping response:", ping_res.result);

    // 2. Test blank_raster
    console.log("2. Testing blank_raster...");
    let blank_path = path.join(test_dir, "test_blank.png");
    let blank_res = await sendTask({
      type: "blank_raster",
      output_path: blank_path,
      width: 100,
      height: 50,
      format: "float32"
    });
    if (!blank_res.success || !fs.existsSync(blank_path)) {
      throw new Error(`Blank raster failed: ${JSON.stringify(blank_res)}`);
    }
    console.log("   [PASS] Blank raster created at:", blank_path);

    // 3. Test convert_to_int32
    console.log("3. Testing convert_to_int32...");
    let int32_path = path.join(test_dir, "test_int32.png");
    let int_res = await sendTask({
      type: "convert_to_int32",
      input_path: blank_path,
      output_path: int32_path,
      rounding_method: "round"
    });
    if (!int_res.success || !fs.existsSync(int32_path)) {
      throw new Error(`Convert to int32 failed: ${JSON.stringify(int_res)}`);
    }
    console.log("   [PASS] Int32 raster created at:", int32_path);

    // 4. Test copy
    console.log("4. Testing copy...");
    let copy_path = path.join(test_dir, "test_copy.png");
    let copy_res = await sendTask({
      type: "copy",
      from_file_path: blank_path,
      output_file_path: copy_path
    });
    if (!copy_res.success || !fs.existsSync(copy_path)) {
      throw new Error(`Copy failed: ${JSON.stringify(copy_res)}`);
    }
    console.log("   [PASS] File copied to:", copy_path);

    // 5. Test raster_operation (scalar scale)
    console.log("5. Testing raster_operation...");
    let scale_path = path.join(test_dir, "test_scale.png");
    let scale_res = await sendTask({
      type: "raster_operation",
      input_path_1: blank_path,
      output_path: scale_path,
      scalar: 2.5
    });
    if (!scale_res.success || !fs.existsSync(scale_path)) {
      throw new Error(`Raster operation failed: ${JSON.stringify(scale_res)}`);
    }
    console.log("   [PASS] Raster operation produced:", scale_path);

    // 6. Test eval_handler
    console.log("6. Testing eval_handler...");
    let eval_res = await sendTask({
      type: "eval_handler",
      handler_source: "function(item) { return item.value * 10; }",
      item: { value: 42 }
    });
    if (!eval_res.success || eval_res.result !== 420) {
      throw new Error(`Eval handler failed: ${JSON.stringify(eval_res)}`);
    }
    console.log("   [PASS] Eval handler returned:", eval_res.result);

    console.log("\n=== ALL PNG_WORKER MODULAR TESTS PASSED! ===");
  } finally {
    worker.terminate();
    // Clean up temporary test files
    if (fs.existsSync(test_dir)) {
      fs.rmSync(test_dir, { recursive: true, force: true });
    }
  }
}

runTests().catch((err) => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
