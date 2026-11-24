import json
import math
import re

with open("tests/lookup_chunk049.py", "r", encoding="utf-8") as f:
  src = f.read()
ns = {}
exec(src.split("HEADERS =")[0], ns)
SETTLEMENTS = ns["SETTLEMENTS"]

with open("tests/wiki_lookup_049.json", "r", encoding="utf-8") as f:
  lookup = {x["key"]: x for x in json.load(f)}

with open("tests/wiki_extracts_049.json", "r", encoding="utf-8") as f:
  extracts = json.load(f)

def haversine(lat1, lon1, lat2, lon2):
  R = 6371.0
  p1, p2 = math.radians(lat1), math.radians(lat2)
  dp = math.radians(lat2 - lat1)
  dl = math.radians(lon2 - lon1)
  a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
  return 2 * R * math.asin(math.sqrt(a))

out_lines = []
for idx, s in enumerate(SETTLEMENTS, 1):
  k = s["key"]
  lat, lon = s["ll"]
  lk = lookup.get(k, {})
  out_lines.append(f"=== {idx}. {k} | n={s['n']} | c={s['c']} | r={s['r']} | ll={s['ll']} | ey={s['ey']} ly={s['ly']} | al={s.get('al',[])} | ex={s.get('ex',[])} ===")
  out_lines.append(f"  geo: {lk.get('geo', [])} | search: {lk.get('search', [])}")
  # Find extracts matching geo or search or close coords
  cand_titles = []
  for g in lk.get("geo", []):
    if g["title"] not in cand_titles:
      cand_titles.append(g["title"])
  for t in lk.get("search", []):
    if t not in cand_titles:
      cand_titles.append(t)
  # Also check any extract within 15km or containing s['n']
  for title, info in extracts.items():
    for c in info.get("coords", []):
      d = haversine(lat, lon, c["lat"], c["lon"])
      if d < 15.0 and title not in cand_titles:
        cand_titles.append(title)
  for t in cand_titles[:4]:
    info = extracts.get(t)
    if not info:
      continue
    ext = info.get("extract", "").replace("\n", " ")
    # Check coord dist if any
    d_str = ""
    if info.get("coords"):
      c0 = info["coords"][0]
      d_str = f" [dist={haversine(lat, lon, c0['lat'], c0['lon']):.1f}km]"
    out_lines.append(f"  [{t}]{d_str}: {ext[:900]}")

with open("tests/summary_049.txt", "w", encoding="utf-8") as f:
  f.write("\n".join(out_lines))
print(f"Wrote {len(out_lines)} lines")
