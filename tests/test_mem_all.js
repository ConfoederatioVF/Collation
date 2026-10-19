let fs = require("node:fs");
let readline = require("node:readline");

async function testMem() {
  let rs = fs.createReadStream("saves/detailed.naissance.pre_hole_closure.bak");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let map = new Map();
  let count = 0;
  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    let val_str = line.slice(colon + 1).replace(/,$/, "");
    try {
      let ent = JSON.parse(val_str);
      map.set(id, ent);
      count++;
    } catch(e){}
  }
  let mem = process.memoryUsage();
  console.log(`Loaded ${count} entities. RSS: ${(mem.rss / 1024 / 1024).toFixed(1)} MB, Heap: ${(mem.heapUsed / 1024 / 1024).toFixed(1)} MB`);
}
testMem().catch(console.error);
