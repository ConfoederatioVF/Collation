//Import libraries
let fs = require("node:fs");
let path = require("node:path");

/**
 * Parses any Wikipedia URL into language code and article title.
 *
 * @param {string} arg0_url
 *
 * @returns {{ lang: string, title: string }|null}
 */
function parseWikiUrl (arg0_url) {
  //Convert from parameters
  let url = arg0_url;

  //Guard clauses
  if (!url) return null;

  //Declare local instance variables
  let match = url.match(/^https?:\/\/([a-z0-9_-]+)(?:\.m)?\.wikipedia\.org(?:\/zh-[a-z]+|\/wiki|\/\/wiki)\/([^#?]+)/i);

  //Guard clauses
  if (!match) return null;

  let lang = match[1];
  let raw_title = match[2];
  let title = raw_title;

  try {
    title = decodeURIComponent(raw_title);
  } catch (e) {}

  //Return statement
  return { lang: lang, title: title };
}


/**
 * Parses wikitext infobox template into semicolon-separated key: value tags.
 *
 * @param {string} arg0_wikitext
 *
 * @returns {string}
 */
function parseWikitextInfobox (arg0_wikitext) {
  //Convert from parameters
  let wikitext = arg0_wikitext;

  //Guard clauses
  if (!wikitext) return "";

  //Declare local instance variables
  let lines = wikitext.split("\n");
  let seen = new Set();
  let skip_keys = [
    "anthem", "audio", "calling_code", "cctld", "coat_of_arms", "coordinates",
    "demonym", "driving_side", "flag", "flag_p1", "flag_p2", "flag_p3", "flag_p4",
    "flag_p5", "flag_s1", "flag_s2", "flag_s3", "flag_s4", "flag_s5",
    "image_armorial", "image_coat", "image_flag", "image_map", "image_map2",
    "map_caption", "map_caption2", "motto", "symbol"
  ];
  let tags = [];

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i].trim();
    let match = line.match(/^\|\s*([a-zA-Z0-9_ ]+?)\s*=\s*(.+)$/);

    if (match) {
      let raw_k = match[1].replace(/_/g, " ").trim();
      let raw_v = match[2];

      let k_lower = raw_k.toLowerCase();
      if (skip_keys.includes(k_lower) || k_lower.startsWith("image") || k_lower.startsWith("flag"))
        continue;

      //Clean wikitext markup: [[link|text]] -> text, {{template}} -> '', <ref> -> ''
      let clean_v = raw_v
        .replace(/<ref[\s\S]*?<\/ref>/gi, "")
        .replace(/<ref[^>]*\/>/gi, "")
        .replace(/\[\[(?:[^|\]]*\|)?([^\]]+)\]\]/g, "$1")
        .replace(/\{\{[^}]+\}\}/g, "")
        .replace(/<[^>]+>/g, " ")
        .replace(/\uFEFF/g, "")
        .replace(/\s+/g, " ")
        .trim();

      //Prefix numeric keys with Year
      if (/^\d+/.test(raw_k))
        raw_k = `Year ${raw_k}`;

      if (clean_v && clean_v !== "—" && clean_v !== "none" && clean_v.length < 200 && raw_k.length < 50) {
        let tag = `${raw_k}: ${clean_v}`;
        if (!seen.has(tag)) {
          seen.add(tag);
          tags.push(tag);
        }
      }
    }
  }

  //Return statement - at most 18 tags
  return tags.slice(0, 18).join("; ");
}


/**
 * Fetches Wikipedia entries in batches of 45 using MediaWiki Action API,
 * extracting plain-text extracts and infobox tags directly, caching in tests/wiki_cache.json.
 *
 * @returns {Promise<void>}
 */
async function A_fetchWikiCacheBatch () {
  //Declare local instance variables
  let cache_file = path.resolve(process.cwd(), "tests/wiki_cache.json");
  let completed = 0;
  let lang_groups = {};
  let tests_dir = path.resolve(process.cwd(), "tests");
  let total_to_fetch = 0;
  let unique_urls_map = new Map();
  let wiki_cache = {};

  //1. Load existing cache if present
  if (fs.existsSync(cache_file)) {
    try {
      wiki_cache = JSON.parse(fs.readFileSync(cache_file, "utf8"));
    } catch (e) {
      wiki_cache = {};
    }
  }

  //2. Collect all unique Wikipedia URLs across all 16 context files
  for (let i = 0; i < 16; i++) {
    let tsv_path = path.join(tests_dir, `polity_descriptions_context_${i}.tsv`);
    if (fs.existsSync(tsv_path)) {
      let lines = fs.readFileSync(tsv_path, "utf8").trim().split(/\r?\n/).slice(1);
      for (let x = 0; x < lines.length; x++) {
        let parts = lines[x].split("\t");
        let link = parts[6];
        if (link) {
          let parsed = parseWikiUrl(link);
          if (parsed && !unique_urls_map.has(link))
            unique_urls_map.set(link, parsed);
        }
      }
    }
  }

  //Group uncached URLs by language
  for (let [url, parsed] of unique_urls_map.entries()) {
    let entry = wiki_cache[url];
    if (!entry || entry.error || (entry.extract === undefined && entry.tags === undefined)) {
      if (!lang_groups[parsed.lang])
        lang_groups[parsed.lang] = [];
      lang_groups[parsed.lang].push({ title: parsed.title, url: url });
      total_to_fetch++;
    }
  }

  console.log(`Total unique Wikipedia URLs: ${unique_urls_map.size}. Already cached: ${unique_urls_map.size - total_to_fetch}. To fetch: ${total_to_fetch}.`);

  if (total_to_fetch === 0) {
    console.log("All Wikipedia URLs already cached!");
    return;
  }

  let saveCache = function () {
    let tmp_path = `${cache_file}.tmp`;
    fs.writeFileSync(tmp_path, JSON.stringify(wiki_cache), "utf8");
    fs.renameSync(tmp_path, cache_file);
  };

  let t0 = Date.now();
  let batch_size = 45;

  for (let lang of Object.keys(lang_groups)) {
    let items = lang_groups[lang];
    let num_batches = Math.ceil(items.length / batch_size);

    for (let b = 0; b < num_batches; b++) {
      let slice = items.slice(b*batch_size, (b + 1)*batch_size);
      let title_to_url = new Map();
      let titles = [];

      for (let item of slice) {
        titles.push(item.title);
        title_to_url.set(item.title.toLowerCase().replace(/_/g, " "), item.url);
        title_to_url.set(item.title.toLowerCase(), item.url);
        title_to_url.set(encodeURIComponent(item.title).toLowerCase(), item.url);
      }

      let api_url = `https://${lang}.wikipedia.org/w/api.php?action=query&titles=${titles.map(encodeURIComponent).join("|")}&prop=extracts|revisions&exintro=1&explaintext=1&rvprop=content&rvsection=0&format=json&origin=*&redirects=1`;

      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          let res = await fetch(api_url, {
            headers: { "User-Agent": "SVEA-Atlas/1.0 (contact@confoederatio.org)" },
            signal: AbortSignal.timeout(12000)
          });

          if (res.status === 429) {
            console.warn("[Envoy 429 rate limit] Sleeping for 11s...");
            await new Promise((resolve) => setTimeout(resolve, 11000));
            continue;
          }

          if (res.ok) {
            let data = await res.json();
            let norm_map = new Map();

            //Map normalized titles
            if (data.query?.normalized) {
              for (let n of data.query.normalized) {
                let from_key = n.from.toLowerCase().replace(/_/g, " ");
                let to_key = n.to.toLowerCase().replace(/_/g, " ");
                if (title_to_url.has(from_key))
                  title_to_url.set(to_key, title_to_url.get(from_key));
              }
            }

            //Map redirects
            if (data.query?.redirects) {
              for (let r of data.query.redirects) {
                let from_key = r.from.toLowerCase().replace(/_/g, " ");
                let to_key = r.to.toLowerCase().replace(/_/g, " ");
                if (title_to_url.has(from_key))
                  title_to_url.set(to_key, title_to_url.get(from_key));
              }
            }

            let pages = Object.values(data.query?.pages || {});

            for (let p of pages) {
              let p_title_key = (p.title || "").toLowerCase().replace(/_/g, " ");
              let matched_url = title_to_url.get(p_title_key);

              if (matched_url) {
                let extract = p.extract || "";
                let tags = parseWikitextInfobox(p.revisions?.[0]?.["*"] || "");

                wiki_cache[matched_url] = {
                  extract: extract,
                  tags: tags
                };
              }
            }
          }

          break;
        } catch (err) {
          if (attempt === 2) console.warn(`Batch error: ${err.message}`);
          await new Promise((resolve) => setTimeout(resolve, 2000*(attempt + 1)));
        }
      }

      completed += slice.length;

      if ((b + 1) % 5 === 0 || b === num_batches - 1) {
        saveCache();
        let elapsed_sec = (Date.now() - t0) / 1000;
        let rate = (completed / elapsed_sec).toFixed(1);
        let rem_sec = Math.round((total_to_fetch - completed) / (completed / elapsed_sec));
        console.log(`[Batch Progress] ${completed}/${total_to_fetch} fetched (${rate} articles/s, ~${rem_sec}s remaining).`);
      }

      //Polite pacing between batch requests
      await new Promise((resolve) => setTimeout(resolve, 400));
    }
  }

  saveCache();
  let total_elapsed = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`\nAll ${completed} Wikipedia URLs fetched in ${total_elapsed}s. Saved to ${cache_file}.`);
}

A_fetchWikiCacheBatch().catch(console.error);
