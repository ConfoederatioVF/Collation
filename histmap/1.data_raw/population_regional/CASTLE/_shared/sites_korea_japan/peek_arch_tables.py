"""Deep-inspects CSV columns & row counts inside JASOSR, c14db_1.3.0, yayoi_demo, NeolithicKorea, Hanseong_C14, and MLIT P32."""

import csv
import io
import os
import zipfile
import shapefile

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_ARCH = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE", "_shared", "sites_korea_japan", "0.raw_data")


def peek_zip_csv(zfn, member_filter, max_files=6):
  p = os.path.join(RAW_ARCH, zfn)
  with zipfile.ZipFile(p) as zf:
    hits = [i for i in zf.infolist() if member_filter(i.filename) and i.file_size > 1000]
    hits.sort(key=lambda x: -x.file_size)
    print(f"\n=== {zfn} (matching {len(hits)} files) ===")
    for info in hits[:max_files]:
      raw = zf.read(info.filename)
      for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis", "euc-kr"):
        try:
          txt = raw.decode(enc)
          break
        except Exception:
          continue
      else:
        txt = raw.decode("utf-8", errors="replace")
      lines = txt.splitlines()
      rdr = csv.reader(lines[:4])
      rows = list(rdr)
      print(f"  {info.filename} ({len(lines):,} lines, {info.file_size/1e6:.2f} MB)")
      if rows:
        print(f"    cols ({len(rows[0])}): {rows[0][:14]}")
      if len(rows) > 1:
        print(f"    row1: {rows[1][:10]}")


def main():
  peek_zip_csv("gh_kotdijian_JASOSR.zip", lambda n: n.lower().endswith(".csv"), max_files=12)
  peek_zip_csv("gh_ercrema_japan_c14db.zip", lambda n: "c14db_1.3.0.csv" in n or "sitenames" in n, max_files=3)
  peek_zip_csv("gh_ercrema_yayoi_demo.zip", lambda n: n.endswith(".csv"), max_files=5)
  peek_zip_csv("gh_ercrema_NeolithicKoreaDemography.zip", lambda n: "Neolithic_C14" in n, max_files=2)
  peek_zip_csv("gh_ChanToRe_Hanseong_C14.zip", lambda n: "AMS_Master" in n, max_files=2)

  # Inspect MLIT P32 shapefile fields & total record count
  with zipfile.ZipFile(os.path.join(RAW_ARCH, "mlit_P32_14_00_GML.zip")) as zf:
    shps = sorted([n for n in zf.namelist() if n.endswith(".shp")])
    tot = 0
    sample_fields = None
    sample_rec = None
    for sn in shps:
      dbf = sn[:-4] + ".dbf"
      if dbf not in zf.namelist():
        continue
      sf = shapefile.Reader(shp=io.BytesIO(zf.read(sn)), dbf=io.BytesIO(zf.read(dbf)), encoding="cp932", encodingErrors="replace")
      tot += len(sf)
      if sample_fields is None and len(sf) > 0:
        sample_fields = [f[0] for f in sf.fields[1:]]
        sample_rec = list(sf.record(0))
    print(f"\n=== MLIT P32: {len(shps)} shapefiles, {tot:,} total cultural property points ===")
    print("  fields:", sample_fields)
    print("  sample:", sample_rec)


if __name__ == "__main__":
  main()

