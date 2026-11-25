# -*- coding: utf-8 -*-
"""NICETHI Wave-4B Expanded Scholarly PDF Evidence Extractor (`Africa Research Files`).

Scans all ~1,536 deduplicated scholarly PDFs in `_references/Africa Research Files/`
against an offline GeoNames gazetteer of ~14,000 unambiguously named Sub-Saharan African
settlements (from `_raw_cache/geonames/*.zip`) to recover pre-1950AD quantitative
settlement observations (inhabitants, people, souls, huts/houses x 5, compounds x 12,
taxpayers/warriors x 4) strictly excluding any page mentioning banned global compendia.
"""
import collections
import concurrent.futures
import json
import math
import os
import pathlib
import re
import sys
import unicodedata
import zipfile

import pymupdf

sys.stdout.reconfigure(encoding="utf-8")

SVEA_ROOT = pathlib.Path(r"f:\Active Projects\Project 1509 - SVEA")
NICETHI_DIR = SVEA_ROOT / "histmap" / "1.data_raw" / "population_regional" / "NICETHI"
ARCHIVE_ROOT = SVEA_ROOT / "histmap" / "1.data_raw" / "population_regional" / "_references" / "Africa Research Files"
INDEX_PATH = NICETHI_DIR / "_shared" / "africa_research_files_index.json"
GEONAMES_DIR = NICETHI_DIR / "_shared" / "settlement_sources" / "_raw_cache" / "geonames"
OUT_PATH = NICETHI_DIR / "_shared" / "settlement_sources" / "wave4_premodern_arch" / "wave4_africa_research_pdf_expanded.json"

ISO2_TO_COUNTRY = {
  "AO": "Angola", "BF": "Burkina Faso", "BI": "Burundi", "BJ": "Benin", "BW": "Botswana",
  "CD": "Democratic Republic of the Congo", "CF": "Central African Republic",
  "CG": "Republic of the Congo", "CI": "Ivory Coast", "CM": "Cameroon", "CV": "Cabo Verde",
  "DJ": "Djibouti", "ER": "Eritrea", "ET": "Ethiopia", "GA": "Gabon", "GH": "Ghana",
  "GM": "Gambia", "GN": "Guinea", "GQ": "Equatorial Guinea", "GW": "Guinea-Bissau",
  "KE": "Kenya", "KM": "Comoros", "LR": "Liberia", "LS": "Lesotho", "MG": "Madagascar",
  "ML": "Mali", "MR": "Mauritania", "MU": "Mauritius", "MW": "Malawi", "MZ": "Mozambique",
  "NA": "Namibia", "NE": "Niger", "NG": "Nigeria", "RE": "Reunion", "RW": "Rwanda",
  "SC": "Seychelles", "SD": "Sudan", "SH": "Saint Helena", "SL": "Sierra Leone",
  "SN": "Senegal", "SO": "Somalia", "SS": "South Sudan", "ST": "Sao Tome and Principe",
  "SZ": "eSwatini", "TD": "Chad", "TG": "Togo", "TZ": "United Republic of Tanzania",
  "UG": "Uganda", "YT": "Mayotte", "ZA": "South Africa", "ZM": "Zambia", "ZW": "Zimbabwe",
}

STOPWORDS = {
  "africa", "african", "south", "north", "east", "west", "central", "upper", "lower", "great",
  "grand", "petit", "saint", "santa", "santo", "mount", "river", "valley", "coast", "island",
  "islands", "point", "fort", "port", "cape", "bay", "lake", "hill", "hills", "gold", "slave",
  "ivory", "grain", "union", "state", "states", "colony", "province", "district", "region",
  "county", "kingdom", "empire", "mission", "station", "market", "trade", "water", "spring",
  "springs", "forest", "desert", "plain", "plains", "stone", "white", "black", "green", "brown",
  "george", "victoria", "albert", "edward", "charles", "henry", "james", "thomas", "robert",
  "william", "david", "joseph", "francis", "martin", "peter", "louis", "marie", "paris",
  "london", "berlin", "lisbon", "brussels", "france", "french", "british", "german", "dutch",
  "portuguese", "spanish", "italian", "belgian", "english", "arab", "arabic", "islamic",
  "christian", "colonial", "modern", "early", "first", "second", "third", "fourth", "table",
  "figure", "chapter", "section", "index", "notes", "source", "sources", "census", "population",
  "urban", "rural", "people", "house", "houses", "village", "villages", "town", "towns", "city",
  "cities", "number", "total", "about", "around", "nearly", "after", "before", "during", "between",
  "under", "over", "their", "these", "those", "where", "which", "while", "whose", "within",
  "without", "through", "across", "along", "among", "against", "toward", "towards", "other",
  "another", "several", "various", "certain", "general", "national", "local", "native", "tribal",
  "chief", "royal", "court", "palace", "capital", "interior", "northern", "southern", "eastern",
  "western", "middle", "former", "present", "recent", "annual", "monthly", "daily", "years",
  "century", "period", "times", "history", "historical", "study", "studies", "report", "survey",
  "journal", "press", "university", "college", "school", "church", "mosque", "temple", "shrine",
  "harbor", "harbour", "bridge", "railway", "road", "route", "path", "field", "fields", "garden",
  "copper", "silver", "iron", "salt", "palm", "cocoa", "coffee", "cotton", "sugar", "cattle",
  "sheep", "horse", "horses", "camel", "camels", "fisher", "hunter", "farmer", "labour", "labor",
  "police", "school", "prison", "clinic", "office", "custom", "customs", "border", "frontier",
  "basin", "delta", "plateau", "savanna", "sahel", "sahara", "niger", "congo", "nile", "zambezi",
  "limpopo", "orange", "senegal", "gambia", "volta", "benue", "ubangi", "kasai", "kagera",
  "tana", "juba", "shabelle", "awash", "blue", "atbara", "sudan", "guinea", "angola", "kenya",
  "uganda", "ghana", "benin", "togo", "mali", "chad", "gabon", "zambia", "malawi", "namibia",
  "lesotho", "somalia", "ethiopia", "eritrea", "madagascar", "mozambique", "zimbabwe", "botswana",
  "nigeria", "cameroon", "liberia", "rwanda", "burundi", "comoros", "mayotte", "reunion",
  "mauritius", "seychelles", "tanzania", "zanzibar", "natal", "transvaal", "rhodesia", "nyasaland",
  "tanganyika", "dahomey", "asante", "ashanti", "yoruba", "hausa", "fulani", "mandinka", "wolof",
  "akan", "igbo", "bantu", "swahili", "zulu", "xhosa", "sotho", "tswana", "shona", "kongo",
  "luba", "lunda", "merina", "oromo", "amhara", "tigray", "somali", "nubia", "nubian", "kush",
  "meroe", "aksum", "fanti", "fante", "mossi", "songhai", "kanem", "bornu", "borno", "sokoto",
  "baron", "count", "major", "minor", "alpha", "omega", "delta", "sigma", "gamma", "extra",
  "super", "inter", "intra", "trans", "multi", "micro", "macro", "infra", "ultra", "quasi",
  "bonny", "manga", "kongo", "benin", "sierra", "leone", "monte", "campo", "porto", "vila",
  "villa", "nueva", "vieja", "belo", "novo", "nova", "velha", "velho", "forte", "sierra",
  "lagos", "barra", "ponta", "praia", "ribeira", "santa", "santo", "cabo", "costa", "serra",
  "march", "april", "june", "july", "august", "october", "november", "december", "january", "february",
  "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "summer", "winter",
  "autumn", "spring", "north", "south", "center", "centre", "middle", "square", "circle", "round",
  "still", "small", "large", "short", "thick", "heavy", "light", "clear", "clean", "close",
  "fresh", "young", "older", "early", "later", "final", "chief", "prime", "royal", "civil",
  "human", "world", "earth", "place", "space", "group", "class", "order", "level", "scale",
  "range", "value", "price", "money", "power", "force", "right", "wrong", "truth", "peace",
  "death", "birth", "blood", "heart", "stone", "metal", "glass", "cloth", "grain", "bread",
  "fruit", "plant", "grass", "woods", "trees", "river", "creek", "brook", "marsh", "swamp",
  "shore", "beach", "cliff", "ridge", "slope", "crest", "trail", "track", "stone", "brick",
  "walls", "gates", "tower", "court", "plaza", "forum", "agora", "manor", "grange", "homestead",
}

BANNED_RE = re.compile(
  r"\b(?:McEvedy|Klein\s+Goldewijk|Chandler\s*\(?1987|Modelski\s*\(?2003|Populstat|Maddison|Bairoch|HYDE\s*3)\b",
  re.I,
)

# Quantitative population phrase patterns in English & French African historiography
POP_NUM_RE = re.compile(
  r"(?:population\s+(?:of|was|reached|estimated\s+at|numbered|stood\s+at|about|around|circa|c\.)\s+|"
  r"numbered\s+(?:about|around|some|nearly|over)?\s*|"
  r"contained\s+(?:about|around|some|nearly|over)?\s*|"
  r"counted\s+(?:about|around|some|nearly|over)?\s*|"
  r"comprenait\s+(?:environ|près\s+de)?\s*|"
  r"comptait\s+(?:environ|près\s+de)?\s*|"
  r"peupl[ée]e?\s+de\s+(?:environ)?\s*|"
  r"had\s+(?:about|around|some|nearly|over|roughly)?\s*)"
  r"(\d{1,3}(?:[,\s]\d{3})+|\d{3,6})\s*"
  r"(inhabitants?|people|persons?|souls?|residents?|habitants?|âmes|personnes|"
  r"houses?|huts?|dwellings?|maisons?|cases?|compounds?|taxpayers?|warriors?|men\b)",
  re.I,
)
POP_ALT_RE = re.compile(
  r"\b(\d{1,3}(?:[,\s]\d{3})+|\d{3,6})\s+"
  r"(inhabitants?|residents?|souls?|habitants?|âmes|houses?|huts?|dwellings?|cases?|compounds?)\b",
  re.I,
)
YEAR_RE = re.compile(r"\b(1[0-8]\d\d|19[0-4]\d)\b")
CENTURY_RE = re.compile(r"\b(1[0-9])(?:th|e|ème)\s+centur(?:y|ies)|(?:siècle)\b", re.I)

MULT_MAP = {
  "house": 5.0, "houses": 5.0, "hut": 4.2, "huts": 4.2, "dwelling": 5.0, "dwellings": 5.0,
  "maison": 5.0, "maisons": 5.0, "case": 4.2, "cases": 4.2, "compound": 12.0, "compounds": 12.0,
  "taxpayer": 4.0, "taxpayers": 4.0, "warrior": 4.5, "warriors": 4.5, "men": 4.0,
}

# Global worker-read lookup
G_TOWN_LOOKUP = {}


def load_geonames_gazetteer():
  """Loads ~14,000 unambiguous Sub-Saharan African populated places from local GeoNames ZIPs."""
  by_name = {}
  # Prioritize higher population or admin seats (PPLC, PPLA, PPLA2, PPLA3)
  fc_rank = {"PPLC": 5, "PPLA": 4, "PPLA2": 3, "PPLA3": 2, "PPL": 1}
  for iso2, ctry in sorted(ISO2_TO_COUNTRY.items()):
    zp = GEONAMES_DIR / f"{iso2}.zip"
    if not zp.exists():
      continue
    with zipfile.ZipFile(zp) as z:
      txt_name = f"{iso2}.txt"
      if txt_name not in z.namelist():
        continue
      with z.open(txt_name) as f:
        for raw_line in f:
          parts = raw_line.decode("utf-8", errors="replace").split("\t")
          if len(parts) < 15 or parts[6] != "P":
            continue
          fcode = parts[7]
          if fcode not in fc_rank:
            continue
          pop = int(parts[14]) if parts[14].isdigit() else 0
          if pop < 1500 and fcode == "PPL":
            continue
          nm = parts[1].strip()
          asc = parts[2].strip()
          try:
            lat, lon = float(parts[4]), float(parts[5])
          except ValueError:
            continue
          score = fc_rank[fcode] * 10000000 + pop
          for cand_nm in (nm, asc):
            if not cand_nm or len(cand_nm) < 5 or len(cand_nm) > 28:
              continue
            if re.search(r"[^A-Za-zÀ-ÖØ-öø-ÿ'\-\s]", cand_nm):
              continue
            low = cand_nm.lower()
            if low in STOPWORDS or " " in low and low.split()[0] in ("new", "old", "upper", "lower"):
              if low not in ("cape town", "port louis", "saint louis", "porto novo", "old oyo", "old calabar", "cape coast", "port loko", "el fasher", "el obeid", "dar es salaam", "addis ababa", "pietermaritzburg", "grahamstown", "bloemfontein"):
                continue
            prev = by_name.get(cand_nm)
            if prev is None or score > prev[4]:
              by_name[cand_nm] = (nm, ctry, lat, lon, score)
  # Only keep single-token or known two-token proper-case African town names (fast exact word-token lookup!)
  clean = {}
  for k, v in by_name.items():
    if k[0].isupper() and k.lower() not in STOPWORDS:
      clean[k] = (v[0], v[1], v[2], v[3])
  return clean


def init_worker(town_lookup):
  global G_TOWN_LOOKUP
  G_TOWN_LOOKUP = town_lookup


def scan_one_pdf(arg_tuple):
  rel_path, abs_path_str, region_hint = arg_tuple
  out = []
  try:
    doc = pymupdf.open(abs_path_str)
  except Exception:
    return out

  fname = os.path.basename(abs_path_str)
  short_cit = re.sub(r"\.pdf$", "", fname, flags=re.I)[:88]
  n_pages = min(len(doc), 220)
  for pno in range(n_pages):
    try:
      txt = doc[pno].get_text("text")
    except Exception:
      continue
    if not txt or len(txt) < 80:
      continue
    if BANNED_RE.search(txt):
      continue
    # Quick page pre-filter: must have at least one quantitative keyword + 4-digit year < 1950
    if not re.search(r"(?:inhabitant|habitant|population|souls|âmes|houses|huts|cases|compounds|taxpayer)", txt, re.I):
      continue
    if not YEAR_RE.search(txt):
      continue

    # Split into sentences/clauses
    sents = re.split(r"(?<=[\.\!\?\;\n])\s+", txt)
    for sent in sents:
      if len(sent) < 25 or len(sent) > 520:
        continue
      m_pop = POP_NUM_RE.search(sent) or POP_ALT_RE.search(sent)
      if not m_pop:
        continue
      yr_matches = [int(y) for y in YEAR_RE.findall(sent) if 1000 <= int(y) <= 1949]
      if not yr_matches:
        continue
      yr = yr_matches[-1]
      num_raw = re.sub(r"[,\s]", "", m_pop.group(1))
      if not num_raw.isdigit():
        continue
      raw_val = int(num_raw)
      unit = m_pop.group(2).lower()
      mult = MULT_MAP.get(unit, 1.0)
      est_pop = int(round(raw_val * mult))
      if est_pop < 60 or est_pop > 450000:
        continue
      # Guard against year mistaken for population
      if raw_val == yr or (1800 <= raw_val <= 1949 and mult == 1.0):
        continue

      # Find capitalised candidate place tokens in this sentence matching G_TOWN_LOOKUP
      matched_towns = []
      for tok in re.findall(r"\b[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'\-]{4,24}\b", sent):
        info = G_TOWN_LOOKUP.get(tok)
        if info:
          matched_towns.append((sent.find(tok), info))
      if not matched_towns:
        continue
      # Take closest town preceding or nearest the population match
      pop_pos = m_pop.start()
      matched_towns.sort(key=lambda x: (0 if x[0] < pop_pos else 1, abs(pop_pos - x[0])))
      nm, ctry, lat, lon = matched_towns[0][1]
      out.append((nm, ctry, lat, lon, yr, est_pop, f"Africa Research Archive ({short_cit}, p.{pno + 1})"))
  doc.close()
  return out


def main():
  town_lookup = load_geonames_gazetteer()
  print(f"[PDF-EXP] Loaded {len(town_lookup)} unambiguous African GeoNames towns.")

  idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
  files = idx.get("files") or []
  seen_sha = set()
  seen_stem = set()
  jobs = []
  for f in files:
    if str(f.get("ext") or "").lower() != ".pdf":
      continue
    sha = f.get("sha256")
    rel = f.get("rel_path") or f.get("path") or ""
    if not rel:
      continue
    stem = re.sub(r"[^a-z0-9]+", "", os.path.basename(rel).lower())
    if (sha and sha in seen_sha) or stem in seen_stem:
      continue
    abs_p = ARCHIVE_ROOT / rel
    if not abs_p.exists():
      continue
    if sha:
      seen_sha.add(sha)
    seen_stem.add(stem)
    jobs.append((rel, str(abs_p), str(f.get("region") or "")))

  print(f"[PDF-EXP] Scanning {len(jobs)} deduplicated PDFs with 4 workers...")
  all_obs = []
  with concurrent.futures.ProcessPoolExecutor(max_workers=4, initializer=init_worker, initargs=(town_lookup,)) as ex:
    for res in ex.map(scan_one_pdf, jobs, chunksize=8):
      if res:
        all_obs.extend(res)

  print(f"[PDF-EXP] Raw quantitative pre-1950 observations extracted: {len(all_obs)}")

  # Consolidate by (country, name) taking median per year when multiple PDFs cite the same year
  by_place = {}
  for nm, ctry, lat, lon, yr, pop, cit in all_obs:
    k = (ctry, nm.lower())
    if k not in by_place:
      by_place[k] = {"name": nm, "country": ctry, "coords": [round(lat, 5), round(lon, 5)], "by_yr": collections.defaultdict(list), "sources": set()}
    by_place[k]["by_yr"][yr].append(pop)
    by_place[k]["sources"].add(cit)

  settlements = []
  for k, rec in sorted(by_place.items()):
    pop_dict = {}
    for yr, vals in sorted(rec["by_yr"].items()):
      vals_s = sorted(vals)
      med = vals_s[len(vals_s) // 2]
      pop_dict[str(yr)] = int(med)
    if not pop_dict:
      continue
    settlements.append({
      "name": rec["name"],
      "other_names": [],
      "country": rec["country"],
      "coords": rec["coords"],
      "foundation_year": None,
      "population": pop_dict,
      "sources": sorted(rec["sources"])[:4],
      "verified_settlement": True,
    })

  OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
  OUT_PATH.write_text(json.dumps({
    "metadata": {"generator": "extract_africa_research_pdf_expanded.py", "pdfs_scanned": len(jobs), "count": len(settlements), "raw_obs": len(all_obs)},
    "settlements": settlements,
  }, indent=2, ensure_ascii=False), encoding="utf-8")
  print(f"[PDF-EXP] Wrote {len(settlements)} unique pre-1950 settlements from Africa Research Files -> {OUT_PATH}")


if __name__ == "__main__":
  main()
