let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

async function checkAllCandidateTiles() {
  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let D = 2;
  let tile_ents = new Map(); // key -> Set of entity IDs

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
        if (kf && kf[0] && kf[0].coordinates && kf[0].coordinates.length > 0) {
          let b = turf.bbox(kf[0]);
          if (b[2] - b[0] > 15 || b[3] - b[1] > 15) continue;
          let min_tx = Math.floor(b[0] / D);
          let max_tx = Math.floor(b[2] / D);
          let min_ty = Math.floor(b[1] / D);
          let max_ty = Math.floor(b[3] / D);
          for (let x = min_tx; x <= max_tx; x++) {
            for (let y = min_ty; y <= max_ty; y++) {
              let key = `${x},${y}`;
              if (!tile_ents.has(key)) tile_ents.set(key, new Set());
              tile_ents.get(key).add(id);
            }
          }
        }
      }
    } catch(e){}
  }

  let multi_tiles = [];
  for (let [k, set] of tile_ents.entries()) {
    if (set.size >= 2) multi_tiles.push({ key: k, count: set.size });
  }

  console.log(`Total 2-degree tiles with 2+ entities across history: ${multi_tiles.length}`);
}

checkAllCandidateTiles().catch(console.error);
