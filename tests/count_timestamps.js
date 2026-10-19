let fs = require("node:fs");
let readline = require("node:readline");

async function countTimestamps() {
  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let ts_set = new Set();
  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let val_str = line.slice(colon + 1).replace(/,$/, "");
    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;
      for (let ts in ent.history) {
        let kf = ent.history[ts];
        if (kf && kf[0] && kf[0].coordinates) {
          ts_set.add(Number(ts));
        }
      }
    } catch(e) {}
  }

  let all_ts = Array.from(ts_set).sort((a,b)=>a-b);
  console.log(`Total unique timestamps with geometry keyframes: ${all_ts.length}`);
  
  // Group timestamps by year
  let years = new Set(all_ts.map(t => Math.round(t / 525960)));
  console.log(`Total unique integer years: ${years.size}`);
}

countTimestamps().catch(console.error);
