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


print("=== 1. CITYPOPULATION ACTUAL LINKS (relative + absolute) ===")
cp_pages = [
  "https://www.citypopulation.de/en/papuanewguinea/",
  "https://www.citypopulation.de/en/indonesia/",
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
for u in cp_pages:
  try:
    html = fetch(u, timeout=15)
    hrefs = sorted(set(re.findall(r'href="([^"#]+)"', html)))
    interesting = [h for h in hrefs if any(k in h for k in ("admin", "cities", "towns", "villages", "localities", "island", "papua", "solomon", "fiji", "vanuatu", "caledonia", "polynesia", "samoa", "tonga", "micronesia", "marshall", "kiribati", "palau", "cook", "guam", "mariana", "tuvalu", "niue", "wallis")) and not h.endswith((".css", ".js", ".png", ".ico", ".svg")) and "citypopulation" not in h]
    # Also check table column headers
    ths = re.findall(r"<th[^>]*>(.*?)</th>", html, re.S)
    ths_clean = [re.sub(r"<[^>]+>", " ", t).strip() for t in ths][:12]
    print(f"CP {u.split('/en/')[1]}: links={interesting[:10]} | ths={ths_clean[:8]}")
  except Exception as e:
    print(f"CP {u}: ERR {e}")

print("\n=== 2. ISEE TRIBUS + DATA.GOUV.NC + ISPF ===")
for u in [
  "https://www.isee.nc/population/recensement/tribus",
  "https://www.isee.nc/population/recensement/donnees-detaillees",
  "https://data.gouv.nc/api/explore/v2.1/catalog/datasets?limit=30&refine=themes:Population",
  "https://www.ispf.pf/bases/Recensements/2022.aspx",
  "https://www.ispf.pf/",
  "https://www.insee.fr/fr/statistiques/6690032",
]:
  try:
    txt = fetch(u, timeout=20)
    if "data.gouv.nc" in u:
      j = json.loads(txt)
      print("DATA.GOUV.NC:", [(r["dataset_id"], r["metas"]["default"].get("title")) for r in j.get("results", [])])
    else:
      files = sorted(set(re.findall(r'href=["\']([^"\']*(?:xls|xlsx|csv|zip|recensement|tribu|population)[^"\']*)["\']', txt, re.I)))
      print(u, "-> links:", files[:15])
  except Exception as e:
    print(u, "ERR:", e)

print("\n=== 3. ANU OPEN RESEARCH & STATOIDS & US CENSUS API ===")
for u in [
  "https://openresearch-repository.anu.edu.au/server/api/discover/search/objects?query=PNG+2000+census&size=10",
  "https://www.statoids.com/ypg.html",
  "https://www.statoids.com/yid.html",
  "https://api.census.gov/data/2020/dec/dhcgu?get=NAME,P1_001N&for=place:*",
  "https://api.census.gov/data/2020/dec/dhcmp?get=NAME,P1_001N&for=place:*",
]:
  try:
    txt = fetch(u, timeout=20)
    print(u[:75], "-> len=", len(txt), "preview=", txt[:250].replace("\n", " "))
  except Exception as e:
    print(u[:75], "ERR:", e)
