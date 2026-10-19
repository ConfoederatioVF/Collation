let fs = require("node:fs");
let readline = require("node:readline");

async function analyze() {
  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let ts_entity_count = new Map();
  let total_geoms = 0;
  let total_entities = 0;

  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    total_entities++;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    let val_str = line.slice(colon + 1).replace(/,$/, "");

    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;

      for (let ts in ent.history) {
        let kf = ent.history[ts];
        if (kf && kf[0] && kf[0].coordinates && kf[0].coordinates.length > 0) {
          total_geoms++;
          let n = Number(ts);
          ts_entity_count.set(n, (ts_entity_count.get(n) || 0) + 1);
        }
      }
    } catch(e) {}
  }

  console.log(`Total entities: ${total_entities}`);
  console.log(`Total keyframes with geometry: ${total_geoms}`);
  console.log(`Total unique timestamps with geoms: ${ts_entity_count.size}`);

  let sorted_ts = Array.from(ts_entity_count.entries()).sort((a,b) => b[1] - a[1]);
  console.log("\nTimestamps with >= 20 entities updating:");
  let major_ts = sorted_ts.filter(x => x[1] >= 20);
  console.log(`Count of major timestamps (>= 20 entities): ${major_ts.length}`);

  let major_by_time = major_ts.map(x => ({ ts: x[0], year: Math.round(x[0]/525960), count: x[1] }))
                              .sort((a,b) => a.ts - b.ts);

  for (let m of major_by_time) {
    console.log(`  Year ${m.year.toString().padStart(5)} (ts ${m.ts}): ${m.count} entities`);
  }
}

analyze().catch(console.error);
