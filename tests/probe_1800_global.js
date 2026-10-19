let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

async function probe1800Global() {
  let target_ts = 1800 * 525960; // 946728000
  let max_hole_area_km2 = 150.0;
  let D = 2;

  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let active_meta = new Map();
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
        let geom = kf ? kf[0] : null;
        if (geom && geom.coordinates && geom.coordinates.length > 0) {
          active_meta.set(id, { id, active_ts, bbox: turf.bbox(geom), geom });
        }
      }
    } catch(e){}
  }

  console.log(`Active entities at 1800 AD: ${active_meta.size}`);

  let tile_map = new Map();
  for (let [id, meta] of active_meta.entries()) {
    let b = meta.bbox;
    if (b[2] - b[0] > 15 || b[3] - b[1] > 15) continue;
    let min_tx = Math.floor(b[0] / D);
    let max_tx = Math.floor(b[2] / D);
    let min_ty = Math.floor(b[1] / D);
    let max_ty = Math.floor(b[3] / D);
    for (let x = min_tx; x <= max_tx; x++) {
      for (let y = min_ty; y <= max_ty; y++) {
        let key = `${x},${y}`;
        if (!tile_map.has(key)) tile_map.set(key, []);
        tile_map.get(key).push(meta);
      }
    }
  }

  let total_holes = 0;
  let tiles_with_holes = 0;

  for (let [key, ents] of tile_map.entries()) {
    if (ents.length < 2) continue;
    let [tx, ty] = key.split(",").map(Number);
    let tile_poly = turf.bboxPolygon([tx*D, ty*D, (tx+1)*D, (ty+1)*D]);

    let clipped = [];
    for (let e of ents) {
      try {
        let c = turf.intersect(turf.featureCollection([turf.feature(e.geom), tile_poly]));
        if (c && c.geometry && c.geometry.coordinates && c.geometry.coordinates.length > 0) clipped.push(c);
      } catch(e){}
    }
    if (clipped.length < 2) continue;

    let u = clipped[0];
    for (let i = 1; i < clipped.length; i++) {
      try {
        let next_u = turf.union(turf.featureCollection([u, clipped[i]]));
        if (next_u) u = next_u;
      } catch(e){}
    }

    let holes = [];
    let extractHoles = (coords) => {
      for (let r = 1; r < coords.length; r++) holes.push(coords[r]);
    };
    if (u.geometry.type === "Polygon") extractHoles(u.geometry.coordinates);
    else for (let poly of u.geometry.coordinates) extractHoles(poly);

    let count = 0;
    for (let h of holes) {
      let a = turf.area(turf.polygon([h])) / 1e6;
      if (a <= max_hole_area_km2 && a >= 0.001) count++;
    }

    if (count > 0) {
      total_holes += count;
      tiles_with_holes++;
    }
  }

  console.log(`Global total at 1800 AD: ${total_holes} small holes across ${tiles_with_holes} tiles!`);
}

probe1800Global().catch(console.error);
