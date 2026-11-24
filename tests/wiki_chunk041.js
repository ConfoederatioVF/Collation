const fs = require("fs");
const d = require("./chunk041_gaz_matches.json");

async function fetchJson(url) {
  const res = await fetch(url, { headers: { "User-Agent": "SVEA-Toponymy/1.0 (research)" } });
  if (!res.ok) return null;
  return res.json();
}

async function queryWiki(lang, title) {
  const u = `https://${lang}.wikipedia.org/w/api.php?action=query&prop=extracts|revisions&rvprop=content&rvslots=main&exintro=1&explaintext=1&titles=${encodeURIComponent(title)}&redirects=1&format=json`;
  const data = await fetchJson(u);
  if (!data || !data.query || !data.query.pages) return null;
  const page = Object.values(data.query.pages)[0];
  if (!page || page.missing !== undefined) return null;
  const wikitext = page.revisions?.[0]?.slots?.main?.["*"] || "";
  return { title: page.title, extract: (page.extract || "").slice(0, 700), wikitext: wikitext.slice(0, 2500) };
}

async function searchWiki(lang, q, lat, lng) {
  const su = `https://${lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(q)}&srlimit=3&format=json`;
  const sdata = await fetchJson(su);
  const hits = (sdata?.query?.search || []).map(x => x.title);
  let geo = [];
  if (Number.isFinite(lat) && Number.isFinite(lng)) {
    const gu = `https://${lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord=${lat}|${lng}&gsradius=10000&gslimit=5&format=json`;
    const gdata = await fetchJson(gu);
    geo = (gdata?.query?.geosearch || []).map(x => `${x.title} (${Math.round(x.dist)}m)`);
  }
  return { hits, geo };
}

(async () => {
  const items = Object.entries(d);
  const out = {};
  for (let i = 0; i < items.length; i += 6) {
    const batch = items.slice(i, i + 6);
    await Promise.all(batch.map(async ([key, arr]) => {
      const v = arr[0]?.v || {};
      const name = v.name || key.split("-")[0];
      const country = v.country || key.split("-").pop();
      const [lat, lng] = v.coords || [null, null];
      const q = `${name} ${country}`.replace(/\(.*\)/g, "").trim();
      const esS = await searchWiki("es", q, lat, lng);
      let page = null;
      for (const cand of esS.hits.slice(0, 2)) {
        const p = await queryWiki("es", cand);
        if (p) { page = { lang: "es", ...p }; break; }
      }
      if (!page && esS.geo.length > 0) {
        const gt = esS.geo[0].replace(/ \(\d+m\)$/, "");
        const p = await queryWiki("es", gt);
        if (p) page = { lang: "es-geo", ...p };
      }
      out[key] = { hits: esS.hits, geo: esS.geo, page };
    }));
  }
  fs.writeFileSync("tests/chunk041_wiki.json", JSON.stringify(out, null, 2));
  console.log("Done wiki lookup for", Object.keys(out).length);
})();
