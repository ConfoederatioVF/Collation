import json
import re
import urllib.request
import urllib.parse


def fetch(url, encoding="utf-8"):
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
  with urllib.request.urlopen(req, timeout=25) as r:
    return r.read().decode(encoding, errors="replace")


print("=== 1. LV PxWeb POP full tree ===")
pop = json.loads(fetch("https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP"))
print("POP nodes:", pop)
for node in pop:
  if node["type"] == "l":
    sub = json.loads(fetch("https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/POP/" + node["id"]))
    print("  SUB", node["id"], ":", [(x["id"], x["type"], x["text"][:80]) for x in sub])

print("\n=== 2. Archive.org nasmesta metadata ===")
m = json.loads(fetch("https://archive.org/metadata/nasmesta"))
print("nasmesta files:", [(f["name"], f.get("size")) for f in m.get("files", [])][:15])

print("\n=== 3. Demoscope 1897 links (cp1251) ===")
h = fetch("https://www.demoscope.ru/weekly/ssp/rus_gub_97.php", encoding="cp1251")
links = re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', h, re.S | re.I)
for href, txt in links:
  clean = re.sub(r"<[^>]+>", " ", txt).strip()
  if any(k in clean.lower() for k in ["ковен", "вилен", "курлянд", "лифлянд", "витебск", "сувалк", "город"]):
    print(" ", href, "|", clean[:70])

print("\n=== 4. lt.wikisource sample 1923 page ===")
w = json.loads(fetch("https://lt.wikisource.org/w/api.php?action=parse&page=" + urllib.parse.quote("Lietuvos apgyventos vietos (1923)/Alytaus apskritis/Alovės valsčius") + "&prop=wikitext&format=json"))
print(w["parse"]["wikitext"]["*"][:1200])
