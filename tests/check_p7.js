let fs = require("node:fs");
let readline = require("node:readline");

let rs = fs.createReadStream("saves/.cache/detailed/partition_7.ndjson");
let rl = readline.createInterface({ input: rs });
let count = 0;
let keys = [];
let total_bytes = 0;
let largest_key = "";
let largest_size = 0;

rl.on("line", function (l) {
  count++;
  total_bytes += l.length;
  let q_end = l.indexOf('"', 1);
  let k = l.slice(1, q_end);
  keys.push(k);
  if (l.length > largest_size) {
    largest_size = l.length;
    largest_key = k;
  }
});

rl.on("close", function () {
  console.log("Lines in partition 7:", count);
  console.log("Total bytes:", total_bytes);
  console.log("Largest entity:", largest_key, "Size:", (largest_size / 1024 / 1024).toFixed(2), "MB");
  console.log("Sample keys:", keys.slice(0, 10));
  
  // Also check memory of JSON.parse on these
  let mem_before = process.memoryUsage().heapUsed;
  console.log("Heap before loading partition 7 into memory:", (mem_before / 1024 / 1024).toFixed(2), "MB");
});
