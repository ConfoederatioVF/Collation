"""Downloads and inspects core Japanese, South Korean, and North Korean archaeological & census open repositories for Project CASTLE."""

import json
import os
import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CASTLE_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE")
RAW_ARCH = os.path.join(CASTLE_DIR, "_shared", "sites_korea_japan", "0.raw_data")
RAW_CEN = os.path.join(CASTLE_DIR, "_shared", "_census_cache")
os.makedirs(RAW_ARCH, exist_ok=True)
os.makedirs(RAW_CEN, exist_ok=True)

HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OperationViscount/2.0"}


def download_file(arg0_name, arg1_url, arg2_out_path):
  if os.path.exists(arg2_out_path) and os.path.getsize(arg2_out_path) > 1024:
    print(f"[SKIP] {arg0_name} already exists ({os.path.getsize(arg2_out_path):,} bytes)")
    return True
  try:
    r = requests.get(arg1_url, headers=HDR, timeout=120, stream=True, allow_redirects=True)
    if r.status_code != 200:
      print(f"[FAIL] {arg0_name}: HTTP {r.status_code}")
      return False
    total = 0
    with open(arg2_out_path, "wb") as fh:
      for chunk in r.iter_content(chunk_size=65536):
        if chunk:
          fh.write(chunk)
          total += len(chunk)
    print(f"[OK] {arg0_name} -> {os.path.basename(arg2_out_path)} ({total:,} bytes)")
    return True
  except Exception as e:
    print(f"[ERR] {arg0_name}: {e}")
    return False


def main():
  # 1. Inspect kotdijian & ercrema repos for Palaeolithic / Jomon / Yayoi / Kofun datasets
  for user in ("kotdijian", "ercrema"):
    r = requests.get(f"https://api.github.com/users/{user}/repos?per_page=100", headers=HDR, timeout=20)
    if r.status_code == 200:
      repos = [(x["name"], x.get("default_branch", "main"), x.get("description") or "") for x in r.json()]
      print(f"\n=== GitHub {user} ({len(repos)} repos) ===")
      for nm, br, desc in repos:
        if any(k in (nm + " " + desc).lower() for k in ("jasosr", "palaeo", "paleo", "jomon", "yayoi", "kofun", "c14", "japan", "korea", "site", "arch", "mound", "shell", "iseki")):
          print(f"  {nm} ({br}): {desc[:90]}")

  # 2. Inspect KHS_LIST XML structure & NRICH_DICT / NRICH_JOUR XML structure
  print("\n=== KHS_LIST sample XML ===")
  r_khs = requests.get("https://www.khs.go.kr/cha/SearchKindOpenapiList.do?pageUnit=2&pageIndex=1", headers=HDR, timeout=20)
  print(r_khs.text[:1500])

  print("\n=== NRICH_DICT sample XML ===")
  r_nd = requests.get("https://portal.nrich.go.kr/kor/openapi.do?idx=39&firstindex=1&recordcountperpage=2", headers=HDR, timeout=20)
  print(r_nd.text[:1500])

  print("\n=== NRICH_JOUR sample XML ===")
  r_nj = requests.get("https://portal.nrich.go.kr/kor/openapi.do?idx=206&firstindex=1&recordcountperpage=2", headers=HDR, timeout=20)
  print(r_nj.text[:1500])

  # 3. Check Zenodo 8377215 & 4308578 file URLs
  for zid in (8377215, 4308578):
    r_z = requests.get(f"https://zenodo.org/api/records/{zid}", headers=HDR, timeout=20)
    if r_z.status_code == 200:
      zj = r_z.json()
      print(f"\n=== Zenodo {zid}: {zj.get('metadata', {}).get('title')} ===")
      for f in zj.get("files", []):
        print(" ", f["key"], f["size"], f["links"]["self"])
        out_p = os.path.join(RAW_ARCH, f"zenodo_{zid}_{f['key']}")
        download_file(f"Zenodo_{zid}_{f['key']}", f["links"]["self"], out_p)

  # 4. Download GitHub repository archives (archaeology + census)
  gh_downloads = [
    ("JASOSR", "https://github.com/kotdijian/JASOSR/archive/refs/heads/master.zip", os.path.join(RAW_ARCH, "gh_kotdijian_JASOSR.zip")),
    ("JAPAN_C14DB", "https://github.com/ercrema/japan_c14db/archive/refs/heads/master.zip", os.path.join(RAW_ARCH, "gh_ercrema_japan_c14db.zip")),
    ("YAYOI_DEMO", "https://github.com/ercrema/yayoi_demo/archive/refs/heads/main.zip", os.path.join(RAW_ARCH, "gh_ercrema_yayoi_demo.zip")),
    ("HANSEONG_C14", "https://github.com/ChanToRe/Hanseong_C14/archive/refs/heads/main.zip", os.path.join(RAW_ARCH, "gh_ChanToRe_Hanseong_C14.zip")),
    ("TIDYCENSUSKR", "https://github.com/sigmafelix/tidycensuskr/archive/refs/heads/main.zip", os.path.join(RAW_CEN, "gh_sigmafelix_tidycensuskr.zip")),
    ("SK_POP", "https://github.com/southkorea/southkorea-population/archive/refs/heads/master.zip", os.path.join(RAW_CEN, "gh_southkorea_population.zip")),
    ("ESTAT_FUKUI", "https://github.com/code4fukui/e-stat/archive/refs/heads/main.zip", os.path.join(RAW_CEN, "gh_code4fukui_estat.zip")),
    ("JP_MUNI", "https://github.com/piuccio/open-data-jp-municipalities/archive/refs/heads/master.zip", os.path.join(RAW_CEN, "gh_piuccio_jp_municipalities.zip")),
  ]
  for name, url, out_p in gh_downloads:
    download_file(name, url, out_p)


if __name__ == "__main__":
  main()

