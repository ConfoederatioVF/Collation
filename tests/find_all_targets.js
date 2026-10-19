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
  
  let name_match = clean.match(/"name":\s*"([^"]+)"/);
  let name = name_match ? name_match[1] : null;
  if (!name) return;
  
  let lower = name.toLowerCase();
  let targets = [
    "soviet", "ukrain", "byeloruss", "belarus", "galicia", "hungar", "bavar",
    "bohemia", "moravia", "slovak", "romania", "poland", "germany", "russian sfsr",
    "bessarabia", "bukovina"
  ];
  
  for (let t of targets) {
    if (lower.includes(t)) {
      let parent_match = clean.match(/"parent":\s*"([^"]+)"/);
      let fill_match = clean.match(/"polygonFill":\s*"([^"]+)"/);
      polities.push({
        key: key,
        name: name,
        parent: parent_match ? parent_match[1] : null,
        fill: fill_match ? fill_match[1] : null,
        length: clean.length
      });
      break;
    }
  }
});

rl.on("close", () => {
  console.log(`Total matching entities: ${polities.length}`);
  // Sort alphabetically by name
  polities.sort((a, b) => a.name.localeCompare(b.name));
  for (let p of polities) {
    console.log(`[${p.key}] "${p.name}" | parent: ${p.parent} | fill: ${p.fill} | bytes: ${p.length}`);
  }
});
