let fs = require("fs");
let path = require("path");

global.ve = { registry: { settings: {} } };
let root = path.resolve(".");
require(path.join(root, "UF/js/date/date_basic.js"));
require(path.join(root, "UF/js/date/date_conversion.js"));

let json = JSON.parse(fs.readFileSync("saves/atlas_dejure.naissance", "utf8"));

let polities = {};

for (let id in json) {
  let ent = json[id];
  if (!ent || typeof ent !== "object" || !ent.history) continue;
  let ent_name = ent.name || (ent.metadata && ent.metadata.name) || "";

  for (let ts in ent.history) {
    let arr = ent.history[ts];
    if (Array.isArray(arr)) {
      for (let item of arr) {
        if (item && typeof item === "object" && (item.cow_code !== undefined || item.gwcode !== undefined)) {
          let date_obj = Date.convertTimestampToDate(Number(ts));
          let year = date_obj ? date_obj.year : Math.round(Number(ts) / 525960 + 1);
          let name = item.name || ent_name || `ID_${id}`;
          
          let key = `${id} | ${name}`;
          if (!polities[key]) polities[key] = [];
          polities[key].push({
            ts: Number(ts),
            year: year,
            cow_code: item.cow_code,
            gwcode: item.gwcode,
            seshat_id: item.seshat_id,
            item_ref: item
          });
        }
      }
    }
  }
}

console.log(`Total polities with cow_code or gwcode: ${Object.keys(polities).length}\n`);

// Filter for target countries or anomalies
let targets = ["germany", "prussia", "yemen", "serbia", "kiribati", "nauru", "tuvalu", "tonga", "vietnam", "yugoslavia"];

for (let key in polities) {
  let isTarget = targets.some(t => key.toLowerCase().includes(t));
  let list = polities[key];
  if (isTarget) {
    console.log(`=== ${key} ===`);
    for (let e of list) {
      console.log(`  Year: ${e.year} (ts: ${e.ts}) | cow_code: ${e.cow_code} | gwcode: ${e.gwcode} | seshat_id: ${e.seshat_id}`);
    }
  }
}
