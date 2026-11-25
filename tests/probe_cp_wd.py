import json
import re
import ssl
import urllib.request
import urllib.parse

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 1. Check citypopulation.de LT & LV cities and subpages
for u in [
  "https://www.citypopulation.de/en/latvia/cities/",
  "https://www.citypopulation.de/en/lithuania/cities/",
]:
  h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read().decode("utf-8", errors="replace")
  ths = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip() for x in re.findall(r"<th[^>]*>(.*?)</th>", h, re.S)]
  links = re.findall(r'href=["\'](/en/(?:latvia|lithuania)/[^"\']+)["\']', h)
  print("=== CP:", u, "===")
  print("  headers:", ths[:20])
  print("  sublinks:", sorted(set(links))[:20])
  trs = re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S)
  print("  rows:", len(trs))
  for tr in trs[:6]:
    tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
    if tds:
      print("   ", tds[:10])

# 2. Check stat.gov.lv historical census publications (with ssl unverified for cert chain)
for u in [
  "https://stat.gov.lv/en/statistics-themes/population/population-census",
  "https://stat.gov.lv/lv/statistikas-temas/iedzivotaji/tautas-skaitisana",
]:
  try:
    h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25, context=ctx).read().decode("utf-8", errors="replace")
    links = re.findall(r'href=["\']([^"\']*(?:1920|1925|1930|1935|pdf|skait|census)[^"\']*)["\']', h, re.I)
    print("\n=== stat.gov.lv:", u, "===")
    print("  links:", links[:20])
  except Exception as e:
    print("stat.gov.lv err:", e)

# 3. Fixed Wikidata SPARQL <= 1995 & P31
for label, qid in [("LT_hist", "Q37"), ("LV_hist", "Q211")]:
  q = f"""
  SELECT ?yr (COUNT(?stmt) AS ?cnt) WHERE {{
    ?item wdt:P17 wd:{qid} .
    ?item wdt:P625 ?coord .
    ?item p:P1082 ?stmt .
    ?stmt pq:P585 ?date .
    BIND(YEAR(?date) AS ?yr)
    FILTER(?yr <= 1995)
  }} GROUP BY ?yr ORDER BY DESC(?cnt) LIMIT 30
  """
  u = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q)
  res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "SVEA-Bot/1.0"}), timeout=30).read().decode("utf-8"))
  print(f"\nWD {label} <=1995:", [(b["yr"]["value"], b["cnt"]["value"]) for b in res["results"]["bindings"]])

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
  print(f"WD {label} P31:", [(b["tp"]["value"].split("/")[-1], b.get("tpLabel", {}).get("value", ""), b["cnt"]["value"]) for b in res["results"]["bindings"]])
