let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

async function checkHolesAcrossKeyframes() {
  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  // Let's test Franconia / Central Germany across major timestamps:
  let test_years = [1356, 1463, 1500, 1548, 1648, 1707, 1787, 1800, 1803, 1806, 1815];
  let bbox = [9.5, 49.5, 11.5, 50.8]; // Franconia

  let all_entities = [];
  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    let val_str = line.slice(colon + 1).replace(/,$/, "");

    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;

      let kfs = [];
      let tss = Object.keys(ent.history).map(Number).sort((a,b)=>a-b);
      for (let i = 0; i < tss.length; i++) {
        let ts = tss[i];
        let next_ts = (i + 1 < tss.length) ? tss[i+1] : Infinity;
        let kf = ent.history[ts];
        let geom = kf ? kf[0] : null;
        if (geom && geom.coordinates && geom.coordinates.length > 0) {
          let b = turf.bbox(geom);
          if (b[0] <= bbox[2] && b[2] >= bbox[0] && b[1] <= bbox[3] && b[3] >= bbox[1]) {
            kfs.push({ ts, next_ts, geom, bbox: b });
          }
        }
      }
      if (kfs.length > 0) {
        all_entities.push({ id, name: ent.name || id, kfs });
      }
    } catch(e) {}
  }

  console.log(`Entities with geoms in Franconia bbox: ${all_entities.length}`);

  for (let year of test_years) {
    let target_ts = year * 525960;
    let active = [];
    for (let ent of all_entities) {
      for (let kf of ent.kfs) {
        if (kf.ts <= target_ts && target_ts < kf.next_ts) {
          active.push(kf);
          break;
        }
      }
    }

    if (active.length < 2) {
      console.log(`Year ${year}: only ${active.length} active entities.`);
      continue;
    }

    let u = turf.feature(active[0].geom);
    for (let i = 1; i < active.length; i++) {
      try {
        let next_u = turf.union(turf.featureCollection([u, turf.feature(active[i].geom)]));
        if (next_u) u = next_u;
      } catch(e) {}
    }

    let holes = [];
    let extractHoles = (coords) => {
      for (let r = 1; r < coords.length; r++) holes.push(coords[r]);
    };
    if (u.geometry.type === "Polygon") extractHoles(u.geometry.coordinates);
    else for (let poly of u.geometry.coordinates) extractHoles(poly);

    let inside_holes = [];
    for (let h of holes) {
      let p = turf.polygon([h]);
      let a = turf.area(p) / 1e6;
      let b = turf.bbox(p);
      if (b[0] >= 9.5 && b[2] <= 11.5 && b[1] >= 49.5 && b[3] <= 50.8) {
        inside_holes.push({ area: a, bbox: b });
      }
    }

    let small = inside_holes.filter(h => h.area <= 150.0 && h.area >= 0.001);
    console.log(`Year ${year} (${active.length} active): ${inside_holes.length} total holes, ${small.length} small holes (<= 150 km²). Max area = ${inside_holes.length > 0 ? Math.max(...inside_holes.map(h=>h.area)).toFixed(1) : 0} km²`);
  }
}

checkHolesAcrossKeyframes().catch(console.error);
