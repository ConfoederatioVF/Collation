import json, pathlib, urllib.request, urllib.parse, time

raw = pathlib.Path("tests/tmp_gather_024.py").read_text(encoding="utf8")
# reuse INPUT by exec
ns = {}
exec(raw.split("def hav")[0], ns)
INPUT = ns["INPUT"]

out = {}
for idx, item in enumerate(INPUT):
    lat, lng = item["ll"]
    q = f"""SELECT ?item ?itemLabel ?itemDescription ?dist ?inception ?officialName ?esTitle ?enTitle WHERE {{
  SERVICE wikibase:around {{
    ?item wdt:P625 ?loc.
    bd:serviceParam wikibase:center "Point({lng} {lat})"^^geo:wktLiteral.
    bd:serviceParam wikibase:radius "8".
    bd:serviceParam wikibase:distance ?dist.
  }}
  OPTIONAL {{ ?item wdt:P571 ?inception. }}
  OPTIONAL {{ ?item wdt:P1448 ?officialName. }}
  OPTIONAL {{ ?esArt schema:about ?item ; schema:isPartOf <https://es.wikipedia.org/> ; schema:name ?esTitle . }}
  OPTIONAL {{ ?enArt schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?enTitle . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en". }}
}} ORDER BY ?dist LIMIT 6"""
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={"User-Agent": "SVEA-Toponymy/1.0 (mailto:research@example.org)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            rows = json.loads(r.read().decode())["results"]["bindings"]
            out[item["key"]] = [
                {k: v["value"] for k, v in row.items()}
                for row in rows
            ]
    except Exception as e:
        out[item["key"]] = [{"error": str(e)}]
    time.sleep(0.15)
    if (idx + 1) % 15 == 0:
        print(f"Queried {idx+1}/{len(INPUT)}", flush=True)

pathlib.Path("tests/tmp_wd_024.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf8")
print("Done WD queries:", len(out))
