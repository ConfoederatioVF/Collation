import csv
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# 1. Inspect ALL M301* flows in osp_dataflows.xml
root = ET.parse("tests/dl/osp_dataflows.xml").getroot()
m301 = []
for el in root.iter():
  if el.tag.endswith("Dataflow"):
    fid = el.attrib.get("id", "")
    names = [n.text for n in el.iter() if n.tag.endswith("Name") and n.text]
    if "M30102" in fid or "surašym" in (" ".join(names)).lower() or "gyvenviet" in (" ".join(names)).lower():
      m301.append((fid, names[0] if names else ""))
print("=== 1. OSP M30102 & census flows ===", len(m301))
for fid, nm in sorted(m301):
  print(" ", fid, "::", nm[:120])

# 2. Check S3R167_M3010210 & S3R167_M3010210_1 & S3R167_M3010319 data sample
for fid in ["S3R167_M3010210", "S3R167_M3010210_1", "S3R167_M3010202", "S3R167_M3010205"]:
  dsd = fid.split("_", 1)[1]
  u = f"https://osp-rs.stat.gov.lt/rest_xml/datastructure/LSD/{dsd}"
  try:
    x = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=15).read()
    r2 = ET.fromstring(x)
    dims = [d.attrib.get("id") for d in r2.iter() if d.tag.endswith("Dimension")]
    print(" DSD", fid, "dims:", dims)
  except Exception as e:
    print(" DSD ERR", fid, e)

# 3. Inspect LV rig010_01.csv & aw_vietu_centroidi.csv
centroids = {}
with open("tests/dl/aw_vietu_centroidi.csv", encoding="utf-8-sig") as f:
  for row in csv.DictReader(f):
    centroids[row["KODS"]] = row
print("\n=== 2. LV centroids count ===", len(centroids))

years = set()
matched_ciems = set()
matched_pils = set()
unmatched_prefixes = set()
with open("tests/dl/rig010_01.csv", encoding="utf-8-sig") as f:
  for row in csv.DictReader(f, delimiter=";"):
    if row.get("AgeGroup") != "TOTAL" or row.get("SEX") != "T":
      continue
    years.add(row.get("TIME"))
    area = row.get("AllAreaLV", "")
    kods = area[2:] if area.startswith("LV") else ""
    if kods in centroids:
      t = centroids[kods]["TIPS_CD"]
      if t == "104":
        matched_pils.add(kods)
      elif t == "106":
        matched_ciems.add(kods)
    else:
      unmatched_prefixes.add(area[:5])
print("rig010 years:", sorted(years))
print("matched pilsetas:", len(matched_pils), "matched ciemi:", len(matched_ciems))
print("unmatched area prefixes (sample):", sorted(unmatched_prefixes)[:20])

# 4. Probe Wikidata SPARQL for Lithuania settlements with dated P1082
q = """
SELECT ?item ?itemLabel ?coord ?pop ?date ?refLabel WHERE {
  ?item wdt:P17 wd:Q37 .
  ?item wdt:P31/wdt:P279* wd:Q486972 .
  ?item wdt:P625 ?coord .
  ?item p:P1082 ?stmt .
  ?stmt ps:P1082 ?pop .
  OPTIONAL { ?stmt pq:P585 ?date . }
  OPTIONAL { ?stmt prov:wasDerivedFrom/pr:P248 ?ref . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "lt,en". }
} LIMIT 30
"""
u = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q)
req = urllib.request.Request(u, headers={"User-Agent": "SVEA-Bot/1.0 (historical demography research)"})
res = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
print("\n=== 3. Wikidata SPARQL LT sample ===", len(res["results"]["bindings"]))
for b in res["results"]["bindings"][:10]:
  print(" ", b["itemLabel"]["value"], b["pop"]["value"], b.get("date", {}).get("value", ""), "|", b.get("refLabel", {}).get("value", ""))
