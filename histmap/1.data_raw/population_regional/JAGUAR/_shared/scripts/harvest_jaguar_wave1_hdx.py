import os
import json
import time
import requests

RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\JAGUAR\_shared\settlement_sources\raw\hdx_cod_ps"
os.makedirs(RAW_DIR, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

JURISDICTION_MAP = {
    # Central America
    "gtm": "central_america", "blz": "central_america", "hnd": "central_america",
    "slv": "central_america", "nic": "central_america", "cri": "central_america",
    "pan": "central_america",
    # Caribbean & Bermuda
    "cub": "caribbean", "hti": "caribbean", "dom": "caribbean", "jam": "caribbean",
    "tto": "caribbean", "brb": "caribbean", "bhs": "caribbean", "atg": "caribbean",
    "dma": "caribbean", "grd": "caribbean", "lca": "caribbean", "vct": "caribbean",
    "kna": "caribbean", "bmu": "caribbean", "abw": "caribbean", "cuw": "caribbean",
    "sxm": "caribbean", "bes": "caribbean", "cym": "caribbean", "tca": "caribbean",
    "vgb": "caribbean", "aia": "caribbean", "msr": "caribbean",
    # Mexico
    "mex": "mexico",
}

manifest = []
for iso, jur in JURISDICTION_MAP.items():
    try:
        # Search for cod-ps first, fallback to subnational population statistics
        r = requests.get(f"https://data.humdata.org/api/3/action/package_search?q=cod-ps-{iso}&rows=5", headers=HEADERS, timeout=20).json()
        pkgs = r.get("result", {}).get("results", [])
        chosen = None
        for p in pkgs:
            if p.get("name", "").lower() == f"cod-ps-{iso}":
                chosen = p
                break
        if not chosen:
            r2 = requests.get(f"https://data.humdata.org/api/3/action/package_search?q=cod-ps+{iso}&rows=5", headers=HEADERS, timeout=20).json()
            for p in r2.get("result", {}).get("results", []):
                if iso in p.get("name", "").lower() and ("pop" in p.get("name", "").lower() or "ps" in p.get("name", "").lower()):
                    chosen = p
                    break
        if not chosen:
            # Try general population statistics for smaller islands
            r3 = requests.get(f"https://data.humdata.org/api/3/action/package_search?fq=groups:{iso}&q=population&rows=5", headers=HEADERS, timeout=20).json()
            for p in r3.get("result", {}).get("results", []):
                if any(k in p.get("title", "").lower() for k in ("subnational population", "population statistics", "census")):
                    chosen = p
                    break
        if not chosen:
            print(f"NO HDX POP PKG: {iso}")
            continue

        pkg_name = chosen["name"]
        pkg_url = f"https://data.humdata.org/dataset/{pkg_name}"
        source_org = chosen.get("dataset_source", "") or chosen.get("organization", {}).get("title", "")
        resources = chosen.get("resources", [])

        # Download ALL CSVs with adm1/adm2/adm3/adm4 or pop in name, plus main admpop xlsx if no detailed csv
        dl_res = []
        csv_res = [x for x in resources if x.get("format", "").lower() == "csv" and "pop" in x.get("name", "").lower()]
        xlsx_res = [x for x in resources if x.get("format", "").lower() in ("xlsx", "xls") and ("pop" in x.get("name", "").lower() or "census" in x.get("name", "").lower())]

        targets = []
        # Always grab the finest CSV levels (adm2, adm3, adm4, or adm1 if smallest island)
        for x in csv_res:
            nm = x["name"].lower()
            if any(lvl in nm for lvl in ("adm2", "adm3", "adm4", "adm1", "pop")):
                if "adm0" not in nm:
                    targets.append(x)
        # Also grab the primary population workbook if available and <= 15MB
        if not targets and xlsx_res:
            targets.append(xlsx_res[0])
        elif xlsx_res:
            # Check if there's a unified workbook that might have deeper sheets
            for x in xlsx_res:
                if "uncertainty" not in x["name"].lower() and "gz" not in x["name"].lower():
                    targets.append(x)
                    break

        for res in targets:
            rname = res["name"]
            safe_name = f"{jur}_{iso}_{rname}".replace(" ", "_").replace("/", "_")
            out_path = os.path.join(RAW_DIR, safe_name)
            url = res["url"]
            if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
                sz = os.path.getsize(out_path)
                dl_res.append({"file": safe_name, "bytes": sz, "url": url, "format": res.get("format", "")})
                continue
            try:
                resp = requests.get(url, headers=HEADERS, timeout=60)
                if resp.status_code == 200 and len(resp.content) > 100:
                    with open(out_path, "wb") as f:
                        f.write(resp.content)
                    sz = len(resp.content)
                    print(f"OK [{iso}] {safe_name} ({sz:,} B)")
                    dl_res.append({"file": safe_name, "bytes": sz, "url": url, "format": res.get("format", "")})
                else:
                    print(f"FAIL {resp.status_code} [{iso}] {rname}")
            except Exception as e:
                print(f"ERR [{iso}] {rname}: {e}")

        if dl_res:
            manifest.append({
                "iso3": iso,
                "jurisdiction": jur,
                "package": pkg_name,
                "title": chosen.get("title", ""),
                "dataset_source": source_org,
                "package_url": pkg_url,
                "files": dl_res,
            })
    except Exception as e:
        print(f"PKG ERR [{iso}]: {e}")

with open(os.path.join(RAW_DIR, "_hdx_download_log.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
print(f"DONE HDX COD-PS: {len(manifest)} countries/territories downloaded.")
