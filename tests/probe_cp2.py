import json
import re
import urllib.request
import urllib.parse

# 1. CityPopulation LT locality rows & LV region page
for u in [
  "https://www.citypopulation.de/en/lithuania/alytus/",
  "https://www.citypopulation.de/en/latvia/admin/LV005__latgale/",
]:
  h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read().decode("utf-8", errors="replace")
  trs = re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S)
  print("=== CP:", u, "total trs:", len(trs), "===")
  for tr in trs[10:22]:
    tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
    if tds:
      print(" ", tds[:8])

# 2. LV Wiki Latvijas_pilsetu_uzskaitijums
u = "https://lv.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=content&titles=" + urllib.parse.quote("Latvijas_pilsētu_uzskaitījums") + "&format=json"
j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "SVEA-Bot/1.0"}), timeout=20).read().decode("utf-8"))
pg = next(iter(j["query"]["pages"].values()))
txt = pg["revisions"][0]["*"]
print("\n=== Latvijas_pilsetu_uzskaitijums (len", len(txt), ") ===")
print(txt[:2500])
