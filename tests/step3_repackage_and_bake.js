//Import libraries
let fs = require("node:fs");
let path = require("node:path");

require("../UF/js/vercengen/db/NDJSON_main.js");

/**
 * Loads all verified formal polity names from temp_jobs/polity_names_<0..7>.txt,
 * streams and updates saves/atlas_defacto.naissance while preserving keyframe diff architecture
 * (no redundant .name properties across multiple keyframes), and bakes saves/.cache/atlas_defacto.
 */
async function A_repackageAndBake () {
  //Declare local instance variables
  let comma_newline = Buffer.from(",\n");
  let depth = 0;
  let file_path = path.resolve(process.cwd(), "saves/atlas_defacto.naissance");
  let in_string = false;
  let is_escaped = false;
  let is_first_entry = true;
  let key_chunks = [];
  let key_start = -1;
  let name_map = new Map();
  let newline = Buffer.from("\n");
  let redundant_kfs_cleaned = 0;
  let renamed_entities = 0;
  let root_opened = false;
  let state = "SEEK_KEY";
  let temp_jobs_dir = path.resolve(process.cwd(), "temp_jobs");
  let tmp_path = `${file_path}.tmp_${Date.now()}`;
  let total_polygons_seen = 0;
  let val_chunks = [];
  let val_start = -1;

  //1. Load all 8 polity_names_<#>.txt chunks
  for (let i = 0; i < 8; i++) {
    let chunk_path = path.join(temp_jobs_dir, `polity_names_${i}.txt`);
    if (!fs.existsSync(chunk_path)) {
      console.error(`Missing chunk file: ${chunk_path}`);
      process.exit(1);
    }
    let lines = fs.readFileSync(chunk_path, "utf8").trimEnd().split(/\r?\n/);
    for (let x = 0; x < lines.length; x++) {
      let sep_idx = lines[x].indexOf(": ");
      if (sep_idx === -1) {
        console.error(`Invalid line in ${chunk_path}:${x + 1} -> ${lines[x]}`);
        process.exit(1);
      }
      let id = lines[x].slice(0, sep_idx).trim();
      let formal_name = lines[x].slice(sep_idx + 2).trim();
      if (!id || !formal_name) {
        console.error(`Empty id or formal_name in ${chunk_path}:${x + 1}`);
        process.exit(1);
      }
      name_map.set(id, formal_name);
    }
  }
  console.log(`Loaded ${name_map.size} verified polity names from temp_jobs/polity_names_0..7.txt.`);

  let writeBuf = async function (arg0_ws, arg1_buf) {
    //Convert from parameters
    let local_ws = arg0_ws;
    let buf = arg1_buf;

    if (!local_ws.write(buf))
      await new Promise((resolve) => local_ws.once("drain", resolve));
  };

  //2. Stream saves/atlas_defacto.naissance -> tmp_path, updating baseline .name and cleaning redundant keyframe .name deltas
  let rs = fs.createReadStream(file_path, { highWaterMark: 4*1024*1024 });
  let ws = fs.createWriteStream(tmp_path, { highWaterMark: 4*1024*1024 });

  await writeBuf(ws, Buffer.from("{\n"));

  let processEntry = async function (arg0_key, arg1_val_str) {
    //Convert from parameters
    let key = arg0_key;
    let val_str = arg1_val_str;

    if (!is_first_entry) {
      await writeBuf(ws, comma_newline);
    }
    is_first_entry = false;

    if (key === "map_settings" || !name_map.has(key)) {
      await writeBuf(ws, Buffer.from(`"${key}":${val_str}`));
      return;
    }

    let obj = JSON.parse(val_str);
    if (obj.class_name !== "GeometryPolygon" || !obj.history) {
      await writeBuf(ws, Buffer.from(`"${key}":${val_str}`));
      return;
    }

    total_polygons_seen++;
    let formal_name = name_map.get(key);
    let kfs = obj.history;
    let ts_keys = Object.keys(kfs).sort((a, b) => Number(a) - Number(b));
    let modified = false;

    if (ts_keys.length > 0) {
      let first_kf = kfs[ts_keys[0]];
      if (!first_kf[2] || typeof first_kf[2] !== "object") first_kf[2] = {};
      if (first_kf[2].name !== formal_name) {
        first_kf[2].name = formal_name;
        modified = true;
        renamed_entities++;
      }

      //Ensure no subsequent keyframe duplicates .name (diff architecture guarantee)
      let active_name = first_kf[2].name;
      for (let i = 1; i < ts_keys.length; i++) {
        let ts = ts_keys[i];
        let kf = kfs[ts];
        if (Array.isArray(kf) && kf[2] && kf[2].name !== undefined) {
          //If subsequent keyframe was a suzerain-tag rename on the same polity (e.g. 4400) or duplicates active_name, strip redundant .name
          delete kf[2].name;
          modified = true;
          redundant_kfs_cleaned++;

          if (Object.keys(kf[2]).length === 0) {
            kf.pop();
            if (kf.length === 2 && (kf[1] === null || kf[1] === undefined)) {
              kf.pop();
            }
            if (kf.length === 1 && (kf[0] === undefined || kf[0] === "undefined")) {
              delete kfs[ts];
            }
          }
        }
      }
    }

    if (!modified) {
      await writeBuf(ws, Buffer.from(`"${key}":${val_str}`));
    } else {
      await writeBuf(ws, Buffer.from(`"${key}":${JSON.stringify(obj)}`));
    }
  };

  for await (let chunk of rs) {
    let str = chunk.toString("utf8");
    let len = str.length;

    for (let i = 0; i < len; i++) {
      let ch = str[i];

      if (is_escaped) {
        is_escaped = false;
        continue;
      }
      if (ch === "\\") {
        is_escaped = true;
        continue;
      }
      if (ch === '"') {
        in_string = !in_string;
        if (state === "SEEK_KEY" && in_string && depth === 1) {
          state = "IN_KEY";
          key_start = i + 1;
        } else if (state === "IN_KEY" && !in_string) {
          state = "SEEK_COLON";
          if (key_start !== -1) {
            key_chunks.push(str.slice(key_start, i));
            key_start = -1;
          }
        }
        continue;
      }
      if (in_string) continue;

      if (!root_opened) {
        if (ch === "{") {
          root_opened = true;
          depth = 1;
        }
        continue;
      }
      if (state === "SEEK_COLON") {
        if (ch === ":") {
          state = "IN_VAL";
          val_start = i + 1;
        }
        continue;
      }
      if (state === "SEEK_KEY") {
        if (ch === "}") {
          depth = 0;
          break;
        }
        continue;
      }
      if (state === "IN_VAL") {
        if (ch === "{" || ch === "[") {
          depth++;
        } else if (ch === "}" || ch === "]") {
          depth--;
          if (depth === 1) {
            if (val_start !== -1) {
              val_chunks.push(str.slice(val_start, i + 1));
              val_start = -1;
            }
            await processEntry(key_chunks.join(""), val_chunks.join("").trim());
            state = "SEEK_KEY";
            key_chunks = [];
            val_chunks = [];
          } else if (depth === 0) {
            break;
          }
        } else if (ch === "," && depth === 1) {
          if (val_start !== -1) {
            val_chunks.push(str.slice(val_start, i));
            val_start = -1;
          }
          await processEntry(key_chunks.join(""), val_chunks.join("").trim());
          state = "SEEK_KEY";
          key_chunks = [];
          val_chunks = [];
        }
      }
    }

    if (state === "IN_KEY" && key_start !== -1) {
      key_chunks.push(str.slice(key_start, len));
      key_start = 0;
    }
    if (state === "IN_VAL" && val_start !== -1) {
      val_chunks.push(str.slice(val_start, len));
      val_start = 0;
    }
  }

  await writeBuf(ws, newline);
  await writeBuf(ws, Buffer.from("}"));
  ws.end();
  await new Promise((resolve) => ws.on("finish", resolve));

  if (total_polygons_seen !== name_map.size) {
    try { fs.unlinkSync(tmp_path); } catch (e) {}
    console.error(`Polygon count mismatch! Expected ${name_map.size}, saw ${total_polygons_seen}`);
    process.exit(1);
  }

  //Verify boundary structure before replacing saves/atlas_defacto.naissance
  let stat = fs.statSync(tmp_path);
  let fd = fs.openSync(tmp_path, "r");
  let head_buf = Buffer.alloc(50);
  let tail_buf = Buffer.alloc(50);
  fs.readSync(fd, head_buf, 0, 50, 0);
  fs.readSync(fd, tail_buf, 0, 50, Math.max(0, stat.size - 50));
  fs.closeSync(fd);

  if (!head_buf.toString("utf8").startsWith("{\n") || !tail_buf.toString("utf8").trim().endsWith("}")) {
    try { fs.unlinkSync(tmp_path); } catch (e) {}
    console.error(`Boundary JSON check failed on ${tmp_path}`);
    process.exit(1);
  }

  fs.renameSync(tmp_path, file_path);
  console.log(`Updated saves/atlas_defacto.naissance (${(stat.size / (1024*1024)).toFixed(2)} MB):`);
  console.log(`  Polygons verified: ${total_polygons_seen}`);
  console.log(`  Polities renamed: ${renamed_entities}`);
  console.log(`  Redundant multi-keyframe .name entries cleaned: ${redundant_kfs_cleaned}`);

  //3. Bake saves/.cache/atlas_defacto via NDJSON.load(..., { force_reload: true })
  console.log(`Baking cache in saves/.cache/atlas_defacto ...`);
  let shard_0 = await NDJSON.load(file_path, { force_reload: true });
  console.log(`Cache baked successfully: ${shard_0}`);
  await NDJSON.terminate();
}

A_repackageAndBake().catch(async (err) => {
  console.error(err);
  try { await NDJSON.terminate(); } catch (e) {}
  process.exit(1);
});
