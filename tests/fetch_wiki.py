import json, urllib.request, urllib.parse, time, sys

UA = "SVEAToponymyResearch/1.0 (https://confoederatio.org; research@confoederatio.org)"

def fetch(url):
  req = urllib.request.Request(url, headers={"User-Agent": UA})
  with urllib.request.urlopen(req, timeout=20) as r:
    return json.loads(r.read().decode("utf-8"))

def wiki_search_and_geo(it):
  lat, lon = it["ll"]
  res = {"key": it["key"], "geo_es": [], "sr_es": [], "sr_en": [], "wd": []}
  try:
    url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
    res["geo_es"] = [(g["title"], round(g["dist"])) for g in fetch(url).get("query", {}).get("geosearch", [])]
    time.sleep(0.25)
  except Exception as e:
    res["geo_es_err"] = str(e)
  try:
    q = urllib.parse.quote(f"{it['n']} {it['c']}")
    url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
    res["sr_es"] = [s["title"] for s in fetch(url).get("query", {}).get("search", [])]
    time.sleep(0.25)
  except Exception as e:
    res["sr_es_err"] = str(e)
  return res

def sparql_batch(items):
  # Query Wikidata for items near any of these points
  out = {}
  for it in items:
    lat, lon = it["ll"]
    q = f'''SELECT ?item ?itemLabel ?inception ?dist ?eswiki ?enwiki WHERE {{
  SERVICE wikibase:around {{
    ?item wdt:P625 ?loc .
    bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral .
    bd:serviceParam wikibase:radius "8" .
    bd:serviceParam wikibase:distance ?dist .
  }}
  OPTIONAL {{ ?item wdt:P571 ?inception . }}
  OPTIONAL {{ ?eswiki schema:about ?item ; schema:isPartOf <https://es.wikipedia.org/> . }}
  OPTIONAL {{ ?enwiki schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en". }}
}} ORDER BY ?dist LIMIT 5'''
    try:
      url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q)
      rows = fetch(url).get("results", {}).get("bindings", [])
      out[it["key"]] = [
        {
          "label": r.get("itemLabel", {}).get("value"),
          "dist": r.get("dist", {}).get("value"),
          "inception": r.get("inception", {}).get("value"),
          "eswiki": r.get("eswiki", {}).get("value"),
          "enwiki": r.get("enwiki", {}).get("value"),
        }
        for r in rows
      ]
    except Exception as e:
      out[it["key"]] = {"err": str(e)}
    time.sleep(0.2)
  return out

if __name__ == "__main__":
  data = json.load(open("tests/input_034.json", encoding="utf-8"))
  mode = sys.argv[1]
  start = int(sys.argv[2])
  end = int(sys.argv[3])
  if mode == "wd":
    res = sparql_batch(data[start:end])
    print(json.dumps(res, ensure_ascii=False, indent=1))
  elif mode == "wiki":
    for it in data[start:end]:
      r = wiki_search_and_geo(it)
      print(json.dumps(r, ensure_ascii=False))
