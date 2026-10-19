let fs = require("node:fs");
let readline = require("node:readline");

let rs = fs.createReadStream("saves/.cache/detailed/partition_7.ndjson");
let rl = readline.createInterface({ input: rs });

let bytes_accum = 0;
let line_idx = 0;

rl.on("line", (l) => {
  line_idx++;
  let start_b = bytes_accum;
  bytes_accum += l.length + 1;
  let end_b = bytes_accum;
  
  if (l.length > 1000000) {
    let q_end = l.indexOf('"', 1);
    let k = l.slice(1, q_end);
    let name_m = l.match(/"name":\s*"([^"]+)"/);
    console.log(`Line ${line_idx}: offset ${start_b}-${end_b}, key: ${k}, len: ${(l.length/1024/1024).toFixed(2)} MB, name: ${name_m ? name_m[1] : 'null'}`);
  }
});
