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

async function testMultiEraClosure() {
  console.log("=== MULTI-ERA KEYFRAME HOLE CLOSURE (FRANCONIA / THURINGIA) ===");
  let bbox = [9.5, 49.5, 11.5, 50.8]; // Franconia screenshot bbox
  let max_hole_area_km2 = 150.0;
  let min_hole_area_km2 = 0.0001;

  let test_years = [1707, 1736, 1753, 1787, 1800, 1803, 1806, 1815];

  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let all_ents = new Map(); // id -> ent

  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    let val_str = line.slice(colon + 1).replace(/,$/, "");

    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;

      let touches_bbox = false;
      for (let ts in ent.history) {
        let kf = ent.history[ts];
        let geom = kf ? kf[0] : null;
        if (geom && geom.coordinates && geom.coordinates.length > 0) {
          let b = turf.bbox(geom);
          if (b[0] <= bbox[2] && b[2] >= bbox[0] && b[1] <= bbox[3] && b[3] >= bbox[1]) {
            touches_bbox = true;
            break;
          }
        }
      }

      if (touches_bbox) {
        all_ents.set(id, ent);
      }
    } catch(e) {}
  }

  console.log(`Loaded ${all_ents.size} entities touching Franconia.\n`);

  for (let year of test_years) {
    let target_ts = year * 525960;
    console.log(`--- Processing Year ${year} (ts ${target_ts}) ---`);

    // Find active entities at this year
    let active_features = [];
    for (let [id, ent] of all_ents.entries()) {
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
    }

    if (active_features.length < 2) {
      console.log(`  Only ${active_features.length} active features; skipping.`);
      continue;
    }

    // Coverage union
    let u = turf.feature(active_features[0].geom);
    for (let i = 1; i < active_features.length; i++) {
      try {
        let nu = turf.union(turf.featureCollection([u, turf.feature(active_features[i].geom)]));
        if (nu) u = nu;
      } catch(e) {}
    }

    let holes = [];
    let extractHoles = (coords) => {
      for (let r = 1; r < coords.length; r++) holes.push(coords[r]);
    };
    if (u.geometry.type === "Polygon") extractHoles(u.geometry.coordinates);
    else for (let poly of u.geometry.coordinates) extractHoles(poly);

    let candidate_holes = [];
    for (let i = 0; i < holes.length; i++) {
      let poly = turf.polygon([holes[i]]);
      let a = turf.area(poly) / 1e6;
      let b = turf.bbox(poly);
      if (a <= max_hole_area_km2 && a >= min_hole_area_km2 &&
          b[0] >= 9.5 && b[2] <= 11.5 && b[1] >= 49.5 && b[3] <= 50.8) {
        candidate_holes.push({ poly, coords: holes[i], area: a, bbox: b });
      }
    }

    console.log(`  Active entities: ${active_features.length} | Candidate holes: ${candidate_holes.length}`);

    if (candidate_holes.length === 0) continue;

    let closed = 0;
    for (let h of candidate_holes) {
      let h_bbox = h.bbox;
      let neighbors = [];
      for (let af of active_features) {
        if (af.bbox[0] <= h_bbox[2] + 0.05 && af.bbox[2] >= h_bbox[0] - 0.05 &&
            af.bbox[1] <= h_bbox[3] + 0.05 && af.bbox[3] >= h_bbox[1] - 0.05) {
          neighbors.push(af);
        }
      }

      if (neighbors.length === 0) continue;

      let tris = turf.tesselate(h.poly);
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

      closed++;
      let center = [(h_bbox[0]+h_bbox[2])/2, (h_bbox[1]+h_bbox[3])/2];
      console.log(`  [Hole ${closed.toString().padStart(2)}/${candidate_holes.length}] at (${center[0].toFixed(2)}°E, ${center[1].toFixed(2)}°N) | Area: ${h.area.toFixed(3).padStart(6)} km² | Assigned: ${Array.from(hole_assigned_to).join(", ")}`);
    }

    // Merge into entity keyframe
    for (let af of active_features) {
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
        
        // Update in-memory entity keyframe!
        let ent = all_ents.get(af.id);
        if (ent && ent.history && ent.history[af.active_ts]) {
          ent.history[af.active_ts][0] = cur.geometry;
        }
      }
    }
  }

  // Final verification across ALL tested years
  console.log("\n=======================================================");
  console.log("FINAL POST-CLOSURE VERIFICATION ACROSS ALL TEST YEARS");
  console.log("=======================================================");

  for (let year of test_years) {
    let target_ts = year * 525960;
    let active = [];
    for (let [id, ent] of all_ents.entries()) {
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
            active.push(kf[0]);
          }
        }
      }
    }

    if (active.length < 2) continue;

    let u = turf.feature(active[0]);
    for (let i = 1; i < active.length; i++) {
      try {
        let nu = turf.union(turf.featureCollection([u, turf.feature(active[i])]));
        if (nu) u = nu;
      } catch(e) {}
    }

    let holes = [];
    let extract = (c) => { for (let r = 1; r < c.length; r++) holes.push(c[r]); };
    if (u.geometry.type === "Polygon") extract(u.geometry.coordinates);
    else for (let poly of u.geometry.coordinates) extract(poly);

    let remaining_small = 0;
    for (let h of holes) {
      let a = turf.area(turf.polygon([h])) / 1e6;
      let b = turf.bbox(turf.polygon([h]));
      if (a <= max_hole_area_km2 && a >= 0.001 &&
          b[0] >= 9.5 && b[2] <= 11.5 && b[1] >= 49.5 && b[3] <= 50.8) {
        remaining_small++;
      }
    }

    console.log(`Year ${year}: ${remaining_small} remaining small holes!`);
  }
}

testMultiEraClosure().catch(console.error);
