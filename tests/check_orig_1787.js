let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

let bbox = [9.5, 49.5, 11.5, 50.8];
let target_ts = 939872160; // 1787 AD

async function check1787HolesWith150() {
  let rs = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let active = [];
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
        if (tss[i] <= target_ts && (i + 1 === tss.length || target_ts < tss[i+1])) {
          active_ts = tss[i];
          break;
        }
      }
      if (active_ts !== null) {
        let kf = ent.history[active_ts];
        if (kf && kf[0] && kf[0].coordinates && kf[0].coordinates.length > 0) {
          let b = turf.bbox(kf[0]);
          if (b[0] <= bbox[2] && b[2] >= bbox[0] && b[1] <= bbox[3] && b[3] >= bbox[1]) {
            active.push({ id, name: ent.name || id, geom: kf[0], b });
          }
        }
      }
    } catch(e){}
  }

  console.log(`Original 1787 active entities: ${active.length}`);
  let u = turf.feature(active[0].geom);
  for (let i = 1; i < active.length; i++) {
    try {
      let nu = turf.union(turf.featureCollection([u, turf.feature(active[i].geom)]));
      if (nu) u = nu;
    } catch(e){}
  }

  let holes = [];
  let extract = (c) => { for (let r = 1; r < c.length; r++) holes.push(c[r]); };
  if (u.geometry.type === "Polygon") extract(u.geometry.coordinates);
  else for (let poly of u.geometry.coordinates) extract(poly);

  console.log(`Total interior holes: ${holes.length}`);
  let inside = [];
  for (let h of holes) {
    let p = turf.polygon([h]);
    let a = turf.area(p) / 1e6;
    let b = turf.bbox(p);
    if (b[0] >= 9.5 && b[2] <= 11.5 && b[1] >= 49.5 && b[3] <= 50.8) {
      inside.push({ a, b });
    }
  }

  inside.sort((a,b) => b.a - a.a);
  console.log(`Holes inside Franconia bbox: ${inside.length}`);
  for (let h of inside) {
    let c = [(h.b[0]+h.b[2])/2, (h.b[1]+h.b[3])/2];
    console.log(`  Area: ${h.a.toFixed(3).padStart(7)} km² | Center: (${c[0].toFixed(2)}°E, ${c[1].toFixed(2)}°N)`);
  }
}

check1787HolesWith150().catch(console.error);
