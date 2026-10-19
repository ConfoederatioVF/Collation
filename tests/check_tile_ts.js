let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

let tile_bbox = [10, 50, 12, 52];

async function checkTileTimestamps() {
  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let tile_ents = [];
  let ts_set = new Set();

  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    let val_str = line.slice(colon + 1).replace(/,$/, "");

    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;

      let touches_tile = false;
      let kfs = [];
      for (let ts in ent.history) {
        let kf = ent.history[ts];
        let geom = kf ? kf[0] : null;
        if (geom && geom.coordinates && geom.coordinates.length > 0) {
          let b = turf.bbox(geom);
          if (b[0] <= tile_bbox[2] && b[2] >= tile_bbox[0] && b[1] <= tile_bbox[3] && b[3] >= tile_bbox[1]) {
            touches_tile = true;
            ts_set.add(Number(ts));
            kfs.push({ ts: Number(ts), geom, b });
          }
        }
      }

      if (touches_tile) {
        tile_ents.push({ id, name: ent.name || id, kfs });
      }
    } catch(e) {}
  }

  console.log(`Entities touching tile [10..12, 50..52]: ${tile_ents.length}`);
  console.log(`Unique timestamps touching this tile: ${ts_set.size}`);
  
  let sorted_ts = Array.from(ts_set).sort((a,b)=>a-b);
  let years = sorted_ts.map(t => Math.round(t / 525960));
  let unique_years = Array.from(new Set(years)).sort((a,b)=>a-b);
  console.log(`Unique years touching this tile: ${unique_years.length}`);
  console.log(`Years sample: [${unique_years.slice(0, 30).join(", ")} ... ${unique_years.slice(-10).join(", ")}]`);
}

checkTileTimestamps().catch(console.error);
