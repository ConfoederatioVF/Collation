import concurrent.futures
import json
import urllib.parse
import urllib.request

INPUT_PATH = "tests/chunk_022_input.json"
OUT_PATH = "tests/chunk_022_wiki.json"


def fetch_json(url):
  req = urllib.request.Request(url, headers={"User-Agent": "ViscountToponymyResearch/1.0 (academic)"})
  with urllib.request.urlopen(req, timeout=10) as r:
    return json.loads(r.read().decode("utf-8"))


def query_wiki(item):
  n = item["n"]
  c = item["c"]
  lat, lng = item["ll"]
  res = {"key": item["key"], "wiki_es": None, "wiki_en": None, "geo_es": [], "geo_en": []}

  for lang, gkey in [("es", "geo_es"), ("en", "geo_en")]:
    try:
      coord = urllib.parse.quote(f"{lat}|{lng}")
      url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={coord}&gsradius=10000&gslimit=5&format=json"
      d = fetch_json(url)
      res[gkey] = [g["title"] for g in d.get("query", {}).get("geosearch", [])]
    except Exception as e:
      res[gkey + "_err"] = str(e)

  for lang, field, gkey in [("es", "wiki_es", "geo_es"), ("en", "wiki_en", "geo_en")]:
    try:
      q = urllib.parse.quote(f"{n} {c}")
      url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=5&format=json"
      d = fetch_json(url)
      hits = d.get("query", {}).get("search", [])
      titles = [h["title"] for h in hits]
      for gt in res.get(gkey, []):
        if n.lower().split()[0] in gt.lower() and gt not in titles:
          titles.insert(0, gt)
      if not titles and res.get(gkey):
        titles = res[gkey][:2]
      if titles:
        t = urllib.parse.quote(titles[0])
        u2 = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&exchars=4000&titles={t}&redirects=1&format=json"
        d2 = fetch_json(u2)
        pages = d2.get("query", {}).get("pages", {})
        for pid, p in pages.items():
          if pid != "-1":
            res[field] = {
              "title": p.get("title"),
              "candidates": titles,
              "extract": p.get("extract", "")
            }
            break
    except Exception as e:
      res[field + "_err"] = str(e)
  return res


def main():
  with open(INPUT_PATH, "r", encoding="utf-8") as f:
    items = json.load(f)
  out = {}
  with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    futs = {ex.submit(query_wiki, it): it for it in items}
    for fut in concurrent.futures.as_completed(futs):
      r = fut.result()
      out[r["key"]] = r
  with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
  print("WIKI_DONE", len(out))


if __name__ == "__main__":
  main()
