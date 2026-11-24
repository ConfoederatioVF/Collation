import json
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

with open("tests/chunk023_wiki.json", encoding="utf-8") as fp:
  ITEMS = json.load(fp)

HEADERS = {'User-Agent': 'ViscountToponymyResearch/1.0 (contact@example.org)'}

def fetch_json(url, retries=3):
  for i in range(retries):
    try:
      req = urllib.request.Request(url, headers=HEADERS)
      with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
      if i == retries - 1:
        raise e
      time.sleep(0.5 * (i + 1))

def get_pages_extracts(lang, titles):
  if not titles:
    return []
  res = []
  for t in titles[:3]:
    url = f"https://{lang}.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(t)}&prop=extracts|coordinates&explaintext=1&exchars=3500&format=json"
    try:
      d = fetch_json(url)
      for pid, p in d.get("query", {}).get("pages", {}).items():
        if pid != "-1":
          res.append({
            "title": p.get("title"),
            "coords": p.get("coordinates"),
            "extract": p.get("extract", "")
          })
    except Exception as e:
      res.append({"title": t, "err": str(e)})
  return res

def query_geosearch(lang, lat, lon):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=12000&gslimit=4&format=json"
  d = fetch_json(url)
  return [g["title"] for g in d.get("query", {}).get("geosearch", [])]

def query_search(lang, query):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&srlimit=3&format=json"
  d = fetch_json(url)
  return [h["title"] for h in d.get("query", {}).get("search", [])]

def query_nominatim(lat, lon):
  url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=jsonv2&zoom=14&accept-language=es"
  d = fetch_json(url)
  return d.get("display_name", ""), d.get("address", {})

def process_item(it):
  lat, lon = it["ll"]
  n = it["n"]
  c = it["c"]
  out = {
    "key": it["key"],
    "n": n,
    "c": c,
    "ll": it["ll"],
    "ey": it["ey"],
    "ly": it["ly"],
    "al": it.get("al", [])
  }
  try:
    geo_titles = query_geosearch("es", lat, lon)
  except Exception as e:
    geo_titles = []
    out["geo_err"] = str(e)

  search_titles = []
  try:
    search_titles = query_search("es", f"{n} {c}")
  except Exception:
    pass

  # Combine unique titles prioritizing geo_titles
  seen = set()
  all_titles = []
  for t in geo_titles + search_titles:
    if t not in seen:
      seen.add(t)
      all_titles.append(t)

  out["es_geo"] = geo_titles
  out["es_pages"] = get_pages_extracts("es", all_titles[:4])

  # If still no good match, try en.wikipedia geosearch/search
  if not out["es_pages"]:
    try:
      en_geo = query_geosearch("en", lat, lon)
      en_s = query_search("en", f"{n} {c}")
      out["en_pages"] = get_pages_extracts("en", (en_geo + en_s)[:3])
    except Exception:
      pass

  return out

results = []
with ThreadPoolExecutor(max_workers=4) as ex:
  futs = {ex.submit(process_item, it): it["key"] for it in ITEMS}
  for f in as_completed(futs):
    results.append(f.result())

order = {it["key"]: i for i, it in enumerate(ITEMS)}
results.sort(key=lambda x: order[x["key"]])

with open("tests/chunk023_detailed.json", "w", encoding="utf-8") as fp:
  json.dump(results, fp, ensure_ascii=False, indent=2)

print("Done:", len(results))
