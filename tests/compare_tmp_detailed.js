let fs = require("node:fs");
let readline = require("node:readline");

async function loadLines(file) {
  let rs = fs.createReadStream(file);
  let rl = readline.createInterface({ input: rs });
  let map = new Map();
  for await (let l of rl) {
    let clean = l.trim();
    if (!clean.startsWith('"')) continue;
    let q_end = clean.indexOf('"', 1);
    if (q_end <= 1) continue;
    let colon_idx = clean.indexOf(':', q_end);
    if (colon_idx === -1) continue;
    let key = clean.slice(1, q_end);
    let val = clean.slice(colon_idx + 1).trim();
    if (val.endsWith(',')) val = val.slice(0, -1);
    map.set(key, val);
  }
  return map;
}

async function run() {
  console.log("Loading tmp file...");
  let tmp_map = await loadLines("saves/.cache/detailed/partition_7.ndjson.tmp_1792445167373_54");
  console.log(`Tmp file had ${tmp_map.size} complete entities.`);

  console.log("Loading original detailed.naissance lines for partition 7 keys...");
  // Let's check against detailed.naissance
  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs });
  let diff_count = 0;
  for await (let l of rl) {
    let clean = l.trim();
    if (!clean.startsWith('"')) continue;
    let q_end = clean.indexOf('"', 1);
    if (q_end <= 1) continue;
    let key = clean.slice(1, q_end);
    if (tmp_map.has(key)) {
      let colon_idx = clean.indexOf(':', q_end);
      let val = clean.slice(colon_idx + 1).trim();
      if (val.endsWith(',')) val = val.slice(0, -1);
      if (val !== tmp_map.get(key)) {
        console.log(`Key ${key} in tmp file is DIFFERENT from detailed.naissance!`);
        diff_count++;
      }
    }
  }
  console.log(`Comparison finished. Diffs found in tmp: ${diff_count}`);
}

run().catch(console.error);
