let fs = require("node:fs");
let readline = require("node:readline");
let turf = require("../UF/js/geospatiale/turf.min.js");

let bbox = [9.5, 49.5, 11.5, 50.8]; // Franconia screenshot bbox

async function findEntitiesInBBox() {
  let rs = fs.createReadStream("saves/detailed.naissance");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let found = [];
  for await (let raw_line of rl) {
    let line = raw_line.trim();
    if (!line.includes('":{')) continue;
    let colon = line.indexOf(":");
    let id = line.slice(1, colon - 1);
    let val_str = line.slice(colon + 1).replace(/,$/, "");

    try {
      let ent = JSON.parse(val_str);
      if (!ent.history) continue;

      let has_in_bbox = false;
      let kf_info = [];
      for (let ts in ent.history) {
        let kf = ent.history[ts];
        let geom = kf ? kf[0] : null;
        if (geom && geom.coordinates && geom.coordinates.length > 0) {
          let b = turf.bbox(geom);
          if (b[0] <= bbox[2] && b[2] >= bbox[0] && b[1] <= bbox[3] && b[3] >= bbox[1]) {
            has_in_bbox = true;
            kf_info.push({ ts: Number(ts), year: Math.round(Number(ts)/525960) });
          }
        }
      }

      if (has_in_bbox) {
        found.push({
          id,
          name: ent.name || ent.metadata?.name || id,
          desc: ent.metadata?.description || "",
          keyframes: kf_info
        });
      }
    } catch(e) {}
  }

  console.log(`Found ${found.length} entities with keyframes in Franconia bbox:`);
  for (let f of found) {
    let years = f.keyframes.map(k=>k.year).join(", ");
    console.log(`  Entity ${f.id.padStart(4)}: "${f.name}" | Years with geoms: [${years}]`);
  }
}

findEntitiesInBBox().catch(console.error);
