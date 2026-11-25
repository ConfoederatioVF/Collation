import json
import re
import urllib.request
import urllib.parse


def fetch(url, encoding="utf-8"):
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
  with urllib.request.urlopen(req, timeout=25) as r:
    return r.read().decode(encoding, errors="replace")


print("=== 1. lt.wikisource rendered text sample ===")
w = json.loads(fetch("https://lt.wikisource.org/w/api.php?action=parse&page=" + urllib.parse.quote("Lietuvos apgyventos vietos (1923)/Alytaus apskritis/Alovės valsčius") + "&prop=text&format=json"))
print(w["parse"]["text"]["*"][:2500])

print("\n=== 2. Demoscope rus_gub_97.php all links & options ===")
h = fetch("https://www.demoscope.ru/weekly/ssp/rus_gub_97.php", encoding="cp1251")
print("options:", re.findall(r'<option[^>]*value=["\']?([^"\'>\s]+)["\']?[^>]*>([^<]+)', h, re.I)[:20])
print("forms:", re.findall(r'<form[^>]*>', h, re.I))
print("scripts/links:", re.findall(r'(?:href|src)=["\']([^"\']+)["\']', h, re.I)[:30])

print("\n=== 3. data.gov.lv rig010_01.csv & aw_pilseta.csv & aw_ciems.csv sample ===")
for u in [
  "https://data.gov.lv/dati/dataset/ac38cc49-fb8c-492f-817b-4595a3576c04/resource/83da473d-68e1-4120-93f4-817bafce88a2/download/rig010_01.csv",
  "https://data.gov.lv/dati/dataset/6b06a7e8-dedf-4705-a47b-2a7c51177473/resource/ee02baa4-2bc3-4f77-a6cb-5427a3e9befe/download/aw_pilseta.csv",
  "https://data.gov.lv/dati/dataset/6b06a7e8-dedf-4705-a47b-2a7c51177473/resource/0d3810f4-1ac0-4fba-8b10-0188084a361b/download/aw_ciems.csv",
]:
  req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Range": "bytes=0-1500"})
  with urllib.request.urlopen(req, timeout=20) as r:
    print("FILE:", u.split("/")[-1])
    print(r.read().decode("utf-8", errors="replace")[:700])
