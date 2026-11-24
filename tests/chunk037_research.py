import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

data = json.load(open("tests/tmp_chunk037_research.json", encoding="utf-8"))
HEADERS = {
  "User-Agent": "Confoederatio-HistoricalToponymy/1.0 (https://confoederatio.org; contact@confoederatio.org)"
}


def fetch_json(url, retries=4):
  for attempt in range(retries):
    try:
      time.sleep(0.18)
      req = urllib.request.Request(url, headers=HEADERS)
      with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
      if e.code == 429:
        wait = 2.0 * (attempt + 1)
        time.sleep(wait)
        continue
      raise
    except Exception:
      if attempt == retries - 1:
        raise
      time.sleep(1.0)
  raise RuntimeError("Max retries exceeded")


for idx, it in enumerate(data):
  lat, lng = it["ll"]
  name = it["n"]
  country = it["c"]
  changed = False
  for lang in ("es", "en"):
    if f"{lang}_geo" not in it:
      it.pop(f"{lang}_geo_err", None)
      try:
        u = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=12000&gslimit=5&format=json"
        gs = fetch_json(u).get("query", {}).get("geosearch", [])
        it[f"{lang}_geo"] = [
          {"title": g["title"], "dist": round(g["dist"])} for g in gs
        ]
        changed = True
      except Exception as e:
        it[f"{lang}_geo_err"] = str(e)
    if f"{lang}_search" not in it:
      it.pop(f"{lang}_search_err", None)
      try:
        q = urllib.parse.quote(f"{name} {country}")
        u = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        sr = fetch_json(u).get("query", {}).get("search", [])
        it[f"{lang}_search"] = [
          {
            "title": s["title"],
            "snippet": re.sub(r"<[^>]+>", "", s.get("snippet", "")),
          }
          for s in sr
        ]
        changed = True
      except Exception as e:
        it[f"{lang}_search_err"] = str(e)
    if not it.get(f"{lang}_extracts"):
      cand = []
      for g in it.get(f"{lang}_geo", [])[:2]:
        cand.append(g["title"])
      for s in it.get(f"{lang}_search", [])[:2]:
        if s["title"] not in cand:
          cand.append(s["title"])
      extracts = {}
      if cand:
        try:
          titles_p = urllib.parse.quote("|".join(cand[:3]))
          u = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&explaintext=1&exchars=5000&titles={titles_p}&format=json"
          pages = fetch_json(u).get("query", {}).get("pages", {})
          for pid, p in pages.items():
            if int(pid) > 0:
              extracts[p.get("title")] = {
                "extract": p.get("extract", ""),
                "coords": p.get("coordinates", []),
              }
          it[f"{lang}_extracts"] = extracts
          it.pop(f"{lang}_extract_err", None)
          changed = True
        except Exception as e:
          it[f"{lang}_extract_err"] = str(e)
  if changed and idx % 10 == 9:
    with open("tests/tmp_chunk037_research.json", "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved through {idx + 1}/90", flush=True)

with open("tests/tmp_chunk037_research.json", "w", encoding="utf-8") as f:
  json.dump(data, f, ensure_ascii=False, indent=2)
print("Completed all 90!")
