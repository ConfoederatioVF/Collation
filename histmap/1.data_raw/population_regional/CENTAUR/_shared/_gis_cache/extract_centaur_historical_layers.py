"""Extracts North American historical polity snapshots from saves/atlas_defacto.naissance
into compact GeoJSON FeatureCollections under _shared/_gis_cache/historical_layers/.
"""

import json
import pathlib
import sys
from shapely.geometry import shape, mapping

sys.stdout.reconfigure(encoding="utf-8")

CACHE_DIR = pathlib.Path(__file__).resolve().parent
CENTAUR_DIR = CACHE_DIR.parents[1]
SVEA_ROOT = CENTAUR_DIR.parents[3]
NAISSANCE_PATH = SVEA_ROOT / "saves" / "atlas_defacto.naissance"
OUT_DIR = CACHE_DIR / "historical_layers"


def year_to_ts(year_int, mid_year=False):
  """Converts positive proleptic Gregorian year to .naissance minute-epoch timestamp."""
  ym1 = year_int - 1
  days = 365 * year_int + ym1 // 4 - ym1 // 100 + ym1 // 400 + 1
  if mid_year:
    days += 181
  return days * 1440


def in_centaur_bbox(geom):
  """Checks whether any ring coordinate lies within North America / Greenland / Hawaii / Samoa."""
  if not isinstance(geom, dict):
    return False
  stack = [geom.get("coordinates", [])]
  while stack:
    item = stack.pop()
    if isinstance(item, list) and item:
      if isinstance(item[0], (int, float)):
        lon, lat = float(item[0]), float(item[1])
        if (-179.0 <= lon <= -42.0 and 16.0 <= lat <= 84.0) or (-42.0 <= lon <= -11.0 and 59.0 <= lat <= 84.0):
          return True
      else:
        stack.extend(item)
  return False


def evaluate_history_at(polity_obj, target_ts):
  """Walks sorted keyframe timestamps up to target_ts to resolve active geometry & metadata."""
  hist = polity_obj.get("history")
  if not isinstance(hist, dict) or not hist:
    return None
  meta = dict(polity_obj.get("metadata") or {})
  geom = None
  symbol = {}
  props = {}
  active = False
  for ts_str, tv in sorted(hist.items(), key=lambda kv: int(kv[0])):
    ts_val = int(ts_str)
    if ts_val > target_ts:
      break
    if not isinstance(tv, list) or not tv:
      continue
    first = tv[0]
    if first is None:
      active = False
      geom = None
      continue
    if isinstance(first, dict):
      if "coordinates" in first:
        geom = first
        active = True
      elif isinstance(first.get("geometry"), dict):
        geom = first["geometry"]
        active = True
    for el in tv[1:]:
      if not isinstance(el, dict):
        continue
      if "polygonFill" in el or "lineWidth" in el:
        symbol.update(el)
      else:
        props.update(el)
  if not active or geom is None:
    return None
  merged_props = {
    "id": polity_obj.get("id") or props.get("id") or meta.get("state_id"),
    "name": props.get("name") or meta.get("name") or "",
    "parent": props.get("parent") or meta.get("parent") or "",
    "control_type": props.get("control_type") or meta.get("control_type") or "",
    "polygonFill": symbol.get("polygonFill") or meta.get("polygonFill") or "#888888",
  }
  return {"type": "Feature", "properties": merged_props, "geometry": geom}


def main():
  OUT_DIR.mkdir(parents=True, exist_ok=True)
  print(f"Loading {NAISSANCE_PATH} ...")
  with open(NAISSANCE_PATH, "r", encoding="utf-8") as fh:
    data = json.load(fh)

  na_candidates = []
  for pid, pobj in data.items():
    if pid == "map_settings" or not isinstance(pobj, dict):
      continue
    hist = pobj.get("history")
    if not isinstance(hist, dict):
      continue
    hit = False
    for tv in hist.values():
      if isinstance(tv, list) and tv and isinstance(tv[0], dict):
        g = tv[0] if "coordinates" in tv[0] else tv[0].get("geometry")
        if g and in_centaur_bbox(g):
          hit = True
          break
    if hit:
      na_candidates.append((pid, pobj))
  print(f"Filtered {len(na_candidates)} North American / Greenland / Pacific candidate polities.")

  snapshots = [
    ("1000", 1000, False),
    ("1250", 1250, False),
    ("1500", 1500, False),
    ("1650", 1650, False),
    ("1707_mid", 1707, True),
    ("1750", 1750, False),
    ("1754_mid", 1754, True),
    ("1763_mid", 1763, True),
    ("1775_mid", 1775, True),
    ("1782", 1782, False),
    ("1784", 1784, False),
    ("1815_mid", 1815, True),
    ("1821_mid", 1821, True),
    ("1850_mid", 1850, True),
    ("1867_mid", 1867, True),
    ("1890", 1890, False),
  ]

  summary = {}
  for tag, yr, mid in snapshots:
    target_ts = year_to_ts(yr, mid)
    feats = []
    names = []
    for pid, pobj in na_candidates:
      feat = evaluate_history_at(pobj, target_ts)
      if feat is None or not in_centaur_bbox(feat["geometry"]):
        continue
      try:
        shp = shape(feat["geometry"]).buffer(0)
        if shp.is_empty:
          continue
        feat["geometry"] = mapping(shp)
      except Exception:
        continue
      feats.append(feat)
      names.append(f"{pid}:{feat['properties']['name']}")
    out_p = OUT_DIR / f"atlas_na_{tag}.geojson"
    out_p.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")
    summary[tag] = names
    print(f"  [{tag}] {len(feats)} active polities -> {out_p.name}")

  (OUT_DIR / "atlas_na_snapshots_summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
  )


if __name__ == "__main__":
  main()
