import json
import math
import os
import time
import urllib.parse
import urllib.request

BASE = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\QUIPU\_shared"
INPUT_PATH = r"f:\Active Projects\Project 1509 - SVEA\tests\c044_input.json"
OUT_JSON = r"f:\Active Projects\Project 1509 - SVEA\tests\c044_dossier.json"

with open(INPUT_PATH, "r", encoding="utf-8") as f:
  items = json.load(f)


def haversine_km(lat1, lon1, lat2, lon2):
  R = 6371.0
  dlat = math.radians(lat2 - lat1)
  dlon = math.radians(lon2 - lon1)
  a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
  return 2 * R * math.asin(math.sqrt(min(1.0, a)))


# 1. Scan local raw sources near coordinates or matching names
local_records = {it["key"]: [] for it in items}
src_dir = os.path.join(BASE, "settlement_sources")
for fn in os.listdir(src_dir):
  if not fn.endswith(".json"):
    continue
  fpath = os.path.join(src_dir, fn)
  try:
    with open(fpath, "r", encoding="utf-8") as f:
      data = json.load(f)
  except Exception:
    continue
  rows = data if isinstance(data, list) else data.get("features", data.get("settlements", data.get("places", [])))
  if isinstance(data, dict) and not rows:
    rows = list(data.values())
  for row in rows:
    if not isinstance(row, dict):
      continue
    lat = row.get("lat") or row.get("latitude")
    lon = row.get("lng") or row.get("lon") or row.get("longitude")
    if lat is None and "geometry" in row and isinstance(row["geometry"], dict):
      coords = row["geometry"].get("coordinates", [])
      if len(coords) >= 2:
        lon, lat = coords[0], coords[1]
    if lat is None or lon is None:
      continue
    try:
      lat, lon = float(lat), float(lon)
    except Exception:
      continue
    for it in items:
      if haversine_km(it["ll"][0], it["ll"][1], lat, lon) < 2.0:
        rec = dict(row)
        rec["_file"] = fn
        local_records[it["key"]].append(rec)

raw_sites_dir = os.path.join(BASE, "sites_quipu_andes_cone", "0.raw_sites")
if os.path.exists(raw_sites_dir):
  for fn in os.listdir(raw_sites_dir):
    if not fn.endswith(".json") and not fn.endswith(".geojson"):
      continue
    fpath = os.path.join(raw_sites_dir, fn)
    try:
      with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    except Exception:
      continue
    rows = data if isinstance(data, list) else data.get("features", [])
    for row in rows:
      if not isinstance(row, dict):
        continue
      props = row.get("properties", row)
      lat = props.get("lat") or props.get("latitude")
      lon = props.get("lng") or props.get("lon") or props.get("longitude")
      if lat is None and "geometry" in row and isinstance(row["geometry"], dict):
        coords = row["geometry"].get("coordinates", [])
        if len(coords) >= 2:
          lon, lat = coords[0], coords[1]
      if lat is None or lon is None:
        continue
      try:
        lat, lon = float(lat), float(lon)
      except Exception:
        continue
      for it in items:
        if haversine_km(it["ll"][0], it["ll"][1], lat, lon) < 2.0:
          rec = dict(props)
          rec["_file"] = "0.raw_sites/" + fn
          local_records[it["key"]].append(rec)


def wiki_get(lang, params):
  url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
  req = urllib.request.Request(url, headers={"User-Agent": "SVEA-QUIPU-Toponymy/1.0 (research)"})
  with urllib.request.urlopen(req, timeout=15) as resp:
    return json.loads(resp.read().decode("utf-8"))


results = {}
for idx, it in enumerate(items):
  key = it["key"]
  lat, lon = it["ll"]
  name = it["n"]
  country = it["c"]
  entry = {
    "input": it,
    "local": local_records[key][:5],
    "es_geo": [],
    "es_search": [],
    "en_geo": [],
    "extracts": {}
  }
  titles_to_fetch_es = []
  titles_to_fetch_en = []
  try:
    g = wiki_get("es", {
      "action": "query",
      "list": "geosearch",
      "gscoord": f"{lat}|{lon}",
      "gsradius": 10000,
      "gslimit": 5,
      "format": "json"
    })
    entry["es_geo"] = g.get("query", {}).get("geosearch", [])
    for hit in entry["es_geo"][:3]:
      titles_to_fetch_es.append(hit["title"])
  except Exception as e:
    entry["es_geo_err"] = str(e)

  try:
    s = wiki_get("es", {
      "action": "query",
      "list": "search",
      "srsearch": f'"{name}" {country}',
      "srlimit": 3,
      "format": "json"
    })
    entry["es_search"] = [x["title"] for x in s.get("query", {}).get("search", [])]
    for t in entry["es_search"][:2]:
      if t not in titles_to_fetch_es:
        titles_to_fetch_es.append(t)
  except Exception as e:
    entry["es_search_err"] = str(e)

  if titles_to_fetch_es:
    try:
      ex = wiki_get("es", {
        "action": "query",
        "prop": "extracts|coordinates",
        "exintro": False,
        "explaintext": True,
        "exchars": 3500,
        "titles": "|".join(titles_to_fetch_es[:4]),
        "format": "json"
      })
      for pid, pdata in ex.get("query", {}).get("pages", {}).items():
        if "missing" not in pdata:
          entry["extracts"]["es:" + pdata["title"]] = {
            "coords": pdata.get("coordinates"),
            "extract": pdata.get("extract", "")[:3500]
          }
    except Exception as e:
      entry["es_ex_err"] = str(e)

  # Also check English Wikipedia geosearch for archaeological sites or if es had few hits
  try:
    g_en = wiki_get("en", {
      "action": "query",
      "list": "geosearch",
      "gscoord": f"{lat}|{lon}",
      "gsradius": 10000,
      "gslimit": 3,
      "format": "json"
    })
    entry["en_geo"] = g_en.get("query", {}).get("geosearch", [])
    for hit in entry["en_geo"][:2]:
      titles_to_fetch_en.append(hit["title"])
  except Exception:
    pass

  if titles_to_fetch_en:
    try:
      ex = wiki_get("en", {
        "action": "query",
        "prop": "extracts|coordinates",
        "exintro": False,
        "explaintext": True,
        "exchars": 2500,
        "titles": "|".join(titles_to_fetch_en[:2]),
        "format": "json"
      })
      for pid, pdata in ex.get("query", {}).get("pages", {}).items():
        if "missing" not in pdata:
          entry["extracts"]["en:" + pdata["title"]] = {
            "coords": pdata.get("coordinates"),
            "extract": pdata.get("extract", "")[:2500]
          }
    except Exception:
      pass

  results[key] = entry
  if (idx + 1) % 15 == 0:
    print(f"Processed {idx + 1}/{len(items)}")
  time.sleep(0.05)

with open(OUT_JSON, "w", encoding="utf-8") as f:
  json.dump(results, f, ensure_ascii=False, indent=2)

print("Done. Saved", OUT_JSON)
