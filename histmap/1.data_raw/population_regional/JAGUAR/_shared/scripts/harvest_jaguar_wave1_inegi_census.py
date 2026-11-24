import os, re, time, json, requests

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\settlement_sources\raw"
os.makedirs(RAW_DIR, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def dl(url, fname):
    out = os.path.join(RAW_DIR, fname)
    if os.path.exists(out) and os.path.getsize(out) > 10000:
        print(f"SKIP {fname} ({os.path.getsize(out):,} B)")
        return {"file": fname, "url": url, "bytes": os.path.getsize(out), "status": "cached"}
    t0 = time.time()
    r = requests.get(url, headers=H, timeout=300, stream=True)
    ct = r.headers.get("content-type", "")
    if r.status_code != 200 or ("text/html" in ct.lower() and not fname.endswith(".html")):
        print(f"FAIL {fname}: HTTP {r.status_code} ({ct})")
        r.close()
        return {"file": fname, "url": url, "status": f"fail_{r.status_code}_{ct}"}
    with open(out, "wb") as f:
        for ch in r.iter_content(262144):
            if ch:
                f.write(ch)
    sz = os.path.getsize(out)
    print(f"OK {fname}: {sz:,} B in {time.time()-t0:.1f}s")
    return {"file": fname, "url": url, "bytes": sz, "status": "ok"}

results = []
# 1. Official INEGI ITER 1990, 2000, 2010, 2020 (ALL Mexican localities!)
inegi_files = [
    ("https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/iter/iter_00_cpv2020_csv.zip", "mexico_inegi_iter_2020_csv.zip"),
    ("https://www.inegi.org.mx/contenidos/programas/ccpv/2010/datosabiertos/iter_nal_2010_csv.zip", "mexico_inegi_iter_2010_csv.zip"),
    ("https://www.inegi.org.mx/contenidos/programas/ccpv/2000/datosabiertos/cgpv2000_iter_00_csv.zip", "mexico_inegi_iter_2000_csv.zip"),
    ("https://www.inegi.org.mx/contenidos/programas/ccpv/1990/microdatos/iter/00_nacional_1990_iter_txt.zip", "mexico_inegi_iter_1990_txt.zip"),
]
for u, fn in inegi_files:
    results.append(dl(u, fn))

# 2. Discover & download official US Census Bureau Puerto Rico CSVs from www2.census.gov
pr_dirs = [
    ("https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/", "prm-est"),
    ("https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/counties/totals/", "prm-est"),
    ("https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/counties/totals/", "prm-est"),
    ("https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/puerto-rico/", "prm-est"),
]
seen_pr = set()
for durl, prefix in pr_dirs:
    try:
        r = requests.get(durl, headers=H, timeout=20)
        csvs = re.findall(r'href="([^"]+\.(?:csv|xlsx|xls))"', r.text, re.I)
        print("CENSUS DIR", durl[-45:], "->", csvs[:10])
        for c in csvs:
            if "prm" in c.lower() or "puerto" in c.lower() or "72" in c.lower():
                if c not in seen_pr:
                    seen_pr.add(c)
                    results.append(dl(durl + c, f"caribbean_pr_uscensus_{c}"))
    except Exception as e:
        print("CENSUS DIR ERR:", e)

# 3. Also check US Census Puerto Rico places/cities (2020 PL 94-171 or sub-est) & USVI 2020/2010
for durl in [
    "https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Puerto_Rico/",
    "https://www2.census.gov/programs-surveys/decennial/2020/data/island-areas/",
    "https://www2.census.gov/programs-surveys/decennial/2010/data/02-Island_Areas/",
]:
    try:
        r = requests.get(durl, headers=H, timeout=20)
        links = [x for x in re.findall(r'href="([^"]+)"', r.text) if not x.startswith("http") and not x.startswith("/") and not x.startswith("?") and not x.startswith("css")]
        print("DEC DIR", durl[45:], "->", links[:15])
    except Exception as e:
        print("DEC DIR ERR:", e)

# 4. INSEE historical series via data.gouv.fr API
try:
    r = requests.get("https://www.data.gouv.fr/api/1/datasets/?q=serie+historique+recensement+population+communes&page_size=5", headers=H, timeout=20).json()
    for ds in r.get("data", []):
        res = [x.get("url") for x in ds.get("resources", []) if x.get("url", "").endswith(".zip") or x.get("url", "").endswith(".csv")]
        if res:
            print("DATAGOUV:", ds.get("title","")[:60], "->", res[:3])
except Exception as e:
    print("DATAGOUV ERR:", e)

with open(os.path.join(RAW_DIR, "_inegi_census_download_log.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
