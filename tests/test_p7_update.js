let path = require("node:path");
require("../UF/js/vercengen/db/NDJSON_main.js");

async function testUpdate() {
  let pool = NDJSON.getWorkerPool(8);
  console.log("Loading partition 7...");
  await NDJSON.task(7, {
    type: "init_partition",
    file_path: path.resolve("saves/detailed.naissance")
  });
  console.log("Calling set_values on Worker 7 for key 6318 (Romania)...");
  try {
    let res = await NDJSON.task(7, {
      type: "set_values",
      file_path: path.resolve("saves/detailed.naissance"),
      update_map: {
        "6318": {
          id: "6318",
          class_name: "GeometryPolygon",
          name: "Romania"
        }
      }
    });
    console.log("set_values result:", res);
  } catch (err) {
    console.error("set_values failed:", err);
  }
  await NDJSON.terminate();
}

testUpdate().catch(console.error);
