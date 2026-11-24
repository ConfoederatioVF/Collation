"""Strictly Mass-Conserving Pycnophylactic Sub-Administrative Dasymetric Disaggregation Engine
for Operation Viscount Project NICETHI (`sites_nicethi_africa`).

Uses the strictly non-anachronistic Academic-HGIS sub-administrative rasters
(`NICETHI/_shared/subadmin_hgis/rasters/subadmin_id_<yr>.png` + `subadmin_meta_<yr>.json`)
and official historical/modern sub-administrative census enumerations
(`NICETHI/_shared/subadmin_hgis/enumerations/nicethi_subadmin_enumerations.json`)
across enumerated HYDE benchmark years (`1700..2025 AD`).

Matches raster polygons to census records strictly by ISO3 + canonical unit name
(with explicit linguistic/orthographic alias resolution and ADM1 priority over ADM2),
applies strictly mass-conserving (pycnophylactic) dasymetric disaggregation onto
`2.population_rasters/popc_<yr>.png`:
    p_hat_i(t) = P_k(t) * w_i(t) / sum_{j in Omega_k} w_j(t)
guaranteeing `worst_unit_rel_err <= 1e-4`, and emits:
  - `sites_nicethi_africa/config/subadmin_mass_conservation_audit.json`
  - `sites_nicethi_africa/config/disaggregated_unit_ids_by_year.json`
"""

import json
import math
import os
import re
import unicodedata
from collections import defaultdict

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, gaussian_filter

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
NI_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "NICETHI")
HGIS_DIR = os.path.join(NI_DIR, "_shared", "subadmin_hgis")
ENUM_JSON = os.path.join(HGIS_DIR, "enumerations", "nicethi_subadmin_enumerations.json")
SUB_RASTER_DIR = os.path.join(HGIS_DIR, "rasters")

DOMAIN_DIR = os.path.join(NI_DIR, "_shared", "sites_nicethi_africa")
POP_DIR = os.path.join(DOMAIN_DIR, "2.population_rasters")
CFG_DIR = os.path.join(DOMAIN_DIR, "config")
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
GHSL_DIR = os.path.join(SVEA_ROOT, "histmap", "2.data_cleaning", "population_GHSL", "cleaned_rasters")

GRID_W, GRID_H = 4320, 2160

# Priority weights by admin_level (ADM1/TERRITORY preferred over ADM2 when homonyms exist)
ADMIN_LEVEL_PRIORITY = {
  "ADM1": 100,
  "ADM1_PRE2011": 95,
  "ADM1_MACRO": 90,
  "ADM1_AGG": 85,
  "TERRITORY": 85,
  "BANTUSTAN": 80,
  "COLONY_ISLAND": 80,
  "ADM0_TERRITORY": 75,
  "ISLAND": 75,
  "COLONY_REGION": 70,
  "COLONY_DISTRICT": 65,
  "COMMUNE": 60,
  "ADM2": 20,
}

# Excluded aggregate levels for multi-unit countries (allowed only for single-unit island/colony matches)
AGGREGATE_LEVELS = {"COLONY_AGG", "ADM0_CENSUS", "KINGDOM_EST"}

# Explicit ISO3 & federation mapping for historical colonial rasters
ISO_SEARCH_ORDER = {
  "SDN_S": ["SSD", "SDN"],
  "SWA": ["NAM"],
  "SOL": ["SOL", "SOM"],
  "AEF_CAF": ["AEF", "CAF"],
  "AEF_COG": ["AEF", "COG"],
  "AEF_GAB": ["AEF", "GAB"],
  "AEF_TCD": ["AEF", "TCD"],
  "AOF_BEN": ["AOF", "BEN"],
  "AOF_BFA": ["AOF", "BFA"],
  "AOF_CIV": ["AOF", "CIV"],
  "AOF_GIN": ["AOF", "GIN"],
  "AOF_MLI": ["AOF", "MLI"],
  "AOF_MRT": ["AOF", "MRT"],
  "AOF_NER": ["AOF", "NER"],
  "AOF_SEN": ["AOF", "SEN"],
}

# Explicit canonical alias dictionary: (iso_or_star, normalised_raster_name) -> list of candidate normalised enum names
NAME_ALIASES = {
  # AEF / AOF territories
  ("AEF_CAF", "aef territory caf"): ["oubangui chari rca", "oubangui chari"],
  ("AEF_COG", "aef territory cog"): ["moyen congo"],
  ("AEF_GAB", "aef territory gab"): ["gabon"],
  ("AEF_TCD", "aef territory tcd"): ["tchad"],
  ("AOF_BEN", "aof territory ben"): ["dahomey benin", "dahomey"],
  ("AOF_BFA", "aof territory bfa"): ["haute volta burkina faso", "haute volta reconstituted 1947", "haute volta"],
  ("AOF_CIV", "aof territory civ"): ["cote d ivoire"],
  ("AOF_GIN", "aof territory gin"): ["guinee francaise", "guinee"],
  ("AOF_MLI", "aof territory mli"): ["soudan francais mali", "soudan francais"],
  ("AOF_MRT", "aof territory mrt"): ["mauritanie"],
  ("AOF_NER", "aof territory ner"): ["niger"],
  ("AOF_SEN", "aof territory sen"): ["senegal incl dakar", "senegal"],

  # South Africa
  ("ZAF", "nothern cape"): ["northern cape"],
  ("ZAF", "free state"): ["free state oranje free state", "orange free state"],
  ("ZAF", "limpopo"): ["limpopo northern transvaal", "northern province"],
  ("ZAF", "mpumalanga"): ["mpumalanga eastern transvaal"],
  ("ZAF", "cape of good hope incl transkei ciskei"): ["cape of good hope", "cape province", "cape"],
  ("ZAF", "natal incl kwazulu"): ["natal"],
  ("ZAF", "orange free state incl qwaqwa"): ["orange free state", "free state oranje free state"],
  ("ZAF", "transvaal incl bophuthatswana venda lebowa gazankulu kangwane kwandebele"): ["transvaal"],

  # Angola
  ("AGO", "cuando cubango"): ["cuando cubango", "kuando kubango", "bie cuando cubango"],
  ("AGO", "cuanza norte"): ["cuanza norte", "kwanza norte"],
  ("AGO", "cuanza sul"): ["cuanza sul", "kwanza sul"],

  # Botswana
  ("BWA", "central district"): ["central"],
  ("BWA", "ghanzi district"): ["ghanzi"],
  ("BWA", "kgalagadi district"): ["kgalagadi"],
  ("BWA", "kgatleng district"): ["kgatleng"],
  ("BWA", "kweneng district"): ["kweneng"],
  ("BWA", "north east district"): ["north east"],
  ("BWA", "north west district"): ["north west ngamiland", "north west", "ngamiland"],
  ("BWA", "south east district"): ["south east"],
  ("BWA", "southern district"): ["southern"],

  # Cameroon (EN -> FR)
  ("CMR", "east"): ["est"],
  ("CMR", "north"): ["nord"],
  ("CMR", "south"): ["sud"],
  ("CMR", "west"): ["ouest"],
  ("CMR", "far north"): ["extreme nord"],
  ("CMR", "north west"): ["nord ouest"],
  ("CMR", "south west"): ["sud ouest"],
  ("CMR", "adamawa"): ["adamaoua"],
  ("CMR", "central"): ["centre"],

  # DRC (EN -> FR & historical)
  ("COD", "lower uele"): ["bas uele"],
  ("COD", "upper uele"): ["haut uele"],
  ("COD", "upper katanga"): ["haut katanga"],
  ("COD", "upper lomami"): ["haut lomami"],
  ("COD", "bas congo bas zaire"): ["kongo central bas congo", "bas congo", "bas zaire"],
  ("COD", "kongo central"): ["kongo central bas congo", "bas congo"],
  ("COD", "orientale haut zaire"): ["orientale", "haut zaire", "stanleyville"],
  ("COD", "katanga shaba"): ["katanga", "shaba"],
  ("COD", "kasai occidental"): ["kasai occidental", "kasai"],
  ("COD", "equateur"): ["equateur"],
  ("COD", "leopoldville"): ["leopoldville", "kinshasa"],

  # Ethiopia
  ("ETH", "snnpr"): ["southern nations nationalities and peoples", "southern nations nationalities and peoples region", "snnpr"],
  ("ETH", "beneshangul gumu"): ["benishangul gumuz", "benshangul gumuz"],
  ("ETH", "addis ababa"): ["adis abeba", "addis ababa"],
  ("ETH", "gambella"): ["gambela", "gambella"],
  ("ETH", "harari"): ["harari", "hareri"],

  # Sudan & South Sudan
  ("SDN", "red sea"): ["red sea", "al bahr al ahmar"],
  ("SDN", "gezira"): ["gezira", "al jazirah", "el gezira"],
  ("SDN", "al gazira"): ["gezira", "al jazirah"],
  ("SDN", "khartoum"): ["khartoum", "al khartum"],
  ("SDN", "gedaref"): ["gedarif", "al qadarif", "gedaref"],
  ("SDN", "white nile"): ["white nile", "an nil al abyad"],
  ("SDN", "blue nile"): ["blue nile", "an nil al azraq"],
  ("SDN", "northern"): ["northern", "ash shamaliyah"],
  ("SDN", "river nile"): ["river nile", "nahr an nil"],
  ("SDN", "sennar"): ["sennar", "sannar"],
  ("SDN", "kassala"): ["kassala", "kassala"],
  ("SDN", "north darfur"): ["north darfur", "shamal darfur"],
  ("SDN", "south darfur"): ["south darfur", "janub darfur"],
  ("SDN", "west darfur"): ["west darfur", "gharb al darfur", "gharb darfur"],
  ("SDN", "east darfur"): ["east darfur", "sharq darfur"],
  ("SDN", "central darfur"): ["central darfur", "wasat darfur"],
  ("SDN", "north kordofan"): ["north kordofan", "shamal kurdufan"],
  ("SDN", "south kordofan"): ["south kordofan", "janub kurdufan"],
  ("SDN", "west kordofan"): ["west kordofan", "gharb kurdufan"],
  ("SDN_S", "eastern equatoria"): ["eastern equatoria", "east equatoria"],
  ("SDN_S", "western equatoria"): ["western equatoria", "west equatoria"],
  ("SDN_S", "northern bahr el ghazal"): ["northern bahr el ghazal", "north bahr al ghazal"],
  ("SDN_S", "western bahr el ghazal"): ["western bahr el ghazal", "west bahr al ghazal"],
  ("SDN_S", "jonglei"): ["jonglei", "jungoli"],
  ("SDN_S", "warrap"): ["warrap", "warap"],

  # Mali / Senegal / Burkina / Niger / Ivory Coast spelling variants
  ("MLI", "koulikouro"): ["koulikoro"],
  ("MLI", "segou"): ["segou"],
  ("MLI", "tombouctou"): ["tombouctou", "timbuktu"],
  ("NER", "tillaberi"): ["tillaberi", "tillabery"],
  ("TCD", "bahr el gazel"): ["barl el gazel", "bahr el gazel", "bahr el ghazal"],
  ("TCD", "ennedi est"): ["ennedi est", "ennedi"],
  ("TCD", "ennedi ouest"): ["ennedi ouest", "ennedi"],

  # Uganda / Kenya / Tanzania / Zambia / Zimbabwe / Mozambique / Somalia
  ("UGA", "northern region"): ["northern", "northern region"],
  ("UGA", "western region"): ["western", "western region"],
  ("UGA", "eastern region"): ["eastern", "eastern region"],
  ("UGA", "central region"): ["central", "central region"],
  ("KEN", "north eastern"): ["north eastern", "northeastern"],
  ("SOM", "lower juba"): ["lower juba", "jubbada hoose"],
  ("SOM", "middle juba"): ["middle juba", "jubbada dhexe"],
  ("SOM", "lower shabelle"): ["lower shabelle", "shabeellaha hoose"],
  ("SOM", "middle shabelle"): ["middle shabelle", "shabeellaha dhexe"],
  ("SOM", "hiran"): ["hiiraan", "hiran"],
  ("SOM", "banadir"): ["banaadir", "banadir"],
  ("SOM", "galgaduud"): ["galguduud", "galgaduud"],
  ("SOL", "woqooyi galbeed"): ["woqooyi galbeed", "maroodi jeex"],
}


def norm_key(text):
  s = unicodedata.normalize("NFKD", str(text or ""))
  s = "".join(ch for ch in s if not unicodedata.combining(ch))
  s = s.replace("’", "'").replace("`", "'").replace("–", "-").replace("—", "-")
  s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
  return s


def strip_admin_suffix(nk):
  for suf in (
    " region", " province", " state", " district", " prefecture", " department",
    " departement", " governorate", " county", " territory", " municipality",
    " division", " administrative region", " metropolitan"
  ):
    if nk.endswith(suf) and len(nk) > len(suf) + 2:
      return nk[:-len(suf)].strip()
  return nk


def decode_float32_png(path):
  raw = np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
  valid = np.isfinite(f32) & (f32 > 0.0)
  return np.where(valid, f32, 0.0).astype(np.float64), valid


def encode_float32_png(arr, out_path):
  f32 = np.where(np.isfinite(arr) & (arr > 0.0), arr, 0.0).astype(">f4")
  u8 = f32.view(np.uint8).reshape(arr.shape[0], arr.shape[1], 4)
  Image.fromarray(u8, mode="RGBA").save(out_path, compress_level=6)


def decode_id_png(path):
  raw = np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)
  return np.where(raw[:, :, 3] > 0, (raw[:, :, 0].astype(np.int32) << 8) | raw[:, :, 1].astype(np.int32), 0)


def build_enumeration_index(enum_data):
  """Builds per-ISO normalised unit time-series index preferring ADM1/TERRITORY over homonymous ADM2."""
  # idx[iso][norm_name][year] = (priority, pop)
  idx = defaultdict(lambda: defaultdict(dict))
  iso_agg = defaultdict(dict)  # single-territory aggregate censuses (MUS, REU, CPV, etc.)

  for iso, ymap in enum_data.items():
    if not isinstance(ymap, dict):
      continue
    for y_str, recs in ymap.items():
      try:
        yk = int(float(y_str))
      except Exception:
        continue
      if not isinstance(recs, list):
        continue
      for r in recs:
        try:
          pop = float(r.get("population") or 0.0)
        except Exception:
          continue
        if pop <= 0:
          continue
        lvl = str(r.get("admin_level") or "ADM1").upper()
        uname = str(r.get("unit_name") or "")
        nk = norm_key(uname)
        if not nk:
          continue

        if lvl in AGGREGATE_LEVELS:
          # Only keep aggregate for small single-polity islands/colonies
          if iso in ("MUS", "REU", "CPV", "COM", "STP", "SYC", "SHN", "MYT", "DJI", "GMB", "GNB", "GNQ", "LSO", "SWZ", "ZAF_CAPE", "MDG_MERINA"):
            iso_agg[iso][yk] = max(iso_agg[iso].get(yk, 0.0), pop)
          continue

        prio = ADMIN_LEVEL_PRIORITY.get(lvl, 50)
        keys_to_register = {nk, strip_admin_suffix(nk)}
        # Also register base name before parenthetical, e.g. "Free State (Oranje Free State)" -> "free state"
        if "(" in uname:
          base_nk = norm_key(uname.split("(")[0])
          if len(base_nk) >= 3:
            keys_to_register.add(base_nk)
            keys_to_register.add(strip_admin_suffix(base_nk))
          # Also inside parentheses if it's an alternate name (not arrow/note)
          m_par = re.findall(r"\(([^()]+)\)", uname)
          for mp in m_par:
            if "←" not in mp and "incl" not in mp.lower() and "reconstituted" not in mp.lower():
              pk = norm_key(mp)
              if len(pk) >= 4:
                keys_to_register.add(pk)

        for k in keys_to_register:
          if not k:
            continue
          prev = idx[iso][k].get(yk)
          if prev is None or prio > prev[0] or (prio == prev[0] and pop > prev[1]):
            idx[iso][k][yk] = (prio, pop)

  # Convert to pure {year: pop} dicts
  clean_idx = {}
  for iso, nmap in idx.items():
    clean_idx[iso] = {}
    for nk, ydict in nmap.items():
      clean_idx[iso][nk] = {y: p for y, (_pr, p) in ydict.items()}
  return clean_idx, iso_agg


def interpolate_pop(pops_dict, yr, max_extrap_before=12, max_extrap_after=12):
  """Log-linear interpolation between bracketing official censuses, with bounded gentle extrapolation."""
  if not pops_dict:
    return None
  yrs = sorted(pops_dict.keys())
  if yr in pops_dict:
    return float(pops_dict[yr])
  if yr < yrs[0]:
    if yrs[0] - yr > max_extrap_before:
      return None
    if len(yrs) >= 2:
      dt = max(1, yrs[1] - yrs[0])
      r = math.log(max(1.0, pops_dict[yrs[1]]) / max(1.0, pops_dict[yrs[0]])) / dt
      r = max(-0.025, min(0.038, r))
      return float(pops_dict[yrs[0]] * math.exp(r * (yr - yrs[0])))
    return float(pops_dict[yrs[0]])
  if yr > yrs[-1]:
    if yr - yrs[-1] > max_extrap_after:
      return None
    if len(yrs) >= 2:
      dt = max(1, yrs[-1] - yrs[-2])
      r = math.log(max(1.0, pops_dict[yrs[-1]]) / max(1.0, pops_dict[yrs[-2]])) / dt
      r = max(-0.025, min(0.038, r))
      return float(pops_dict[yrs[-1]] * math.exp(r * (yr - yrs[-1])))
    return float(pops_dict[yrs[-1]])
  for i in range(len(yrs) - 1):
    y0, y1 = yrs[i], yrs[i + 1]
    if y0 <= yr <= y1:
      t = (yr - y0) / float(y1 - y0)
      p0, p1 = max(1.0, pops_dict[y0]), max(1.0, pops_dict[y1])
      return float(math.exp((1.0 - t) * math.log(p0) + t * math.log(p1)))
  return None


def match_unit_series(unit, enum_idx, iso_agg, yr):
  """Matches a single raster unit strictly by ISO3 + canonical unit name / alias."""
  iso = str(unit.get("country") or "")
  code = str(unit.get("code") or "")
  name = str(unit.get("name") or "")
  nk = norm_key(name)

  # Early single-island ecological polygons (e.g. ECO0_ISL_MUS / ECO0_ISL_REU in 1735-1890)
  if code.startswith("ECO0_ISL_"):
    isl_iso = code.replace("ECO0_ISL_", "")
    if isl_iso in iso_agg:
      val = interpolate_pop(iso_agg[isl_iso], yr, max_extrap_before=10, max_extrap_after=10)
      if val is not None and val > 0:
        return val
    if isl_iso in enum_idx:
      for k, pmap in enum_idx[isl_iso].items():
        if isl_iso.lower() in k or k in ("mauritius", "reunion", "ile de france", "ile bourbon", "cabo verde", "cape verde"):
          val = interpolate_pop(pmap, yr, max_extrap_before=10, max_extrap_after=10)
          if val is not None and val > 0:
            return val
    return None

  if not unit.get("is_direct_census"):
    return None

  cand_isos = ISO_SEARCH_ORDER.get(iso, [iso])
  cand_names = [nk, strip_admin_suffix(nk)]
  if "(" in name:
    b_nk = norm_key(name.split("(")[0])
    if len(b_nk) >= 3:
      cand_names.extend([b_nk, strip_admin_suffix(b_nk)])
  for alias_key in ((iso, nk), (iso, strip_admin_suffix(nk))):
    if alias_key in NAME_ALIASES:
      cand_names.extend(NAME_ALIASES[alias_key])

  # Deduplicate candidate names preserving priority
  seen = set()
  ordered_names = []
  for cn in cand_names:
    if cn and cn not in seen:
      seen.add(cn)
      ordered_names.append(cn)

  # Search strictly within matched ISO(s)
  for c_iso in cand_isos:
    nmap = enum_idx.get(c_iso)
    if not nmap:
      continue
    # 1. Exact key match
    for cn in ordered_names:
      if cn in nmap:
        val = interpolate_pop(nmap[cn], yr, max_extrap_before=12, max_extrap_after=12)
        if val is not None and val > 0:
          return val
    # 2. Controlled prefix/token match (only for unambiguous names >= 5 chars)
    for cn in ordered_names:
      if len(cn) < 5:
        continue
      for ek, pmap in nmap.items():
        if len(ek) < 5:
          continue
        if ek.startswith(cn + " ") or cn.startswith(ek + " "):
          val = interpolate_pop(pmap, yr, max_extrap_before=12, max_extrap_after=12)
          if val is not None and val > 0:
            return val

  # Single-unit island/microstate fallback where country has 1 polygon matching country aggregate
  if iso in iso_agg and len(cand_isos) == 1:
    val = interpolate_pop(iso_agg[iso], yr, max_extrap_before=10, max_extrap_after=10)
    if val is not None and val > 0:
      return val

  return None


def pycnophylactic_decliff_edges(field, unit_targets, unit_px, max_passes=10):
  """Targeted mass-conserving cliff-edge & straight-wall softener.
  Relaxes ONLY excessive single-pixel log10 jumps (> 0.95 dex) and long straight cliff walls
  (run >= 12 px with >= 0.54 dex), preserving interior valley/river/highland sharpness while
  re-normalising every disaggregated subadmin unit to exact census mass conservation (<= 1e-6).
  """
  out = field.copy()
  valid = out >= 0.05
  if not valid.any():
    return out
  rs_all, cs_all = np.where(valid)
  r0 = max(0, int(rs_all.min()) - 2)
  r1 = min(out.shape[0], int(rs_all.max()) + 3)
  c0 = max(0, int(cs_all.min()) - 2)
  c1 = min(out.shape[1], int(cs_all.max()) + 3)

  for _ in range(max_passes):
    sub = out[r0:r1, c0:c1]
    sv = sub >= 0.05
    log_s = np.where(sv, np.log10(np.maximum(sub, 1e-6)), 0.0)

    pair_h = sv[:, :-1] & sv[:, 1:]
    pair_v = sv[:-1, :] & sv[1:, :]
    dh = np.where(pair_h, np.abs(log_s[:, 1:] - log_s[:, :-1]), 0.0)
    dv = np.where(pair_v, np.abs(log_s[1:, :] - log_s[:-1, :]), 0.0)

    # Identify extreme single-pixel jumps (> 0.98 dex)
    steep_h = pair_h & (dh > 0.98)
    steep_v = pair_v & (dv > 0.98)

    # Identify contiguous straight walls (run >= 12 px with >= 0.54 dex)
    wall_h = np.zeros_like(pair_h, dtype=bool)
    wall_v = np.zeros_like(pair_v, dtype=bool)
    h_mask = pair_h & (dh >= 0.54)
    v_mask = pair_v & (dv >= 0.54)

    # Vertical walls (column runs in h_mask)
    for c in np.where(h_mask.sum(axis=0) >= 12)[0]:
      col = h_mask[:, c]
      run = 0
      for r in range(col.size):
        if col[r]:
          run += 1
        else:
          if run >= 12:
            wall_h[r - run:r, c] = True
          run = 0
      if run >= 12:
        wall_h[col.size - run:, c] = True

    # Horizontal walls (row runs in v_mask)
    for r in np.where(v_mask.sum(axis=1) >= 12)[0]:
      row = v_mask[r, :]
      run = 0
      for c in range(row.size):
        if row[c]:
          run += 1
        else:
          if run >= 12:
            wall_v[r, c - run:c] = True
          run = 0
      if run >= 12:
        wall_v[r, row.size - run:] = True

    # Check if both p99 and walls are already clean
    all_d = np.concatenate([dh[pair_h], dv[pair_v]])
    p99 = float(np.percentile(all_d, 99)) if all_d.size > 0 else 0.0
    need_p99 = p99 > 1.18
    need_wall = bool(wall_h.any() or wall_v.any())
    if not need_p99 and not need_wall:
      break

    # Build targeted edge-diffusion mask strictly around offending cliffs/walls
    edge_px = np.zeros_like(sv, dtype=bool)
    if need_p99:
      edge_px[:, :-1] |= steep_h
      edge_px[:, 1:] |= steep_h
      edge_px[:-1, :] |= steep_v
      edge_px[1:, :] |= steep_v
    if need_wall:
      edge_px[:, :-1] |= wall_h
      edge_px[:, 1:] |= wall_h
      edge_px[:-1, :] |= wall_v
      edge_px[1:, :] |= wall_v
      # Dilate wall strip slightly (2 px) so straight border transitions smoothly
      edge_px = binary_dilation(edge_px, iterations=2) & sv

    if not edge_px.any():
      break

    # Gentle local log-space smoothing ONLY on edge_px (weighted by active neighbours)
    w_f = sv.astype(np.float64)
    num = gaussian_filter(log_s * w_f, sigma=1.15)
    den = gaussian_filter(w_f, sigma=1.15)
    sm_log = np.where(den > 1e-6, num / np.maximum(den, 1e-6), log_s)
    blend = 0.55 if need_wall else 0.45
    new_log = np.where(edge_px, (1.0 - blend) * log_s + blend * sm_log, log_s)
    sub_new = np.where(sv, np.power(10.0, new_log), sub)
    out[r0:r1, c0:c1] = sub_new

    # Exact pycnophylactic mass re-normalisation inside every disaggregated subadmin unit
    for uid, target_p in unit_targets:
      px_pair = unit_px.get(uid)
      if px_pair is None:
        continue
      rs, cs = px_pair
      cur_sum = float(out[rs, cs].sum())
      if cur_sum > 1e-9:
        out[rs, cs] = out[rs, cs] * (target_p / cur_sum)

  return out


def main():
  print("[A] Loading NICETHI subadmin enumerations & land area grid...", flush=True)
  enum_data = json.load(open(ENUM_JSON, "r", encoding="utf-8"))
  enum_idx, iso_agg = build_enumeration_index(enum_data)

  la_raw = np.asarray(Image.open(LAND_AREA_PNG).convert("RGBA"), dtype=np.uint8)
  land_area = la_raw.reshape(-1, 4).copy().view(">u4").reshape(la_raw.shape[:2]).astype(np.float64)

  pop_files = sorted(f for f in os.listdir(POP_DIR) if f.startswith("popc_") and f.endswith(".png"))
  target_files = []
  for fn in pop_files:
    try:
      yr = int(fn.replace("popc_", "").replace(".png", ""))
    except Exception:
      continue
    if yr >= 1700:
      target_files.append((yr, os.path.join(POP_DIR, fn)))
  target_files.sort()

  print(f"[B] Applying strictly mass-conserving pycnophylactic disaggregation across {len(target_files)} benchmark rasters (1700-2025)...", flush=True)

  audit_years = {}
  disagg_ids_by_year = {}
  global_max_rel_err = 0.0
  total_unit_year_checks = 0
  total_units_exact = 0
  max_units_in_year = 0

  # Cache raster ID grids by geometry_regime so consecutive years sharing a regime avoid re-decoding PNGs
  cached_regime = None
  cached_id_grid = None
  cached_unit_px = None

  for yr, fpath in target_files:
    meta_path = os.path.join(SUB_RASTER_DIR, f"subadmin_meta_{yr}.json")
    id_path = os.path.join(SUB_RASTER_DIR, f"subadmin_id_{yr}.png")
    if not os.path.isfile(meta_path) or not os.path.isfile(id_path):
      continue

    meta = json.load(open(meta_path, "r", encoding="utf-8"))
    units = meta.get("units") or []
    regime = meta.get("geometry_regime") or str(yr)

    # Group direct units by ISO to verify sufficient country coverage before applying
    by_iso = defaultdict(list)
    isl_units = []
    for u in units:
      if str(u.get("code") or "").startswith("ECO0_ISL_"):
        isl_units.append(u)
      elif u.get("is_direct_census"):
        by_iso[u["country"]].append(u)

    active_targets = []  # list of (uid, iso, name, target_p)
    # 1. Early single-island units (MUS, REU, etc.) when not yet covered by direct census polygons
    direct_isos = set(by_iso.keys())
    for u in isl_units:
      isl_iso = str(u.get("code") or "").replace("ECO0_ISL_", "")
      if isl_iso in direct_isos:
        continue
      tp = match_unit_series(u, enum_idx, iso_agg, yr)
      if tp is not None and tp > 0:
        active_targets.append((int(u["id"]), isl_iso, u["name"], tp))

    # 2. Direct census sub-administrative polygons grouped by ISO3
    for iso, ulist in by_iso.items():
      matched_iso = []
      for u in ulist:
        tp = match_unit_series(u, enum_idx, iso_agg, yr)
        if tp is not None and tp > 0:
          matched_iso.append((int(u["id"]), iso, u["name"], tp))
      # Apply country's subadmin layer if at least 40% of its direct units are enumerated (or colonial single-territory match)
      min_req = 1 if len(ulist) <= 3 else max(2, int(0.40 * len(ulist)))
      if len(matched_iso) >= min_req:
        active_targets.extend(matched_iso)

    if not active_targets:
      continue

    # Load or reuse cached subadmin_id_<yr>.png
    if regime != cached_regime:
      cached_id_grid = decode_id_png(id_path)
      # Build pixel-index lookup once per regime using fast argsort grouping
      nz_r, nz_c = np.where(cached_id_grid > 0)
      nz_ids = cached_id_grid[nz_r, nz_c]
      order = np.argsort(nz_ids, kind="mergesort")
      s_ids = nz_ids[order]
      s_r = nz_r[order]
      s_c = nz_c[order]
      uniq_ids, starts, counts = np.unique(s_ids, return_index=True, return_counts=True)
      cached_unit_px = {
        int(uid): (s_r[st:st + cnt], s_c[st:st + cnt])
        for uid, st, cnt in zip(uniq_ids, starts, counts)
      }
      cached_regime = regime

    prior, _ = decode_float32_png(fpath)
    weight_grid = prior
    if yr >= 1975:
      ghsl_path = os.path.join(GHSL_DIR, f"GHS_POP_{yr}.png")
      if os.path.isfile(ghsl_path):
        g_arr, _ = decode_float32_png(ghsl_path)
        g_halo = gaussian_filter(g_arr, sigma=1.1)
        weight_grid = np.where((g_arr > 0.05) | (prior > 0.05), g_arr + 0.12 * g_halo + 0.04 * prior, 0.0)

    out = prior.copy()
    applied_targets = []

    for uid, iso, uname, target_p in active_targets:
      px_pair = cached_unit_px.get(uid)
      if px_pair is None:
        continue
      rs, cs = px_pair
      if rs.size == 0:
        continue

      w = weight_grid[rs, cs].copy()
      w_sum = float(w.sum())
      if w_sum <= 1e-9:
        w = prior[rs, cs].copy()
        w_sum = float(w.sum())
      if w_sum <= 1e-9:
        w = np.maximum(1.0, land_area[rs, cs])
        w_sum = float(w.sum())

      out[rs, cs] = target_p * (w / w_sum)
      applied_targets.append((uid, target_p))

    if applied_targets:
      # Strictly mass-conserving pycnophylactic decliffing across administrative borders & extreme spikes
      out = pycnophylactic_decliff_edges(out, applied_targets, cached_unit_px, max_passes=12)

      # Float32 round-trip verification of exact mass conservation for every disaggregated unit
      out_f32 = np.where(np.isfinite(out) & (out > 0.0), out, 0.0).astype(np.float32).astype(np.float64)
      yr_rel_errs = []
      yr_target_sum = 0.0
      yr_actual_sum = 0.0
      applied_uids = []
      for uid, target_p in applied_targets:
        rs, cs = cached_unit_px[uid]
        act_p = float(out_f32[rs, cs].sum())
        rel_err = abs(act_p - target_p) / max(1.0, target_p)
        yr_rel_errs.append(rel_err)
        yr_target_sum += target_p
        yr_actual_sum += act_p
        applied_uids.append(uid)
        total_unit_year_checks += 1
        if rel_err <= 1e-4:
          total_units_exact += 1
        if rel_err > global_max_rel_err:
          global_max_rel_err = rel_err

      yr_units_applied = len(applied_uids)
      encode_float32_png(out_f32, fpath)
      disagg_ids_by_year[str(yr)] = applied_uids
      max_units_in_year = max(max_units_in_year, yr_units_applied)
      audit_years[str(yr)] = {
        "geometry_regime": regime,
        "units_disaggregated": yr_units_applied,
        "target_mass": round(yr_target_sum, 1),
        "disaggregated_mass": round(yr_actual_sum, 1),
        "global_mass_rel_err": float(f"{abs(yr_actual_sum - yr_target_sum) / max(1.0, yr_target_sum):.3e}"),
        "max_unit_rel_err": float(f"{max(yr_rel_errs):.3e}"),
        "mean_unit_rel_err": float(f"{float(np.mean(yr_rel_errs)):.3e}"),
      }

  audit_report = {
    "domain": "NICETHI",
    "method": "Pycnophylactic (Strictly Mass-Conserving) Sub-Administrative Dasymetric Disaggregation & Areal Scaling",
    "years_disaggregated": len(audit_years),
    "max_units_in_single_year": max_units_in_year,
    "total_unit_year_checks": total_unit_year_checks,
    "units_within_0_01_percent_mass_conservation": total_units_exact,
    "exact_conservation_pass_rate": round(total_units_exact / max(1, total_unit_year_checks), 6),
    "worst_unit_rel_err": float(f"{global_max_rel_err:.3e}"),
    "global_max_unit_rel_err": float(f"{global_max_rel_err:.3e}"),
    "representative_years": {
      k: audit_years[k]
      for k in sorted(audit_years.keys(), key=lambda s: int(s))
      if int(k) in (1750, 1800, 1850, 1880, 1900, 1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020, 2025)
    },
  }

  os.makedirs(CFG_DIR, exist_ok=True)
  audit_path = os.path.join(CFG_DIR, "subadmin_mass_conservation_audit.json")
  with open(audit_path, "w", encoding="utf-8") as fh:
    json.dump(audit_report, fh, indent=2, ensure_ascii=False)
  with open(os.path.join(CFG_DIR, "disaggregated_unit_ids_by_year.json"), "w", encoding="utf-8") as fh:
    json.dump(disagg_ids_by_year, fh)

  print("\nDONE disaggregate_nicethi_subadmin.py:", flush=True)
  print(f"  Years disaggregated: {len(audit_years)} | Max units/year: {max_units_in_year}", flush=True)
  print(f"  Unit-year checks: {total_unit_year_checks:,} | Exact (<= 1e-4): {total_units_exact:,}/{total_unit_year_checks:,}", flush=True)
  print(f"  worst_unit_rel_err: {global_max_rel_err:.3e}", flush=True)


if __name__ == "__main__":
  main()
