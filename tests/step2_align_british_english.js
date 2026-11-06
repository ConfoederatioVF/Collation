//Import libraries
let fs = require("node:fs");
let path = require("node:path");

let invariant_ize = new Set([
  "assize", "assizes",
  "belize",
  "capsize", "capsizes", "capsized", "capsizing",
  "maize",
  "prize", "prizes", "prized", "prizing",
  "seize", "seizes", "seized", "seizing", "seizure", "seizures",
  "size", "sizes", "sized",
  "suez"
]);

/**
 * Parses and aligns a polity description text with non-Oxford British English (EN-GB).
 * Converts American quotation marks to British single inverted commas,
 * handles logical punctuation, and converts US spellings to EN-GB.
 *
 * @param {string} arg0_text
 *
 * @returns {string}
 */
function toBritishEnglish (arg0_text) {
  //Convert from parameters
  let text = arg0_text;

  //Guard clauses
  if (!text) return "";

  //Declare local instance variables
  let ence_words = [
    [/(\b[Dd]ef)ense(s?)\b/g, "$1ence$2"],
    [/(\b[Oo]ff)ense(s?)\b/g, "$1ence$2"],
    [/(\b[Pp]ret)ense(s?)\b/g, "$1ence$2"]
  ];
  let l_doubling = [
    [/(\b[Tt]ravel)ed\b/g, "$1led"],
    [/(\b[Tt]ravel)ing\b/g, "$1ling"],
    [/(\b[Tt]ravel)er(s?)\b/g, "$1ler$2"],
    [/(\b[Cc]ancel)ed\b/g, "$1led"],
    [/(\b[Cc]ancel)ing\b/g, "$1ling"],
    [/(\b[Mm]odel)ed\b/g, "$1led"],
    [/(\b[Mm]odel)ing\b/g, "$1ling"],
    [/(\b[Ss]ignal)ed\b/g, "$1led"],
    [/(\b[Ss]ignal)ing\b/g, "$1ling"],
    [/(\b[Ii]nitial)ed\b/g, "$1led"],
    [/(\b[Ii]nitial)ing\b/g, "$1ling"],
    [/(\b[Cc]hannel)ed\b/g, "$1led"],
    [/(\b[Cc]hannel)ing\b/g, "$1ling"],
    [/(\b[Ll]abel)ed\b/g, "$1led"],
    [/(\b[Ll]abel)ing\b/g, "$1ling"]
  ];
  let ogue_words = [
    [/(\b[Cc]atal)og(s?)\b/g, "$1ogue$2"],
    [/(\b[Dd]ial)og(s?)\b/g, "$1ogue$2"],
    [/(\b[Mm]onol)og(s?)\b/g, "$1ogue$2"],
    [/(\b[Pp]rol)og(s?)\b/g, "$1ogue$2"]
  ];
  let our_words = [
    [/(\b[Nn]eighb)or(s?|hoods?)\b/g, "$1our$2"],
    [/(\b[Cc]ol)or(s?|ed|ing|ful)\b/g, "$1our$2"],
    [/(\b[Ff]lav)or(s?|ed|ing|ful)\b/g, "$1our$2"],
    [/(\b[Hh]on)or(s?|ed|ing|able)\b/g, "$1our$2"],
    [/(\b[Hh]arb)or(s?|ed|ing)\b/g, "$1our$2"],
    [/(\b[Ll]ab)or(s?|ed|ing)\b/g, "$1our$2"],
    [/(\b[Rr]um)or(s?|ed)\b/g, "$1our$2"],
    [/(\b[Aa]rm)or(s?|ed|y|ies)\b/g, (m, g1, g2) => g2.startsWith("y") || g2.startsWith("ie") ? m : `${g1}our${g2}`],
    [/(\b[Ss]plend)or(s?)\b/g, "$1our$2"],
    [/(\b[Vv]ig)or(ous|ously)?\b/g, (m, g1, g2) => g2 ? `${g1}our${g2}` : `${g1}our`],
    [/(\b[Rr]ig)or(s?|ous|ously)\b/g, (m, g1, g2) => `${g1}our${g2}`],
    [/(\b[Ff]av)or(s?|ed|ing|ite|ites)\b/g, (m, g1, g2) => `${g1}our${g2}`],
    [/(\b[Bb]ehavi)or(s?|al)\b/g, "$1our$2"],
    [/(\b[Dd]emean)or(s?)\b/g, "$1our$2"],
    [/(\b[Ss]avi)or(s?)\b/g, "$1our$2"],
    [/(\b[Cc]lam)or(s?|ed|ing)\b/g, "$1our$2"],
    [/(\b[Ff]erv)or\b/g, "$1our"],
    [/(\b[Cc]and)or\b/g, "$1our"],
    [/(\b[Ss]ucc)or\b/g, "$1our"],
    [/(\b[Aa]rd)or\b/g, "$1our"]
  ];
  let re_words = [
    [/(\b[Cc]ent)er(s?)\b/g, "$1re$2"],
    [/(\b[Tt]heat)er(s?)\b/g, "$1re$2"],
    [/(\b[Kk]ilomet)er(s?)\b/g, "$1re$2"],
    [/(\b[Cc]entimet)er(s?)\b/g, "$1re$2"],
    [/(\b[Mm]illimet)er(s?)\b/g, "$1re$2"],
    [/(\b[Ff]ib)er(s?)\b/g, "$1re$2"],
    [/(\b[Ll]ust)er(s?)\b/g, "$1re$2"],
    [/(\b[Ss]omb)er\b/g, "$1re"],
    [/(\b[Ss]epulch)er(s?)\b/g, "$1re$2"],
    [/(\b[Ss]pect)er(s?)\b/g, "$1re$2"],
    [/(\b[Cc]alib)er(s?)\b/g, "$1re$2"],
    [/(?<=\d\s*|\b(?:cubic|square|lineal)\s+)[Mm]eters?\b/g, (m) => m.endsWith("s") ? (m[0] === "M" ? "Metres" : "metres") : (m[0] === "M" ? "Metre" : "metre")]
  ];
  let res = text;

  //1. Inverted commas: parse double quotation marks into British single inverted commas
  res = res.replace(/(?<!\d)"([^"\r\n]+)"/g, (match, inner) => {
    let clean_inner = inner;
    let trailing_punct = "";

    if (/[a-zA-Z0-9][.,]$/.test(clean_inner) && !clean_inner.includes(". ")) {
      trailing_punct = clean_inner.slice(-1);
      clean_inner = clean_inner.slice(0, -1);
    }

    clean_inner = clean_inner.replace(/(?<=\s|^)'([^'\r\n]+)'(?=\s|$|[.,;])/g, '"$1"');
    clean_inner = clean_inner.replace(/(?<=[a-zA-Z])'(?=[a-zA-Z])/g, "’");

    return `'${clean_inner}'${trailing_punct}`;
  });

  //Parse curly double quotation marks
  res = res.replace(/[“]([^“”\r\n]+)[”]/g, (match, inner) => {
    let clean_inner = inner;
    let trailing_punct = "";

    if (/[a-zA-Z0-9][.,]$/.test(clean_inner) && !clean_inner.includes(". ")) {
      trailing_punct = clean_inner.slice(-1);
      clean_inner = clean_inner.slice(0, -1);
    }

    clean_inner = clean_inner.replace(/(?<=\s|^)[‘']([^’'\r\n]+)[’'](?=\s|$|[.,;])/g, '"$1"');
    clean_inner = clean_inner.replace(/(?<=[a-zA-Z])[‘'](?=[a-zA-Z])/g, "’");

    return `‘${clean_inner}’${trailing_punct}`;
  });

  //2. Vocabulary & doubled 'l'
  res = res.replace(/\bpercent\b/gi, (m) => m[0] === "P" ? "Per cent" : "per cent");

  for (let i = 0; i < l_doubling.length; i++)
    res = res.replace(l_doubling[i][0], l_doubling[i][1]);

  for (let i = 0; i < re_words.length; i++)
    res = res.replace(re_words[i][0], re_words[i][1]);

  for (let i = 0; i < ence_words.length; i++)
    res = res.replace(ence_words[i][0], ence_words[i][1]);

  for (let i = 0; i < our_words.length; i++)
    res = res.replace(our_words[i][0], our_words[i][1]);

  //-ize -> -ise (non-Oxford EN-GB)
  res = res.replace(/\b([a-zA-Z]+)iz(e|ed|es|ing|ation|ations|er|ers)\b/g, (match, stem, suffix) => {
    let lower_match = match.toLowerCase();
    let lower_stem = stem.toLowerCase();

    if (invariant_ize.has(lower_stem) || invariant_ize.has(lower_match))
      return match;

    return `${stem}is${suffix}`;
  });

  for (let i = 0; i < ogue_words.length; i++)
    res = res.replace(ogue_words[i][0], ogue_words[i][1]);

  //Return statement
  return res;
}

/**
 * Loops through all 16 chunk files in temp_jobs/polity_descriptions_<0..15>.txt,
 * parses each description, applies British English alignment, and updates the chunks.
 *
 * @returns {Promise<void>}
 */
async function A_alignBritishEnglish () {
  //Declare local instance variables
  let temp_jobs_dir = path.resolve(process.cwd(), "temp_jobs");
  let total_modified = 0;
  let total_polities = 0;

  for (let chunk_idx = 0; chunk_idx < 16; chunk_idx++) {
    let chunk_path = path.join(temp_jobs_dir, `polity_descriptions_${chunk_idx}.txt`);
    if (!fs.existsSync(chunk_path)) {
      console.error(`Chunk file missing: ${chunk_path}`);
      process.exit(1);
    }

    let chunk_modified = 0;
    let matches = [];
    let match;
    let new_entries = [];
    let regex = /^(\d+):\s*/gm;
    let text = fs.readFileSync(chunk_path, "utf8").replace(/\r\n/g, "\n");

    while ((match = regex.exec(text)) !== null) {
      matches.push({
        full_start: match.index,
        id: match[1],
        start: match.index + match[0].length
      });
    }

    for (let x = 0; x < matches.length; x++) {
      let cur = matches[x];
      let next_start = (x + 1 < matches.length) ? matches[x + 1].full_start : text.length;
      let desc = text.slice(cur.start, next_start).trim();

      total_polities++;
      let brit_desc = toBritishEnglish(desc);

      if (brit_desc !== desc) {
        chunk_modified++;
        total_modified++;
      }

      new_entries.push(`${cur.id}: ${brit_desc}`);
    }

    let output_text = new_entries.join("\n\n") + "\n";
    fs.writeFileSync(chunk_path, output_text, "utf8");
    console.log(`Chunk ${chunk_idx}: ${matches.length} polities, ${chunk_modified} aligned with British English -> ${chunk_path}`);
  }

  console.log(`\nCompleted British English alignment: ${total_modified} of ${total_polities} polities updated across 16 chunks.`);
  module.exports = { toBritishEnglish };
}

if (require.main === module)
  A_alignBritishEnglish().catch(console.error);

module.exports = { toBritishEnglish };

