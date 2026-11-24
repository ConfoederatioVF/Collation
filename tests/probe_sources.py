import json
import re
import urllib.parse
import urllib.request

HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
}


def fetch(url, timeout=20):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=timeout) as r:
    return r.read().decode("utf-8", "ignore")


print("=== 1. HDX PACKAGES ===")
for pkg in [
  "village-coordinates-lookup",
  "cod-ps-png",
  "cod-ps-slb",
  "cod-ps-fji",
  "cod-ps-fsm",
  "population-datasets",
  "cod-ps-vut",
  "cod-ps-wsm",
  "cod-ps-ton",
  "cod-ps-kir",
  "cod-ps-mhl",
  "cod-ps-plw",
  "cod-ps-cok",
]:
  try:
    res = json.loads(fetch(f"https://data.humdata.org/api/3/action/package_show?id={pkg}"))
    r = res["result"]
    print(f"HDX {pkg}: {r['title']}")
    for resx in r.get("resources", []):
      print(f"   - {resx['name']} ({resx.get('format')}) -> {resx['url']}")
  except Exception as e:
    print(f"HDX {pkg}: {e}")

print("\n=== 2. CITYPOPULATION ===")
cp_urls = [
  "https://www.citypopulation.de/en/papuanewguinea/",
  "https://www.citypopulation.de/en/papuanewguinea/admin/",
  "https://www.citypopulation.de/en/indonesia/papua/admin/",
  "https://www.citypopulation.de/en/indonesia/papuabarat/admin/",
  "https://www.citypopulation.de/en/fiji/",
  "https://www.citypopulation.de/en/solomons/",
  "https://www.citypopulation.de/en/vanuatu/",
  "https://www.citypopulation.de/en/newcaledonia/",
  "https://www.citypopulation.de/en/frenchpolynesia/",
  "https://www.citypopulation.de/en/samoa/",
  "https://www.citypopulation.de/en/tonga/",
  "https://www.citypopulation.de/en/micronesia/",
  "https://www.citypopulation.de/en/marshallislands/",
  "https://www.citypopulation.de/en/kiribati/",
  "https://www.citypopulation.de/en/palau/",
  "https://www.citypopulation.de/en/cookislands/",
  "https://www.citypopulation.de/en/guam/",
  "https://www.citypopulation.de/en/northernmarianas/",
  "https://www.citypopulation.de/en/tuvalu/",
  "https://www.citypopulation.de/en/niue/",
  "https://www.citypopulation.de/en/wallisandfutuna/",
]
for u in cp_urls:
  try:
    html = fetch(u, timeout=15)
    links = sorted(set(re.findall(r'href="(/en/[^"#]+)"', html)))
    pref = u.replace("https://www.citypopulation.de", "").rstrip("/")
    sub = [l for l in links if l.startswith(pref) and l != pref and l != pref + "/"]
    years = sorted(set(re.findall(r"\b(18\d\d|19\d\d|20[012]\d)\b", html)))
    print(f"CP {pref}: years={years[:6]}..{years[-6:]} | sub={sub[:8]}")
  except Exception as e:
    print(f"CP {u}: ERR {e}")

print("\n=== 3. ISEE / DATA.GOUV.NC / ISPF / PDH SDMX ===")
for u in [
  "https://data.gouv.nc/api/explore/v2.1/catalog/datasets?limit=25&where=search(metas.default.title,%22recensement%22)",
  "https://data.gouv.nc/api/explore/v2.1/catalog/datasets?limit=25&where=search(metas.default.title,%22tribu%22)",
  "https://www.isee.nc/population/recensement/communautes",
  "https://www.isee.nc/population/recensement/structure-de-la-population-et-evolutions",
  "https://www.ispf.pf/themes/Population/Recensements",
  "https://stats-nsi-stable.pacificdata.org/rest/dataflow/SPC",
]:
  try:
    txt = fetch(u, timeout=20)
    if "data.gouv.nc" in u:
      j = json.loads(txt)
      print("DATA.GOUV.NC:", [(r["dataset_id"], r["metas"]["default"].get("title")) for r in j.get("results", [])])
    elif "pacificdata.org" in u:
      dfs = re.findall(r'id="(DF_[^"]+)"', txt)
      pop_dfs = [d for d in sorted(set(dfs)) if any(k in d.lower() for k in ("pop", "cens", "vil", "admin", "urb"))]
      print("PDH SDMX dataflows:", pop_dfs[:30])
    else:
      files = sorted(set(re.findall(r'href=["\']([^"\']*(?:xls|xlsx|csv|pdf|zip)[^"\']*)["\']', txt, re.I)))
      print(u, "-> files:", files[:15])
  except Exception as e:
    print(u, "ERR:", e)
