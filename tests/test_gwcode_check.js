let fs = require("fs");
let simp = JSON.parse(fs.readFileSync("saves/atlas_simplified.naissance", "utf8"));
let burma = simp["79315678680"];
for (let t in burma.history) {
  let kf = burma.history[t];
  console.log(`ts: ${t}, len: ${kf.length}, feat_props:`, kf[0] && kf[0].feature ? kf[0].feature.properties : null, "props_diff:", kf[2]);
}
