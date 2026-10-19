let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

async function testTileCaching() {
  let tile_bbox = [6.0, 44.0, 8.0, 46.0];
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
  console.log(`Loaded ${tile_ents.size} entities with ${sorted_ts.length} global timestamps in Tile [6, 44].`);

  let start_t = Date.now();

  let t_pre_start = Date.now();
  // Pre-clip each entity's keyframes to the tile once, storing a geometry hash / coordinate count
  // ent_id -> Map<ts, { clipped_geom, sig }>
  let clipped_cache = new Map();
  for (let [id, ent] of tile_ents.entries()) {
    let m = new Map();
    for (let ts in ent.history) {
      let kf = ent.history[ts];
      let geom = kf ? kf[0] : null;
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
              m.set(Number(ts), { geom: c.geometry, sig, b: b_clip });
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
  let t_pre_end = Date.now();
  console.log(`Pre-clipping took: ${((t_pre_end - t_pre_start)/1000).toFixed(2)}s`);

  // Now, evaluate timestamps with tile-local state signature
  let t_eval_start = Date.now();
  let last_tile_sig = null;
  let evaluated = 0;
  let skipped = 0;
  let holes_found = 0;

  for (let target_ts of sorted_ts) {
    let active_sigs = [];
    let active_items = [];

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
        let cached = clipped_cache.get(id)?.get(active_ts);
        if (cached) {
          active_sigs.push(`${id}:${cached.sig}`);
          active_items.push({ id, active_ts, cached });
        }
      }
    }

    if (active_items.length < 2) continue;

    let tile_sig = active_sigs.sort().join(";");
    if (tile_sig === last_tile_sig) {
      skipped++;
      continue;
    }
    last_tile_sig = tile_sig;
    evaluated++;

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

    for (let h of holes) {
      let p = turf.polygon([h]);
      let a = turf.area(p) / 1e6;
      let b = turf.bbox(p);
      if (a <= 150.0 && a >= 0.05 &&
          b[0] >= tile_bbox[0] - 0.001 && b[2] <= tile_bbox[2] + 0.001 &&
          b[1] >= tile_bbox[1] - 0.001 && b[3] <= tile_bbox[3] + 0.001) {
        holes_found++;
      }
    }
  }

  let t_eval_end = Date.now();
  console.log(`Union & Hole eval took: ${((t_eval_end - t_eval_start)/1000).toFixed(2)}s`);

  let elapsed = ((Date.now() - start_t) / 1000).toFixed(2);
  console.log(`Tile [6, 44] Result: Evaluated: ${evaluated}, Skipped duplicate local states: ${skipped}, Holes found: ${holes_found}, Time: ${elapsed}s`);
}

testTileCaching().catch(console.error);
