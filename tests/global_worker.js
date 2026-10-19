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

async function runWorker() {
  let args = process.argv.slice(2);
  let min_lon = -180;
  let max_lon = 180;
  let band_id = 0;
  let out_file = "tests/pieces_default.ndjson";

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--min_lon") min_lon = Number(args[i+1]);
    if (args[i] === "--max_lon") max_lon = Number(args[i+1]);
    if (args[i] === "--band_id") band_id = Number(args[i+1]);
    if (args[i] === "--out_file") out_file = args[i+1];
  }

  let D = 2; // 2x2 degree tiles
  let start_time = Date.now();
  console.log(`[Band ${band_id}] Starting longitude range [${min_lon}°, ${max_lon}°]`);

  let rs = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let band_ents = new Map();
  let tile_events = new Map();
  let tile_ents = new Map();

  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    let val_str = line.slice(colon + 1).replace(/,$/, "");

    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;

      let history_obj = (typeof ent.history === "string") ? JSON.parse(ent.history) : ent.history;
      let raw_kfs = (history_obj && history_obj.keyframes) ? history_obj.keyframes : history_obj;

      let touches_band = false;

      for (let ts in raw_kfs) {
        let kf = raw_kfs[ts];
        let geom = Array.isArray(kf) ? kf[0] : (kf?.value ? kf.value[0] : null);
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

      if (touches_band) {
        ent.history = raw_kfs;
        band_ents.set(id, ent);
      }
    } catch(e) {}
  }

  let active_tiles = [];
  for (let [tkey, ents_set] of tile_ents.entries()) {
    if (ents_set.size >= 2) {
      let [tx, ty] = tkey.split(",").map(Number);
      active_tiles.push({ tx, ty, tkey, events: Array.from(tile_events.get(tkey)).sort((a,b)=>a-b), ent_ids: ents_set });
    }
  }

  console.log(`[Band ${band_id}] Loaded ${band_ents.size} entities across ${active_tiles.length} multi-entity tiles.`);

  let ws = fs.createWriteStream(out_file, { flags: "w" });
  let total_holes = 0;
  let pieces_count = 0;

  for (let t of active_tiles) {
    let tile_bbox = [t.tx * D, t.ty * D, (t.tx + 1) * D, (t.ty + 1) * D];
    let buffered_poly = turf.bboxPolygon([tile_bbox[0] - 0.08, tile_bbox[1] - 0.08, tile_bbox[2] + 0.08, tile_bbox[3] + 0.08]);

    // Pre-clip each entity's keyframes once to this tile for fast local signatures
    let clipped_cache = new Map();
    for (let id of t.ent_ids) {
      let ent = band_ents.get(id);
      if (!ent || !ent.history) continue;
      let m = new Map();
      for (let ts in ent.history) {
        let kf = ent.history[ts];
        let geom = Array.isArray(kf) ? kf[0] : (kf?.value ? kf.value[0] : null);
        if (geom && geom.coordinates && geom.coordinates.length > 0) {
          let b = turf.bbox(geom);
          if (b[0] <= tile_bbox[2] + 0.08 && b[2] >= tile_bbox[0] - 0.08 && b[1] <= tile_bbox[3] + 0.08 && b[3] >= tile_bbox[1] - 0.08) {
            try {
              let c = turf.intersect(turf.featureCollection([turf.feature(geom), buffered_poly]));
              if (c && c.geometry && c.geometry.coordinates && c.geometry.coordinates.length > 0) {
                let vcount = 0;
                let plist = (c.geometry.type === "Polygon") ? [c.geometry.coordinates] : c.geometry.coordinates;
                for (let poly of plist) for (let r of poly) vcount += r.length;
                let b_clip = turf.bbox(c.geometry);
                let sig = `${vcount}:${b_clip[0].toFixed(3)},${b_clip[1].toFixed(3)},${b_clip[2].toFixed(3)},${b_clip[3].toFixed(3)}`;
                m.set(Number(ts), { geom: c.geometry, sig, b: b_clip, segs: extractSegments(c.geometry) });
              } else {
                m.set(Number(ts), null);
              }
            } catch(e) {
              m.set(Number(ts), null);
            }
          } else {
            m.set(Number(ts), null);
          }
        }
      }
      clipped_cache.set(id, m);
    }

    let last_tile_sig = null;

    for (let target_ts of t.events) {
      let year = Math.round(target_ts / 525960);
      let active_sigs = [];
      let active_items = [];

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
          let cached = clipped_cache.get(id)?.get(active_ts);
          if (cached) {
            active_sigs.push(`${id}:${cached.sig}`);
            active_items.push({
              id,
              name: ent.name || ent.history[active_ts]?.[2]?.name || id,
              active_ts,
              cached
            });
          }
        }
      }

      if (active_items.length < 2) continue;

      let tile_sig = active_sigs.sort().join(";");
      if (tile_sig === last_tile_sig) continue;
      last_tile_sig = tile_sig;

      // Union
      let u = turf.feature(active_items[0].cached.geom);
      for (let i = 1; i < active_items.length; i++) {
        try {
          let nu = turf.union(turf.featureCollection([u, turf.feature(active_items[i].cached.geom)]));
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

      for (let h of small_holes) {
        let touching = [];
        for (let af of active_items) {
          if (af.cached.b[0] <= h.b[2] + 0.02 && af.cached.b[2] >= h.b[0] - 0.02 &&
              af.cached.b[1] <= h.b[3] + 0.02 && af.cached.b[3] >= h.b[1] - 0.02) {
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
            let d = minDistToGeomSq(c[0], c[1], af.cached.segs);
            if (d < min_d) { min_d = d; best_af = af; }
          }
          if (best_af) {
            ws.write(JSON.stringify({
              id: best_af.id,
              ts: best_af.active_ts,
              coords: tri.geometry.coordinates
            }) + "\n");
            assigned_to.add(best_af.name || best_af.id);
            pieces_count++;
          }
        }

        total_holes++;
        let center = [(h.b[0]+h.b[2])/2, (h.b[1]+h.b[3])/2];
        console.log(`[Band ${band_id} | Tile ${tile_bbox[0]}°E, ${tile_bbox[1]}°N | Year ${year}] Hole at (${center[0].toFixed(2)}°E, ${center[1].toFixed(2)}°N) | Area: ${h.a.toFixed(2)} km² | Assigned to: ${Array.from(assigned_to).join(", ")}`);
      }
    }
  }

  ws.end();
  await new Promise(r => ws.on("finish", r));

  let elapsed = ((Date.now() - start_time) / 1000).toFixed(1);
  console.log(`[Band ${band_id} Complete] Closed ${total_holes} holes (${pieces_count} triangles) in ${elapsed}s.`);
}

runWorker().catch((e) => {
  console.error(e);
  process.exit(1);
});
