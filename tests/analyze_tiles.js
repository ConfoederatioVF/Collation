let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

async function analyzeTiles() {
  let rs = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let D = 2; // 2x2 degree tiles
  // For each tile, store list of { id, start_ts, end_ts, bbox }
  let tile_spans = new Map();

  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    let val_str = line.slice(colon + 1).replace(/,$/, "");
    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;

      let tss = Object.keys(ent.history).map(Number).sort((a,b)=>a-b);
      for (let i = 0; i < tss.length; i++) {
        let ts = tss[i];
        let next_ts = (i + 1 < tss.length) ? tss[i+1] : Infinity;
        let kf = ent.history[ts];
        let geom = kf ? kf[0] : null;
        if (!geom || !geom.coordinates || geom.coordinates.length === 0) continue;

        let b = turf.bbox(geom);
        // Skip world-spanning geoms if any
        if (b[2] - b[0] > 60 || b[3] - b[1] > 60) continue;

        let min_tx = Math.floor(b[0] / D);
        let max_tx = Math.floor(b[2] / D);
        let min_ty = Math.floor(b[1] / D);
        let max_ty = Math.floor(b[3] / D);

        for (let x = min_tx; x <= max_tx; x++) {
          for (let y = min_ty; y <= max_ty; y++) {
            let key = `${x},${y}`;
            if (!tile_spans.has(key)) tile_spans.set(key, []);
            tile_spans.get(key).push({ id, ts, next_ts, b });
          }
        }
      }
    } catch(e){}
  }

  console.log(`Total tiles touched: ${tile_spans.size}`);

  // Now, for each tile, how many unique entities ever touch it?
  // And if >= 2 entities touch it, do their time spans ever overlap?
  let tiles_with_overlap = 0;
  let total_overlapping_intervals = 0;

  for (let [key, spans] of tile_spans.entries()) {
    let ent_ids = new Set(spans.map(s => s.id));
    if (ent_ids.size < 2) continue; // Only 1 entity ever in this tile -> no gaps between entities possible

    // Collect all unique event timestamps where an entity in this tile starts or ends
    let events = new Set();
    for (let s of spans) {
      events.add(s.ts);
    }
    let sorted_events = Array.from(events).sort((a,b)=>a-b);

    // Count how many intervals have >= 2 active entities
    let active_intervals = 0;
    for (let i = 0; i < sorted_events.length; i++) {
      let t = sorted_events[i];
      let active_ents = new Set();
      for (let s of spans) {
        if (s.ts <= t && t < s.next_ts) {
          active_ents.add(s.id);
        }
      }
      if (active_ents.size >= 2) {
        active_intervals++;
      }
    }

    if (active_intervals > 0) {
      tiles_with_overlap++;
      total_overlapping_intervals += active_intervals;
    }
  }

  console.log(`Tiles with overlapping active entities: ${tiles_with_overlap}`);
  console.log(`Total overlapping intervals: ${total_overlapping_intervals}`);
}

analyzeTiles().catch(console.error);
