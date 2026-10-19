let fs = require("node:fs");

let buf = fs.readFileSync("saves/.cache/detailed/partition_7.ndjson.tmp_1792445167373_54");
console.log("Length:", buf.length);
let str = buf.slice(Math.max(0, buf.length - 1000)).toString("utf8");
console.log("Last 1000 chars of tmp file:\n", str);
