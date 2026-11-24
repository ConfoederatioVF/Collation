let fs = require("fs");
let path = require("path");

let input = JSON.parse(fs.readFileSync("tests/chunk_044_input.json", "utf8"));
let quipu_dir = "histmap/1.data_raw/population_regional/QUIPU";

function walk(dir, files = []) {
  for (let ent of fs.readdirSync(dir, { withFileTypes: true })) {
    let p = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(p, files);
    else if (ent.name.endsWith(".json") && !ent.name.includes("subadmin") && !ent.name.includes("sources")) files.push(p);
  }
  return files;
}

let files = walk(quipu_dir);
let matches = {};
for (let item of input) matches[item.key] = [];

for (let f of files) {
  let data;
  try { data = JSON.parse(fs.readFileSync(f, "utf8")); } catch (e) { continue; }
  if (!data || typeof data !== "object" || Array.isArray(data)) continue;
  for (let item of input) {
    let rec = data[item.key];
    if (rec) {
      matches[item.key].push({
        file: path.relative(quipu_dir, f),
        ...rec
      });
    }
  }
}

fs.writeFileSync("tests/chunk_044_gaz_matches.json", JSON.stringify(matches, null, 2));
let matched_count = Object.values(matches).filter(a => a.length > 0).length;
console.log("Matched keys:", matched_count, "/", input.length);
