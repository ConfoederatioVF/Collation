let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

let bbox = [5.5, 47.0, 15.0, 55.0]; // Entire Germany / Holy Roman Empire
let start_ts = 1648 * 525960;
let end_ts = 1815 * 525960;

async function checkHRETimestamps() {
  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let ts_set = new Set();
  let kf_count = 0;

  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let val_str = line.slice(colon + 1).replace(/,$/, "");

    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;

      for (let ts in ent.history) {
        let n = Number(ts);
        if (n >= start_ts && n <= end_ts) {
          let kf = ent.history[ts];
          let geom = kf ? kf[0] : null;
          if (geom && geom.coordinates && geom.coordinates.length > 0) {
            let b = turf.bbox(geom);
            if (b[0] <= bbox[2] && b[2] >= bbox[0] && b[1] <= bbox[3] && b[3] >= bbox[1]) {
              ts_set.add(n);
              kf_count++;
            }
          }
        }
      }
    } catch(e) {}
  }

  let sorted_ts = Array.from(ts_set).sort((a,b)=>a-b);
  console.log(`HRE (1648-1815): ${kf_count} keyframes across ${sorted_ts.length} timestamps.`);
  let years = new Set(sorted_ts.map(t => Math.round(t / 525960)));
  console.log(`Unique years in HRE (1648-1815): ${years.size}`);
}

checkHRETimestamps().catch(console.error);
