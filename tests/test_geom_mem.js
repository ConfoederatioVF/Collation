let fs = require("node:fs");
let readline = require("node:readline");

async function testGeomMem() {
  let rs = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let geom_store = new Map();
  let count = 0;

  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    let val_str = line.slice(colon + 1).replace(/,$/, "");
    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;

      let hist = {};
      let has = false;
      for (let ts in ent.history) {
        let kf = ent.history[ts];
        let g = kf ? kf[0] : null;
        if (g && g.coordinates && g.coordinates.length > 0) {
          hist[ts] = g;
          has = true;
        }
      }
      if (has) {
        geom_store.set(id, { name: ent.name, hist });
        count++;
      }
    } catch(e){}
  }

  let mem = process.memoryUsage();
  console.log(`Loaded ${count} entities with geometry only. RSS: ${(mem.rss / 1024 / 1024).toFixed(1)} MB, Heap: ${(mem.heapUsed / 1024 / 1024).toFixed(1)} MB`);
}

testGeomMem().catch(console.error);
