import urllib.request, urllib.parse, json, re, sys, time, os

HEADERS = {"User-Agent": "SVEA-HistoricalToponymy/1.0 (https://confoederatio.org; research@confoederatio.org)"}
CACHE_PATH = "tests/wp_cache.json"

def load_cache():
  if os.path.exists(CACHE_PATH):
    with open(CACHE_PATH, encoding="utf-8") as f:
      return json.load(f)
  return {}

def save_cache(cache):
  with open(CACHE_PATH, "w", encoding="utf-8") as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

def fetch_json(url):
  for attempt in range(4):
    try:
      req = urllib.request.Request(url, headers=HEADERS)
      time.sleep(0.45)
      return json.loads(urllib.request.urlopen(req, timeout=15).read())
    except urllib.error.HTTPError as e:
      if e.code == 429:
        wait = int(e.headers.get("Retry-After", 5)) + attempt * 3
        print(f"  [429 backoff {wait}s]", file=sys.stderr, flush=True)
        time.sleep(wait)
      else:
        raise
  raise RuntimeError("Too many 429s")

def geosearch(lat, lng, lang="es", radius=10000):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius={radius}&gslimit=5&format=json"
  return fetch_json(url).get("query", {}).get("geosearch", [])

def search_wp(q, lang="es", limit=2):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&srlimit={limit}&format=json"
  return fetch_json(url).get("query", {}).get("search", [])

def get_extracts_batch(titles, lang="es", chars=3000):
  out = {}
  for i in range(0, len(titles), 10):
    chunk = titles[i:i+10]
    tstr = "|".join(chunk)
    url = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&explaintext=true&exintro=false&exchars={chars}&titles={urllib.parse.quote(tstr)}&format=json"
    pages = fetch_json(url).get("query", {}).get("pages", {})
    for pid, p in pages.items():
      if "title" in p:
        out[p["title"]] = {
          "coords": p.get("coordinates"),
          "extract": p.get("extract", "")
        }
  return out

if __name__ == "__main__":
  mode = sys.argv[1]
  cache = load_cache()
  with open("tests/input_chunk025.json", encoding="utf-8") as f:
    items = json.load(f)

  if mode == "collect":
    start, end = int(sys.argv[2]), int(sys.argv[3])
    for idx in range(start, end):
      item = items[idx]
      key = item["key"]
      if key in cache and cache[key].get("geo") is not None and cache[key].get("srch") is not None:
        continue
      lat, lng = item["ll"]
      n = item["n"]
      c = item["c"]
      geo = geosearch(lat, lng, "es", 10000)
      srch = search_wp(f"{n} {c}", "es", 2)
      cache[key] = {
        "geo": [(g["title"], round(g["dist"])) for g in geo],
        "srch": [(h["title"], re.sub("<[^>]+>", "", h.get("snippet", ""))[:160]) for h in srch]
      }
      save_cache(cache)
      print(f"[{idx}] {key}: geo={cache[key]['geo'][:2]} srch={[s[0] for s in cache[key]['srch']]}", flush=True)
  elif mode == "print_cache":
    for idx, item in enumerate(items):
      key = item["key"]
      entry = cache.get(key, {})
      print(f"[{idx}] {key} | r={item['r']} | ey={item['ey']} ly={item['ly']} | al={item.get('al')} | ex={item.get('ex')}")
      print(f"  GEO: {entry.get('geo')}")
      print(f"  SRCH: {entry.get('srch')}")
  elif mode == "extracts":
    titles = sys.argv[2:]
    res = get_extracts_batch(titles, "es", 2500)
    for t in titles:
      info = res.get(t, {})
      print(f"=== {t} {info.get('coords')} ===")
      print(info.get("extract", "")[:2200])
      print()
