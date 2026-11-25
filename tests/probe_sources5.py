import json
import re
import urllib.request
import urllib.parse


def fetch(url, encoding="utf-8"):
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
  with urllib.request.urlopen(req, timeout=25) as r:
    return r.read().decode(encoding, errors="replace")


print("=== 1. LV data.gov.lv varis all resources & vietvardi ===")
d = json.loads(fetch("https://data.gov.lv/dati/api/3/action/package_show?id=varis-atvertie-dati"))
for res in d["result"]["resources"]:
  print(" VARIS:", res.get("name"), "|", res.get("format"), "|", res.get("url"))

r = json.loads(fetch("https://data.gov.lv/dati/api/3/action/package_search?q=vietvardi+OR+ciemu+koordinates&rows=10"))
for pkg in r["result"]["results"]:
  print(" LV GEO:", pkg["name"], "|", pkg["title"], "|", [(x.get("format"), x.get("url")) for x in pkg.get("resources", [])][:2])

print("\n=== 2. LV PxWeb RIG010 & IRD081 ===")
for u in [
  "https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP/IR/IRS/RIG010",
  "https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP/IR/IRD/IRD081",
  "https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP/IR/IRD/IRD080",
  "https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP/IR/A_IR/IRS030",
]:
  try:
    j = json.loads(fetch(u))
    print("PX:", u.split("/")[-1], "vars:", [(v["code"], len(v["values"]), v["values"][:5]) for v in j.get("variables", [])])
  except Exception as e:
    print("PX ERR:", u.split("/")[-1], e)

print("\n=== 3. Demoscope 1897 reg=17 (Kovno) & check towns ===")
h = fetch("https://www.demoscope.ru/weekly/ssp/rus_gub_97.php?reg=17", encoding="cp1251")
txt = re.sub(r"<[^>]+>", " ", h)
txt = re.sub(r"\s+", " ", txt)
print("Kovno 1897 text:", txt[:1200])
# Check if goroda links exist
print("Kovno links:", re.findall(r'href=["\']([^"\']+)["\'][^>]*>([^<]+)', h)[:20])

print("\n=== 4. lt.wikisource table HTML ===")
w = json.loads(fetch("https://lt.wikisource.org/w/api.php?action=parse&page=" + urllib.parse.quote("Lietuvos apgyventos vietos (1923)/Alytaus apskritis/Alovės valsčius") + "&prop=text&format=json"))
html = w["parse"]["text"]["*"]
idx = html.find("<table class=\"av\"")
print(html[idx:idx+2000] if idx != -1 else html[1500:3500])

print("\n=== 5. osp-rs.stat.gov.lt REST API ===")
for u in [
  "https://osp-rs.stat.gov.lt/rest_json/dataflow/LSD",
  "https://osp-rs.stat.gov.lt/rest_json/dataflow",
]:
  try:
    print("OSP REST:", u, "->", fetch(u)[:500])
  except Exception as e:
    print("OSP REST ERR:", u, e)
