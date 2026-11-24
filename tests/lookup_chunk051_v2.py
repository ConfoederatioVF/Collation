import json
import time
import urllib.parse
import urllib.request

with open("tests/lookup_chunk051.py", "r", encoding="utf-8") as f:
  src = f.read()
start = src.index("SETTLEMENTS = [")
end = src.index("\ndef wiki_search")
ns = {}
exec(src[start:end], ns)
SETTLEMENTS = ns["SETTLEMENTS"]

UA = "ViscountToponymyResearch/1.0 (https://confoederatio.org; research@confoederatio.org)"

def fetch_json(url):
  req = urllib.request.Request(url, headers={"User-Agent": UA})
  with urllib.request.urlopen(req, timeout=12) as r:
    return json.loads(r.read())

def wiki_geo(lang, lat, lng):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=3&format=json"
  return [x["title"] for x in fetch_json(url).get("query", {}).get("geosearch", [])]

def wiki_search(lang, q):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&srlimit=2&format=json"
  return [x["title"] for x in fetch_json(url).get("query", {}).get("search", [])]

def wiki_extracts_batch(lang, titles):
  if not titles:
    return {}
  joined = "|".join(titles[:20])
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={urllib.parse.quote(joined)}&format=json"
  pages = fetch_json(url).get("query", {}).get("pages", {})
  res = {}
  for pid, p in pages.items():
    if "title" in p:
      res[p["title"]] = p.get("extract", "")[:900]
  return res

results = {}
all_titles = []
for idx, s in enumerate(SETTLEMENTS):
  key = s["key"]
  n = s["n"]
  c = s["c"]
  lat, lng = s["ll"]
  try:
    geo = wiki_geo("es", lat, lng)
    time.sleep(0.15)
    sr = wiki_search("es", f'"{n}" {c}')
    time.sleep(0.15)
    if not sr:
      sr = wiki_search("es", f"{n} {c}")
      time.sleep(0.15)
    results[key] = {"geo": geo, "search": sr}
    for t in geo + sr:
      if t not in all_titles:
        all_titles.append(t)
  except Exception as e:
    results[key] = {"error": str(e)}
  if idx % 15 == 14:
    print(f"Searched {idx+1}/90", flush=True)

extracts = {}
for i in range(0, len(all_titles), 20):
  batch = all_titles[i:i+20]
  try:
    extracts.update(wiki_extracts_batch("es", batch))
    time.sleep(0.2)
  except Exception as e:
    print("Batch extract err:", e)

for k, v in results.items():
  v["extracts"] = {t: extracts.get(t, "") for t in (v.get("geo", []) + v.get("search", [])) if extracts.get(t)}

with open("tests/chunk051_wiki2.json", "w", encoding="utf-8") as f:
  json.dump(results, f, ensure_ascii=False, indent=2)
print("Done all wiki2")
