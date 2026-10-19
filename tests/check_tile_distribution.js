let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

async function checkTileTimestamps() {
  let min_lon = 0, max_lon = 30;
  let D = 2;

  let rs = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let tile_ents = new Map();

  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    let val_str = line.slice(colon + 1).replace(/,$/, "");

    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;

      for (let ts in ent.history) {
        let kf = ent.history[ts];
        let geom = kf ? kf[0] : null;
        if (geom && geom.coordinates && geom.coordinates.length > 0) {
          let b = turf.bbox(geom);
          if (b[0] <= max_lon + 0.08 && b[2] >= min_lon - 0.08) {
            let min_tx = Math.max(Math.floor(min_lon / D), Math.floor((b[0] - 0.08) / D));
            let max_tx = Math.min(Math.floor((max_lon - 0.001) / D), Math.floor((b[2] + 0.08) / D));
            let min_ty = Math.floor((b[1] - 0.08) / D);
            let max_ty = Math.floor((b[3] + 0.08) / D);

            for (let x = min_tx; x <= max_tx; x++) {
              for (let y = min_ty; y <= max_ty; y++) {
                let tkey = `${x},${y}`;
                if (!tile_ents.has(tkey)) tile_ents.set(tkey, new Set());
                tile_ents.get(tkey).add(id);
              }
            }
          }
        }
      }
    } catch(e) {}
  }

  let hist = [0, 0, 0, 0, 0]; // 2-5, 6-10, 11-25, 26-50, 50+
  let active_tiles = 0;
  for (let [k, set] of tile_ents.entries()) {
    if (set.size >= 2) {
      active_tiles++;
      if (set.size <= 5) hist[0]++;
      else if (set.size <= 10) hist[1]++;
      else if (set.size <= 25) hist[2]++;
      else if (set.size <= 50) hist[3]++;
      else hist[4]++;
    }
  }

  console.log(`Active tiles in Band 6: ${active_tiles}`);
  console.log(`2-5 entities: ${hist[0]}`);
  console.log(`6-10 entities: ${hist[1]}`);
  console.log(`11-25 entities: ${hist[2]}`);
  console.log(`26-50 entities: ${hist[3]}`);
  console.log(`50+ entities: ${hist[4]}`);
}

checkTileTimestamps().catch(console.error);
