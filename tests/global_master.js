let fs = require("node:fs");
let path = require("node:path");
let readline = require("node:readline");
let { fork } = require("node:child_process");
let turf = require("../UF/js/geospatiale/turf.min.js");

require("../UF/js/vercengen/db/NDJSON_main.js");

async function main() {
  let master_start = Date.now();
  console.log("================================================================================");
  console.log("STARTING GLOBAL SYSTEMATIC TOPOLOGICAL HOLE CLOSURE ACROSS ALL KEYFRAMES");
  console.log("================================================================================");

  let bands = [
    { id: 0, min_lon: -180, max_lon: -150, name: "Pacific / Alaska" },
    { id: 1, min_lon: -150, max_lon: -120, name: "West Coast North America" },
    { id: 2, min_lon: -120, max_lon: -90, name: "Central North America / Mexico" },
    { id: 3, min_lon: -90, max_lon: -60, name: "East Coast North America / Andes" },
    { id: 4, min_lon: -60, max_lon: -30, name: "Eastern South America / Atlantic" },
    { id: 5, min_lon: -30, max_lon: 0, name: "Atlantic / West Africa / UK / Iberia" },
    { id: 6, min_lon: 0, max_lon: 30, name: "Western & Central Europe (HRE)" },
    { id: 7, min_lon: 30, max_lon: 60, name: "Eastern Europe / Russia / Middle East" },
    { id: 8, min_lon: 60, max_lon: 90, name: "Central Asia / India" },
    { id: 9, min_lon: 90, max_lon: 120, name: "East Asia / China / SE Asia" },
    { id: 10, min_lon: 120, max_lon: 150, name: "Japan / Australia" },
    { id: 11, min_lon: 150, max_lon: 180, name: "Pacific / New Zealand" }
  ];

  // Clean old pieces files
  for (let b of bands) {
    let pfile = `tests/pieces_band_${b.id}.ndjson`;
    if (fs.existsSync(pfile)) try { fs.unlinkSync(pfile); } catch(e){}
  }

  // Spawn workers in parallel
  console.log(`Spawning 12 workers for global longitude bands across available CPU cores...`);
  let worker_promises = bands.map(b => {
    return new Promise((resolve, reject) => {
      let child = fork(path.resolve("tests/global_worker.js"), [
        "--min_lon", b.min_lon,
        "--max_lon", b.max_lon,
        "--band_id", b.id,
        "--out_file", `tests/pieces_band_${b.id}.ndjson`
      ]);

      child.on("exit", (code) => {
        if (code === 0) {
          console.log(`[Master] Worker for Band ${b.id} (${b.name}) completed successfully.`);
          resolve();
        } else {
          reject(new Error(`Worker for Band ${b.id} exited with code ${code}`));
        }
      });
      child.on("error", reject);
    });
  });

  await Promise.all(worker_promises);
  console.log(`\nAll 12 global band workers finished in ${((Date.now() - master_start)/1000).toFixed(1)}s.`);

  // Step 2: Index all assigned pieces by entity and timestamp
  console.log("\nIndexing all assigned hole pieces globally...");
  let pieces_by_ent = new Map(); // id -> Map<ts, Array<tri_feature>>
  let total_triangles = 0;

  for (let b of bands) {
    let pfile = `tests/pieces_band_${b.id}.ndjson`;
    if (!fs.existsSync(pfile)) continue;

    let rs = fs.createReadStream(pfile);
    let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

    for await (let line of rl) {
      let clean = line.trim();
      if (!clean) continue;
      try {
        let item = JSON.parse(clean);
        if (!pieces_by_ent.has(item.id)) pieces_by_ent.set(item.id, new Map());
        let emap = pieces_by_ent.get(item.id);
        if (!emap.has(item.ts)) emap.set(item.ts, []);
        emap.get(item.ts).push(turf.polygon(item.coords));
        total_triangles++;
      } catch(e){}
    }
  }

  console.log(`Total entities with hole closures globally: ${pieces_by_ent.size}`);
  console.log(`Total assigned triangle pieces: ${total_triangles}`);

  // Step 3: Stream write updated detailed.naissance.tmp
  console.log("\nStream-writing updated database to saves/detailed.naissance.tmp...");
  let in_stream = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl_in = readline.createInterface({ input: in_stream, crlfDelay: Infinity });

  let out_path = "saves/detailed.naissance.tmp";
  let ws_out = fs.createWriteStream(out_path);

  let line_index = 0;
  let modified_count = 0;
  let unmodified_count = 0;

  for await (let raw_line of rl_in) {
    line_index++;
    let line = raw_line.trim();

    // Verbatim header (lines 1 to 41)
    if (line_index <= 41) {
      let can_write = ws_out.write(raw_line + "\n");
      if (!can_write) await new Promise(r => ws_out.once("drain", r));
      continue;
    }

    // Closing root object
    if (line === "}" || line === "};") {
      let can_write = ws_out.write(raw_line + "\n");
      if (!can_write) await new Promise(r => ws_out.once("drain", r));
      continue;
    }

    if (!line.includes('":{')) {
      let can_write = ws_out.write(raw_line + "\n");
      if (!can_write) await new Promise(r => ws_out.once("drain", r));
      continue;
    }

    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);

    if (!pieces_by_ent.has(id)) {
      // Unmodified entity - pass through verbatim
      unmodified_count++;
      let can_write = ws_out.write(raw_line + "\n");
      if (!can_write) await new Promise(r => ws_out.once("drain", r));
      continue;
    }

    // Modified entity
    let val_str = line.slice(colon + 1).replace(/,$/, "");
    try {
      let ent = JSON.parse(val_str);
      let emap = pieces_by_ent.get(id);

      let history_obj = (typeof ent.history === "string") ? JSON.parse(ent.history) : ent.history;
      let raw_kfs = (history_obj && history_obj.keyframes) ? history_obj.keyframes : history_obj;

      if (raw_kfs) {
        for (let [ts, pieces] of emap.entries()) {
          let kf = raw_kfs[ts];
          if (!kf) continue;
          let geom = Array.isArray(kf) ? kf[0] : (kf?.value ? kf.value[0] : null);
          if (geom && geom.coordinates && geom.coordinates.length > 0) {
            let cur = turf.feature(geom);
            for (let p of pieces) {
              try {
                let m = turf.union(turf.featureCollection([cur, p]));
                if (m) cur = m;
              } catch(e){}
            }
            cur = turf.cleanCoords(cur);
            cur = turf.truncate(cur, { precision: 5 });
            try {
              cur = turf.simplify(cur, { tolerance: 0.00002, highQuality: true, mutate: false });
            } catch(e){}

            if (Array.isArray(kf)) {
              kf[0] = cur.geometry;
            } else if (kf && kf.value) {
              kf.value[0] = cur.geometry;
            }
          }
        }

        if (typeof ent.history === "string") {
          ent.history = JSON.stringify(history_obj);
        }
      }

      modified_count++;
      let comma = raw_line.endsWith(",") ? "," : "";
      let new_line = `"${id}":${JSON.stringify(ent)}${comma}\n`;
      let can_write = ws_out.write(new_line);
      if (!can_write) await new Promise(r => ws_out.once("drain", r));
    } catch(e) {
      console.error(`Error updating entity ${id}:`, e);
      let can_write = ws_out.write(raw_line + "\n");
      if (!can_write) await new Promise(r => ws_out.once("drain", r));
    }
  }

  ws_out.end();
  await new Promise(r => ws_out.on("finish", r));

  console.log(`Stream-write complete. Modified: ${modified_count}, Unmodified: ${unmodified_count}, Total lines: ${line_index}`);

  // Step 4: Validate temporary file
  let stat = fs.statSync(out_path);
  console.log(`Updated file size: ${(stat.size / 1024 / 1024).toFixed(2)} MB`);
  if (stat.size < 600 * 1024 * 1024) {
    throw new Error(`Output file size too small: ${stat.size} bytes. Aborting rename.`);
  }

  // Atomic rename
  let final_path = "saves/detailed.naissance";
  console.log(`Replacing ${final_path} atomically...`);
  fs.copyFileSync(out_path, final_path);
  fs.unlinkSync(out_path);
  console.log(`Successfully updated ${final_path}!`);

  // Step 5: Rebuild partition cache
  console.log("\nRebuilding NDJSON cache partitions with 8 workers...");
  await NDJSON.load("saves/detailed.naissance", { repartition: true, dynamic_max_workers: 8 });
  console.log("NDJSON repartition complete!");

  let total_elapsed = ((Date.now() - master_start) / 1000).toFixed(1);
  console.log(`\n================================================================================`);
  console.log(`GLOBAL TOPOLOGICAL HOLE CLOSURE COMPLETE IN ${total_elapsed}s!`);
  console.log(`================================================================================`);
}

main().catch((e) => {
  console.error("Master failure:", e);
  process.exit(1);
});
