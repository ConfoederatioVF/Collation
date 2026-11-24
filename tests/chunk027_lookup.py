import json
import time
import urllib.error
import urllib.parse
import urllib.request

from chunk027_data import INPUT_DATA

HEADERS = {"User-Agent": "OperationViscountResearch/1.0 (https://github.com/svea-project; mailto:research@svea-project.org)"}

def fetch_json(url):
  for attempt in range(4):
    try:
      req = urllib.request.Request(url, headers=HEADERS)
      with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
      if e.code == 429:
        time.sleep(2.5 * (attempt + 1))
        continue
      raise
    except Exception:
      if attempt < 3:
        time.sleep(1.5)
        continue
      raise
  raise RuntimeError("Failed after retries")

out = {}
for idx, item in enumerate(INPUT_DATA):
  k = item["key"]
  n = item["n"]
  c = item["c"]
  lat, lng = item["ll"]
  entry = {"hits": [], "geohits": []}
  # 1. Search by name + country
  q = f"{n} {c}"
  url = "https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch=" + urllib.parse.quote(q) + "&srlimit=3&format=json"
  try:
    data = fetch_json(url)
    hits = data.get("query", {}).get("search", [])
    titles = [h["title"] for h in hits[:2]]
    if titles:
      time.sleep(0.25)
      url2 = "https://es.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&exintro=1&explaintext=1&titles=" + urllib.parse.quote("|".join(titles)) + "&format=json"
      pages = fetch_json(url2).get("query", {}).get("pages", {})
      for pid, pdata in pages.items():
        entry["hits"].append({
          "title": pdata.get("title"),
          "coords": pdata.get("coordinates"),
          "extract": (pdata.get("extract") or "")[:600]
        })
  except Exception as e:
    entry["error"] = str(e)
  time.sleep(0.25)
  # 2. Geosearch near coords for non-ancient or missing
  if item["ey"] >= 1500:
    url_geo = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=3&format=json"
    try:
      gdata = fetch_json(url_geo)
      entry["geohits"] = [g["title"] for g in gdata.get("query", {}).get("geosearch", [])]
    except Exception as e:
      entry["geo_error"] = str(e)
    time.sleep(0.25)
  out[k] = entry
  if (idx + 1) % 15 == 0:
    print(f"Processed {idx + 1}/90", flush=True)

with open("tests/chunk027_wiki.json", "w", encoding="utf-8") as f:
  json.dump(out, f, ensure_ascii=False, indent=2)
print("Done:", len(out))
