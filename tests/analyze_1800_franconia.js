let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

let bbox = [9.5, 49.5, 11.5, 50.8]; // Franconia screenshot bbox
let year_1800_ts = 1800 * 525960; // 946728000

async function analyze1800Franconia() {
  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let active_ents = [];

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
            let name = ent.name || kf?.[2]?.name || id;
            active_ents.push({
              id,
              name,
              active_ts,
              geom,
              bbox: b
            });
          }
        }
      }
    } catch(e) {}
  }

  console.log(`Active entities in Franconia at 1800 AD: ${active_ents.length}`);
  for (let e of active_ents) {
    console.log(`  Entity ${e.id.padStart(4)}: "${e.name}" (active_ts: ${e.active_ts})`);
  }

  // Union
  console.log("Computing coverage union of active entities at 1800 AD...");
  let u = turf.feature(active_ents[0].geom);
  for (let i = 1; i < active_ents.length; i++) {
    try {
      let next_u = turf.union(turf.featureCollection([u, turf.feature(active_ents[i].geom)]));
      if (next_u) u = next_u;
    } catch(e) {}
  }

  let holes = [];
  let extractHoles = (coords) => {
    for (let r = 1; r < coords.length; r++) holes.push(coords[r]);
  };
  if (u.geometry.type === "Polygon") extractHoles(u.geometry.coordinates);
  else for (let poly of u.geometry.coordinates) extractHoles(poly);

  console.log(`Total interior holes in union at 1800 AD: ${holes.length}`);

  let small_holes = [];
  for (let i = 0; i < holes.length; i++) {
    let p = turf.polygon([holes[i]]);
    let a = turf.area(p) / 1e6;
    let b = turf.bbox(p);
    if (b[0] >= 9.5 && b[2] <= 11.5 && b[1] >= 49.5 && b[3] <= 50.8) {
      small_holes.push({ index: i, area: a, bbox: b, coords: holes[i] });
    }
  }

  console.log(`Holes inside target region at 1800 AD: ${small_holes.length}`);
  small_holes.sort((a,b) => b.area - a.area);
  for (let h of small_holes.slice(0, 20)) {
    let center = [(h.bbox[0]+h.bbox[2])/2, (h.bbox[1]+h.bbox[3])/2];
    console.log(`  Hole ${h.index}: Area = ${h.area.toFixed(3)} km², center = (${center[0].toFixed(2)}°E, ${center[1].toFixed(2)}°N)`);
  }
}

analyze1800Franconia().catch(console.error);
