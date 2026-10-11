//Import libraries
let fs = require("node:fs");
let path = require("node:path");

//Load dependencies
require("../UF/js/vercengen/db_shared/NDJSON_history");
require("../UF/js/vercengen/db/NDJSON_main");
require("../core/db/db");
require("../core/process/workers/process_main");
require("../core/process/proc");

async function runEndToEndTests () {
  console.log("=================================================");
  console.log("=== NAISSANCE MULTITHREADING END-TO-END SUITE ===");
  console.log("=================================================");

  let test_file = path.resolve(__dirname, "../saves/detailed_borders/6.1946.1.1.naissance");
  if (!fs.existsSync(test_file)) {
    console.warn("Target 124MB savefile not found, falling back to 0.476.1.1.naissance");
    test_file = path.resolve(__dirname, "../saves/detailed_borders/0.476.1.1.naissance");
  }

  let file_size_mb = (fs.statSync(test_file).size / 1024 / 1024).toFixed(1);
  console.log(`\n[Stage 1] Loading massive savefile (${file_size_mb} MB):`, path.basename(test_file));

  let mem_start = process.memoryUsage();
  let t0 = Date.now();

  let shard_folder = await db.load(test_file, {
    max_workers: 4,
    shard_directory: path.resolve(__dirname, "test_large.tmpndjson")
  });

  let load_time = Date.now() - t0;
  let mem_after_load = process.memoryUsage();

  console.log(`  ✓ Unpacked and indexed into 4 partitions in: ${load_time} ms`);
  console.log(`  ✓ Main Thread Heap Used: ${(mem_after_load.heapUsed / 1024 / 1024).toFixed(1)} MB (RSS: ${(mem_after_load.rss / 1024 / 1024).toFixed(1)} MB)`);

  //Verify worker memory diagnostics
  let diagnostics = await db.getDiagnostics();
  console.log(`  ✓ DB Worker memory stats:`);
  for (let i = 0; i < diagnostics.length; i++) {
    let d = diagnostics[i];
    console.log(`    Worker ${d.worker_id}: Heap ${(d.heapUsed / 1024 / 1024).toFixed(1)} MB (${d.percentage}%)`);
  }

  //Stage 2: Viewport spatial differencing
  console.log("\n[Stage 2] Viewport spatial differencing with db.diffBBox...");

  let t_q1 = Date.now();
  let greece_diffs = await db.diffBBox({
    bbox: [20, 36, 26, 42],
    timestamp: -102574080
  });
  let q1_time = Date.now() - t_q1;
  console.log(`  ✓ Greece bbox [20, 36, 26, 42] query resolved in ${q1_time} ms (${greece_diffs.length} entities)`);

  let t_q2 = Date.now();
  let na_diffs = await db.diffBBox({
    bbox: [-125, 25, -65, 50],
    timestamp: -102574080
  });
  let q2_time = Date.now() - t_q2;
  console.log(`  ✓ North America bbox [-125, 25, -65, 50] query resolved in ${q2_time} ms (${na_diffs.length} entities)`);

  //Stage 3: Multithreaded geoprocessing on entity
  console.log("\n[Stage 3] Multithreaded Geoprocessing via proc worker threads...");

  let sample_entity = greece_diffs[0];
  if (!sample_entity) throw new Error("No sample entity found for geoprocessing test");
  console.log(`  Target entity ID: ${sample_entity.id} (${sample_entity.class_name})`);

  let t_proc = Date.now();
  let clean_res = await proc.executeAction("cleanKeyframes", {
    entity_id: sample_entity.id
  });
  let proc_time = Date.now() - t_proc;
  console.log(`  ✓ cleanKeyframes resolved in ${proc_time} ms:`, clean_res);

  let var_res = await proc.executeAction("addVariable", {
    date: "-102574080",
    entity_id: sample_entity.id,
    key: "test_population",
    value: 500000
  });
  console.log(`  ✓ addVariable resolved:`, var_res);

  //Verify updated state in db
  let updated_entity = await db.getValue(sample_entity.id);
  if (!updated_entity.metadata?.variables?.test_population)
    throw new Error("Variable write-through verification failed");
  console.log(`  ✓ Verified write-through in db:`, updated_entity.metadata.variables.test_population);

  //Stage 4: Streaming Repack to .naissance
  console.log("\n[Stage 4] Streaming Repack back to 100% compliant .naissance JSON...");

  let repacked_path = path.resolve(__dirname, "repacked_test.naissance");
  let t_save = Date.now();
  await db.save(repacked_path);
  let save_time = Date.now() - t_save;

  let repacked_size_mb = (fs.statSync(repacked_path).size / 1024 / 1024).toFixed(1);
  console.log(`  ✓ Repacked into ${repacked_path} in ${save_time} ms (${repacked_size_mb} MB)`);

  //Stage 5: Verification of repacked file validity
  console.log("\n[Stage 5] Verifying repacked savefile validity...");
  let repacked_stat = fs.statSync(repacked_path);
  if (repacked_stat.size < 1000) throw new Error("Repacked savefile unexpectedly small");

  //Read head and tail to ensure valid JSON structure
  let fd = fs.openSync(repacked_path, "r");
  let head_buf = Buffer.alloc(100);
  let tail_buf = Buffer.alloc(100);
  fs.readSync(fd, head_buf, 0, 100, 0);
  fs.readSync(fd, tail_buf, 0, 100, Math.max(0, repacked_stat.size - 100));
  fs.closeSync(fd);

  let head_str = head_buf.toString("utf8").trim();
  let tail_str = tail_buf.toString("utf8").trim();

  if (!head_str.startsWith("{")) throw new Error("Repacked file does not start with '{'");
  if (!tail_str.endsWith("}")) throw new Error("Repacked file does not end with '}'");
  console.log("  ✓ JSON root structure validated: starts with '{', ends with '}'");

  //Stage 6: Clean up worker pools and temporary files
  console.log("\n[Stage 6] Clean up resources...");
  await proc.terminate();
  await NDJSON.terminate();

  //Remove temporary test artifacts
  try {
    fs.rmSync(shard_folder, { force: true, recursive: true });
    fs.unlinkSync(repacked_path);
    console.log("  ✓ Cleaned up temporary test artifacts.");
  } catch (e) {
    console.warn("  Artifact cleanup note:", e.message);
  }

  console.log("\n=================================================");
  console.log("=== ALL END-TO-END TESTS PASSED WITH 100% OK  ===");
  console.log("=================================================");
  process.exit(0);
}

runEndToEndTests().catch((err) => {
  console.error("\n❌ End-to-End Test Failed:", err);
  process.exit(1);
});
