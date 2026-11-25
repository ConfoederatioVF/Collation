import json
import re
import urllib.request


def fetch(url):
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
  with urllib.request.urlopen(req, timeout=25) as r:
    return r.read().decode("utf-8", errors="replace")


print("=== 1. data.gov.lt 2938 ===")
try:
  h = fetch("https://data.gov.lt/datasets/2938/")
  links = re.findall(r'href=["\']([^"\']*(?:get\.data\.gov\.lt|download|\.json|\.csv)[^"\']*)["\']', h, re.I)
  print("links:", links[:10])
  m = re.findall(r"https?://get\.data\.gov\.lt/[^\s\"'<>]+", h)
  print("get.data.gov.lt:", m[:10])
except Exception as e:
  print("err:", e)

print("=== 2. LV PxWeb ===")
for u in [
  "https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP/IR/A_IR",
  "https://data.stat.gov.lv/api/v1/lv/OSP_PUB/START/POP/IR/RIG/RIG010",
  "https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP/IR/IRS/IRS031",
  "https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP/IR/IRD/IRD060",
  "https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP/IR/IRD/IRD070",
]:
  try:
    print(u.split("/")[-1], "->", fetch(u)[:350])
  except Exception as e:
    print("ERR", u.split("/")[-1], e)

print("=== 3. data.gov.lv CKAN ===")
try:
  r = json.loads(fetch("https://data.gov.lv/dati/api/3/action/package_search?q=ciemi&rows=10"))
  for pkg in r["result"]["results"]:
    print("pkg:", pkg["name"], "|", pkg["title"], "|", [(res.get("format"), res.get("url")) for res in pkg.get("resources", [])][:2])
except Exception as e:
  print("err:", e)

print("=== 4. Demoscope 1897 ===")
try:
  h = fetch("https://www.demoscope.ru/weekly/ssp/rus_gub_97.php")
  print("demoscope len:", len(h))
  links = re.findall(r'href=["\']([^"\']*97[^"\']*)["\'][^>]*>([^<]+)', h)
  print("links:", links[:15])
except Exception as e:
  print("err:", e)

print("=== 5. IA 1923 ===")
try:
  m = json.loads(fetch("https://archive.org/metadata/lietuvos-apgyventos-vietos-1925"))
  print("files:", [(f["name"], f.get("size")) for f in m.get("files", [])][:15])
except Exception as e:
  print("err:", e)

print("=== 6. lt.wikisource 1923 ===")
try:
  w = json.loads(fetch("https://lt.wikisource.org/w/api.php?action=query&list=categorymembers&cmtitle=Kategorija:Lietuvos_apgyventos_vietos_(1923)&cmlimit=50&format=json"))
  cm = w.get("query", {}).get("categorymembers", [])
  print("cat members:", len(cm), [x["title"] for x in cm[:10]])
except Exception as e:
  print("err:", e)

print("=== 7. SGKP ===")
try:
  s = fetch("https://dir.icm.edu.pl/pl/Slownik_geograficzny/")
  print("SGKP len:", len(s), "links:", re.findall(r'href=["\']([^"\']*Tom[^"\']*)["\']', s)[:10])
except Exception as e:
  print("err:", e)
