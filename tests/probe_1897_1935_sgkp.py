import json
import urllib.request
import urllib.parse

# 1. Check Archive.org for Latvian census / statistical yearbooks (1920-1935)
for q in [
  '"tautas skaitīšana" Latvia OR Latvijā',
  '"Latvijas statistiskā gada grāmata"',
  '"pilsētu apraksti" OR "Latvijas pilsētas" 1935',
]:
  u = "https://archive.org/advancedsearch.php?q=" + urllib.parse.quote(q) + "&fl[]=identifier,title,year&rows=10&output=json"
  res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode("utf-8"))
  print("IA LV:", q, "->", [(d["identifier"], d.get("year"), d.get("title", "")[:60]) for d in res["response"]["docs"]])

# 2. Check Wikidata SPARQL specifically for historical years (1897, 1920-1939, 1959, 1970, 1979, 1989) in LT & LV
for label, qid in [("LT_hist", "Q37"), ("LV_hist", "Q211")]:
  q = f"""
  SELECT (YEAR(?date) AS ?yr) (COUNT(?stmt) AS ?cnt) WHERE {{
    ?item wdt:P17 wd:{qid} .
    ?item wdt:P625 ?coord .
    ?item p:P1082 ?stmt .
    ?stmt pq:P585 ?date .
    FILTER(YEAR(?date) <= 1995)
  }} GROUP BY (YEAR(?date)) ORDER BY DESC(?cnt) LIMIT 25
  """
  u = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q)
  res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "SVEA-Bot/1.0"}), timeout=30).read().decode("utf-8"))
  print(f"WD {label} <=1995:", [(b["yr"]["value"], b["cnt"]["value"]) for b in res["results"]["bindings"]])

# 3. Check Wikidata P31 classes in Lithuania & Latvia that have P1082
for label, qid in [("LT_types", "Q37"), ("LV_types", "Q211")]:
  q = f"""
  SELECT ?tp ?tpLabel (COUNT(DISTINCT ?item) AS ?cnt) WHERE {{
    ?item wdt:P17 wd:{qid} .
    ?item wdt:P625 ?coord .
    ?item p:P1082 ?stmt .
    ?item wdt:P31 ?tp .
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
  }} GROUP BY ?tp ?tpLabel ORDER BY DESC(?cnt) LIMIT 20
  """
  u = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q)
  res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "SVEA-Bot/1.0"}), timeout=30).read().decode("utf-8"))
  print(f"WD {label} P31:", [(b["tp"]["value"].split("/")[-1], b.get("tpLabel",{}).get("value",""), b["cnt"]["value"]) for b in res["results"]["bindings"]])
