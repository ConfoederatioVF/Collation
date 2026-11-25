import csv
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# 1. OSP Lithuania S3R167_M3010210 & M3010210_1
for fid in ["S3R167_M3010210", "S3R167_M3010210_1"]:
  u = f"https://osp-rs.stat.gov.lt/rest_json/data/{fid}/"
  req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
  j = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
  dims = j["structure"]["dimensions"].get("series", []) or j["structure"]["dimensions"].get("dataSet", [])
  obs_dims = j["structure"]["dimensions"].get("observation", [])
  print("OSP DATA", fid, "dim keys:", list(j["structure"]["dimensions"].keys()), "series dims:", [(d["id"], len(d["values"])) for d in dims], "obs:", [(d["id"], len(d["values"]), [v["id"] for v in d["values"][:5]], [v["id"] for v in d["values"][-3:]]) for d in obs_dims])
  for d in dims + obs_dims:
    if "miestas" in d["id"].lower():
      print("  sample cities:", [(v["id"], v["name"]) for v in d["values"][:10]])

# Check any 2011/2021/2001/1989 flows in osp_dataflows.xml
root = ET.parse("tests/dl/osp_dataflows.xml").getroot()
hits = []
for el in root.iter():
  if el.tag.endswith("Dataflow"):
    fid = el.attrib.get("id", "")
    names = [n.text for n in el.iter() if n.tag.endswith("Name") and n.text]
    joined = " | ".join(names)
    if any(k in joined.lower() for k in ["2021 m.", "2011 m.", "2001 m.", "surašym", "seniūnij", "gyvenviet"]) and "žemės ūkio" not in joined.lower():
      hits.append((fid, names[0] if names else ""))
print("\nOSP census/locality flows:", len(hits))
for fid, nm in hits[:40]:
  print(" ", fid, "::", nm[:120])

# 2. LV IRD081 AREA codes (cities/towns vs novadi/pagasti)
ird = json.loads(urllib.request.urlopen("https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP/IR/IRD/IRD081").read().decode("utf-8"))
for v in ird["variables"]:
  if v["code"] == "AREA":
    pairs = list(zip(v["values"], v["valueTexts"]))
    cities = [(c, t) for c, t in pairs if any(w in t.lower() for w in ["city", "town", "riga", "daugavpils", "liepāja", "jelgava"]) or (not any(w in t.lower() for w in ["municipality", "parish", "region", "latvia", "neighbourhood", "densely"]) and not c.startswith(("LVDPA", "LV100")))]
    print("\nLV IRD081 non-muni/parish/dpa:", len(cities), cities[:25])

# 3. Fast Wikidata SPARQL test for LT & LV dated P1082 (no P279*)
for country_name, qid in [("Lithuania", "Q37"), ("Latvia", "Q211")]:
  q = f"""
  SELECT ?item ?itemLabel ?coord ?pop ?date ?refLabel WHERE {{
    ?item wdt:P17 wd:{qid} .
    ?item wdt:P625 ?coord .
    ?item p:P1082 ?stmt .
    ?stmt ps:P1082 ?pop .
    ?stmt pq:P585 ?date .
    OPTIONAL {{ ?stmt prov:wasDerivedFrom/pr:P248 ?ref . }}
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,lt,lv". }}
  }} LIMIT 20
  """
  u = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q)
  req = urllib.request.Request(u, headers={"User-Agent": "SVEA-Bot/1.0"})
  res = json.loads(urllib.request.urlopen(req, timeout=25).read().decode("utf-8"))
  print(f"\nWD {country_name} sample:", len(res["results"]["bindings"]))
  for b in res["results"]["bindings"][:8]:
    print(" ", b["itemLabel"]["value"], b["pop"]["value"], b["date"]["value"][:10], "|", b.get("refLabel", {}).get("value", ""))
