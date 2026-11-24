import glob
import json
import os
import time
import urllib.parse
import urllib.request

with open("tests/tmp_quipu_029_wiki.json", "r", encoding="utf-8") as f:
  wiki_prev = json.load(f)

from tmp_quipu_029_lookup import ITEMS, HEADERS, fetch_json

# 1. Retry Wikipedia geosearch + search for items that had 429 or missing
for idx, it in enumerate(ITEMS):
  prev = wiki_prev[idx]
  if "geo_err" in prev or "search_err" in prev:
    lat, lng = it["ll"]
    name = it["n"]
    country = it["c"]
    if "geo_err" in prev:
      prev.pop("geo_err", None)
      try:
        gurl = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}%7C{lng}&gsradius=10000&gslimit=5&format=json"
        gd = fetch_json(gurl)
        prev["geo"] = [{"title": g["title"], "dist": g["dist"]} for g in gd.get("query", {}).get("geosearch", [])]
      except Exception as e:
        prev["geo_err"] = str(e)
      time.sleep(0.25)
    if "search_err" in prev:
      prev.pop("search_err", None)
      try:
        q = urllib.parse.quote(f"{name} {country}")
        surl = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        sd = fetch_json(surl)
        prev["search"] = [{"title": s["title"], "snippet": s["snippet"]} for s in sd.get("query", {}).get("search", [])]
      except Exception as e:
        prev["search_err"] = str(e)
      time.sleep(0.25)

with open("tests/tmp_quipu_029_wiki.json", "w", encoding="utf-8") as f:
  json.dump(wiki_prev, f, ensure_ascii=False, indent=2)

# 2. Match against local QUIPU settlement_sources and sites_quipu_andes_cone
local_matches = {it["key"]: [] for it in ITEMS}
target_by_ll = [(it["key"], it["ll"][0], it["ll"][1], it["n"].lower()) for it in ITEMS]

for pat in [
  "histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/*.json",
  "histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/*.json",
  "histmap/1.data_raw/population_regional/QUIPU/*/*.json",
  "histmap/1.data_raw/population_regional/QUIPU/*/*.json5",
]:
  for fp in sorted(glob.glob(pat)):
    if not fp.endswith(".json"):
      continue
    try:
      with open(fp, "r", encoding="utf-8") as f:
        data = json.load(f)
    except Exception:
      continue
    rows = data if isinstance(data, list) else (data.get("settlements") or data.get("features") or data.get("sites") or [])
    if not isinstance(rows, list):
      continue
    bn = os.path.basename(fp)
    for r in rows:
      if not isinstance(r, dict):
        continue
      rlat = r.get("lat") or r.get("latitude") or (r.get("ll")[0] if isinstance(r.get("ll"), list) and len(r.get("ll")) == 2 else None)
      rlng = r.get("lng") or r.get("lon") or r.get("longitude") or (r.get("ll")[1] if isinstance(r.get("ll"), list) and len(r.get("ll")) == 2 else None)
      if rlat is None or rlng is None:
        continue
      try:
        rlat, rlng = float(rlat), float(rlng)
      except Exception:
        continue
      for k, tlat, tlng, tn in target_by_ll:
        if abs(rlat - tlat) < 0.005 and abs(rlng - tlng) < 0.005:
          local_matches[k].append({"file": bn, "record": {kk: vv for kk, vv in r.items() if kk != "geometry"}})

with open("tests/tmp_quipu_029_local.json", "w", encoding="utf-8") as f:
  json.dump(local_matches, f, ensure_ascii=False, indent=2)

print("Updated wiki and saved local matches:", sum(1 for v in local_matches.values() if v))
