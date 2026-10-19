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

async function testOpt() {
  let tile_bbox = [10.0, 50.0, 12.0, 52.0];
  let buffered_poly = turf.bboxPolygon([tile_bbox[0] - 0.08, tile_bbox[1] - 0.08, tile_bbox[2] + 0.08, tile_bbox[3] + 0.08]);

  let rs = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let tile_ents = new Map();
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

      let touches = false;
      for (let ts in ent.history) {
        let kf = ent.history[ts];
        let geom = kf ? kf[0] : null;
        if (geom && geom.coordinates && geom.coordinates.length > 0) {
          let b = turf.bbox(geom);
          if (b[0] <= tile_bbox[2] + 0.08 && b[2] >= tile_bbox[0] - 0.08 && b[1] <= tile_bbox[3] + 0.08 && b[3] >= tile_bbox[1] - 0.08) {
            touches = true;
            ts_set.add(Number(ts));
          }
        }
      }
      if (touches) tile_ents.set(id, ent);
    } catch(e) {}
  }

  let sorted_ts = Array.from(ts_set).sort((a,b)=>a-b);
  console.log(`Loaded ${tile_ents.size} entities with ${sorted_ts.length} timestamps.`);

  let start_t = Date.now();
  let last_state_key = null;
  let evaluated = 0;
  let skipped = 0;
  let holes_found = 0;

  for (let target_ts of sorted_ts) {
    let active = [];
    let state_parts = [];

    for (let [id, ent] of tile_ents.entries()) {
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
          if (b[0] <= tile_bbox[2] + 0.08 && b[2] >= tile_bbox[0] - 0.08 && b[1] <= tile_bbox[3] + 0.08 && b[3] >= tile_bbox[1] - 0.08) {
            active.push({ id, active_ts, geom });
            state_parts.push(`${id}:${active_ts}`);
          }
        }
      }
    }

    if (active.length < 2) continue;

    // Fast state signature check
    let state_key = state_parts.sort().join(";");
    if (state_key === last_state_key) {
      skipped++;
      continue;
    }
    last_state_key = state_key;
    evaluated++;

    // Now clip
    let clipped_active = [];
    for (let a of active) {
      try {
        let c = turf.intersect(turf.featureCollection([turf.feature(a.geom), buffered_poly]));
        if (c && c.geometry && c.geometry.coordinates && c.geometry.coordinates.length > 0) {
          clipped_active.push({
            id: a.id,
            active_ts: a.active_ts,
            clipped_geom: c.geometry,
            b: turf.bbox(c.geometry)
          });
        }
      } catch(e) {}
    }

    if (clipped_active.length < 2) continue;

    // Union
    let u = turf.feature(clipped_active[0].clipped_geom);
    for (let i = 1; i < clipped_active.length; i++) {
      try {
        let nu = turf.union(turf.featureCollection([u, turf.feature(clipped_active[i].clipped_geom)]));
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
          b[0] >= tile_bbox[0] - 0.001 && b[2] <= tile_bbox[2] + 0.001 &&
          b[1] >= tile_bbox[1] - 0.001 && b[3] <= tile_bbox[3] + 0.001) {
        holes_found++;
      }
    }
  }

  let elapsed = ((Date.now() - start_t) / 1000).toFixed(2);
  console.log(`Evaluated: ${evaluated}, Skipped duplicate states: ${skipped}, Holes found: ${holes_found}, Time: ${elapsed}s`);
}

testOpt().catch(console.error);
