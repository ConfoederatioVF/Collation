import json
import time
import urllib.error
import urllib.parse
import urllib.request

HEADERS = {
  "User-Agent": "OperationViscountToponymy/1.0 (https://confoederatio.org; contact@confoederatio.org)"
}


def fetch_json(url, retries=4):
  delay = 1.5
  for attempt in range(retries):
    try:
      req = urllib.request.Request(url, headers=HEADERS)
      with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
      if e.code == 429 and attempt < retries - 1:
        time.sleep(delay)
        delay *= 2
        continue
      raise


def query_wiki(lang, params):
  qs = urllib.parse.urlencode(params)
  url = f"https://{lang}.wikipedia.org/w/api.php?{qs}"
  time.sleep(0.22)
  return fetch_json(url)


def main():
  with open("tests/input_015.json", "r", encoding="utf-8") as f:
    items = json.load(f)

  results = []
  all_titles = set()

  for idx, item in enumerate(items):
    key = item["key"]
    name = item["n"]
    country = item["c"]
    region = item["r"]
    lat, lng = item["ll"]

    out = {
      "key": key,
      "n": name,
      "c": country,
      "r": region,
      "ll": [lat, lng],
      "es_geo": [],
      "es_search": [],
      "en_geo": [],
      "en_search": [],
      "pages": {},
    }

    try:
      geo = query_wiki(
        "es",
        {
          "action": "query",
          "list": "geosearch",
          "gscoord": f"{lat}|{lng}",
          "gsradius": 10000,
          "gslimit": 5,
          "format": "json",
        },
      )
      out["es_geo"] = [
        {"title": g["title"], "dist": g["dist"]}
        for g in geo.get("query", {}).get("geosearch", [])
      ]
    except Exception as e:
      out["es_geo_err"] = str(e)

    try:
      sr = query_wiki(
        "es",
        {
          "action": "query",
          "list": "search",
          "srsearch": f"{name} {country}",
          "srlimit": 5,
          "format": "json",
        },
      )
      out["es_search"] = [
        s["title"] for s in sr.get("query", {}).get("search", [])
      ]
    except Exception as e:
      out["es_search_err"] = str(e)

    if not out["es_geo"] and not out["es_search"]:
      try:
        sr_en = query_wiki(
          "en",
          {
            "action": "query",
            "list": "search",
            "srsearch": f"{name} {country}",
            "srlimit": 3,
            "format": "json",
          },
        )
        out["en_search"] = [
          s["title"] for s in sr_en.get("query", {}).get("search", [])
        ]
      except Exception:
        pass

    cand_titles = []
    for g in out["es_geo"][:2]:
      if g["title"] not in cand_titles:
        cand_titles.append(g["title"])
    for t in out["es_search"][:2]:
      if t not in cand_titles:
        cand_titles.append(t)
    out["cand_titles"] = cand_titles
    for t in cand_titles:
      all_titles.add(t)

    results.append(out)
    if (idx + 1) % 15 == 0:
      print(f"Searched {idx + 1}/90...", flush=True)

  # Batch fetch page extracts & infoboxes from es.wikipedia
  page_cache = {}
  title_list = sorted(all_titles)
  for i in range(0, len(title_list), 10):
    batch = title_list[i : i + 10]
    try:
      data = query_wiki(
        "es",
        {
          "action": "query",
          "prop": "extracts|revisions",
          "explaintext": True,
          "exchars": 3500,
          "rvprop": "content",
          "rvslots": "main",
          "titles": "|".join(batch),
          "format": "json",
        },
      )
      for pid, pinfo in data.get("query", {}).get("pages", {}).items():
        if int(pid) > 0:
          title = pinfo.get("title", "")
          extract = pinfo.get("extract", "")
          wikitext = ""
          revs = pinfo.get("revisions", [])
          if revs:
            wikitext = revs[0].get("slots", {}).get("main", {}).get("*", "")[:3000]
          page_cache[title] = {"extract": extract, "infobox": wikitext}
    except Exception as e:
      print("Batch fetch err:", e, flush=True)

  for out in results:
    for t in out["cand_titles"]:
      if t in page_cache:
        out["pages"][t] = page_cache[t]

  with open("tests/wiki_report.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
  print(f"Done: {len(results)} items, {len(page_cache)} unique es.wiki pages fetched")


if __name__ == "__main__":
  main()
