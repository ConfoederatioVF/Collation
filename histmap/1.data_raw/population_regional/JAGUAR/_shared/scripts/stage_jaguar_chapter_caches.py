"""Stages pre-computed JSON summary caches for all 14 Project JAGUAR chapters
and the root synthesis (`JAGUAR/_shared/jaguar_root_summary.json`).

Strictly raster-only / data-only (imports NO matplotlib) so POLARIS Gatekeeper D2
keeps raster-to-cache aggregation cleanly decoupled from 100% vector figure scripts.

Computes for each chapter `<chapter_dir>/<stem>_summary_cache.json`:
  - `chapter_meta`: index, stem, title, subtitle, domain, group, folder, regime, jurisdictions
  - `area_km2` and `subregions`: id, name, rgb, area_km2, pixel_count, start_pop, peak_pop,
    end_pop, end_density_km2, trajectory (computed strictly from JAGUAR `2.population_rasters`
    masked by `<stem>_areal_mask.png`)
  - `domain_trajectory`: `{ "<year>": <float> }` across all overlapping HYDE years
  - `settlement_stats`: total_settlements, suburb_count, city_proper_count, top_settlements (top 20),
    zipf_stats (for n >= 25), country_counts
  - `hgis_subadmin_table`: top 15-30 authentic scraped sub-administrative enumeration rows
    relevant to that chapter's region and era, ready for `viscount_table()` rendering.
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
JAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JAGUAR")
SHARED = os.path.join(JAG_DIR, "_shared")
ITIN_PATH = os.path.join(JAG_DIR, "jaguar_itinerary.json5")
AREAL_CFG_PATH = os.path.join(JAG_DIR, "jaguar_areal_masks.json5")
POP_DIR = os.path.join(SHARED, "sites_jaguar_mesoamerica", "2.population_rasters")
KRIG_DIAG_PATH = os.path.join(SHARED, "sites_jaguar_mesoamerica", "config", "kriging_diagnostics.json")
DOMAIN_MASK_PATH = os.path.join(SHARED, "sites_jaguar_mesoamerica", "config", "jaguar_domain_mask.png")
HGIS_CSV = os.path.join(SHARED, "subadmin_hgis", "subadmin_enumerations_for_literature_reviews.csv")
HGIS_LIT_JSON = os.path.join(SHARED, "subadmin_hgis", "subadmin_enumerations_for_literature_reviews.json")
JSE_PATH = os.path.join(SHARED, "subadmin_hgis", "parsed", "jaguar_subadmin_enumerations.json")
ENUM_SRC_PATH = os.path.join(SHARED, "subadmin_hgis", "parsed", "jaguar_enum_sources.json")
WAVE2_PATH = os.path.join(SHARED, "wave2_papers_manifest.json")

GRID_W, GRID_H = 4320, 2160
CELL_LON_RAD = 2.0 * math.pi / GRID_W
R_EARTH_KM = 6371.0088

# Bounding crop covering all of JAGUAR (lon -120..-55, lat 4..36) for fast exact raster decoding
# col = (lon + 180) * 4320 / 360 -> 720..1500; row = (90 - lat) * 2160 / 180 -> 648..1032
R0, R1 = 620, 1050
C0, C1 = 700, 1520

CHAPTER_COUNTRIES = {
  "precolumbian_mesoamerica": {"Mexico"},
  "classic_postclassic_maya": {"Mexico", "Guatemala", "Belize", "Honduras", "El Salvador"},
  "aztec_late_postclassic_mexico": {"Mexico"},
  "precolumbian_lower_central_america": {"Honduras", "Nicaragua", "Costa Rica", "Panama", "El Salvador"},
  "precolumbian_caribbean_islands": {
    "Cuba", "Haiti", "Dominican Republic", "Jamaica", "Puerto Rico", "The Bahamas", "Bahamas",
    "Barbados", "Trinidad and Tobago", "Guadeloupe", "Martinique", "Saint Lucia", "Grenada",
    "Dominica", "Antigua and Barbuda", "Saint Kitts and Nevis", "Saint Vincent and the Grenadines",
    "Aruba", "Curaçao", "Caribbean Netherlands", "United States Virgin Islands", "British Virgin Islands",
    "Cayman Islands", "Turks and Caicos Islands", "Anguilla", "Montserrat", "Caribbean",
  },
  "conquest_collapse_mesoamerica": {"Mexico", "Guatemala", "Belize", "Honduras", "El Salvador", "Nicaragua", "Costa Rica", "Panama"},
  "viceroyalty_of_new_spain": {"Mexico"},
  "captaincy_general_guatemala": {"Guatemala", "Belize", "Honduras", "El Salvador", "Nicaragua", "Costa Rica", "Panama"},
  "conquest_indigenous_caribbean": {
    "Cuba", "Haiti", "Dominican Republic", "Jamaica", "Puerto Rico", "The Bahamas", "Bahamas",
    "Barbados", "Trinidad and Tobago", "Guadeloupe", "Martinique", "Saint Lucia", "Grenada",
    "Dominica", "Antigua and Barbuda", "Saint Kitts and Nevis", "Saint Vincent and the Grenadines",
    "Caribbean",
  },
  "colonial_caribbean_plantation": {
    "Cuba", "Haiti", "Dominican Republic", "Jamaica", "Puerto Rico", "The Bahamas", "Bahamas",
    "Barbados", "Trinidad and Tobago", "Guadeloupe", "Martinique", "Saint Lucia", "Grenada",
    "Dominica", "Antigua and Barbuda", "Saint Kitts and Nevis", "Saint Vincent and the Grenadines",
    "Aruba", "Curaçao", "Caribbean Netherlands", "United States Virgin Islands", "British Virgin Islands",
    "Cayman Islands", "Turks and Caicos Islands", "Anguilla", "Montserrat", "Bermuda",
    "Saint Barthelemy", "Saint-Martin", "Sint Maarten",
  },
  "mexico_after_independence": {"Mexico"},
  "central_american_republics": {"Guatemala", "Belize", "Honduras", "El Salvador", "Nicaragua", "Costa Rica", "Panama"},
  "greater_antilles_modern": {"Cuba", "Haiti", "Dominican Republic", "Jamaica", "Puerto Rico", "Cayman Islands"},
  "lesser_antilles_bahamas_bermuda": {
    "The Bahamas", "Bahamas", "Bermuda", "Barbados", "Trinidad and Tobago", "Guadeloupe",
    "Martinique", "Saint Lucia", "Grenada", "Dominica", "Antigua and Barbuda",
    "Saint Kitts and Nevis", "Saint Vincent and the Grenadines", "Aruba", "Curaçao",
    "Caribbean Netherlands", "United States Virgin Islands", "British Virgin Islands",
    "Turks and Caicos Islands", "Anguilla", "Montserrat", "Saint Barthelemy", "Saint-Martin", "Sint Maarten",
  },
}

# Pre-Columbian CSV unit prefixes/tokens matching chapters 1-5
PRECOL_UNIT_MATCH = {
  "precolumbian_mesoamerica": (
    "olmec", "veracruz", "basin", "mexico", "oaxaca", "mixteca", "zapotec", "teotihuacan",
    "west mexico", "santiago", "balsas", "bajio", "sierra madre", "sonora", "aridoamerica",
    "toltec", "juxtlahuaca", "huastec", "tarascan", "aztec",
  ),
  "classic_postclassic_maya": ("maya", "peten", "yucatan", "belize", "copan", "motagua", "chiapas", "grijalva", "quiche", "cakchiquel"),
  "aztec_late_postclassic_mexico": (
    "aztec", "tenochtitlan", "mexica", "tarascan", "purepecha", "tlaxcala", "mixtec", "zapotec",
    "basin", "mexico", "oaxaca", "west mexico", "bajio", "sierra madre", "aridoamerica", "gulf", "huastec",
  ),
  "precolumbian_lower_central_america": ("cocle", "chiriqui", "nicaragua", "nicoya", "mosquitia", "honduras", "darien", "costa rica", "panama", "lenca", "chorotega"),
  "precolumbian_caribbean_islands": ("cuba", "hispaniola", "jamaica", "puerto rico", "lucayan", "bahamas", "antilles", "trinidad", "taino", "saladoid", "igneri", "carib"),
}

# Primary JSE eras mapped cleanly to chapters 6-14
CHAPTER_JSE_ERAS = {
  "conquest_collapse_mesoamerica": [("colonial_new_spain_1570_1810", 1518, 1650)],
  "viceroyalty_of_new_spain": [("colonial_new_spain_1570_1810", 1535, 1821)],
  "captaincy_general_guatemala": [("colonial_central_america_1778_1816", 1524, 1821)],
  "conquest_indigenous_caribbean": [],
  "colonial_caribbean_plantation": [("colonial_caribbean_bermuda_1655_1899", 1650, 1898)],
  "mexico_after_independence": [("mexico_republic_19c_1820_1889", 1821, 1894), ("mexico_inegi_1895_2020", 1895, 2025)],
  "central_american_republics": [("central_america_modern_1864_2024", 1821, 2025)],
  "greater_antilles_modern": [("greater_antilles_historic_1899_1979", 1838, 1979), ("greater_antilles_modern_1935_2023", 1935, 2025)],
  "lesser_antilles_bahamas_bermuda": [("lesser_antilles_bahamas_bermuda_1900_2025", 1838, 2025), ("colonial_caribbean_bermuda_1655_1899", 1838, 1899)],
}


def load_json5_simple (arg0_path):
  raw = open(arg0_path, encoding="utf-8").read()
  raw = re.sub(r"//.*", "", raw)
  raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
  raw = re.sub(r",(\s*[}\]])", r"\1", raw)
  raw = re.sub(r"(\{|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
  return json.loads(raw)


def compute_row_cell_areas_km2 ():
  lats_n = np.linspace(90.0, -90.0, GRID_H + 1)
  sin_n = np.sin(np.radians(lats_n[:-1]))
  sin_s = np.sin(np.radians(lats_n[1:]))
  return (R_EARTH_KM ** 2) * CELL_LON_RAD * np.abs(sin_n - sin_s)


def decode_velk_crop (arg0_path):
  arr = np.ascontiguousarray(Image.open(arg0_path).convert("RGBA"), dtype=np.uint8)[R0:R1, C0:C1]
  vals = arr.view(">f4").reshape(arr.shape[:2])
  return np.where(np.isfinite(vals) & (vals > 0.0) & (vals < 1e8), vals, 0.0).astype(np.float64)


def compute_zipf_stats (arg0_setts_dict):
  """Computes OLS log-log rank-size fit over peak settlement populations (strictly n >= 25)."""
  peaks = []
  yr_counts = Counter()
  for s in arg0_setts_dict.values():
    pdict = s.get("population") or {}
    pos = [(int(k), float(v)) for k, v in pdict.items() if 0.0 < float(v) < 25_000_000.0]
    if not pos:
      continue
    pk_yr, pk_val = max(pos, key=lambda kv: kv[1])
    peaks.append(pk_val)
    yr_counts[pk_yr] += 1
  n_all = len(peaks)
  if n_all < 25:
    return {"n": n_all, "slope": None, "alpha": None, "r2": None, "year_used": None, "n_fit": 0}
  peaks.sort(reverse=True)
  ranks = np.arange(1, n_all + 1, dtype=np.float64)
  pops = np.array(peaks, dtype=np.float64)
  n_fit = min(max(25, n_all // 2), 180)
  lx = np.log10(ranks[:n_fit])
  ly = np.log10(pops[:n_fit])
  slope, intercept = np.polyfit(lx, ly, 1)
  y_hat = slope * lx + intercept
  ss_res = float(np.sum((ly - y_hat) ** 2))
  ss_tot = float(np.sum((ly - np.mean(ly)) ** 2))
  r2 = max(0.0, 1.0 - ss_res / max(1e-12, ss_tot))
  mode_yr = yr_counts.most_common(1)[0][0] if yr_counts else None
  return {
    "n": n_all,
    "n_fit": int(n_fit),
    "slope": round(float(slope), 4),
    "alpha": round(float(-slope), 4),
    "r2": round(float(r2), 4),
    "year_used": int(mode_yr) if mode_yr is not None else None,
  }


def build_hgis_subadmin_table (arg0_stem, arg1_d0, arg2_d1, arg3_jse, arg4_csv_rows, arg5_enum_sources):
  """Builds 15-30 authentic scraped sub-administrative enumeration rows matched to chapter era & region."""
  rows_out = []
  seen = set()

  # 1. For Colonial & Modern chapters (Ch 6-8, 10-14), prioritise primary census/fiscal series from jaguar_subadmin_enumerations.json
  era_specs = CHAPTER_JSE_ERAS.get(arg0_stem, [])
  cand_jse = []
  for era_key, y_lo, y_hi in era_specs:
    era_dict = arg3_jse.get(era_key, {})
    for uid, rec in era_dict.items():
      ctry = rec.get("admin_country", "")
      if ctry not in CHAPTER_COUNTRIES.get(arg0_stem, set()):
        continue
      uname = rec.get("name", uid)
      lvl = rec.get("level", "")
      skeys = rec.get("source_keys") or []
      src_lbl = ", ".join(
        arg5_enum_sources.get(sk, {}).get("author", sk).split("(")[0].strip()[:36]
        for sk in skeys[:2]
      )
      for yk, pval in (rec.get("years") or {}).items():
        try:
          yr = int(yk)
          pv = int(round(float(pval)))
        except Exception:
          continue
        if y_lo <= yr <= y_hi and pv > 0:
          cand_jse.append({
            "unit_code": uid,
            "unit_name": uname,
            "country": ctry,
            "level": lvl,
            "year": yr,
            "population": pv,
            "source": src_lbl or era_key,
          })

  if cand_jse:
    # Spread selections cleanly across countries and benchmark years (latest & earliest major benchmarks)
    by_unit = defaultdict(list)
    for r in cand_jse:
      by_unit[(r["country"], r["unit_name"])].append(r)
    picked = []
    # Sort units by peak population, take up to 24 diverse sub-admin rows (picking earliest + latest for top units if few units)
    unit_ranks = sorted(by_unit.items(), key=lambda kv: -max(x["population"] for x in kv[1]))
    if len(unit_ranks) >= 18:
      # Ensure every country in the chapter gets represented first
      by_c = defaultdict(list)
      for uk, rlist in unit_ranks:
        by_c[uk[0]].append((uk, rlist))
      # Round-robin across countries
      idx_c = 0
      c_order = sorted(by_c.keys(), key=lambda c: -max(x["population"] for _, rl in by_c[c] for x in rl))
      while len(picked) < 25:
        added_any = False
        for c in c_order:
          if idx_c < len(by_c[c]):
            _, rlist = by_c[c][idx_c]
            rlist_s = sorted(rlist, key=lambda x: x["year"])
            chosen = rlist_s[-1]
            sk = (chosen["unit_name"], chosen["year"])
            if sk not in seen:
              seen.add(sk)
              picked.append(chosen)
              added_any = True
              if len(picked) >= 25:
                break
        if not added_any:
          break
        idx_c += 1
    else:
      for _, rlist in unit_ranks:
        rlist_s = sorted(rlist, key=lambda x: x["year"])
        sel = [rlist_s[0], rlist_s[-1]] if len(rlist_s) >= 2 else [rlist_s[0]]
        for chosen in sel:
          sk = (chosen["unit_name"], chosen["year"])
          if sk not in seen:
            seen.add(sk)
            picked.append(chosen)
            if len(picked) >= 26:
              break
        if len(picked) >= 26:
          break
    rows_out = sorted(picked, key=lambda x: (x["year"], -x["population"]))

  # 2. If fewer than 15 rows (e.g. Ch 1-5 Pre-Columbian or Ch 6/9 Conquest), supplement from CSV
  if len(rows_out) < 15:
    ctry_set = CHAPTER_COUNTRIES.get(arg0_stem, set())
    toks = PRECOL_UNIT_MATCH.get(arg0_stem, ())
    csv_cands = []
    for hr in arg4_csv_rows:
      yr = hr["year"]
      # Allow slight bracket window for pre-Columbian / conquest snapshots
      lo_win = 1000 if arg0_stem == "aztec_late_postclassic_mexico" else (arg1_d0 if arg1_d0 >= 0 else 0)
      hi_win = arg2_d1 + (50 if arg0_stem in ("conquest_collapse_mesoamerica", "conquest_indigenous_caribbean") else 10)
      if not (lo_win <= yr <= hi_win):
        continue
      c = hr["country"]
      un_low = hr["unit_name"].lower()
      matched = False
      if c in ctry_set:
        matched = True
      elif (c.startswith("PRECOLUMBIAN") or c in ("DEJURE", "FALLBACK", "OHM")) and toks:
        if any(t in un_low for t in toks):
          matched = True
      elif arg0_stem == "conquest_indigenous_caribbean" and any(
        t in un_low for t in ("cuba", "hispaniola", "jamaica", "puerto rico", "santo domingo", "bahamas", "antilles", "trinidad", "barbados", "taino", "carib")
      ):
        matched = True
      elif arg0_stem == "conquest_collapse_mesoamerica" and (c in ("Mexico", "Guatemala", "Honduras", "Nicaragua", "El Salvador", "Costa Rica", "Panama", "DEJURE", "OHM") or c.startswith("PRECOLUMBIAN")):
        if not (c.startswith("PRECOLUMBIAN") or c in ("DEJURE", "OHM")) or any(t in un_low for t in ("mexico", "aztec", "maya", "oaxaca", "zapotec", "tarascan", "gulf", "bajio", "nicaragua", "honduras", "cocle", "chiriqui", "new spain", "guatemala")):
          matched = True
      if matched and hr["population"] > 0:
        csv_cands.append(hr)

    # Deduplicate and spread across snapshots
    csv_cands.sort(key=lambda x: (-x["population"], x["year"]))
    for hr in csv_cands:
      sk = (hr["unit_name"], hr["year"])
      if sk in seen:
        continue
      seen.add(sk)
      rows_out.append({
        "unit_code": hr["unit_code"],
        "unit_name": hr["unit_name"],
        "country": hr["country"],
        "level": f"regime_{hr['snapshot_regime']}",
        "year": hr["year"],
        "population": hr["population"],
        "area_km2": hr["area_km2"],
        "source": hr["source"],
      })
      if len(rows_out) >= 24:
        break
    rows_out.sort(key=lambda x: (x["year"], -x["population"]))

  return rows_out[:28]


def main ():
  itin = load_json5_simple(ITIN_PATH)
  areal_cfg = load_json5_simple(AREAL_CFG_PATH)
  hyde_years = [int(y) for y in areal_cfg["hyde_years"]]
  row_areas = compute_row_cell_areas_km2()
  row_areas_crop = row_areas[R0:R1, None]

  jse = json.load(open(JSE_PATH, encoding="utf-8"))
  enum_src_meta = json.load(open(ENUM_SRC_PATH, encoding="utf-8"))
  enum_sources = enum_src_meta.get("sources", {})
  krig_diag = json.load(open(KRIG_DIAG_PATH, encoding="utf-8"))
  wave2 = json.load(open(WAVE2_PATH, encoding="utf-8"))
  hgis_lit_json = json.load(open(HGIS_LIT_JSON, encoding="utf-8"))

  csv_rows = []
  with open(HGIS_CSV, encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
      try:
        csv_rows.append({
          "snapshot_regime": int(r["snapshot_regime"]),
          "country": str(r["country"]).strip(),
          "unit_code": str(r["unit_code"]).strip(),
          "unit_name": str(r["unit_name"]).strip(),
          "year": int(r["year"]),
          "population": int(round(float(r["population"]))),
          "area_km2": round(float(r["area_km2"]), 1),
          "source": str(r["source"]).strip(),
        })
      except Exception:
        continue

  print(f"[1] Loading 14 chapter areal masks and preparing exact pixel indices...", flush=True)
  # Load global JAGUAR domain mask crop
  dom_arr = np.asarray(Image.open(DOMAIN_MASK_PATH).convert("RGBA"), dtype=np.uint8)[R0:R1, C0:C1]
  dom_mask_bool = (dom_arr[:, :, 3] > 0) & ((dom_arr[:, :, 0] > 0) | (dom_arr[:, :, 1] > 0) | (dom_arr[:, :, 2] > 0))
  jaguar_total_area_km2 = float((dom_mask_bool * row_areas_crop).sum())

  chapter_preps = []
  for ch in itin["chapters"]:
    stem = ch["stem"]
    ch_dir = os.path.join(JAG_DIR, ch["group"], ch["folder"])
    j5 = load_json5_simple(os.path.join(ch_dir, f"{stem}.json5"))
    mask_path = os.path.join(ch_dir, f"{stem}_areal_mask.png")
    mask_crop = np.asarray(Image.open(mask_path).convert("RGBA"), dtype=np.uint8)[R0:R1, C0:C1]
    alpha_ok = mask_crop[:, :, 3] > 0

    sr_preps = []
    ch_area_km2 = 0.0
    for reg in j5.get("regions", []):
      rgb = tuple(int(v) for v in reg["rgb"])
      m_bool = alpha_ok & (mask_crop[:, :, 0] == rgb[0]) & (mask_crop[:, :, 1] == rgb[1]) & (mask_crop[:, :, 2] == rgb[2])
      px_cnt = int(m_bool.sum())
      area_km2 = float((m_bool * row_areas_crop).sum())
      ch_area_km2 += area_km2
      sr_preps.append({
        "id": reg["id"],
        "name": reg.get("name") or reg["id"],
        "rgb": list(rgb),
        "area_km2": round(area_km2, 1),
        "pixel_count": px_cnt,
        "mask_idx": np.flatnonzero(m_bool.ravel()),
        "raw_traj": {},
      })

    d0, d1 = int(ch["domain"][0]), int(ch["domain"][1])
    ov_yrs = [y for y in hyde_years if d0 <= y <= d1]
    # Also find bracketing HYDE years for chapters with sparse centennial overlap (e.g. Ch 5, Ch 6, Ch 9)
    prev_y = max((y for y in hyde_years if y <= d0), default=hyde_years[0])
    next_y = min((y for y in hyde_years if y >= d1), default=hyde_years[-1])
    needed_yrs = set(ov_yrs) | {prev_y, next_y}
    chapter_preps.append({
      "ch": ch,
      "ch_dir": ch_dir,
      "j5": j5,
      "area_km2": round(ch_area_km2, 1),
      "subregions": sr_preps,
      "ov_yrs": ov_yrs,
      "prev_y": prev_y,
      "next_y": next_y,
      "needed_yrs": needed_yrs,
    })

  print(f"[2] Streaming all {len(hyde_years)} JAGUAR 2.population_rasters once for exact aggregation...", flush=True)
  jaguar_root_trajectory = {}
  for y in hyde_years:
    rp = os.path.join(POP_DIR, f"popc_{y}.png")
    if not os.path.isfile(rp):
      continue
    grid = decode_velk_crop(rp)
    flat = grid.ravel()
    jaguar_root_trajectory[str(y)] = round(float(grid[dom_mask_bool].sum()), 1)
    for cp in chapter_preps:
      if y in cp["needed_yrs"]:
        for sr in cp["subregions"]:
          sr["raw_traj"][y] = float(flat[sr["mask_idx"]].sum())

  def interp_log (arg0_raw_dict, arg1_target_y, arg2_y0, arg3_y1):
    v0 = arg0_raw_dict.get(arg2_y0, 0.0)
    v1 = arg0_raw_dict.get(arg3_y1, 0.0)
    if arg2_y0 == arg3_y1 or arg1_target_y == arg2_y0:
      return v0
    if arg1_target_y == arg3_y1:
      return v1
    t = (arg1_target_y - arg2_y0) / float(arg3_y1 - arg2_y0)
    if v0 > 0.0 and v1 > 0.0:
      return math.exp((1.0 - t) * math.log(v0) + t * math.log(v1))
    return (1.0 - t) * v0 + t * v1

  print(f"[3] Writing 14 per-chapter `<stem>_summary_cache.json` files and root summary...", flush=True)
  chapters_overview = []
  total_settlements_all = 0
  total_suburbs_all = 0
  total_city_proper_all = 0
  zipf_by_chapter = []

  for cp in chapter_preps:
    ch = cp["ch"]
    stem = ch["stem"]
    ch_dir = cp["ch_dir"]
    d0, d1 = int(ch["domain"][0]), int(ch["domain"][1])

    # Build trajectory years: all overlapping HYDE years; if domain endpoints are > 15 yrs from nearest HYDE year
    # or fewer than 4 overlapping points exist, include raster-interpolated domain endpoints cleanly.
    traj_years = list(cp["ov_yrs"])
    if len(traj_years) < 4:
      if d0 not in traj_years:
        traj_years.insert(0, d0)
      if d1 not in traj_years:
        traj_years.append(d1)
    traj_years = sorted(set(traj_years))

    subregions_out = []
    domain_traj = {str(y): 0.0 for y in traj_years}
    for sr in cp["subregions"]:
      raw_t = sr["raw_traj"]
      avail_sorted = sorted(raw_t.keys())
      sr_traj = {}
      for y in traj_years:
        if y in raw_t:
          val = raw_t[y]
        else:
          y_lo = max((ay for ay in avail_sorted if ay <= y), default=avail_sorted[0])
          y_hi = min((ay for ay in avail_sorted if ay >= y), default=avail_sorted[-1])
          val = interp_log(raw_t, y, y_lo, y_hi)
        val_r = round(val, 1)
        sr_traj[str(y)] = val_r
        domain_traj[str(y)] = round(domain_traj[str(y)] + val_r, 1)

      vals_seq = [sr_traj[str(y)] for y in traj_years]
      start_p = vals_seq[0] if vals_seq else 0.0
      peak_p = max(vals_seq) if vals_seq else 0.0
      end_p = vals_seq[-1] if vals_seq else 0.0
      end_dens = round(end_p / max(1.0, sr["area_km2"]), 3)
      subregions_out.append({
        "id": sr["id"],
        "name": sr["name"],
        "rgb": sr["rgb"],
        "area_km2": sr["area_km2"],
        "pixel_count": sr["pixel_count"],
        "start_pop": start_p,
        "peak_pop": peak_p,
        "end_pop": end_p,
        "end_density_km2": end_dens,
        "trajectory": sr_traj,
      })

    # Settlements analysis
    sett_path = os.path.join(ch_dir, f"{stem}_settlements.json")
    setts = json.load(open(sett_path, encoding="utf-8"))
    suburb_cnt = 0
    city_proper_cnt = 0
    country_cnt = Counter()
    top_setts = []
    for s in setts.values():
      sc = str(s.get("population_scope") or "city_proper")
      if sc == "suburb":
        suburb_cnt += 1
      else:
        city_proper_cnt += 1
      ctry = str(s.get("country") or "")
      if ctry:
        country_cnt[ctry] += 1
      pdict = s.get("population") or {}
      pos = [(int(k), int(round(float(v)))) for k, v in pdict.items() if 0.0 < float(v) < 25_000_000.0]
      if pos:
        pk_yr, pk_pop = max(pos, key=lambda kv: kv[1])
        top_setts.append({
          "name": s["name"],
          "country": ctry,
          "lat": round(float(s["coords"][0]), 4),
          "lon": round(float(s["coords"][1]), 4),
          "peak_year": pk_yr,
          "peak_pop": pk_pop,
          "scope": sc,
          "sources": s.get("sources") or [],
        })
    top_setts.sort(key=lambda x: -x["peak_pop"])
    zipf_stats = compute_zipf_stats(setts)

    total_settlements_all += len(setts)
    total_suburbs_all += suburb_cnt
    total_city_proper_all += city_proper_cnt

    # HGIS sub-admin rows ready for viscount_table()
    hgis_table = build_hgis_subadmin_table(stem, d0, d1, jse, csv_rows, enum_sources)

    n_pdfs = len(glob.glob(os.path.join(ch_dir, "papers", "*.pdf")))
    cache_obj = {
      "chapter_meta": {
        "index": ch["index"],
        "stem": stem,
        "title": ch["title"],
        "subtitle": ch["subtitle"],
        "domain": [d0, d1],
        "group": ch["group"],
        "folder": ch["folder"],
        "regime": ch.get("regime", ""),
        "jurisdictions": ch.get("jurisdictions", []),
      },
      "area_km2": cp["area_km2"],
      "subregions": subregions_out,
      "domain_trajectory": domain_traj,
      "settlement_stats": {
        "total_settlements": len(setts),
        "suburb_count": suburb_cnt,
        "city_proper_count": city_proper_cnt,
        "top_settlements": top_setts[:20],
        "zipf_stats": zipf_stats,
        "country_counts": dict(sorted(country_cnt.items(), key=lambda kv: -kv[1])),
      },
      "hgis_subadmin_table": hgis_table,
      "archival_pdf_count": n_pdfs,
    }
    out_cache = os.path.join(ch_dir, f"{stem}_summary_cache.json")
    with open(out_cache, "w", encoding="utf-8") as fh:
      json.dump(cache_obj, fh, indent=2, ensure_ascii=False)

    y_first, y_last = str(traj_years[0]), str(traj_years[-1])
    chapters_overview.append({
      "index": ch["index"],
      "stem": stem,
      "title": ch["title"],
      "group": ch["group"],
      "folder": ch["folder"],
      "domain": [d0, d1],
      "area_km2": cp["area_km2"],
      "subregions": len(subregions_out),
      "start_year": int(y_first),
      "end_year": int(y_last),
      "start_pop": domain_traj[y_first],
      "peak_pop": max(domain_traj.values()) if domain_traj else 0.0,
      "end_pop": domain_traj[y_last],
      "settlement_count": len(setts),
      "suburb_count": suburb_cnt,
      "city_proper_count": city_proper_cnt,
      "zipf_alpha": zipf_stats["alpha"],
      "zipf_r2": zipf_stats["r2"],
      "hgis_table_rows": len(hgis_table),
      "archival_pdfs": n_pdfs,
    })
    zipf_by_chapter.append({
      "index": ch["index"],
      "stem": stem,
      "title": ch["title"],
      "domain": [d0, d1],
      "n": zipf_stats["n"],
      "alpha": zipf_stats["alpha"],
      "r2": zipf_stats["r2"],
    })
    print(
      f"  [CH {ch['index']:02d}] {stem:35s}: area={cp['area_km2']/1e6:5.2f}M km² | "
      f"pop({y_first}->{y_last})={domain_traj[y_first]/1e6:5.2f}M->{domain_traj[y_last]/1e6:6.2f}M | "
      f"setts={len(setts):5d} | Zipf a={zipf_stats['alpha']:.2f} R2={zipf_stats['r2']:.2f} | HGIS={len(hgis_table):2d}",
      flush=True,
    )

  # Subadmin HGIS coverage summary by era & snapshot
  jse_era_summary = []
  for era_k, units_dict in jse.items():
    obs_cnt = sum(len(u.get("years", {})) for u in units_dict.values())
    ctries = sorted(set(u.get("admin_country", "") for u in units_dict.values() if u.get("admin_country")))
    yrs_era = [int(y) for u in units_dict.values() for y in u.get("years", {}).keys() if str(y).isdigit()]
    jse_era_summary.append({
      "era": era_k,
      "units": len(units_dict),
      "observations": obs_cnt,
      "jurisdictions": len(ctries),
      "year_min": min(yrs_era) if yrs_era else None,
      "year_max": max(yrs_era) if yrs_era else None,
    })

  root_summary = {
    "project": "JAGUAR",
    "macro_scope": itin.get("macro_scope", ""),
    "total_area_km2": round(jaguar_total_area_km2, 1),
    "chapter_count": len(chapters_overview),
    "gridded_trajectory": jaguar_root_trajectory,
    "chapters": chapters_overview,
    "settlement_totals": {
      "total_chapter_settlement_records": total_settlements_all,
      "city_proper_records": total_city_proper_all,
      "suburb_records": total_suburbs_all,
      "zipf_by_chapter": zipf_by_chapter,
    },
    "archaeological_sites": {
      "total_unique_sites": krig_diag.get("domestic_site_count_unique_sum", 0),
      "regional_share": krig_diag.get("arch_regional_share", 0.0),
      "crowd_share": krig_diag.get("arch_crowd_share", 0.0),
      "domestic_catchments": krig_diag.get("domestic_catchments", 0),
      "active_domestic_catchments": krig_diag.get("active_domestic_catchments", 0),
      "adm2_coverage_ratio": krig_diag.get("adm2_coverage_ratio", 0.0),
      "jurisdiction_arch_coverage": krig_diag.get("jurisdiction_arch_coverage", {}),
      "source_provenance_breakdown": krig_diag.get("source_provenance_breakdown", {}),
    },
    "kriging_diagnostics": krig_diag,
    "subadmin_hgis_coverage": {
      "total_csv_rows": len(csv_rows),
      "distinct_boundary_regimes": hgis_lit_json.get("distinct_boundary_regimes", 0),
      "hyde_ad_year_count": hgis_lit_json.get("hyde_ad_year_count", 0),
      "primary_sources_count": len(enum_sources),
      "primary_units": enum_src_meta.get("total_units", 0),
      "primary_observations": enum_src_meta.get("total_observations", 0),
      "primary_jurisdictions": enum_src_meta.get("total_jurisdictions", 0),
      "era_breakdown": jse_era_summary,
      "mass_conservation": krig_diag.get("subadmin_hgis_mass_conservation", {}),
    },
    "verified_pdfs": {
      "total_papers": wave2.get("total_papers", 0),
      "unique_sha256": wave2.get("unique_sha256", 0),
      "min_chapter_pdfs": wave2.get("min_chapter_pdfs", 0),
      "min_chapter_domains": wave2.get("min_chapter_domains", 0),
      "zenodo_count": wave2.get("zenodo_count", 0),
    },
  }
  root_out = os.path.join(SHARED, "jaguar_root_summary.json")
  with open(root_out, "w", encoding="utf-8") as fh:
    json.dump(root_summary, fh, indent=2, ensure_ascii=False)
  print(f"\n[DONE] Staged 14 chapter summary caches + jaguar_root_summary.json ({len(jaguar_root_trajectory)} gridded epochs).", flush=True)


if __name__ == "__main__":
  main()
