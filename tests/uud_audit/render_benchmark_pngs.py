"""Renders high-DPI benchmark .png plots for Phase 4 UUD visual auditing."""

import json
import math
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
AUDIT_DIR = os.path.dirname(os.path.abspath(__file__))
PNG_DIR = os.path.join(AUDIT_DIR, "pngs")
CHUNK_PATH = os.path.join(AUDIT_DIR, "chunk_stadester.json")
LOG_PATH = os.path.join(AUDIT_DIR, "merge_audit_log.json")
COAST_PATH = os.path.join(ROOT_DIR, "histmap", "1.data_raw", "population_regional", "_shared", "_gis_cache", "ne_50m_coastline.geojson")
BORDERS_PATH = os.path.join(ROOT_DIR, "histmap", "1.data_raw", "population_regional", "_shared", "_gis_cache", "ne_50m_admin_0_countries.geojson")

BENCHMARK_YEARS = [-1000, 1, 1000, 1300, 1500, 1800, 1950, 2025]

BBOXES = {
  "europe": (-10.0, 33.0, 35.0, 62.0),
  "greece_turkey": (19.0, 45.0, 34.0, 43.0),
}

INSET_SPECS = [
  ("london_se_england", (-0.50, 0.30, 51.28, 51.72), [1, 1800, 1950, 2025]),
  ("istanbul_marmara", (28.55, 29.45, 40.75, 41.30), [1000, 1500, 1950, 2025]),
  ("athens_attica", (23.40, 24.10, 37.75, 38.18), [-1000, 1, 1950, 2025]),
  ("malta", (14.15, 14.60, 35.78, 36.10), [1800, 2025]),
  ("paris_ile_de_france", (2.15, 2.55, 48.75, 48.95), [1800, 2025]),
  ("budapest_split_vs_merged", (18.85, 19.35, 47.30, 47.70), [1800, 1950]),
  ("berlin_split_vs_merged", (13.05, 13.80, 52.30, 52.70), [1800, 1950]),
  ("hamburg_altona", (9.65, 10.35, 53.35, 53.75), [1800, 1950]),
  ("pale_east_prussia_seam", (17.0, 34.0, 47.5, 58.0), [1800, 1950]),
  ("mongolia_steppe", (87.5, 120.0, 41.5, 52.2), [1000, 1800, 2025]),
  ("cairo_giza", (30.8, 31.8, 29.6, 30.5), [1500, 2025]),
  ("rabat_sale", (-7.0, -6.6, 33.8, 34.2), [2025]),
  ("tokyo_yokohama", (138.8, 140.8, 34.5, 36.5), [1800, 2025]),
  ("wuhan_sanmin", (113.5, 115.2, 29.8, 31.4), [1800, 2025]),
  ("nyc_newark", (-74.5, -73.5, 40.3, 41.2), [1800, 2025]),
  ("delhi_ncr", (76.8, 77.6, 28.2, 29.0), [2025]),
  ("mexico_city", (-99.5, -98.8, 19.0, 19.8), [1500, 2025]),
  ("sao_paulo", (-47.1, -46.1, -24.1, -23.2), [2025]),
  ("sydney_parramatta", (150.6, 151.4, -34.2, -33.5), [2025]),
  ("johannesburg_pretoria", (27.6, 28.5, -26.6, -25.5), [2025]),
]


def load_lines(arg0_path):
  """Extracts line segments from GeoJSON LineString/Polygon geometries."""
  if not os.path.exists(arg0_path):
    return []
  gj = json.load(open(arg0_path, encoding="utf-8"))
  segs = []
  for feat in gj.get("features", []):
    geom = feat.get("geometry") or {}
    gtype = geom.get("type")
    coords = geom.get("coordinates") or []
    if gtype == "LineString":
      if len(coords) >= 2:
        segs.append([(p[0], p[1]) for p in coords])
    elif gtype == "MultiLineString":
      for line in coords:
        if len(line) >= 2:
          segs.append([(p[0], p[1]) for p in line])
    elif gtype == "Polygon":
      for ring in coords:
        if len(ring) >= 2:
          segs.append([(p[0], p[1]) for p in ring])
    elif gtype == "MultiPolygon":
      for poly in coords:
        for ring in poly:
          if len(ring) >= 2:
            segs.append([(p[0], p[1]) for p in ring])
  return segs


def fmt_pop(arg0_val):
  """Formats population with compact k/M abbreviations."""
  v = float(arg0_val)
  if v >= 1e6:
    return f"{v/1e6:.2f}M"
  if v >= 1e3:
    return f"{v/1e3:.1f}k"
  return str(int(round(v)))


def get_pop_at_year(arg0_city, arg1_yr):
  """Gets population at exact year or nearest year within +/- 25 years."""
  pop = arg0_city.get("population") or {}
  sk = str(arg1_yr)
  if sk in pop and pop[sk] is not None and float(pop[sk]) > 0:
    return float(pop[sk])
  best_d = 9999
  best_v = 0.0
  for k, v in pop.items():
    try:
      yk = int(k)
      fv = float(v)
    except Exception:
      continue
    if fv > 0 and abs(yk - arg1_yr) <= 25 and abs(yk - arg1_yr) < best_d:
      best_d = abs(yk - arg1_yr)
      best_v = fv
  return best_v


def render_map(arg0_title, arg1_out_path, arg2_bbox, arg3_pts, arg4_coast, arg5_borders, arg6_max_labels=65):
  """Renders a single high-DPI map .png with collision-filtered labels."""
  xmin, xmax, ymin, ymax = arg2_bbox
  fig, ax = plt.subplots(figsize=(11, 8), dpi=300)
  ax.set_facecolor("#eef4f8")

  if arg5_borders:
    ax.add_collection(LineCollection(arg5_borders, colors="#c5ccd3", linewidths=0.5, zorder=1))
  if arg4_coast:
    ax.add_collection(LineCollection(arg4_coast, colors="#6d7c8a", linewidths=0.7, zorder=2))

  pts_sorted = sorted(arg3_pts, key=lambda r: r[2], reverse=True)
  if pts_sorted:
    xs = [p[1] for p in pts_sorted]
    ys = [p[0] for p in pts_sorted]
    sizes = [max(8.0, min(260.0, (math.log10(max(10.0, p[2])) - 1.5)*28.0)) for p in pts_sorted]
    colors = ["#c0392b" if p[4] else "#1f5a8a" for p in pts_sorted]
    ax.scatter(xs, ys, s=sizes, c=colors, alpha=0.78, edgecolors="#ffffff", linewidths=0.5, zorder=4)

  placed = []
  dx_tol = (xmax - xmin)*0.055
  dy_tol = (ymax - ymin)*0.028
  labels_drawn = 0
  for lat, lon, pop, name, is_merged in pts_sorted:
    if labels_drawn >= arg6_max_labels:
      break
    if any(abs(lat - py) < dy_tol and abs(lon - px) < dx_tol for py, px in placed):
      continue
    placed.append((lat, lon))
    lbl = f"{name} ({fmt_pop(pop)})"
    ax.annotate(
      lbl,
      (lon, lat),
      xytext=(3, 3),
      textcoords="offset points",
      fontsize=6.5,
      color="#7b1d14" if is_merged else "#102a43",
      fontweight="bold" if pop >= 100000 else "normal",
      bbox={"boxstyle": "round,pad=0.12", "fc": "#ffffff", "ec": "none", "alpha": 0.72},
      zorder=5,
    )
    labels_drawn += 1

  ax.set_xlim(xmin, xmax)
  ax.set_ylim(ymin, ymax)
  ax.set_title(f"{arg0_title}  |  n={len(pts_sorted)} settlements  |  red=merged/reconciled", fontsize=10, fontweight="bold")
  ax.set_xlabel("Longitude")
  ax.set_ylabel("Latitude")
  ax.grid(True, linestyle=":", linewidth=0.4, color="#b0bec5", zorder=0)
  fig.tight_layout()
  fig.savefig(arg1_out_path, dpi=300)
  plt.close(fig)


def main():
  os.makedirs(PNG_DIR, exist_ok=True)
  data = json.load(open(CHUNK_PATH, encoding="utf-8"))
  audit_log = json.load(open(LOG_PATH, encoding="utf-8")) if os.path.exists(LOG_PATH) else []
  merged_keys = set()
  for ev in audit_log:
    for k in (ev.get("target"), ev.get("parent_key"), ev.get("kept"), ev.get("source")):
      if k:
        merged_keys.add(str(k))

  coast = load_lines(COAST_PATH)
  borders = load_lines(BORDERS_PATH)

  cities = []
  for k, c in data.items():
    coords = c.get("coords")
    if not isinstance(coords, list) or len(coords) < 2:
      continue
    lat, lon = float(coords[0]), float(coords[1])
    cities.append((k, c, lat, lon, k in merged_keys))

  rendered = 0
  for region_name, bbox in BBOXES.items():
    xmin, xmax, ymin, ymax = bbox
    for yr in BENCHMARK_YEARS:
      pts = []
      for k, c, lat, lon, is_m in cities:
        if ymin <= lat <= ymax and xmin <= lon <= xmax:
          pop = get_pop_at_year(c, yr)
          if pop > 0:
            pts.append((lat, lon, pop, c.get("name", k), is_m))
      out_p = os.path.join(PNG_DIR, f"{region_name}_{yr}.png")
      render_map(f"{region_name} ({yr})", out_p, bbox, pts, coast, borders, arg6_max_labels=65)
      rendered += 1

  for inset_name, bbox, yrs in INSET_SPECS:
    xmin, xmax, ymin, ymax = bbox
    for yr in yrs:
      pts = []
      for k, c, lat, lon, is_m in cities:
        if ymin <= lat <= ymax and xmin <= lon <= xmax:
          pop = get_pop_at_year(c, yr)
          if pop > 0:
            pts.append((lat, lon, pop, c.get("name", k), is_m))
      out_p = os.path.join(PNG_DIR, f"inset_{inset_name}_{yr}.png")
      render_map(f"Inset: {inset_name} ({yr})", out_p, bbox, pts, coast, borders, arg6_max_labels=55)
      rendered += 1

  print(f"[render_benchmark_pngs] Rendered {rendered} PNGs into {PNG_DIR}", flush=True)


if __name__ == "__main__":
  main()
