import os
import urllib.request

DL = r"f:\Active Projects\Project 1509 - SVEA\tests\dl"
os.makedirs(DL, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0"}

files = {
  "nc_evolution_pop.xlsx": "https://www.isee.nc/sites/default/files/2025-10/evolution-population_0.xlsx",
  "nc_rp_pop.xls": "https://www.isee.nc/sites/default/files/2025-10/rp-population_0.xls",
  "nc_rp_pop_ref.xlsx": "https://www.isee.nc/sites/default/files/2025-10/rp-populations-reference_0.xlsx",
  "kir_admpop_2020.xlsx": "https://data.humdata.org/dataset/e656842e-9643-4ef7-97f9-18c33654022d/resource/cb0fd355-5326-4574-a76a-81bae7894991/download/kir_admpop_2020.xlsx",
  "mhl_admpop_2021.xlsx": "https://data.humdata.org/dataset/855354a5-f090-4bb2-8e65-e25d156d9693/resource/c5accc3e-03b1-4fcf-8e5b-bfd5c1bc8eb2/download/mhl_admpop_2021.xlsx",
  "fsm_pplp.xlsx": "https://data.humdata.org/dataset/a1a30440-d7ab-4e22-8636-ef717a20be5d/resource/9eab4b38-d225-425a-ac45-e2fbcc2ce0f8/download/fsm_pplp.xlsx",
}

for fn, url in files.items():
  out = os.path.join(DL, fn)
  try:
    req = urllib.request.Request(url, headers=HEADERS)
    data = urllib.request.urlopen(req, timeout=30).read()
    with open(out, "wb") as f:
      f.write(data)
    print(f"OK {fn}: {len(data):,} B")
  except Exception as e:
    print(f"ERR {fn}: {e}")
