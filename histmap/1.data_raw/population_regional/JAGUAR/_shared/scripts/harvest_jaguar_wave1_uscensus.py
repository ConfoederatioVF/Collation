import os, re, time, json, requests

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\settlement_sources\raw"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def dl(url, fname):
    out = os.path.join(RAW_DIR, fname)
    if os.path.exists(out) and os.path.getsize(out) > 2000:
        print(f"SKIP {fname} ({os.path.getsize(out):,} B)")
        return {"file": fname, "url": url, "bytes": os.path.getsize(out), "status": "cached"}
    t0 = time.time()
    r = requests.get(url, headers=H, timeout=180, stream=True)
    ct = r.headers.get("content-type", "")
    if r.status_code != 200 or ("text/html" in ct.lower()):
        print(f"FAIL {fname}: {r.status_code} ({ct})")
        r.close()
        return {"file": fname, "url": url, "status": f"fail_{r.status_code}"}
    with open(out, "wb") as f:
        for ch in r.iter_content(131072):
            if ch:
                f.write(ch)
    sz = os.path.getsize(out)
    print(f"OK {fname}: {sz:,} B in {time.time()-t0:.1f}s")
    return {"file": fname, "url": url, "bytes": sz, "status": "ok"}

res = []
# 1. Puerto Rico 2020 Redistricting PL 94-171 (all municipios, barrios, zonas urbanas, comunidades!)
res.append(dl(
    "https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Puerto_Rico/pr2020.pl.zip",
    "caribbean_pr_uscensus_2020_pl94171.zip"
))

# 2. Check & download Puerto Rico popest municipios 2020-2024 & 2010-2020 & USVI 2020
dirs = [
    "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/asrh/",
    "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/municipios/totals/",
    "https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/municipios/totals/",
    "https://www2.census.gov/programs-surveys/popest/tables/2020-2024/municipios/totals/",
    "https://www2.census.gov/programs-surveys/popest/tables/2010-2020/municipios/totals/",
    "https://www2.census.gov/programs-surveys/decennial/2020/data/island-areas/us-virgin-islands/",
    "https://www2.census.gov/programs-surveys/decennial/2020/data/island-areas/us-virgin-islands/demographic-profile/",
    "https://www2.census.gov/programs-surveys/decennial/2020/data/island-areas/us-virgin-islands/population-and-housing-unit-counts/",
    "https://www2.census.gov/programs-surveys/decennial/2010/data/01-Redistricting_File--PL_94-171/Puerto_Rico/",
]
for d in dirs:
    try:
        r = requests.get(d, headers=H, timeout=15)
        if r.status_code != 200:
            print(f"DIR {r.status_code}: {d[45:]}")
            continue
        links = [x for x in re.findall(r'href="([^"]+)"', r.text) if not x.startswith("http") and not x.startswith("/") and not x.startswith("?") and not x.startswith("css")]
        print(f"DIR 200 {d[45:]} -> {links[:12]}")
        for l in links:
            ll = l.lower()
            if ll.endswith((".csv", ".xlsx", ".xls", ".zip")) and ("prm" in ll or "pr2010" in ll or "vi" in ll or "virgin" in ll or "usvi" in ll):
                if "agesex" not in ll and "char" not in ll:
                    prefix = "caribbean_usvi_uscensus_" if ("vi" in ll or "virgin" in ll) else "caribbean_pr_uscensus_"
                    res.append(dl(d + l, prefix + l))
    except Exception as e:
        print("DIR ERR:", d[45:], e)

# 3. Also check local inegi_ehm2014_1_poblacion.pdf table of contents using fitz if available
try:
    import fitz
    pdf = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\subadmin_hgis\raw_sources\inegi_ehm2014_1_poblacion.pdf"
    doc = fitz.open(pdf)
    print(f"INEGI EHM 2014 PDF: {len(doc)} pages")
    for i in range(min(8, len(doc))):
        txt = doc[i].get_text()
        if "1." in txt or "Índice" in txt or "Contenido" in txt or "ciudad" in txt.lower() or "localidad" in txt.lower():
            print(f"  Page {i+1}:", txt[:350].replace("\n", " | "))
    doc.close()
except Exception as e:
    print("PDF check err:", e)

with open(os.path.join(RAW_DIR, "_uscensus_extra_log.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2)
