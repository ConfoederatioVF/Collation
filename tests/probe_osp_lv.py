import csv
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# 1. Check OSP S3R167_* DSDs to see which has settlements/towns/elderships
root = ET.parse("tests/dl/osp_dataflows.xml").getroot()
for el in root.iter():
  if el.tag.endswith("Dataflow"):
    fid = el.attrib.get("id", "")
    if fid.startswith("S3R167"):
      names = [n.text for n in el.iter() if n.tag.endswith("Name") and n.text]
      print("OSP FLOW:", fid, "::", names[0] if names else "")

# Probe a couple of S3R167 DSDs
for fid in ["S3R167_M3010210", "S3R167_M3010214", "S3R167_M3010216", "S3R167_M3010224", "S3R167_M3010319"]:
  dsd_id = fid.split("_", 1)[1]
  u = f"https://osp-rs.stat.gov.lt/rest_xml/datastructure/LSD/{dsd_id}"
  try:
    x = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=15).read()
    r2 = ET.fromstring(x)
    dims = [d.attrib.get("id") for d in r2.iter() if d.tag.endswith("Dimension")]
    codes = []
    for c in r2.iter():
      if c.tag.endswith("Code"):
        cid = c.attrib.get("id", "")
        cname = next((n.text for n in c.iter() if n.tag.endswith("Name") and n.text), "")
        codes.append((cid, cname))
    print(" DSD", fid, "dims:", dims, "codes count:", len(codes), "sample:", codes[:8])
  except Exception as e:
    print(" DSD ERR", fid, e)

# 2. Inspect LV data.gov.lv downloaded CSVs (aw_vietu_centroidi, rig010_01, ird080_01)
for fn in ["aw_vietu_centroidi.csv", "rig010_01.csv", "ird080_01.csv"]:
  fp = "tests/dl/" + fn
  with open(fp, encoding="utf-8-sig") as f:
    reader = csv.reader(f, delimiter=";" if "0" in fn else ",")
    hdr = next(reader)
    rows = [next(reader) for _ in range(5)]
    print("LV CSV:", fn, "hdr:", hdr, "sample:", rows[:2])
