import json
import os
import urllib.request

DL = "tests/dl"
os.makedirs(DL, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def dl(url, fname):
  fp = os.path.join(DL, fname)
  if os.path.exists(fp) and os.path.getsize(fp) > 500:
    print("SKIP", fname, os.path.getsize(fp))
    return fp
  req = urllib.request.Request(url, headers=UA)
  with urllib.request.urlopen(req, timeout=120) as r, open(fp, "wb") as f:
    while True:
      c = r.read(262144)
      if not c:
        break
      f.write(c)
  print("OK", fname, os.path.getsize(fp))
  return fp


# 1. Inspect existing pale_east_prussia jsons
for fn in ["wd_belarus_towns.json", "wd_kaliningrad.json", "wd_moldova_direct.json"]:
  p = "histmap/1.data_raw/population_regional/MAGNETIC/_shared/settlement_sources/pale_east_prussia/" + fn
  d = json.load(open(p, encoding="utf-8"))
  print(fn, type(d), len(d), str(d[:1])[:200] if isinstance(d, list) else str(list(d.items())[:1])[:200])

# 2. Download pop-stat.mashke.org LT & LV files
urls = [
  ("http://pop-stat.mashke.org/lithuania-cities.htm", "ps_lt_cities.htm"),
  ("http://pop-stat.mashke.org/lithuania-census1959-1970.htm", "ps_lt_1959_1970.htm"),
  ("http://pop-stat.mashke.org/lithuania-census1979.htm", "ps_lt_1979.htm"),
  ("http://pop-stat.mashke.org/lithuania-census1989.htm", "ps_lt_1989.htm"),
  ("http://pop-stat.mashke.org/lithuania-census2001.htm", "ps_lt_2001.htm"),
  ("http://pop-stat.mashke.org/lithuania-census2011.htm", "ps_lt_2011.htm"),
  ("http://pop-stat.mashke.org/lithuania-census2021.htm", "ps_lt_2021.htm"),
  ("http://pop-stat.mashke.org/latvia-cities.htm", "ps_lv_cities.htm"),
  ("https://data.gov.lv/dati/dataset/ac38cc49-fb8c-492f-817b-4595a3576c04/resource/69956a7b-32f2-48df-a149-9ff29882c9dd/download/ird081_01.zip", "ird081_01.zip"),
  ("https://archive.org/download/nasmesta/nasmesta_djvu.xml", "nasmesta_djvu.xml"),
]
for u, fn in urls:
  dl(u, fn)
