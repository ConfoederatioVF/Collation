let fs = require("node:fs");
let readline = require("node:readline");

let target_names = [
  "Würzburg Prince-Bishopric",
  "Bamberg Prince-Bishopric",
  "Saxony-Meiningen-Coburg Duchy",
  "Saxony-Saalfeld-Coburg Duchy",
  "Saxony-Hildburghausen Duchy",
  "Fulda Prince-Bishopric",
  "Imperial City of Schweinfurth",
  "Castell County"
];

async function inspect() {
  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    let val_str = line.slice(colon + 1).replace(/,$/, "");

    for (let name of target_names) {
      if (val_str.includes(`"${name}"`)) {
        let ent = JSON.parse(val_str);
        console.log(`\nEntity ${id}: "${name}"`);
        let tss = Object.keys(ent.history).map(Number).sort((a,b)=>a-b);
        for (let ts of tss) {
          let year = Math.round(ts / 525960);
          let kf = ent.history[ts];
          let has_geom = Boolean(kf && kf[0] && kf[0].coordinates);
          let geom_type = has_geom ? kf[0].type : "null";
          console.log(`  ts ${ts} (Year ${year}): geom = ${geom_type}, props = ${JSON.stringify(kf?.[2] || kf?.[1] || {})}`);
        }
      }
    }
  }
}

inspect().catch(console.error);
