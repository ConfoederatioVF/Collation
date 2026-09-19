let cp = require("child_process");
let { Worker, isMainThread, parentPort, workerData } = require("worker_threads");
let os = require("os");

console.log("CPUs available:", os.cpus().length);

//Test worker_threads
let w = new Worker(`
  const { parentPort } = require("worker_threads");
  parentPort.postMessage({ status: "worker_thread_ok", threadId: require("worker_threads").threadId });
`, { eval: true });

w.on("message", (msg) => {
  console.log("Received from worker_thread:", msg);
});

//Test child_process.fork
let f = cp.fork("-e", ['process.send({ status: "child_process_ok", pid: process.pid });']);
f.on("message", (msg) => {
  console.log("Received from child_process:", msg);
});
