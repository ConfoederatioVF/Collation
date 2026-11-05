//Import libraries
let fs = require("node:fs");
let path = require("node:path");

/**
 * Decodes common HTML entities into their unicode characters.
 *
 * @param {string} arg0_str
 *
 * @returns {string}
 */
function decodeHtmlEntities (arg0_str) {
  //Convert from parameters
  let str = arg0_str;

  //Guard clauses
  if (!str) return "";

  //Return statement
  return str
    .replace(/&#160;|&nbsp;/gi, " ")
    .replace(/&#8211;|&ndash;/gi, "–")
    .replace(/&#8212;|&mdash;/gi, "—")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&#91;/gi, "[")
    .replace(/&#93;/gi, "]")
    .replace(/&#x[0-9a-fA-F]+;/gi, "")
    .replace(/&#\d+;/g, "")
    .replace(/\uFEFF/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Extracts and formats infobox rows from Wikipedia section 0 HTML as semicolon-separated tags.
 *
 * @param {string} arg0_html
 *
 * @returns {string}
 */
function extractInfoboxTags (arg0_html) {
  //Convert from parameters
  let html = arg0_html;

  //Guard clauses
  if (!html) return "";

  //Declare local instance variables
  let rows = [];
  let seen = new Set();
  let skip_labels = [
    "anthem", "audio", "calling code", "cctld", "coat of arms", "coordinates",
    "criteria", "demonym (s)", "driving side", "emblem", "flag", "globe",
    "image", "inscription", "insignia", "internet tld", "iso 3166 code",
    "location", "map", "motto", "reference", "seal", "symbol", "website"
  ];
  let tableMatch = html.match(/<table[^>]*class="[^"]*infobox[^"]*"[^>]*>[\s\S]*?<\/table>/i);
  let tags = [];

  //Guard clauses
  if (!tableMatch) return "";

  let table = tableMatch[0];
  table = table.replace(/<style[\s\S]*?<\/style>/gi, "");
  table = table.replace(/<script[\s\S]*?<\/script>/gi, "");
  table = table.replace(/<sup[^>]*>[\s\S]*?<\/sup>/gi, "");
  table = table.replace(/<span[^>]*class="[^"]*(?:geo|latitude|longitude|nowrap)[^"]*"[^>]*>[\s\S]*?<\/span>/gi, "");
  table = table.replace(/<audio[\s\S]*?<\/audio>/gi, "");

  rows = table.match(/<tr[^>]*>[\s\S]*?<\/tr>/gi) || [];

  for (let i = 0; i < rows.length; i++) {
    let r = rows[i];
    let tdMatch = r.match(/<td[^>]*>([\s\S]*?)<\/td>/i);
    let thMatch = r.match(/<th[^>]*>([\s\S]*?)<\/th>/i);

    if (thMatch && tdMatch) {
      let label = decodeHtmlEntities(thMatch[1].replace(/<[^>]+>/g, " "));
      let value = decodeHtmlEntities(tdMatch[1].replace(/<[^>]+>/g, " "));

      //Strip citation brackets like [ 1 ], [ a ]
      label = label.replace(/\[\s*[a-z0-9]+\s*\]/gi, "").trim();
      value = value.replace(/\[\s*[a-z0-9]+\s*\]/gi, "").trim();

      //Clean leading bullet characters
      label = label.replace(/^[•\-\*\u2022]\s*/, "").trim();
      value = value.replace(/^[•\-\*\u2022]\s*/, "").trim();

      //Clean coordinate degrees and coordinate slashes
      value = value.replace(/\d+°\d+[′'].*?(\/|;|$)/g, "").replace(/\/\s*\/\s*[\d\.\s;\-]+/g, "").trim();

      let label_lower = label.toLowerCase();
      if (skip_labels.some((s) => label_lower === s || label_lower.startsWith(s))) continue;

      if (label && value && label.length < 50 && value.length < 250 && value !== "—" && value !== "none" && value !== "undefined") {
        let tag = `${label}: ${value}`;
        if (!seen.has(tag)) {
          seen.add(tag);
          tags.push(tag);
        }
      }
    }
  }

  //Return statement - limit to at most 18 informative tags to keep description concise
  return tags.slice(0, 18).join("; ");
}

/**
 * Formats a brief 1-3 sentence summary based on Wikipedia extract and polity metadata.
 *
 * @param {string} arg0_extract
 * @param {string} arg1_name
 * @param {string} arg2_fallback_desc
 *
 * @returns {string}
 */
function formatBriefSummary (arg0_extract, arg1_name, arg2_fallback_desc) {
  //Convert from parameters
  let extract = arg0_extract;
  let fallback_desc = arg2_fallback_desc;
  let name = arg1_name;

  //Guard clauses
  if (!extract) {
    if (fallback_desc && fallback_desc.length > 5) return fallback_desc;
    return `${name}.`;
  }

  //Declare local instance variables
  let clean = decodeHtmlEntities(extract)
    .replace(/\[\s*[a-z0-9]+\s*\]/gi, "")
    .replace(/\s+/g, " ")
    .trim();
  let sentences = clean.match(/[^.!?]+[.!?]+(\s|$)/g) || [clean];
  let summary = "";

  sentences = sentences.map((s) => s.trim()).filter(Boolean);

  for (let i = 0; i < sentences.length; i++) {
    let s = sentences[i];
    if ((summary + " " + s).trim().length <= 350 || !summary) {
      summary = (summary ? summary + " " : "") + s;
    } else {
      break;
    }
  }

  //If polity has a specific formal qualifier (e.g. military occupation, dynasty, or distinctive title) not in summary opening
  let clean_name_base = name.split("(")[0].trim().toLowerCase();
  let summary_lower = summary.toLowerCase();

  if (!summary_lower.includes(clean_name_base) && !summary.startsWith(name)) {
    //Check if name ends with period
    let prefix = name.endsWith(".") ? name : `${name}.`;
    summary = `${prefix} ${summary}`;
  }

  //Return statement
  return summary.trim();
}

/**
 * Reads all 16 context TSV files, parses Wikipedia cache data into regenerated descriptions,
 * and writes temp_jobs/polity_descriptions_<0..15>.txt.
 *
 * @returns {Promise<void>}
 */
async function A_generateDescriptions () {
  //Declare local instance variables
  let cache_file = path.resolve(process.cwd(), "tests/wiki_cache.json");
  let temp_jobs_dir = path.resolve(process.cwd(), "temp_jobs");
  let tests_dir = path.resolve(process.cwd(), "tests");
  let total_polities = 0;
  let with_tags_count = 0;

  if (!fs.existsSync(cache_file)) {
    console.error("Cache file does not exist! Please run tests/fetch_wiki_cache.js first.");
    process.exit(1);
  }

  let wiki_cache = JSON.parse(fs.readFileSync(cache_file, "utf8"));
  console.log(`Loaded wiki cache with ${Object.keys(wiki_cache).length} entries.`);

  for (let chunk_idx = 0; chunk_idx < 16; chunk_idx++) {
    let chunk_entries = [];
    let tsv_path = path.join(tests_dir, `polity_descriptions_context_${chunk_idx}.tsv`);
    let txt_path = path.join(temp_jobs_dir, `polity_descriptions_${chunk_idx}.txt`);

    if (!fs.existsSync(tsv_path)) {
      console.error(`Missing context TSV: ${tsv_path}`);
      process.exit(1);
    }

    let lines = fs.readFileSync(tsv_path, "utf8").trim().split(/\r?\n/).slice(1);

    for (let i = 0; i < lines.length; i++) {
      let parts = lines[i].split("\t");
      let control_type = parts[3];
      let fallback_desc = parts[7] || "";
      let id = parts[0];
      let label = parts[5];
      let link = parts[6];
      let name = parts[1];
      let parent = parts[4];
      let span = parts[2];

      let entry = (link && wiki_cache[link]) ? wiki_cache[link] : null;
      let extract = entry?.extract || "";
      let html = entry?.html || "";

      let summary = formatBriefSummary(extract, name, fallback_desc);
      let tags = extractInfoboxTags(html);

      let full_desc = summary;
      if (tags) {
        full_desc = `${summary}\n\n${tags}`;
        with_tags_count++;
      }

      chunk_entries.push(`${id}: ${full_desc}`);
      total_polities++;
    }

    let output_text = chunk_entries.join("\n\n") + "\n";
    fs.writeFileSync(txt_path, output_text, "utf8");
    console.log(`Chunk ${chunk_idx}: ${lines.length} polities written to ${txt_path}`);
  }

  console.log(`Successfully generated descriptions for ${total_polities} polities across 16 chunks (${with_tags_count} with infobox tags).`);
}

A_generateDescriptions().catch(console.error);

