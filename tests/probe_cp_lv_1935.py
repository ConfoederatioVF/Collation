import json
import re
import ssl
import urllib.request
import urllib.parse

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 1. Check citypopulation.de LT county & city subpage
for u in [
  "https://www.citypopulation.de/en/lithuania/alytus/",
  "https://www.citypopulation.de/en/lithuania/alytus/alytus/01204008__daugai/",
  "https://www.citypopulation.de/en/latvia/kurzeme/dienvidkurzemes_novads/LV002720000__aizpute/",
]:
  h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read().decode("utf-8", errors="replace")
  ths = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip() for x in re.findall(r"<th[^>]*>(.*?)</th>", h, re.S)]
  coords = re.findall(r"(\d{2}\.\d+,\s*\d{2}\.\d+|data-lat=[\"'][^\"']+[\"']|lat[\"']?\s*:\s*\d+\.\d+)", h)
  print("=== CP:", u, "===")
  print("  ths:", ths[:15])
  print("  coords:", coords[:5])
  trs = re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S)
  print("  rows:", len(trs))
  for tr in trs[:6]:
    tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
    if tds:
      print("   ", tds[:10])

# 2. Check lv.wikipedia.org Latvijas pilsētas & Rīga / Daugavpils / Liepāja wikitext for 1920-1935 census citations
for title in ["Latvijas_pilsētas", "Daugavpils", "Cēsis"]:
  u = "https://lv.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=content&titles=" + urllib.parse.quote(title) + "&format=json"
  j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "SVEA-Bot/1.0"}), timeout=20).read().decode("utf-8"))
  pg = next(iter(j["query"]["pages"].values()))
  txt = pg["revisions"][0]["*"]
  print(f"\n=== LV WIKI {title} (len {len(txt)}) ===")
  for m in re.finditer(r"(1920|1925|1930|1935)", txt):
    s = max(0, m.start() - 40)
    print(" ", txt[s:s+140].replace("\n", " "))
    break
  if title == "Latvijas_pilsētas":
    print(txt[:1500])

# 3. Check stat.gov.lv search or publications API
for u in [
  "https://stat.gov.lv/lv/meklesana?search=tautas+skait%C4%AB%C5%A1ana+1935",
  "https://stat.gov.lv/en/node/611",
]:
  try:
    h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20, context=ctx).read().decode("utf-8", errors="replace")
    pdfs = re.findall(r'href=["\']([^"\']*\.pdf[^"\']*)["\']', h, re.I)
    print("stat.gov.lv:", u, "pdfs:", pdfs[:10])
  except Exception as e:
    print("stat.gov.lv err:", u, e)
