let fs = require("node:fs");
let readline = require("node:readline");

console.log("Memory before test:", (process.memoryUsage().heapUsed / 1024 / 1024).toFixed(2), "MB");

// Let's test readline on partition_7.ndjson and log memory at each line
let rs = fs.createReadStream("saves/.cache/detailed/partition_7.ndjson");
let rl = readline.createInterface({ input: rs, crlfDelay: Infinity });

let line_no = 0;
async function run() {
  for await (let line of rl) {
    line_no++;
    if (line.length > 500000) {
      let mem = process.memoryUsage();
      console.log(`Line ${line_no}: len=${(line.length/1024/1024).toFixed(2)} MB, heapUsed=${(mem.heapUsed/1024/1024).toFixed(2)} MB, rss=${(mem.rss/1024/1024).toFixed(2)} MB`);
    }
  }
  console.log("Finished all lines. Final heapUsed:", (process.memoryUsage().heapUsed / 1024 / 1024).toFixed(2), "MB");
}

run().catch(console.error);
