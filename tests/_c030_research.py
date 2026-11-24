import concurrent.futures
import glob
import json
import os
import re
import urllib.parse
import urllib.request

UA = "SVEA-Research/1.0 (https://confoederatio.org)"

def fetch_json(url):
  req = urllib.request.Request(url, headers={"User-Agent": UA})
  with urllib.request.urlopen(req, timeout=15) as r:
    return json.loads(r.read().decode("utf-8"))

def wiki_lookup(item):
  lat, lng = item["ll"]
  name = item["n"]
  country = item["c"]
  out = {"key": item["key"], "es": [], "en": [], "wd": []}

  for lang in ("es", "en"):
    # Geosearch within 10km
    try:
      u = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
      d = fetch_json(u)
      geo = d.get("query", {}).get("geosearch", [])
    except Exception as e:
      geo = []

    # Text search
    try:
      q = urllib.parse.quote(f"{name} {country}")
      u2 = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
      d2 = fetch_json(u2)
      sr = d2.get("query", {}).get("search", [])
    except Exception:
      sr = []

    titles = []
    seen = set()
    for g in geo:
      t = g["title"]
      if t not in seen:
        seen.add(t)
        titles.append((t, f"geo:{int(g.get('dist', 0))}m"))
    for s in sr:
      t = s["title"]
      if t not in seen:
        seen.add(t)
        titles.append((t, "search"))

    if titles:
      top_titles = [t[0] for t in titles[:4]]
      try:
        ts = urllib.parse.quote("|".join(top_titles))
        u3 = f"https://{lang}.wikipedia.org/w/api.php?action=query&titles={ts}&prop=extracts|revisions&explaintext=1&exchars=1800&rvprop=content&rvslots=main&format=json"
        # Actually just extracts first + infobox via wikitext slice
        u3 = f"https://{lang}.wikipedia.org/w/api.php?action=query&titles={ts}&prop=extracts&explaintext=1&exchars=2500&format=json"
        d3 = fetch_json(u3)
        pages = d3.get("query", {}).get("pages", {})
        by_t = {p.get("title"): p.get("extract", "") for p in pages.values()}
        for t, how in titles[:4]:
          ext = by_t.get(t, "")
          if ext:
            out[lang].append({"title": t, "how": how, "extract": ext[:1800]})
      except Exception:
        pass
  return out

def scan_local_quipu(items):
  # Scan QUIPU gazetteer / json / csv / md files for mentions of keys or names
  root = "histmap/1.data_raw/population_regional/QUIPU"
  files = []
  for ext in ("*.json", "*.json5", "*.csv"):
    files.extend(glob.glob(os.path.join(root, "**", ext), recursive=True))
  hits = {it["key"]: [] for it in items}
  for fp in files:
    try:
      txt = open(fp, encoding="utf-8", errors="ignore").read()
    except Exception:
      continue
    rel = os.path.relpath(fp, root)
    for it in items:
      k = it["key"]
      n = it["n"]
      if k in txt or (len(n) >= 5 and n in txt):
        # Find line snippets
        for line in txt.splitlines():
          if k in line or n in line:
            hits[k].append(f"[{rel}] {line.strip()[:260]}")
            if len(hits[k]) >= 3:
              break
  return hits

def main():
  items = json.load(open("tests/_c030_input.json", encoding="utf-8"))
  local_hits = scan_local_quipu(items)
  results = {}
  with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    futs = {ex.submit(wiki_lookup, it): it["key"] for it in items}
    for f in concurrent.futures.as_completed(futs):
      r = f.result()
      r["local"] = local_hits.get(r["key"], [])
      results[r["key"]] = r
  with open("tests/_c030_research.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
  print(f"Done: {len(results)} settlements")

if __name__ == "__main__":
  main()
