"""Parse Mexico INEGI EHM 2014 + CPV 2020 and fetch CBS Caribbean Netherlands."""

import json
import os
import re
import urllib.request

import openpyxl
import pymupdf

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\subadmin_hgis\raw_sources"


def parse_mexico_inegi ():
  doc = pymupdf.open(os.path.join(RAW_DIR, "inegi_ehm2014_1_poblacion.pdf"))
  full_text = ""
  for p in range(119, 134):
    full_text += "\n<<<PAGE %d>>>\n" % (p + 1) + doc[p].get_text("text")

  parts = re.split(r"(?=Población total del (?:estado|Distrito Federal))", full_text)
  states = {}
  for part in parts[1:]:
    m_hdr = re.match(r"Población total del (?:estado\s*(?:de\s*)?|)(.+?)\s*Cuadro\s+(1\.\d+)", part, re.S)
    if not m_hdr:
      continue
    st_name = re.sub(r"\s+", " ", m_hdr.group(1)).strip()
    st_name = re.sub(r"^estado\s+de\s+", "", st_name)
    cuadro = m_hdr.group(2)
    if int(cuadro.split(".")[1]) > 50:
      continue
    body = re.split(r"\n(?:a |INEGI\.)", part)[0]
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    yr_data = {}
    i = 0
    while i < len(lines):
      m_yr = re.match(r"^(\d{4})(?:\s+[a-z])?$", lines[i])
      if m_yr and i + 1 < len(lines):
        yr = int(m_yr.group(1))
        m_pop = re.match(r"^(\d[\d\s]*\d|\d)$", lines[i + 1])
        if m_pop:
          pop = int(m_pop.group(1).replace(" ", ""))
          src = lines[i + 2] if i + 2 < len(lines) else ""
          if str(yr) not in yr_data or "Censo" in src or "Conteo" in src or "Busto" in src:
            yr_data[str(yr)] = {"pop": pop, "src": src}
          i += 2
          continue
      i += 1
    states[st_name] = {"cuadro": cuadro, "years": yr_data}

  print("Parsed states from EHM 2014:", len(states))
  wb = openpyxl.load_workbook(os.path.join(RAW_DIR, "inegi_cpv2020_01_poblacion.xlsx"), read_only=True, data_only=True)
  ws = wb["01"]
  pop2020 = {}
  for row in ws.iter_rows(values_only=True):
    if row[0] and row[1] == "Población":
      nm = re.sub(r"^\d{2}\s+", "", str(row[0]).strip())
      pop2020[nm] = int(row[2])

  print("Parsed 2020 entities:", len(pop2020), "National:", pop2020.get("Estados Unidos Mexicanos"))

  census_yrs = ["1830", "1857", "1877", "1895", "1900", "1910", "1921", "1930", "1940", "1950", "1960", "1970", "1980", "1990", "1995", "2000", "2005", "2010"]
  for y in census_yrs:
    s = sum(v["years"][y]["pop"] for v in states.values() if y in v["years"])
    cnt = sum(1 for v in states.values() if y in v["years"])
    missing = [k for k, v in states.items() if y not in v["years"]]
    print(f"  {y}: {cnt:2d} states -> sum = {s:,} | missing ({len(missing)}): {missing[:5]}")

  for st in sorted(states):
    ys = sorted(int(y) for y in states[st]["years"])
    c = states[st]["cuadro"]
    print(f"  {c:5s} {st:34s}: {len(ys):2d} yrs ({ys[0]}..{ys[-1]})")

  with open(os.path.join(RAW_DIR, "mexico_inegi_parsed.json"), "w", encoding="utf-8") as f:
    json.dump({"ehm2014": states, "cpv2020": pop2020}, f, ensure_ascii=False, indent=2)


def fetch_cbs_caribbean_nl ():
  url = (
    "https://opendata.cbs.nl/ODataApi/odata/83698ENG/TypedDataSet"
    "?$filter=Sex%20eq%20'T001038'%20and%20Age%20eq%20'10000'%20and%20MaritalStatus%20eq%20'T001019'"
  )
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
  with urllib.request.urlopen(req, timeout=20) as r:
    cbs_rows = json.loads(r.read())["value"]
  cbs_out = {}
  rmap = {"CN01  ": "Caribbean Netherlands", "GM9001": "Bonaire", "GM9002": "Sint Eustatius", "GM9003": "Saba"}
  for row in cbs_rows:
    reg = rmap.get(row["CaribbeanNetherlands"], row["CaribbeanNetherlands"])
    yr = row["Periods"][:4]
    val = row["PopulationOnJanuary1st_1"]
    if val is not None:
      cbs_out.setdefault(reg, {})[yr] = int(val)
  print("\nCBS Caribbean Netherlands fetched:")
  for k, v in cbs_out.items():
    ys = sorted(v)
    print(f"  {k:24s}: {len(ys)} yrs ({ys[0]}={v[ys[0]]:,} .. {ys[-1]}={v[ys[-1]]:,})")
  with open(os.path.join(RAW_DIR, "cbs_caribbean_netherlands.json"), "w", encoding="utf-8") as f:
    json.dump(cbs_out, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
  parse_mexico_inegi()
  fetch_cbs_caribbean_nl()
