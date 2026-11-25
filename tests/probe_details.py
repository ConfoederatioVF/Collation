import json
import re
import urllib.request
import urllib.parse


def fetch(url, encoding="utf-8"):
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
  with urllib.request.urlopen(req, timeout=30) as r:
    return r.read().decode(encoding, errors="replace")


print("=== 1. Demoscope Kovno table (past select) ===")
h = fetch("https://www.demoscope.ru/weekly/ssp/rus_gub_97.php?reg=17", encoding="cp1251")
s_end = h.find("</select>")
txt = re.sub(r"<[^>]+>", " ", h[s_end:])
txt = re.sub(r"\s+", " ", txt)
print("len:", len(txt))
print(txt[1200:3500])

print("\n=== 2. Archive.org nasmesta_djvu.txt search for Ковенская / Курляндская ===")
req = urllib.request.Request("https://archive.org/download/nasmesta/nasmesta_djvu.txt", headers={"User-Agent": "Mozilla/5.0", "Range": "bytes=0-15000"})
with urllib.request.urlopen(req, timeout=25) as r:
  head = r.read().decode("utf-8", errors="replace")
print("nasmesta head:", head[:1500])

print("\n=== 3. Archive.org slownik-4 metadata ===")
m = json.loads(fetch("https://archive.org/metadata/slownik-4"))
print("slownik-4 files:", [(f["name"], f.get("size")) for f in m.get("files", [])][:12])

print("\n=== 4. Test govlt/powerbi-map-lt & Eurostat urb_cpop1 LT/LV cities ===")
import csv
with open("histmap/1.data_raw/population_regional/MAGNETIC/_shared/settlement_sources/eurostat_urb_cpop1_1990_2024.csv", encoding="utf-8") as f:
  r = csv.DictReader(f)
  cities = set()
  for row in r:
    c = row.get("cities", "")
    if c.startswith(("LT", "LV")) and len(c) > 2:
      cities.add(c)
print("eurostat cities:", sorted(cities))

print("\n=== 5. Check Wikisource index of 1923 Lithuanian Census ===")
w = json.loads(fetch("https://lt.wikisource.org/w/api.php?action=parse&page=" + urllib.parse.quote("Lietuvos apgyventos vietos (1923)") + "&prop=text&format=json"))
txt1923 = re.sub(r"<[^>]+>", " ", w["parse"]["text"]["*"])
print("1923 main page:", re.sub(r"\s+", " ", txt1923)[:1500])
