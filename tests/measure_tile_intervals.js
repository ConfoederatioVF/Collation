let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

async function measure() {
  let rs = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let D = 2;
  let tile_events = new Map(); // tile_key -> Set of timestamps

  let total_kfs = 0;
  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let val_str = line.slice(colon + 1).replace(/,$/, "");
    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;
      for (let ts in ent.history) {
        let kf = ent.history[ts];
        if (kf && kf[0] && kf[0].coordinates && kf[0].coordinates.length > 0) {
          total_kfs++;
          let b = turf.bbox(kf[0]);
          if (b[2] - b[0] > 15 || b[3] - b[1] > 15) continue;
          let min_tx = Math.floor(b[0] / D);
          let max_tx = Math.floor(b[2] / D);
          let min_ty = Math.floor(b[1] / D);
          let max_ty = Math.floor(b[3] / D);
          let n_ts = Number(ts);
          for (let x = min_tx; x <= max_tx; x++) {
            for (let y = min_ty; y <= max_ty; y++) {
              let key = `${x},${y}`;
              if (!tile_events.has(key)) tile_events.set(key, new Set());
              tile_events.get(key).add(n_ts);
            }
          }
        }
      }
    } catch(e){}
  }

  let total_intervals = 0;
  let tiles_with_multi = 0;
  for (let [k, set] of tile_events.entries()) {
    if (set.size >= 2) {
      tiles_with_multi++;
      total_intervals += set.size;
    }
  }

  console.log(`Total keyframes with geometry: ${total_kfs}`);
  console.log(`Tiles with 2+ events: ${tiles_with_multi}`);
  console.log(`Average events per active tile: ${(total_intervals / tiles_with_multi).toFixed(1)}`);
  console.log(`Total tile-interval evaluations needed globally: ${total_intervals}`);
}

measure().catch(console.error);
