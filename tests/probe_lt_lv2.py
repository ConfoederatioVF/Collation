import json
import re
import urllib.request


def fetch(url):
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
  with urllib.request.urlopen(req, timeout=25) as r:
    return r.read().decode("utf-8", errors="replace")


print("=== 1. data.gov.lv iedzivotaji & varis ===")
for pkg in ["iedzivotaji", "varis-atvertie-dati"]:
  d = json.loads(fetch(f"https://data.gov.lv/dati/api/3/action/package_show?id={pkg}"))
  print("PKG:", pkg)
  for res in d["result"]["resources"]:
    print(" ", res.get("name"), "|", res.get("format"), "|", res.get("url"))

print("\n=== 2. LV PxWeb POP tree ===")
for path in [
  "https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP",
  "https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP/IR/A_IR",
  "https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP/IR/IRS",
  "https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP/IR/IRD",
]:
  print("PATH:", path)
  print(" ", fetch(path)[:1000])

print("\n=== 3. Demoscope rus_gub_97.php ===")
h = fetch("https://www.demoscope.ru/weekly/ssp/rus_gub_97.php")
# Check encoding or links
links = re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', h, re.S)
for href, txt in links:
  if any(k in href for k in ["gub", "gor", "97", "emp"]):
    print(" ", href, "|", re.sub(r"<[^>]+>", "", txt).strip()[:60])

print("\n=== 4. Archive.org search 1897 & SGKP ===")
for q in [
  "title:(Населенные места Российской империи в 500 и более жителей)",
  "identifier:slownik-*",
]:
  u = "https://archive.org/advancedsearch.php?q=" + urllib.parse.quote(q) + "&fl[]=identifier,title&rows=20&output=json"
  print("IA:", q, "->", fetch(u)[:800])

print("\n=== 5. lt.wikisource 1923 count ===")
w = json.loads(fetch("https://lt.wikisource.org/w/api.php?action=query&prop=categoryinfo&titles=Kategorija:Lietuvos_apgyventos_vietos_(1923)&format=json"))
print("catinfo:", w)
