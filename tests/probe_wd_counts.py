import json
import urllib.request
import urllib.parse

# 1. Check Wikidata SPARQL for ALL Latvian cities/towns (Q515/Q3957/Q532) and Lithuanian cities/towns/miesteliai/villages
# Specifically count how many settlements have P1082 with P585 dates and what years appear!
for label, q_filter in [
  ("LT_towns_villages", "?item wdt:P17 wd:Q37 . VALUES ?tp { wd:Q515 wd:Q3957 wd:Q532 wd:Q5084 wd:Q253019 } ?item wdt:P31 ?tp ."),
  ("LV_towns_villages", "?item wdt:P17 wd:Q211 . VALUES ?tp { wd:Q515 wd:Q3957 wd:Q532 wd:Q5084 wd:Q15284 } ?item wdt:P31 ?tp ."),
]:
  q = f"""
  SELECT ?item ?itemLabel ?tpLabel ?coord ?pop ?date ?refLabel WHERE {{
    {q_filter}
    ?item wdt:P625 ?coord .
    ?item p:P1082 ?stmt .
    ?stmt ps:P1082 ?pop .
    ?stmt pq:P585 ?date .
    OPTIONAL {{ ?stmt prov:wasDerivedFrom/pr:P248 ?ref . }}
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,lt,lv". }}
  }} LIMIT 5000
  """
  u = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q)
  req = urllib.request.Request(u, headers={"User-Agent": "SVEA-Bot/1.0"})
  try:
    res = json.loads(urllib.request.urlopen(req, timeout=45).read().decode("utf-8"))
    rows = res["results"]["bindings"]
    from collections import Counter
    yrs = Counter(r["date"]["value"][:4] for r in rows)
    items = set(r["item"]["value"] for r in rows)
    refs = Counter(r.get("refLabel", {}).get("value", "") for r in rows)
    print(f"=== {label}: {len(rows)} stmts, {len(items)} unique items ===")
    print("  top years:", yrs.most_common(15))
    print("  top refs:", refs.most_common(10))
  except Exception as e:
    print(f"=== {label} ERR: {e} ===")
