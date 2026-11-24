import json, os, glob, math, time, urllib.parse, urllib.request

with open("tests/_c048_research.json", encoding="utf-8") as f:
  data = json.load(f)

HEADERS = {"User-Agent": "SVEA-Historical-Toponymy-Research/1.0 (https://confoederatio.org; polite sequential)"}

def fetch_json(url):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=15) as resp:
    return json.loads(resp.read().decode("utf-8"))

# Retry any item with ERR:HTTP Error 429 or missing extracts
for i, r in enumerate(data):
  need_geo = isinstance(r.get("es_geo"), str) and "429" in r["es_geo"]
  need_search = isinstance(r.get("es_search"), str) and "429" in r["es_search"]
  if not (need_geo or need_search):
    continue
  lat, lng = r["ll"]
  n, c = r["n"], r["c"]
  if need_geo:
    try:
      gs_url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
      gs = fetch_json(gs_url).get("query", {}).get("geosearch", [])
      r["es_geo"] = [(g["title"], round(g["dist"])) for g in gs]
    except Exception as e:
      r["es_geo"] = f"ERR:{e}"
    time.sleep(0.15)
  if need_search:
    try:
      q = urllib.parse.quote(f"{n} {c}")
      ts_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
      ts = fetch_json(ts_url).get("query", {}).get("search", [])
      r["es_search"] = [s["title"] for s in ts]
    except Exception as e:
      r["es_search"] = f"ERR:{e}"
    time.sleep(0.15)

  titles = []
  if isinstance(r.get("es_geo"), list) and r["es_geo"]:
    titles.append(r["es_geo"][0][0])
  if isinstance(r.get("es_search"), list):
    for t in r["es_search"][:2]:
      if t not in titles:
        titles.append(t)
  r["extracts"] = {}
  for t in titles[:2]:
    try:
      ex_url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={urllib.parse.quote(t)}&format=json"
      pages = fetch_json(ex_url).get("query", {}).get("pages", {})
      for pid, p in pages.items():
        if "extract" in p:
          r["extracts"][t] = p["extract"][:700]
      time.sleep(0.12)
    except Exception:
      pass

with open("tests/_c048_research.json", "w", encoding="utf-8") as f:
  json.dump(data, f, ensure_ascii=False, indent=2)

# Also match against local QUIPU chapter settlement files by coordinate/name
def dist_km(lat1, lon1, lat2, lon2):
  R = 6371.0
  p = math.pi/180
  a = 0.5 - math.cos((lat2-lat1)*p)/2 + math.cos(lat1*p)*math.cos(lat2*p)*(1-math.cos((lon2-lon1)*p))/2
  return 2*R*math.asin(math.sqrt(max(0,a)))

local_matches = {r["key"]: [] for r in data}
for p in glob.glob("histmap/1.data_raw/population_regional/QUIPU/*/*/*_settlements.json"):
  try:
    obj = json.load(open(p, encoding="utf-8"))
    rows = obj if isinstance(obj, list) else obj.get("settlements", obj.get("records", []))
    if isinstance(rows, dict): rows = list(rows.values())
    bn = os.path.basename(p).replace("_settlements.json", "")
    for row in rows:
      if not isinstance(row, dict): continue
      rlat = row.get("lat")
      rlng = row.get("lng", row.get("lon"))
      if rlat is None and isinstance(row.get("coords"), list) and len(row["coords"]) >= 2:
        rlat, rlng = row["coords"][0], row["coords"][1]
      if rlat is None or rlng is None: continue
      rlat, rlng = float(rlat), float(rlng)
      for r in data:
        if dist_km(r["ll"][0], r["ll"][1], rlat, rlng) <= 1.5:
          local_matches[r["key"]].append({
            "file": bn,
            "name": row.get("name"),
            "fy": row.get("foundation_year"),
            "src": row.get("source"),
            "notes": row.get("notes"),
            "other": row.get("other_names"),
            "years": sorted(list((row.get("population") or row.get("years") or {}).keys()))[:5] if isinstance(row.get("population") or row.get("years"), dict) else None
          })
  except Exception:
    pass

with open("tests/_c048_digest2.txt", "w", encoding="utf-8") as f:
  for i, r in enumerate(data):
    f.write(f"=== [{i}] {r['key']} | n={r['n']} | c={r['c']} | r={r['r']} | ll={r['ll']} | ey={r['ey']}..{r['ly']} | al={r['al']} | ex={r['ex']} ===\n")
    f.write(f"  es_geo: {r.get('es_geo')}\n")
    f.write(f"  es_search: {r.get('es_search')}\n")
    for t, txt in r.get("extracts", {}).items():
      f.write(f"  [{t}]: {txt.replace(chr(10), ' ')}\n")
    if local_matches[r["key"]]:
      f.write(f"  LOCAL: {json.dumps(local_matches[r['key']], ensure_ascii=False)}\n")
    f.write("\n")

print("Done. Local matches:", sum(1 for v in local_matches.values() if v))
