import json
import re
import urllib.parse
import urllib.request

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get_json(u, timeout=15):
  with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=timeout) as r:
    return json.loads(r.read().decode("utf-8"))

# 1. Inspect services7.arcgis.com/nxa9pzeDn9ehHIfE (Tonga 2021 Census & sibling Pacific censuses!)
try:
  cat = get_json("https://services7.arcgis.com/nxa9pzeDn9ehHIfE/arcgis/rest/services?f=json")
  svcs = cat.get("services", [])
  print(f"=== services7/nxa9pzeDn9ehHIfE ({len(svcs)} services) ===")
  for s in svcs[:40]:
    print(" ", s.get("name"), s.get("type"))
except Exception as e:
  print("ERR nxa9:", e)

# 2. Check US Census 2020 Island Areas API (Guam=66, CNMI=69)
print("\n=== US CENSUS 2020 GUAM & CNMI ===")
for tag, u in [
  ("Guam 2020 dhcgu place", "https://api.census.gov/data/2020/dec/dhcgu?get=NAME,P1_001N&for=place:*&in=state:66"),
  ("Guam 2020 dpgu place", "https://api.census.gov/data/2020/dec/dpgu?get=NAME,DP1_0001C&for=place:*&in=state:66"),
  ("CNMI 2020 dhcmp place", "https://api.census.gov/data/2020/dec/dhcmp?get=NAME,P1_001N&for=place:*&in=state:69"),
  ("CNMI 2020 dpmp place", "https://api.census.gov/data/2020/dec/dpmp?get=NAME,DP1_0001C&for=place:*&in=state:69"),
  ("Guam 2020 dhcgu csub", "https://api.census.gov/data/2020/dec/dhcgu?get=NAME,P1_001N&for=county%20subdivision:*&in=state:66"),
  ("CNMI 2020 dhcmp csub", "https://api.census.gov/data/2020/dec/dhcmp?get=NAME,P1_001N&for=county%20subdivision:*&in=state:69"),
]:
  try:
    rows = get_json(u)
    print(f"  {tag:24s}: {len(rows)-1} rows | sample={rows[1:4]}")
  except Exception as e:
    print(f"  {tag:24s}: ERR {e}")

# 3. Retry HDX search for Samoa, Tonga, Kiribati, Cook Islands, Wallis & Futuna, French Polynesia
print("\n=== HDX PACIFIC RETRY ===")
for q in ["cod-ps-wsm", "cod-ps-ton", "cod-ps-kir", "cod-ps-cok", "samoa census village", "tonga census village", "kiribati census village"]:
  try:
    d = get_json("https://data.humdata.org/api/3/action/package_search?q=" + urllib.parse.quote(q) + "&rows=3")
    hits = [(r["name"], [x.get("name") for x in r.get("resources", [])[:3]]) for r in d["result"]["results"]]
    print(f"  {q:24s}: {hits}")
  except Exception as e:
    print(f"  {q:24s}: ERR {e}")

# 4. Search ArcGIS Online for owner:sdg_admin or Samoa/Kiribati/Cook/FSM/Wallis/French Polynesia census layers
print("\n=== AGOL PACIFIC NSOs ===")
for q in ['owner:sdg_admin', 'Tonga 2021 Census', 'Samoa Census 2021 OR 2016', 'Kiribati Census 2020 OR 2015', 'French Polynesia commune OR recensement']:
  try:
    d = get_json("https://www.arcgis.com/sharing/rest/search?q=" + urllib.parse.quote(q) + "&f=json&num=10")
    hits = [(r.get("title","")[:50], r.get("owner",""), (r.get("url") or "")[:85]) for r in d.get("results",[]) if r.get("url")]
    print(f"  {q:38s}: {hits[:4]}")
  except Exception as e:
    print("  ERR", q, e)
