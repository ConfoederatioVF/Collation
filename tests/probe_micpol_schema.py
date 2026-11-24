import json
import urllib.parse
import urllib.request

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
def gj(u):
  with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=15) as r:
    return json.loads(r.read().decode("utf-8"))

# 1. Tonga 2021 Census & Palau 2020 Census FeatureServer layers
for nm in [
  "Tonga_2021_Census__Population__Education__Employment__Health__and_Internet_Access",
  "Palau_Population_by_Age_and_Sex_2020_Census",
]:
  u = f"https://services7.arcgis.com/nxa9pzeDn9ehHIfE/arcgis/rest/services/{nm}/FeatureServer"
  d = gj(u + "?f=json")
  layers = [(ly["id"], ly["name"]) for ly in d.get("layers", [])]
  print(f"SVC {nm[:35]}: layers={layers}")
  for lid, lnm in layers[:3]:
    cnt = gj(f"{u}/{lid}/query?where=1%3D1&returnCountOnly=true&f=json").get("count")
    smp = gj(f"{u}/{lid}/query?where=1%3D1&outFields=*&resultRecordCount=1&outSR=4326&f=json").get("features", [])
    attrs = smp[0].get("attributes") if smp else None
    gkeys = list((smp[0].get("geometry") or {}).keys()) if smp else None
    print(f"  L{lid} ({lnm}) n={cnt} | keys={list(attrs.keys())[:14] if attrs else None} | sample={dict(list(attrs.items())[:6]) if attrs else None} | g={gkeys}")

# 2. US Census 2020 Guam & CNMI exact geography + variable check
for ds in ("dhcgu", "dhcmp"):
  try:
    g = gj(f"https://api.census.gov/data/2020/dec/{ds}/geography.json")
    print(f"CENSUS {ds} geos:", [(x.get("name"), x.get("requires")) for x in g.get("fips", [])[:10]])
    # Try querying place without state or with wildcard
    rows = gj(f"https://api.census.gov/data/2020/dec/{ds}?get=NAME,P1_001N&for=place:*")
    print(f"  {ds} place:* n={len(rows)-1} sample={rows[1:4]}")
  except Exception as e:
    print(f"CENSUS {ds} err:", e)

# 3. Check US Census TIGERweb 2020 Guam & CNMI Places FeatureServer
for u in [
  "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer?f=json",
]:
  try:
    d = gj(u)
    print("TIGERweb layers:", [(ly["id"], ly["name"]) for ly in d.get("layers", [])[:12]])
  except Exception as e:
    print("TIGERweb err:", e)

# 4. Check HDX Samoa & Wallis & French Polynesia & Cook Islands packages by country filter
for iso3 in ("wsm", "cok", "wlf", "pyf", "tuv", "niu"):
  try:
    d = gj(f"https://data.humdata.org/api/3/action/package_search?fq=groups:{iso3}&q=population+OR+census&rows=5")
    hits = [(r["name"], [x.get("name") for x in r.get("resources", [])[:3]]) for r in d["result"]["results"]]
    print(f"HDX {iso3}: {hits}")
  except Exception as e:
    print(f"HDX {iso3} err:", e)
