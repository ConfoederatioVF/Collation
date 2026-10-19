let { Worker, isMainThread, parentPort } = require("node:worker_threads");
let v8 = require("node:v8");

if (isMainThread) {
  let w = new Worker(__filename, {
    resourceLimits: {
      maxOldGenerationSizeMb: 4096,
      maxYoungGenerationSizeMb: 128
    }
  });
  w.on("message", (msg) => {
    console.log("Worker reported heap limit:", (msg.heapLimit / 1024 / 1024).toFixed(2), "MB");
  });
  w.on("exit", () => console.log("Worker exited"));
} else {
  let stats = v8.getHeapStatistics();
  parentPort.postMessage({ heapLimit: stats.heap_size_limit });
  process.exit(0);
}
