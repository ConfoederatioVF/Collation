import json
import re
import urllib.parse
import urllib.request

HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}


def fetch(url, timeout=25):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=timeout) as r:
    return r.read().decode("utf-8", "ignore")


# 1. CityPopulation Oceania directory & PNG mun/admin + Indonesia Papua pages
print("=== 1. CITYPOPULATION OCEANIA INDEX ===")
for u in [
  "https://www.citypopulation.de/en/oceania/",
  "https://www.citypopulation.de/en/indonesia/",
  "https://www.citypopulation.de/en/papuanewguinea/mun/admin/",
  "https://www.citypopulation.de/en/papuanewguinea/cities/",
  "https://www.citypopulation.de/en/fiji/admin/",
  "https://www.citypopulation.de/en/vanuatu/admin/",
  "https://www.citypopulation.de/en/samoa/admin/",
  "https://www.citypopulation.de/en/samoa/cities/",
  "https://www.citypopulation.de/en/tonga/admin/",
  "https://www.citypopulation.de/en/tonga/cities/",
]:
  try:
    html = fetch(u)
    if u.endswith("/oceania/"):
      links = sorted(set(re.findall(r'href="(/en/[a-z]+/[^"]*)"', html)))
      print("OCEANIA links:", links)
    elif u.endswith("/indonesia/"):
      links = sorted(set(re.findall(r'href="([^"]*papua[^"]*)"', html, re.I)))
      print("IDN papua links:", links)
    else:
      ths = [re.sub(r"<[^>]+>", " ", t).strip() for t in re.findall(r"<th[^>]*>(.*?)</th>", html, re.S)]
      rows = len(re.findall(r"<tr[^>]*>", html))
      sublinks = sorted(set(re.findall(r'href="([^"]*admin/[^"]*)"', html)))[:8]
      print(f"{u.replace('https://www.citypopulation.de','')}: rows={rows} | ths={ths[:10]} | sub={sublinks}")
  except Exception as e:
    print(f"{u}: ERR {e}")

# 2. data.gouv.nc datasets & isee.nc recensement subpages & ispf.pf
print("\n=== 2. DATA.GOUV.NC & ISEE & ISPF ===")
try:
  j = json.loads(fetch("https://data.gouv.nc/api/explore/v2.1/catalog/datasets?limit=100"))
  matches = [
    (r["dataset_id"], r["metas"]["default"].get("title"))
    for r in j.get("results", [])
    if any(k in (r["dataset_id"] + " " + str(r["metas"]["default"].get("title", ""))).lower() for k in ("tribu", "recens", "pop", "commune", "village"))
  ]
  print("data.gouv.nc matches:", matches[:30])
except Exception as e:
  print("data.gouv.nc ERR:", e)

try:
  html = fetch("https://www.isee.nc/population/recensement")
  links = sorted(set(re.findall(r'href="([^"]*(?:recensement|tribu|population|xls|xlsx)[^"]*)"', html, re.I)))
  print("isee.nc/population/recensement:", links[:25])
except Exception as e:
  print("isee ERR:", e)

try:
  html = fetch("https://www.ispf.pf/themes/population")
  links = sorted(set(re.findall(r'href="([^"]*(?:recens|pop|xls|xlsx|csv|commune|publication)[^"]*)"', html, re.I)))
  print("ispf.pf/themes/population:", links[:25])
except Exception as e:
  print("ispf ERR:", e)

# 3. ANU Open Research searches for PNG 2000/1990/1980/1973 & Pacific historical censuses
print("\n=== 3. ANU OPEN RESEARCH ===")
for q in ["Papua New Guinea 2000 census", "Papua New Guinea village directory", "PNGRIS", "Island Populations of the Pacific McArthur", "Fiji census 1966 1956 1946"]:
  try:
    j = json.loads(fetch("https://openresearch-repository.anu.edu.au/server/api/discover/search/objects?query=" + urllib.parse.quote(q) + "&size=6"))
    objs = j.get("_embedded", {}).get("searchResult", {}).get("_embedded", {}).get("objects", [])
    titles = []
    for o in objs:
      idx = o.get("_embedded", {}).get("indexableObject", {})
      t = idx.get("name", "")
      u = idx.get("handle", "")
      titles.append((u, t[:70]))
    print(f"ANU [{q}]:", titles)
  except Exception as e:
    print(f"ANU [{q}] ERR:", e)
