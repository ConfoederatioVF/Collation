import json
import re
import urllib.request
import urllib.parse


def fetch(url, encoding="utf-8"):
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
  with urllib.request.urlopen(req, timeout=25) as r:
    return r.read().decode(encoding, errors="replace")


print("=== 1. Demoscope 1897 full Kovno table & Suwalki reg ===")
h = fetch("https://www.demoscope.ru/weekly/ssp/rus_gub_97.php?reg=17", encoding="cp1251")
opts = re.findall(r'<option[^>]*value=["\']?([^"\'>\s]+)["\']?[^>]*>([^<]+)', h, re.I)
for v, t in opts:
  if any(k in t.lower() for k in ["сувалк", "лифлянд", "курлянд", "вилен", "витеб", "ковен", "гроднен"]):
    print(" OPT:", v, t.strip())
idx = h.find("<table")
print("Kovno tables:", len(re.findall(r"<table", h, re.I)))
# print text after select
s_end = h.find("</select>")
txt = re.sub(r"<[^>]+>", " ", h[s_end:])
txt = re.sub(r"\s+", " ", txt)
print("Kovno body:", txt[:1500])

print("\n=== 2. data.gov.lv iedzivotaji metadata & aw_vietu_centroidi ===")
for u in [
  "https://data.gov.lv/dati/dataset/6b06a7e8-dedf-4705-a47b-2a7c51177473/resource/68f1152c-0f4c-4fc3-abb3-df4b8bfea992/download/aw_vietu_centroidi.csv",
]:
  req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Range": "bytes=0-1200"})
  with urllib.request.urlopen(req, timeout=20) as r:
    print("aw_vietu_centroidi:", r.read().decode("utf-8", errors="replace")[:700])

d = json.loads(fetch("https://data.gov.lv/dati/api/3/action/package_show?id=iedzivotaji"))
for res in d["result"]["resources"]:
  if "meta" in (res.get("name") or "").lower() or res.get("format") == "JSON" or "rig010" in (res.get("url") or "").lower():
    print("LV RES:", res.get("name"), "|", res.get("format"), "|", res.get("url"))

print("\n=== 3. Archive.org slownik-* ===")
u = "https://archive.org/advancedsearch.php?q=" + urllib.parse.quote("identifier:slownik-*") + "&fl[]=identifier,title&rows=50&output=json"
res = json.loads(fetch(u))
for doc in sorted(res["response"]["docs"], key=lambda x: x["identifier"]):
  print(" ", doc["identifier"], "|", doc.get("title", "")[:70])

print("\n=== 4. lt.wikisource allpages 1923 ===")
w = json.loads(fetch("https://lt.wikisource.org/w/api.php?action=query&list=categorymembers&cmtitle=Kategorija:Lietuvos_apgyventos_vietos_(1923)&cmlimit=500&format=json"))
cm = w["query"]["categorymembers"]
print("total cat members:", len(cm))
counties = [x["title"] for x in cm if x["title"].count("/") == 1]
print("counties:", counties)
