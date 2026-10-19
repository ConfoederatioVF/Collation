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

async function testBufferedTile() {
  console.log("=== TESTING BUFFERED TILE (REGION 9.5 to 11.5, 49.5 to 51.5) ===");
  let region_bbox = [9.4, 49.4, 11.6, 51.6]; // Slightly buffered screenshot area
  let check_bbox = [9.5, 49.5, 11.5, 50.8]; // Exact screenshot area
  let region_poly = turf.bboxPolygon(region_bbox);
  let max_hole_area_km2 = 150.0;

  let start_ts = 1648 * 525960;
  let end_ts = 1815 * 525960;

  let rs = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let region_ents = new Map();
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
        let n = Number(ts);
        if (n >= start_ts && n <= end_ts) {
          let kf = ent.history[ts];
          let geom = kf ? kf[0] : null;
          if (geom && geom.coordinates && geom.coordinates.length > 0) {
            let b = turf.bbox(geom);
            if (b[0] <= region_bbox[2] && b[2] >= region_bbox[0] && b[1] <= region_bbox[3] && b[3] >= region_bbox[1]) {
              touches = true;
              ts_set.add(n);
            }
          }
        }
      }

      if (touches) region_ents.set(id, ent);
    } catch(e) {}
  }

  let sorted_ts = Array.from(ts_set).sort((a,b)=>a-b);
  console.log(`Loaded ${region_ents.size} entities across ${sorted_ts.length} timestamps.`);

  for (let target_ts of sorted_ts) {
    let active = [];
    for (let [id, ent] of region_ents.entries()) {
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
          if (b[0] <= region_bbox[2] && b[2] >= region_bbox[0] && b[1] <= region_bbox[3] && b[3] >= region_bbox[1]) {
            try {
              let c = turf.intersect(turf.featureCollection([turf.feature(geom), region_poly]));
              if (c && c.geometry && c.geometry.coordinates && c.geometry.coordinates.length > 0) {
                active.push({
                  id,
                  name: ent.name || kf?.[2]?.name || id,
                  active_ts,
                  geom,
                  clipped: c.geometry,
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

    let u = turf.feature(active[0].clipped);
    for (let i = 1; i < active.length; i++) {
      try {
        let nu = turf.union(turf.featureCollection([u, turf.feature(active[i].clipped)]));
        if (nu) u = nu;
      } catch(e) {}
    }

    let holes = [];
    let extract = (c) => { for (let r = 1; r < c.length; r++) holes.push(c[r]); };
    if (u.geometry.type === "Polygon") extract(u.geometry.coordinates);
    else for (let poly of u.geometry.coordinates) extract(poly);

    let small_holes = [];
    for (let h of holes) {
      let p = turf.polygon([h]);
      let a = turf.area(p) / 1e6;
      let b = turf.bbox(p);
      // Strictly inside the buffered region
      if (a <= max_hole_area_km2 && a >= 0.0001 &&
          b[0] >= region_bbox[0] + 0.01 && b[2] <= region_bbox[2] - 0.01 &&
          b[1] >= region_bbox[1] + 0.01 && b[3] <= region_bbox[3] - 0.01) {
        small_holes.push({ poly: p, a, b });
      }
    }

    if (small_holes.length === 0) continue;

    let pieces_by_id = new Map();
    for (let h of small_holes) {
      let touching = [];
      for (let af of active) {
        if (af.b[0] <= h.b[2] + 0.02 && af.b[2] >= h.b[0] - 0.02 &&
            af.b[1] <= h.b[3] + 0.02 && af.b[3] >= h.b[1] - 0.02) {
          touching.push(af);
        }
      }

      if (touching.length === 0) continue;

      let tris = turf.tesselate(h.poly);
      for (let tri of tris.features) {
        let c = turf.centroid(tri).geometry.coordinates;
        let best_af = null;
        let min_d = Infinity;
        for (let af of touching) {
          let d = minDistToGeomSq(c[0], c[1], af.segs);
          if (d < min_d) { min_d = d; best_af = af; }
        }
        if (best_af) {
          if (!pieces_by_id.has(best_af.id)) pieces_by_id.set(best_af.id, { active_ts: best_af.active_ts, pieces: [] });
          pieces_by_id.get(best_af.id).pieces.push(tri);
        }
      }
    }

    for (let [id, data] of pieces_by_id.entries()) {
      let ent = region_ents.get(id);
      if (!ent || !ent.history || !ent.history[data.active_ts]) continue;
      let cur = turf.feature(ent.history[data.active_ts][0]);
      for (let p of data.pieces) {
        try {
          let m = turf.union(turf.featureCollection([cur, p]));
          if (m) cur = m;
        } catch(e) {}
      }
      cur = turf.cleanCoords(cur);
      cur = turf.truncate(cur, { precision: 5 });
      try {
        cur = turf.simplify(cur, { tolerance: 0.00002, highQuality: true, mutate: false });
      } catch(e) {}
      ent.history[data.active_ts][0] = cur.geometry;
    }
  }

  // Verification at 1800 AD strictly inside screenshot bbox
  console.log("\nVerifying 1800 AD inside screenshot bbox [9.5..11.5, 49.5..50.8]:");
  let t_ts = 1800 * 525960;
  let act = [];
  for (let [id, ent] of region_ents.entries()) {
    let tss = Object.keys(ent.history).map(Number).sort((a,b)=>a-b);
    let at = null;
    for (let i = 0; i < tss.length; i++) {
      if (tss[i] <= t_ts && (i + 1 === tss.length || t_ts < tss[i+1])) { at = tss[i]; break; }
    }
    if (at !== null && ent.history[at]?.[0]?.coordinates?.length > 0) {
      let g = ent.history[at][0];
      let b = turf.bbox(g);
      if (b[0] <= check_bbox[2] && b[2] >= check_bbox[0] && b[1] <= check_bbox[3] && b[3] >= check_bbox[1]) {
        try {
          let c = turf.intersect(turf.featureCollection([turf.feature(g), turf.bboxPolygon(check_bbox)]));
          if (c && c.geometry?.coordinates?.length > 0) act.push(c.geometry);
        } catch(e) {}
      }
    }
  }

  let u = turf.feature(act[0]);
  for (let i = 1; i < act.length; i++) {
    try {
      let nu = turf.union(turf.featureCollection([u, turf.feature(act[i])]));
      if (nu) u = nu;
    } catch(e) {}
  }
  let holes = [];
  let extract = (c) => { for (let r = 1; r < c.length; r++) holes.push(c[r]); };
  if (u.geometry.type === "Polygon") extract(u.geometry.coordinates);
  else for (let poly of u.geometry.coordinates) extract(poly);

  let remaining_holes = [];
  for (let h of holes) {
    let p = turf.polygon([h]);
    let a = turf.area(p) / 1e6;
    let b = turf.bbox(p);
    if (a <= max_hole_area_km2 && a >= 0.0001 &&
        b[0] >= check_bbox[0] && b[2] <= check_bbox[2] &&
        b[1] >= check_bbox[1] && b[3] <= check_bbox[3]) {
      remaining_holes.push({ a, b });
    }
  }

  console.log(`Remaining holes in screenshot bbox at 1800 AD: ${remaining_holes.length}!`);
  for (let rh of remaining_holes) {
    console.log(`  Hole: area = ${rh.a.toFixed(3)} km², center = (${((rh.b[0]+rh.b[2])/2).toFixed(2)}, ${((rh.b[1]+rh.b[3])/2).toFixed(2)})`);
  }
}

testBufferedTile().catch(console.error);
