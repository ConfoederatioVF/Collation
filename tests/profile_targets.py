import json
import os
from collections import Counter, defaultdict

BASE = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\AUSTRAL\_shared\settlement_sources"

# 1. Inspect Micronesia & Polynesia counts by polity across all existing modern files
micpol_countries = {
  "Federated States of Micronesia", "Marshall Islands", "Palau", "Guam",
  "Northern Mariana Islands", "Kiribati", "Nauru", "Samoa", "Tonga",
  "French Polynesia", "Cook Islands", "Tuvalu", "Niue", "Tokelau",
  "Wallis and Futuna", "Pitcairn Islands", "Chile",
}
mel_countries = {"Fiji", "Solomon Islands", "Vanuatu", "New Caledonia"}

for fn in ["enriched_mel_mic_pol_modern.json", "micronesia_census_raw.json", "polynesia_census_raw.json", "melanesia_census_raw.json"]:
  d = json.load(open(os.path.join(BASE, fn), encoding="utf-8"))
  s = d.get("settlements", d)
  by_c = defaultdict(list)
  for k, v in s.items():
    by_c[v.get("country", "")].append(v)
  print(f"=== {fn} ===")
  for c in sorted(by_c.keys()):
    rows = by_c[c]
    yrs = Counter(int(y) for r in rows for y in (r.get("population") or {}))
    min_y = min(yrs) if yrs else None
    pre95 = sum(1 for r in rows if min(int(y) for y in r.get("population", {"9999": 1})) <= 1995)
    pre70 = sum(1 for r in rows if min(int(y) for y in r.get("population", {"9999": 1})) <= 1970)
    print(f"  {c:32s}: n={len(rows):3d} | pre95={pre95:3d} | pre70={pre70:3d} | top_yrs={yrs.most_common(5)}")

# 2. Check PNG admin2 / LLG coverage in enriched_png_wards_llgs.json
png = json.load(open(os.path.join(BASE, "enriched_png_wards_llgs.json"), encoding="utf-8"))["settlements"]
print("\n=== PNG enriched_png_wards_llgs sample fields ===")
for k in list(png.keys())[:5]:
  print(" ", k, json.dumps(png[k], ensure_ascii=False))

# Check unique LLGs / admin2 / admin_code prefixes in PNG
llg_prefixes = Counter()
for v in png.values():
  code = str(v.get("admin_code", ""))
  if len(code) >= 8:
    llg_prefixes[code[:8]] += 1
print(f"PNG unique 8-char LLG code prefixes: {len(llg_prefixes)}, sample: {llg_prefixes.most_common(5)}")

# 3. Check Indonesian Papua sample fields
pap = json.load(open(os.path.join(BASE, "enriched_papua_idn_distriks.json"), encoding="utf-8"))["settlements"]
print("\n=== Papua IDN enriched_papua_idn_distriks sample fields ===")
for k in list(pap.keys())[:5]:
  print(" ", k, json.dumps(pap[k], ensure_ascii=False))
adm2 = Counter((v.get("admin1", ""), v.get("admin2", "")) for v in pap.values())
print(f"Papua IDN unique (admin1, admin2): {len(adm2)}")
