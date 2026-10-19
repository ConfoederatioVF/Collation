let fs = require("node:fs");
let readline = require("node:readline");

async function run() {
  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });
  let map = new Map();
  for await (let line of rl) {
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    try {
      let ent = JSON.parse(line.slice(colon + 1).replace(/,$/, ""));
      if (!ent.history) continue;
      for (let ts in ent.history) {
        if (ent.history[ts]?.[0]?.coordinates) {
          let t = Number(ts);
          map.set(t, (map.get(t) || 0) + 1);
        }
      }
    } catch(e){}
  }
  let arr = Array.from(map.values()).sort((a,b)=>b-a);
  console.log("Total timestamps with geoms:", arr.length);
  console.log("Timestamps with >= 100 entities:", arr.filter(x => x >= 100).length);
  console.log("Timestamps with >= 50 entities:", arr.filter(x => x >= 50).length);
  console.log("Timestamps with >= 20 entities:", arr.filter(x => x >= 20).length);
  console.log("Timestamps with >= 10 entities:", arr.filter(x => x >= 10).length);
  console.log("Timestamps with >= 5 entities:", arr.filter(x => x >= 5).length);
  console.log("Timestamps with == 1 entity:", arr.filter(x => x === 1).length);
}
run().catch(console.error);
