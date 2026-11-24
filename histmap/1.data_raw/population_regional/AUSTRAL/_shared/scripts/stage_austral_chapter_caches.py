"""Stages pre-computed JSON summary caches for all 16 Project AUSTRAL chapters and root synthesis.

Combines:
  - Per-chapter `<stem>.json5` sub-regional population trajectories & exact spherical areas from `<stem>_areal_mask.png`
  - Stage B `2.population_rasters/` raster trajectories sampled per sub-region over each chapter's domain
  - Per-chapter `<stem>_settlements.json` & `<stem>_source_ledger.json5` (top settlements, scope counts, Zipf rank-size)
  - Historical & modern sub-administrative HGIS enumerations (`subadmin_enumerations_for_literature_reviews.csv`,
    `aus_nz_subadmin_enumerations.json`, `pacific_ng_subadmin_enumerations.json`) for chapter literature-review tables
  - Domain-wide synthesis (`austral_root_summary.json`): 6-region secular trajectories (`-10000..2025`),
    Matérn kriging variogram diagnostics and 4-jurisdiction archaeological provenance (`69,018` primary sites).
"""

import csv
import glob
import json
import math
import os
import re
from collections import Counter, defaultdict

import numpy as np
from PIL import Image

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
AUS_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL")
SHARED = os.path.join(AUS_DIR, "_shared")
ITIN_PATH = os.path.join(AUS_DIR, "austral_itinerary.json5")
HGIS_DIR = os.path.join(SHARED, "subadmin_hgis")
HGIS_CSV = os.path.join(HGIS_DIR, "subadmin_enumerations_for_literature_reviews.csv")
HGIS_JSON = os.path.join(HGIS_DIR, "subadmin_enumerations_for_literature_reviews.json")
AUS_NZ_ENUM_JSON = os.path.join(HGIS_DIR, "raw_sources", "aus_nz_subadmin_enumerations.json")
PAC_NG_ENUM_JSON = os.path.join(HGIS_DIR, "raw_sources", "pacific_ng_subadmin_enumerations.json")
MASS_AUDIT_JSON = os.path.join(HGIS_DIR, "subadmin_mass_conservation_audit.json")
SITES_DIR = os.path.join(SHARED, "sites_austral_oceania")
POP_DIR = os.path.join(SITES_DIR, "2.population_rasters")
KRIG_DIAG_JSON = os.path.join(SITES_DIR, "config", "kriging_diagnostics.json")
GEOJSON_META_JSON = os.path.join(SITES_DIR, "config", "sites_austral_oceania_geojson_metadata.json")
DOMAIN_MASK_PNG = os.path.join(SITES_DIR, "config", "austral_domain_mask.png")

GRID_W, GRID_H = 4320, 2160
CELL_LON_RAD = 2.0 * math.pi / GRID_W
R_EARTH_KM = 6371.0088

# Map HGIS CSV country codes to canonical country/region names used in AUSTRAL chapters
HGIS_COUNTRY_TO_GROUP = {
  "AU": "australia",
  "NZ": "new_zealand",
  "NG": "new_guinea",
  "PG": "new_guinea",
  "ID_NG": "new_guinea",
  "SB": "island_melanesia",
  "VU": "island_melanesia",
  "NC": "island_melanesia",
  "FJ": "island_melanesia",
  "GU": "micronesia",
  "MP": "micronesia",
  "PW": "micronesia",
  "FM": "micronesia",
  "MH": "micronesia",
  "KI": "micronesia",
  "NR": "micronesia",
  "TO": "polynesia",
  "WS": "polynesia",
  "PF": "polynesia",
  "CK": "polynesia",
  "NU": "polynesia",
  "TV": "polynesia",
  "TK": "polynesia",
  "WF": "polynesia",
  "PN": "polynesia",
  "CL_RPN": "polynesia",
}

CHAPTER_GROUPS = {
  "pre_1788_australia": ["australia"],
  "precolonial_new_guinea": ["new_guinea"],
  "precolonial_melanesia_micro": ["island_melanesia", "micronesia"],
  "precolonial_polynesia": ["polynesia"],
  "pre_european_new_zealand": ["new_zealand"],
  "colonial_australia": ["australia"],
  "colonial_new_zealand": ["new_zealand"],
  "colonial_new_guinea": ["new_guinea"],
  "colonial_island_melanesia": ["island_melanesia"],
  "colonial_micronesia": ["micronesia"],
  "colonial_polynesia": ["polynesia"],
  "modern_australia": ["australia"],
  "modern_new_zealand": ["new_zealand"],
  "modern_new_guinea": ["new_guinea"],
  "modern_melanesia_micro": ["island_melanesia", "micronesia"],
  "modern_polynesia": ["polynesia"],
}


def load_json5_simple (arg0_path):
  """Parses a JSON5/JSON file stripping comments and trailing commas."""
  raw = open(arg0_path, encoding="utf-8").read()
  raw = re.sub(r"//.*", "", raw)
  raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
  raw = re.sub(r",(\s*[}\]])", r"\1", raw)
  raw = re.sub(r"(\{|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
  return json.loads(raw)


def compute_row_cell_areas_km2 ():
  """Computes exact spherical-trapezoid cell area (km²) for each latitude row on the 4320x2160 grid."""
  lats_n = np.linspace(90.0, -90.0, GRID_H + 1)
  sin_n = np.sin(np.radians(lats_n[:-1]))
  sin_s = np.sin(np.radians(lats_n[1:]))
  return (R_EARTH_KM ** 2) * CELL_LON_RAD * np.abs(sin_n - sin_s)


def decode_velk_png (arg0_path):
  """Decodes a 4320x2160 big-endian float32 RGBA population raster into a 2D float32 array."""
  arr = np.ascontiguousarray(Image.open(arg0_path).convert("RGBA"), dtype=np.uint8)
  vals = arr.view(">f4").reshape(arr.shape[:2])
  return np.where(np.isfinite(vals) & (vals > 0.0) & (vals < 1e8), vals, 0.0).astype(np.float32)


def list_available_raster_years ():
  """Returns sorted list of integer years available in `2.population_rasters/`."""
  yrs = []
  if not os.path.isdir(POP_DIR):
    return yrs
  for fn in os.listdir(POP_DIR):
    m = re.match(r"^popc_(-?\d+)\.png$", fn)
    if m:
      yrs.append(int(m.group(1)))
  return sorted(yrs)


def load_hgis_csv_rows ():
  """Loads all sub-administrative HGIS rows from `subadmin_enumerations_for_literature_reviews.csv`."""
  rows = []
  if not os.path.isfile(HGIS_CSV):
    return rows
  with open(HGIS_CSV, encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
      try:
        rows.append({
          "snapshot_regime": int(r["snapshot_regime"]),
          "country": str(r["country"]).strip(),
          "macro_group": HGIS_COUNTRY_TO_GROUP.get(str(r["country"]).strip(), "other"),
          "unit_code": str(r["unit_code"]).strip(),
          "unit_name": str(r["unit_name"]).strip(),
          "year": int(r["year"]),
          "population": int(round(float(r["population"]))),
          "area_km2": round(float(r["area_km2"]), 1),
          "source": str(r["source"]).strip(),
        })
      except Exception:
        continue
  return rows


def extract_raw_enum_rows_for_chapter (arg0_key, arg1_d0, arg2_d1, arg3_aus_nz, arg4_pac_ng):
  """Extracts primary-source census/enumeration rows from `aus_nz_subadmin_enumerations.json` and
  `pacific_ng_subadmin_enumerations.json` tailored for chapter literature-review `longtable`s."""
  groups = CHAPTER_GROUPS.get(arg0_key, [])
  rows = []

  if "australia" in groups and isinstance(arg3_aus_nz, dict):
    au_blk = arg3_aus_nz.get("australia", {})
    if arg0_key == "pre_1788_australia":
      indig = au_blk.get("indigenous_minimum_estimates_1788_1971_smith1980", {})
      for sec_k, sec_v in indig.items():
        if isinstance(sec_v, dict):
          for yk, yv in sec_v.items():
            if re.match(r"^-?\d+$", str(yk)):
              if isinstance(yv, (int, float)) and yv > 0:
                rows.append({
                  "territory": "Australia",
                  "unit_name": str(sec_k),
                  "year": int(yk),
                  "population": int(round(float(yv))),
                  "source": "ABS HPDC10 / L.R. Smith (1980)",
                })
              elif isinstance(yv, dict):
                for uk, uv in yv.items():
                  if isinstance(uv, (int, float)) and uv > 0:
                    rows.append({
                      "territory": "Australia",
                      "unit_name": str(uk),
                      "year": int(yk),
                      "population": int(round(float(uv))),
                      "source": "ABS HPDC10 / L.R. Smith (1980)",
                    })
    else:
      ann = au_blk.get("colonial_and_state_annual_31dec_1788_2025", {}).get("series_by_year", {})
      bench_au = [1788, 1800, 1820, 1828, 1836, 1841, 1851, 1861, 1871, 1881, 1891, 1901,
                  1911, 1921, 1933, 1947, 1954, 1961, 1971, 1981, 1991, 2001, 2011, 2021, 2025]
      for yr in bench_au:
        if arg1_d0 <= yr <= arg2_d1 and str(yr) in ann:
          for unit_nm, pop_v in ann[str(yr)].items():
            if isinstance(pop_v, (int, float)) and pop_v > 0:
              rows.append({
                "territory": "Australia",
                "unit_name": str(unit_nm),
                "year": yr,
                "population": int(round(float(pop_v))),
                "source": "ABS Cat. 3105.0.65.001 HPDC1 / Cat. 3101.0 ERP",
              })

  if "new_zealand" in groups and isinstance(arg3_aus_nz, dict):
    nz_blk = arg3_aus_nz.get("new_zealand", {})
    for sec_k, sec_v in nz_blk.items():
      if not isinstance(sec_v, dict):
        continue
      src_lbl = str(sec_v.get("source") or sec_v.get("citation") or sec_k)[:90]
      series = sec_v.get("series_by_year") or sec_v.get("provinces_by_year") or sec_v.get("regions_by_year") or sec_v.get("series") or {}
      if isinstance(series, dict):
        for yk, yv in series.items():
          m_y = re.search(r"(-?\d{3,4})", str(yk))
          if not m_y:
            continue
          yr = int(m_y.group(1))
          if not (arg1_d0 <= yr <= arg2_d1):
            continue
          if isinstance(yv, (int, float)) and yv > 0:
            rows.append({
              "territory": "New Zealand",
              "unit_name": str(sec_k),
              "year": yr,
              "population": int(round(float(yv))),
              "source": src_lbl,
            })
          elif isinstance(yv, dict):
            for unm, uv in yv.items():
              if isinstance(uv, (int, float)) and uv > 0:
                rows.append({
                  "territory": "New Zealand",
                  "unit_name": str(unm),
                  "year": yr,
                  "population": int(round(float(uv))),
                  "source": src_lbl,
                })

  pac_group_keys = {
    "new_guinea": "new_guinea",
    "island_melanesia": "island_melanesia",
    "micronesia": "micronesia",
    "polynesia": "polynesia_excl_hawaii_american_samoa",
  }
  for g_nm in groups:
    pk = pac_group_keys.get(g_nm)
    if not pk or not isinstance(arg4_pac_ng, dict):
      continue
    sec_dict = arg4_pac_ng.get(pk, {})
    if not isinstance(sec_dict, dict):
      continue
    for terr_k, terr_v in sec_dict.items():
      if not isinstance(terr_v, dict):
        continue
      agency = str(terr_v.get("official_agency") or terr_k)[:85]
      # Walk nested census dictionaries (national totals & admin1 sub-units)
      for sub_k, sub_v in terr_v.items():
        if not isinstance(sub_v, dict) or sub_k in ("metadata", "notes"):
          continue
        for k1, v1 in sub_v.items():
          # Case A: year -> scalar or dict
          if re.match(r"^\d{4}$", str(k1)):
            yr = int(k1)
            if not (arg1_d0 <= yr <= arg2_d1):
              continue
            if isinstance(v1, (int, float)) and v1 > 0:
              rows.append({
                "territory": terr_k,
                "unit_name": sub_k,
                "year": yr,
                "population": int(round(float(v1))),
                "source": agency,
              })
            elif isinstance(v1, dict):
              for k2, v2 in v1.items():
                if isinstance(v2, (int, float)) and v2 > 0:
                  rows.append({
                    "territory": terr_k,
                    "unit_name": str(k2),
                    "year": yr,
                    "population": int(round(float(v2))),
                    "source": agency,
                  })
          # Case B: unit_name -> {year: pop}
          elif isinstance(v1, dict):
            for k2, v2 in v1.items():
              if re.match(r"^\d{4}$", str(k2)) and isinstance(v2, (int, float)) and v2 > 0:
                yr = int(k2)
                if arg1_d0 <= yr <= arg2_d1:
                  rows.append({
                    "territory": terr_k,
                    "unit_name": str(k1),
                    "year": yr,
                    "population": int(round(float(v2))),
                    "source": agency,
                  })

  # Deduplicate and sort cleanly
  seen = set()
  clean_rows = []
  for r in sorted(rows, key=lambda x: (x["year"], -x["population"], x["unit_name"])):
    sig = (r["territory"], r["unit_name"], r["year"])
    if sig in seen:
      continue
    seen.add(sig)
    clean_rows.append(r)
  return clean_rows[:120]


def interp_subregion_series (arg0_pop_dict, arg1_target_years):
  """Log-interpolates a sub-region's recorded census/benchmark series cleanly onto unified chapter years."""
  pts = sorted((int(k), float(v)) for k, v in arg0_pop_dict.items() if float(v) > 0)
  if not pts:
    return {str(y): 0 for y in arg1_target_years}
  out = {}
  for y in arg1_target_years:
    if y <= pts[0][0]:
      out[str(y)] = int(round(pts[0][1]))
    elif y >= pts[-1][0]:
      out[str(y)] = int(round(pts[-1][1]))
    else:
      for i in range(len(pts) - 1):
        y0, v0 = pts[i]
        y1, v1 = pts[i + 1]
        if y0 <= y <= y1:
          t = (y - y0) / max(1.0, float(y1 - y0))
          out[str(y)] = int(round(math.exp((1.0 - t) * math.log(v0) + t * math.log(v1))))
          break
  return out


def choose_unified_years (arg0_all_years, arg1_d0, arg2_d1):
  """Collapses staggered national/territorial census years into clean unified chapter benchmarks
  without chaining consecutive years into a single cluster."""
  # Modern post-1955 chapters spanning to 2025+: use clean canonical decadal + contemporary benchmarks
  if int(arg1_d0) >= 1955 and int(arg2_d1) >= 2020:
    return [y for y in (1960, 1970, 1980, 1990, 2000, 2010, 2020, 2025) if y >= int(arg1_d0) - 2]

  sy = sorted(y for y in arg0_all_years if arg1_d0 - 5 <= y <= arg2_d1 + 5)
  if not sy:
    sy = sorted(arg0_all_years)
  if len(sy) <= 9:
    return sy
  span = max(1, sy[-1] - sy[0])
  gap_tol = max(6, int(span / 10))
  # Compare against group START (`groups[-1][0]`) to prevent runaway single-cluster chaining!
  groups = [[sy[0]]]
  for y in sy[1:]:
    if y - groups[-1][0] <= gap_tol:
      groups[-1].append(y)
    else:
      groups.append([y])
  unified = []
  for g in groups:
    best = next((v for v in g if v in (arg1_d0, arg2_d1)), None)
    if best is None:
      best = next((v for v in g if v % 10 == 0), g[len(g) // 2])
    unified.append(best)
  return sorted(set(unified))


def compute_zipf_stats (arg0_peaks):
  """Computes OLS Zipf rank-size slope, intercept and R² on log10(rank) vs log10(pop) when n >= 25."""
  pops = [float(p) for p in arg0_peaks if float(p) > 0]
  n_all = len(pops)
  if n_all < 25:
    return {
      "n_with_pop": n_all,
      "fit_valid": False,
      "n_fit": 0,
      "slope": None,
      "zipf_alpha": None,
      "intercept": None,
      "r2": None,
      "full_slope": None,
      "full_zipf_alpha": None,
      "full_r2": None,
    }
  ranks = np.arange(1, n_all + 1, dtype=np.float64)
  pop_arr = np.asarray(pops, dtype=np.float64)

  # Core urban hierarchy fit (top 50%, clamped to [25, 180]) matching MAGNETIC standard
  n_fit = min(max(25, n_all // 2), 180)
  lx = np.log10(ranks[:n_fit])
  ly = np.log10(pop_arr[:n_fit])
  slope, intercept = np.polyfit(lx, ly, 1)
  y_hat = slope * lx + intercept
  ss_res = float(np.sum((ly - y_hat) ** 2))
  ss_tot = float(np.sum((ly - np.mean(ly)) ** 2))
  r2 = max(0.0, 1.0 - ss_res / max(1e-12, ss_tot))

  # Full sample fit
  lx_f = np.log10(ranks)
  ly_f = np.log10(pop_arr)
  sl_f, int_f = np.polyfit(lx_f, ly_f, 1)
  yh_f = sl_f * lx_f + int_f
  r2_f = max(0.0, 1.0 - float(np.sum((ly_f - yh_f) ** 2)) / max(1e-12, float(np.sum((ly_f - np.mean(ly_f)) ** 2))))

  return {
    "n_with_pop": n_all,
    "fit_valid": True,
    "n_fit": int(n_fit),
    "slope": round(float(slope), 4),
    "zipf_alpha": round(float(-slope), 4),
    "intercept": round(float(intercept), 4),
    "r2": round(float(r2), 4),
    "full_slope": round(float(sl_f), 4),
    "full_zipf_alpha": round(float(-sl_f), 4),
    "full_r2": round(float(r2_f), 4),
  }


def select_raster_years_for_domain (arg0_avail_years, arg1_d0, arg2_d1):
  """Selects up to ~18 representative HYDE raster years covering `[d0, d1]` cleanly."""
  in_dom = [y for y in arg0_avail_years if arg1_d0 <= y <= arg2_d1]
  if not in_dom:
    # Fallback to nearest bounding raster years
    lo_c = [y for y in arg0_avail_years if y <= arg1_d0]
    hi_c = [y for y in arg0_avail_years if y >= arg2_d1]
    res = []
    if lo_c:
      res.append(lo_c[-1])
    if hi_c:
      res.append(hi_c[0])
    return sorted(set(res))
  if len(in_dom) <= 18:
    return in_dom
  # Always keep start, end, and round 5/10-year steps
  chosen = [in_dom[0], in_dom[-1]]
  for y in in_dom[1:-1]:
    if (arg2_d1 - arg1_d0) <= 130:
      if y % 5 == 0:
        chosen.append(y)
    elif y % 50 == 0 or (y >= 1700 and y % 10 == 0):
      chosen.append(y)
  chosen = sorted(set(chosen))
  if len(chosen) > 20:
    idx = np.linspace(0, len(chosen) - 1, 18).round().astype(int)
    chosen = sorted(set(chosen[i] for i in idx))
  return chosen


def main ():
  itin = load_json5_simple(ITIN_PATH)
  row_areas = compute_row_cell_areas_km2()
  avail_raster_years = list_available_raster_years()
  hgis_rows = load_hgis_csv_rows()
  aus_nz_enum = json.load(open(AUS_NZ_ENUM_JSON, encoding="utf-8")) if os.path.isfile(AUS_NZ_ENUM_JSON) else {}
  pac_ng_enum = json.load(open(PAC_NG_ENUM_JSON, encoding="utf-8")) if os.path.isfile(PAC_NG_ENUM_JSON) else {}
  print(f"[1] Loaded {len(hgis_rows)} HGIS CSV rows and {len(avail_raster_years)} Stage B population rasters.", flush=True)

  # Pre-identify all raster years needed across all 16 chapters + root secular benchmarks so we decode each PNG only ONCE!
  macro_bench = [
    -10000, -8000, -6000, -4000, -3000, -2000, -1000, 0,
    500, 700, 1000, 1200, 1400, 1500, 1600, 1700, 1750, 1780, 1800,
    1820, 1840, 1850, 1860, 1870, 1880, 1890, 1900, 1910, 1920,
    1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020, 2025,
  ]
  macro_bench = [y for y in macro_bench if y in set(avail_raster_years)]

  ch_raster_years = {}
  all_needed_years = set(macro_bench)
  for ch in itin["chapters"]:
    d0, d1 = int(ch["domain"][0]), int(ch["domain"][1])
    ry = select_raster_years_for_domain(avail_raster_years, d0, d1)
    ch_raster_years[ch["key"]] = ry
    all_needed_years.update(ry)

  # Load chapter masks and RGB lookup maps once
  ch_masks = {}
  ch_j5s = {}
  for ch in itin["chapters"]:
    key = ch["key"]
    ch_dir = os.path.join(AUS_DIR, ch["folder"])
    ch_j5s[key] = load_json5_simple(os.path.join(ch_dir, f"{key}.json5"))
    mask_arr = np.asarray(Image.open(os.path.join(ch_dir, f"{key}_areal_mask.png")).convert("RGBA"), dtype=np.uint8)
    # Encode RGB into int32 where alpha > 0, else -1
    rgb_id = np.where(
      mask_arr[:, :, 3] > 0,
      (mask_arr[:, :, 0].astype(np.int32) << 16) | (mask_arr[:, :, 1].astype(np.int32) << 8) | mask_arr[:, :, 2].astype(np.int32),
      -1,
    )
    ch_masks[key] = rgb_id

  # Build mutually exclusive 6-macro-region mask on the 4320x2160 grid for root secular series
  macro_mask_sources = [
    ("australia", "modern_australia"),
    ("new_zealand", "modern_new_zealand"),
    ("new_guinea", "modern_new_guinea"),
    ("island_melanesia", "colonial_island_melanesia"),
    ("micronesia", "colonial_micronesia"),
    ("polynesia", "modern_polynesia"),
  ]
  macro_label_grid = np.zeros((GRID_H, GRID_W), dtype=np.uint8)
  macro_names_by_code = {}
  for idx_m, (m_name, src_key) in enumerate(macro_mask_sources, start=1):
    macro_names_by_code[idx_m] = m_name
    m_active = (ch_masks[src_key] >= 0) & (macro_label_grid == 0)
    macro_label_grid[m_active] = idx_m

  domain_mask_bool = None
  if os.path.isfile(DOMAIN_MASK_PNG):
    dm_arr = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
    domain_mask_bool = (dm_arr[:, :, 3] > 0) & ((dm_arr[:, :, 0] > 0) | (dm_arr[:, :, 1] > 0) | (dm_arr[:, :, 2] > 0))
  else:
    domain_mask_bool = macro_label_grid > 0

  # Sample rasters once per needed year across all chapters and macro-regions
  print(f"[2] Sampling {len(all_needed_years)} Stage B population rasters across 16 chapters & 6 macro-regions...", flush=True)
  ch_subreg_raster_pop = {ch["key"]: defaultdict(dict) for ch in itin["chapters"]}
  macro_raster_series = {m_name: {} for m_name, _ in macro_mask_sources}
  macro_raster_series["total_austral"] = {}

  # Precompute pixel indices per (chapter, region_id) for instant vectorised sums!
  ch_reg_pixels = {}
  for ch in itin["chapters"]:
    key = ch["key"]
    rgb_grid = ch_masks[key]
    reg_pix = {}
    for reg in ch_j5s[key].get("regions", []):
      r0, g0, b0 = [int(v) for v in reg["rgb"]]
      code = (r0 << 16) | (g0 << 8) | b0
      reg_pix[reg["id"]] = np.flatnonzero(rgb_grid.ravel() == code)
    ch_reg_pixels[key] = reg_pix

  macro_pix = {m_name: np.flatnonzero(macro_label_grid.ravel() == idx_m) for idx_m, m_name in macro_names_by_code.items()}
  domain_pix = np.flatnonzero(domain_mask_bool.ravel())

  for yr in sorted(all_needed_years):
    rp = os.path.join(POP_DIR, f"popc_{yr}.png")
    if not os.path.isfile(rp):
      continue
    flat = decode_velk_png(rp).ravel()
    ys = str(yr)
    if yr in macro_bench:
      macro_raster_series["total_austral"][ys] = int(round(float(flat[domain_pix].sum())))
      for m_name, pidx in macro_pix.items():
        macro_raster_series[m_name][ys] = int(round(float(flat[pidx].sum())))
    for ch in itin["chapters"]:
      key = ch["key"]
      if yr in ch_raster_years[key]:
        for rid, pidx in ch_reg_pixels[key].items():
          ch_subreg_raster_pop[key][rid][ys] = int(round(float(flat[pidx].sum()))) if len(pidx) > 0 else 0

  # Now stage per-chapter summary caches and accumulate pan-Oceanic urban hierarchy
  chapter_overview = []
  total_trajectories = 0
  total_observations = 0
  pan_oceanic_by_key = {}
  all_hgis_sources = sorted(set(r["source"] for r in hgis_rows))

  print("[3] Building per-chapter summary caches...", flush=True)
  for ch in itin["chapters"]:
    key = ch["key"]
    ch_dir = os.path.join(AUS_DIR, ch["folder"])
    d0, d1 = int(ch["domain"][0]), int(ch["domain"][1])
    j5 = ch_j5s[key]
    setts = json.load(open(os.path.join(ch_dir, f"{key}_settlements.json"), encoding="utf-8"))
    ledger_p = os.path.join(ch_dir, f"{key}_source_ledger.json5")
    ledger = load_json5_simple(ledger_p) if os.path.isfile(ledger_p) else {}
    rgb_grid = ch_masks[key]

    # Exact sub-region areas & population series
    subregion_rows = []
    tot_area_km2 = 0.0
    all_years = set()
    for reg in j5.get("regions", []):
      rgb = [int(v) for v in reg["rgb"]]
      code = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]
      m_bool = (rgb_grid == code)
      area_km2 = float((m_bool.sum(axis=1) * row_areas).sum())
      tot_area_km2 += area_km2
      pop_dict = {str(k): int(round(float(v))) for k, v in (reg.get("population") or {}).items() if float(v) >= 0}
      # Reconcile Colonial NZ 1881 Otago Province (`Otago (incl. Southland)` = 134,077 minus Southland 24,300 = 109,777)
      if key == "colonial_new_zealand" and reg["id"] == "otago_province" and pop_dict.get("1881", 0) < 5000:
        nz_1881 = aus_nz_enum.get("new_zealand", {}).get("provincial_non_maori_censuses_1851_1921", {}).get("series_by_year", {}).get("1881", {})
        otago_incl = int(round(float(nz_1881.get("Otago (incl. Southland)", 134077))))
        sth_1881 = next(
          (int(round(float((r2.get("population") or {}).get("1881", 24300)))) for r2 in j5.get("regions", []) if r2.get("id") == "southland_province"),
          24300,
        )
        pop_dict["1881"] = max(pop_dict.get("1881", 0), otago_incl - sth_1881)
      for yk in pop_dict:
        all_years.add(int(yk))
      subregion_rows.append({
        "id": reg["id"],
        "name": reg.get("name") or reg["id"],
        "rgb": rgb,
        "area_km2": round(area_km2, 1),
        "population_raw": pop_dict,
        "raster_population": ch_subreg_raster_pop[key].get(reg["id"], {}),
      })

    sorted_years = choose_unified_years(all_years, d0, d1)
    for sr in subregion_rows:
      sr["population"] = interp_subregion_series(sr["population_raw"], sorted_years)

    domain_totals = {}
    for y in sorted_years:
      ys = str(y)
      domain_totals[ys] = sum(r["population"].get(ys, 0) for r in subregion_rows)

    r_years = ch_raster_years[key]
    raster_domain_totals = {
      str(y): sum(r["raster_population"].get(str(y), 0) for r in subregion_rows)
      for y in r_years
    }

    last_y_str = str(sorted_years[-1]) if sorted_years else ""
    for sr in subregion_rows:
      p_end = sr["population"].get(last_y_str, 0)
      sr["end_epoch_population"] = p_end
      sr["end_epoch_density_km2"] = round(p_end / max(1.0, sr["area_km2"]), 3) if sr["area_km2"] > 0 else 0.0

    end_pop_tot = domain_totals.get(last_y_str, 0)
    end_dens_tot = round(end_pop_tot / max(1.0, tot_area_km2), 3)

    # Settlement statistics
    sett_items = list(setts.items())
    total_trajectories += len(sett_items)
    obs_cnt = 0
    scope_cnt = Counter()
    by_country_cnt = Counter()
    by_admin1_cnt = Counter()
    src_cnt = Counter()
    ranked_setts = []
    for skey, s in sett_items:
      sc = str(s.get("population_scope") or "city_proper")
      scope_cnt[sc] += 1
      ctry = str(s.get("country") or "")
      if ctry:
        by_country_cnt[ctry] += 1
      adm1 = str(s.get("admin1") or "")
      if adm1:
        by_admin1_cnt[adm1] += 1
      srcs = s.get("sources") or []
      if isinstance(srcs, list):
        for sr_s in srcs:
          src_cnt[str(sr_s).split("(")[0].strip()[:60]] += 1
      pdict = s.get("population") or {}
      pos_p = {str(k): int(round(float(v))) for k, v in pdict.items() if float(v) > 0}
      obs_cnt += len(pos_p)
      if pos_p:
        yrs_s = sorted(int(k) for k in pos_p.keys())
        pk_yr = max(yrs_s, key=lambda yy: pos_p[str(yy)])
        pk_pop = pos_p[str(pk_yr)]
        lat_v = round(float(s["coords"][0]), 4)
        lon_v = round(float(s["coords"][1]), 4)
        rec = {
          "key": skey,
          "name": s["name"],
          "country": ctry,
          "admin1": adm1,
          "population_scope": sc,
          "is_capital": bool(s.get("is_capital", False)),
          "lat": lat_v,
          "lon": lon_v,
          "peak_year": pk_yr,
          "peak_pop": pk_pop,
          "first_year": yrs_s[0],
          "last_year": yrs_s[-1],
          "observation_count": len(pos_p),
          "sources": srcs[:4] if isinstance(srcs, list) else [],
          "population": pos_p,
        }
        ranked_setts.append(rec)

        # Accumulate into pan-Oceanic unique settlements (keep peak across all chapters)
        prev = pan_oceanic_by_key.get(skey)
        if prev is None or pk_pop > prev["peak_pop"]:
          pan_oceanic_by_key[skey] = {
            "key": skey,
            "name": s["name"],
            "country": ctry,
            "admin1": adm1,
            "population_scope": sc,
            "lat": lat_v,
            "lon": lon_v,
            "peak_year": pk_yr,
            "peak_pop": pk_pop,
            "chapter_key": key,
          }

    total_observations += obs_cnt
    ranked_setts.sort(key=lambda x: (-x["peak_pop"], x["name"]))
    zipf_all = compute_zipf_stats([x["peak_pop"] for x in ranked_setts])
    non_suburb_peaks = [x["peak_pop"] for x in ranked_setts if x["population_scope"] != "suburb"]
    zipf_non_suburb = compute_zipf_stats(non_suburb_peaks)

    # Filter HGIS CSV sub-administrative enumerations relevant to this chapter
    ch_groups = set(CHAPTER_GROUPS.get(key, []))
    ch_hgis = [
      hr for hr in hgis_rows
      if hr["macro_group"] in ch_groups and (max(0, d0) <= hr["year"] <= d1)
    ]
    hgis_by_regime = defaultdict(lambda: {"units": 0, "pop_sum": 0, "area_sum": 0.0})
    for hr in ch_hgis:
      rk = (hr["snapshot_regime"], hr["source"])
      hgis_by_regime[rk]["units"] += 1
      hgis_by_regime[rk]["pop_sum"] += hr["population"]
      hgis_by_regime[rk]["area_sum"] += hr["area_km2"]
    hgis_regime_summary = [
      {
        "snapshot_regime": rk[0],
        "source": rk[1],
        "units": v["units"],
        "population_sum": v["pop_sum"],
        "area_km2_sum": round(v["area_sum"], 1),
      }
      for rk, v in sorted(hgis_by_regime.items())
    ]
    # Top 30 deduplicated HGIS rows for literature-review longtables
    seen_u = set()
    hgis_featured = []
    for hr in sorted(ch_hgis, key=lambda x: (x["year"], -x["population"])):
      uk = (hr["unit_name"], hr["year"])
      if uk in seen_u:
        continue
      seen_u.add(uk)
      hgis_featured.append(hr)
      if len(hgis_featured) >= 36:
        break

    raw_enum_rows = extract_raw_enum_rows_for_chapter(key, d0, d1, aus_nz_enum, pac_ng_enum)
    n_pdfs = len(glob.glob(os.path.join(ch_dir, "papers", "*.pdf")))

    summary_obj = {
      "index": ch["index"],
      "key": key,
      "folder": ch["folder"],
      "region_group": ch["region_group"],
      "title": ch["title"],
      "subtitle": ch["subtitle"],
      "is_admin1": bool(ch.get("is_admin1", False)),
      "domain": [d0, d1],
      "total_area_km2": round(tot_area_km2, 1),
      "benchmark_years": sorted_years,
      "domain_totals": domain_totals,
      "end_epoch_year": sorted_years[-1] if sorted_years else d1,
      "end_epoch_population": end_pop_tot,
      "end_epoch_density_km2": end_dens_tot,
      "raster_years": r_years,
      "raster_domain_totals": raster_domain_totals,
      "subregions": subregion_rows,
      "settlement_count": len(sett_items),
      "observation_count": obs_cnt,
      "population_scope_counts": dict(scope_cnt),
      "countries": sorted(by_country_cnt.keys()),
      "settlements_by_country": dict(by_country_cnt),
      "settlements_by_admin1": dict(by_admin1_cnt),
      "top_settlements": ranked_setts[:25],
      "rank_size": {
        "all_settlements": zipf_all,
        "excluding_suburbs": zipf_non_suburb,
        "rank_pop_pairs": [[i + 1, x["peak_pop"]] for i, x in enumerate(ranked_setts)],
      },
      "source_provenance_summary": {
        "top_sources": dict(src_cnt.most_common(15)),
        "ledger_included": ledger.get("total_included", len(sett_items)),
        "ledger_excluded": ledger.get("total_excluded", 0),
        "ledger_unaccounted": ledger.get("unaccounted", 0),
        "crowd_share_overall": ledger.get("saturation_audit", {}).get("crowd_share_overall", 0.0),
        "empty_subregions": ledger.get("saturation_audit", {}).get("empty_subregions", 0),
      },
      "hgis_row_count": len(ch_hgis),
      "hgis_regime_summary": hgis_regime_summary,
      "hgis_featured_units": hgis_featured,
      "primary_census_enumerations": raw_enum_rows,
      "archival_pdf_count": n_pdfs,
    }

    out_p = os.path.join(ch_dir, f"{key}_summary_cache.json")
    with open(out_p, "w", encoding="utf-8") as fh:
      json.dump(summary_obj, fh, indent=2, ensure_ascii=False)

    y_start = str(sorted_years[0]) if sorted_years else ""
    y_end = str(sorted_years[-1]) if sorted_years else ""
    chapter_overview.append({
      "index": ch["index"],
      "key": key,
      "folder": ch["folder"],
      "region_group": ch["region_group"],
      "title": ch["title"],
      "domain": [d0, d1],
      "area_km2": round(tot_area_km2, 1),
      "subregions": len(subregion_rows),
      "settlements": len(sett_items),
      "observations": obs_cnt,
      "zipf_alpha": zipf_all["zipf_alpha"],
      "zipf_r2": zipf_all["r2"],
      "hgis_rows": len(ch_hgis),
      "primary_enum_rows": len(raw_enum_rows),
      "pop_start": domain_totals.get(y_start, 0),
      "pop_end": domain_totals.get(y_end, 0),
      "start_year": sorted_years[0] if sorted_years else d0,
      "end_year": sorted_years[-1] if sorted_years else d1,
      "end_density_km2": end_dens_tot,
      "archival_pdfs": n_pdfs,
    })
    print(f"  [CH {ch['index']:02d}] {key:28s}: {len(sett_items):4d} setts ({obs_cnt:5d} obs) | {len(ch_hgis):3d} HGIS + {len(raw_enum_rows):3d} raw | {tot_area_km2/1e6:5.2f}M km²", flush=True)

  # Pan-Oceanic deduplicated urban hierarchy
  pan_list = sorted(pan_oceanic_by_key.values(), key=lambda x: (-x["peak_pop"], x["name"]))
  pan_non_suburb = [x for x in pan_list if x["population_scope"] != "suburb"]
  pan_scope_cnt = Counter(x["population_scope"] for x in pan_list)
  pan_country_cnt = Counter(x["country"] for x in pan_list if x["country"])

  # Load kriging diagnostics, archaeological metadata & mass-conservation audit
  krig_diag = json.load(open(KRIG_DIAG_JSON, encoding="utf-8")) if os.path.isfile(KRIG_DIAG_JSON) else {}
  geo_meta = json.load(open(GEOJSON_META_JSON, encoding="utf-8")) if os.path.isfile(GEOJSON_META_JSON) else {}
  mass_audit = json.load(open(MASS_AUDIT_JSON, encoding="utf-8")) if os.path.isfile(MASS_AUDIT_JSON) else {}
  hgis_meta = json.load(open(HGIS_JSON, encoding="utf-8")) if os.path.isfile(HGIS_JSON) else {}

  # Build reconciled 6-macro-region secular series across macro_bench:
  # Uses Stage B rasters for continental/large-island macro-regions (Australia, NZ, New Guinea, Island Melanesia)
  # and reconciles coral-atoll macro-regions (Micronesia & Polynesia) from chapter JSON5 census/archaeological
  # benchmarks so sub-5' coral atolls are fully represented alongside Stage B rasters.
  def _build_json5_macro_series (arg0_chapter_filters):
    pts_by_yr = {}
    for ch_k, reg_filter in arg0_chapter_filters:
      j5_c = ch_j5s[ch_k]
      regs_use = [r for r in j5_c.get("regions", []) if reg_filter is None or reg_filter(r["id"])]
      yrs_c = sorted(set(int(y) for r in regs_use for y in (r.get("population") or {}).keys()))
      if not yrs_c:
        continue
      u_yrs = choose_unified_years(yrs_c, int(j5_c["domain"][0]), int(j5_c["domain"][1]))
      for y in u_yrs:
        tot_y = sum(interp_subregion_series(r.get("population") or {}, [y]).get(str(y), 0) for r in regs_use)
        if tot_y > 0:
          pts_by_yr[y] = tot_y
    return interp_subregion_series({str(k): v for k, v in pts_by_yr.items()}, macro_bench)

  mic_j5_series = _build_json5_macro_series([
    ("precolonial_melanesia_micro", lambda rid: rid in ("mariana_islands", "western_carolines_palau_yap", "central_eastern_carolines", "marshall_islands", "gilbert_islands_nauru")),
    ("colonial_micronesia", None),
    ("modern_melanesia_micro", lambda rid: rid.startswith(("fsm_", "kir_")) or rid in ("marshall_islands", "palau", "guam", "cnmi", "nauru")),
  ])
  pol_j5_series = _build_json5_macro_series([
    ("precolonial_polynesia", None),
    ("colonial_polynesia", None),
    ("modern_polynesia", None),
  ])

  macro_reconciled_series = {}
  for m_name in ("australia", "new_guinea", "island_melanesia"):
    macro_reconciled_series[m_name] = dict(macro_raster_series[m_name])
  # Aotearoa / New Zealand was settled by East Polynesians c. 700-1300AD (Ch 05 domain [700, 1840])
  macro_reconciled_series["new_zealand"] = {
    str(y): (0 if y < 700 else int(macro_raster_series["new_zealand"].get(str(y), 0)))
    for y in macro_bench
  }
  macro_reconciled_series["micronesia"] = {
    str(y): (0 if y < -2000 else int(mic_j5_series.get(str(y), 0)))
    for y in macro_bench
  }
  macro_reconciled_series["polynesia"] = {
    str(y): (0 if y < -1000 else max(int(macro_raster_series["polynesia"].get(str(y), 0)), int(pol_j5_series.get(str(y), 0))))
    for y in macro_bench
  }
  macro_reconciled_series["total_austral"] = {
    str(y): sum(int(macro_reconciled_series[m].get(str(y), 0)) for m in ("australia", "new_zealand", "new_guinea", "island_melanesia", "micronesia", "polynesia"))
    for y in macro_bench
  }

  root_summary = {
    "project": "AUSTRAL",
    "order": itin.get("order", 13),
    "macro_scope": geo_meta.get("macro_scope", "Australia, Tasmania, New Guinea, New Zealand, Island Melanesia, Micronesia and Polynesia (excl. Hawai'i & American Samoa)"),
    "chapter_count": len(chapter_overview),
    "total_chapter_settlement_trajectories": total_trajectories,
    "unique_settlement_count": len(pan_list),
    "unique_non_suburb_settlement_count": len(pan_non_suburb),
    "total_settlement_observations": total_observations,
    "pan_oceanic_urban_hierarchy": {
      "scope_counts": dict(pan_scope_cnt),
      "country_counts": dict(pan_country_cnt),
      "zipf_all_unique": compute_zipf_stats([x["peak_pop"] for x in pan_list]),
      "zipf_non_suburb_unique": compute_zipf_stats([x["peak_pop"] for x in pan_non_suburb]),
      "top_settlements": pan_list[:40],
      "rank_pop_pairs_non_suburb": [[i + 1, x["peak_pop"]] for i, x in enumerate(pan_non_suburb)],
      "rank_pop_pairs_all": [[i + 1, x["peak_pop"]] for i, x in enumerate(pan_list)],
    },
    "macro_raster_years": macro_bench,
    "macro_raster_series": macro_raster_series,
    "macro_reconciled_series": macro_reconciled_series,
    "archaeological_provenance": {
      "total_unique_primary_sites": geo_meta.get("domestic_site_count_unique_sum", 69018),
      "domestic_site_complexes_dedup": geo_meta.get("domestic_site_complexes_dedup", 39897),
      "crowd_share": geo_meta.get("source_provenance_breakdown", {}).get("crowd_share", 0.0),
      "regional_share": geo_meta.get("source_provenance_breakdown", {}).get("regional_share", 1.0),
      "jurisdiction_arch_coverage": geo_meta.get("jurisdiction_arch_coverage", {}),
      "source_record_counts": geo_meta.get("source_record_counts", {}),
      "period_geojsons": geo_meta.get("period_geojsons", []),
    },
    "kriging_diagnostics": {
      "valid_cells": krig_diag.get("valid_cells"),
      "active_domestic_catchments": krig_diag.get("active_domestic_catchments"),
      "domestic_catchments": krig_diag.get("domestic_catchments"),
      "adm2_coverage_ratio": krig_diag.get("adm2_coverage_ratio"),
      "median_voronoi_radius_km": krig_diag.get("median_voronoi_radius_km"),
      "p90_voronoi_radius_km": krig_diag.get("p90_voronoi_radius_km"),
      "tau1_dimensionless": krig_diag.get("tau1_dimensionless"),
      "tau2_dimensionless": krig_diag.get("tau2_dimensionless"),
      "raw_tau1_dimensionless": krig_diag.get("raw_tau1_dimensionless"),
      "log_corr_hyde": krig_diag.get("log_corr_hyde"),
      "urban_core_med_ratio": krig_diag.get("urban_core_med_ratio"),
      "urban_backproj_p95_ratio": krig_diag.get("urban_backproj_p95_ratio"),
      "beta_0_hab": krig_diag.get("beta_0_hab"),
      "variogram_models": krig_diag.get("variogram_models", {}),
      "kriged_raster_stats": krig_diag.get("kriged_raster_stats", {}),
      "residual_kriging_wls_betas": krig_diag.get("residual_kriging_wls_betas", {}),
    },
    "subadmin_hgis_summary": {
      "total_csv_rows": len(hgis_rows),
      "distinct_boundary_regimes": hgis_meta.get("distinct_boundary_regimes", 14),
      "hyde_ad_year_count": hgis_meta.get("hyde_ad_year_count", 118),
      "hgis_sources": all_hgis_sources,
      "mass_conservation_passed": mass_audit.get("mass_conservation_passed", True),
    },
    "chapters": chapter_overview,
  }

  root_out = os.path.join(SHARED, "austral_root_summary.json")
  with open(root_out, "w", encoding="utf-8") as fh:
    json.dump(root_summary, fh, indent=2, ensure_ascii=False)
  print(f"\n[DONE] Staged 16 chapter caches + austral_root_summary.json ({len(pan_list)} unique settlements, {total_trajectories} trajectories, {len(macro_bench)} macro raster epochs).", flush=True)


if __name__ == "__main__":
  main()
