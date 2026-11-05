let fs = require("node:fs");
global.ve = { registry: { settings: {} } };
require("../UF/js/date/date_basic.js");
require("../UF/js/date/date_conversion.js");

async function inspectQuirks () {
  let file_path = "saves/atlas_defacto.naissance";
  let rs = fs.createReadStream(file_path, { highWaterMark: 4 * 1024 * 1024 });
  let in_string = false, is_escaped = false, depth = 0, root_opened = false;
  let state = "SEEK_KEY", key_start = -1, val_start = -1, key_chunks = [], val_chunks = [];

  let all = [];
  let handleEntry = (key, val_str) => {
    if (key === "map_settings") return;
    let obj = JSON.parse(val_str);
    if (obj.class_name !== "GeometryPolygon") return;
    let kfs = obj.history;
    let ts_keys = Object.keys(kfs).sort((a, b) => Number(a) - Number(b));
    let p = kfs[ts_keys[0]][2] || {};
    let d1 = Date.convertTimestampToDate(Number(ts_keys[0]));
    let d2 = Date.convertTimestampToDate(Number(ts_keys[ts_keys.length - 1]));
    all.push({
      id: Number(key),
      name: p.name,
      start: d1.year,
      end: d2.year,
      ct: p.control_type || "",
      parent: p.parent || "",
      label: p.label || "",
      link: p.link || "",
      desc: (obj.metadata?.description || "").replace(/\s+/g, " ").slice(0, 120)
    });
  };

  for await (let chunk of rs) {
    let str = chunk.toString("utf8");
    let len = str.length, i = 0;
    while (i < len) {
      let ch = str[i];
      if (is_escaped) { is_escaped = false; i++; continue; }
      if (ch === "\\") { is_escaped = true; i++; continue; }
      if (ch === '"') {
        in_string = !in_string;
        if (state === "SEEK_KEY" && in_string && depth === 1) { state = "IN_KEY"; key_start = i + 1; }
        else if (state === "IN_KEY" && !in_string) {
          state = "SEEK_COLON";
          if (key_start !== -1) { key_chunks.push(str.slice(key_start, i)); key_start = -1; }
        }
        i++; continue;
      }
      if (in_string) { i++; continue; }
      if (!root_opened) { if (ch === "{") { root_opened = true; depth = 1; } i++; continue; }
      if (state === "SEEK_COLON") { if (ch === ":") { state = "IN_VAL"; val_start = i + 1; } i++; continue; }
      if (state === "SEEK_KEY") { if (ch === "}") { depth = 0; break; } i++; continue; }
      if (state === "IN_VAL") {
        if (ch === "{" || ch === "[") depth++;
        else if (ch === "}" || ch === "]") {
          depth--;
          if (depth === 1) {
            if (val_start !== -1) { val_chunks.push(str.slice(val_start, i + 1)); val_start = -1; }
            handleEntry(key_chunks.join(""), val_chunks.join("").trim());
            state = "SEEK_KEY"; key_chunks = []; val_chunks = [];
          } else if (depth === 0) break;
        } else if (ch === "," && depth === 1) {
          if (val_start !== -1) { val_chunks.push(str.slice(val_start, i)); val_start = -1; }
          handleEntry(key_chunks.join(""), val_chunks.join("").trim());
          state = "SEEK_KEY"; key_chunks = []; val_chunks = [];
        }
      }
      i++;
    }
    if (state === "IN_KEY" && key_start !== -1) { key_chunks.push(str.slice(key_start, len)); key_start = 0; }
    if (state === "IN_VAL" && val_start !== -1) { val_chunks.push(str.slice(val_start, len)); val_start = 0; }
  }

  all.sort((a, b) => a.id - b.id);
  console.log("=== FIRST 30 HRE ===");
  for (let e of all.slice(0, 30)) console.log(`${e.id}: ${e.name} [${e.start}-${e.end}] link=${e.link}`);

  console.log("\n=== SAMPLE DYNASTIES ===");
  for (let e of all.filter((x) => /Dynasty/i.test(x.name)).slice(0, 35)) console.log(`${e.id}: ${e.name} [${e.start}-${e.end}] link=${e.link}`);

  console.log("\n=== SAMPLE GREEK POLEIS ===");
  for (let e of all.filter((x) => x.label.includes("greek poleis")).slice(0, 25)) console.log(`${e.id}: ${e.name} [${e.start}-${e.end}] link=${e.link}`);

  console.log("\n=== SAMPLE REBELS / MILITANTS / ACRONYMS ===");
  for (let e of all.filter((x) => /^[A-Z0-9-]{2,8}$/.test(x.name) || /Rebels|Insurgents|Front|Movement|Army|Brigade|Militia|Junta|ISIS|ISIL|Taliban/i.test(x.name)).slice(0, 40)) {
    console.log(`${e.id}: ${e.name} [${e.start}-${e.end}] link=${e.link} desc=${e.desc}`);
  }
}

inspectQuirks().catch(console.error);
