let fs = require("node:fs");
let readline = require("node:readline");

async function check() {
  let rs = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let total_ents = 0;
  let ents_with_geom = 0;
  let total_geoms = 0;
  let geom_ts_set = new Set();
  let ts_counts = new Map();

  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    total_ents++;
    let colon = line.indexOf(":");
    let val_str = line.slice(colon + 1).replace(/,$/, "");
    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;
      let has_g = false;
      for (let ts in ent.history) {
        let kf = ent.history[ts];
        if (kf && kf[0] && kf[0].coordinates && kf[0].coordinates.length > 0) {
          has_g = true;
          total_geoms++;
          let n_ts = Number(ts);
          geom_ts_set.add(n_ts);
          ts_counts.set(n_ts, (ts_counts.get(n_ts) || 0) + 1);
        }
      }
      if (has_g) ents_with_geom++;
    } catch(e){}
  }
  
  let sorted_ts = Array.from(ts_counts.entries()).sort((a,b)=>b[1]-a[1]);
  console.log({ total_ents, ents_with_geom, total_geoms, unique_geom_timestamps: geom_ts_set.size });
  console.log("Top 20 timestamps by number of entities with geometry definition:");
  for (let i = 0; i < Math.min(20, sorted_ts.length); i++) {
    let [ts, count] = sorted_ts[i];
    let year = (ts / 525960).toFixed(1);
    console.log(`  ts: ${ts} (Year ${year}) -> ${count} entities`);
  }
}
check().catch(console.error);
