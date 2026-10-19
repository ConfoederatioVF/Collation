let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

async function checkHoleTimestamps() {
  console.log("Analyzing which timestamps across history have enclosed holes in Central Europe / HRE...");
  let bbox = [5.5, 47.0, 15.0, 55.0]; // Central Europe
  let max_hole_area_km2 = 150.0;

  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let ents = [];
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

      let kfs = [];
      let tss = Object.keys(ent.history).map(Number).sort((a,b)=>a-b);
      for (let i = 0; i < tss.length; i++) {
        let ts = tss[i];
        let next_ts = (i + 1 < tss.length) ? tss[i+1] : Infinity;
        let kf = ent.history[ts];
        let geom = kf ? kf[0] : null;
        if (geom && geom.coordinates && geom.coordinates.length > 0) {
          let b = turf.bbox(geom);
          if (b[0] <= bbox[2] && b[2] >= bbox[0] && b[1] <= bbox[3] && b[3] >= bbox[1]) {
            kfs.push({ ts, next_ts, geom, b });
            ts_set.add(ts);
          }
        }
      }

      if (kfs.length > 0) {
        ents.push({ id, kfs });
      }
    } catch(e) {}
  }

  let sorted_ts = Array.from(ts_set).sort((a,b)=>a-b);
  console.log(`Loaded ${ents.length} Central Europe entities with ${sorted_ts.length} unique timestamps.`);

  // Let's sample timestamps every 10 years, plus all major keyframe timestamps
  let years_checked = new Set();
  let candidate_ts = [];
  for (let ts of sorted_ts) {
    let y = Math.round(ts / 525960);
    if (!years_checked.has(y)) {
      years_checked.add(y);
      candidate_ts.push(ts);
    }
  }

  console.log(`Checking ${candidate_ts.length} unique year timestamps for holes...`);

  let ts_with_holes = [];
  for (let ts of candidate_ts) {
    let y = Math.round(ts / 525960);
    // Find active entities at ts
    let active = [];
    for (let e of ents) {
      for (let k of e.kfs) {
        if (k.ts <= ts && ts < k.next_ts) {
          active.push(k);
          break;
        }
      }
    }

    if (active.length < 5) continue;

    // Check union for Franconia sub-bbox
    let f_active = active.filter(k => k.b[0] <= 11.5 && k.b[2] >= 9.5 && k.b[1] <= 50.8 && k.b[3] >= 49.5);
    if (f_active.length < 2) continue;

    let u = turf.feature(f_active[0].geom);
    for (let i = 1; i < f_active.length; i++) {
      try {
        let nu = turf.union(turf.featureCollection([u, turf.feature(f_active[i].geom)]));
        if (nu) u = nu;
      } catch(e) {}
    }

    let holes = [];
    let extract = (c) => { for (let r = 1; r < c.length; r++) holes.push(c[r]); };
    if (u.geometry.type === "Polygon") extract(u.geometry.coordinates);
    else for (let poly of u.geometry.coordinates) extract(poly);

    let small = 0;
    for (let h of holes) {
      let a = turf.area(turf.polygon([h])) / 1e6;
      if (a <= max_hole_area_km2 && a >= 0.01) small++;
    }

    if (small > 0) {
      ts_with_holes.push({ ts, year: y, count: small });
    }
  }

  console.log(`\nYears with holes in Franconia: ${ts_with_holes.length}`);
  for (let h of ts_with_holes.slice(0, 30)) {
    console.log(`  Year ${h.year.toString().padStart(5)}: ${h.count} holes`);
  }
}

checkHoleTimestamps().catch(console.error);
