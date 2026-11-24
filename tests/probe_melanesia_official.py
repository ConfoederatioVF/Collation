import json
import urllib.parse
import urllib.request

H = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
  "Accept": "application/json, text/plain, */*",
}

def get_json(url, timeout=15):
  req = urllib.request.Request(url, headers=H)
  with urllib.request.urlopen(req, timeout=timeout) as r:
    return json.loads(r.read().decode("utf-8"))

# 1. ArcGIS Online official FBoS & Pacific NSO Feature Services
agol_queries = [
  'owner:simoli.louise_fbos',
  'owner:fiu_community_fiji',
  'Fiji localities OR village OR enumeration OR tikina type:"Feature Service"',
  'Vanuatu village OR enumeration OR census OR locality type:"Feature Service"',
  'Solomon Islands village OR ward OR enumeration OR census type:"Feature Service"',
  'New Caledonia OR Nouvelle-Caledonie tribu OR village OR recensement type:"Feature Service"',
  'Samoa OR Tonga OR Kiribati OR Micronesia village census type:"Feature Service"',
]
for q in agol_queries:
  u = "https://www.arcgis.com/sharing/rest/search?q=" + urllib.parse.quote(q) + "&f=json&num=20"
  try:
    d = get_json(u)
    print(f"\n=== AGOL [{q}] total={d.get('total')} ===")
    for r in d.get("results", []):
      print(f"  {r.get('title','')[:58]:58s} | {r.get('owner',''):24s} | {r.get('url') or ''}")
  except Exception as e:
    print(f"ERR AGOL {q}: {e}")

# 2. Check FBoS org services catalog directly
for svc_root in [
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services?f=json",
  "https://services9.arcgis.com/rcR6NmM708l8kJG6/arcgis/rest/services?f=json",
]:
  try:
    d = get_json(svc_root)
    svcs = d.get("services", [])
    print(f"\n=== REST CATALOG {svc_root} ({len(svcs)} services) ===")
    for s in svcs[:40]:
      print(f"  {s.get('name')} ({s.get('type')})")
  except Exception as e:
    print(f"ERR REST {svc_root}: {e}")

# 3. Check Open Data New Caledonia (data.gouv.nc — official Government of New Caledonia / ISEE)
try:
  d = get_json("https://data.gouv.nc/api/explore/v2.1/catalog/datasets?limit=25&where=search(default%2C%22population%22)")
  print(f"\n=== data.gouv.nc population datasets (total={d.get('total_count')}) ===")
  for r in d.get("results", []):
    ds = r.get("dataset_id")
    meta = (r.get("metas") or {}).get("default") or {}
    print(f"  {ds} | {meta.get('title','')[:70]} | records={meta.get('records_count')}")
except Exception as e:
  print("ERR data.gouv.nc:", e)

# 4. Check data.gouv.nc tribus / quartiers / localites
try:
  d = get_json("https://data.gouv.nc/api/explore/v2.1/catalog/datasets?limit=25&where=search(default%2C%22tribu%22)%20OR%20search(default%2C%22recensement%22)")
  print(f"\n=== data.gouv.nc tribu/recensement (total={d.get('total_count')}) ===")
  for r in d.get("results", []):
    ds = r.get("dataset_id")
    meta = (r.get("metas") or {}).get("default") or {}
    print(f"  {ds} | {meta.get('title','')[:70]} | records={meta.get('records_count')}")
except Exception as e:
  print("ERR data.gouv.nc2:", e)

# 5. Check Fiji Open Data / Pacific Data Hub with browser headers
for url in [
  "https://pacificdata.org/data/api/3/action/package_search?q=fiji+census+2017&rows=5",
  "https://stats-nsi-stable.pacificdata.org/rest/dataflow/SPC?references=none",
]:
  try:
    req = urllib.request.Request(url, headers={**H, "Referer": "https://pacificdata.org/"})
    with urllib.request.urlopen(req, timeout=15) as r:
      txt = r.read(400).decode("utf-8", errors="ignore")
      print(f"\n=== OK {url} -> {txt[:200]}")
  except Exception as e:
    print(f"ERR {url}: {e}")
