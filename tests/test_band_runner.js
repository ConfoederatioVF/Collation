let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

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

async function processBand(min_lon, max_lon, band_name) {
  let start_time = Date.now();
  console.log(`\n======================================================`);
  console.log(`PROCESSING ${band_name} [Lon: ${min_lon}° to ${max_lon}°]`);
  console.log(`======================================================`);

  // Step 1: Stream entities that touch this longitude band
  let rs = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let band_ents = new Map();
  let D = 2; // 2 degree tiles
  let tile_events = new Map(); // "tx,ty" -> Set of timestamps
  let tile_ents = new Map(); // "tx,ty" -> Set of ent_ids

  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    let val_str = line.slice(colon + 1).replace(/,$/, "");

    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;

      let touches_band = false;
      let ent_tiles = [];

      for (let ts in ent.history) {
        let kf = ent.history[ts];
        let geom = kf ? kf[0] : null;
        if (geom && geom.coordinates && geom.coordinates.length > 0) {
          let b = turf.bbox(geom);
          if (b[0] <= max_lon + 0.08 && b[2] >= min_lon - 0.08) {
            touches_band = true;
            let n_ts = Number(ts);
            let min_tx = Math.max(Math.floor(min_lon / D), Math.floor((b[0] - 0.08) / D));
            let max_tx = Math.min(Math.floor((max_lon - 0.001) / D), Math.floor((b[2] + 0.08) / D));
            let min_ty = Math.floor((b[1] - 0.08) / D);
            let max_ty = Math.floor((b[3] + 0.08) / D);

            for (let x = min_tx; x <= max_tx; x++) {
              for (let y = min_ty; y <= max_ty; y++) {
                let tkey = `${x},${y}`;
                if (!tile_events.has(tkey)) tile_events.set(tkey, new Set());
                tile_events.get(tkey).add(n_ts);

                if (!tile_ents.has(tkey)) tile_ents.set(tkey, new Set());
                tile_ents.get(tkey).add(id);
              }
            }
          }
        }
      }

      if (touches_band) band_ents.set(id, ent);
    } catch(e) {}
  }

  let mem1 = process.memoryUsage();
  console.log(`Loaded ${band_ents.size} entities in band. RSS: ${(mem1.rss/1024/1024).toFixed(1)} MB, Heap: ${(mem1.heapUsed/1024/1024).toFixed(1)} MB`);

  // Filter tiles with >= 2 entities
  let active_tiles = [];
  for (let [tkey, ents_set] of tile_ents.entries()) {
    if (ents_set.size >= 2) {
      let [tx, ty] = tkey.split(",").map(Number);
      active_tiles.push({ tx, ty, tkey, events: Array.from(tile_events.get(tkey)).sort((a,b)=>a-b), ent_ids: ents_set });
    }
  }

  console.log(`Active multi-entity tiles in band: ${active_tiles.length}`);

  let total_holes = 0;
  let pieces_count = 0;

  for (let t of active_tiles) {
    let tile_bbox = [t.tx * D, t.ty * D, (t.tx + 1) * D, (t.ty + 1) * D];
    let buffered_poly = turf.bboxPolygon([tile_bbox[0] - 0.08, tile_bbox[1] - 0.08, tile_bbox[2] + 0.08, tile_bbox[3] + 0.08]);

    let last_state_key = null;
    for (let target_ts of t.events) {
      let year = Math.round(target_ts / 525960);
      let active = [];
      let state_parts = [];

      for (let id of t.ent_ids) {
        let ent = band_ents.get(id);
        if (!ent || !ent.history) continue;
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
              active.push({ id, active_ts, geom, name: ent.name || kf?.[2]?.name || id });
              state_parts.push(`${id}:${active_ts}`);
            }
          }
        }
      }

      if (active.length < 2) continue;

      let state_key = state_parts.sort().join(";");
      if (state_key === last_state_key) continue;
      last_state_key = state_key;

      let clipped_active = [];
      for (let a of active) {
        try {
          let c = turf.intersect(turf.featureCollection([turf.feature(a.geom), buffered_poly]));
          if (c && c.geometry && c.geometry.coordinates && c.geometry.coordinates.length > 0) {
            clipped_active.push({
              id: a.id,
              name: a.name,
              active_ts: a.active_ts,
              clipped_geom: c.geometry,
              segs: extractSegments(c.geometry),
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

      let small_holes = [];
      for (let h of holes) {
        let p = turf.polygon([h]);
        let a = turf.area(p) / 1e6;
        let b = turf.bbox(p);
        if (a <= 150.0 && a >= 0.05 &&
            b[0] >= tile_bbox[0] - 0.001 && b[2] <= tile_bbox[2] + 0.001 &&
            b[1] >= tile_bbox[1] - 0.001 && b[3] <= tile_bbox[3] + 0.001) {
          small_holes.push({ poly: p, a, b });
        }
      }

      if (small_holes.length === 0) continue;

      // Assign triangles to touching polities
      let pieces_by_id = new Map();
      for (let h of small_holes) {
        let touching = [];
        for (let af of clipped_active) {
          if (af.b[0] <= h.b[2] + 0.02 && af.b[2] >= h.b[0] - 0.02 &&
              af.b[1] <= h.b[3] + 0.02 && af.b[3] >= h.b[1] - 0.02) {
            touching.push(af);
          }
        }
        if (touching.length === 0) continue;

        let tris = turf.tesselate(h.poly);
        let assigned_to = new Set();
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
            assigned_to.add(best_af.name || best_af.id);
            pieces_count++;
          }
        }

        total_holes++;
        let center = [(h.b[0]+h.b[2])/2, (h.b[1]+h.b[3])/2];
        console.log(`[Tile ${tile_bbox[0]}°E, ${tile_bbox[1]}°N | Year ${year}] Hole at (${center[0].toFixed(2)}°E, ${center[1].toFixed(2)}°N) | Area: ${h.a.toFixed(2)} km² | Assigned to: ${Array.from(assigned_to).join(", ")}`);
      }

      // Merge assigned pieces directly into the polity keyframe in memory
      for (let [id, data] of pieces_by_id.entries()) {
        let ent = band_ents.get(id);
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
  }

  let elapsed = ((Date.now() - start_time) / 1000).toFixed(1);
  let mem2 = process.memoryUsage();
  console.log(`\nFinished ${band_name}: Closed ${total_holes} holes (${pieces_count} triangles) across ${active_tiles.length} active tiles in ${elapsed}s.`);
  console.log(`Final memory: RSS: ${(mem2.rss/1024/1024).toFixed(1)} MB, Heap: ${(mem2.heapUsed/1024/1024).toFixed(1)} MB`);
}

async function run() {
  // Test Band 6: Europe (0 to 30)
  await processBand(0, 30, "Band 6: Western & Central Europe");
}

run().catch(console.error);
