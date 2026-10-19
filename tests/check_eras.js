let fs = require("node:fs");
let readline = require("node:readline");

async function checkEras() {
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
        if (ent.history[ts]?.[0]?.coordinates) {
          ts_set.add(Number(ts));
        }
      }
    } catch(e){}
  }

  let all_ts = Array.from(ts_set).sort((a,b)=>a-b);
  let before_1500 = all_ts.filter(t => t < 1500 * 525960);
  let era_1500_1800 = all_ts.filter(t => t >= 1500 * 525960 && t <= 1800 * 525960);
  let era_1800_1900 = all_ts.filter(t => t > 1800 * 525960 && t <= 1900 * 525960);
  let era_1900_present = all_ts.filter(t => t > 1900 * 525960);

  console.log(`Before 1500: ${before_1500.length} timestamps`);
  console.log(`1500 to 1800: ${era_1500_1800.length} timestamps`);
  console.log(`1800 to 1900: ${era_1800_1900.length} timestamps`);
  console.log(`1900 to present: ${era_1900_present.length} timestamps`);
}

checkEras().catch(console.error);
