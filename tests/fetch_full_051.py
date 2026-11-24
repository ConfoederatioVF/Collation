import concurrent.futures
import json
import math
import re
import urllib.parse
import urllib.request

HEADERS = {"User-Agent": "SVEA-ToponymyResearch/1.0 (https://confoederatio.org)"}

def fetch_json(url):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=15) as resp:
    return json.loads(resp.read().decode("utf-8"))

def haversine(la1, lo1, la2, lo2):
  d1 = math.radians(la2 - la1)
  d2 = math.radians(lo2 - lo1)
  a = math.sin(d1/2)**2 + math.cos(math.radians(la1))*math.cos(math.radians(la2))*math.sin(d2/2)**2
  return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))

def fetch_page_full(lang, title):
  url = (
    f"https://{lang}.wikipedia.org/w/api.php?action=query"
    f"&prop=extracts|revisions|coordinates&explaintext=1&exchars=4500"
    f"&rvprop=content&rvslots=main&rvsection=0"
    f"&titles={urllib.parse.quote(title)}&format=json"
  )
  data = fetch_json(url)
  pages = data.get("query", {}).get("pages", {})
  for p in pages.values():
    if "missing" in p:
      return None
    wikitext = ""
    revs = p.get("revisions") or []
    if revs:
      wikitext = revs[0].get("slots", {}).get("main", {}).get("*", "")
    return {
      "lang": lang,
      "title": p.get("title"),
      "coords": p.get("coordinates"),
      "extract": p.get("extract", ""),
      "infobox": wikitext[:2500]
    }
  return None

def main():
  dossier = json.load(open("tests/quipu_051_dossier.json", encoding="utf-8"))
  
  # Select candidate pages for each item
  def process(item):
    lat, lng = item["ll"]
    cands = []
    seen = set()
    # Geo hits within 10km
    for h in item["geo_hits"]:
      if "title" in h and (h["lang"], h["title"]) not in seen:
        seen.add((h["lang"], h["title"]))
        cands.append((h["lang"], h["title"], f"geo:{round(h['dist'])}m"))
    # Search hits
    for h in item["search_hits"]:
      if "title" in h and ("es", h["title"]) not in seen:
        dist_note = "srch"
        if h.get("coords"):
          c0 = h["coords"][0]
          d = haversine(lat, lng, c0["lat"], c0["lon"])
          dist_note = f"srch:{round(d, 1)}km"
        seen.add(("es", h["title"]))
        cands.append(("es", h["title"], dist_note))
    
    # Also search en.wikipedia if no geo hits
    if not any(h.get("title") for h in item["geo_hits"]):
      q = f'"{item["n"]}" {item["c"]}'
      try:
        u = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&srlimit=2&format=json"
        for h in fetch_json(u).get("query", {}).get("search", []):
          if ("en", h["title"]) not in seen:
            seen.add(("en", h["title"]))
            cands.append(("en", h["title"], "en_srch"))
      except Exception:
        pass

    pages = []
    for lang, title, src in cands[:4]:
      try:
        info = fetch_page_full(lang, title)
        if info:
          info["src"] = src
          if info.get("coords"):
            c0 = info["coords"][0]
            info["dist_km"] = round(haversine(lat, lng, c0["lat"], c0["lon"]), 2)
          pages.append(info)
      except Exception as e:
        pages.append({"lang": lang, "title": title, "src": src, "error": str(e)})
    return {"meta": {k: item[k] for k in ("key", "n", "c", "r", "ll", "ey", "ly")}, "pages": pages}

  out = []
  with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    for r in ex.map(process, dossier):
      out.append(r)

  with open("tests/quipu_051_full.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

  # Write concise readable text summary
  lines = []
  for idx, r in enumerate(out):
    m = r["meta"]
    lines.append(f"=== [{idx:02d}] {m['key']} | n={m['n']} | c={m['c']} | r={m['r']} | ll={m['ll']} | ey={m['ey']} ly={m['ly']} ===")
    for p in r["pages"]:
      lines.append(f"  -- [{p.get('lang')}] {p.get('title')} ({p.get('src')}, dist_km={p.get('dist_km')}) --")
      ib = p.get("infobox", "")
      # extract key infobox lines
      for line in ib.splitlines():
        if re.search(r"fundaci|creaci|nombre|otros|fundador|fecha|erecci|establec|año|year|founded|established|native|other_name|type|tipo|categor", line, re.I):
          lines.append(f"    IB: {line.strip()[:160]}")
      ext = (p.get("extract") or "").replace("\n", " ")
      lines.append(f"    EXT: {ext[:1200]}")
    lines.append("")
  with open("tests/quipu_051_summary.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
  print("Wrote tests/quipu_051_summary.txt, lines=", len(lines))

if __name__ == "__main__":
  main()
