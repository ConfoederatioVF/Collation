import csv, io, os, time, urllib.request, zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUT_CSV = os.path.join(SHARED_DIR, "settlement_sources/parsed/jaguar_supplemental_geonames_coords.csv")

ISOS = [
  "TT", "VI", "HT", "BS", "TC", "MS", "AI", "BM", "VG", "KY",
  "AW", "CW", "BQ", "SX", "MF", "BL", "GD", "VC", "KN", "AG",
  "DM", "LC", "BB", "JM", "CU", "DO", "PR", "GP", "MQ",
  "PA", "CR", "NI", "HN", "SV", "GT", "BZ"
]

existing = set()
rows = []
if os.path.exists(OUT_CSV):
  with open(OUT_CSV, encoding="utf-8-sig", errors="replace") as fh:
    r = csv.DictReader(fh)
    fieldnames = r.fieldnames
    for row in r:
      rows.append(row)
      existing.add((row.get("iso2", ""), row.get("name", ""), row.get("lat", ""), row.get("lon", "")))
else:
  fieldnames = ["iso2", "name", "asciiname", "lat", "lon", "fclass", "fcode", "geonames_pop_ref"]

hdr = {"User-Agent": "Mozilla/5.0"}
added = 0
for iso in ISOS:
  u = f"https://download.geonames.org/export/dump/{iso}.zip"
  try:
    raw = urllib.request.urlopen(urllib.request.Request(u, headers=hdr), timeout=20).read()
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
      txt_nm = f"{iso}.txt"
      if txt_nm not in zf.namelist():
        continue
      with zf.open(txt_nm) as fh:
        for line in io.TextIOWrapper(fh, encoding="utf-8", errors="replace"):
          parts = line.rstrip("\r\n").split("\t")
          if len(parts) < 15:
            continue
          fclass = parts[6]
          if fclass not in ("P", "A", "L", "T"):
            continue
          nm = parts[1].strip()
          anm = parts[2].strip()
          lat = parts[4].strip()
          lon = parts[5].strip()
          fcode = parts[7].strip()
          pop_ref = parts[14].strip() or "0"
          k = (iso, nm, lat, lon)
          if k in existing:
            continue
          existing.add(k)
          rows.append({
            "iso2": iso, "name": nm, "asciiname": anm,
            "lat": lat, "lon": lon, "fclass": fclass, "fcode": fcode,
            "geonames_pop_ref": pop_ref,
          })
          added += 1
          #Also index alternate names for exact administrative/community geocoding
          alts = [a.strip() for a in parts[3].split(",") if a.strip() and len(a.strip()) >= 3][:4]
          for alt in alts:
            ka = (iso, alt, lat, lon)
            if ka not in existing:
              existing.add(ka)
              rows.append({
                "iso2": iso, "name": alt, "asciiname": alt,
                "lat": lat, "lon": lon, "fclass": fclass, "fcode": fcode,
                "geonames_pop_ref": pop_ref,
              })
              added += 1
    time.sleep(0.1)
  except Exception as e:
    print(f"  WARN {iso}: {e}")

with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
  w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
  w.writeheader()
  w.writerows(rows)
print(f"Expanded GeoNames coords-only reference (0% pop): +{added:,} entries -> total {len(rows):,}")
