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

function printMem(tag) {
  let mem = process.memoryUsage();
  console.log(`[Mem: ${tag}] RSS = ${(mem.rss/1024/1024).toFixed(1)}MB | Heap = ${(mem.heapUsed/1024/1024).toFixed(1)}MB`);
}

async function runTemporalHRE() {
  let start_time = Date.now();
  console.log("================================================================================");
  console.log("COMPREHENSIVE TEMPORAL KEYFRAME HOLE CLOSURE (CENTRAL EUROPE / HRE)");
  console.log("================================================================================");
  printMem("Startup");

  // Region: Entire Holy Roman Empire / Central Europe
  let region_bbox = [5.0, 46.0, 16.0, 56.0];
  let max_hole_area_km2 = 150.0;
  let min_hole_area_km2 = 0.0001;

  // Era of fragmentation: 1356 AD to 1820 AD
  let min_year = 1356;
  let max_year = 1820;
  let start_ts = min_year * 525960;
  let end_ts = max_year * 525960;

  let D = 2; // 2 degree tiles

  console.log("\n[Pass 1/4] Streaming entities touching Central Europe...");
  let rs = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let all_ents = new Map(); // id -> ent
  let total_lines = 0;

  for await (let raw_line of rl) {
    total_lines++;
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    let val_str = line.slice(colon + 1).replace(/,$/, "");

    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;

      let touches_region = false;
      for (let ts in ent.history) {
        let n = Number(ts);
        if (n >= start_ts && n <= end_ts) {
          let kf = ent.history[ts];
          let geom = kf ? kf[0] : null;
          if (geom && geom.coordinates && geom.coordinates.length > 0) {
            let b = turf.bbox(geom);
            if (b[0] <= region_bbox[2] && b[2] >= region_bbox[0] &&
                b[1] <= region_bbox[3] && b[3] >= region_bbox[1]) {
              touches_region = true;
              break;
            }
          }
        }
      }

      if (touches_region) {
        all_ents.set(id, ent);
      }
    } catch(e) {}
  }

  console.log(`[Pass 1] Loaded ${all_ents.size} entities touching Central Europe in ${min_year}–${max_year} AD.`);
  printMem("Entities Loaded");

  // Subdivide Central Europe into 2-degree tiles with 0.1 degree overlap buffer
  let tiles = [];
  let buffer = 0.08; // 0.08 degree buffer to avoid edge-sliver cuts
  for (let x = Math.floor(region_bbox[0]/D)*D; x < region_bbox[2]; x += D) {
    for (let y = Math.floor(region_bbox[1]/D)*D; y < region_bbox[3]; y += D) {
      let t_bbox = [x - buffer, y - buffer, x + D + buffer, y + D + buffer];
      tiles.push({
        x, y,
        bbox: t_bbox,
        poly: turf.bboxPolygon(t_bbox),
        core_bbox: [x, y, x + D, y + D]
      });
    }
  }

  console.log(`[Pass 2/4] Processing ${tiles.length} buffered tiles across keyframe history...`);

  let total_holes_closed_all_tiles = 0;
  let polities_modified = new Set();

  for (let tile_idx = 0; tile_idx < tiles.length; tile_idx++) {
    let tile = tiles[tile_idx];
    let { x, y, bbox: t_bbox, poly: t_poly, core_bbox } = tile;

    // Find entities touching this tile
    let tile_ents = [];
    let ts_set = new Set();

    for (let [id, ent] of all_ents.entries()) {
      let touches = false;
      for (let ts in ent.history) {
        let n = Number(ts);
        if (n >= start_ts && n <= end_ts) {
          let kf = ent.history[ts];
          let geom = kf ? kf[0] : null;
          if (geom && geom.coordinates && geom.coordinates.length > 0) {
            let b = turf.bbox(geom);
            if (b[0] <= t_bbox[2] && b[2] >= t_bbox[0] && b[1] <= t_bbox[3] && b[3] >= t_bbox[1]) {
              touches = true;
              ts_set.add(n);
            }
          }
        }
      }
      if (touches) tile_ents.push(ent);
    }

    if (tile_ents.length < 2 || ts_set.size === 0) continue;

    let sorted_ts = Array.from(ts_set).sort((a,b)=>a-b);
    let tile_holes_closed = 0;

    for (let target_ts of sorted_ts) {
      // Find active entities at this timestamp
      let active = [];
      for (let ent of tile_ents) {
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
            if (b[0] <= t_bbox[2] && b[2] >= t_bbox[0] && b[1] <= t_bbox[3] && b[3] >= t_bbox[1]) {
              try {
                let c = turf.intersect(turf.featureCollection([turf.feature(geom), t_poly]));
                if (c && c.geometry && c.geometry.coordinates && c.geometry.coordinates.length > 0) {
                  active.push({
                    id: ent.id,
                    name: ent.name || kf?.[2]?.name || ent.id,
                    active_ts,
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

      // Union
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

      if (holes.length === 0) continue;

      let candidate_holes = [];
      for (let h of holes) {
        let p = turf.polygon([h]);
        let a = turf.area(p) / 1e6;
        let b = turf.bbox(p);
        // Only close holes whose centroid/box falls inside the core tile
        let cx = (b[0] + b[2]) / 2;
        let cy = (b[1] + b[3]) / 2;
        if (a <= max_hole_area_km2 && a >= min_hole_area_km2 &&
            cx >= core_bbox[0] && cx <= core_bbox[2] &&
            cy >= core_bbox[1] && cy <= core_bbox[3]) {
          candidate_holes.push({ poly: p, a, b, cx, cy });
        }
      }

      if (candidate_holes.length === 0) continue;

      let pieces_by_id = new Map();
      for (let h of candidate_holes) {
        let touching = [];
        for (let af of active) {
          if (af.b[0] <= h.b[2] + 0.03 && af.b[2] >= h.b[0] - 0.03 &&
              af.b[1] <= h.b[3] + 0.03 && af.b[3] >= h.b[1] - 0.03) {
            touching.push(af);
          }
        }

        if (touching.length === 0) continue;

        let tris = turf.tesselate(h.poly);
        let assigned_names = new Set();

        for (let tri of tris.features) {
          let c = turf.centroid(tri).geometry.coordinates;
          let best_af = null;
          let min_d = Infinity;
          for (let af of touching) {
            let d = minDistToGeomSq(c[0], c[1], af.segs);
            if (d < min_d) { min_d = d; best_af = af; }
          }
          if (best_af) {
            if (!pieces_by_id.has(best_af.id)) {
              pieces_by_id.set(best_af.id, { active_ts: best_af.active_ts, pieces: [] });
            }
            pieces_by_id.get(best_af.id).pieces.push(tri);
            assigned_names.add(best_af.name || best_af.id);
          }
        }

        tile_holes_closed++;
        total_holes_closed_all_tiles++;
        let year = Math.round(target_ts / 525960);
        console.log(`[Tile ${x}°, ${y}° | Year ${year}] Hole at (${h.cx.toFixed(2)}°E, ${h.cy.toFixed(2)}°N) | Area: ${h.a.toFixed(2).padStart(6)} km² | Assigned: ${Array.from(assigned_names).join(", ")}`);
      }

      // Merge into in-memory entity history
      for (let [id, data] of pieces_by_id.entries()) {
        let ent = all_ents.get(id);
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
        polities_modified.add(id);
      }
    }
  }

  console.log(`\n[Pass 2] Total holes closed across all tiles & keyframes: ${total_holes_closed_all_tiles}`);
  console.log(`[Pass 2] Total polities modified: ${polities_modified.size}`);
  printMem("After Tile Processing");

  // PASS 3: Stream write back to saves/detailed.naissance.tmp
  console.log("\n[Pass 3/4] Streaming updated database to saves/detailed.naissance.tmp...");
  let rs_in = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl_in = readline.createInterface({ input: rs_in, crlfDelay: Infinity });
  let ws_out = fs.createWriteStream("saves/detailed.naissance.tmp", { encoding: "utf8" });

  let line_index = 0;
  let updated_in_file = 0;

  for await (let raw_line of rl_in) {
    line_index++;
    if (line_index <= 41) {
      ws_out.write(raw_line + "\n");
      continue;
    }
    if (raw_line.trim() === "}") {
      ws_out.write(raw_line + "\n");
      continue;
    }

    let line = raw_line.trim();
    if (!line.includes('":{')) {
      ws_out.write(raw_line + "\n");
      continue;
    }

    let had_trailing_comma = line.endsWith(",");
    let clean_line = had_trailing_comma ? line.slice(0, -1) : line;
    let colon_idx = clean_line.indexOf(":");
    let id = clean_line.slice(1, colon_idx - 1);

    if (polities_modified.has(id)) {
      let ent = all_ents.get(id);
      if (ent) {
        let serialized = JSON.stringify(ent);
        let new_line = `"${id}":${serialized}${had_trailing_comma ? "," : ""}\n`;
        ws_out.write(new_line);
        updated_in_file++;
        continue;
      }
    }

    ws_out.write(raw_line + "\n");
  }

  await new Promise((resolve) => ws_out.end(resolve));

  console.log(`[Pass 3] Wrote ${line_index} lines (${updated_in_file} entities modified).`);

  let stat_orig = fs.statSync("saves/detailed.naissance.pre_hole_closure.bak");
  let stat_tmp = fs.statSync("saves/detailed.naissance.tmp");
  console.log(`Original file size: ${stat_orig.size} bytes`);
  console.log(`New .tmp file size: ${stat_tmp.size} bytes (diff: ${stat_tmp.size - stat_orig.size} bytes)`);

  if (stat_tmp.size < 600000000) {
    throw new Error(`Generated .tmp file size is suspiciously small: ${stat_tmp.size} bytes! Aborting.`);
  }

  // Atomically replace
  console.log("\n[Pass 4/4] Atomically replacing saves/detailed.naissance...");
  fs.renameSync("saves/detailed.naissance.tmp", "saves/detailed.naissance");
  console.log("Replacement complete!");

  let total_elapsed = ((Date.now() - start_time) / 1000).toFixed(2);
  console.log(`\n================================================================================`);
  console.log(`ALL KEYFRAMES CLOSED SUCCESSFULLY IN ${total_elapsed}s!`);
  console.log(`================================================================================`);
}

runTemporalHRE().catch(console.error);
