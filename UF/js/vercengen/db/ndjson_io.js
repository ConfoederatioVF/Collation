//[VERCENGEN]

//Import libraries
let fs = require("node:fs");
let path = require("node:path");

if (!global?.NDJSON) global.NDJSON = {};

//Initialise NDJSON binary file streaming and atomic compilation helpers
{
  let comma_newline_buf = Buffer.from(",\n");
  let newline_buf = Buffer.from("\n");
  let open_brace_buf = Buffer.from("{\n");
  let close_brace_buf = Buffer.from("}");

  /**
   * Atomically replaces `arg1_target_path` with `arg0_source_path`, falling back to async copy + unlink across volumes (`EXDEV`).
   *
   * @param {string} arg0_source_path
   * @param {string} arg1_target_path
   *
   * @returns {Promise<void>}
   */
  NDJSON.atomicMoveFile = async function (arg0_source_path, arg1_target_path) {
    //Convert from parameters
    let source_path = arg0_source_path;
    let target_path = arg1_target_path;

    //Declare local instance variables
    let attempts = 0;

    while (attempts < 10) {
      try {
        await fs.promises.rename(source_path, target_path);
        return;
      } catch (err) {
        if (err.code === "EXDEV") {
          await fs.promises.copyFile(source_path, target_path);
          try {
            await fs.promises.unlink(source_path);
          } catch (unlink_err) {}
          return;
        }
        attempts++;
        if (attempts >= 10) throw err;
        await new Promise((resolve) => setTimeout(resolve, 50));
      }
    }
  };


  /**
   * Compiles all NDJSON shard files and `metadata.json` into a `.naissance` file off the main thread using 4MB buffered streams and atomic renames.
   *
   * @param {Object} [arg0_options]
   *  @param {string} arg0_options.folder_path
   *  @param {number} arg0_options.pool_length
   *  @param {string} arg0_options.target_folder_path
   *  @param {string} arg0_options.target_path
   *
   * @returns {Promise<string>}
   */
  NDJSON.compileSavefile = async function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let bak_path = `${options.target_path}.bak`;
    let folder_path = options.folder_path;
    let has_written_entry = false;
    let metadata_path = path.join(folder_path, "metadata.json");
    let pool_length = Math.max(1, options.pool_length || 1);
    let target_dir = path.dirname(options.target_path);
    let target_folder_path = options.target_folder_path;
    let target_path = options.target_path;
    let tmp_path = `${target_path}.tmp_${Date.now()}_${Math.floor(Math.random()*1000)}`;

    //Guard clause if cache directory does not exist
    if (!folder_path || !fs.existsSync(folder_path))
      return target_path;

    if (!fs.existsSync(target_dir))
      await fs.promises.mkdir(target_dir, { recursive: true });

    let fh_out = await fs.promises.open(tmp_path, "w");
    let out_buf = Buffer.allocUnsafe(4*1024*1024 + 65536);
    let out_pos = 0;

    let flushOut = async function () {
      if (out_pos > 0) {
        let written = 0;
        while (written < out_pos) {
          let res = await fh_out.write(out_buf, written, out_pos - written);
          written += res.bytesWritten;
        }
        out_pos = 0;
      }
    };

    let appendBuf = async function (arg0_buf) {
      let buf = arg0_buf;
      if (buf.length === 0) return;
      if (buf.length > out_buf.length) {
        await flushOut();
        let written = 0;
        while (written < buf.length) {
          let res = await fh_out.write(buf, written, buf.length - written);
          written += res.bytesWritten;
        }
        return;
      }
      if (out_pos + buf.length > out_buf.length)
        await flushOut();
      buf.copy(out_buf, out_pos);
      out_pos += buf.length;
    };

    try {
      await appendBuf(open_brace_buf);

      //1. Write map_settings metadata without trailing comma
      if (fs.existsSync(metadata_path)) {
        let meta_raw = (await fs.promises.readFile(metadata_path, "utf8")).trim();
        if (meta_raw.length > 0) {
          await appendBuf(Buffer.from(`"map_settings":${meta_raw}`));
          has_written_entry = true;
        }
      }

      //2. Stream all partition shards using SIMD Buffer.indexOf(10) and 4MB coalesced buffer writes
      for (let i = 0; i < pool_length; i++) {
        let page_file = path.join(folder_path, `partition_${i}.ndjson`);
        if (!fs.existsSync(page_file)) {
          let legacy_file = path.join(folder_path, `${i}.ndjson`);
          if (fs.existsSync(legacy_file)) page_file = legacy_file;
        }
        if (!fs.existsSync(page_file)) continue;

        let leftover = null;
        let rs = fs.createReadStream(page_file, { highWaterMark: 4*1024*1024 });

        for await (let chunk of rs) {
          let pos = 0;

          while (pos < chunk.length) {
            let nl_idx = chunk.indexOf(10, pos);
            if (nl_idx === -1) break;

            let line_end = (nl_idx > pos && chunk[nl_idx - 1] === 13) ? nl_idx - 1 : nl_idx;
            if (leftover !== null) {
              let tail_slice = chunk.subarray(pos, line_end);
              let full_line = (tail_slice.length > 0) ? Buffer.concat([leftover, tail_slice]) : leftover;
              leftover = null;
              if (full_line.length > 0 && full_line[full_line.length - 1] === 13)
                full_line = full_line.subarray(0, full_line.length - 1);
              if (full_line.length > 0) {
                if (has_written_entry) await appendBuf(comma_newline_buf);
                has_written_entry = true;
                await appendBuf(full_line);
              }
            } else if (line_end > pos) {
              let line_len = line_end - pos;
              let needed = line_len + (has_written_entry ? 2 : 0);
              if (needed <= out_buf.length) {
                if (out_pos + needed > out_buf.length)
                  await flushOut();
                if (has_written_entry) {
                  out_buf[out_pos] = 44;
                  out_buf[out_pos + 1] = 10;
                  out_pos += 2;
                }
                has_written_entry = true;
                chunk.copy(out_buf, out_pos, pos, line_end);
                out_pos += line_len;
              } else {
                if (has_written_entry) await appendBuf(comma_newline_buf);
                has_written_entry = true;
                await appendBuf(chunk.subarray(pos, line_end));
              }
            }
            pos = nl_idx + 1;
          }

          if (pos < chunk.length) {
            let rem = chunk.subarray(pos);
            leftover = (leftover !== null) ? Buffer.concat([leftover, rem]) : Buffer.from(rem);
          }
        }

        if (leftover !== null && leftover.length > 0) {
          if (leftover[leftover.length - 1] === 13)
            leftover = leftover.subarray(0, leftover.length - 1);
          if (leftover.length > 0) {
            if (has_written_entry) await appendBuf(comma_newline_buf);
            has_written_entry = true;
            await appendBuf(leftover);
          }
        }
      }

      if (has_written_entry)
        await appendBuf(newline_buf);
      await appendBuf(close_brace_buf);
      await flushOut();
      await fh_out.close();
      fh_out = null;

      //3. Verify head and tail JSON boundaries asynchronously
      let stat = await fs.promises.stat(tmp_path);
      let fh = await fs.promises.open(tmp_path, "r");
      let head_len = Math.min(50, stat.size);
      let tail_len = Math.min(50, stat.size);
      let head_buf = Buffer.alloc(head_len);
      let tail_buf = Buffer.alloc(tail_len);

      try {
        await fh.read(head_buf, 0, head_len, 0);
        await fh.read(tail_buf, 0, tail_len, Math.max(0, stat.size - tail_len));
      } finally {
        await fh.close();
      }

      let head_str = head_buf.toString("utf8");
      let tail_str = tail_buf.toString("utf8");
      if (!head_str.startsWith("{") || !tail_str.trim().endsWith("}")) {
        try { await fs.promises.unlink(tmp_path); } catch (e) {}
        console.error(`[NDJSON.compileSavefile] Invalid JSON boundaries in ${tmp_path}`);
        return target_path;
      }

      //4. Atomic O(1) backup and target replacement (zero synchronous file copies)
      let moved_to_bak = false;
      if (fs.existsSync(target_path)) {
        try {
          if (fs.existsSync(bak_path))
            await fs.promises.unlink(bak_path);
          await NDJSON.atomicMoveFile(target_path, bak_path);
          moved_to_bak = true;
        } catch (bak_err) {
          try { await fs.promises.copyFile(target_path, bak_path); } catch (e) {}
        }
      }

      try {
        await NDJSON.atomicMoveFile(tmp_path, target_path);
      } catch (replace_err) {
        if (moved_to_bak && !fs.existsSync(target_path) && fs.existsSync(bak_path)) {
          try { await NDJSON.atomicMoveFile(bak_path, target_path); } catch (e) {}
        }
        throw replace_err;
      }

      //5. Align cache timestamps (or clone cache directory on Save-As) so subsequent loads reuse cache
      let now = new Date();
      if (target_folder_path && path.resolve(target_folder_path) !== path.resolve(folder_path)) {
        try {
          await fs.promises.mkdir(target_folder_path, { recursive: true });
          let cache_entries = await fs.promises.readdir(folder_path);
          for (let i = 0; i < cache_entries.length; i++) {
            let entry_name = cache_entries[i];
            if (entry_name === "metadata.json" || (entry_name.startsWith("partition_") && entry_name.endsWith(".ndjson")))
              await fs.promises.copyFile(path.join(folder_path, entry_name), path.join(target_folder_path, entry_name));
          }
          let target_meta = path.join(target_folder_path, "metadata.json");
          if (fs.existsSync(target_meta))
            await fs.promises.utimes(target_meta, now, now);
        } catch (cache_err) {
          console.warn("[NDJSON.compileSavefile] Could not mirror cache for Save-As target:", cache_err);
        }
      } else if (fs.existsSync(metadata_path)) {
        try { await fs.promises.utimes(metadata_path, now, now); } catch (e) {}
      }
    } catch (err) {
      if (fh_out) {
        try { await fh_out.close(); } catch (e) {}
      }
      if (fs.existsSync(tmp_path)) {
        try { await fs.promises.unlink(tmp_path); } catch (e) {}
      }
      throw err;
    }

    //Return statement
    return target_path;
  };


  /**
   * Streams a `.naissance` JSON savefile and partitions its top-level entries across NDJSON shard files and `metadata.json`.
   *
   * @param {Object} [arg0_options]
   *  @param {string} arg0_options.file_path
   *  @param {string} arg0_options.folder_path
   *  @param {Function} arg0_options.get_worker_id
   *  @param {number} arg0_options.pool_length
   *
   * @returns {Promise<void>}
   */
  NDJSON.partitionSavefileToCache = async function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let depth = 0;
    let file_path = options.file_path;
    let folder_path = options.folder_path;
    let get_worker_id = options.get_worker_id;
    let in_string = false;
    let is_escaped = false;
    let key_chunks = [];
    let key_start = -1;
    let pool_length = Math.max(1, options.pool_length || 1);
    let root_opened = false;
    let state = "SEEK_KEY";
    let val_chunks = [];
    let val_start = -1;
    let write_streams = {};

    if (!fs.existsSync(folder_path)) {
      fs.mkdirSync(folder_path, { recursive: true });
    } else {
      let old_files = fs.readdirSync(folder_path);
      for (let i = 0; i < old_files.length; i++) {
        let ofile = old_files[i];
        if (ofile.startsWith("partition_") && ofile.endsWith(".ndjson")) {
          try { fs.unlinkSync(path.join(folder_path, ofile)); } catch (e) {}
        }
      }
    }

    for (let i = 0; i < pool_length; i++)
      write_streams[i] = fs.createWriteStream(path.join(folder_path, `partition_${i}.ndjson`), { highWaterMark: 1024*1024 });

    let metadata_ws = fs.createWriteStream(path.join(folder_path, "metadata.json"));

    let writeEntry = async function (arg0_key, arg1_val_str) {
      let key = arg0_key;
      let val_str = arg1_val_str;
      if (key === "map_settings") {
        if (!metadata_ws.write(val_str))
          await new Promise((r) => metadata_ws.once("drain", r));
      } else {
        if (val_str.indexOf("\n") !== -1 || val_str.indexOf("\r") !== -1)
          val_str = JSON.stringify(JSON.parse(val_str));
        let wid = get_worker_id(key, pool_length);
        if (!write_streams[wid].write(`"${key}":${val_str}\n`))
          await new Promise((r) => write_streams[wid].once("drain", r));
      }
    };

    let rs = fs.createReadStream(file_path, { highWaterMark: 4*1024*1024 });

    for await (let chunk of rs) {
      let str = (typeof chunk === "string") ? chunk : chunk.toString("utf8");
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
              let key = key_chunks.join("");
              let val = val_chunks.join("").trim();
              state = "SEEK_KEY";
              key_chunks = [];
              val_chunks = [];
              await writeEntry(key, val);
            } else if (depth === 0) {
              break;
            }
          } else if (ch === "," && depth === 1) {
            if (val_start !== -1) {
              val_chunks.push(str.slice(val_start, i));
              val_start = -1;
            }
            let key = key_chunks.join("");
            let val = val_chunks.join("").trim();
            state = "SEEK_KEY";
            key_chunks = [];
            val_chunks = [];
            await writeEntry(key, val);
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

    metadata_ws.end();
    await new Promise((r) => metadata_ws.on("finish", r));

    for (let i = 0; i < pool_length; i++) {
      write_streams[i].end();
      await new Promise((r) => write_streams[i].on("finish", r));
    }
  };


  /**
   * Streams an NDJSON partition shard through a binary chunk scanner, updating, deleting or appending targeted keys without UTF-8 decoding untouched lines.
   *
   * @param {string} arg0_page_file
   * @param {Function} arg1_get_updated_value
   * @param {Object} [arg2_options]
   *
   * @returns {Promise<void>}
   */
  NDJSON.updateShardFile = async function (arg0_page_file, arg1_get_updated_value, arg2_options) {
    //Convert from parameters
    let page_file = arg0_page_file;
    let get_updated_value = arg1_get_updated_value;
    let options = (arg2_options) ? arg2_options : {};

    //Declare local instance variables
    let dir = path.dirname(page_file);
    let target_id = (options.target_id !== undefined && options.target_id !== null) ? String(options.target_id) : null;
    let target_keys = options.target_keys || null;
    let tmp_file = `${page_file}.tmp_${Date.now()}_${Math.floor(Math.random()*1000)}`;
    let updated = false;

    if (!fs.existsSync(dir))
      await fs.promises.mkdir(dir, { recursive: true });

    let fh_out = await fs.promises.open(tmp_file, "w");

    let writeRawBuf = async function (arg0_buf, arg1_offset, arg2_len) {
      let buf = arg0_buf;
      let offset = (arg1_offset !== undefined) ? arg1_offset : 0;
      let total = (arg2_len !== undefined) ? arg2_len : buf.length;
      let written = 0;
      while (written < total) {
        let res = await fh_out.write(buf, offset + written, total - written);
        written += res.bytesWritten;
      }
    };

    let extractKeyFromSpan = function (arg0_buf, arg1_start, arg2_end) {
      let buf = arg0_buf;
      let idx = arg1_start;
      let end = arg2_end;
      while (idx < end && buf[idx] <= 32) idx++;
      if (idx < end && buf[idx] === 34) {
        let quote_end = buf.indexOf(34, idx + 1);
        if (quote_end > idx + 1 && quote_end < end) {
          let colon_idx = buf.indexOf(58, quote_end + 1);
          if (colon_idx > quote_end && colon_idx < end)
            return { colon_idx: colon_idx - arg1_start, key: buf.toString("utf8", idx + 1, quote_end), start_idx: idx };
        }
      }
      return null;
    };

    let processSingleLineBuf = async function (arg0_line_buf) {
      let line_buf = arg0_line_buf;
      let end_idx = (line_buf.length > 0 && line_buf[line_buf.length - 1] === 13) ? line_buf.length - 1 : line_buf.length;
      if (end_idx === 0) return;

      let parsed = extractKeyFromSpan(line_buf, 0, end_idx);
      if (parsed !== null) {
        let key = parsed.key;
        let is_targeted = (target_id === null || key === target_id) && (target_keys === null || target_keys.has(key));
        if (is_targeted) {
          let new_value = get_updated_value(key, parsed.colon_idx);
          if (new_value !== undefined) {
            updated = true;
            if (new_value !== null)
              await writeRawBuf(Buffer.from(`"${key}":${JSON.stringify(new_value)}\n`));
            return;
          }
        }
      }
      await writeRawBuf(line_buf, parsed ? parsed.start_idx : 0, end_idx - (parsed ? parsed.start_idx : 0));
      await writeRawBuf(newline_buf);
    };

    try {
      if (fs.existsSync(page_file)) {
        let leftover = null;
        let rs = fs.createReadStream(page_file, { highWaterMark: 4*1024*1024 });

        for await (let chunk of rs) {
          let passthrough_start = -1;
          let pos = 0;

          while (pos < chunk.length) {
            let nl_idx = chunk.indexOf(10, pos);
            if (nl_idx === -1) break;

            if (leftover !== null) {
              if (passthrough_start !== -1 && passthrough_start < pos) {
                await writeRawBuf(chunk, passthrough_start, pos - passthrough_start);
                passthrough_start = -1;
              }
              let full_line = Buffer.concat([leftover, chunk.subarray(pos, nl_idx)]);
              leftover = null;
              await processSingleLineBuf(full_line);
              pos = nl_idx + 1;
              continue;
            }

            let end_idx = (nl_idx > pos && chunk[nl_idx - 1] === 13) ? nl_idx - 1 : nl_idx;
            let parsed = (end_idx > pos) ? extractKeyFromSpan(chunk, pos, end_idx) : null;
            let key = parsed ? parsed.key : null;
            let is_hit = (key !== null) &&
              ((target_id !== null && key === target_id) ||
               (target_keys !== null && target_keys.has(key)) ||
               (target_id === null && target_keys === null));

            if (!is_hit) {
              if (passthrough_start === -1 && end_idx > pos)
                passthrough_start = pos;
            } else {
              if (passthrough_start !== -1 && passthrough_start < pos) {
                await writeRawBuf(chunk, passthrough_start, pos - passthrough_start);
                passthrough_start = -1;
              }
              await processSingleLineBuf(chunk.subarray(pos, nl_idx));
            }
            pos = nl_idx + 1;
          }

          if (passthrough_start !== -1 && passthrough_start < pos)
            await writeRawBuf(chunk, passthrough_start, pos - passthrough_start);

          if (pos < chunk.length) {
            let rem = chunk.subarray(pos);
            leftover = (leftover !== null) ? Buffer.concat([leftover, rem]) : Buffer.from(rem);
          }
        }

        if (leftover !== null && leftover.length > 0)
          await processSingleLineBuf(leftover);
      }

      let extra_appends = get_updated_value(null, null, updated);
      if (extra_appends) {
        let append_keys = Object.keys(extra_appends);
        for (let i = 0; i < append_keys.length; i++) {
          let k = append_keys[i];
          let val = extra_appends[k];
          if (val !== null && val !== undefined)
            await writeRawBuf(Buffer.from(`"${k}":${JSON.stringify(val)}\n`));
        }
      }

      await fh_out.close();
      fh_out = null;

      await NDJSON.atomicMoveFile(tmp_file, page_file);
    } catch (err) {
      if (fh_out) {
        try { await fh_out.close(); } catch (e) {}
      }
      if (fs.existsSync(tmp_file)) {
        try { await fs.promises.unlink(tmp_file); } catch (e) {}
      }
      throw err;
    }
  };
}
