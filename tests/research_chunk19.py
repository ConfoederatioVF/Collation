import json
import time
import urllib.parse
import urllib.request

HEADERS = {"User-Agent": "SVEA-Toponymy-Research/1.0 (https://confoederatio.org; polite-research-1req-per-300ms)"}

def fetch_json (url):
  for attempt in range(4):
    try:
      time.sleep(0.28)
      req = urllib.request.Request(url, headers=HEADERS)
      with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
      if e.code == 429:
        time.sleep(3 * (attempt + 1))
        continue
      raise
  raise RuntimeError("Rate limited repeatedly")

with open("tests/chunk19_research.json", "r", encoding="utf-8") as fh:
  items = json.load(fh)

# Load original input metadata from script or hardcode? We have key, n, c, r, ll, ey, ly in items already.
updated = []
for idx, item in enumerate(items):
  lat, lng = item["ll"]
  name = item["n"]
  country = item["c"]
  need_geo = "es_geo_err" in item or "es_geo" not in item
  need_search = "es_search_err" in item or "es_pages" not in item
  # Also if es_pages has empty extract for a geosearch title < 3000m, refetch that title!
  if need_geo:
    try:
      geo_url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
      g = fetch_json(geo_url)
      item["es_geo"] = [{"title": x["title"], "dist": x["dist"]} for x in g.get("query", {}).get("geosearch", [])]
      item.pop("es_geo_err", None)
    except Exception as e:
      item["es_geo_err"] = str(e)

  # Determine candidate titles to fetch full extracts (up to 4500 chars)
  titles = []
  for gx in item.get("es_geo", []):
    if gx["dist"] <= 5000 and gx["title"] not in titles:
      titles.append(gx["title"])

  if need_search or not titles:
    try:
      q = urllib.parse.quote(f"{name} {country}")
      sr_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
      s = fetch_json(sr_url)
      for x in s.get("query", {}).get("search", []):
        if x["title"] not in titles:
          titles.append(x["title"])
      item.pop("es_search_err", None)
    except Exception as e:
      item["es_search_err"] = str(e)

  # Check if we already have non-empty long extracts for top titles
  existing_pages = item.get("es_pages", {})
  fetch_titles = []
  for t in titles[:3]:
    if t not in existing_pages or len(existing_pages[t].get("extract", "")) < 100:
      fetch_titles.append(t)

  if fetch_titles:
    try:
      # Fetch one by one or all together with exlimit=max
      tparam = urllib.parse.quote("|".join(fetch_titles))
      ex_url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&explaintext=1&exlimit=max&exchars=3500&titles={tparam}&format=json"
      ex = fetch_json(ex_url)
      if "es_pages" not in item:
        item["es_pages"] = {}
      for pid, pdata in ex.get("query", {}).get("pages", {}).items():
        if "missing" not in pdata:
          item["es_pages"][pdata.get("title")] = {
            "coords": pdata.get("coordinates"),
            "extract": pdata.get("extract", "")[:3500]
          }
    except Exception as e:
      item["es_ex_err"] = str(e)

  updated.append(item)
  if (idx + 1) % 15 == 0:
    with open("tests/chunk19_research.json", "w", encoding="utf-8") as fh:
      json.dump(updated + items[idx+1:], fh, ensure_ascii=False, indent=2)
    print(f"Progress: {idx+1}/90")

with open("tests/chunk19_research.json", "w", encoding="utf-8") as fh:
  json.dump(updated, fh, ensure_ascii=False, indent=2)
print("Finished all 90!")
