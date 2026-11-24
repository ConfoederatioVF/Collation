# -*- coding: utf-8 -*-
"""
Operation Viscount — Project JAGUAR
Stage C Enrichment Parser 1: Official INEGI Archivo Histórico de Localidades (AHL 1900-2020).

Parses all 32 Mexican federal entities inside `mexico_inegi_ahl_nacional.zip`:
  - `AHLxxHabitantes.csv`: Official INEGI census populations (1900, 1910, 1921, 1930, 1940,
    1950, 1960, 1970, 1980, 1990, 1995, 2000, 2005, 2010, 2020)
  - `AHLxxMaestro.csv`: Official ITRF2008/WGS84 DMS coordinates, altitude, urban/rural type
  - `AHLxxMovimientos.csv`: Official current & historical locality names (for Stage F toponymy!)
  - `AHLxxRes_hist.csv`: Historical monograph dates for cabeceras municipales

Enforces Municipal-Limits Non-Decomposition:
  - ENT == '09' (Ciudad de México / Distrito Federal) is strictly consolidated into ONE unified
    city_proper record (`090000000`) using official INEGI ITER/EHM totals.
  - Extra-municipal suburbs in ZMVM (Estado de México + Tizayuca), ZMG, and ZMM are preserved
    as distinct records tagged `population_scope="suburb"` + `metro_parent`.
"""

import csv
import io
import json
import os
import re
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
RAW_AHL_ZIP = os.path.join(SHARED_DIR, "settlement_sources/raw/mexico_inegi_ahl_nacional.zip")
ITER_CSV = os.path.join(SHARED_DIR, "settlement_sources/parsed/mexico_inegi_iter_1990_2020_consolidated.csv")
OUT_CSV = os.path.join(SHARED_DIR, "settlement_sources/parsed/mexico_inegi_ahl_1900_2020_enriched.csv")
OUT_HIST_NAMES = os.path.join(SHARED_DIR, "settlement_sources/parsed/mexico_ahl_historical_names.json")
OUT_SUMMARY = os.path.join(SHARED_DIR, "settlement_sources/parsed/_mexico_ahl_summary.json")

VALID_YEARS = ("1900", "1910", "1921", "1930", "1940", "1950", "1960", "1970", "1980", "1990", "1995", "2000", "2005", "2010", "2020")

ZMVM_SUBURB_MUNS = {
  "15002","15011","15013","15020","15023","15024","15025","15028","15029","15030","15031",
  "15033","15035","15037","15039","15044","15053","15057","15058","15059","15060","15068",
  "15069","15070","15075","15081","15083","15084","15091","15092","15093","15095","15099",
  "15100","15103","15104","15108","15109","15120","15121","15122","15125","13069",
}
ZMG_SUBURB_MUNS = {"14120", "14098", "14101", "14097", "14070", "14044", "14051"}
ZMM_SUBURB_MUNS = {"19026", "19006", "19046", "19021", "19048", "19019", "19018", "19031", "19009", "19045"}


def dms_to_dec(arg0_val, is_lon=False):
  """Converts INEGI DMS strings (`21°52'47.362"N`) into signed decimal degrees."""
  s = str(arg0_val or "").strip().strip('"').replace('""', '"').replace(" ", "")
  if not s or s in ("*", "N/D", "ND"):
    return None
  m = re.match(r"(\d+)[°º](\d+)'([\d\.]+)\"?([NSEW])?", s)
  if m:
    deg = float(m.group(1)) + float(m.group(2)) / 60.0 + float(m.group(3)) / 3600.0
    hemi = m.group(4) or ("W" if is_lon else "N")
    if hemi in ("S", "W") or (is_lon and deg > 0):
      deg = -abs(deg)
    return round(deg, 5)
  try:
    v = float(s)
    if is_lon and v > 0:
      v = -v
    if (is_lon and -119.0 <= v <= -86.0) or (not is_lon and 14.0 <= v <= 33.0):
      return round(v, 5)
  except ValueError:
    pass
  return None


def clean_loc_name(arg0_raw):
  """Cleans INEGI AHL locality name (strips '(Cab.)' and parenthetical codes)."""
  s = str(arg0_raw or "").strip()
  s = re.sub(r"\s*\(Cab\.?\)", "", s, flags=re.I)
  s = re.sub(r"\s*\([^)]*\)", "", s)
  s = re.sub(r"\s*\[[^\]]*\]", "", s)
  s = s.replace("?", "").replace("`", "").strip(" ,;:-")
  return re.sub(r"\s+", " ", s)


def main():
  #Load existing unified CDMX record from ITER consolidated CSV
  cdmx_iter_pops = {}
  if os.path.exists(ITER_CSV):
    with open(ITER_CSV, encoding="utf-8-sig") as fh:
      for row in csv.DictReader(fh):
        if row.get("cvegeo") == "090000000":
          for yr in ("1990", "2000", "2010", "2020"):
            v = str(row.get(f"pop_{yr}") or "").strip()
            if v.isdigit() and int(v) > 0:
              cdmx_iter_pops[yr] = int(v)
          break

  records = []
  hist_name_map = {}
  year_totals = {y: 0 for y in VALID_YEARS}
  cdmx_ahl_sum = {y: 0 for y in VALID_YEARS}
  total_scanned = 0

  with zipfile.ZipFile(RAW_AHL_ZIP) as zmaster:
    for st_zip_name in sorted(zmaster.namelist()):
      if not st_zip_name.lower().endswith(".zip"):
        continue
      with zipfile.ZipFile(io.BytesIO(zmaster.read(st_zip_name))) as zst:
        names = zst.namelist()
        hab_fn = next((n for n in names if "habitantes" in n.lower()), None)
        mae_fn = next((n for n in names if "maestro" in n.lower()), None)
        mov_fn = next((n for n in names if "movimientos" in n.lower()), None)
        if not hab_fn or not mae_fn:
          continue

        #1. Parse Habitantes (cve -> {year: pop})
        pops_by_cve = {}
        with zst.open(hab_fn) as fh:
          for row in csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1", errors="replace")):
            cve = (row.get("CVE_GEOEST") or "").strip().zfill(9)
            yr = (row.get("EVE_CENSAL") or "").strip()
            p_s = (row.get("TOT_HAB") or "").replace(",", "").replace(" ", "").strip()
            if yr not in VALID_YEARS or not p_s.isdigit():
              continue
            pv = int(p_s)
            if pv <= 0:
              continue
            if cve.startswith("09"):
              cdmx_ahl_sum[yr] += pv
              continue
            pm = pops_by_cve.setdefault(cve, {})
            if yr not in pm or pv > pm[yr]:
              pm[yr] = pv

        #Filter cves to keep BEFORE reading full movements:
        #ALL cabeceras municipales (loc == '0001') OR max_pop >= 500 in ANY census 1900-2020
        #OR inhabited in 1900-1950 with max_pop >= 300 (preserves rich 1900-1950 village network!)
        keep_cves = {}
        for cve, pm in pops_by_cve.items():
          total_scanned += 1
          mx = max(pm.values())
          is_cab = cve.endswith("0001")
          has_early = any(y in pm for y in ("1900", "1910", "1921", "1930", "1940"))
          if is_cab or mx >= 500 or (has_early and mx >= 350):
            keep_cves[cve] = (pm, mx, is_cab)

        if not keep_cves:
          continue

        #2. Parse Maestro (coords, state, mun, tipo)
        meta_by_cve = {}
        with zst.open(mae_fn) as fh:
          for row in csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1", errors="replace")):
            cve = (row.get("CVE_GEOEST") or "").strip().zfill(9)
            if cve not in keep_cves:
              continue
            lat = dms_to_dec(row.get("LATITUD"), is_lon=False)
            lon = dms_to_dec(row.get("LONGITUD"), is_lon=True)
            if lat is None or lon is None:
              continue
            if not (14.3 <= lat <= 32.8 and -118.5 <= lon <= -86.5):
              continue
            meta_by_cve[cve] = {
              "lat": lat,
              "lon": lon,
              "nom_ent": (row.get("NOMBRE_EDO") or "").strip(),
              "nom_mun": (row.get("NOMBRE_MUN") or "").strip(),
              "tipo": (row.get("TIPO") or "").strip(),
            }

        #3. Parse Movimientos (latest official name + chronological historical names!)
        latest_name = {}
        all_hist_names = {}
        if mov_fn:
          with zst.open(mov_fn) as fh:
            for row in csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1", errors="replace")):
              cve = (row.get("CVE_GEOEST") or "").strip().zfill(9)
              if cve not in meta_by_cve:
                continue
              idx_s = (row.get("INDICE") or "").strip()
              idx = int(idx_s) if idx_s.isdigit() else 0
              raw_nm = (row.get("NOM_LOC") or "").strip()
              clean_nm = clean_loc_name(raw_nm)
              if not clean_nm or len(clean_nm) < 2 or clean_nm.isdigit():
                continue
              prev = latest_name.get(cve)
              if prev is None or idx > prev[0]:
                latest_name[cve] = (idx, clean_nm)
              #Record distinct historical names if any
              ori = (row.get("ORI_MODIF") or "")
              ym = re.search(r"\b(1[89]\d\d|20[0-2]\d)\b", ori)
              all_hist_names.setdefault(cve, []).append((idx, clean_nm, int(ym.group(1)) if ym else None))

        #4. Emit consolidated records for this state
        for cve, meta in meta_by_cve.items():
          pm, mx, is_cab = keep_cves[cve]
          nm = latest_name[cve][1] if cve in latest_name else clean_loc_name(meta["nom_mun"])
          if not nm or len(nm) < 2 or nm.isdigit():
            continue

          ent = cve[:2]
          mun = cve[2:5]
          loc = cve[5:9]
          entmun = f"{ent}{mun}"
          scope = "city_proper"
          metro_parent = ""
          if entmun in ZMVM_SUBURB_MUNS:
            scope = "suburb"
            metro_parent = "Ciudad de México"
          elif entmun in ZMG_SUBURB_MUNS:
            scope = "suburb"
            metro_parent = "Guadalajara"
          elif entmun in ZMM_SUBURB_MUNS:
            scope = "suburb"
            metro_parent = "Monterrey"

          rec = {
            "cvegeo": cve,
            "ent": ent,
            "nom_ent": meta["nom_ent"],
            "mun": mun,
            "nom_mun": meta["nom_mun"],
            "loc": loc,
            "nom_loc": nm,
            "is_cabecera_municipal": 1 if is_cab else 0,
            "population_scope": scope,
            "metro_parent": metro_parent,
            "lat": meta["lat"],
            "lon": meta["lon"],
            "max_pop": mx,
          }
          for y in VALID_YEARS:
            v = pm.get(y, "")
            rec[f"pop_{y}"] = v
            if v:
              year_totals[y] += 1
          records.append(rec)

          #Store distinct historical names if locality ever changed name
          hlist = all_hist_names.get(cve, [])
          distinct_nms = []
          seen_low = set()
          for _, hnm, hyr in sorted(hlist, key=lambda x: x[0]):
            low = hnm.lower()
            if low not in seen_low:
              seen_low.add(low)
              distinct_nms.append({"name": hnm, "year": hyr})
          if len(distinct_nms) > 1:
            hist_name_map[cve] = distinct_nms

  #Add unified Ciudad de Mexico record (prefer official CDMX entity totals for 1990-2020, AHL sum for 1900-1980)
  cdmx_rec = {
    "cvegeo": "090000000",
    "ent": "09",
    "nom_ent": "Ciudad de México",
    "mun": "000",
    "nom_mun": "Ciudad de México (16 alcaldías unified)",
    "loc": "0000",
    "nom_loc": "Ciudad de México",
    "is_cabecera_municipal": 1,
    "population_scope": "city_proper",
    "metro_parent": "Ciudad de México",
    "lat": 19.43261,
    "lon": -99.13321,
    "max_pop": 0,
  }
  for y in VALID_YEARS:
    val = cdmx_iter_pops.get(y) or cdmx_ahl_sum.get(y) or ""
    cdmx_rec[f"pop_{y}"] = val
    if val:
      year_totals[y] += 1
      if int(val) > cdmx_rec["max_pop"]:
        cdmx_rec["max_pop"] = int(val)
  records.insert(0, cdmx_rec)
  records.sort(key=lambda r: -int(r["max_pop"]))

  fieldnames = [
    "cvegeo", "ent", "nom_ent", "mun", "nom_mun", "loc", "nom_loc",
    "is_cabecera_municipal", "population_scope", "metro_parent", "lat", "lon", "max_pop"
  ] + [f"pop_{y}" for y in VALID_YEARS]

  with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(records)

  with open(OUT_HIST_NAMES, "w", encoding="utf-8") as fh:
    json.dump(hist_name_map, fh, indent=2, ensure_ascii=False)

  summary = {
    "total_raw_ahl_localities_scanned": total_scanned,
    "enriched_localities_emitted": len(records),
    "historical_name_changes_captured": len(hist_name_map),
    "counts_by_census_year": year_totals,
    "cdmx_unified_pops": {y: cdmx_rec[f"pop_{y}"] for y in VALID_YEARS if cdmx_rec[f"pop_{y}"]},
  }
  with open(OUT_SUMMARY, "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2, ensure_ascii=False)

  print(f"INEGI AHL 1900-2020 ENRICHED: {len(records):,} Mexican settlements (scanned {total_scanned:,}, name-change histories={len(hist_name_map):,})")
  for y in VALID_YEARS:
    print(f"  {y}: {year_totals[y]:6,}")


if __name__ == "__main__":
  main()
