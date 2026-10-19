let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

let target_ids = ["95", "8", "804", "801", "35", "173", "300"];
let year_1800_ts = 1800 * 525960; // 946728000

async function check() {
  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let ents = new Map();
  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    if (!target_ids.includes(id)) continue;

    let ent = JSON.parse(line.slice(colon + 1).replace(/,$/, ""));
    ents.set(id, ent);
  }

  console.log(`Loaded ${ents.size} entities.`);

  for (let [id, ent] of ents.entries()) {
    console.log(`\nEntity ${id}:`);
    let tss = Object.keys(ent.history).map(Number).sort((a,b)=>a-b);
    let active_ts_1787 = null;
    let active_ts_1800 = null;

    let target_ts_1787 = 939872160;
    for (let i = 0; i < tss.length; i++) {
      if (tss[i] <= target_ts_1787 && (i + 1 === tss.length || target_ts_1787 < tss[i+1])) {
        active_ts_1787 = tss[i];
      }
      if (tss[i] <= year_1800_ts && (i + 1 === tss.length || year_1800_ts < tss[i+1])) {
        active_ts_1800 = tss[i];
      }
    }

    console.log(`  Active ts at 1787 AD: ${active_ts_1787} (Year ${Math.round(active_ts_1787/525960)})`);
    console.log(`  Active ts at 1800 AD: ${active_ts_1800} (Year ${Math.round(active_ts_1800/525960)})`);

    let kf_1800 = ent.history[active_ts_1800];
    let geom_1800 = kf_1800 ? kf_1800[0] : null;
    if (geom_1800 && geom_1800.coordinates) {
      let b = turf.bbox(geom_1800);
      let v = 0;
      let poly_list = (geom_1800.type === "Polygon") ? [geom_1800.coordinates] : geom_1800.coordinates;
      for (let poly of poly_list) for (let r of poly) v += r.length;
      console.log(`  Geom at 1800: ${geom_1800.type}, ${v} vertices, bbox = [${b.map(x=>x.toFixed(2)).join(", ")}]`);
    } else {
      console.log(`  Geom at 1800: null/none`);
    }
  }
}

check().catch(console.error);
