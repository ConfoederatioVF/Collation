import glob
import json
import math
import os
import urllib.parse
import urllib.request

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get_json(u, timeout=15):
  with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=timeout) as r:
    return json.loads(r.read().decode("utf-8"))

# 1. Finish diag_round3 checks (Port Moresby <=12km, Polynesian Outer Islands, Amuri/Aitutaki)
AUSTRAL = r"histmap\1.data_raw\population_regional\AUSTRAL"
def hav(a1, o1, a2, o2):
  d1, d2 = math.radians(a2 - a1), math.radians(o2 - o1)
  x = math.sin(d1 / 2) ** 2 + math.cos(math.radians(a1)) * math.cos(math.radians(a2)) * math.sin(d2 / 2) ** 2
  return 6371.0 * 2.0 * math.atan2(math.sqrt(x), math.sqrt(max(0.0, 1.0 - x)))

ng_p = glob.glob(os.path.join(AUSTRAL, "3.modern", "*", "modern_new_guinea_settlements.json"))[0]
ng = json.load(open(ng_p, encoding="utf-8"))
print("=== PORT MORESBY <= 12 km ===")
for k, v in ng.items():
  if v.get("country") == "Papua New Guinea":
    d = hav(v["coords"][0], v["coords"][1], -9.4438, 147.1803)
    if d <= 12.0:
      print(f"  {d:.2f} km | {k} | {v['name']} | {v.get('admin1')} | {v['population']}")

mm_p = glob.glob(os.path.join(AUSTRAL, "3.modern", "*", "modern_melanesia_micro_settlements.json"))[0]
mm = json.load(open(mm_p, encoding="utf-8"))
for k, v in mm.items():
  if "polynesian" in v["name"].lower():
    print("SOL_POLY:", k, v["name"], v["coords"], v["population"], v["sources"][:1])

mp_p = glob.glob(os.path.join(AUSTRAL, "3.modern", "*", "modern_polynesia_settlements.json"))[0]
mp = json.load(open(mp_p, encoding="utf-8"))
for k, v in mp.items():
  if v["country"] == "Cook Islands" and any(w in v["name"].lower() for w in ("amuri", "aitutaki")):
    print("COOK_AIT:", k, v["name"], v["coords"], v["population"])

# 2. Check HDX COD-PS for Samoa, Tonga, Kiribati, FSM, RMI, Palau, Cook Islands, Wallis & Futuna, French Polynesia
print("\n=== HDX COD-PS MICRONESIA & POLYNESIA ===")
for pid in ["cod-ps-wsm", "cod-ps-ton", "cod-ps-kir", "cod-ps-fsm", "cod-ps-mhl", "cod-ps-plw", "cod-ps-cok", "cod-ps-wlf", "cod-ps-pyf", "cod-ps-nru", "cod-ps-tuv"]:
  try:
    pkg = get_json(f"https://data.humdata.org/api/3/action/package_show?id={pid}")
    res = [(r.get("name"), r.get("format"), r.get("size")) for r in pkg["result"]["resources"][:5]]
    print(f"  {pid:12s}: {res}")
  except Exception as e:
    print(f"  {pid:12s}: ERR {e}")

# 3. Check US Census 2020 Island Areas API (Guam & CNMI places / estates!)
print("\n=== US CENSUS 2020 ISLAND AREAS API ===")
for tag, u in [
  ("Guam places", "https://api.census.gov/data/2020/dec/dhcgu?get=NAME,P1_001N&for=place:*"),
  ("CNMI places", "https://api.census.gov/data/2020/dec/dhcmp?get=NAME,P1_001N&for=place:*"),
  ("Guam 2010 places", "https://api.census.gov/data/2010/dec/gu?get=NAME,P0010001&for=place:*"),
  ("CNMI 2010 places", "https://api.census.gov/data/2010/dec/mp?get=NAME,P0010001&for=place:*"),
]:
  try:
    rows = get_json(u)
    print(f"  {tag:18s}: {len(rows)-1} places | sample={rows[1:4]}")
  except Exception as e:
    print(f"  {tag:18s}: ERR {e}")

# 4. Check CityPopulation village-level pages for Samoa, Tonga, Kiribati, Wallis & Futuna, French Polynesia, Guam, CNMI
print("\n=== CITYPOPULATION MICRONESIA & POLYNESIA ===")
import re
for tag, u in [
  ("Samoa villages", "https://www.citypopulation.de/en/samoa/"),
  ("Tonga villages", "https://www.citypopulation.de/en/tonga/"),
  ("Tonga admin", "https://www.citypopulation.de/en/tonga/admin/"),
  ("Kiribati", "https://www.citypopulation.de/en/kiribati/"),
  ("Wallis & Futuna", "https://www.citypopulation.de/en/wallisfutuna/"),
  ("French Polynesia", "https://www.citypopulation.de/en/frenchpolynesia/"),
  ("Cook Islands", "https://www.citypopulation.de/en/cookislands/"),
  ("Nauru", "https://www.citypopulation.de/en/nauru/"),
]:
  try:
    html = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=15).read().decode("utf-8", "ignore")
    rnames = len(re.findall(r'<td[^>]*class="rname"', html))
    print(f"  {tag:20s}: rname_rows={rnames}")
  except Exception as e:
    print(f"  {tag:20s}: ERR {e}")

# 5. Check ArcGIS Online for Samoa/Tonga/Kiribati/FSM/Wallis/FP census village FeatureServers
print("\n=== AGOL MICRONESIA & POLYNESIA ===")
for q in ['Samoa village OR census type:"Feature Service"', 'Tonga village OR census type:"Feature Service"', 'Kiribati village OR census type:"Feature Service"', 'Palau OR Micronesia village census type:"Feature Service"']:
  try:
    d = get_json("https://www.arcgis.com/sharing/rest/search?q=" + urllib.parse.quote(q) + "&f=json&num=8")
    hits = [(r.get("title","")[:45], r.get("owner",""), (r.get("url") or "")[:75]) for r in d.get("results",[]) if "osm" not in (r.get("owner") or "").lower()]
    print(f"  {q[:35]:35s}: {hits[:4]}")
  except Exception as e:
    print("  ERR", q[:25], e)
