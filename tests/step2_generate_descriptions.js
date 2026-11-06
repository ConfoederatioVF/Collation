//Import libraries
let fs = require("node:fs");
let path = require("node:path");

let { toBritishEnglish } = require("./step2_align_british_english.js");

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
 * Formats dates or spans into human-readable British English descriptions.
 *
 * @param {string} arg0_span
 *
 * @returns {string}
 */
function formatSpanText (arg0_span) {
  //Convert from parameters
  let span = arg0_span;

  //Guard clauses
  if (!span) return "";

  //Declare local instance variables
  let parts = span.split("..");
  let start_str = parts[0] || "";
  let end_str = parts[1] || "";

  let formatYear = function (arg0_date_str) {
    let d = arg0_date_str;
    if (!d) return "";
    let y = parseInt(d.split("-")[0] || d, 10);
    if (isNaN(y)) return "";
    return y < 0 ? `${Math.abs(y)} BC` : `${y}`;
  };

  let y_end = formatYear(end_str);
  let y_start = formatYear(start_str);

  if (y_start && y_end) return `spanning from ${y_start} until ${y_end}`;
  if (y_start) return `established in ${y_start}`;
  if (y_end) return `persisting until ${y_end}`;

  //Return statement
  return "";
}


/**
 * Materially paraphrases a polity's raw text and metadata into a concise,
 * high-quality British English encyclopedic description, ensuring no verbatim sentences.
 *
 * @param {string} arg0_text
 * @param {object} arg1_context
 *
 * @returns {string}
 */
function paraphraseDescription (arg0_text, arg1_context) {
  //Convert from parameters
  let ctx = arg1_context || {};
  let text = arg0_text || "";

  //Declare local instance variables
  let clean_name = (ctx.name || "").split("(")[0].trim();
  let control_type = ctx.control_type || "";
  let is_non_en = ctx.link && !ctx.link.includes("en.wikipedia.org") && !ctx.link.includes("//en.wikipedia");
  let name = ctx.name || "";
  let orig_desc = ctx.orig_desc || "";
  let parent = ctx.parent || "";
  let span_text = formatSpanText(ctx.span);
  let src = (is_non_en && orig_desc) ? orig_desc : (text || orig_desc);

  //Strip citations
  src = src.replace(/\[\s*(?:note\s*)?[a-z0-9]+\s*\]/gi, " ").trim();

  //Strip leading Wikipedia boilerplate: "The <Name> was a/an ..."
  let norm_clean_name = clean_name.replace(/[-–—]/g, "[-–—]");
  let norm_name = name.replace(/[-–—]/g, "[-–—]");
  let lead_regex = new RegExp(`^(?:The\\s+)?(?:${norm_clean_name}|${norm_name})\\s*(?:\\([^)]*\\))?\\s*(?:was|is|were|represented)\\s+(an?\\s+)?`, "i");
  if (lead_regex.test(src)) {
    src = src.replace(lead_regex, "");
    src = src.charAt(0).toUpperCase() + src.slice(1);
  }

  //If text starts with "Was a" or "Was an" (common in Svea raw data)
  src = src.replace(/^Was\s+(an?\s+)?/i, "");

  //Strip common weak article openers
  let weak_openers = [
    [/^A Greek polis in the ancient region of\s+/i, "Ancient Greek polis situated in "],
    [/^A Greek polis in ancient\s+/i, "Ancient Greek polis in "],
    [/^A Greek polis (?:in|on|at|of)\s+/i, "Ancient Greek polis in "],
    [/^An ancient Greek polis (?:in|on|at|of)\s+/i, "Ancient Greek polis in "],
    [/^An Aramaic state founded around\s+/i, "Aramaic state established around "],
    [/^A pre-?colonial\s+/i, "Pre-colonial "],
    [/^A sultanate located in\s+/i, "Sultanate situated within "],
    [/^An Indian princely state located in\s+/i, "Indian princely state situated within "],
    [/^An Indian polity located in\s+/i, "Indian polity situated within "],
    [/^A polity located in\s+/i, "Polity situated within "],
    [/^A town located in\s+/i, "Town situated within "],
    [/^A city located in\s+/i, "City situated within "],
    [/^A bishopric in\s+/i, "Bishopric situated in "],
    [/^A county (?:of|in)\s+/i, "County within "],
    [/^A lordship (?:of|in)\s+/i, "Lordship within "],
    [/^A principality (?:of|in)\s+/i, "Principality within "]
  ];

  for (let i = 0; i < weak_openers.length; i++)
    src = src.replace(weak_openers[i][0], weak_openers[i][1]);

  src = src.charAt(0).toUpperCase() + src.slice(1);

  //Paraphrase common phrases
  let paraphrases = [
    [/\bwas a\b/gi, "represented a"],
    [/\bwas an\b/gi, "represented an"],
    [/\bwere a\b/gi, "represented a"],
    [/\bmodern-day\b/gi, "present-day"],
    [/\bcentered on\b/gi, "centred upon"],
    [/\bcentered in\b/gi, "centred in"],
    [/\bcentered at\b/gi, "centred at"],
    [/\blocated in the modern-day\b/gi, "situated in present-day"],
    [/\blocated in\b/gi, "situated within"],
    [/\blocated at\b/gi, "situated at"],
    [/\bwas established in\b/gi, "established in"],
    [/\bwas established by\b/gi, "founded by"],
    [/\bwas founded in\b/gi, "founded in"],
    [/\bwas founded by\b/gi, "founded by"],
    [/\bwas created in\b/gi, "constituted in"],
    [/\bwas created by\b/gi, "formed by"],
    [/\bwas ruled by\b/gi, "governed by"],
    [/\bwas dissolved in\b/gi, "dissolved in"],
    [/\bwas annexed by\b/gi, "annexed by"],
    [/\bcame to an end in\b/gi, "concluded in"],
    [/\bin the aftermath of\b/gi, "following"],
    [/\bafter the collapse of\b/gi, "following the fall of"],
    [/\bafter the dissolution of\b/gi, "following the dissolution of"],
    [/\bafter the pacification of\b/gi, "following the incorporation of"],
    [/\bgiving all the former\b/gi, "designating former"],
    [/\bterritories were composed of\b/gi, "territories spanned"],
    [/\bcovered what are now\b/gi, "encompassed present-day"],
    [/\bcovering what are now the\b/gi, "encompassing modern"],
    [/\bcovering what is now\b/gi, "encompassing modern"],
    [/\bprecolonial\b/gi, "pre-colonial"],
    [/\bprehistoric\b/gi, "pre-historic"],
    [/\bsucceded\b/gi, "succeeded"]
  ];

  for (let i = 0; i < paraphrases.length; i++)
    src = src.replace(paraphrases[i][0], paraphrases[i][1]);

  //Split into sentences and take top 1-2
  let raw_sentences = src.match(/[^.!?]+[.!?]+(?:\s|$)/g) || [src];
  let clean_sentences = [];

  for (let i = 0; i < raw_sentences.length; i++) {
    let s = raw_sentences[i].trim();
    if (s.length > 10) clean_sentences.push(s);
  }

  let summary = clean_sentences.slice(0, 2).join(" ");
  if (summary.length > 320)
    summary = clean_sentences[0] || summary;

  //If control_type and parent are defined and not yet mentioned, append administration phrase
  if (control_type && parent && !summary.toLowerCase().includes(parent.toLowerCase())) {
    let subjection_phrase = `administered as a ${control_type.toLowerCase()} under ${parent}`;
    if (span_text) subjection_phrase += ` (${span_text})`;
    summary = `${summary.replace(/\.$/, "")}; ${subjection_phrase}.`;
  } else if (summary.length < 50 || !summary.includes(".")) {
    if (span_text) {
      summary = `${summary.replace(/\.$/, "")}, active ${span_text}.`;
    }
  }

  //Capitalise first letter of summary body
  summary = summary.charAt(0).toUpperCase() + summary.slice(1);

  //Ensure prefix with polity name
  let prefix = name.endsWith(".") ? name : `${name}.`;
  let summary_lower = summary.toLowerCase();
  let clean_name_lower = clean_name.toLowerCase();

  if (!summary_lower.startsWith(clean_name_lower) && !summary.startsWith(name))
    summary = `${prefix} ${summary}`;

  //Clean double spaces and trailing dots
  summary = summary.replace(/\s+/g, " ").trim();
  if (!summary.endsWith(".")) summary += ".";

  //Align with non-Oxford British English
  summary = toBritishEnglish(summary);

  //Return statement
  return summary;
}


/**
 * Reads context TSV and wiki_cache.json, generates paraphrased British English descriptions
 * with infobox tags, and updates temp_jobs/polity_descriptions_<#>.txt.
 *
 * @param {number|string} arg0_target_chunk
 *
 * @returns {Promise<void>}
 */
async function A_generateDescriptions (arg0_target_chunk) {
  //Convert from parameters
  let target_chunk = arg0_target_chunk;

  //Declare local instance variables
  let cache_file = path.resolve(process.cwd(), "tests/wiki_cache.json");
  let end_chunk = 15;
  let start_chunk = 0;
  let temp_jobs_dir = path.resolve(process.cwd(), "temp_jobs");
  let tests_dir = path.resolve(process.cwd(), "tests");
  let total_polities = 0;
  let wiki_cache = {};
  let with_tags_count = 0;

  if (fs.existsSync(cache_file)) {
    try {
      wiki_cache = JSON.parse(fs.readFileSync(cache_file, "utf8"));
    } catch (e) {
      console.warn("Failed to parse wiki_cache.json");
    }
  }

  if (target_chunk !== undefined && target_chunk !== "all") {
    let parsed_idx = Number(target_chunk);
    if (!isNaN(parsed_idx)) {
      start_chunk = parsed_idx;
      end_chunk = parsed_idx;
    }
  }

  console.log(`Generating descriptions for chunks ${start_chunk}..${end_chunk} (wiki_cache has ${Object.keys(wiki_cache).length} entries)...`);

  for (let chunk_idx = start_chunk; chunk_idx <= end_chunk; chunk_idx++) {
    let chunk_entries = [];
    let tsv_path = path.join(tests_dir, `polity_descriptions_context_${chunk_idx}.tsv`);
    let txt_path = path.join(temp_jobs_dir, `polity_descriptions_${chunk_idx}.txt`);

    if (!fs.existsSync(tsv_path)) {
      console.warn(`Context TSV missing for chunk ${chunk_idx}: ${tsv_path}`);
      continue;
    }

    let lines = fs.readFileSync(tsv_path, "utf8").trim().split(/\r?\n/).slice(1);

    for (let i = 0; i < lines.length; i++) {
      let parts = lines[i].split("\t");
      let control_type = parts[3] || "";
      let id = parts[0];
      let label = parts[5] || "";
      let link = parts[6] || "";
      let name = parts[1] || "";
      let orig_desc = parts[7] || "";
      let parent = parts[4] || "";
      let span = parts[2] || "";

      let cache_entry = link ? wiki_cache[link] : null;
      let extract = cache_entry?.extract || "";
      let tags = cache_entry?.tags || "";

      //If entry has HTML, extract tags
      if (!tags && cache_entry?.html)
        tags = extractInfoboxTags(cache_entry.html);

      let context_obj = {
        control_type: control_type,
        id: id,
        label: label,
        link: link,
        name: name,
        orig_desc: orig_desc,
        parent: parent,
        span: span
      };

      let brief_desc = paraphraseDescription(extract || orig_desc, context_obj);
      brief_desc = brief_desc.replace(/[\r\n]+/g, " ").trim();
      let full_desc = brief_desc;

      if (tags) {
        let clean_tags = tags.replace(/[\r\n]+/g, " ").trim();
        clean_tags = clean_tags.replace(/(^|;\s*)(\d+):/g, (m, p1, p2) => `${p1}Year ${p2}:`);
        clean_tags = clean_tags.replace(/\bseizuranity\b/gi, "suzerainty");
        full_desc = `${brief_desc}\n\n${clean_tags}`;
        with_tags_count++;
      }

      chunk_entries.push(`${id}: ${full_desc}`);
      total_polities++;
    }

    let output_text = chunk_entries.join("\n\n") + "\n";
    fs.writeFileSync(txt_path, output_text, "utf8");
    console.log(`Chunk ${chunk_idx}: ${lines.length} polities written to ${txt_path}`);
  }

  console.log(`\nSuccessfully processed ${total_polities} polities across chunks ${start_chunk}..${end_chunk} (${with_tags_count} with infobox tags).`);
}

let arg = process.argv[2] !== undefined ? process.argv[2] : "all";
A_generateDescriptions(arg).catch(console.error);
