import csv
import json
import os
import re
import urllib.request
import urllib.parse

DL_DIR = "tests/dl"
os.makedirs(DL_DIR, exist_ok=True)


def fetch(url, encoding="utf-8"):
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
  with urllib.request.urlopen(req, timeout=40) as r:
    return r.read().decode(encoding, errors="replace")


def download(url, fname):
  fp = os.path.join(DL_DIR, fname)
  if os.path.exists(fp) and os.path.getsize(fp) > 100:
    return fp
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
  with urllib.request.urlopen(req, timeout=120) as r, open(fp, "wb") as f:
    while True:
      ch = r.read(262144)
      if not ch:
        break
      f.write(ch)
  return fp


print("=== 1. Demoscope 1897 governorate pages ===")
h0 = fetch("https://www.demoscope.ru/weekly/ssp/rus_gub_97.php", encoding="cp1251")
opts = re.findall(r'<option[^>]*value=["\']?([^"\'>\s]+)["\']?[^>]*>([^<]+)', h0, re.I)
for v, t in opts:
  if any(k in t.lower() for k in ["вилен", "витеб", "ковен", "курлянд", "лифлянд", "сувалк", "гроднен"]):
    print("GUB:", v, t.strip())
    hg = fetch(f"https://www.demoscope.ru/weekly/ssp/rus_gub_97.php?reg={v}", encoding="cp1251")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", hg, re.S | re.I)
    for tr in rows:
      tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", td)).strip() for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
      if len(tds) >= 5 and ("г." in tds[0] or "посад" in tds[0] or "м." in tds[0]):
        print("  TOWN:", tds[:6])

print("\n=== 2. LV data.gov.lv download & inspect ===")
lv_files = {
  "aw_pilseta.csv": "https://data.gov.lv/dati/dataset/6b06a7e8-dedf-4705-a47b-2a7c51177473/resource/ee02baa4-2bc3-4f77-a6cb-5427a3e9befe/download/aw_pilseta.csv",
  "aw_ciems.csv": "https://data.gov.lv/dati/dataset/6b06a7e8-dedf-4705-a47b-2a7c51177473/resource/0d3810f4-1ac0-4fba-8b10-0188084a361b/download/aw_ciems.csv",
  "aw_vietu_centroidi.csv": "https://data.gov.lv/dati/dataset/6b06a7e8-dedf-4705-a47b-2a7c51177473/resource/68f1152c-0f4c-4fc3-abb3-df4b8bfea992/download/aw_vietu_centroidi.csv",
  "rig010_01.csv": "https://data.gov.lv/dati/dataset/ac38cc49-fb8c-492f-817b-4595a3576c04/resource/83da473d-68e1-4120-93f4-817bafce88a2/download/rig010_01.csv",
  "ird080_01.csv": "https://data.gov.lv/dati/dataset/ac38cc49-fb8c-492f-817b-4595a3576c04/resource/c842bb5d-2c2a-4c53-bce1-e060ff7f1dd9/download/ird080_01.csv",
}
for fn, u in lv_files.items():
  fp = download(u, fn)
  print("DL:", fn, os.path.getsize(fp))

# Check iedzivotaji metadata resources
pkg = json.loads(fetch("https://data.gov.lv/dati/api/3/action/package_show?id=iedzivotaji"))
for res in pkg["result"]["resources"]:
  if "rig010" in (res.get("url") or "").lower() or "ird08" in (res.get("url") or "").lower() or "kodi" in (res.get("name") or "").lower() or res.get("format") in ("JSON", "XLSX"):
    print("IEDZ RES:", res.get("name"), "|", res.get("format"), "|", res.get("url"))

print("\n=== 3. Check nasmesta_djvu.txt download ===")
fp_nas = download("https://archive.org/download/nasmesta/nasmesta_djvu.txt", "nasmesta_djvu.txt")
print("nasmesta_djvu.txt size:", os.path.getsize(fp_nas))
txt_nas = open(fp_nas, encoding="utf-8", errors="replace").read()
for m in re.finditer(r"(Ковенская|Курляндская|Виленская|Лифляндская|Витебская)\s+губерн", txt_nas):
  print("NAS MATCH:", m.group(0), "at", m.start())
  print(txt_nas[m.start():m.start()+600].replace("\n", " | "))
