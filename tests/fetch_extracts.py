import json, urllib.request, urllib.parse, time

UA = "SVEAToponymyResearch/1.0 (https://confoederatio.org; research@confoederatio.org)"

def fetch(url):
  req = urllib.request.Request(url, headers={"User-Agent": UA})
  with urllib.request.urlopen(req, timeout=25) as r:
    return json.loads(r.read().decode("utf-8"))

def batch_extracts(lang, titles):
  res = {}
  titles = list(dict.fromkeys(titles))
  for i in range(0, len(titles), 15):
    chunk = titles[i:i+15]
    tparam = "|".join(chunk)
    url = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&titles={urllib.parse.quote(tparam)}&format=json"
    data = fetch(url).get("query", {}).get("pages", {})
    for pid, p in data.items():
      if pid != "-1":
        res[p["title"]] = p.get("extract", "")[:4000]
    time.sleep(0.5)
  return res

es_titles = []
en_titles = []
for fn in ["tests/wd_0_30.json", "tests/wd_30_60.json", "tests/wd_60_90.json"]:
  d = json.load(open(fn, encoding="utf-8"))
  for k, rows in d.items():
    if isinstance(rows, list):
      for r in rows:
        if r.get("eswiki"):
          t = urllib.parse.unquote(r["eswiki"].split("/wiki/")[-1]).replace("_", " ")
          es_titles.append(t)
        if r.get("enwiki"):
          t = urllib.parse.unquote(r["enwiki"].split("/wiki/")[-1]).replace("_", " ")
          en_titles.append(t)

# Also add explicit titles for items that might have Wikipedia pages by name
extra_es = [
  "Valle de Huentota", "Aporoma", "Catriló", "San Isidro de Patulú", "Lacramarca",
  "Distrito de Lacramarca", "Pueblo de Poco Poco", "Pocopoco", "Súa", "Masparrito",
  "Calamarí", "Cartagena de Indias", "Iruya", "Villa Paranacito", "Catamarca",
  "Sierra Chica (Buenos Aires)", "Arroyo Leyes", "Hughes (Santa Fe)", "30 de Agosto",
  "Pacto (Ecuador)", "Guangopolo", "Ayacucho (Trujillo)", "Aregue", "Chiquinquirá",
  "Zenta", "San Ramón de la Nueva Orán", "Casa del Minero", "Churajón",
  "Viluco", "San Luis (San Andrés)", "América (Manabí)", "Yanabaya"
]
es_titles.extend(extra_es)

es_out = batch_extracts("es", es_titles)
en_out = batch_extracts("en", en_titles)
json.dump({"es": es_out, "en": en_out}, open("tests/wiki_extracts.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("Saved es:", len(es_out), "en:", len(en_out))
