import json
import urllib.parse
import urllib.request

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get_json(u, timeout=15):
  with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=timeout) as r:
    return json.loads(r.read().decode("utf-8"))

# 1. ALL Pacific COD-PS packages on HDX (search q=admpop OR pplp with Pacific tags / OCHA ROP!)
for q in ["organization:ocha-rop cod-ps", "cod-ps samoa OR cook OR polynesia OR wallis OR niue OR tuvalu OR palau OR tonga OR kiribati"]:
  try:
    d = get_json("https://data.humdata.org/api/3/action/package_search?q=" + urllib.parse.quote(q) + "&rows=30")
    print(f"=== HDX [{q}] count={d['result']['count']} ===")
    for r in d["result"]["results"]:
      nm = r["name"]
      if any(w in nm for w in ("wsm", "ton", "kir", "fsm", "mhl", "plw", "cok", "wlf", "pyf", "tuv", "niu", "nru", "samoa", "tonga", "kiribati", "cook", "polynesia", "wallis")):
        res = [(x.get("name"), x.get("format"), x.get("url")) for x in r.get("resources", []) if x.get("format") in ("XLSX", "XLS", "CSV")][:4]
        print(f"  {nm:28s}: {[(x[0], x[1]) for x in res]}")
  except Exception as e:
    print("ERR HDX:", e)

# 2. Exact US Census 2020 Island Areas endpoints
try:
  dec = get_json("https://api.census.gov/data/2020/dec.json")
  print("\n=== US CENSUS 2020 ISLAND AREAS DATASETS ===")
  for ds in dec.get("dataset", []):
    t = ds.get("title", "")
    if any(w in t.lower() for w in ("guam", "mariana", "island")):
      print(" ", ds.get("c_dataset"), "|", t[:70], "|", ds.get("distribution", [{}])[0].get("accessURL"))
except Exception as e:
  print("ERR Census:", e)

# 3. Exact Tonga_2021_Census FeatureServer on services7/nxa9pzeDn9ehHIfE
try:
  cat = get_json("https://services7.arcgis.com/nxa9pzeDn9ehHIfE/arcgis/rest/services?f=json")
  for s in cat.get("services", []):
    if any(w in s.get("name", "").lower() for w in ("tonga", "samoa", "kiribati", "pacific", "cook", "fiji", "vanuatu", "solomon", "palau", "micronesia", "marshall")):
      print("SDG SVC:", s.get("name"), s.get("type"))
except Exception as e:
  print("ERR SDG:", e)

# 4. Also check Samoa Bureau of Statistics & Wallis & Futuna INSEE / Wikipedia official tables
for pid in ["cod-ps-ton", "cod-ps-kir", "cod-ps-mhl", "cod-ps-fsm"]:
  try:
    pkg = get_json(f"https://data.humdata.org/api/3/action/package_show?id={pid}")
    print(f"\nPKG {pid}:")
    for x in pkg["result"]["resources"]:
      print(f"  {x.get('name'):45s} | {x.get('format'):6s} | {x.get('url')}")
  except Exception as e:
    print(f"ERR {pid}: {e}")
