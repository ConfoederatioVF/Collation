//Import libraries
let path = require("node:path");

//Set up environment
require("../core/db/db.js");
require("../core/process/workers/process_main.js");
require("../core/process/proc.js");

async function runTests () {
  console.log("=== Starting proc Engine Tests ===");

  let test_poly1 = {
    type: "Polygon",
    coordinates: [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]]
  };
  let test_poly2 = {
    type: "Polygon",
    coordinates: [[[5, 0], [5, 10], [15, 10], [15, 0], [5, 0]]]
  };

  //1. Test local spatial actions directly
  console.log("\n[1] Testing direct spatial actions...");

  let union_res = await proc.actions.union({ geometry_a: test_poly1, geometry_b: test_poly2 });
  if (!union_res.success || !union_res.geometry) throw new Error("Union failed");
  console.log("  ✓ Union action succeeded:", union_res.geometry.type);

  let diff_res = await proc.actions.difference({ geometry_a: test_poly1, geometry_b: test_poly2 });
  if (!diff_res.success || !diff_res.geometry) throw new Error("Difference failed");
  console.log("  ✓ Difference action succeeded:", diff_res.geometry.type);

  let inter_res = await proc.actions.intersect({ geometry_a: test_poly1, geometry_b: test_poly2 });
  if (!inter_res.success || !inter_res.geometry) throw new Error("Intersect failed");
  console.log("  ✓ Intersect action succeeded:", inter_res.geometry.type);

  let buf_res = await proc.actions.buffer({ distance: 5, geometry: test_poly1 });
  if (!buf_res.success || !buf_res.geometry) throw new Error("Buffer failed");
  console.log("  ✓ Buffer action succeeded:", buf_res.geometry.type);

  let simp_res = await proc.actions.simplifyPolygon({ geometry: buf_res.geometry, tolerance: 0.1 });
  if (!simp_res.success || !simp_res.geometry) throw new Error("Simplify failed");
  console.log("  ✓ Simplify action succeeded:", simp_res.geometry.type);

  //2. Test multithreaded worker execution via proc.executeAction -> proc.IPC_task
  console.log("\n[2] Testing multithreaded worker execution...");
  let start_time = Date.now();

  let worker_union = await proc.executeAction("union", {
    geometry_a: test_poly1,
    geometry_b: test_poly2
  });
  if (!worker_union.success || !worker_union.geometry) throw new Error("Multithreaded union failed");
  console.log("  ✓ Multithreaded Union dispatched and resolved in:", Date.now() - start_time, "ms");

  let worker_buf = await proc.executeAction("buffer", {
    distance: 10,
    geometry: test_poly1
  });
  if (!worker_buf.success || !worker_buf.geometry) throw new Error("Multithreaded buffer failed");
  console.log("  ✓ Multithreaded Buffer resolved:", worker_buf.geometry.type);

  //3. Test RAM diagnostics across all workers
  console.log("\n[3] Testing worker diagnostics...");
  let diagnostics = await proc.IPC_getDiagnostics();
  if (!Array.isArray(diagnostics) || diagnostics.length === 0) throw new Error("Diagnostics failed");
  console.log(`  ✓ Retrieved diagnostics from ${diagnostics.length} workers:`);
  for (let i = 0; i < diagnostics.length; i++) {
    console.log(`    Worker ${diagnostics[i].worker_id}: RSS ${(diagnostics[i].rss / 1024 / 1024).toFixed(1)}MB, Heap ${(diagnostics[i].heapUsed / 1024 / 1024).toFixed(1)}MB (${diagnostics[i].percentage}%)`);
  }

  //4. Clean up worker pool
  console.log("\n[4] Terminating worker pool...");
  await proc.terminate();
  console.log("  ✓ Worker pool terminated cleanly.");

  console.log("\n=== All proc Engine Tests Passed Successfully ===");
  process.exit(0);
}

runTests().catch((err) => {
  console.error("Test failed with error:", err);
  process.exit(1);
});
