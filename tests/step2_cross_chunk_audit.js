//Import libraries
let fs = require("node:fs");
let path = require("node:path");

/**
 * Audits all 8 edited polity_names_<#>.txt chunks against polity_context_<#>.tsv
 * for structural integrity, formal naming rules, military occupation suffixes,
 * leftover disambiguators, acronyms, inverted titles, and cross-chunk consistency.
 */
function A_auditChunks () {
  //Declare local instance variables
  let acronym_flags = [];
  let all_records = [];
  let by_link = new Map();
  let format_errors = [];
  let inverted_flags = [];
  let occupation_flags = [];
  let ordinal_flags = [];
  let paren_flags = [];
  let temp_jobs_dir = path.resolve(process.cwd(), "temp_jobs");
  let tests_dir = path.resolve(process.cwd(), "tests");
  let total_changed = 0;
  let typo_flags = [];

  for (let i = 0; i < 8; i++) {
    let ctx_path = path.join(tests_dir, `polity_context_${i}.tsv`);
    let txt_path = path.join(temp_jobs_dir, `polity_names_${i}.txt`);

    if (!fs.existsSync(txt_path)) {
      format_errors.push(`Missing chunk file: ${txt_path}`);
      continue;
    }

    let ctx_lines = fs.readFileSync(ctx_path, "utf8").trimEnd().split(/\r?\n/).slice(1);
    let txt_lines = fs.readFileSync(txt_path, "utf8").trimEnd().split(/\r?\n/);

    if (ctx_lines.length !== txt_lines.length) {
      format_errors.push(`Chunk ${i}: line count mismatch (expected ${ctx_lines.length}, got ${txt_lines.length})`);
    }

    let max_len = Math.min(ctx_lines.length, txt_lines.length);
    for (let x = 0; x < max_len; x++) {
      let ctx_parts = ctx_lines[x].split("\t");
      let expected_id = ctx_parts[0];
      let orig_name = ctx_parts[1];
      let span = ctx_parts[2];
      let control_type = ctx_parts[3];
      let parent = ctx_parts[4];
      let label = ctx_parts[5];
      let link = ctx_parts[6];
      let desc = ctx_parts[7] || "";

      let line = txt_lines[x];
      let sep_idx = line.indexOf(": ");
      if (sep_idx === -1) {
        format_errors.push(`Chunk ${i} line ${x + 1}: missing ': ' separator -> ${line}`);
        continue;
      }

      let actual_id = line.slice(0, sep_idx);
      let new_name = line.slice(sep_idx + 2);

      if (actual_id !== expected_id) {
        format_errors.push(`Chunk ${i} line ${x + 1}: ID mismatch (expected ${expected_id}, got ${actual_id})`);
      }
      if (new_name.length === 0 || new_name.trim() !== new_name || /\s{2,}/.test(new_name)) {
        format_errors.push(`Chunk ${i} ID ${actual_id}: whitespace/empty issue -> "${new_name}"`);
      }

      if (new_name !== orig_name) total_changed++;

      let rec = {
        chunk: i,
        control_type,
        desc,
        id: actual_id,
        label,
        link,
        new_name,
        orig_name,
        parent,
        span
      };
      all_records.push(rec);

      if (link) {
        if (!by_link.has(link)) by_link.set(link, []);
        by_link.get(link).push(rec);
      }

      //1. Check parentheticals
      let parens = [...new_name.matchAll(/\(([^)]*)\)/g)].map((m) => m[1]);
      for (let y = 0; y < parens.length; y++) {
        if (parens[y] !== "Military Occupation" && parens[y] !== "Keeling") {
          paren_flags.push(`Chunk ${i} ID ${actual_id}: "${orig_name}" -> "${new_name}" [${span}]`);
        }
      }
      if ((new_name.match(/\(/g) || []).length !== (new_name.match(/\)/g) || []).length) {
        format_errors.push(`Chunk ${i} ID ${actual_id}: unbalanced parentheses -> "${new_name}"`);
      }

      //2. Check military occupations
      let had_occ_in_orig = /occupation/i.test(orig_name);
      let is_ct_occ = (control_type === "Military Occupation");
      if (had_occ_in_orig && !new_name.endsWith(" (Military Occupation)")) {
        occupation_flags.push(`Chunk ${i} ID ${actual_id} (lost suffix): "${orig_name}" -> "${new_name}" [ct=${control_type}]`);
      } else if (is_ct_occ && !new_name.endsWith(" (Military Occupation)") && !/Administration|Operational Zone|Military Territory|Military Commander|Governorate/i.test(new_name)) {
        occupation_flags.push(`Chunk ${i} ID ${actual_id} (ct=Military Occupation without suffix): "${orig_name}" -> "${new_name}"`);
      }

      //3. Check acronyms / short uppercase codes
      if (/^(?:[A-Z0-9&/-]{2,7}|USA|USSR|PRC|ROC|DRC|UAE|UK|CAR)$/.test(new_name) || /\b(USA|USSR|PRC|AFDL|AQAP|ISIL|ISIS|FARC|UNITA|MNLA|SPLM|SPLA)\b/.test(new_name)) {
        acronym_flags.push(`Chunk ${i} ID ${actual_id}: "${orig_name}" -> "${new_name}" [${span}] desc=${desc.slice(0, 80)}`);
      }

      //4. Check informal regime names / ordinals / tetrarchy colons
      if (/\b(First|Second|Third|Fourth|Fifth)\s+.*(Republic|Empire)\b/i.test(new_name) || /\b(Weimar Republic|Nazi Germany|Vichy France)\b/i.test(new_name) || /:\s*(East|West|Africa)\b/.test(new_name)) {
        ordinal_flags.push(`Chunk ${i} ID ${actual_id}: "${orig_name}" -> "${new_name}" [${span}]`);
      }

      //5. Check inverted feudal titles
      if (/\b(Prince-Bishopric|Archbishopric|Bishopric|Duchy|Grand Duchy|Landgraviate|Margraviate|County|Burgraviate|Lordship|Barony|Marquisate|Patriarchate|Provostry|Imperial Monastery)$/i.test(new_name)) {
        inverted_flags.push(`Chunk ${i} ID ${actual_id}: "${orig_name}" -> "${new_name}" [${span}]`);
      }

      //6. Check common Phersu typos
      if (/Governatorate|Civili\b|Trisana|Enre Rios|Const\. County|Military occupation|militarly/i.test(new_name)) {
        typo_flags.push(`Chunk ${i} ID ${actual_id}: "${orig_name}" -> "${new_name}"`);
      }
    }
  }

  //7. Cross-chunk consistency for shared Wikipedia links across different chunks
  let link_divergences = [];
  for (let [link, recs] of by_link.entries()) {
    let non_occ = recs.filter((r) => r.control_type !== "Military Occupation" && !r.new_name.endsWith("(Military Occupation)"));
    let chunks_set = new Set(non_occ.map((r) => r.chunk));
    let names_set = new Set(non_occ.map((r) => r.new_name));
    if (chunks_set.size > 1 && names_set.size > 1 && non_occ.length <= 6) {
      link_divergences.push({
        entries: non_occ.map((r) => `c${r.chunk}#${r.id}[${r.span.slice(0, 4)}..]: "${r.orig_name}" -> "${r.new_name}"`),
        link
      });
    }
  }

  console.log(`=== AUDIT SUMMARY ===`);
  console.log(`Total records audited: ${all_records.length} (renamed: ${total_changed})`);
  console.log(`Format errors: ${format_errors.length}`);
  for (let e of format_errors.slice(0, 30)) console.log(`  [FMT] ${e}`);
  console.log(`Parenthetical flags: ${paren_flags.length}`);
  for (let e of paren_flags.slice(0, 50)) console.log(`  [PAREN] ${e}`);
  console.log(`Occupation flags: ${occupation_flags.length}`);
  for (let e of occupation_flags.slice(0, 50)) console.log(`  [OCC] ${e}`);
  console.log(`Acronym flags: ${acronym_flags.length}`);
  for (let e of acronym_flags.slice(0, 50)) console.log(`  [ACR] ${e}`);
  console.log(`Ordinal/Regime flags: ${ordinal_flags.length}`);
  for (let e of ordinal_flags.slice(0, 50)) console.log(`  [ORD] ${e}`);
  console.log(`Inverted title flags: ${inverted_flags.length}`);
  for (let e of inverted_flags.slice(0, 50)) console.log(`  [INV] ${e}`);
  console.log(`Typo flags: ${typo_flags.length}`);
  for (let e of typo_flags.slice(0, 50)) console.log(`  [TYPO] ${e}`);
  console.log(`Cross-chunk link divergences (<=6 entries): ${link_divergences.length}`);
  for (let d of link_divergences.slice(0, 60)) {
    console.log(`  [LINK] ${d.link}\n    ${d.entries.join("\n    ")}`);
  }
}

A_auditChunks();

