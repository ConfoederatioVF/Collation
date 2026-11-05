//Import libraries
let fs = require("node:fs");
let path = require("node:path");

/**
 * Gathers all unique Wikipedia URLs from tests/polity_descriptions_context_<0..15>.tsv
 * and fetches the summary extract and infobox HTML for each via Wikipedia REST v1 API,
 * streaming HTML to read only the infobox table, caching into tests/wiki_cache.json.
 *
 * @returns {Promise<void>}
 */
async function A_fetchWikiCache () {
  //Declare local instance variables
  let cache_file = path.resolve(process.cwd(), "tests/wiki_cache.json");
  let completed = 0;
  let concurrency = 16;
  let errors = 0;
  let save_interval = 100;
  let tests_dir = path.resolve(process.cwd(), "tests");
  let unique_urls_set = new Set();
  let url_queue = [];
  let wiki_cache = {};

  //1. Load existing cache if present
  if (fs.existsSync(cache_file)) {
    try {
      wiki_cache = JSON.parse(fs.readFileSync(cache_file, "utf8"));
    } catch (e) {
      console.warn("Failed to parse existing cache file, starting fresh.");
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
        if (link && link.startsWith("https://en.wikipedia.org/wiki/"))
          unique_urls_set.add(link);
      }
    }
  }

  for (let url of unique_urls_set) {
    let entry = wiki_cache[url];
    //Re-fetch if missing, errored, or both extract and html were empty
    if (!entry || entry.error || (!entry.extract && !entry.html))
      url_queue.push(url);
  }

  console.log(`Total unique Wikipedia URLs: ${unique_urls_set.size}. Already valid in cache: ${unique_urls_set.size - url_queue.length}. To fetch: ${url_queue.length}.`);

  if (url_queue.length === 0) {
    console.log("All Wikipedia URLs already cached!");
    return;
  }

  let saveCache = function () {
    let tmp_path = `${cache_file}.tmp`;
    fs.writeFileSync(tmp_path, JSON.stringify(wiki_cache), "utf8");
    fs.renameSync(tmp_path, cache_file);
  };

  let t0 = Date.now();
  let total_to_fetch = url_queue.length;

  let worker = async () => {
    while (url_queue.length > 0) {
      let url = url_queue.shift();
      let raw_title = url.split("/wiki/")[1];
      let title = raw_title;
      try {
        title = decodeURIComponent(raw_title);
      } catch (e) {}

      let extract = "";
      let html = "";
      let success = false;

      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          let s_res = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}`, {
            headers: { "User-Agent": "SVEA-Atlas/1.0 (contact@confoederatio.org)" }
          });
          if (s_res.status === 429) {
            await new Promise((resolve) => setTimeout(resolve, 2000*(attempt + 1)));
            continue;
          }
          if (s_res.ok) {
            let s_data = await s_res.json();
            extract = s_data.extract || "";
          }

          let h_res = await fetch(`https://en.wikipedia.org/api/rest_v1/page/html/${encodeURIComponent(title)}`, {
            headers: { "User-Agent": "SVEA-Atlas/1.0 (contact@confoederatio.org)" }
          });
          if (h_res.ok) {
            let reader = h_res.body.getReader();
            let decoder = new TextDecoder();
            let buffer = "";

            while (true) {
              let { done, value } = await reader.read();
              if (done) break;
              buffer += decoder.decode(value, { stream: true });
              let start = buffer.search(/<table[^>]*class="[^"]*infobox[^"]*"[^>]*>/i);
              if (start !== -1) {
                let end = buffer.indexOf("</table>", start);
                if (end !== -1) {
                  html = buffer.slice(start, end + 8);
                  reader.cancel();
                  break;
                }
              } else if (buffer.length > 200000) {
                reader.cancel();
                break;
              }
            }
          }

          success = true;
          break;
        } catch (err) {
          if (attempt === 2) errors++;
          await new Promise((resolve) => setTimeout(resolve, 1000*(attempt + 1)));
        }
      }

      if (success) {
        wiki_cache[url] = {
          extract: extract,
          html: html
        };
      }

      completed++;
      if (completed % 100 === 0) {
        let elapsed_sec = (Date.now() - t0) / 1000;
        let rate = (completed / elapsed_sec).toFixed(1);
        let rem_sec = Math.round((total_to_fetch - completed) / (completed / elapsed_sec));
        console.log(`[Fetch Progress] ${completed}/${total_to_fetch} fetched (${rate} req/s, ~${rem_sec}s remaining, ${errors} errs).`);
      }

      if (completed % save_interval === 0)
        saveCache();

      //Pacing delay between requests
      await new Promise((resolve) => setTimeout(resolve, 30));
    }
  };

  let workers_array = [];
  for (let i = 0; i < concurrency; i++)
    workers_array.push(worker());

  await Promise.all(workers_array);
  saveCache();

  let total_elapsed = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`Completed fetching all ${completed} Wikipedia URLs in ${total_elapsed}s. Saved to ${cache_file}.`);
}

A_fetchWikiCache().catch(console.error);
