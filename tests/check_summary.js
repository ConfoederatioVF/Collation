let fs = require("node:fs");
let readline = require("node:readline");

async function checkBands() {
  let rs = fs.createReadStream("C:/Users/htmlp/.gemini/antigravity-ide/brain/8e5fac50-deb5-4b87-b27c-0cfa90fc7215/.system_generated/tasks/task-3829.log");
  let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

  let latest = new Map();
  let total_holes_by_band = new Map();
  let completed_bands = new Set();

  for await (let line of rl) {
    if (line.includes("[Band ") && line.includes("Complete]")) {
      let m = line.match(/\[Band (\d+) Complete\]/);
      if (m) completed_bands.add(m[1]);
    }
    if (line.includes("[Band ") && line.includes("Tile ")) {
      let m = line.match(/\[Band (\d+) \| Tile ([^\|]+) \| Year (\d+)\]/);
      if (m) {
        let b = m[1];
        latest.set(b, { tile: m[2].trim(), year: m[3] });
        total_holes_by_band.set(b, (total_holes_by_band.get(b) || 0) + 1);
      }
    }
  }

  console.log("=== BAND PROGRESS SUMMARY ===");
  for (let i = 0; i < 12; i++) {
    let key = String(i);
    let info = latest.get(key);
    let holes = total_holes_by_band.get(key) || 0;
    let is_done = completed_bands.has(key) ? " [FINISHED]" : "";
    if (info) {
      console.log(`Band ${key}${is_done}: ${holes} holes closed | Current: Tile ${info.tile} (Year ${info.year})`);
    } else {
      console.log(`Band ${key}${is_done}: 0 holes`);
    }
  }
}
checkBands().catch(console.error);
