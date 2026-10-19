let fs = require("node:fs");
let path = require("node:path");
let v8 = require("node:v8");

require("../UF/js/vercengen/db/NDJSON_main.js");

async function run() {
  let pool = NDJSON.getWorkerPool(8);
  console.log("Worker pool created, count:", pool.length);
  
  let diag_before = await NDJSON.task(7, { type: "get_diagnostics" });
  console.log("Worker 7 diagnostics before init:", diag_before);
  
  console.log("Sending init_partition to Worker 7...");
  let init_res = await NDJSON.task(7, {
    type: "init_partition",
    file_path: path.resolve("saves/detailed.naissance")
  });
  console.log("Worker 7 init result:", init_res);
  
  let diag_after = await NDJSON.task(7, { type: "get_diagnostics" });
  console.log("Worker 7 diagnostics after init:", diag_after);
  
  await NDJSON.terminate();
}

run().catch(console.error);
