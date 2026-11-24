import json
import time
import urllib.parse
import urllib.request

# Load the 90 input records from previous cache
old_cache = json.load(open("tests/quipu_wiki_cache.json", encoding="utf-8"))
INPUT = [v["input"] for v in old_cache.values()]

HEADERS = {"User-Agent": "Project1509SVEA/1.0 (https://confoederatio.org; research@confoederatio.org)"}

def fetch_json(url, retries=3):
  for attempt in range(retries):
    try:
      req = urllib.request.Request(url, headers=HEADERS)
      with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
      if e.code == 429:
        wait = 2 * (attempt + 1)
        print(f"429 on {url[:80]}, sleeping {wait}s...")
        time.sleep(wait)
      else:
        return {"_error": str(e)}
    except Exception as e:
      return {"_error": str(e)}
  return {"_error": "max retries"}

def wiki_geosearch(lang, lat, lon, radius=10000):
  params = urllib.parse.urlencode({
    "action": "query",
    "list": "geosearch",
    "gscoord": f"{lat}|{lon}",
    "gsradius": radius,
    "gslimit": 5,
    "format": "json"
  })
  data = fetch_json(f"https://{lang}.wikipedia.org/w/api.php?{params}")
  return data.get("query", {}).get("geosearch", [])

def wiki_search(lang, query):
  params = urllib.parse.urlencode({
    "action": "query",
    "list": "search",
    "srsearch": query,
    "srlimit": 3,
    "format": "json"
  })
  data = fetch_json(f"https://{lang}.wikipedia.org/w/api.php?{params}")
  return [x["title"] for x in data.get("query", {}).get("search", [])]

def fetch_extracts_batch(lang, titles):
  out = {}
  titles = list(dict.fromkeys(titles))
  for i in range(0, len(titles), 20):
    chunk = titles[i:i+20]
    params = urllib.parse.urlencode({
      "action": "query",
      "prop": "extracts|coordinates",
      "explaintext": 1,
      "exintro": 0,
      "exchars": 3500,
      "exlimit": 20,
      "titles": "|".join(chunk),
      "redirects": 1,
      "format": "json"
    })
    data = fetch_json(f"https://{lang}.wikipedia.org/w/api.php?{params}")
    pages = data.get("query", {}).get("pages", {})
    for pid, p in pages.items():
      if str(pid) != "-1":
        out[p.get("title")] = {
          "coords": p.get("coordinates"),
          "extract": p.get("extract", "")
        }
    time.sleep(0.2)
  return out

def main():
  results = {}
  all_es_titles = []
  all_en_titles = []
  for idx, item in enumerate(INPUT):
    lat, lon = item["ll"]
    name = item["n"]
    country = item["c"]
    geo_es = wiki_geosearch("es", lat, lon, 10000)
    time.sleep(0.15)
    search_es = []
    if not geo_es or (name not in [g["title"] for g in geo_es] and name != "None"):
      search_es = wiki_search("es", f"{name} {country}")
      time.sleep(0.15)
    geo_en = []
    if not geo_es and not search_es:
      geo_en = wiki_geosearch("en", lat, lon, 10000)
      time.sleep(0.15)

    item_es_titles = [g["title"] for g in geo_es[:2]] + [t for t in search_es[:2]]
    item_en_titles = [g["title"] for g in geo_en[:2]]
    all_es_titles.extend(item_es_titles)
    all_en_titles.extend(item_en_titles)

    results[item["key"]] = {
      "input": item,
      "geo_es": geo_es,
      "search_es": search_es,
      "geo_en": geo_en,
      "es_titles": list(dict.fromkeys(item_es_titles)),
      "en_titles": list(dict.fromkeys(item_en_titles)),
    }
    if (idx + 1) % 15 == 0:
      print(f"Queried {idx+1}/90...")

  print(f"Fetching extracts for {len(set(all_es_titles))} eswiki titles and {len(set(all_en_titles))} enwiki titles...")
  es_extracts = fetch_extracts_batch("es", all_es_titles)
  en_extracts = fetch_extracts_batch("en", all_en_titles)

  # Map back (note redirects might change title, so also keep fuzzy/partial or re-fetch if needed)
  for k, v in results.items():
    v["extracts"] = {}
    for t in v["es_titles"]:
      if t in es_extracts:
        v["extracts"][f"es:{t}"] = es_extracts[t]
    for t in v["en_titles"]:
      if t in en_extracts:
        v["extracts"][f"en:{t}"] = en_extracts[t]

  with open("tests/quipu_wiki_cache.json", "w", encoding="utf-8") as f:
    json.dump({"results": results, "es_extracts": es_extracts, "en_extracts": en_extracts}, f, ensure_ascii=False, indent=2)
  print("Done!")

if __name__ == "__main__":
  main()
