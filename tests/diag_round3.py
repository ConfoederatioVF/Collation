import json
import math
import os

SRC = r"histmap\1.data_raw\population_regional\AUSTRAL\_shared\settlement_sources"
AUSTRAL = r"histmap\1.data_raw\population_regional\AUSTRAL"

def hav(a1, o1, a2, o2):
  d1, d2 = math.radians(a2 - a1), math.radians(o2 - o1)
  x = math.sin(d1 / 2) ** 2 + math.cos(math.radians(a1)) * math.cos(math.radians(a2)) * math.sin(d2 / 2) ** 2
  return 6371.0 * 2.0 * math.atan2(math.sqrt(x), math.sqrt(max(0.0, 1.0 - x)))

# 1. All "disaggregation" records across SRC
disagg = []
for fn in sorted(os.listdir(SRC)):
  if not fn.endswith(".json"):
    continue
  d = json.load(open(os.path.join(SRC, fn), encoding="utf-8"))
  so = d.get("settlements", d)
  if not isinstance(so, dict):
    continue
  for k, v in so.items():
    if not isinstance(v, dict):
      continue
    s = " ".join(v.get("sources") or []).lower()
    if "disaggregation" in s:
      disagg.append((fn, k, v.get("name"), v.get("country"), v.get("population")))
print(f"DISAGGREGATION records total={len(disagg)}:")
for x in disagg:
  print(" ", x)

# 2. Port Moresby inner 10 km in modern_new_guinea_settlements.json
ng = json.load(open(os.path.join(AUSTRAL, "3.modern", "14.modern_new_guinea", "modern_new_guinea_settlements.json"), encoding="utf-8"))
print("\nPORT MORESBY <= 12 km:")
for k, v in ng.items():
  if v.get("country") == "Papua New Guinea":
    dist = hav(v["coords"][0], v["coords"][1], -9.4438, 147.1803)
    if dist <= 12.0:
      print(f"  {dist:.2f} km | {k} | {v['name']} | {v.get('admin1')} | {v['population']} | {v['sources'][:1]}")

# 3. Polynesian Outer Islands & Cook Islands Amuri/Aitutaki & FSM gap file
mm = json.load(open(os.path.join(AUSTRAL, "3.modern", "15.modern_melanesia_micro", "modern_melanesia_micro_settlements.json"), encoding="utf-8"))
for k, v in mm.items():
  if "polynesian" in v["name"].lower() or (v["country"] == "Federated States of Micronesia" and any(w in v["name"].lower() for w in ("kitti", "nett", "village", "magur", "makur"))):
    print("MM:", k, "|", v["name"], "|", v["coords"], "|", v["population"])

mp = json.load(open(os.path.join(AUSTRAL, "3.modern", "16.modern_polynesia", "modern_polynesia_settlements.json"), encoding="utf-8"))
for k, v in mp.items():
  if v["country"] == "Cook Islands" and any(w in v["name"].lower() for w in ("amuri", "aitutaki")):
    print("CK:", k, "|", v["name"], "|", v["coords"], "|", v["population"])
