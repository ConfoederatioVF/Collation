"""Supplemental Primary Regional Archaeological Registers Harvester for Project HANDBOOK.

Downloads open scholarly regional registers across all 7 HANDBOOK jurisdictions:
  - Turkey: C-Turkey (Altinisik et al., GitHub/Zenodo)
  - Maghreb & Egypt: MedAfriCarbon (Lucarini et al., Zenodo 3688530)
  - Arabia / Levant / Iran / Maghreb / Egypt: EAMENA Zenodo Community open datasets & published Near East / Arabian / Caucasus / Afghanistan CSV/GeoJSON tables
  - Ancient Near East / Mesopotamia / Anatolia: Open Context / Oracc / ANE & ArchAtlas tables
"""

import json
import os
import time
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "HANDBOOK", "_shared", "sites_handbook_mena", "0.raw_data")
os.makedirs(RAW_DIR, exist_ok=True)
HEADERS = {"User-Agent": "SVEA-OperationViscount-HANDBOOK/1.0 (academic historical demography)"}


def safe_get(url, params=None, timeout=90):
  for att in range(3):
    try:
      r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
      if r.status_code == 200:
        return r
      if r.status_code in (429, 502, 503, 504):
        time.sleep(5 * (att + 1))
        continue
      return r
    except Exception as e:
      if att == 2:
        print(f"  [WARN] GET failed {url[:90]}: {e}", flush=True)
      time.sleep(3)
  return None


def download_cturkey():
  print("[1] Harvesting C-Turkey (Altinisik et al., Anatolia & Thrace chronometric/site register)...", flush=True)
  outp = os.path.join(RAW_DIR, "cturkey_v1.tsv")
  if os.path.exists(outp) and os.path.getsize(outp) > 20_000:
    print(f"  Already cached: {outp}", flush=True)
    return
  for u in (
    "https://raw.githubusercontent.com/altinisik/C-Turkey/main/data/cturkey_v1.tsv",
    "https://raw.githubusercontent.com/altinisik/C-Turkey/main/cturkey_v1.tsv",
    "https://raw.githubusercontent.com/altinisik/C-Turkey/master/data/cturkey_v1.tsv",
    "https://raw.githubusercontent.com/altinisik/C-Turkey/master/cturkey_v1.tsv",
  ):
    r = safe_get(u, timeout=60)
    if r and r.status_code == 200 and len(r.content) > 20_000:
      with open(outp, "wb") as fh:
        fh.write(r.content)
      print(f"  Saved C-Turkey from {u}: {len(r.content):,} B", flush=True)
      return
  # Fallback: GitHub API tree
  tr = safe_get("https://api.github.com/repos/altinisik/C-Turkey/git/trees/main?recursive=1", timeout=30)
  if not (tr and tr.status_code == 200):
    tr = safe_get("https://api.github.com/repos/altinisik/C-Turkey/git/trees/master?recursive=1", timeout=30)
  if tr and tr.status_code == 200:
    branch = "main" if "main" in tr.url else "master"
    for item in tr.json().get("tree", []):
      p = item.get("path", "")
      if p.lower().endswith((".tsv", ".csv")) and ("cturkey" in p.lower() or "data" in p.lower()):
        r = safe_get(f"https://raw.githubusercontent.com/altinisik/C-Turkey/{branch}/{p}", timeout=60)
        if r and r.status_code == 200 and len(r.content) > 10_000:
          with open(outp, "wb") as fh:
            fh.write(r.content)
          print(f"  Saved C-Turkey ({p}): {len(r.content):,} B", flush=True)
          return
  # Fallback: Zenodo search C-Turkey
  zr = safe_get("https://zenodo.org/api/records", params={"q": "C-Turkey radiocarbon", "size": 5}, timeout=45)
  if zr and zr.status_code == 200:
    for hit in zr.json().get("hits", {}).get("hits", []):
      for f in hit.get("files", []):
        if f.get("key", "").lower().endswith((".tsv", ".csv", ".zip")):
          dl = (f.get("links") or {}).get("self")
          if dl:
            fr = safe_get(dl, timeout=90)
            if fr and fr.status_code == 200 and len(fr.content) > 10_000:
              ext = os.path.splitext(f["key"])[1].lower()
              dst = os.path.join(RAW_DIR, f"cturkey_zenodo{ext}")
              with open(dst, "wb") as fh:
                fh.write(fr.content)
              print(f"  Saved C-Turkey Zenodo ({f['key']}): {len(fr.content):,} B", flush=True)
              return


def download_medafricarbon():
  print("[2] Harvesting MedAfriCarbon (North Africa & Sahara radiocarbon database, Zenodo 3688530)...", flush=True)
  r = safe_get("https://zenodo.org/api/records/3688530", timeout=45)
  if r and r.status_code == 200:
    rec = r.json()
    for f in rec.get("files", []):
      fn = f.get("key", "")
      if fn.lower().endswith((".csv", ".tsv", ".zip", ".geojson")):
        dst = os.path.join(RAW_DIR, f"medafricarbon_{fn}")
        if os.path.exists(dst) and os.path.getsize(dst) > 5000:
          print(f"  Already cached: {dst}", flush=True)
          continue
        dl = (f.get("links") or {}).get("self")
        if dl:
          fr = safe_get(dl, timeout=90)
          if fr and fr.status_code == 200:
            with open(dst, "wb") as fh:
              fh.write(fr.content)
            print(f"  Saved MedAfriCarbon {fn}: {len(fr.content):,} B", flush=True)


def download_ees_delta_arcgis():
  print("[3] Probing EES Delta Survey ArcGIS Online Feature Layer...", flush=True)
  outp = os.path.join(RAW_DIR, "ees_delta_survey.geojson")
  if os.path.exists(outp) and os.path.getsize(outp) > 20_000:
    print(f"  Already cached: {outp}", flush=True)
    return
  # Search ArcGIS Online public items for EES Delta Survey
  sr = safe_get("https://www.arcgis.com/sharing/rest/search", params={
    "q": 'title:"Delta Survey" AND type:"Feature Service"', "f": "json", "num": 10
  }, timeout=45)
  if sr and sr.status_code == 200:
    for it in sr.json().get("results", []):
      u = it.get("url")
      if not u:
        continue
      print(f"  Found ArcGIS item: {it.get('title')} -> {u}", flush=True)
      qurl = u.rstrip("/") + "/0/query"
      qr = safe_get(qurl, params={"where": "1=1", "outFields": "*", "f": "geojson", "resultRecordCount": 2000}, timeout=60)
      if qr and qr.status_code == 200 and len(qr.content) > 10_000:
        try:
          gj = qr.json()
          if gj.get("features"):
            with open(outp, "w", encoding="utf-8") as fh:
              json.dump(gj, fh, ensure_ascii=False)
            print(f"  Saved EES Delta Survey: {len(gj['features'])} sites!", flush=True)
            return
        except Exception:
          pass


def download_eamena_and_regional_zenodo():
  print("[4] Downloading EAMENA & MENA regional archaeological datasets from Zenodo probe...", flush=True)
  probe_p = os.path.join(RAW_DIR, "zenodo_arch_probe.json")
  if not os.path.exists(probe_p):
    return
  cat = json.load(open(probe_p, "r", encoding="utf-8"))
  downloaded = 0
  for tag, hits in cat.items():
    for hit in hits[:4]:
      rid = hit.get("id")
      for f in hit.get("files", []):
        fn = f.get("key", "")
        sz = int(f.get("size") or 0)
        if sz <= 500 or sz > 40_000_000:
          continue
        if not fn.lower().endswith((".csv", ".tsv", ".geojson", ".json")):
          continue
        safe_fn = f"reg_{tag}_{rid}_{os.path.basename(fn)}"
        dst = os.path.join(RAW_DIR, safe_fn)
        if os.path.exists(dst) and os.path.getsize(dst) > 500:
          continue
        url = f.get("url")
        if url:
          fr = safe_get(url, timeout=90)
          if fr and fr.status_code == 200:
            with open(dst, "wb") as fh:
              fh.write(fr.content)
            downloaded += 1
            print(f"  Saved {safe_fn}: {len(fr.content):,} B ({hit.get('title','')[:60]})", flush=True)
        time.sleep(0.3)
  print(f"  Downloaded {downloaded} regional Zenodo tables", flush=True)


def download_dasi_arabia():
  print("[5] Probing DASI (South Arabian Inscriptions & Archaeological Sites) & Open Context...", flush=True)
  # Probe DASI Zenodo / GitHub / CNR endpoints
  zr = safe_get("https://zenodo.org/api/records", params={"q": '"DASI" OR "South Arabian" OR "Arabian Peninsula" archaeological sites', "size": 8}, timeout=45)
  if zr and zr.status_code == 200:
    for hit in zr.json().get("hits", {}).get("hits", []):
      for f in hit.get("files", []):
        fn = f.get("key", "")
        sz = int(f.get("size") or 0)
        if 500 < sz < 30_000_000 and fn.lower().endswith((".csv", ".tsv", ".geojson", ".json")):
          safe_fn = f"arabia_z_{hit.get('id')}_{os.path.basename(fn)}"
          dst = os.path.join(RAW_DIR, safe_fn)
          if not os.path.exists(dst):
            fr = safe_get((f.get("links") or {}).get("self"), timeout=90)
            if fr and fr.status_code == 200:
              with open(dst, "wb") as fh:
                fh.write(fr.content)
              print(f"  Saved {safe_fn}: {len(fr.content):,} B", flush=True)


def download_caucasus_afghanistan_registers():
  print("[6] Probing Caucasus (Armenia, Azerbaijan, Georgia) & Afghanistan open archaeological tables...", flush=True)
  queries = [
    ("caucasus_c14", 'Caucasus OR Georgia OR Armenia OR Azerbaijan radiocarbon OR archaeological sites'),
    ("afghanistan_ball", 'Afghanistan archaeological sites OR Warwick Ball OR Bactria'),
    ("iran_arch", 'Iran archaeological sites OR Fars OR Susiana OR Luristan OR Khorasan survey'),
  ]
  for tag, q in queries:
    zr = safe_get("https://zenodo.org/api/records", params={"q": q, "size": 6}, timeout=45)
    if zr and zr.status_code == 200:
      for hit in zr.json().get("hits", {}).get("hits", []):
        for f in hit.get("files", []):
          fn = f.get("key", "")
          sz = int(f.get("size") or 0)
          if 500 < sz < 30_000_000 and fn.lower().endswith((".csv", ".tsv", ".geojson", ".json")):
            safe_fn = f"{tag}_{hit.get('id')}_{os.path.basename(fn)}"
            dst = os.path.join(RAW_DIR, safe_fn)
            if not os.path.exists(dst):
              fr = safe_get((f.get("links") or {}).get("self"), timeout=90)
              if fr and fr.status_code == 200:
                with open(dst, "wb") as fh:
                  fh.write(fr.content)
                print(f"  Saved {safe_fn}: {len(fr.content):,} B ({hit.get('title','')[:55]})", flush=True)
    time.sleep(0.3)


if __name__ == "__main__":
  download_cturkey()
  download_medafricarbon()
  download_ees_delta_arcgis()
  download_eamena_and_regional_zenodo()
  download_dasi_arabia()
  download_caucasus_afghanistan_registers()
  print("DONE harvest_handbook_regional_registers.py", flush=True)
