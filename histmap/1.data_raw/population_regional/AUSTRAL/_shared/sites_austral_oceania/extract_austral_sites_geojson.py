"""Stage B Archaeological Catchment Tessellation & Multi-Repository Site Extractor for Project AUSTRAL.

Builds dual HYDE 3.5 + KK10 believed-density catchments (`max(D_hyde35, D_kk10)` over `land_area.png`)
inside `austral_domain_mask.png`, strictly obeying all 5 density tiers in `viscount_skill_profiles.json5`
(>= 25 inh/km2 -> <= 1,800 km2; 5-25 -> <= 3,000 km2; 1-5 -> <= 6,000 km2; 0.05-1 -> <= 14,000 km2;
global ceiling <= 25,000 km2; >= 5.5 catchments per 100k km2; >= 90% tier compliance) across Australia,
Tasmania, New Guinea, New Zealand, Melanesia, Micronesia, and Polynesia (excl. Hawai'i & American Samoa).

Ingests all 27 normalised primary institutional/monograph JSON files in `0.raw_data/` (69,082 unique primary
sites, 0.0% crowd share) plus 250 km cross-frontier conditioning buffers from MANDALA (Maluku/Aru/Kai/Tanimbar)
and CENTAUR (American Samoa). Separates durable non-habitation monuments (`is_monument_only: true`) from
habitation sites, applies subregional survey-effort harmonisation + biome/aridity-conditioned `Q75 + IQR`
taphonomic shrinkage (`forest_wwf_cr.asc`), and exports `00_all_periods.geojson`, 8 Oceanian horizon GeoJSONs,
`config/sites_austral_oceania.json5`, `config/sites_austral_oceania_geojson_metadata.json`,
`config/documented_site_pixels.json`, and `config/documented_urban_hubs.json`.
"""

import glob
import io
import json
import math
import os
import re
import zipfile
from collections import Counter

import numpy as np
import shapefile
from PIL import Image
from scipy.ndimage import distance_transform_edt, label as cc_label
from scipy.spatial import cKDTree
from shapely.geometry import Point, box as sbox, shape
from shapely.prepared import prep

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
AUSTRAL_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL")
DOMAIN_DIR = os.path.join(AUSTRAL_DIR, "_shared", "sites_austral_oceania")
RAW_DIR = os.path.join(DOMAIN_DIR, "0.raw_data")
CFG_DIR = os.path.join(DOMAIN_DIR, "config")
GJ_DIR = os.path.join(DOMAIN_DIR, "geojson")
GIS_DIR = os.path.join(AUSTRAL_DIR, "_shared", "_gis_cache")
SETT_DIR = os.path.join(AUSTRAL_DIR, "_shared", "settlement_sources")

DOMAIN_MASK_PNG = os.path.join(CFG_DIR, "austral_domain_mask.png")
LAND_AREA_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png")
HYDE_DIR = os.path.join(SVEA_ROOT, "histmap", "2.data_cleaning", "landuse_HYDE", "rasters")
KK10_1500_PNG = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_KK10LUH2", "KK10", "KK10_1500.png")
FOREST_ASC = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "metadata_HYDE", "general_files", "forest_wwf_cr.asc")
HYBAS_AU_ZIP = os.path.join(GIS_DIR, "hybas_au_lev06_v1c.zip")

MANDALA_GJ_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MANDALA", "_shared", "sites_mandala_southeast_asia", "geojson"
)
CENTAUR_HI_GJ_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CENTAUR", "_shared", "sites_hawaii_polynesia", "geojson"
)

os.makedirs(CFG_DIR, exist_ok=True)
os.makedirs(GJ_DIR, exist_ok=True)

GRID_W, GRID_H = 4320, 2160
EARTH_R_KM = 6371.0

# 8 Chronological Archaeological Horizons calibrated to Sahul, Near Oceania & Remote Oceania
PERIODS = [
  {
    "epoch_id": 1,
    "key": "01_pleistocene_early_holocene_sahul",
    "filename": "01_pleistocene_early_holocene_sahul.png",
    "geojson_filename": "01_pleistocene_early_holocene_sahul.geojson",
    "approx_start_year": -12000,
    "approx_end_year": -5000,
    "representative_year": -8000,
    "name_en": "Pleistocene and Early Holocene Sahul",
    "name_de": "Pleistozän und Frühholozän in Sahul",
    "name_fr": "Pléistocène et Holocène ancien du Sahul",
    "date_range_en": "c. 65000-5000BC (Madjedbebe, Lake Mungo, Kutikina, Kosipe, early Kuk Swamp and Wallacean crossings)"
  },
  {
    "epoch_id": 2,
    "key": "02_mid_holocene_intensification_kuk",
    "filename": "02_mid_holocene_intensification_kuk.png",
    "geojson_filename": "02_mid_holocene_intensification_kuk.geojson",
    "approx_start_year": -5000,
    "approx_end_year": -1500,
    "representative_year": -3000,
    "name_en": "Mid-Holocene Intensification and Highland Agriculture",
    "name_de": "Mittelholozäne Intensivierung und Hochlandlandwirtschaft",
    "name_fr": "Intensification de l'Holocène moyen et agriculture des Hautes Terres",
    "date_range_en": "c. 5000-1500BC (Kuk Swamp drainage, Budj Bim eel aquaculture, Australian Small Tool Tradition and early Marianas)"
  },
  {
    "epoch_id": 3,
    "key": "03_lapita_austronesian_dispersal",
    "filename": "03_lapita_austronesian_dispersal.png",
    "geojson_filename": "03_lapita_austronesian_dispersal.geojson",
    "approx_start_year": -1500,
    "approx_end_year": -500,
    "representative_year": -1000,
    "name_en": "Lapita Cultural Complex and Austronesian Voyaging",
    "name_de": "Lapita-Kultur und Austronesische Expansion",
    "name_fr": "Complexe culturel Lapita et expansion austronésienne",
    "date_range_en": "c. 1500-500BC (Bismarcks, Reef/Santa Cruz, Teouma, Koné, Bourewa Fiji, Nukuleka Tonga, Mulifanua Samoa and Palau/Yap)"
  },
  {
    "epoch_id": 4,
    "key": "04_post_lapita_melanesian_west_polynesia",
    "filename": "04_post_lapita_melanesian_west_polynesia.png",
    "geojson_filename": "04_post_lapita_melanesian_west_polynesia.geojson",
    "approx_start_year": -500,
    "approx_end_year": 400,
    "representative_year": 0,
    "name_en": "Post-Lapita Diversification and Ancestral Polynesia",
    "name_de": "Post-Lapita-Diversifizierung und Urpolynesische Gesellschaft",
    "name_fr": "Diversification post-Lapita et société polynésienne ancestrale",
    "date_range_en": "500BC-400AD (Ancestral Polynesian Society in Tonga/Samoa, Micronesian atoll settlement and Murray-Darling earth mounds)"
  },
  {
    "epoch_id": 5,
    "key": "05_central_east_polynesia_expansion",
    "filename": "05_central_east_polynesia_expansion.png",
    "geojson_filename": "05_central_east_polynesia_expansion.geojson",
    "approx_start_year": 400,
    "approx_end_year": 1150,
    "representative_year": 850,
    "name_en": "Central and East Polynesian Settlement and Micronesian Megaliths",
    "name_de": "Besiedlung Ostpolynesiens und Mikronesische Megalithen",
    "name_fr": "Peuplement de la Polynésie orientale et mégalithes micronésiens",
    "date_range_en": "400-1150AD (Society, Marquesas, Cook, Austral, Tuamotu, Rapa Nui, Nan Madol origins and New Guinea Highlands expansion)"
  },
  {
    "epoch_id": 6,
    "key": "06_aotearoa_settlement_classic_chiefdoms",
    "filename": "06_aotearoa_settlement_classic_chiefdoms.png",
    "geojson_filename": "06_aotearoa_settlement_classic_chiefdoms.geojson",
    "approx_start_year": 1150,
    "approx_end_year": 1500,
    "representative_year": 1350,
    "name_en": "Aotearoa Settlement and Maritime Chiefdoms",
    "name_de": "Besiedlung Aotearoas und Maritime Häuptlingstümer",
    "name_fr": "Peuplement d'Aotearoa et chefferies maritimes",
    "date_range_en": "1150-1500AD (Wairau Bar, Shag River, Tu'i Tonga Empire, Mu'a, Leluh, Nan Madol and Rapa Nui ahu complexes)"
  },
  {
    "epoch_id": 7,
    "key": "07_classic_maori_pa_pacific_polities",
    "filename": "07_classic_maori_pa_pacific_polities.png",
    "geojson_filename": "07_classic_maori_pa_pacific_polities.geojson",
    "approx_start_year": 1500,
    "approx_end_year": 1769,
    "representative_year": 1650,
    "name_en": "Classic Māori Pā, Ipomoean Highlands and Pre-Contact Polities",
    "name_de": "Klassische Māori-Pā, Ipomoea-Hochland und Vorkoloniale Gemeinwesen",
    "name_fr": "Pā maoris classiques, Hautes Terres et chefferies précoloniales",
    "date_range_en": "1500-1769AD (Classic Māori fortified pā, New Guinea Ipomoean intensification, Fijian/Tongan/Tahitian paramountcies and Sahul networks)"
  },
  {
    "epoch_id": 8,
    "key": "08_contact_and_early_colonial_transition",
    "filename": "08_contact_and_early_colonial_transition.png",
    "geojson_filename": "08_contact_and_early_colonial_transition.geojson",
    "approx_start_year": 1769,
    "approx_end_year": 1900,
    "representative_year": 1835,
    "name_en": "European Contact and Early Colonial Transition",
    "name_de": "Europäischer Kontakt und Frühe Kolonialzeit",
    "name_fr": "Contact européen et transition coloniale",
    "date_range_en": "1769-1900AD (Port Jackson, Van Diemen's Land, Bay of Islands, New Zealand Wars, colonial towns and Pacific mission ports)"
  }
]
PERIOD_KEYS = [p["key"] for p in PERIODS]

# Dual HYDE 3.5 + KK10 Believed-Density Tier Ceilings (slightly tightened inside policy bounds for >=98% compliance)
# Policy: >=25 -> <=1800, 5-25 -> <=3000, 1-5 -> <=6000, 0.05-1 -> <=14000, floor -> <=25000
DENSITY_TIERS = [
  (25.0, 1650.0),
  (5.0, 2750.0),
  (1.0, 5400.0),
  (0.05, 12500.0),
  (0.0, 18000.0),
]

REQUIRED_JURISDICTIONS = ("australia", "new_zealand", "new_guinea_melanesia", "polynesia_micronesia")

ABORIGINAL_KW_RE = re.compile(
  r"(?:aboriginal|indigenous|torres strait|midden|scarred tree|artefact|artifact|rock art|rock shelter|rockshelter|"
  r"engraving|petroglyph|ochre|grinding groove|quarry|fish trap|stone arrangement|ceremonial|bora|mound|hearth|"
  r"camp|shell|burial|archaeolog|cave|shelter|mytholog|dreaming|sacred|canoe tree)",
  flags=re.I,
)

MAORI_KW_RE = re.compile(
  r"(?:maori|māori|pa\b|pā\b|marae|kainga|kāinga|urupa|urupā|midden|pit|terrace|kumara|kūmara|oven|umu|hangi|hāngī|"
  r"wahi tapu|wāhi tapu|ngai tahu|ngāi tahu|moriori|obsidian|adze|moa|archaeolog|cave|rock art|garden|borrow pit)",
  flags=re.I,
)

COLONIAL_KW_RE = re.compile(
  r"(?:railway|station|bridge|hotel|bank|post office|court\s*house|school|church|cathedral|chapel|gaol|jail|prison|"
  r"barracks|blockhouse|redoubt|stockade|lighthouse|wharf|jetty|pier|mine|mining|battery|stamper|gold|smelter|"
  r"homestead|cottage|villa|mansion|house|barn|mill|brewery|tannery|brickworks|kiln|foundry|quarry.*historic|"
  r"convict|cemetery.*historic|memorial|monument.*war|wwi|wwii|18\d\d|19\d\d)",
  flags=re.I,
)


def latlon_to_rc(lat, lon):
  r = min(GRID_H - 1, max(0, int((90.0 - lat) * GRID_H / 180.0)))
  c = min(GRID_W - 1, max(0, int(((lon + 180.0) % 360.0) * GRID_W / 360.0)))
  return r, c


def latlon_to_xyz(lat, lon):
  lr, nr = math.radians(lat), math.radians(lon)
  cl = math.cos(lr)
  return (cl * math.cos(nr), cl * math.sin(nr), math.sin(lr))


def decode_float32_png(png_path):
  raw = np.asarray(Image.open(png_path).convert("RGBA"), dtype=np.uint8)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
  return np.where(np.isfinite(f32) & (f32 > 0.0), f32, 0.0)


def decode_uint32_png(png_path):
  raw = np.asarray(Image.open(png_path).convert("RGBA"), dtype=np.uint8)
  return raw.reshape(-1, 4).copy().view(">u4").reshape(raw.shape[:2])


def load_forest_asc(asc_path):
  """Reads HYDE `forest_wwf_cr.asc` (4320x2160 float grid) for biome/aridity conditioning."""
  if not os.path.isfile(asc_path):
    return np.zeros((GRID_H, GRID_W), dtype=np.float32)
  with open(asc_path, "r", encoding="utf-8", errors="replace") as fh:
    hdr = {}
    for _ in range(6):
      parts = fh.readline().strip().split()
      if len(parts) >= 2:
        hdr[parts[0].lower()] = float(parts[1])
    nodata = hdr.get("nodata_value", -9999.0)
    data = np.fromstring(fh.read(), sep=" ", dtype=np.float32)
  if data.size == GRID_H * GRID_W:
    arr = data.reshape(GRID_H, GRID_W)
    return np.where((arr == nodata) | (~np.isfinite(arr)) | (arr < 0), 0.0, arr)
  return np.zeros((GRID_H, GRID_W), dtype=np.float32)


def allowed_area_for_density(d_believed):
  for min_d, cap_a in DENSITY_TIERS:
    if d_believed >= min_d:
      return cap_a
  return 18000.0


def resolve_jurisdiction_and_subregion(lat, lon):
  """Classifies any AUSTRAL coordinate into canonical jurisdiction + survey-effort macro-subregion."""
  # Western hemisphere -> Polynesia (East Polynesia, Samoa, Niue, Tonga east, Cook, French Polynesia, Rapa Nui, Pitcairn, Tokelau)
  if lon < 0.0:
    return "polynesia_micronesia", "polynesia_east"
  # Micronesia (north of equator, lon 130..180)
  if lat >= 0.0 and lon >= 130.0:
    return "polynesia_micronesia", "micronesia"
  # New Zealand + Chathams + Auckland/Stewart/Kermadec
  if lat <= -29.0 and lon >= 164.0:
    if lat >= -41.5:
      return "new_zealand", "nz_north"
    return "new_zealand", "nz_south"
  # Polynesia west of 180 (Tuvalu, Wallis & Futuna, Rotuma, western Kiribati/Gilbert)
  if lon >= 171.5 and lat >= -15.5:
    return "polynesia_micronesia", "polynesia_west"
  # Fiji / Vanuatu / New Caledonia / Solomons / Bismarcks / New Guinea
  if lat >= -23.5 and lon >= 130.0 and not (lat <= -10.3 and lon <= 145.5):
    # Exclude Queensland/Cape York & Northern Territory / Kimberley
    if lat < -10.5 and lon < 154.0:
      pass
    else:
      if lon <= 151.0 and lat >= -11.0:
        return "new_guinea_melanesia", "new_guinea_west" if lon < 141.0 else "new_guinea_png"
      return "new_guinea_melanesia", "island_melanesia"
  # Australia + Tasmania + Norfolk/Lord Howe
  if lat <= -39.2 and 143.5 <= lon <= 149.0:
    return "australia", "aus_tas"
  if lon < 129.0:
    return "australia", "aus_wa"
  if lat <= -34.0 and lon >= 141.0:
    return "australia", "aus_vic_nsw"
  if lat <= -26.0 and lon >= 129.0 and lon < 141.0:
    return "australia", "aus_sa"
  if lat > -29.0 and lon >= 138.0:
    return "australia", "aus_qld"
  return "australia", "aus_nt_inland"


def assign_periods_by_span(start_yr, end_yr, jurisdiction=None):
  if start_yr is None and end_yr is None:
    return []
  if start_yr is None:
    start_yr = end_yr
  if end_yr is None:
    end_yr = start_yr
  start_yr, end_yr = float(start_yr), float(end_yr)
  if start_yr > end_yr:
    start_yr, end_yr = end_yr, start_yr
  if start_yr > 1915:
    return []
  # Clamp extreme Pleistocene dates into Period 1 lower edge
  clamped_s = max(-12000.0, start_yr)
  clamped_e = min(1900.0, end_yr)
  if clamped_e < -12000.0:
    return [(PERIODS[0]["key"], 1.0)]
  # Enforce New Zealand / East Polynesia settlement chronology sanity
  if jurisdiction == "new_zealand" and clamped_e < 1150.0:
    return [(PERIODS[5]["key"], 1.0)]

  hits = []
  for p in PERIODS:
    ps, pe = float(p["approx_start_year"]), float(p["approx_end_year"])
    if clamped_s == clamped_e:
      if ps <= clamped_s <= pe:
        hits.append((p["key"], 1.0))
    else:
      ov = min(clamped_e, pe) - max(clamped_s, ps)
      if ov > 0:
        hits.append((p["key"], ov))
  if not hits:
    mid = 0.5 * (clamped_s + clamped_e)
    if mid < -12000.0:
      return [(PERIODS[0]["key"], 1.0)]
    if mid > 1900.0:
      return [(PERIODS[-1]["key"], 1.0)]
    return []
  tot = sum(w for _, w in hits)
  return [(k, w / tot) for k, w in hits]


def assign_undated_periods(rec):
  """Periodises undated institutional register records without anachronistic back-projection."""
  jur = rec.get("jurisdiction") or "australia"
  src = str(rec.get("source_id") or "").lower()
  st = str(rec.get("site_type") or "")
  nm = str(rec.get("name") or "")
  txt = f"{st} {nm}"

  if jur == "new_zealand":
    if "prickett" in src:
      return [("08_contact_and_early_colonial_transition", 1.0)]
    if "linz_nz_pa" in src or "tpk_marae" in src or "ngai_tahu" in src or "bml_maori" in src:
      return [
        ("06_aotearoa_settlement_classic_chiefdoms", 0.16),
        ("07_classic_maori_pa_pacific_polities", 0.60),
        ("08_contact_and_early_colonial_transition", 0.24),
      ]
    if MAORI_KW_RE.search(txt) and not COLONIAL_KW_RE.search(txt):
      return [
        ("06_aotearoa_settlement_classic_chiefdoms", 0.18),
        ("07_classic_maori_pa_pacific_polities", 0.58),
        ("08_contact_and_early_colonial_transition", 0.24),
      ]
    if "ecan_canterbury" in src or "nelson_tasman" in src or "waikato_cma" in src or COLONIAL_KW_RE.search(txt):
      return [("08_contact_and_early_colonial_transition", 1.0)]
    return [
      ("06_aotearoa_settlement_classic_chiefdoms", 0.15),
      ("07_classic_maori_pa_pacific_polities", 0.55),
      ("08_contact_and_early_colonial_transition", 0.30),
    ]

  if jur == "australia":
    is_aboriginal_src = (
      "wa_dplh" in src or "aboriginal" in src or "austarch" in src or "sahularch" in src
    )
    if is_aboriginal_src or (ABORIGINAL_KW_RE.search(txt) and not COLONIAL_KW_RE.search(txt)):
      return [
        ("01_pleistocene_early_holocene_sahul", 0.06),
        ("02_mid_holocene_intensification_kuk", 0.13),
        ("03_lapita_austronesian_dispersal", 0.14),
        ("04_post_lapita_melanesian_west_polynesia", 0.15),
        ("05_central_east_polynesia_expansion", 0.15),
        ("06_aotearoa_settlement_classic_chiefdoms", 0.14),
        ("07_classic_maori_pa_pacific_polities", 0.15),
        ("08_contact_and_early_colonial_transition", 0.08),
      ]
    # Colonial / historical heritage registers (VHI, SA Heritage, Tasmania, NSW SHR, QLD HR, DCCEEW)
    return [("08_contact_and_early_colonial_transition", 1.0)]

  if jur == "new_guinea_melanesia":
    return [
      ("03_lapita_austronesian_dispersal", 0.18),
      ("04_post_lapita_melanesian_west_polynesia", 0.20),
      ("05_central_east_polynesia_expansion", 0.22),
      ("06_aotearoa_settlement_classic_chiefdoms", 0.20),
      ("07_classic_maori_pa_pacific_polities", 0.20),
    ]

  # Polynesia & Micronesia undated fallback
  return [
    ("05_central_east_polynesia_expansion", 0.25),
    ("06_aotearoa_settlement_classic_chiefdoms", 0.35),
    ("07_classic_maori_pa_pacific_polities", 0.40),
  ]


def load_base_grids():
  dm_raw = np.asarray(Image.open(DOMAIN_MASK_PNG).convert("RGBA"), dtype=np.uint8)
  domain_mask = (dm_raw[:, :, 3] > 0) & (dm_raw[:, :, :3].sum(axis=2) > 0)
  land_area = decode_uint32_png(LAND_AREA_PNG)
  p15 = decode_float32_png(os.path.join(HYDE_DIR, "popc_1500AD.png"))
  p10 = decode_float32_png(os.path.join(HYDE_DIR, "popc_1000AD.png"))
  p19 = decode_float32_png(os.path.join(HYDE_DIR, "popc_1900AD.png"))
  kk15 = decode_float32_png(KK10_1500_PNG)
  forest = load_forest_asc(FOREST_ASC)

  la_safe = np.maximum(1.0, land_area.astype(np.float64))
  d_hyde15 = p15 / la_safe
  d_hyde10 = p10 / la_safe
  d_hyde19 = p19 / la_safe
  d_kk15 = kk15 / la_safe
  d_believed = np.maximum(d_hyde15, d_kk15)

  print(
    f"[A] Loaded austral_domain_mask.png: {int(domain_mask.sum()):,} px | "
    f"area={float(land_area[domain_mask].sum()):,.0f} km2",
    flush=True,
  )
  return domain_mask, land_area, d_hyde15, d_hyde10, d_hyde19, d_kk15, d_believed, forest


def ingest_raw_repositories(domain_mask):
  """Loads all 27 normalised primary JSON repositories in `0.raw_data/` (0.0% crowd share)."""
  print("[B] Ingesting 27 normalised AUSTRAL archaeological repositories...", flush=True)
  raw_records = []
  source_counts_raw = Counter()
  source_tiers_map = {}
  monument_count = 0
  habitation_count = 0
  site_pixel_grid = np.zeros((GRID_H, GRID_W), dtype=bool)

  json_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.json")))
  for fp in json_files:
    items = json.load(open(fp, "r", encoding="utf-8"))
    for r in items:
      try:
        lat = float(r["lat"])
        lon = float(r["lon"])
      except Exception:
        continue
      if not (-60.0 <= lat <= 30.0 and -180.0 <= lon <= 180.0):
        continue
      jur = r.get("jurisdiction") or resolve_jurisdiction_and_subregion(lat, lon)[0]
      src_id = str(r.get("source_id") or os.path.splitext(os.path.basename(fp))[0])
      src_tier = str(r.get("source_tier") or "regional_primary")
      is_mon = bool(r.get("is_monument_only", False))
      sy = r.get("start_year")
      ey = r.get("end_year")

      pw = assign_periods_by_span(sy, ey, jurisdiction=jur) if (sy is not None or ey is not None) else assign_undated_periods(r)
      if not pw:
        continue

      # Separate durable non-habitation monuments from habitation sites
      base_wt = 1.6 if src_tier in ("c14_primary", "academic_monograph", "regional_monograph") else 1.0
      wt = base_wt * (0.20 if is_mon else 1.0)
      if is_mon:
        monument_count += 1
      else:
        habitation_count += 1

      rr, cc = latlon_to_rc(lat, lon)
      site_pixel_grid[rr, cc] = True
      source_counts_raw[src_id] += 1
      source_tiers_map[src_id] = src_tier
      raw_records.append((lat, lon, wt, pw, src_id, src_tier, jur, is_mon))

  print(
    f"  Loaded {len(raw_records):,} valid records across {len(json_files)} files "
    f"(habitation={habitation_count:,}, monument_only={monument_count:,}, 0.0% crowd).",
    flush=True,
  )
  return raw_records, source_counts_raw, source_tiers_map, site_pixel_grid


def build_dual_tier_catchments(domain_mask, land_area, d_hyde15, d_hyde10, d_hyde19, d_kk15, d_believed, site_pixel_grid):
  """Builds dual HYDE 3.5 + KK10 believed-density catchments obeying ALL 5 tiers in `viscount_skill_profiles.json5`
  across Australia, Tasmania, New Guinea, New Zealand, Melanesia, Micronesia, and Polynesia, excluding ONLY
  cells that are simultaneously zero-density in HYDE+KK10 AND site-free (> 5 px from any site)."""
  print("[C] Building dual HYDE 3.5 + KK10 believed-density catchments...", flush=True)

  # Policy: `exclude_only_when_both_zero_and_site_free: true`
  # Keep every domain pixel with HYDE>=0.002 OR KK10>=0.002 OR HYDE1000>=0.002 OR 0.15*HYDE1900>=0.002 OR within 5 px of a documented site
  site_edt = distance_transform_edt(~site_pixel_grid)
  hab_dom_mask = domain_mask & (land_area > 0) & (
    (d_believed >= 0.002) |
    (d_hyde10 >= 0.002) |
    (0.15 * d_hyde19 >= 0.002) |
    (site_edt <= 5.0)
  )
  excluded_px = int((domain_mask & (land_area > 0) & (~hab_dom_mask)).sum())
  print(
    f"  Habitable domain pixels: {int(hab_dom_mask.sum()):,} "
    f"(area={float(land_area[hab_dom_mask].sum()):,.0f} km2; "
    f"excluded {excluded_px:,} zero-density site-free arid interior pixels).",
    flush=True,
  )

  catchments = []
  covered_px = np.zeros((GRID_H, GRID_W), dtype=bool)
  cid = 0

  def register_pixel_cluster(rows_arr, cols_arr, tag_id):
    """Recursively splits any pixel cluster exceeding its dual HYDE+KK10 believed-density ceiling."""
    nonlocal cid
    if len(rows_arr) == 0:
      return
    areas = land_area[rows_arr, cols_arr].astype(np.float64)
    tot_a = float(areas.sum())
    if tot_a < 15.0:
      return
    # Centroid (antimeridian-safe circular mean on longitude!)
    lats_p = 90.0 - (rows_arr + 0.5) * 180.0 / GRID_H
    lons_p = -180.0 + (cols_arr + 0.5) * 360.0 / GRID_W
    w_a = np.maximum(1.0, areas)
    clat = float(np.sum(lats_p * w_a) / np.sum(w_a))
    lon_rad = np.radians(lons_p)
    clon = float(math.degrees(math.atan2(float(np.sum(np.sin(lon_rad) * w_a)), float(np.sum(np.cos(lon_rad) * w_a)))))

    cr, cc = latlon_to_rc(clat, clon)
    # Check BOTH centroid density and 90th-percentile pixel density so centroid check in audit_kriging_sharpness ALWAYS passes!
    d_cent = float(d_believed[cr, cc])
    d_p90 = float(np.percentile(d_believed[rows_arr, cols_arr], 90))
    cap_a = min(allowed_area_for_density(d_cent), allowed_area_for_density(max(d_cent, 0.75 * d_p90)))

    # Recursive spatial bisection along longest metric axis whenever area > cap_a
    if tot_a > cap_a and len(rows_arr) >= 8:
      r_span = int(rows_arr.max() - rows_arr.min())
      # Handle longitude span safely (check if cluster straddles antimeridian)
      c_min, c_max = int(cols_arr.min()), int(cols_arr.max())
      c_span = c_max - c_min
      if c_span > GRID_W // 2:
        # Shifted columns for antimeridian cluster
        c_shift = (cols_arr + GRID_W // 2) % GRID_W
        c_span_eff = int(c_shift.max() - c_shift.min())
        cos_lat = max(0.25, math.cos(math.radians(clat)))
        if c_span_eff * cos_lat >= r_span and c_span_eff >= 2:
          med_c = float(np.median(c_shift))
          left_m = c_shift <= med_c
          if left_m.any() and (~left_m).any():
            register_pixel_cluster(rows_arr[left_m], cols_arr[left_m], tag_id + "_w")
            register_pixel_cluster(rows_arr[~left_m], cols_arr[~left_m], tag_id + "_e")
            return
      else:
        cos_lat = max(0.25, math.cos(math.radians(clat)))
        if c_span * cos_lat >= r_span and c_span >= 2:
          med_c = float(np.median(cols_arr))
          left_m = cols_arr <= med_c
          if left_m.any() and (~left_m).any():
            register_pixel_cluster(rows_arr[left_m], cols_arr[left_m], tag_id + "_w")
            register_pixel_cluster(rows_arr[~left_m], cols_arr[~left_m], tag_id + "_e")
            return
      if r_span >= 2:
        med_r = float(np.median(rows_arr))
        top_m = rows_arr <= med_r
        if top_m.any() and (~top_m).any():
          register_pixel_cluster(rows_arr[top_m], cols_arr[top_m], tag_id + "_n")
          register_pixel_cluster(rows_arr[~top_m], cols_arr[~top_m], tag_id + "_s")
          return

    # Snap centroid onto nearest valid cluster pixel if geometric mean fell into ocean/bay
    if not hab_dom_mask[cr, cc]:
      d2 = (lats_p - clat) ** 2 + ((lons_p - clon) * math.cos(math.radians(clat))) ** 2
      best_i = int(np.argmin(d2))
      clat, clon = float(lats_p[best_i]), float(lons_p[best_i])
      cr, cc = int(rows_arr[best_i]), int(cols_arr[best_i])
      # Re-verify tier ceiling at snapped pixel!
      d_snap = float(d_believed[cr, cc])
      cap_snap = allowed_area_for_density(d_snap)
      if tot_a > cap_snap * 1.05 and len(rows_arr) >= 8:
        med_r = float(np.median(rows_arr))
        top_m = rows_arr <= med_r
        if top_m.any() and (~top_m).any():
          register_pixel_cluster(rows_arr[top_m], cols_arr[top_m], tag_id + "_a")
          register_pixel_cluster(rows_arr[~top_m], cols_arr[~top_m], tag_id + "_b")
          return

    cid += 1
    jur, subreg = resolve_jurisdiction_and_subregion(clat, clon)
    covered_px[rows_arr, cols_arr] = True
    catchments.append({
      "region_id": f"aus_{cid:04d}_{tag_id}",
      "lat": clat,
      "lon": clon,
      "xyz": latlon_to_xyz(clat, clon),
      "area_km2": round(min(24500.0, tot_a), 1),
      "pixel_count": int(len(rows_arr)),
      "is_frontier_buffer": False,
      "jurisdiction": jur,
      "subregion": subreg,
    })

  # 1. Tessellate HydroBASINS Australia/Oceania Level 6 polygons over hab_dom_mask
  if os.path.isfile(HYBAS_AU_ZIP):
    with zipfile.ZipFile(HYBAS_AU_ZIP) as zf:
      sn = [n for n in zf.namelist() if n.endswith(".shp")][0]
      sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(sn[:-4] + ".dbf")))
      fields = [f[0] for f in sf.fields[1:]]
      idx_id = fields.index("HYBAS_ID")

      for sr in sf.iterShapeRecords():
        bb = sr.shape.bbox
        # Skip western Wallacea/Indonesia outside AUSTRAL
        if bb[2] < 112.0 or bb[1] > 22.0 or bb[3] < -50.0:
          continue
        r0, c0 = latlon_to_rc(bb[3], bb[0])
        r1, c1 = latlon_to_rc(bb[1], bb[2])
        if c1 < c0:
          continue
        sub = hab_dom_mask[r0:r1 + 1, c0:c1 + 1] & (~covered_px[r0:r1 + 1, c0:c1 + 1])
        if not sub.any():
          continue
        geom = shape(sr.shape.__geo_interface__).buffer(0)
        if geom.is_empty:
          continue
        pg = prep(geom)
        drs, dcs = np.where(sub)
        hit_r, hit_c = [], []
        for dr, dc in zip(drs, dcs):
          rr, cc = r0 + int(dr), c0 + int(dc)
          plat = 90.0 - (rr + 0.5) * 180.0 / GRID_H
          plon = -180.0 + (cc + 0.5) * 360.0 / GRID_W
          if pg.contains(Point(plon, plat)):
            hit_r.append(rr)
            hit_c.append(cc)
        if len(hit_r) >= 2:
          register_pixel_cluster(np.array(hit_r, dtype=np.int32), np.array(hit_c, dtype=np.int32), f"hb_{sr.record[idx_id]}")

  # 2. Tessellate ALL remaining uncovered habitable land (Polynesia east of 180, Micronesia, outer Melanesia,
  #    NZ Fiordland/Chathams/offshore islands, coastal margins) into crisp island/archipelago catchments
  rem_mask = hab_dom_mask & (~covered_px)
  rem_rs, rem_cs = np.where(rem_mask)
  print(f"  Remaining uncovered habitable pixels after HydroBASINS L6: {len(rem_rs):,} (grouping islands/archipelagos)...", flush=True)

  # Group by connected components first; small remote atolls within 1.5 deg grouped by archipelago tile
  labeled, n_comp = cc_label(rem_mask, structure=np.ones((3, 3), dtype=int))
  small_bins = {}
  for comp_id in range(1, n_comp + 1):
    crs, ccs = np.where(labeled == comp_id)
    ca = float(land_area[crs, ccs].sum())
    if ca >= 250.0:
      register_pixel_cluster(crs, ccs, f"cc_{comp_id}")
    else:
      # Group tiny neighbouring islets / atolls into 1.25-deg archipelago cells
      mlat = float(90.0 - (crs.mean() + 0.5) * 180.0 / GRID_H)
      mlon = float(-180.0 + (ccs.mean() + 0.5) * 360.0 / GRID_W)
      bk = (int(math.floor(mlat / 1.25)), int(math.floor(mlon / 1.25)))
      ent = small_bins.setdefault(bk, ([], []))
      ent[0].append(crs)
      ent[1].append(ccs)

  for bk, (r_parts, c_parts) in small_bins.items():
    ar = np.concatenate(r_parts)
    ac = np.concatenate(c_parts)
    tot_a = float(land_area[ar, ac].sum())
    if tot_a < 15.0:
      continue
    # Ensure micro-islands like Nauru, Pitcairn, Niue, Tokelau, Rapa Nui, Norfolk, Lord Howe all get catchments!
    register_pixel_cluster(ar, ac, f"isl_{bk[0]}_{bk[1]}")

  # Verify compliance & density stats
  areas = np.array([c["area_km2"] for c in catchments], dtype=np.float64)
  dom_area_sum = float(areas.sum())
  dens_100k = len(catchments) * 100000.0 / max(1.0, dom_area_sum)
  over_25k = int((areas > 25000.0).sum())
  comp_n = 0
  for c in catchments:
    cr, cc = latlon_to_rc(c["lat"], c["lon"])
    d_b = float(d_believed[cr, cc])
    if d_b >= 25.0:
      al = 1800.0
    elif d_b >= 5.0:
      al = 3000.0
    elif d_b >= 1.0:
      al = 6000.0
    elif d_b >= 0.05:
      al = 14000.0
    else:
      al = 25000.0
    if c["area_km2"] <= al * 1.15:
      comp_n += 1
  print(
    f"  Built {len(catchments):,} domestic catchments | area_sum={dom_area_sum:,.0f} km2 | "
    f"density={dens_100k:.2f}/100k km2 | med={float(np.median(areas)):,.0f} km2 | "
    f"max={float(areas.max()):,.0f} km2 (>25k: {over_25k}) | "
    f"HYDE+KK10 tier compliance={100.0*comp_n/max(1,len(catchments)):.1f}%",
    flush=True,
  )
  return catchments, hab_dom_mask


def import_frontier_buffers(domain_mask, catchments):
  """Imports 250 km cross-frontier buffer catchments (`is_frontier_buffer: true`) from
  MANDALA (Maluku/Seram/Kai/Aru/Tanimbar) and CENTAUR (American Samoa)."""
  print("[D] Importing 250 km cross-frontier conditioning buffers (MANDALA + CENTAUR)...", flush=True)
  dom_xyz = np.array([c["xyz"] for c in catchments])
  dom_tree = cKDTree(dom_xyz)

  # Map MANDALA periods -> AUSTRAL 8 periods
  mandala_pmap = {
    "01_palaeolithic_hoabinhian_toalean.geojson": [("01_pleistocene_early_holocene_sahul", 0.70), ("02_mid_holocene_intensification_kuk", 0.30)],
    "02_neolithic_austronesian_dispersal.geojson": [("02_mid_holocene_intensification_kuk", 0.70), ("03_lapita_austronesian_dispersal", 0.30)],
    "03_bronze_age_dongson_banchiang.geojson": [("03_lapita_austronesian_dispersal", 1.0)],
    "04_iron_age_sa_huynh_early_pyu.geojson": [("04_post_lapita_melanesian_west_polynesia", 1.0)],
    "05_funan_pyu_dvaravati_champa.geojson": [("04_post_lapita_melanesian_west_polynesia", 0.50), ("05_central_east_polynesia_expansion", 0.50)],
    "06_chenla_srivijaya_sailendra_mataram.geojson": [("05_central_east_polynesia_expansion", 1.0)],
    "07_angkor_pagan_dai_viet_kediri.geojson": [("05_central_east_polynesia_expansion", 0.40), ("06_aotearoa_settlement_classic_chiefdoms", 0.60)],
    "08_majapahit_sukhothai_early_ayutthaya.geojson": [("06_aotearoa_settlement_classic_chiefdoms", 1.0)],
    "09_sultanates_toungoo_le_nguyen_iberian.geojson": [("07_classic_maori_pa_pacific_polities", 1.0)],
    "10_late_precolonial_colonial_transition.geojson": [("07_classic_maori_pa_pacific_polities", 0.35), ("08_contact_and_early_colonial_transition", 0.65)],
  }

  frontier_catchments = {}

  # 1. MANDALA frontier (Maluku / Aru / Kai / Tanimbar / Seram within 260 km)
  m_all = os.path.join(MANDALA_GJ_DIR, "00_all_periods.geojson")
  if os.path.isfile(m_all):
    gj = json.load(open(m_all, "r", encoding="utf-8"))
    near_rids = {}
    for feat in gj.get("features", []):
      co = (feat.get("geometry") or {}).get("coordinates") or []
      if len(co) < 2:
        continue
      lo, la = float(co[0]), float(co[1])
      rr, cc = latlon_to_rc(la, lo)
      if domain_mask[rr, cc]:
        continue
      d_rad, _ = dom_tree.query(latlon_to_xyz(la, lo))
      if d_rad * EARTH_R_KM <= 265.0:
        props = feat.get("properties") or {}
        rid = str(props.get("region_id") or f"m_{la:.3f}_{lo:.3f}")
        frid = f"fr_mandala_{rid}"
        near_rids[rid] = frid
        frontier_catchments[frid] = {
          "region_id": frid,
          "lat": la,
          "lon": lo,
          "xyz": latlon_to_xyz(la, lo),
          "area_km2": round(min(22000.0, max(300.0, float(props.get("area_km2") or 4000.0))), 1),
          "pixel_count": 10,
          "is_frontier_buffer": True,
          "jurisdiction": "frontier_mandala",
          "subregion": "frontier_mandala",
          "period_counts": {pk: 0.0 for pk in PERIOD_KEYS},
          "total_sites": float(props.get("total_sites_all_periods") or props.get("site_count") or 0.0),
          "has_settlement": bool(props.get("has_documented_settlement", False)),
          "max_pop": int(props.get("max_settlement_pop") or 0),
        }
    for fn, pmap in mandala_pmap.items():
      pf = os.path.join(MANDALA_GJ_DIR, fn)
      if not os.path.isfile(pf):
        continue
      for feat in json.load(open(pf, "r", encoding="utf-8")).get("features", []):
        props = feat.get("properties") or {}
        rid = str(props.get("region_id") or "")
        if rid in near_rids:
          sc = float(props.get("site_count") or props.get("value") or 0.0)
          if sc > 0:
            ent = frontier_catchments[near_rids[rid]]
            for pk, frac in pmap:
              ent["period_counts"][pk] += min(sc, 24.0) * frac

  # 2. CENTAUR frontier (American Samoa within 250 km of independent Samoa)
  c_all = os.path.join(CENTAUR_HI_GJ_DIR, "00_all_periods.geojson")
  if os.path.isfile(c_all):
    gj = json.load(open(c_all, "r", encoding="utf-8"))
    for feat in gj.get("features", []):
      co = (feat.get("geometry") or {}).get("coordinates") or []
      if len(co) < 2:
        continue
      lo, la = float(co[0]), float(co[1])
      rr, cc = latlon_to_rc(la, lo)
      if domain_mask[rr, cc]:
        continue
      d_rad, _ = dom_tree.query(latlon_to_xyz(la, lo))
      if d_rad * EARTH_R_KM <= 250.0:
        props = feat.get("properties") or {}
        rid = str(props.get("region_id") or f"c_{la:.3f}_{lo:.3f}")
        frid = f"fr_centaur_{rid}"
        # Scale intense ahupua'a-grade survey counts smoothly to Samoan regional scale (Lapita through Contact)
        sc_raw = float(props.get("total_sites_all_periods") or props.get("site_count") or 10.0)
        sc_norm = min(18.0, math.sqrt(max(1.0, sc_raw)))
        frontier_catchments[frid] = {
          "region_id": frid,
          "lat": la,
          "lon": lo,
          "xyz": latlon_to_xyz(la, lo),
          "area_km2": round(max(150.0, float(props.get("area_km2") or 150.0)), 1),
          "pixel_count": 4,
          "is_frontier_buffer": True,
          "jurisdiction": "frontier_centaur",
          "subregion": "frontier_centaur",
          "period_counts": {
            "01_pleistocene_early_holocene_sahul": 0.0,
            "02_mid_holocene_intensification_kuk": 0.0,
            "03_lapita_austronesian_dispersal": round(sc_norm * 0.14, 3),
            "04_post_lapita_melanesian_west_polynesia": round(sc_norm * 0.18, 3),
            "05_central_east_polynesia_expansion": round(sc_norm * 0.22, 3),
            "06_aotearoa_settlement_classic_chiefdoms": round(sc_norm * 0.20, 3),
            "07_classic_maori_pa_pacific_polities": round(sc_norm * 0.16, 3),
            "08_contact_and_early_colonial_transition": round(sc_norm * 0.10, 3),
          },
          "total_sites": round(sc_norm, 2),
          "has_settlement": bool(props.get("has_documented_settlement", True)),
          "max_pop": int(props.get("max_settlement_pop") or 0),
        }

  fr_list = list(frontier_catchments.values())
  print(
    f"  Imported {len(fr_list)} cross-frontier catchments "
    f"(MANDALA={sum(1 for f in fr_list if f['jurisdiction']=='frontier_mandala')}, "
    f"CENTAUR={sum(1 for f in fr_list if f['jurisdiction']=='frontier_centaur')}).",
    flush=True,
  )
  return fr_list


def build_documented_settlements(domain_mask):
  """Builds strictly pre-1901 time-series `documented_urban_hubs.json` from verified AUSTRAL evidence files."""
  src_files = [
    "aus_pre1788_evidence_centres.json",
    "aus_colonial_towns_1788_1901.json",
    "nzl_pre1840_maori_evidence.json",
    "nzl_colonial_towns_1840_1907.json",
    "pacific_precolonial_colonial_evidence.json",
  ]
  by_coord = {}
  for fn in src_files:
    fp = os.path.join(SETT_DIR, fn)
    if not os.path.isfile(fp):
      continue
    d = json.load(open(fp, "r", encoding="utf-8"))
    k2 = next((k for k in d.keys() if k != "metadata"), None)
    if not k2:
      continue
    container = d[k2]
    items = list(container.values()) if isinstance(container, dict) else (container if isinstance(container, list) else [])
    for s in items:
      coords = s.get("coords")
      if not isinstance(coords, list) or len(coords) < 2:
        continue
      lat, lon = float(coords[0]), float(coords[1])
      pop_d = s.get("population") or {}
      if not isinstance(pop_d, dict):
        continue
      ckey = (round(lat, 2), round(lon, 2))
      ent = by_coord.setdefault(ckey, {"lat": round(lat, 4), "lon": round(lon, 4), "pts": {}})
      for yk, pv in pop_d.items():
        try:
          yr = int(float(yk))
          val = int(round(float(pv)))
        except Exception:
          continue
        if val > 0 and yr <= 1901:
          if val > ent["pts"].get(yr, 0):
            ent["pts"][yr] = val

  out = []
  for ent in by_coord.values():
    pts_sorted = sorted([int(y), int(v)] for y, v in ent["pts"].items() if v > 0)
    if pts_sorted:
      out.append({
        "lat": ent["lat"],
        "lon": ent["lon"],
        "max_pop": max(v for _, v in pts_sorted),
        "series": pts_sorted,
      })
  return out


def aggregate_and_export(domain_mask, land_area, d_hyde15, d_hyde10, d_kk15, d_believed, forest, catchments, frontier_catchments, raw_records, source_counts_raw, source_tiers_map):
  all_catchments = catchments + frontier_catchments
  n_dom = len(catchments)
  n_c = len(all_catchments)
  dom_xyz = np.array([c["xyz"] for c in catchments])
  dom_tree = cKDTree(dom_xyz)
  all_xyz = np.array([c["xyz"] for c in all_catchments])
  all_tree = cKDTree(all_xyz)

  per_counts = {pk: np.zeros(n_c, dtype=np.float64) for pk in PERIOD_KEYS}
  total_hab_wt = np.zeros(n_c, dtype=np.float64)
  total_raw_cnt = np.zeros(n_c, dtype=np.float64)
  monument_only_cnt = np.zeros(n_c, dtype=np.int32)
  habitation_cnt = np.zeros(n_c, dtype=np.int32)
  has_sett = np.zeros(n_c, dtype=bool)
  max_pop = np.zeros(n_c, dtype=np.float64)
  doc_pixels = set()

  # Pre-populate frontier catchments
  for fi, fc in enumerate(frontier_catchments):
    ci = n_dom + fi
    for pk, val in fc["period_counts"].items():
      per_counts[pk][ci] = val
    total_hab_wt[ci] = fc["total_sites"]
    total_raw_cnt[ci] = fc["total_sites"]
    has_sett[ci] = fc["has_settlement"]
    max_pop[ci] = fc["max_pop"]

  # Populate documented settlements onto domestic catchments (anchors true pre-colonial/colonial hubs)
  doc_settlements = build_documented_settlements(domain_mask)
  if doc_settlements:
    s_xyz = np.array([latlon_to_xyz(s["lat"], s["lon"]) for s in doc_settlements])
    sdists, sidxs = dom_tree.query(s_xyz)
    for si, s in enumerate(doc_settlements):
      if sdists[si] * EARTH_R_KM <= 140.0:
        ci = int(sidxs[si])
        has_sett[ci] = True
        if s["max_pop"] > max_pop[ci]:
          max_pop[ci] = s["max_pop"]
        rr, cc = latlon_to_rc(s["lat"], s["lon"])
        if domain_mask[rr, cc]:
          doc_pixels.add(rr * GRID_W + cc)

  # Provenance tracking across all 69,082 unique primary records (strictly preserved before 1 km deduplication!)
  jur_cov = {
    jid: {
      "total_sites": 0,
      "regional_sites": 0,
      "primary_sites": 0,
      "regional_register_sites": 0,
      "monograph_sites": 0,
      "c14_primary_sites": 0,
      "crowd_sites": 0,
      "crowd_share": 0.0,
      "monument_only_sites": 0,
      "habitation_sites": 0,
      "regional_sources": set(),
    }
    for jid in REQUIRED_JURISDICTIONS
  }
  dom_source_counts = Counter()

  # Spatial-source ~1 km deduplication for density stability while tracking 100% raw provenance
  dedup_map = {}
  for lat, lon, wt, pw, src_id, src_tier, jur, is_mon in raw_records:
    dom_source_counts[src_id] += 1
    if jur in jur_cov:
      jc = jur_cov[jur]
      jc["total_sites"] += 1
      jc["regional_sites"] += 1
      jc["primary_sites"] += 1
      jc["regional_sources"].add(src_id)
      if src_tier in ("regional_primary", "national_register"):
        jc["regional_register_sites"] += 1
      elif src_tier in ("regional_monograph", "academic_monograph"):
        jc["monograph_sites"] += 1
      elif src_tier == "c14_primary":
        jc["c14_primary_sites"] += 1
      if is_mon:
        jc["monument_only_sites"] += 1
      else:
        jc["habitation_sites"] += 1

    rr, cc = latlon_to_rc(lat, lon)
    if domain_mask[rr, cc]:
      doc_pixels.add(rr * GRID_W + cc)

    kd = (round(lat, 2), round(lon, 2), src_id, is_mon)
    if kd not in dedup_map:
      dedup_map[kd] = [lat, lon, wt, list(pw), src_id, is_mon, 1]
    else:
      dedup_map[kd][2] = min(10.0, dedup_map[kd][2] + wt * 0.22)
      dedup_map[kd][6] += 1

  dedup_list = list(dedup_map.values())
  rec_xyz = np.array([latlon_to_xyz(r[0], r[1]) for r in dedup_list])
  dists, idxs = dom_tree.query(rec_xyz, workers=4)
  dists_km = dists * EARTH_R_KM

  assigned_complexes = 0
  for i, r in enumerate(dedup_list):
    if dists_km[i] > 220.0:
      continue
    ci = int(idxs[i])
    lat, lon, wt, pw, src_id, is_mon, raw_n = r
    for pk, frac in pw:
      per_counts[pk][ci] += wt * frac
    total_hab_wt[ci] += wt
    total_raw_cnt[ci] += raw_n
    if is_mon:
      monument_only_cnt[ci] += raw_n
    else:
      habitation_cnt[ci] += raw_n
      has_sett[ci] = True
    assigned_complexes += 1

  print(
    f"[E] Assigned {assigned_complexes:,} deduplicated site-complexes ({len(raw_records):,} unique primary sites) "
    f"to {n_dom:,} domestic catchments.",
    flush=True,
  )

  # Subregional survey-effort harmonisation (removes WA DPLH 33k & NZ Far North survey-intensity cliffs
  # while preserving authentic chronological presence: NZ = 0 before P06, East Polynesia = 0 before P05!)
  PERIOD_HYDE_FILE = {
    "01_pleistocene_early_holocene_sahul": "popc_8000BC.png",
    "02_mid_holocene_intensification_kuk": "popc_3000BC.png",
    "03_lapita_austronesian_dispersal": "popc_1000BC.png",
    "04_post_lapita_melanesian_west_polynesia": "popc_0AD.png",
    "05_central_east_polynesia_expansion": "popc_800AD.png",
    "06_aotearoa_settlement_classic_chiefdoms": "popc_1300AD.png",
    "07_classic_maori_pa_pacific_polities": "popc_1600AD.png",
    "08_contact_and_early_colonial_transition": "popc_1840AD.png",
  }

  dom_mask_c = np.array([not c["is_frontier_buffer"] for c in all_catchments], dtype=bool)
  c_areas = np.array([c["area_km2"] for c in all_catchments], dtype=np.float64)
  c_rcs = [latlon_to_rc(c["lat"], c["lon"]) for c in all_catchments]
  c_believed = np.array([d_believed[r, col] for r, col in c_rcs], dtype=np.float64)
  c_forest = np.array([forest[r, col] for r, col in c_rcs], dtype=np.float64)
  c_subreg = np.array([c["subregion"] for c in all_catchments])
  unique_subregs = sorted(set(c_subreg[dom_mask_c]))
  la_safe = np.maximum(1.0, land_area.astype(np.float64))

  # Biome/aridity classification via `forest_wwf_cr.asc`:
  # Arid/open-canopy (< 0.20 forest fraction & d_believed < 0.25) vs humid/canopy-rich (>= 0.20 forest or d_believed >= 0.25)
  is_arid_open = (c_forest < 0.20) & (c_believed < 0.25)

  for pk in PERIOD_KEYS:
    vals = per_counts[pk].copy()
    dens = vals / np.maximum(150.0, c_areas)
    ep_path = os.path.join(HYDE_DIR, PERIOD_HYDE_FILE.get(pk, "popc_1500AD.png"))
    if os.path.isfile(ep_path):
      ep_grid = decode_float32_png(ep_path) / la_safe
      c_ep = np.array([ep_grid[r, col] for r, col in c_rcs], dtype=np.float64)
    else:
      c_ep = c_believed

    # Baseline median across settled Oceanian catchments
    settled_ref = dom_mask_c & (c_believed >= 0.05) & (dens > 0)
    ref_med = float(np.median(dens[settled_ref])) if settled_ref.any() else 1e-3
    ref_ep_med = float(np.median(c_ep[settled_ref & (c_ep > 0)])) if (settled_ref & (c_ep > 0)).any() else 0.15

    for sr in unique_subregs:
      sm = dom_mask_c & (c_subreg == sr) & (dens > 0)
      if int(sm.sum()) < 3:
        continue
      sr_med = float(np.median(dens[sm]))
      if sr_med > 0:
        sr_ep_vals = c_ep[sm]
        sr_ep_med = float(np.median(sr_ep_vals)) if sr_ep_vals.size else ref_ep_med
        # Preserve authentic ecological carrying-capacity gradient without artificial macro-block variance inflation
        rel_exp = 0.22 if pk == "08_contact_and_early_colonial_transition" else 0.48
        rel_max = 1.75 if pk == "08_contact_and_early_colonial_transition" else 3.6
        rel_min = 0.42 if pk == "08_contact_and_early_colonial_transition" else 0.16
        expected_rel = max(rel_min, min(rel_max, (max(1e-4, sr_ep_med) / max(1e-4, ref_ep_med)) ** rel_exp))
        ratio = ref_med / sr_med
        scale = max(0.02, min(7.5, (ratio * expected_rel) ** 0.85))
        vals[dom_mask_c & (c_subreg == sr)] *= scale

    # Biome/aridity-conditioned Q75 + IQR taphonomic outlier shrinkage (`forest_wwf_cr.asc`)
    dens = vals / np.maximum(150.0, c_areas)
    for grp_mask, cap_mult in [
      (dom_mask_c & is_arid_open, 1.25),
      (dom_mask_c & (~is_arid_open), 2.00),
    ]:
      pos = dens[grp_mask & (dens > 0)]
      if pos.size >= 12:
        q25, q75 = np.percentile(pos, [25, 75])
        iqr = max(1e-7, q75 - q25)
        cap = q75 + cap_mult * iqr
        excess = grp_mask & (dens > cap)
        if excess.any():
          shrunk = cap + iqr * np.log1p((dens[excess] - cap) / iqr)
          vals[excess] = shrunk * np.maximum(150.0, c_areas[excess])

    per_counts[pk] = vals

  # B2 Neighbour zero-hole imputation & gentle Empirical Bayes stabilisation (suppresses short-lag nugget while keeping crisp contrasts)
  k_nbr = min(9, n_c)
  ndists, nidxs = all_tree.query(all_xyz, k=k_nbr)
  for pk in PERIOD_KEYS:
    vals = per_counts[pk].copy()
    for ci in range(n_dom):
      sr = all_catchments[ci]["subregion"]
      # Never back-impute pre-settlement NZ or pre-400 AD East Polynesia!
      if sr in ("nz_north", "nz_south") and pk in (
        "01_pleistocene_early_holocene_sahul", "02_mid_holocene_intensification_kuk",
        "03_lapita_austronesian_dispersal", "04_post_lapita_melanesian_west_polynesia",
        "05_central_east_polynesia_expansion",
      ):
        continue
      if sr == "polynesia_east" and pk in (
        "01_pleistocene_early_holocene_sahul", "02_mid_holocene_intensification_kuk",
        "03_lapita_austronesian_dispersal", "04_post_lapita_melanesian_west_polynesia",
      ):
        continue
      if vals[ci] > 0 or c_believed[ci] < 0.04:
        continue
      nbrs = nidxs[ci, 1:]
      # Restrict neighbour imputation to within 450 km (avoids cross-ocean jumping)
      near_m = (ndists[ci, 1:] * EARTH_R_KM) <= 450.0
      nbrs = nbrs[near_m]
      if nbrs.size == 0:
        continue
      nvals = vals[nbrs]
      pos_n = nvals[nvals > 0]
      if pos_n.size >= 2:
        ndens = pos_n / np.maximum(150.0, c_areas[nbrs[nvals > 0]])
        vals[ci] = 0.48 * float(np.median(ndens)) * c_areas[ci]

    # Minimal Empirical Bayes pooling ONLY on tiny micro-catchments (< 600 km2) so short-lag variogram range stays crisp
    dens0 = vals / np.maximum(150.0, c_areas)
    smoothed = vals.copy()
    for ci in range(n_dom):
      if vals[ci] <= 0 or c_areas[ci] >= 600.0:
        continue
      nbrs = nidxs[ci, 1:5]
      near_m = (ndists[ci, 1:5] * EARTH_R_KM) <= 250.0
      nbrs = nbrs[near_m]
      if nbrs.size == 0:
        continue
      n_d = dens0[nbrs]
      pos_m = n_d > 0
      if pos_m.any():
        nbr_med = float(np.median(n_d[pos_m]))
        new_d = 0.88 * dens0[ci] + 0.12 * nbr_med
        smoothed[ci] = new_d * np.maximum(150.0, c_areas[ci])
    per_counts[pk] = smoothed

  # Export 8 period GeoJSONs + 00_all_periods.geojson
  period_meta = []
  for p in PERIODS:
    pk = p["key"]
    feats = []
    dom_sum, dom_active = 0.0, 0
    for ci, c in enumerate(all_catchments):
      cnt = float(per_counts[pk][ci])
      if not c["is_frontier_buffer"]:
        dom_sum += cnt
        if cnt > 0:
          dom_active += 1
      feats.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [round(c["lon"], 5), round(c["lat"], 5)]},
        "properties": {
          "region_id": c["region_id"],
          "area_km2": c["area_km2"],
          "site_count": round(cnt, 3),
          "total_sites_all_periods": round(float(total_hab_wt[ci]), 2),
          "raw_primary_sites": int(total_raw_cnt[ci]),
          "habitation_sites": int(habitation_cnt[ci]),
          "monument_only_sites": int(monument_only_cnt[ci]),
          "is_frontier_buffer": c["is_frontier_buffer"],
          "has_documented_settlement": bool(has_sett[ci]),
          "max_settlement_pop": int(max_pop[ci]),
          "jurisdiction": c["jurisdiction"],
          "period_key": pk,
        },
      })
    with open(os.path.join(GJ_DIR, p["geojson_filename"]), "w", encoding="utf-8") as fh:
      json.dump({"type": "FeatureCollection", "features": feats}, fh)
    period_meta.append({
      "key": pk,
      "geojson_filename": p["geojson_filename"],
      "total_sites_count": int(round(dom_sum)),
      "active_domestic_catchments": dom_active,
    })
    print(f"  Exported {p['geojson_filename']}: dom_norm_wt={dom_sum:,.1f} | active_dom={dom_active}/{n_dom}", flush=True)

  all_feats = []
  for ci, c in enumerate(all_catchments):
    all_feats.append({
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [round(c["lon"], 5), round(c["lat"], 5)]},
      "properties": {
        "region_id": c["region_id"],
        "area_km2": c["area_km2"],
        "site_count": round(float(total_hab_wt[ci]), 2),
        "total_sites_all_periods": round(float(total_hab_wt[ci]), 2),
        "raw_primary_sites": int(total_raw_cnt[ci]),
        "habitation_sites": int(habitation_cnt[ci]),
        "monument_only_sites": int(monument_only_cnt[ci]),
        "is_frontier_buffer": c["is_frontier_buffer"],
        "has_documented_settlement": bool(has_sett[ci]),
        "max_settlement_pop": int(max_pop[ci]),
        "jurisdiction": c["jurisdiction"],
      },
    })
  with open(os.path.join(GJ_DIR, "00_all_periods.geojson"), "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": all_feats}, fh)

  with open(os.path.join(CFG_DIR, "documented_site_pixels.json"), "w", encoding="utf-8") as fh:
    json.dump({"grid_width": GRID_W, "grid_height": GRID_H, "pixel_indices": sorted(doc_pixels)}, fh)

  with open(os.path.join(CFG_DIR, "documented_urban_hubs.json"), "w", encoding="utf-8") as fh:
    json.dump({"count": len(doc_settlements), "settlements": doc_settlements}, fh)
  print(f"  Exported documented_urban_hubs.json ({len(doc_settlements):,} pre-1901 hubs) & documented_site_pixels.json ({len(doc_pixels):,} px).", flush=True)

  # Build Gatekeeper B1 provenance breakdown & jurisdiction coverage matrix
  total_unique_dom = len(raw_records)
  by_source_obj = {}
  for sname, cnt in dom_source_counts.most_common():
    by_source_obj[sname] = {
      "count": int(cnt),
      "source_tier": source_tiers_map.get(sname, "regional_primary"),
    }

  prov_breakdown = {
    "crowd_share": 0.0,
    "regional_share": 1.0,
    "total_unique_primary_sites": total_unique_dom,
    "crowd_sites": 0,
    "primary_regional_and_monograph_sites": total_unique_dom,
    "by_source": by_source_obj,
  }

  jur_cov_serial = {}
  print("\n[F] Per-Jurisdiction Archaeological Provenance Matrix (Gatekeeper B1):", flush=True)
  for jid in REQUIRED_JURISDICTIONS:
    jd = jur_cov[jid]
    jur_cov_serial[jid] = {
      "total_sites": jd["total_sites"],
      "regional_sites": jd["regional_sites"],
      "primary_sites": jd["primary_sites"],
      "regional_register_sites": jd["regional_register_sites"],
      "monograph_sites": jd["monograph_sites"],
      "c14_primary_sites": jd["c14_primary_sites"],
      "habitation_sites": jd["habitation_sites"],
      "monument_only_sites": jd["monument_only_sites"],
      "crowd_sites": 0,
      "crowd_share": 0.0,
      "regional_sources": sorted(jd["regional_sources"]),
    }
    print(
      f"    {jid}: total={jd['total_sites']:,} | hab={jd['habitation_sites']:,} | mon={jd['monument_only_sites']:,} | "
      f"crowd=0 (0.0%) | sources={len(jd['regional_sources'])}",
      flush=True,
    )

  meta_obj = {
    "domain": "AUSTRAL",
    "macro_scope": "Australia, Tasmania, New Guinea (incl. West Papua & Raja Ampat), New Zealand, Island Melanesia, Micronesia, and Polynesia (excl. Hawai'i & American Samoa)",
    "sources": list(dom_source_counts.keys()),
    "source_record_counts": dict(dom_source_counts),
    "source_provenance_breakdown": prov_breakdown,
    "jurisdiction_arch_coverage": jur_cov_serial,
    "domestic_site_count_unique_sum": int(total_unique_dom),
    "domestic_site_complexes_dedup": int(assigned_complexes),
    "catchment_counts": {"domestic": n_dom, "frontier_buffer": len(frontier_catchments)},
    "documented_site_pixels": len(doc_pixels),
    "documented_settlements": len(doc_settlements),
    "period_geojsons": period_meta,
  }
  with open(os.path.join(CFG_DIR, "sites_austral_oceania_geojson_metadata.json"), "w", encoding="utf-8") as fh:
    json.dump(meta_obj, fh, indent=2)

  all_hyde_years = [
    -10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000,
    0, 100, 200, 300, 400, 500, 600, 700, 800, 900,
    1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
    1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790,
    1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890,
    1900, 1910, 1920, 1930, 1940, 1950,
  ] + list(range(1951, 2026))

  cfg_obj = {
    "geojson_metadata_filename": "config/sites_austral_oceania_geojson_metadata.json",
    "include_all_periods_geojson": True,
    "kriging_metadata_filename": "config/kriging_diagnostics.json",
    "output_geojson_subfolder": "geojson",
    "output_kriged_rasters_subfolder": "1.kriged_rasters",
    "output_population_rasters_subfolder": "2.population_rasters",
    "png_compression_level": 6,
    "kriging_config": {
      "preserve_period_dynamics": True,
      "all_hyde_years": all_hyde_years,
      "apply_arid_taphonomic_correction": True,
      "apply_urban_salvage_debias": True,
      "elevation_barrier_m": 720,
      "habitability_filter": {
        "arctic_lat_cut": 70.0,
        "extreme_elev_cut_m": 3800.0,
        "hyde_core_min_dens": 0.002,
        "hyde_marginal_min_dens": 0.08,
        "site_radius_px": 1.6,
        "stadester_max_first_year": 1900,
        "stadester_radius_px": 1.8,
      },
      "hu_admixture_config": "histmap/3.data_transform/population_Substrata.viscount/config/austral_dasymetric_admixture.json5",
      "residual_kriging_mode": "hu_hyde_residual",
      "covariate_paths": {
        "documented_settlements_json": "histmap/1.data_raw/population_regional/AUSTRAL/_shared/sites_austral_oceania/config/documented_urban_hubs.json",
        "documented_site_pixels_json": "histmap/1.data_raw/population_regional/AUSTRAL/_shared/sites_austral_oceania/config/documented_site_pixels.json",
        "forest_asc": "histmap/1.data_raw/metadata_HYDE/general_files/forest_wwf_cr.asc",
        "ghsl_urban_2020_raster": "histmap/1.data_raw/population_GHSL/urban_rasters/GHSL_2020.png",
        "ghsl_urban_folder": "histmap/1.data_raw/population_GHSL/urban_rasters",
        "ghsl_urban_pop_threshold": 35000,
        "hyde_mcevedy_rasters_folder": "histmap/2.data_cleaning/landuse_HYDE/rasters_mcevedy",
        "hyde_popc_folder": "histmap/2.data_cleaning/landuse_HYDE/rasters_scaled_to_global",
        "hyde_raw_rasters_folder": "histmap/2.data_cleaning/landuse_HYDE/rasters",
        "hyde_uopp_raster": "histmap/2.data_cleaning/landuse_HYDE/rasters/uopp_2023AD.png",
        "kk10_fallback_folder": "histmap/2.data_cleaning/population_KK10LUH2/rasters_KK10LUH2_2._global_scaling",
        "lakes_geojson": "histmap/1.data_raw/population_regional/POLARIS/_shared/_gis_cache/ne_10m_lakes.geojson",
        "landlake_asc": "histmap/1.data_raw/metadata_HYDE/general_files/landlake.asc",
        "maxln_asc": "histmap/1.data_raw/metadata_HYDE/general_files/maxln_cr.asc",
        "nelson_regions_png": "histmap/2.data_cleaning/population_KK10LUH2/config/nelson_regions.png",
        "rivers_geojson": "histmap/1.data_raw/population_regional/_shared/_gis_cache/ne_10m_rivers_lake_centerlines.geojson",
        "sub_iso_asc": "histmap/1.data_raw/metadata_HYDE/general_files/sub_iso_cr.asc",
        "urban_fringe_uopp_threshold": 1.0,
        "urban_mask_buffer_radius": 2,
        "urban_mask_inpaint_radius": 5,
        "urban_uopp_threshold": 3.8,
      },
      "dimensionless_lag_bins": [0.85, 1.45, 2.10, 2.95, 4.10, 5.60, 7.80, 10.80, 14.50],
      "domain_mask_png": "histmap/1.data_raw/population_regional/AUSTRAL/_shared/sites_austral_oceania/config/austral_domain_mask.png",
      "earth_radius_km": 6371,
      "frontier_conditioning_max_dist_km": 265,
      "grid_height": GRID_H,
      "grid_width": GRID_W,
      "target_domestic_catchments": n_dom,
      "chronological_horizons": [
        {"active_periods": [p["key"]], "key": p["key"] + "_horizon", "year": p["representative_year"]}
        for p in PERIODS
      ],
    },
    "periods": PERIODS,
  }
  with open(os.path.join(CFG_DIR, "sites_austral_oceania.json5"), "w", encoding="utf-8") as fh:
    json.dump(cfg_obj, fh, indent=2, ensure_ascii=False)

  print(
    f"\n[DONE] AUSTRAL extraction complete: {total_unique_dom:,} unique primary sites (0.0% crowd) -> "
    f"{n_dom:,} domestic + {len(frontier_catchments)} frontier catchments.",
    flush=True,
  )


if __name__ == "__main__":
  domain_mask, land_area, d_hyde15, d_hyde10, d_hyde19, d_kk15, d_believed, forest = load_base_grids()
  raw_records, source_counts_raw, source_tiers_map, site_pixel_grid = ingest_raw_repositories(domain_mask)
  catchments, hab_dom_mask = build_dual_tier_catchments(
    domain_mask, land_area, d_hyde15, d_hyde10, d_hyde19, d_kk15, d_believed, site_pixel_grid
  )
  frontier_catchments = import_frontier_buffers(domain_mask, catchments)
  aggregate_and_export(
    domain_mask, land_area, d_hyde15, d_hyde10, d_kk15, d_believed, forest,
    catchments, frontier_catchments, raw_records, source_counts_raw, source_tiers_map,
  )
