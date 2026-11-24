"""Builds the pre-computed demographic, spatial and urban-hierarchy JSON cache for Project NICETHI.

Pure NumPy/PIL/Shapely data preparation script (zero Matplotlib imports) that aggregates:
  1. Per-chapter total & sub-regional population trajectories from `2.population_rasters/popc_<yr>.png`.
  2. Exact spherical sub-regional areas (km²) and end-epoch population densities (inhabitants / km²).
  3. Deduplicated settlement gazetteer trajectories, active counts, top named cities and Zipf rank-size vectors.
  4. Pan-NICETHI 128-year secular trajectories across 6 macro-regions + 5-epoch urban rank-size benchmarks.
"""

import json
import math
import os
import re
import unicodedata

import numpy as np
from PIL import Image

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
NIC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "NICETHI")
SHARED_DIR = os.path.join(NIC_DIR, "_shared")
POP_DIR = os.path.join(SHARED_DIR, "sites_nicethi_africa", "2.population_rasters")
OUT_CACHE = os.path.join(SHARED_DIR, "nicethi_figure_cache.json")

GRID_W, GRID_H = 4320, 2160

CANONICAL_TITLES = {
  "prehistoric_ssa": "Prehistoric Sub-Saharan Africa",
  "ancient_mediaeval_nubia": "Ancient and Mediaeval Sudan and Nubia",
  "ancient_horn_africa": "Ancient and Mediaeval Ethiopia and the Horn",
  "early_west_africa_sahel": "Early West Africa and the Sahel States",
  "bantu_expansion_africa": "The Bantu Expansion Across Sub-Saharan Africa",
  "atlantic_west_equatoria": "Early Modern West Africa, Equatoria and Angola",
  "early_modern_sahel_sudan": "Early Modern Sahel and Sudan",
  "early_modern_east_africa": "Early Modern East Africa and Mozambique",
  "precolonial_south_africa": "Pre-Colonial Southern Africa and the Cape Frontier",
  "early_african_islands": "Western Indian Ocean and Atlantic Islands",
  "colonial_west_sahel": "Colonial West Africa and the Sahel",
  "colonial_equatoria_congo": "Colonial Equatoria, Belgian Congo and Angola",
  "colonial_horn_sudan": "Colonial Horn of Africa and Anglo-Egyptian Sudan",
  "colonial_east_africa": "Colonial East Africa",
  "colonial_south_central": "Colonial South-Central Africa and Mozambique",
  "modern_southern_africa": "Modern Southern Africa",
  "modern_african_islands": "Modern African Ocean Islands",
  "postcolonial_sahel": "Post-Colonial Sahel States",
  "postcolonial_west_africa": "Post-Colonial West Africa",
  "postcolonial_congo_angola": "Post-Colonial Equatoria, DR Congo and Angola",
  "postcolonial_horn_sudan": "Post-Colonial Sudan, Ethiopia and the Horn",
  "postcolonial_east_africa": "Post-Colonial East Africa",
  "postcolonial_south_central": "Post-Colonial South-Central Africa and Mozambique",
}

MACRO_BASIN_MAP = {
  "senegal_gambia_atlantic": "West Africa & Sahel",
  "upper_middle_niger": "West Africa & Sahel",
  "upper_guinea_forest": "West Africa & Sahel",
  "lower_niger_benue_volta": "West Africa & Sahel",
  "chad_mega_basin": "West Africa & Sahel",
  "nile_nubia_sudd": "Horn of Africa & Sudan",
  "ethiopian_highlands_horn": "Horn of Africa & Sudan",
  "somali_arid_horn": "Horn of Africa & Sudan",
  "congo_ubangi_basin": "Central Africa & Angola",
  "lower_guinea_ogowe_cuanza": "Central Africa & Angola",
  "east_african_great_lakes": "East Africa & Great Lakes",
  "swahili_rufiji_coast": "East Africa & Great Lakes",
  "zambezi_okavango_limpopo": "Southern Africa",
  "kalahari_namib_arid": "Southern Africa",
  "orange_cape_drakensberg": "Southern Africa",
  "madagascar_wio_atlantic_isl": "African Ocean Islands",
}

PRIMATE_CITIES = [
  ("Lagos", (6.45, 3.39), ["lagos"]),
  ("Kinshasa", (-4.32, 15.31), ["kinshasa", "leopoldville"]),
  ("Johannesburg", (-26.20, 28.04), ["johannesburg"]),
  ("Nairobi", (-1.29, 36.82), ["nairobi"]),
  ("Khartoum", (15.50, 32.56), ["khartoum", "al-khartum", "alkhartum", "umm durman", "omdurman"]),
  ("Addis Ababa", (9.03, 38.74), ["addis ababa", "adis abeba"]),
  ("Cape Town", (-33.92, 18.42), ["cape town"]),
  ("Antananarivo", (-18.91, 47.52), ["antananarivo", "tananarive"]),
]


def compute_row_cell_areas_km2 ():
  """Computes exact spherical surface area (km²) of one 5-arcminute cell per latitude row."""
  r_km = 6371.0088
  dlon = math.radians(360.0 / GRID_W)
  rows = np.arange(GRID_H, dtype=np.float64)
  lat_hi = np.radians(90.0 - rows * (180.0 / GRID_H))
  lat_lo = np.radians(90.0 - (rows + 1.0) * (180.0 / GRID_H))
  areas = (r_km ** 2) * dlon * np.abs(np.sin(lat_hi) - np.sin(lat_lo))
  return areas.astype(np.float64)


def decode_velk_pop_png (arg0_path):
  """Decodes a 4320x2160 big-endian float32 RGBA population raster into inhabitants per cell."""
  arr = np.ascontiguousarray(Image.open(arg0_path).convert("RGBA"), dtype=np.uint8)
  vals = arr.view(">f4").reshape(arr.shape[:2])
  return np.where(np.isfinite(vals) & (vals > 0.0) & (vals < 1e8), vals, 0.0).astype(np.float32)


def normalise_name (arg0_name):
  """Strips diacritics, agglomeration tags and punctuation to canonicalise duplicate city names."""
  s = str(arg0_name or "").strip()
  s = re.sub(r"\s*\(Agglomeration\)\s*", "", s, flags=re.I)
  s = re.sub(r"\s*\(Metro[^)]*\)\s*", "", s, flags=re.I)
  s = unicodedata.normalize("NFKD", s)
  s = "".join(ch for ch in s if not unicodedata.combining(ch))
  s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
  return s


def clean_display_name (arg0_name):
  """Produces a concise human-readable settlement display name without Agglomeration clutter."""
  s = str(arg0_name or "").strip()
  s = re.sub(r"\s*\(Agglomeration\)\s*", "", s, flags=re.I).strip()
  # Normalise common orthographic variants for clean cartographic readability
  aliases = {
    "Adis Abeba": "Addis Ababa",
    "Al-Kharṭūm": "Khartoum",
    "Al-Khartum": "Khartoum",
    "Umm Durmān": "Omdurman",
    "Sannār": "Sennar",
    "Port Louis": "Port-Louis",
    "Nothern Cape": "Northern Cape",
  }
  return aliases.get(s, s)


def is_valid_city_name (arg0_name):
  """Filters out placeholder or unnamed records from display callouts and top-city rankings."""
  s = str(arg0_name or "").strip().lower()
  if not s or len(s) < 2:
    return False
  for bad in ("(n.d.)", "unnamed", "unknown", "site ", "n/a"):
    if bad in s:
      return False
  return True


def deduplicate_settlements (arg0_setts_dict, arg1_domain):
  """Merges co-located city-proper / agglomeration duplicates inside a chapter domain."""
  d0, d1 = int(arg1_domain[0]), int(arg1_domain[1])
  raw_list = []
  for k, s in arg0_setts_dict.items():
    nm = str(s.get("name") or "").strip()
    coords = s.get("coords")
    if not coords or len(coords) < 2:
      continue
    lat, lon = float(coords[0]), float(coords[1])
    pdict = {}
    for yk, v in (s.get("population") or {}).items():
      try:
        yi = int(yk)
        vf = float(v)
      except Exception:
        continue
      if vf > 0.0 and d0 <= yi <= d1:
        pdict[yi] = vf
    if not pdict:
      continue
    pk_val = max(pdict.values())
    pk_yr = max(pdict.keys(), key=lambda y: pdict[y])
    raw_list.append({
      "key": k,
      "raw_name": nm,
      "display_name": clean_display_name(nm),
      "norm_name": normalise_name(nm),
      "valid_name": is_valid_city_name(nm),
      "lat": lat,
      "lon": lon,
      "country": str(s.get("country") or ""),
      "pop": pdict,
      "peak_pop": pk_val,
      "peak_year": pk_yr,
    })

  # Sort largest peak first so canonical larger agglomerations anchor merges
  raw_list.sort(key=lambda r: (-r["peak_pop"], 0 if r["valid_name"] else 1))
  merged = []
  for item in raw_list:
    matched = None
    for m in merged:
      dlat = abs(item["lat"] - m["lat"])
      dlon = abs(item["lon"] - m["lon"])
      if dlat <= 0.30 and dlon <= 0.30:
        same_nm = (
          item["norm_name"] == m["norm_name"]
          or (len(item["norm_name"]) >= 4 and (item["norm_name"] in m["norm_name"] or m["norm_name"] in item["norm_name"]))
          or (dlat <= 0.12 and dlon <= 0.12 and (
            item["display_name"] == m["display_name"]
            or item["raw_name"].endswith("(Agglomeration)")
            or m["raw_name"].endswith("(Agglomeration)")
          ))
        )
        if same_nm:
          matched = m
          break
    if matched is not None:
      for yi, vf in item["pop"].items():
        if vf > matched["pop"].get(yi, 0.0):
          matched["pop"][yi] = vf
      if item["peak_pop"] > matched["peak_pop"]:
        matched["peak_pop"] = item["peak_pop"]
        matched["peak_year"] = item["peak_year"]
      if (not matched["valid_name"]) and item["valid_name"]:
        matched["display_name"] = item["display_name"]
        matched["valid_name"] = True
    else:
      merged.append(item)

  return merged


def select_benchmark_years (arg0_hyde_years, arg1_domain):
  """Selects 6 to 14 well-spaced raster years spanning a chapter's temporal domain."""
  d0, d1 = int(arg1_domain[0]), int(arg1_domain[1])
  in_dom = sorted(y for y in arg0_hyde_years if d0 <= y <= d1)
  if not in_dom:
    nearest = min(arg0_hyde_years, key=lambda y: abs(y - d1))
    return [nearest]
  if len(in_dom) <= 14:
    return in_dom
  idxs = np.linspace(0, len(in_dom) - 1, 14).round().astype(int)
  chosen = sorted(set(in_dom[i] for i in idxs))
  return chosen


def build_urban_trajectory (arg0_merged_setts, arg1_domain, arg2_bench_years):
  """Computes attested urban population & active settlement count across benchmark bins inside domain."""
  d0, d1 = int(arg1_domain[0]), int(arg1_domain[1])
  span = max(1, d1 - d0)
  # Use either benchmark years or dense urban sample years
  sample_yrs = sorted(set(arg2_bench_years))
  if len(sample_yrs) < 5:
    sample_yrs = sorted(set(int(round(v)) for v in np.linspace(d0, d1, 8)))

  # Half-window tolerance for assigning settlement records to nearest benchmark bin
  tol = max(5, min(250, int(round(span / (len(sample_yrs) * 1.4)))))
  series = []
  for ty in sample_yrs:
    tot_u = 0.0
    cnt_u = 0
    for s in arg0_merged_setts:
      pd = s["pop"]
      if not pd:
        continue
      # Interpolate if bracketed within domain, else nearest within tolerance
      ys = sorted(pd.keys())
      if ys[0] <= ty <= ys[-1]:
        # linear interpolation in log space for smooth city growth
        val = None
        for i in range(len(ys) - 1):
          if ys[i] <= ty <= ys[i + 1]:
            if ys[i] == ty:
              val = pd[ys[i]]
            elif ys[i + 1] == ty:
              val = pd[ys[i + 1]]
            else:
              frac = (ty - ys[i]) / float(ys[i + 1] - ys[i])
              val = math.exp(math.log(max(1.0, pd[ys[i]])) * (1.0 - frac) + math.log(max(1.0, pd[ys[i + 1]])) * frac)
            break
        if val is not None and val > 0.0:
          tot_u += val
          cnt_u += 1
      else:
        best_y = min(ys, key=lambda y: abs(y - ty))
        if abs(best_y - ty) <= tol:
          tot_u += pd[best_y]
          cnt_u += 1
    series.append({"year": int(ty), "urban_pop": round(tot_u, 1), "settlement_count": int(cnt_u)})

  return series


def main ():
  masks_cfg = json.load(open(os.path.join(NIC_DIR, "nicethi_areal_masks.json5"), encoding="utf-8"))
  gaz_cfg = json.load(open(os.path.join(NIC_DIR, "nicethi_gazetteers.json5"), encoding="utf-8"))
  hyde_years = sorted(int(y) for y in masks_cfg["hyde_years"])
  row_areas = compute_row_cell_areas_km2()

  # Map chapter id -> mask info
  mask_by_id = {}
  for m in masks_cfg["specialist_masks"] + masks_cfg["national_epoch_masks"]:
    mask_by_id[m["id"]] = m

  print("[1] Loading prehistoric_ssa basin mask for 6-macro-region decomposition...", flush=True)
  p_pre = os.path.join(SVEA_ROOT, mask_by_id["prehistoric_ssa"]["mask_path"])
  j_pre = json.load(open(os.path.join(SVEA_ROOT, mask_by_id["prehistoric_ssa"]["json5_path"]), encoding="utf-8"))
  pre_rgba = np.asarray(Image.open(p_pre).convert("RGBA"), dtype=np.uint8)
  pre_rgb = (pre_rgba[:, :, 0].astype(np.int32) << 16) | (pre_rgba[:, :, 1].astype(np.int32) << 8) | pre_rgba[:, :, 2].astype(np.int32)
  pre_valid = pre_rgba[:, :, 3] > 0

  macro_names = [
    "West Africa & Sahel",
    "Horn of Africa & Sudan",
    "Central Africa & Angola",
    "East Africa & Great Lakes",
    "Southern Africa",
    "African Ocean Islands",
  ]
  macro_masks = {mn: np.zeros((GRID_H, GRID_W), dtype=bool) for mn in macro_names}
  for sr in j_pre["subregions"]:
    code = (int(sr["rgb"][0]) << 16) | (int(sr["rgb"][1]) << 8) | int(sr["rgb"][2])
    mn = MACRO_BASIN_MAP.get(sr["id"], "West Africa & Sahel")
    macro_masks[mn] |= (pre_valid & (pre_rgb == code))

  # Compute exact pixel row/col indices per macro region for ultra-fast summation
  macro_idx = {mn: np.where(m) for mn, m in macro_masks.items()}

  # Pre-load chapter masks (bounding box + RGB codes per subregion)
  print("[2] Indexing all 23 chapter areal masks & spherical areas...", flush=True)
  ch_meta = []
  needed_years = set(hyde_years)
  for idx, g in enumerate(gaz_cfg["gazetteers"], 1):
    key = g["key"]
    m_info = mask_by_id[key]
    j_path = os.path.join(SVEA_ROOT, m_info["json5_path"])
    m_path = os.path.join(SVEA_ROOT, m_info["mask_path"])
    ch_dir = os.path.dirname(j_path)
    j_obj = json.load(open(j_path, encoding="utf-8"))

    rgba = np.asarray(Image.open(m_path).convert("RGBA"), dtype=np.uint8)
    valid = rgba[:, :, 3] > 0
    ys_v, xs_v = np.where(valid)
    r0, r1 = int(ys_v.min()), int(ys_v.max()) + 1
    c0, c1 = int(xs_v.min()), int(xs_v.max()) + 1
    sub_rgba = rgba[r0:r1, c0:c1]
    sub_valid = sub_rgba[:, :, 3] > 0
    sub_rgb = (sub_rgba[:, :, 0].astype(np.int32) << 16) | (sub_rgba[:, :, 1].astype(np.int32) << 8) | sub_rgba[:, :, 2].astype(np.int32)

    # Map RGB code -> subregion index (1..n)
    code_to_idx = {}
    sr_list = []
    for s_i, sr in enumerate(j_obj["subregions"], 1):
      code = (int(sr["rgb"][0]) << 16) | (int(sr["rgb"][1]) << 8) | int(sr["rgb"][2])
      code_to_idx[code] = s_i
      sr_list.append({
        "id": sr["id"],
        "name": sr["name"],
        "rgb": sr["rgb"],
        "iso3": sr["id"].split("_")[0].upper() if j_obj.get("is_admin1") else "",
        "area_km2": 0.0,
        "pop_by_year": {},
      })

    id_crop = np.zeros(sub_rgb.shape, dtype=np.int32)
    for code, s_i in code_to_idx.items():
      m_sr = sub_valid & (sub_rgb == code)
      id_crop[m_sr] = s_i
      rr, _ = np.where(m_sr)
      if rr.size > 0:
        sr_list[s_i - 1]["area_km2"] = round(float(row_areas[r0 + rr].sum()), 1)

    bench_yrs = select_benchmark_years(hyde_years, g["domain"])
    ch_meta.append({
      "index": idx,
      "key": key,
      "folder": os.path.relpath(ch_dir, NIC_DIR).replace("\\", "/"),
      "title": CANONICAL_TITLES.get(key, g["itinerary_title"]),
      "domain": g["domain"],
      "is_admin1": bool(j_obj.get("is_admin1", False)),
      "bbox_px": (r0, r1, c0, c1),
      "id_crop": id_crop,
      "subregions": sr_list,
      "benchmark_years": bench_yrs,
      "total_pop_by_year": {},
      "sett_path": os.path.join(SVEA_ROOT, g["path"]),
    })

  # Single pass over all 128 population rasters!
  print(f"[3] Streaming {len(hyde_years)} population rasters across 6 macro-regions & 23 chapters...", flush=True)
  macro_series = {"years": [], "total": [], "regions": {mn: [] for mn in macro_names}}
  for yr in hyde_years:
    rp = os.path.join(POP_DIR, f"popc_{yr}.png")
    if not os.path.isfile(rp):
      continue
    grid = decode_velk_pop_png(rp)
    macro_series["years"].append(int(yr))
    macro_series["total"].append(round(float(grid.sum()), 1))
    for mn in macro_names:
      rr, cc = macro_idx[mn]
      macro_series["regions"][mn].append(round(float(grid[rr, cc].sum()), 1))

    # Accumulate chapter subregional & total pops for benchmark years
    for cm in ch_meta:
      if yr in cm["benchmark_years"]:
        r0, r1, c0, c1 = cm["bbox_px"]
        crop_pop = grid[r0:r1, c0:c1]
        id_crop = cm["id_crop"]
        n_sr = len(cm["subregions"])
        sums = np.bincount(id_crop.ravel(), weights=crop_pop.ravel(), minlength=n_sr + 1)
        cm["total_pop_by_year"][str(yr)] = round(float(sums[1:].sum()), 1)
        for s_i in range(1, n_sr + 1):
          cm["subregions"][s_i - 1]["pop_by_year"][str(yr)] = round(float(sums[s_i]), 1)

  # Process settlements per chapter + Pan-NICETHI unified settlement pool
  print("[4] Processing & deduplicating settlements for all 23 chapters and Pan-NICETHI benchmarks...", flush=True)
  pan_pool = {}
  chapters_out = []
  for cm in ch_meta:
    raw_setts = json.load(open(cm["sett_path"], encoding="utf-8"))
    merged = deduplicate_settlements(raw_setts, cm["domain"])

    # Feed into Pan-NICETHI pool
    for k, s in raw_setts.items():
      if k not in pan_pool:
        pan_pool[k] = {
          "name": s.get("name", ""),
          "coords": s.get("coords"),
          "country": s.get("country", ""),
          "population": {},
        }
      for yk, v in (s.get("population") or {}).items():
        try:
          yi = int(yk)
          vf = float(v)
          if vf > 0:
            pan_pool[k]["population"][str(yi)] = max(pan_pool[k]["population"].get(str(yi), 0.0), vf)
        except Exception:
          pass

    urban_series = build_urban_trajectory(merged, cm["domain"], cm["benchmark_years"])
    named_sorted = [s for s in merged if s["valid_name"]]
    named_sorted.sort(key=lambda s: -s["peak_pop"])
    top_cities = []
    for s in named_sorted[:24]:
      pts = sorted((int(y), round(float(v), 1)) for y, v in s["pop"].items())
      top_cities.append({
        "name": s["display_name"],
        "lon": round(s["lon"], 4),
        "lat": round(s["lat"], 4),
        "country": s["country"],
        "peak_pop": round(s["peak_pop"], 1),
        "peak_year": int(s["peak_year"]),
        "series": pts,
      })

    zipf_peaks = sorted([round(s["peak_pop"], 1) for s in merged if s["peak_pop"] > 0], reverse=True)

    # Compute end-epoch density for every subregion
    end_yr = str(cm["benchmark_years"][-1])
    for sr in cm["subregions"]:
      p_end = sr["pop_by_year"].get(end_yr, 0.0)
      sr["end_density"] = round(p_end / max(1.0, sr["area_km2"]), 3)

    chapters_out.append({
      "index": cm["index"],
      "key": cm["key"],
      "folder": cm["folder"],
      "title": cm["title"],
      "domain": cm["domain"],
      "is_admin1": cm["is_admin1"],
      "benchmark_years": cm["benchmark_years"],
      "total_pop_by_year": cm["total_pop_by_year"],
      "urban_series": urban_series,
      "n_settlements_raw": len(raw_setts),
      "n_settlements_dedup": len(merged),
      "top_cities": top_cities,
      "zipf_peaks": zipf_peaks,
      "subregions": cm["subregions"],
    })

  # Pan-NICETHI deduplicated settlements across all time
  print("[5] Computing Pan-NICETHI 5-epoch Zipf evolution & primate city growth curves...", flush=True)
  pan_merged = deduplicate_settlements(pan_pool, [-10000, 2026])
  pan_zipf_epochs = {}
  for ty, tol in [(1000, 100), (1500, 50), (1850, 25), (1950, 10), (2020, 5)]:
    vals = []
    for s in pan_merged:
      pd = s["pop"]
      if not pd:
        continue
      ys = sorted(pd.keys())
      val = None
      if ys[0] <= ty <= ys[-1]:
        for i in range(len(ys) - 1):
          if ys[i] <= ty <= ys[i + 1]:
            if ys[i] == ty:
              val = pd[ys[i]]
            elif ys[i + 1] == ty:
              val = pd[ys[i + 1]]
            else:
              frac = (ty - ys[i]) / float(ys[i + 1] - ys[i])
              val = math.exp(math.log(max(1.0, pd[ys[i]])) * (1.0 - frac) + math.log(max(1.0, pd[ys[i + 1]])) * frac)
            break
      else:
        best_y = min(ys, key=lambda y: abs(y - ty))
        if abs(best_y - ty) <= tol:
          val = pd[best_y]
      if val is not None and val >= 500.0:
        vals.append((round(val, 1), s["display_name"], round(s["lon"], 3), round(s["lat"], 3)))
    vals.sort(reverse=True)
    pan_zipf_epochs[str(ty)] = {
      "n": len(vals),
      "sum_pop": round(sum(v[0] for v in vals), 1),
      "pops": [v[0] for v in vals],
      "top10": [{"name": v[1], "pop": v[0], "lon": v[2], "lat": v[3]} for v in vals[:10]],
    }

  # Primate city trajectories (1800-2025)
  primate_out = []
  for cname, (clat, clon), kw_list in PRIMATE_CITIES:
    combined_pts = {}
    for s in pan_merged:
      if abs(s["lat"] - clat) <= 0.65 and abs(s["lon"] - clon) <= 0.65:
        if any(kw in s["norm_name"] for kw in kw_list):
          for yi, vf in s["pop"].items():
            if 1800 <= yi <= 2025:
              combined_pts[yi] = max(combined_pts.get(yi, 0.0), vf)
    pts_sorted = sorted((int(y), round(float(v), 1)) for y, v in combined_pts.items())
    primate_out.append({"name": cname, "lat": clat, "lon": clon, "series": pts_sorted})

  # Pan-NICETHI secular urban total at key years for Fig 3 overlay
  pan_urban_secular = []
  for ty, tol in [(-1000, 250), (0, 150), (500, 150), (1000, 100), (1500, 60), (1700, 40), (1800, 30), (1850, 25), (1900, 15), (1950, 10), (1975, 6), (2000, 5), (2020, 5)]:
    tot_u = 0.0
    for s in pan_merged:
      pd = s["pop"]
      if not pd:
        continue
      ys = sorted(pd.keys())
      if ys[0] <= ty <= ys[-1]:
        for i in range(len(ys) - 1):
          if ys[i] <= ty <= ys[i + 1]:
            frac = (ty - ys[i]) / float(max(1, ys[i + 1] - ys[i]))
            tot_u += math.exp(math.log(max(1.0, pd[ys[i]])) * (1.0 - frac) + math.log(max(1.0, pd[ys[i + 1]])) * frac)
            break
      else:
        best_y = min(ys, key=lambda y: abs(y - ty))
        if abs(best_y - ty) <= tol:
          tot_u += pd[best_y]
    pan_urban_secular.append({"year": ty, "urban_pop": round(tot_u, 1)})

  # Top 30 historical + modern corridor cities for Fig 1 overview map
  pan_top_cities = []
  seen_c = set()
  for s in sorted(pan_merged, key=lambda r: -r["peak_pop"]):
    if not s["valid_name"]:
      continue
    if s["display_name"] in seen_c:
      continue
    seen_c.add(s["display_name"])
    pan_top_cities.append({
      "name": s["display_name"],
      "lon": round(s["lon"], 3),
      "lat": round(s["lat"], 3),
      "peak_pop": round(s["peak_pop"], 1),
      "peak_year": int(s["peak_year"]),
    })
    if len(pan_top_cities) >= 45:
      break

  cache = {
    "chapters": chapters_out,
    "macro_series": macro_series,
    "pan_urban_secular": pan_urban_secular,
    "pan_zipf_epochs": pan_zipf_epochs,
    "primate_cities": primate_out,
    "pan_top_cities": pan_top_cities,
  }
  with open(OUT_CACHE, "w", encoding="utf-8") as fh:
    json.dump(cache, fh, indent=2, ensure_ascii=False)
  print(f"[DONE] Wrote {OUT_CACHE} ({len(chapters_out)} chapters, {len(macro_series['years'])} years).", flush=True)


if __name__ == "__main__":
  main()
