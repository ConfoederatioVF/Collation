let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

let year_1800_ts = 1800 * 525960;
let bbox = [9.5, 49.5, 11.5, 50.8];

async function checkTouching1800() {
  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let active_features = [];
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
      let active_ts = null;
      for (let i = 0; i < tss.length; i++) {
        if (tss[i] <= year_1800_ts && (i + 1 === tss.length || year_1800_ts < tss[i+1])) {
          active_ts = tss[i];
          break;
        }
      }
      if (active_ts !== null) {
        let kf = ent.history[active_ts];
        let geom = kf ? kf[0] : null;
        if (geom && geom.coordinates && geom.coordinates.length > 0) {
          let b = turf.bbox(geom);
          if (b[0] <= bbox[2] && b[2] >= bbox[0] && b[1] <= bbox[3] && b[3] >= bbox[1]) {
            active_features.push({
              id,
              name: ent.name || kf?.[2]?.name || id,
              active_ts,
              geom,
              bbox: b
            });
          }
        }
      }
    } catch(e){}
  }

  let u = turf.feature(active_features[0].geom);
  for (let i = 1; i < active_features.length; i++) {
    try {
      let next_u = turf.union(turf.featureCollection([u, turf.feature(active_features[i].geom)]));
      if (next_u) u = next_u;
    } catch(e){}
  }

  let holes = [];
  let extractHoles = (coords) => {
    for (let r = 1; r < coords.length; r++) holes.push(coords[r]);
  };
  if (u.geometry.type === "Polygon") extractHoles(u.geometry.coordinates);
  else for (let poly of u.geometry.coordinates) extractHoles(poly);

  console.log(`Found ${holes.length} total interior rings.`);

  for (let i = 0; i < holes.length; i++) {
    let p = turf.polygon([holes[i]]);
    let a = turf.area(p) / 1e6;
    let b = turf.bbox(p);
    if (a >= 0.5 && b[0] >= 9.5 && b[2] <= 11.5 && b[1] >= 49.5 && b[3] <= 50.8) {
      let touching = [];
      for (let af of active_features) {
        if (af.bbox[0] <= b[2] + 0.05 && af.bbox[2] >= b[0] - 0.05 &&
            af.bbox[1] <= b[3] + 0.05 && af.bbox[3] >= b[1] - 0.05) {
          touching.push(`${af.id} (${af.name}, active_ts: ${af.active_ts})`);
        }
      }
      let c = [(b[0]+b[2])/2, (b[1]+b[3])/2];
      console.log(`\nHole at (${c[0].toFixed(2)}°E, ${c[1].toFixed(2)}°N), Area = ${a.toFixed(2)} km²:`);
      console.log(`  Touching: ${touching.join("; ")}`);
    }
  }
}

checkTouching1800().catch(console.error);
