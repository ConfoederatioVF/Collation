let fs = require("fs");

let input = JSON.parse(fs.readFileSync("tests/chunk_044_input.json", "utf8"));

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function fetchJson(url) {
  let r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function queryWiki(lang, title, lat, lng) {
  let geoUrl = `https://${lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gsradius=10000&gscoord=${lat}|${lng}&gslimit=5&format=json`;
  let cleanTitle = title.replace(/\s*\([^)]*\)\s*/g, " ").trim();
  let srUrl = `https://${lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(cleanTitle)}&srlimit=3&format=json`;
  let geo = [], search = [];
  try {
    let g = await fetchJson(geoUrl);
    geo = g?.query?.geosearch?.map(x => ({ title: x.title, pageid: x.pageid, dist: x.dist })) || [];
  } catch (e) {}
  try {
    let s = await fetchJson(srUrl);
    search = s?.query?.search?.map(x => ({ title: x.title, pageid: x.pageid, snippet: x.snippet.replace(/<[^>]+>/g, "") })) || [];
  } catch (e) {}
  return { geo, search };
}

async function getPageInfo(lang, pageid) {
  let url = `https://${lang}.wikipedia.org/w/api.php?action=query&prop=extracts|revisions&explaintext=1&exchars=3500&rvprop=content&rvslots=main&rvsection=0&pageids=${pageid}&format=json`;
  try {
    let d = await fetchJson(url);
    let p = d?.query?.pages?.[String(pageid)];
    if (!p) return null;
    let wikitext = p.revisions?.[0]?.slots?.main?.["*"] || "";
    let lines = wikitext.split("\n").filter(l => /fundac|creac|erecc|nombre|antiguo|etimo|establec|fecha|poblaci/i.test(l)).slice(0, 20);
    return {
      title: p.title,
      extract: (p.extract || "").slice(0, 2500),
      infobox_hints: lines
    };
  } catch (e) {
    return null;
  }
}

async function main() {
  let out = {};
  for (let i = 0; i < input.length; i++) {
    let item = input[i];
    // Skip obvious synthetic archaeological survey report names that won't be in Wikipedia
    let skipWiki = /^(Concentración|En Proceso|Yacimiento 1|Reporte HF|Mor-Cc|Área Depósito)/i.test(item.n);
    let pages = [];
    if (!skipWiki) {
      let es = await queryWiki("es", `${item.n} ${item.c}`, item.ll[0], item.ll[1]);
      let pageIds = [];
      for (let g of es.geo) pageIds.push({ lang: "es", id: g.pageid, via: "geo", dist: g.dist, title: g.title });
      for (let s of es.search.slice(0, 2)) {
        if (!pageIds.some(x => x.id === s.pageid)) {
          pageIds.push({ lang: "es", id: s.pageid, via: "search", title: s.title });
        }
      }
      for (let p of pageIds.slice(0, 2)) {
        let info = await getPageInfo(p.lang, p.id);
        if (info) pages.push({ ...p, ...info });
        await sleep(50);
      }
      await sleep(80);
    }
    out[item.key] = { n: item.n, c: item.c, r: item.r, ll: item.ll, ey: item.ey, al: item.al, pages };
    if ((i + 1) % 15 === 0) console.log(`Processed ${i + 1}/${input.length}`);
  }
  fs.writeFileSync("tests/chunk_044_wiki.json", JSON.stringify(out, null, 2));
  console.log("Done! Pages found for:", Object.values(out).filter(x => x.pages.length > 0).length);
}

main();
