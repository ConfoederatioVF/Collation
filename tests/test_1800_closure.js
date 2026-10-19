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

async function test1800Closure() {
  console.log("=== TESTING 1800 AD HOLE CLOSURE IN FRANCONIA ===");
  let target_ts = 1800 * 525960; // 946728000
  let bbox = [9.5, 49.5, 11.5, 50.8]; // Franconia screenshot bbox
  let max_hole_area_km2 = 150.0;

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
          if (b[0] <= bbox[2] && b[2] >= bbox[0] && b[1] <= bbox[3] && b[3] >= bbox[1]) {
            let name = ent.name || kf?.[2]?.name || id;
            active_features.push({
              id,
              name,
              active_ts,
              geom,
              bbox: b,
              segs: extractSegments(geom),
              assigned_pieces: []
            });
          }
        }
      }
    } catch(e) {}
  }

  console.log(`Matched ${active_features.length} active features in Franconia at 1800 AD.`);

  let u = turf.feature(active_features[0].geom);
  for (let i = 1; i < active_features.length; i++) {
    try {
      let next_u = turf.union(turf.featureCollection([u, turf.feature(active_features[i].geom)]));
      if (next_u) u = next_u;
    } catch(e) {}
  }

  let holes = [];
  let extractHoles = (coords) => {
    for (let r = 1; r < coords.length; r++) holes.push(coords[r]);
  };
  if (u.geometry.type === "Polygon") extractHoles(u.geometry.coordinates);
  else for (let poly of u.geometry.coordinates) extractHoles(poly);

  console.log(`Total interior holes: ${holes.length}`);

  let small_holes = [];
  for (let i = 0; i < holes.length; i++) {
    let poly = turf.polygon([holes[i]]);
    let a = turf.area(poly) / 1e6;
    let b = turf.bbox(poly);
    if (a <= max_hole_area_km2 && a >= 0.0001 && b[0] >= 9.5 && b[2] <= 11.5 && b[1] >= 49.5 && b[3] <= 50.8) {
      small_holes.push({ index: i, poly, coords: holes[i], area: a, bbox: b });
    }
  }

  console.log(`Candidate small holes to close in screenshot area: ${small_holes.length}`);

  let closed_count = 0;
  for (let h of small_holes) {
    let h_poly = h.poly;
    let h_bbox = h.bbox;

    let neighbors = [];
    for (let af of active_features) {
      if (af.bbox[0] <= h_bbox[2] + 0.05 && af.bbox[2] >= h_bbox[0] - 0.05 &&
          af.bbox[1] <= h_bbox[3] + 0.05 && af.bbox[3] >= h_bbox[1] - 0.05) {
        neighbors.push(af);
      }
    }

    if (neighbors.length === 0) continue;

    let tris = turf.tesselate(h_poly);
    let hole_assigned_to = new Set();

    for (let tri of tris.features) {
      let c = turf.centroid(tri).geometry.coordinates;
      let best_neighbor = null;
      let min_d = Infinity;

      for (let nb of neighbors) {
        let d = minDistToGeomSq(c[0], c[1], nb.segs);
        if (d < min_d) {
          min_d = d;
          best_neighbor = nb;
        }
      }

      if (best_neighbor) {
        best_neighbor.assigned_pieces.push(tri);
        hole_assigned_to.add(best_neighbor.name || best_neighbor.id);
      }
    }

    closed_count++;
    let center = [(h_bbox[0]+h_bbox[2])/2, (h_bbox[1]+h_bbox[3])/2];
    console.log(`[Hole ${closed_count.toString().padStart(2)}/${small_holes.length}] at (${center[0].toFixed(2)}°E, ${center[1].toFixed(2)}°N) | Area: ${h.area.toFixed(3).padStart(6)} km² | Assigned to: ${Array.from(hole_assigned_to).join(", ")}`);
  }

  // Merge
  console.log("\nMerging assigned pieces into respective polities...");
  let initial_v = 0;
  let final_v = 0;

  for (let af of active_features) {
    initial_v += countVertices(af.geom);
    if (af.assigned_pieces.length > 0) {
      let cur = turf.feature(af.geom);
      for (let p of af.assigned_pieces) {
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
      af.geom = cur.geometry;
    }
    final_v += countVertices(af.geom);
  }

  console.log(`Initial vertices: ${initial_v} -> Final vertices: ${final_v} (+${final_v - initial_v}, +${(((final_v - initial_v)/initial_v)*100).toFixed(1)}%)`);

  // Verify
  console.log("\nVerifying remaining holes in region...");
  let new_u = turf.feature(active_features[0].geom);
  for (let i = 1; i < active_features.length; i++) {
    try {
      let next_u = turf.union(turf.featureCollection([new_u, turf.feature(active_features[i].geom)]));
      if (next_u) new_u = next_u;
    } catch(e) {}
  }

  let remaining = [];
  if (new_u.geometry.type === "Polygon") extractHoles(new_u.geometry.coordinates);
  else for (let poly of new_u.geometry.coordinates) extractHoles(poly);

  let remaining_target = 0;
  for (let h of remaining) {
    let p = turf.polygon([h]);
    let a = turf.area(p) / 1e6;
    let b = turf.bbox(p);
    if (a <= max_hole_area_km2 && a >= 0.0001 && b[0] >= 9.5 && b[2] <= 11.5 && b[1] >= 49.5 && b[3] <= 50.8) {
      remaining_target++;
      console.log(`  Remaining hole: area = ${a.toFixed(3)} km², bbox = [${b.map(x=>x.toFixed(2)).join(", ")}]`);
    }
  }

  console.log(`\nRemaining small holes in Franconia at 1800 AD: ${remaining_target} (Reduced from ${small_holes.length})`);
}

test1800Closure().catch(console.error);
