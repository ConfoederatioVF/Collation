"""Verifies EVERY single specific city/defect named by the Hydrogen Auditor Round-2 on live rebuilt disk!"""
import glob
import json
import os

AUSTRAL = r"histmap\1.data_raw\population_regional\AUSTRAL"

def load_ch(stem):
  p = glob.glob(os.path.join(AUSTRAL, "*", "*", f"{stem}_settlements.json"))[0]
  return json.load(open(p, encoding="utf-8"))

# 1. Check 0 disaggregation citations across all 16 chapters
dis_cnt = 0
unbal_other = 0
for p in glob.glob(os.path.join(AUSTRAL, "*", "*", "*_settlements.json")):
  d = json.load(open(p, encoding="utf-8"))
  for k, v in d.items():
    if "disaggregation" in " ".join(v.get("sources") or []).lower():
      dis_cnt += 1
    for o in v.get("other_names") or []:
      if ("(" in o and ")" not in o) or (")" in o and "(" not in o):
        unbal_other += 1
print(f"GLOBAL CHECK: disaggregation_count={dis_cnt} | unbalanced_other_names={unbal_other}")

# 2. Check specific auditor-named settlements
checks = [
  ("modern_new_guinea", ["Timika", "Waisai", "Botawa", "Wewak", "Daru", "Kavieng"]),
  ("modern_new_zealand", ["Levin", "Richmond", "Oamaru"]),
  ("modern_australia", ["Albany", "Warrnambool", "Cairns", "Darwin"]),
  ("colonial_australia", ["East Maitland", "Araluen", "Etheridge", "Aramac", "Yalpara", "Semaphore", "Albany"]),
  ("modern_polynesia", ["Amuri", "Taunga", "'Eueiki", "Falevai", "Motukoiti"]),
  ("modern_melanesia_micro", ["Kitti", "Kitti Wone", "Namoluk", "Magur", "Kwajalein", "Malolo", "Vulaga", "Veivatuloa", "Ambrym", "Motalava", "Hienghène", "Voh", "Butaritari"]),
  ("precolonial_polynesia", ["Mu'a", "Kauvai"]),
  ("precolonial_melanesia_micro", ["Lebang Takoroi", "Lebang Halika", "Lebang Tatale"]),
]
for ch_stem, names in checks:
  d = load_ch(ch_stem)
  print(f"\n=== {ch_stem} ===")
  nset = {x.lower() for x in names}
  for k, v in d.items():
    if v["name"].lower() in nset or any(v["name"].lower().startswith(x + " (") for x in nset):
      print(f"  {k:38s} | {v['coords']} | adm={v['admin1']} | {v['population']}")
