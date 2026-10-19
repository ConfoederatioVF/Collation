let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

function countVertices(geom) {
  let count = 0;
  let poly_list = (geom.type === "Polygon") ? [geom.coordinates] : geom.coordinates;
  for (let poly of poly_list) {
    for (let ring of poly) count += ring.length;
  }
  return count;
}

function pointToSegmentDistanceSq(px, py, ax, ay, bx, by) {
  let dx = bx - ax;
  let dy = by - ay;
  let lenSq = dx * dx + dy * dy;
  if (lenSq === 0) return (px - ax) * (px - ax) + (py - ay) * (py - ay);
  let t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / lenSq));
  let projX = ax + t * dx;
  let projY = ay + t * dy;
  let diffX = px - projX;
  let diffY = py - projY;
  return diffX * diffX + diffY * diffY;
}

function extractSegments(geom) {
  let segs = [];
  let poly_list = (geom.type === "Polygon") ? [geom.coordinates] : geom.coordinates;
  for (let p = 0; p < poly_list.length; p++) {
    let poly = poly_list[p];
    for (let r = 0; r < poly.length; r++) {
      let ring = poly[r];
      for (let i = 0; i < ring.length - 1; i++) {
        segs.push([ring[i][0], ring[i][1], ring[i+1][0], ring[i+1][1]]);
      }
    }
  }
  return segs;
}

function minDistToGeomSq(px, py, segs) {
  let minD = Infinity;
  for (let i = 0; i < segs.length; i++) {
    let s = segs[i];
    let d = pointToSegmentDistanceSq(px, py, s[0], s[1], s[2], s[3]);
    if (d < minD) minD = d;
  }
  return minD;
}

async function testRegions() {
  let test_tiles = [
    { name: "Franconia (HRE)", bbox: [10.0, 49.0, 12.0, 51.0] },
    { name: "Northern India", bbox: [75.0, 25.0, 77.0, 27.0] },
    { name: "Russian Principalities", bbox: [37.0, 55.0, 39.0, 57.0] },
    { name: "Central China", bbox: [113.0, 33.0, 115.0, 35.0] },
    { name: "Japan (Kansai)", bbox: [135.0, 34.0, 137.0, 36.0] }
  ];

  console.log("=== SCANNING ENTITIES FOR REGIONAL TILES ===");
  let rs = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let tile_data = test_tiles.map(t => ({
    ...t,
    poly: turf.bboxPolygon([t.bbox[0] - 0.08, t.bbox[1] - 0.08, t.bbox[2] + 0.08, t.bbox[3] + 0.08]),
    ents: new Map(),
    ts_set: new Set()
  }));

  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    let val_str = line.slice(colon + 1).replace(/,$/, "");

    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;

      for (let t of tile_data) {
        let touches = false;
        for (let ts in ent.history) {
          let kf = ent.history[ts];
          let geom = kf ? kf[0] : null;
          if (geom && geom.coordinates && geom.coordinates.length > 0) {
            let b = turf.bbox(geom);
            if (b[0] <= t.bbox[2] && b[2] >= t.bbox[0] && b[1] <= t.bbox[3] && b[3] >= t.bbox[1]) {
              touches = true;
              t.ts_set.add(Number(ts));
            }
          }
        }
        if (touches) t.ents.set(id, ent);
      }
    } catch(e) {}
  }

  for (let t of tile_data) {
    let start_tile = Date.now();
    let sorted_ts = Array.from(t.ts_set).sort((a,b)=>a-b);
    console.log(`\n--- Testing ${t.name} (BBox: ${t.bbox.join(", ")}) ---`);
    console.log(`Entities: ${t.ents.size}, Keyframe Timestamps: ${sorted_ts.length}`);

    let holes_found = 0;
    let evaluated_intervals = 0;

    for (let target_ts of sorted_ts) {
      let year = Math.round(target_ts / 525960);
      let active = [];

      for (let [id, ent] of t.ents.entries()) {
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
            let b = turf.bbox(geom);
            if (b[0] <= t.bbox[2] + 0.08 && b[2] >= t.bbox[0] - 0.08 && b[1] <= t.bbox[3] + 0.08 && b[3] >= t.bbox[1] - 0.08) {
              try {
                let c = turf.intersect(turf.featureCollection([turf.feature(geom), t.poly]));
                if (c && c.geometry && c.geometry.coordinates && c.geometry.coordinates.length > 0) {
                  active.push({
                    id,
                    name: ent.name || kf?.[2]?.name || id,
                    active_ts,
                    clipped_geom: c.geometry,
                    segs: extractSegments(c.geometry),
                    b: turf.bbox(c.geometry)
                  });
                }
              } catch(e) {}
            }
          }
        }
      }

      if (active.length < 2) continue;
      evaluated_intervals++;

      // Union
      let u = turf.feature(active[0].clipped_geom);
      for (let i = 1; i < active.length; i++) {
        try {
          let nu = turf.union(turf.featureCollection([u, turf.feature(active[i].clipped_geom)]));
          if (nu) u = nu;
        } catch(e) {}
      }

      let holes = [];
      let extract = (c) => { for (let r = 1; r < c.length; r++) holes.push(c[r]); };
      if (u.geometry.type === "Polygon") extract(u.geometry.coordinates);
      else for (let poly of u.geometry.coordinates) extract(poly);

      for (let h of holes) {
        let p = turf.polygon([h]);
        let a = turf.area(p) / 1e6;
        let b = turf.bbox(p);
        if (a <= 150.0 && a >= 0.0001 &&
            b[0] >= t.bbox[0] - 0.001 && b[2] <= t.bbox[2] + 0.001 &&
            b[1] >= t.bbox[1] - 0.001 && b[3] <= t.bbox[3] + 0.001) {
          holes_found++;
          let center = [(b[0]+b[2])/2, (b[1]+b[3])/2];
          console.log(`  [${t.name} | Year ${year}] Hole at (${center[0].toFixed(2)}°E, ${center[1].toFixed(2)}°N) | Area: ${a.toFixed(2)} km²`);
        }
      }
    }

    let elapsed = ((Date.now() - start_tile) / 1000).toFixed(2);
    console.log(`Result for ${t.name}: Evaluated ${evaluated_intervals} multi-entity intervals, found ${holes_found} holes in ${elapsed}s`);
  }
}

testRegions().catch(console.error);
