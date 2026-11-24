let fs = require("fs");

let items = [
  {"key": "Las Lajas-Colombia", "n": "Las Lajas", "c": "Colombia", "ll": [1.58273, -78.70609], "ey": 1000, "ly": 1500},
  {"key": "Tarapoa-Ecuador", "n": "Tarapoa", "c": "Ecuador", "ll": [-0.1247, -76.34551], "ey": 1920, "ly": 2025},
  {"key": "Choquecancha-Peru", "n": "Choquecancha", "c": "Peru", "ll": [-13.0397, -72.036], "ey": 1525, "ly": 2017},
  {"key": "La Libertad-Peru", "n": "La Libertad", "c": "Peru", "ll": [-9.63306, -77.74139], "ey": 1525, "ly": 2025},
  {"key": "Moretecocha-Ecuador_2", "n": "Moretecocha", "c": "Ecuador", "ll": [-1.61, -77.35], "ey": 357, "ly": 1438},
  {"key": "Alto Jahuel-Chile", "n": "Alto Jahuel", "c": "Chile", "ll": [-33.73753, -70.68519], "ey": 1850, "ly": 2017},
  {"key": "Toro-Peru", "n": "Toro", "c": "Peru", "ll": [-15.26444, -72.92833], "ey": 1525, "ly": 2025},
  {"key": "Tumbabarreto-Colombia", "n": "Tumbabarreto", "c": "Colombia", "ll": [5.43811, -75.70027], "ey": 1525, "ly": 2018},
  {"key": "Maucallacta-Peru", "n": "Maucallacta", "c": "Peru", "ll": [-13.5601, -73.4934], "ey": 1525, "ly": 2017},
  {"key": "Tocmoche-Peru", "n": "Tocmoche", "c": "Peru", "ll": [-6.41278, -79.36083], "ey": 1525, "ly": 2025},
  {"key": "Andajes-Peru", "n": "Andajes", "c": "Peru", "ll": [-10.79278, -76.90917], "ey": 1000, "ly": 2025},
  {"key": "Quípama-Colombia", "n": "Quípama", "c": "Colombia", "ll": [5.52055, -74.18003], "ey": 1525, "ly": 2025},
  {"key": "La Punta-Chile", "n": "La Punta", "c": "Chile", "ll": [-34.01085, -70.64988], "ey": 1525, "ly": 2017},
  {"key": "Otoca-Peru", "n": "Otoca", "c": "Peru", "ll": [-14.49, -74.68667], "ey": 1525, "ly": 2025},
  {"key": "Tangui-Peru", "n": "Tangui", "c": "Peru", "ll": [-12.383, -76.383], "ey": 1525, "ly": 1825},
  {"key": "Aquia-Peru", "n": "Aquia", "c": "Peru", "ll": [-10.07444, -77.145], "ey": 1525, "ly": 2025},
  {"key": "Pampas (vp_intendencia_lima)-Peru", "n": "Pampas", "c": "Peru", "ll": [-11.314, -76.777], "ey": 1525, "ly": 1825},
  {"key": "San Juan de Viscas-Peru", "n": "San Juan de Viscas", "c": "Peru", "ll": [-12.3273, -76.2787], "ey": 1525, "ly": 2017},
  {"key": "Chibunga-Ecuador", "n": "Chibunga", "c": "Ecuador", "ll": [-0.03782, -79.74084], "ey": 1850, "ly": 2025},
  {"key": "Páez (ven_barinas)-Venezuela", "n": "Páez", "c": "Venezuela", "ll": [8.03111, -70.00667], "ey": 1850, "ly": 2025},
  {"key": "Condormarca-Peru", "n": "Condormarca", "c": "Peru", "ll": [-7.54667, -77.59972], "ey": 1440, "ly": 2025},
  {"key": "Buena Vista (ven_lara)-Venezuela", "n": "Buena Vista", "c": "Venezuela", "ll": [9.88667, -69.48111], "ey": 1850, "ly": 2025},
  {"key": "Viraco-Peru", "n": "Viraco", "c": "Peru", "ll": [-15.65833, -72.525], "ey": 1525, "ly": 2025},
  {"key": "San Francisco Socoroma-Chile", "n": "San Francisco Socoroma", "c": "Chile", "ll": [-18.264, -69.602], "ey": 1525, "ly": 1825},
  {"key": "La Capilla-Colombia", "n": "La Capilla", "c": "Colombia", "ll": [5.09569, -73.44435], "ey": 1793, "ly": 2025},
  {"key": "Anaica-Peru", "n": "Anaica", "c": "Peru", "ll": [-11.583, -76.67], "ey": 1525, "ly": 1825},
  {"key": "Cantagallo-Venezuela", "n": "Cantagallo", "c": "Venezuela", "ll": [9.78852, -67.43191], "ey": 1850, "ly": 2025},
  {"key": "Auquimarca-Peru_2", "n": "Auquimarca", "c": "Peru", "ll": [-10.951, -76.914], "ey": 1525, "ly": 1825},
  {"key": "San Ignacio (per_la_libertad)-Peru", "n": "San Ignacio", "c": "Peru", "ll": [-7.8312, -78.7152], "ey": 1525, "ly": 2017},
  {"key": "Juan Pablo Peñaloza-Venezuela", "n": "Juan Pablo Peñaloza", "c": "Venezuela", "ll": [8.03722, -71.85444], "ey": 1850, "ly": 2025},
  {"key": "Sabaino-Peru", "n": "Sabaino", "c": "Peru", "ll": [-14.31333, -72.94528], "ey": 1525, "ly": 2025},
  {"key": "Malchinguí-Ecuador", "n": "Malchinguí", "c": "Ecuador", "ll": [0.05794, -78.34935], "ey": 1850, "ly": 2025},
  {"key": "Pallac-Peru_2", "n": "Pallac", "c": "Peru", "ll": [-11.349, -76.807], "ey": 1525, "ly": 1825},
  {"key": "Puncurin-Peru", "n": "Puncurin", "c": "Peru", "ll": [-9.80468, -76.79086], "ey": 1438, "ly": 1530},
  {"key": "Calpi-Ecuador", "n": "Calpi", "c": "Ecuador", "ll": [-1.61671, -78.75715], "ey": 1525, "ly": 2025},
  {"key": "Guayrapongo-Ecuador", "n": "Guayrapongo", "c": "Ecuador", "ll": [-2.512, -78.927], "ey": 1525, "ly": 1830},
  {"key": "Santo Domingo de Menahermosa-Peru", "n": "Santo Domingo de Menahermosa", "c": "Peru", "ll": [-11.391, -75.63], "ey": 1542, "ly": 1825},
  {"key": "Pararin-Peru", "n": "Pararin", "c": "Peru", "ll": [-10.05, -77.65444], "ey": 1525, "ly": 2025},
  {"key": "Zaacata-Peru", "n": "Zaacata", "c": "Peru", "ll": [-16.164, -69.515], "ey": 1525, "ly": 1825},
  {"key": "Arahuay-Peru", "n": "Arahuay", "c": "Peru", "ll": [-11.62139, -76.67028], "ey": 1525, "ly": 2025},
  {"key": "San Lorenzo (vp_intendencia_lima)-Peru", "n": "San Lorenzo", "c": "Peru", "ll": [-11.553, -76.682], "ey": 1525, "ly": 1825},
  {"key": "Mucuruba-Venezuela", "n": "Mucuruba", "c": "Venezuela", "ll": [8.71, -70.98833], "ey": 1538, "ly": 2025},
  {"key": "Nava-Peru", "n": "Nava", "c": "Peru", "ll": [-10.731, -76.835], "ey": 1525, "ly": 1825},
  {"key": "Pampallacta (per_apurimac)-Peru", "n": "Pampallacta", "c": "Peru", "ll": [-14.0043, -73.0969], "ey": 1525, "ly": 2017},
  {"key": "Uchumarca-Peru", "n": "Uchumarca", "c": "Peru", "ll": [-7.04722, -77.80556], "ey": 1525, "ly": 2025},
  {"key": "Casiri-Peru", "n": "Casiri", "c": "Peru", "ll": [-15.33, -73.34], "ey": 1525, "ly": 1825},
  {"key": "Tinta (per_lima)-Peru", "n": "Tinta", "c": "Peru", "ll": [-10.6802, -76.8228], "ey": 1525, "ly": 2017},
  {"key": "Huataca-Peru", "n": "Huataca", "c": "Peru", "ll": [-15.076, -73.331], "ey": 1525, "ly": 1825},
  {"key": "Atiquipa-Peru", "n": "Atiquipa", "c": "Peru", "ll": [-15.79611, -74.36361], "ey": 1525, "ly": 2025},
  {"key": "Pariamarca (per_lima)-Peru", "n": "Pariamarca", "c": "Peru", "ll": [-11.4919, -76.6295], "ey": 1525, "ly": 2017},
  {"key": "San Pedro de Laraos-Peru", "n": "San Pedro de Laraos", "c": "Peru", "ll": [-11.66444, -76.53944], "ey": 1525, "ly": 2025},
  {"key": "San Jose (vp_intendencia_lima)-Peru", "n": "San Jose", "c": "Peru", "ll": [-11.505, -76.675], "ey": 1525, "ly": 1825},
  {"key": "Yamor-Peru", "n": "Yamor", "c": "Peru", "ll": [-10.199, -77.483], "ey": 1525, "ly": 1825},
  {"key": "La Sierra (col_boyaca)-Colombia", "n": "La Sierra", "c": "Colombia", "ll": [6.22731, -74.56735], "ey": 1525, "ly": 2018},
  {"key": "Quintero-Colombia_2", "n": "Quintero", "c": "Colombia", "ll": [4.472, -76.095], "ey": 1525, "ly": 1830},
  {"key": "Sabaneta (ven_falcon)-Venezuela", "n": "Sabaneta", "c": "Venezuela", "ll": [11.26, -69.98944], "ey": 1850, "ly": 2025},
  {"key": "Huanangui-Peru", "n": "Huanangui", "c": "Peru", "ll": [-11.1328, -77.0363], "ey": 1525, "ly": 2017},
  {"key": "Santiago Apostol-Colombia", "n": "Santiago Apostol", "c": "Colombia", "ll": [9.0069, -74.92686], "ey": 1541, "ly": 2018},
  {"key": "Anton Moreno-Colombia", "n": "Anton Moreno", "c": "Colombia", "ll": [2.41, -76.62], "ey": 1525, "ly": 1830},
  {"key": "Nanis-Peru", "n": "Nanis", "c": "Peru", "ll": [-10.383, -77.15], "ey": 1525, "ly": 1825},
  {"key": "Loreto (crp_gobernacion_tucuman)-Argentina", "n": "Loreto", "c": "Argentina", "ll": [-28.301, -64.184], "ey": 1536, "ly": 1830},
  {"key": "Mercedes Díaz-Venezuela", "n": "Mercedes Díaz", "c": "Venezuela", "ll": [9.30027, -70.63088], "ey": 1850, "ly": 2025},
  {"key": "Huambacho Nueva (la Huaca)-Peru", "n": "Huambacho Nueva (la Huaca)", "c": "Peru", "ll": [-9.2589, -78.4352], "ey": -855, "ly": 2017},
  {"key": "Jorobamba-Peru", "n": "Jorobamba", "c": "Peru", "ll": [-5.8533, -78.6166], "ey": 1525, "ly": 2017},
  {"key": "Nonogasta-Argentina", "n": "Nonogasta", "c": "Argentina", "ll": [-29.30222, -67.50633], "ey": 1850, "ly": 2010},
  {"key": "Hunchos-Peru", "n": "Hunchos", "c": "Peru", "ll": [-12.588, -74.535], "ey": 1525, "ly": 1825},
  {"key": "Lampa (per_ayacucho)-Peru", "n": "Lampa", "c": "Peru", "ll": [-15.185, -73.34917], "ey": -2000, "ly": 2025},
  {"key": "Apuri-Peru", "n": "Apuri", "c": "Peru", "ll": [-12.882, -75.808], "ey": 1525, "ly": 1825},
  {"key": "Tumbabiro-Ecuador", "n": "Tumbabiro", "c": "Ecuador", "ll": [0.4628, -78.18135], "ey": 1525, "ly": 2025},
  {"key": "San Buenaventura (per_lima)-Peru", "n": "San Buenaventura", "c": "Peru", "ll": [-11.48917, -76.66222], "ey": 1525, "ly": 2025},
  {"key": "Coronado-Colombia", "n": "Coronado", "c": "Colombia", "ll": [3.552, -76.318], "ey": 1525, "ly": 1830},
  {"key": "Choquekancha-Peru", "n": "Choquekancha", "c": "Peru", "ll": [-13.03601, -72.03543], "ey": 0, "ly": 1530},
  {"key": "Mian-Peru", "n": "Mian", "c": "Peru", "ll": [-6.318, -77.43], "ey": 1525, "ly": 1825},
  {"key": "Mangan-Ecuador", "n": "Mangan", "c": "Ecuador", "ll": [-2.711, -78.941], "ey": 1525, "ly": 1830},
  {"key": "San Jose (vp_intendencia_lima_2)-Peru", "n": "San Jose", "c": "Peru", "ll": [-14.048, -75.274], "ey": 1525, "ly": 1825},
  {"key": "Payandé-Colombia", "n": "Payandé", "c": "Colombia", "ll": [4.29758, -75.0984], "ey": 1775, "ly": 2018},
  {"key": "Mamara-Peru", "n": "Mamara", "c": "Peru", "ll": [-14.22861, -72.59083], "ey": 0, "ly": 2025},
  {"key": "Huayrahuacho-Peru", "n": "Huayrahuacho", "c": "Peru", "ll": [-13.893, -72.96], "ey": 1525, "ly": 1825},
  {"key": "Cotaruse-Peru", "n": "Cotaruse", "c": "Peru", "ll": [-14.41583, -73.205], "ey": -2000, "ly": 2025},
  {"key": "Surco-Peru", "n": "Surco", "c": "Peru", "ll": [-11.8825, -76.43611], "ey": 1525, "ly": 2025},
  {"key": "Pichanas-Argentina", "n": "Pichanas", "c": "Argentina", "ll": [-30.77, -65.192], "ey": 1536, "ly": 1830},
  {"key": "Chingos-Peru", "n": "Chingos", "c": "Peru", "ll": [-10.541, -77.186], "ey": 1525, "ly": 1825},
  {"key": "Mangas-Peru", "n": "Mangas", "c": "Peru", "ll": [-10.36944, -77.10333], "ey": 1525, "ly": 2025},
  {"key": "Atabillos Altos-Peru", "n": "Atabillos Altos", "c": "Peru", "ll": [-11.254, -76.674], "ey": 1525, "ly": 1825},
  {"key": "San Pedro de Pilas-Peru", "n": "San Pedro de Pilas", "c": "Peru", "ll": [-12.45444, -76.22694], "ey": 1525, "ly": 2025},
  {"key": "San Francisco de Sangayaico-Peru", "n": "San Francisco de Sangayaico", "c": "Peru", "ll": [-13.79528, -75.24917], "ey": 1525, "ly": 2025},
  {"key": "Calacoto (bol_la_paz)-Bolivia", "n": "Calacoto", "c": "Bolivia", "ll": [-17.28359, -68.63476], "ey": 1525, "ly": 2024},
  {"key": "San Benito-Colombia", "n": "San Benito", "c": "Colombia", "ll": [6.12666, -73.50907], "ey": 1525, "ly": 2025},
  {"key": "Arma-Peru", "n": "Arma", "c": "Peru", "ll": [-13.12639, -75.54194], "ey": 1525, "ly": 2025},
  {"key": "Acotama-Peru", "n": "Acotama", "c": "Peru", "ll": [-11.142, -77.066], "ey": 1525, "ly": 1825}
];

let headers = {"User-Agent": "ViscountBot/1.0 (https://example.org; contact@example.org)"};

async function fetchJson(url) {
  for (let attempt = 0; attempt < 4; attempt++) {
    let r = await fetch(url, {headers});
    if (r.status === 429 || r.status === 503) {
      await new Promise(res => setTimeout(res, 1000*(attempt + 1)));
      continue;
    }
    if (!r.ok) return null;
    try {
      return await r.json();
    } catch (e) {
      return null;
    }
  }
  return null;
}

async function queryWiki(lang, lat, lng, name, country) {
  let gsUrl = `https://${lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord=${lat}|${lng}&gsradius=10000&gslimit=5&format=json`;
  let gs = await fetchJson(gsUrl);
  let hits = (gs && gs.query && gs.query.geosearch) ? gs.query.geosearch : [];
  if (hits.length === 0) {
    let q = encodeURIComponent(`${name} ${country}`);
    let sr = await fetchJson(`https://${lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch=${q}&srlimit=3&format=json`);
    if (sr && sr.query && sr.query.search) {
      hits = sr.query.search.map(x => ({title: x.title, pageid: x.pageid, dist: -1}));
    }
  }
  let allHits = hits.slice(0, 2);
  let extracts = [];
  if (allHits.length > 0) {
    let ids = allHits.map(h => h.pageid).join("|");
    let ex = await fetchJson(`https://${lang}.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&exchars=3500&pageids=${ids}&format=json`);
    if (ex && ex.query && ex.query.pages) {
      for (let h of allHits) {
        let p = ex.query.pages[h.pageid];
        if (p) extracts.push({lang, title: p.title, dist: h.dist, extract: (p.extract || "").replace(/\s+/g, " ").slice(0, 2500)});
      }
    }
  }
  return extracts;
}

async function queryItem(it) {
  let [lat, lng] = it.ll;
  let extracts = await queryWiki("es", lat, lng, it.n, it.c);
  if (extracts.length === 0) {
    extracts = await queryWiki("en", lat, lng, it.n, it.c);
  }
  return {key: it.key, n: it.n, c: it.c, ll: it.ll, ey: it.ey, ly: it.ly, extracts};
}

async function main() {
  let out = [];
  for (let i = 0; i < items.length; i++) {
    let res = await queryItem(items[i]);
    out.push(res);
    await new Promise(r => setTimeout(r, 120));
  }
  let lines = [];
  for (let r of out) {
    lines.push(`=== ${r.key} (${r.c}, ey=${r.ey}, ly=${r.ly}, ll=${r.ll}) ===`);
    if (r.extracts.length === 0) lines.push("  [NO WIKI HIT]");
    for (let e of r.extracts) {
      lines.push(`  [${e.lang}:${e.title} | dist=${e.dist}m]: ${e.extract}`);
    }
  }
  fs.writeFileSync("tests/chunk18_wiki_report.txt", lines.join("\n"), "utf8");
  console.log("Wrote tests/chunk18_wiki_report.txt, total items:", out.length, "hits:", out.filter(x => x.extracts.length > 0).length);
}

main();
