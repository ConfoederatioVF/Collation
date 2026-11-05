//Import libraries
let fs = require("node:fs");
let path = require("node:path");

global.ve = { registry: { settings: {} } };
require("../UF/js/date/date_basic.js");
require("../UF/js/date/date_conversion.js");

/**
 * Streams saves/atlas_defacto.naissance and writes 1024-polity chunks to temp_jobs/polity_names_<#>.txt
 * alongside historical context files in tests/polity_context_<#>.tsv.
 */
async function A_chunkPolityNames () {
  //Declare local instance variables
  let chunk_size = 1024;
  let depth = 0;
  let entities_array = [];
  let file_path = path.resolve(process.cwd(), "saves/atlas_defacto.naissance");
  let in_string = false;
  let is_escaped = false;
  let key_chunks = [];
  let key_start = -1;
  let root_opened = false;
  let rs = fs.createReadStream(file_path, { highWaterMark: 4*1024*1024 });
  let state = "SEEK_KEY";
  let temp_jobs_dir = path.resolve(process.cwd(), "temp_jobs");
  let tests_dir = path.resolve(process.cwd(), "tests");
  let val_chunks = [];
  let val_start = -1;

  if (!fs.existsSync(temp_jobs_dir)) fs.mkdirSync(temp_jobs_dir, { recursive: true });
  if (!fs.existsSync(tests_dir)) fs.mkdirSync(tests_dir, { recursive: true });

  let processEntry = function (arg0_key, arg1_val_str) {
    //Convert from parameters
    let key = arg0_key;
    let val_str = arg1_val_str;

    //Guard clauses
    if (key === "map_settings") return;

    //Declare local instance variables
    let obj = JSON.parse(val_str);
    if (obj.class_name !== "GeometryPolygon") return;

    let kfs = obj.history;
    let ts_keys = Object.keys(kfs).sort((a, b) => Number(a) - Number(b));
    let first_props = kfs[ts_keys[0]]?.[2] || {};
    let d_start = Date.convertTimestampToDate(Number(ts_keys[0]));
    let d_end = Date.convertTimestampToDate(Number(ts_keys[ts_keys.length - 1]));

    entities_array.push({
      control_type: (first_props.control_type || "").replace(/[\t\r\n]+/g, " ").trim(),
      description: (obj.metadata?.description || "").replace(/[\t\r\n]+/g, " ").trim(),
      end_date: `${d_end.year}-${String(d_end.month).padStart(2, "0")}-${String(d_end.day).padStart(2, "0")}`,
      id: key,
      id_num: Number(key),
      label: (first_props.label || "").replace(/[\t\r\n]+/g, " ").trim(),
      link: (first_props.link || "").replace(/[\t\r\n]+/g, " ").trim(),
      name: first_props.name || "",
      parent: (first_props.parent || "").replace(/[\t\r\n]+/g, " ").trim(),
      start_date: `${d_start.year}-${String(d_start.month).padStart(2, "0")}-${String(d_start.day).padStart(2, "0")}`
    });
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
            processEntry(key_chunks.join(""), val_chunks.join("").trim());
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
          processEntry(key_chunks.join(""), val_chunks.join("").trim());
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

  entities_array.sort((a, b) => a.id_num - b.id_num);

  let total_chunks = Math.ceil(entities_array.length / chunk_size);
  for (let i = 0; i < total_chunks; i++) {
    let slice = entities_array.slice(i*chunk_size, (i + 1)*chunk_size);
    let txt_lines = [];
    let tsv_lines = ["id\tname\tspan\tcontrol_type\tparent\tlabel\tlink\tdescription"];

    for (let x = 0; x < slice.length; x++) {
      let item = slice[x];
      txt_lines.push(`${item.id}: ${item.name}`);
      tsv_lines.push(`${item.id}\t${item.name}\t${item.start_date}..${item.end_date}\t${item.control_type}\t${item.parent}\t${item.label}\t${item.link}\t${item.description}`);
    }

    let txt_path = path.join(temp_jobs_dir, `polity_names_${i}.txt`);
    let tsv_path = path.join(tests_dir, `polity_context_${i}.tsv`);
    fs.writeFileSync(txt_path, txt_lines.join("\n") + "\n", "utf8");
    fs.writeFileSync(tsv_path, tsv_lines.join("\n") + "\n", "utf8");
    console.log(`Chunk ${i}: ${slice.length} polities (IDs ${slice[0].id}..${slice[slice.length - 1].id}) -> ${txt_path}`);
  }
  console.log(`Total polities chunked: ${entities_array.length} across ${total_chunks} chunks.`);
}

A_chunkPolityNames().catch(console.error);
