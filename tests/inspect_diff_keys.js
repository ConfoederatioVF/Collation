let fs = require("node:fs");
let readline = require("node:readline");

let diff_keys = new Set(['7370', '1788', '2114', '7433', '4112', '6537', '6318']);

let rs = fs.createReadStream("saves/detailed.naissance");
let rl = readline.createInterface({ input: rs });

rl.on("line", (line) => {
  let clean = line.trim();
  if (!clean.startsWith('"')) return;
  let q_end = clean.indexOf('"', 1);
  if (q_end <= 1) return;
  let key = clean.slice(1, q_end);
  if (diff_keys.has(key)) {
    let name_m = clean.match(/"name":\s*"([^"]+)"/);
    console.log(`Key ${key}: "${name_m ? name_m[1] : 'unknown'}"`);
  }
});
