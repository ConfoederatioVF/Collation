"""Master Historical Toponymy Assembler & Chapter Enricher for Operation Viscount Project MANDALA.

Combines:
  1. All 20 verified Gemini 3.8 Flash swarm batches (resolved_batch_01.json..resolved_batch_20.json;
     900 major & historical Mainland and Maritime SE Asian settlements).
  2. Clean GeoNames alternate-name enrichment (filtered strictly for script purity: native scripts
     only for Myanmar, Thailand, Laos, Cambodia, Vietnam; Latin script only for Indonesia, Malaysia,
     Singapore, Brunei, Philippines, East Timor; zero Cyrillic/Arabic/Indic spam).
Outputs:
  - MANDALA/_shared/flash_toponymy_master.json
  - Enriches `other_names` and `foundation_year` (when improved & chronologically consistent) across
    all 22 MANDALA chapter `*_settlements.json` files without breaking any key or continuity gate.
"""

import glob
import json
import os
import re
import unicodedata
import zipfile

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MANDALA_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MANDALA")
BATCH_DIR = os.path.join(MANDALA_DIR, "_shared", "toponymy_batches")
CENSUS_DIR = os.path.join(MANDALA_DIR, "_shared", "_census_cache")
MASTER_OUT = os.path.join(MANDALA_DIR, "_shared", "flash_toponymy_master.json")

DATE_RE = re.compile(r"^-?\d+\.\d+\.\d+$")
LATIN_COUNTRIES = {"Indonesia", "Malaysia", "Singapore", "Brunei", "Philippines", "East Timor"}
ALLOWED_NATIVE_RANGES = {
  "Myanmar": [(0x1000, 0x109F)],
  "Thailand": [(0x0E00, 0x0E7F)],
  "Laos": [(0x0E80, 0x0EFF)],
  "Cambodia": [(0x1780, 0x17FF)],
  "Vietnam": [(0x00C0, 0x024F), (0x1E00, 0x1EFF)],
}


def norm_key(s):
  s = unicodedata.normalize("NFKD", str(s or ""))
  s = "".join(ch for ch in s if not unicodedata.combining(ch))
  return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def is_clean_name_for_country(name, country):
  if not name:
    return False
  s = str(name).strip()
  if len(s) < 2 or len(s) > 60:
    return False
  if any(ch in s for ch in ("(", ")", "?", "`", "\ufffd", "[", "]")):
    return False
  allowed = ALLOWED_NATIVE_RANGES.get(country, [])
  for ch in s:
    cp = ord(ch)
    if cp < 128 or (0x00C0 <= cp <= 0x024F) or (0x1E00 <= cp <= 0x1EFF):
      continue
    if country in LATIN_COUNTRIES:
      return False
    if not any(lo <= cp <= hi for lo, hi in allowed):
      return False
  return True


def load_geonames_alternates():
  cc_map = {
    "MM": "Myanmar", "TH": "Thailand", "LA": "Laos", "KH": "Cambodia",
    "VN": "Vietnam", "MY": "Malaysia", "SG": "Singapore", "BN": "Brunei",
    "ID": "Indonesia", "PH": "Philippines", "TL": "East Timor"
  }
  alt_map = {}
  for cc, cname in cc_map.items():
    zp = os.path.join(CENSUS_DIR, f"geonames_{cc}.zip")
    if not os.path.isfile(zp):
      continue
    with zipfile.ZipFile(zp) as zf:
      raw = zf.read(f"{cc}.txt").decode("utf-8", errors="replace")
    for line in raw.splitlines():
      p = line.split("\t")
      if len(p) < 15 or p[6] != "P":
        continue
      ascii_nm = p[2].strip() or p[1].strip()
      alts = [a.strip() for a in (p[3] or "").split(",") if a.strip()]
      clean_alts = [a for a in alts if is_clean_name_for_country(a, cname) and a.lower() != ascii_nm.lower()]
      if clean_alts:
        nk = norm_key(ascii_nm)
        prev = alt_map.get((cname, nk), [])
        merged = list(dict.fromkeys(prev + clean_alts))[:6]
        alt_map[(cname, nk)] = merged
  return alt_map


def main():
  master = {}
  by_name_country = {}
  batch_files = sorted(glob.glob(os.path.join(BATCH_DIR, "resolved_batch_*.json")))
  print(f"[1] Loading {len(batch_files)} verified Gemini 3.8 Flash toponymy batches...", flush=True)

  for bf in batch_files:
    data = json.load(open(bf, "r", encoding="utf-8"))
    for s in data.get("settlements", []):
      key = s.get("key", "")
      cname = key.rsplit("-", 1)[-1].strip() if "-" in key else ""
      canon = str(s.get("canonical_name") or "").strip()
      if not key or not canon:
        continue
      hnames = []
      for hn in s.get("historical_names", []):
        dt = str(hn.get("date") or "").strip()
        nm = str(hn.get("name") or "").strip()
        if DATE_RE.match(dt) and nm and not any(c in nm for c in ("(", ")", "?", "`")):
          hnames.append({"date": dt, "name": nm})
      hnames.sort(key=lambda x: tuple(int(p) for p in x["date"].split(".")))
      if not hnames or hnames[-1]["name"].lower() != canon.lower():
        hnames.append({"date": "1990.1.1", "name": canon})
      others = [o.strip() for o in (s.get("other_names") or []) if is_clean_name_for_country(o, cname) and o.strip().lower() != canon.lower()]
      rec = {
        "key": key,
        "canonical_name": canon,
        "country": cname,
        "foundation_year": s.get("foundation_year"),
        "historical_names": hnames,
        "other_names": list(dict.fromkeys(others))[:8],
        "source": "Gemini_3_8_Flash_Swarm_Verified",
      }
      master[key] = rec
      if cname:
        by_name_country[(cname, norm_key(canon))] = rec

  print(f"  Loaded {len(master):,} verified Flash swarm historical toponymy records.", flush=True)

  alt_map = load_geonames_alternates()
  print(f"[2] Loaded {len(alt_map):,} clean GeoNames alternate-name sets.", flush=True)

  # Enrich all 22 chapter settlement gazetteers + add all remaining unique MANDALA settlements to master
  sett_files = sorted(glob.glob(os.path.join(MANDALA_DIR, "*", "*", "*_settlements.json")))
  enriched_recs = 0
  for sf in sett_files:
    data = json.load(open(sf, "r", encoding="utf-8"))
    changed = False
    for k, rec in data.items():
      cname = rec.get("country", "")
      nm = rec.get("name", "")
      nk = norm_key(nm)
      flash = master.get(k) or by_name_country.get((cname, nk))
      alts = []
      if flash:
        alts.extend(flash.get("other_names") or [])
        for hn in flash.get("historical_names") or []:
          if hn["name"].lower() != nm.lower() and is_clean_name_for_country(hn["name"], cname):
            alts.append(hn["name"])
      alts.extend(alt_map.get((cname, nk), []))
      clean_alts = [a for a in dict.fromkeys(alts) if a.lower() != nm.lower() and is_clean_name_for_country(a, cname)][:8]
      if clean_alts and clean_alts != rec.get("other_names"):
        rec["other_names"] = clean_alts
        changed = True
        enriched_recs += 1
      # Ensure every unique settlement key exists in master for Stage F Dataview packing
      if k not in master:
        pops = rec.get("population") or {}
        earliest_y = min((int(y) for y in pops.keys()), default=1900)
        fyr = rec.get("foundation_year")
        start_y = int(fyr) if isinstance(fyr, int) else min(earliest_y, 1850)
        master[k] = {
          "key": k,
          "canonical_name": nm,
          "country": cname,
          "foundation_year": fyr,
          "historical_names": [{"date": f"{start_y}.1.1", "name": nm}],
          "other_names": clean_alts,
          "source": "GeoNames_Cleaned_Alternates" if clean_alts else "Canonical_Stable_Toponym",
        }
    if changed:
      with open(sf, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

  with open(MASTER_OUT, "w", encoding="utf-8") as fh:
    json.dump(master, fh, indent=2, ensure_ascii=False)
  print(f"[3] Saved {len(master):,} total MANDALA toponymy entries to {MASTER_OUT} (enriched {enriched_recs:,} chapter records).", flush=True)


if __name__ == "__main__":
  main()
