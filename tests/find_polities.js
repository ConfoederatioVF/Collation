let fs = require("node:fs");
let readline = require("node:readline");

let rs = fs.createReadStream("saves/detailed.naissance");
let rl = readline.createInterface({ input: rs });

let polities = [];

rl.on("line", (line) => {
  let clean = line.trim();
  if (clean.length === 0 || !clean.startsWith('"')) return;
  let q_end = clean.indexOf('"', 1);
  if (q_end <= 1) return;
  let key = clean.slice(1, q_end);
  
  // Extract name
  let name_match = clean.match(/"name":\s*"([^"]+)"/);
  let name = name_match ? name_match[1] : null;
  
  if (name) {
    let lower = name.toLowerCase();
    if (
      lower.includes("soviet") ||
      lower.includes("ukrain") ||
      lower.includes("byeloruss") ||
      lower.includes("belarus") ||
      lower.includes("galicia") ||
      lower.includes("hungar") ||
      lower.includes("bavar") ||
      lower.includes("german") ||
      lower.includes("bohemia") ||
      lower.includes("moravia") ||
      lower.includes("slovak") ||
      lower.includes("romania") ||
      lower.includes("poland") ||
      lower.includes("russia")
    ) {
      // also extract parent, fill, etc.
      let parent_match = clean.match(/"parent":\s*"([^"]+)"/);
      let fill_match = clean.match(/"polygonFill":\s*"([^"]+)"/);
      polities.push({
        key: key,
        name: name,
        parent: parent_match ? parent_match[1] : null,
        fill: fill_match ? fill_match[1] : null,
        length: clean.length
      });
    }
  }
});

rl.on("close", () => {
  console.log(`Found ${polities.length} matched polities.`);
  console.log(JSON.stringify(polities, null, 2));
});
