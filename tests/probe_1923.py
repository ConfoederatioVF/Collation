import json
import re
import urllib.request
import urllib.parse

# Check Archive.org 1923 Lithuanian census djvu.txt and lt.wikisource Kauno miestas & Alytaus miestas
print("=== 1. IA 1923 djvu.txt sample ===")
req = urllib.request.Request(
  "https://archive.org/download/lietuvos-apgyventos-vietos-1925/" + urllib.parse.quote("Lietuvos apgyventos vietos, 1925_djvu.txt"),
  headers={"User-Agent": "Mozilla/5.0", "Range": "bytes=40000-46000"}
)
with urllib.request.urlopen(req, timeout=25) as r:
  print(r.read().decode("utf-8", errors="replace")[:2000])

print("\n=== 2. lt.wikisource Anyksciu valscius & Kauno miestas ===")
for pg in [
  "Lietuvos apgyventos vietos (1923)/Kauno miestas",
  "Lietuvos apgyventos vietos (1923)/Utenos apskritis/Anykščių valsčius",
]:
  u = "https://lt.wikisource.org/w/api.php?action=parse&page=" + urllib.parse.quote(pg) + "&prop=text&format=json"
  j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read().decode("utf-8"))
  html = j["parse"]["text"]["*"]
  rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
  print("PAGE:", pg, "rows:", len(rows))
  for tr in rows[2:10]:
    tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", td)).strip() for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
    print(" ", tds[:6])
