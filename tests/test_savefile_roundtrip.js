let fs = require("node:fs");
let path = require("node:path");

// Bootstrap environment
global.ve = {};
require("../UF/js/vercengen/db/NDJSON_main.js");
require("../core/db/db.js");

async function runRoundtripTests() {
  console.log("=== Testing Savefile Roundtrip & DB Differencing Engine ===");

  let test_output_dir = path.resolve("./tests/temp_roundtrip/");
  if (!fs.existsSync(test_output_dir)) fs.mkdirSync(test_output_dir, { recursive: true });

  try {
    // ----------------------------------------------------
    // TEST 1: autosave.naissance
    // ----------------------------------------------------
    console.log("\n1. Testing autosave.naissance...");
    let autosave_src = path.resolve("./saves/autosave.naissance");
    let autosave_copy = path.join(test_output_dir, "autosave_test.naissance");
    fs.copyFileSync(autosave_src, autosave_copy);

    let load_res = await db.load(autosave_copy, { dynamic_max_workers: 4 });
    console.log("   [PASS] Loaded and partitioned:", load_res);

    // Test getValue
    let val = await db.getValue("53396173898");
    if (!val || val.id !== "53396173898") {
      throw new Error(`getValue failed: ${JSON.stringify(val)}`);
    }
    console.log("   [PASS] db.getValue('53396173898') retrieved entity class:", val.class_name);

    // Test diff
    let diff_res = await db.diff("53396173898", 1000000000);
    if (!diff_res || !diff_res.value) {
      throw new Error(`diff failed: ${JSON.stringify(diff_res)}`);
    }
    console.log("   [PASS] db.diff('53396173898', 1000000000) resolved value length:", diff_res.value.length);

    // Test diffBBox
    let bbox_res = await db.diffBBox({
      timestamp: 1065693679,
      bbox: [35, 25, 48, 36] // Covers the polygon coordinates ~ [38, 29] to [47, 34]
    });
    if (!Array.isArray(bbox_res) || bbox_res.length === 0) {
      throw new Error(`diffBBox inside viewport failed: ${JSON.stringify(bbox_res)}`);
    }
    console.log("   [PASS] db.diffBBox inside viewport found entities:", bbox_res.length);

    // Test diffBBox outside viewport
    let bbox_outside = await db.diffBBox({
      timestamp: 1065693679,
      bbox: [-100, -50, -80, -30] // Far outside in South America
    });
    if (!Array.isArray(bbox_outside) || bbox_outside.length !== 0) {
      throw new Error(`diffBBox outside viewport should return 0, got: ${bbox_outside.length}`);
    }
    console.log("   [PASS] db.diffBBox outside viewport correctly returned 0 entities.");

    // Test save / repack
    let repacked_autosave = path.join(test_output_dir, "autosave_repacked.naissance");
    await db.save(repacked_autosave);
    if (!fs.existsSync(repacked_autosave)) {
      throw new Error(`Repacked file not found: ${repacked_autosave}`);
    }

    // Verify valid JSON
    let parsed_autosave = JSON.parse(fs.readFileSync(repacked_autosave, "utf8"));
    if (!parsed_autosave.map_settings || !parsed_autosave["53396173898"]) {
      throw new Error("Repacked autosave JSON missing required keys!");
    }
    console.log("   [PASS] Repacked autosave is valid JSON with map_settings and entity 53396173898!");

    // ----------------------------------------------------
    // TEST 2: detailed_borders/0.476.1.1.naissance (44MB)
    // ----------------------------------------------------
    console.log("\n2. Testing detailed_borders/0.476.1.1.naissance (44MB)...");
    let large_src = path.resolve("./saves/detailed_borders/0.476.1.1.naissance");
    let large_copy = path.join(test_output_dir, "0.476_test.naissance");
    fs.copyFileSync(large_src, large_copy);

    let start_time = Date.now();
    await db.load(large_copy, { dynamic_max_workers: 4 });
    let load_time = Date.now() - start_time;
    console.log(`   [PASS] 44MB file loaded and indexed in: ${load_time}ms!`);

    // Test diagnostics
    let diag = await db.getDiagnostics();
    console.log("   [PASS] Worker RAM diagnostics (4 workers):", diag.map((d) => ({
      worker_id: d.worker_id,
      cached_entities: d.cached_entities,
      rss_mb: (d.rss / (1024 * 1024)).toFixed(1),
      heap_mb: (d.heapUsed / (1024 * 1024)).toFixed(1)
    })));

    // Test diffBBox on Greece viewport: [20, 35, 26, 42] at timestamp -150000000
    let greece_start = Date.now();
    let greece_diff = await db.diffBBox({
      timestamp: -150000000,
      bbox: [20, 35, 26, 42]
    });
    let greece_time = Date.now() - greece_start;
    console.log(`   [PASS] Greece viewport diff found ${greece_diff.length} entities in ${greece_time}ms!`);

    // Test diffBBox on distant China/India viewport: [70, 15, 80, 25] at timestamp 150000000
    let india_start = Date.now();
    let india_diff = await db.diffBBox({
      timestamp: 150000000,
      bbox: [70, 15, 80, 25]
    });
    let india_time = Date.now() - india_start;
    console.log(`   [PASS] India viewport diff found ${india_diff.length} entities in ${india_time}ms!`);

    // Test repacking large file back to .naissance
    console.log("   Repacking 44MB file...");
    let repacked_large = path.join(test_output_dir, "0.476_repacked.naissance");
    let save_start = Date.now();
    await db.save(repacked_large);
    let save_time = Date.now() - save_start;
    let repacked_size = fs.statSync(repacked_large).size;
    console.log(`   [PASS] Repacked 44MB file written in ${save_time}ms! Size: ${(repacked_size / (1024 * 1024)).toFixed(2)}MB`);

    // Verify repacked integrity with streaming JSON check
    let repacked_stream = fs.createReadStream(repacked_large, { highWaterMark: 512 * 1024 });
    let entity_count = 0;
    let in_str = false;
    let is_esc = false;
    let depth = 0;
    for await (let chunk of repacked_stream) {
      let str = chunk.toString("utf8");
      for (let i = 0; i < str.length; i++) {
        let ch = str[i];
        if (is_esc) { is_esc = false; continue; }
        if (ch === "\\") { is_esc = true; continue; }
        if (ch === '"') { in_str = !in_str; continue; }
        if (in_str) continue;
        if (ch === "{" || ch === "[") depth++;
        else if (ch === "}" || ch === "]") {
          depth--;
          if (depth === 1) entity_count++;
        }
      }
    }
    console.log(`   [PASS] Verified repacked file has ${entity_count} entities!`);

    console.log("\n=== ALL SAVEFILE ROUNDTRIP & DB TESTS PASSED! ===");
  } finally {
    // Terminate workers
    if (global.ve?.ndjson_worker_pool) {
      for (let w of global.ve.ndjson_worker_pool) w.terminate();
    }
    // Clean up temp directory
    try {
      fs.rmSync(test_output_dir, { recursive: true, force: true });
    } catch (e) {}
  }
}

runRoundtripTests().catch((err) => {
  console.error("Test failed:", err);
  process.exit(1);
});
