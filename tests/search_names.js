let fs = require("node:fs");
let readline = require("node:readline");

function searchFile(filepath, terms) {
  return new Promise((resolve) => {
    let rs = fs.createReadStream(filepath);
    let rl = readline.createInterface({ input: rs });
    let matches = [];
    rl.on("line", (l) => {
      let lower = l.toLowerCase();
      for (let t of terms) {
        if (lower.includes(t)) {
          let q_end = l.indexOf('"', 1);
          let k = (q_end > 1) ? l.slice(1, q_end) : "unknown";
          // Try extracting name if present
          let name_match = l.match(/"name":\s*"([^"]+)"/);
          let name = name_match ? name_match[1] : null;
          matches.push({ file: filepath, key: k, name: name, term: t, sample: l.slice(0, 150) });
          break;
        }
      }
    });
    rl.on("close", () => resolve(matches));
  });
}

async function main() {
  let terms = ["bukov", "bucov", "bessarab", "chernivtsi", "cernauti", "moldav", "romania", "ukrain"];
  console.log("Searching detailed.naissance...");
  let res_detailed = await searchFile("saves/detailed.naissance", ["bukov", "bucov", "bessarab", "chernivtsi", "cernauti"]);
  console.log("Detailed matches for Bukovina/Bessarabia:", res_detailed);

  let res_atlas = await searchFile("saves/atlas.naissance", ["bukov", "bucov", "bessarab", "chernivtsi", "cernauti"]);
  console.log("Atlas matches for Bukovina/Bessarabia:", res_atlas);
}

main().catch(console.error);
